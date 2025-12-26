"""
AI-Powered PDF Parser for Bank Statements

Uses vision models (LMStudio, OpenAI, etc.) to extract structured
transaction data from PDF bank statements. Designed as a fallback
when bank-specific parsers fail or for unknown bank formats.

Features:
- Multi-page PDF support with intelligent batching
- Structured JSON output with confidence scores
- Merchant name extraction and normalization
- Category hints for downstream processing
- Works with local models (free) or cloud APIs
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from . import PDFParseResult
from ..normalization import normalize_description, parse_date

logger = logging.getLogger(__name__)


@dataclass
class AIParseConfig:
    """Configuration for AI PDF parsing."""
    max_pages_per_request: int = 3  # Batch pages to reduce API calls
    temperature: float = 0.1  # Low temp for consistent extraction
    max_tokens: int = 4096  # Response size limit
    timeout: float = 120.0  # Longer timeout for vision models
    retry_count: int = 2
    include_enrichment: bool = True  # Extract merchant names, categories


# Extraction prompt optimized for financial documents
EXTRACTION_PROMPT = """You are a financial document parser. Extract ALL transactions from this bank statement image.

For EACH transaction, extract:
- date: Transaction date (YYYY-MM-DD format)
- description: Full transaction description as shown
- amount: Transaction amount (negative for debits/withdrawals, positive for credits/deposits)
- running_balance: Balance after transaction if shown (null if not visible)
- merchant_name: Cleaned merchant/payee name (e.g., "STARBUCKS #12345 SEATTLE WA" -> "Starbucks")
- category_hint: Likely category (e.g., "food_dining", "shopping", "utilities", "income", "transfer")

CRITICAL RULES:
1. Extract EVERY transaction row visible in the image
2. Use NEGATIVE amounts for debits/purchases/withdrawals
3. Use POSITIVE amounts for credits/deposits/refunds
4. Dates must be YYYY-MM-DD format
5. Include the exact description text from the statement
6. If balance column exists, capture it

Return ONLY valid JSON in this exact format:
{
  "transactions": [
    {
      "date": "2025-01-15",
      "description": "STARBUCKS STORE #12345 SEATTLE WA",
      "amount": -5.75,
      "running_balance": 1234.56,
      "merchant_name": "Starbucks",
      "category_hint": "food_dining"
    }
  ],
  "metadata": {
    "bank_name": "Bank of America",
    "account_last4": "1234",
    "statement_period": "January 2025",
    "opening_balance": 1500.00,
    "closing_balance": 1234.56,
    "page_number": 1
  },
  "confidence": 0.95
}

If you cannot parse the image or it's not a bank statement, return:
{"transactions": [], "metadata": {}, "confidence": 0.0, "error": "reason"}
"""


def _pdf_to_images(file_bytes: bytes, dpi: int = 150) -> List[bytes]:
    """Convert PDF pages to PNG images.

    Uses pdfplumber for rendering (already a dependency).
    Falls back to pdf2image if available for better quality.
    """
    images = []

    # Try pdf2image first (better quality)
    try:
        from pdf2image import convert_from_bytes
        pil_images = convert_from_bytes(file_bytes, dpi=dpi)
        for img in pil_images:
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            images.append(buf.getvalue())
        return images
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"pdf2image failed, trying pdfplumber: {e}")

    # Fallback to pdfplumber page rendering
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                # Render page to image
                img = page.to_image(resolution=dpi)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                images.append(buf.getvalue())
        return images
    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {e}")
        raise ValueError(f"Cannot convert PDF to images: {e}")


def _encode_image_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 data URL."""
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:image/png;base64,{b64}"


def _call_vision_api(
    images_b64: List[str],
    config: AIParseConfig,
    provider_url: str,
    api_key: str,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Call vision API with images and extraction prompt.

    Works with OpenAI-compatible APIs (LMStudio, OpenAI, etc.)
    """
    import requests

    # Build messages with images
    content = [{"type": "text", "text": EXTRACTION_PROMPT}]
    for img_b64 in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": img_b64, "detail": "high"}
        })

    # Determine model
    if not model:
        # Try to get available models from LMStudio
        try:
            models_resp = requests.get(
                f"{provider_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
            if models_resp.ok:
                models = models_resp.json().get("data", [])
                # Prefer vision models
                vision_models = [m for m in models if any(
                    x in m.get("id", "").lower()
                    for x in ["vision", "vl", "llava", "qwen"]
                )]
                model = vision_models[0]["id"] if vision_models else models[0]["id"] if models else "default"
        except Exception:
            model = "default"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{provider_url}/chat/completions",
        json=payload,
        headers=headers,
        timeout=config.timeout
    )

    if not response.ok:
        raise ValueError(f"Vision API error: {response.status_code} - {response.text}")

    result = response.json()
    content_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Parse JSON from response
    try:
        # Handle markdown code blocks
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0]
        elif "```" in content_text:
            content_text = content_text.split("```")[1].split("```")[0]

        return json.loads(content_text.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        logger.debug(f"Raw response: {content_text[:500]}")
        return {"transactions": [], "confidence": 0.0, "error": f"JSON parse error: {e}"}


def _normalize_transaction(tx: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize AI-extracted transaction to standard format."""
    # Parse date
    date_str = tx.get("date", "")
    try:
        if isinstance(date_str, str):
            posted_at = parse_date(date_str)
        else:
            posted_at = date_str
    except Exception:
        posted_at = None

    # Get amount
    amount = tx.get("amount", 0)
    if isinstance(amount, str):
        # Handle string amounts like "$1,234.56" or "(123.45)"
        amount = amount.replace("$", "").replace(",", "").strip()
        if amount.startswith("(") and amount.endswith(")"):
            amount = -float(amount[1:-1])
        else:
            amount = float(amount)

    # Normalize description
    description = tx.get("description", "")
    description_norm = normalize_description(description)

    return {
        "posted_at": posted_at,
        "description": description,
        "description_norm": description_norm,
        "amount": float(amount),
        "running_balance": tx.get("running_balance"),
        "ai_merchant_name": tx.get("merchant_name"),
        "ai_category_hint": tx.get("category_hint"),
        "ai_confidence": tx.get("confidence", 0.8),
    }


def parse_pdf_with_ai(
    file_bytes: bytes,
    config: Optional[AIParseConfig] = None,
    provider_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> PDFParseResult:
    """
    Parse a PDF bank statement using AI vision model.

    Args:
        file_bytes: Raw PDF file bytes
        config: Parsing configuration (uses defaults if None)
        provider_url: API base URL (defaults to LMStudio settings)
        api_key: API key (defaults to LMStudio settings)
        model: Model name (auto-detects if None)

    Returns:
        PDFParseResult with extracted transactions

    Raises:
        ValueError: If PDF cannot be parsed
    """
    if config is None:
        config = AIParseConfig()

    # Load provider settings from environment/config
    if provider_url is None or api_key is None:
        from ..ai import AIConfig
        ai_config = AIConfig.from_env()
        provider_url = provider_url or ai_config.lmstudio_base_url
        api_key = api_key or ai_config.lmstudio_api_key
        model = model or ai_config.lmstudio_model

    logger.info(f"AI PDF parsing with provider: {provider_url}")

    # Convert PDF to images
    try:
        page_images = _pdf_to_images(file_bytes)
    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {e}")
        return PDFParseResult(rows=[], meta={"error": str(e)}, anomalies=[str(e)])

    logger.info(f"Converted PDF to {len(page_images)} page images")

    all_transactions = []
    all_metadata = {}
    anomalies = []
    total_confidence = 0.0
    page_count = 0

    # Process pages in batches
    for i in range(0, len(page_images), config.max_pages_per_request):
        batch = page_images[i:i + config.max_pages_per_request]
        batch_b64 = [_encode_image_base64(img) for img in batch]

        logger.info(f"Processing pages {i+1}-{i+len(batch)} of {len(page_images)}")

        try:
            result = _call_vision_api(
                batch_b64, config, provider_url, api_key, model
            )

            if result.get("error"):
                anomalies.append(f"Page {i+1}: {result['error']}")
                continue

            # Extract transactions
            for tx in result.get("transactions", []):
                try:
                    normalized = _normalize_transaction(tx)
                    if normalized["posted_at"] is not None:
                        all_transactions.append(normalized)
                except Exception as e:
                    anomalies.append(f"Failed to normalize transaction: {e}")

            # Merge metadata
            meta = result.get("metadata", {})
            if meta:
                for key, value in meta.items():
                    if value and key not in all_metadata:
                        all_metadata[key] = value

            total_confidence += result.get("confidence", 0.0)
            page_count += 1

        except Exception as e:
            logger.error(f"Error processing pages {i+1}-{i+len(batch)}: {e}")
            anomalies.append(f"Pages {i+1}-{i+len(batch)}: {str(e)}")

    # Calculate average confidence
    avg_confidence = total_confidence / page_count if page_count > 0 else 0.0
    all_metadata["ai_confidence"] = avg_confidence
    all_metadata["ai_pages_processed"] = page_count
    all_metadata["ai_parser"] = "vision"

    # Sort transactions by date
    all_transactions.sort(key=lambda x: x.get("posted_at") or date.min)

    logger.info(f"AI extracted {len(all_transactions)} transactions with {avg_confidence:.0%} confidence")

    return PDFParseResult(
        rows=all_transactions,
        meta=all_metadata,
        anomalies=anomalies
    )


async def parse_pdf_with_ai_async(
    file_bytes: bytes,
    config: Optional[AIParseConfig] = None,
    provider_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> PDFParseResult:
    """Async version of parse_pdf_with_ai for use in async contexts."""
    import asyncio

    # Run sync version in thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: parse_pdf_with_ai(file_bytes, config, provider_url, api_key, model)
    )
