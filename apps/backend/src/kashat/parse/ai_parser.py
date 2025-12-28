"""
AI-Powered PDF Parser for Bank Statements

Supports multiple providers:
1. OpenAI (GPT-4o, GPT-4o-mini) - Native PDF input (best, no conversion)
2. LMStudio (Qwen2.5-VL, etc.) - Vision via images (free, local)

Features:
- Native PDF parsing with OpenAI (no image conversion needed!)
- Multi-page support with intelligent batching
- Structured JSON output with confidence scores
- Merchant name extraction and normalization
- Category hints for downstream processing
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
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
    max_pages_per_request: int = 10  # OpenAI supports up to 100 pages
    temperature: float = 0.1  # Low temp for consistent extraction
    max_tokens: int = 4096  # Response size limit
    timeout: float = 120.0  # Longer timeout for PDF processing
    retry_count: int = 2
    include_enrichment: bool = True  # Extract merchant names, categories
    prefer_native_pdf: bool = True  # Use native PDF input when available


# Extraction prompt optimized for financial documents
EXTRACTION_PROMPT = """You are a financial document parser. Extract ALL transactions from this bank statement.

For EACH transaction, extract:
- date: Transaction date (YYYY-MM-DD format)
- description: Full transaction description as shown
- amount: Transaction amount (negative for debits/withdrawals, positive for credits/deposits)
- running_balance: Balance after transaction if shown (null if not visible)
- merchant_name: Cleaned merchant/payee name (e.g., "STARBUCKS #12345 SEATTLE WA" -> "Starbucks")
- category_hint: Likely category (e.g., "food_dining", "shopping", "utilities", "income", "transfer")

CRITICAL RULES:
1. Extract EVERY transaction row visible
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
    "closing_balance": 1234.56
  },
  "confidence": 0.95
}

If you cannot parse or it's not a bank statement, return:
{"transactions": [], "metadata": {}, "confidence": 0.0, "error": "reason"}
"""


def _pdf_to_images(file_bytes: bytes, dpi: int = 150) -> List[bytes]:
    """Convert PDF pages to PNG images for vision models without native PDF support."""
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


def _call_openai_native_pdf(
    file_bytes: bytes,
    config: AIParseConfig,
    api_key: str,
    model: str = "gpt-4o-mini",
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call OpenAI API with native PDF input (no image conversion needed).

    This is the preferred method for OpenAI - sends PDF directly.
    Ref: https://platform.openai.com/docs/guides/pdf-files
    """
    import requests

    # Encode PDF as base64
    pdf_b64 = base64.b64encode(file_bytes).decode('utf-8')

    # Build message with native PDF input
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": EXTRACTION_PROMPT},
            {
                "type": "file",
                "file": {
                    "filename": "statement.pdf",
                    "file_data": f"data:application/pdf;base64,{pdf_b64}"
                }
            }
        ]
    }]

    url = base_url or "https://api.openai.com/v1"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    logger.info(f"Calling OpenAI with native PDF input ({len(file_bytes)} bytes)")

    response = requests.post(
        f"{url}/chat/completions",
        json=payload,
        headers=headers,
        timeout=config.timeout
    )

    if not response.ok:
        error_text = response.text[:500]
        logger.error(f"OpenAI API error: {response.status_code} - {error_text}")
        raise ValueError(f"OpenAI API error: {response.status_code}")

    result = response.json()
    content_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    return _parse_json_response(content_text)


def _call_openai_vision(
    images_b64: List[str],
    config: AIParseConfig,
    api_key: str,
    model: str = "gpt-4o-mini",
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call OpenAI API with images (fallback for older method or other providers).
    """
    import requests

    # Build messages with images
    content = [{"type": "text", "text": EXTRACTION_PROMPT}]
    for img_b64 in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": img_b64, "detail": "high"}
        })

    url = base_url or "https://api.openai.com/v1"

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
        f"{url}/chat/completions",
        json=payload,
        headers=headers,
        timeout=config.timeout
    )

    if not response.ok:
        raise ValueError(f"Vision API error: {response.status_code} - {response.text[:500]}")

    result = response.json()
    content_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    return _parse_json_response(content_text)


def _call_lmstudio_vision(
    images_b64: List[str],
    config: AIParseConfig,
    base_url: str,
    api_key: str = "lm-studio",
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call LMStudio API with images.

    LMStudio doesn't support native PDF, so we use image conversion.
    """
    import requests

    # Build messages with images
    content = [{"type": "text", "text": EXTRACTION_PROMPT}]
    for img_b64 in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": img_b64, "detail": "high"}
        })

    # Auto-detect model if not specified
    if not model:
        try:
            models_resp = requests.get(f"{base_url}/models", timeout=5)
            if models_resp.ok:
                models = models_resp.json().get("data", [])
                vision_models = [m for m in models if any(
                    x in m.get("id", "").lower()
                    for x in ["vision", "vl", "llava", "qwen"]
                )]
                model = vision_models[0]["id"] if vision_models else (models[0]["id"] if models else "default")
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
        f"{base_url}/chat/completions",
        json=payload,
        headers=headers,
        timeout=config.timeout
    )

    if not response.ok:
        raise ValueError(f"LMStudio API error: {response.status_code} - {response.text[:500]}")

    result = response.json()
    content_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    return _parse_json_response(content_text)


def _parse_json_response(content_text: str) -> Dict[str, Any]:
    """Parse JSON from AI response, handling markdown code blocks."""
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
    provider: Optional[str] = None,  # "openai", "lmstudio", "auto"
) -> PDFParseResult:
    """
    Parse a PDF bank statement using AI.

    Automatically selects the best method:
    - OpenAI with native PDF input (preferred - no conversion)
    - LMStudio with vision (free, requires image conversion)

    Args:
        file_bytes: Raw PDF file bytes
        config: Parsing configuration (uses defaults if None)
        provider: Force specific provider ("openai", "lmstudio", "auto")

    Returns:
        PDFParseResult with extracted transactions
    """
    if config is None:
        config = AIParseConfig()

    # Load AI configuration
    from ..ai import AIConfig
    ai_config = AIConfig.from_env()

    # Determine provider
    if provider is None or provider == "auto":
        # Prefer OpenAI if API key is available (native PDF support)
        if ai_config.openai_api_key:
            provider = "openai"
        else:
            provider = "lmstudio"

    logger.info(f"AI PDF parsing with provider: {provider}")

    all_transactions = []
    all_metadata = {}
    anomalies = []

    try:
        if provider == "openai" and ai_config.openai_api_key:
            # Use OpenAI with native PDF input (BEST - no image conversion!)
            logger.info("Using OpenAI native PDF input")
            result = _call_openai_native_pdf(
                file_bytes,
                config,
                api_key=ai_config.openai_api_key,
                model=ai_config.openai_model,
                base_url=ai_config.openai_base_url,
            )
            all_metadata["ai_method"] = "openai_native_pdf"

        else:
            # Use LMStudio or OpenAI with image conversion
            logger.info("Converting PDF to images for vision API")
            page_images = _pdf_to_images(file_bytes)
            logger.info(f"Converted PDF to {len(page_images)} images")

            # Process pages in batches
            for i in range(0, len(page_images), config.max_pages_per_request):
                batch = page_images[i:i + config.max_pages_per_request]
                batch_b64 = [_encode_image_base64(img) for img in batch]

                logger.info(f"Processing pages {i+1}-{i+len(batch)} of {len(page_images)}")

                if provider == "openai" and ai_config.openai_api_key:
                    result = _call_openai_vision(
                        batch_b64, config,
                        api_key=ai_config.openai_api_key,
                        model=ai_config.openai_model,
                        base_url=ai_config.openai_base_url,
                    )
                else:
                    result = _call_lmstudio_vision(
                        batch_b64, config,
                        base_url=ai_config.lmstudio_base_url,
                        api_key=ai_config.lmstudio_api_key,
                        model=ai_config.lmstudio_model,
                    )

                # Accumulate transactions from batch
                for tx in result.get("transactions", []):
                    all_transactions.append(tx)

                # Merge metadata
                for k, v in result.get("metadata", {}).items():
                    if v and k not in all_metadata:
                        all_metadata[k] = v

            all_metadata["ai_method"] = f"{provider}_vision"

        # Process single-call results (native PDF)
        if "transactions" in result and not all_transactions:
            all_transactions = result.get("transactions", [])
            all_metadata.update(result.get("metadata", {}))

        # Normalize all transactions
        normalized = []
        for tx in all_transactions:
            try:
                norm = _normalize_transaction(tx)
                if norm["posted_at"] is not None:
                    normalized.append(norm)
            except Exception as e:
                anomalies.append(f"Failed to normalize: {e}")

        # Add confidence to metadata
        confidence = result.get("confidence", 0.8)
        all_metadata["ai_confidence"] = confidence
        all_metadata["ai_provider"] = provider

        # Sort by date
        normalized.sort(key=lambda x: x.get("posted_at") or date.min)

        logger.info(f"AI extracted {len(normalized)} transactions with {confidence:.0%} confidence")

        return PDFParseResult(
            rows=normalized,
            meta=all_metadata,
            anomalies=anomalies
        )

    except Exception as e:
        logger.error(f"AI parsing failed: {e}")
        return PDFParseResult(
            rows=[],
            meta={"error": str(e), "ai_provider": provider},
            anomalies=[str(e)]
        )


async def parse_pdf_with_ai_async(
    file_bytes: bytes,
    config: Optional[AIParseConfig] = None,
    provider: Optional[str] = None,
) -> PDFParseResult:
    """Async version of parse_pdf_with_ai."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: parse_pdf_with_ai(file_bytes, config, provider)
    )
