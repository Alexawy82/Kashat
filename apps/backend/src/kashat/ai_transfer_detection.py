"""
AI-Enhanced Transfer Detection Module for LedgerLoop

Combines heuristic-based transfer detection with AI analysis for ambiguous cases.
Uses the same AI infrastructure as transaction categorization.

Key features:
- Pre-filter with heuristics (fast, free)
- AI analysis for uncertain pairs
- Learning from user confirmations
- Batch processing with job tracking
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Tuple

from .transfers import (
    jaccard_similarity,
    _canonical_pair,
    _is_income_description,
    _is_transfer_category,
    _transfer_description_keywords,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class TransferDetectionConfig:
    """Configuration for AI-enhanced transfer detection."""

    # Detection thresholds
    max_days: int = 3
    amount_tolerance_pct: float = 0.02  # 2%
    min_heuristic_score: float = 0.5

    # AI thresholds
    ai_confidence_threshold: float = 0.75  # Use AI suggestion if >= this
    high_confidence_threshold: float = 0.90  # Auto-confirm if >= this
    medium_confidence_threshold: float = 0.70  # Suggest to user

    # Processing
    batch_size: int = 20  # Pairs per AI batch
    max_concurrent_ai_calls: int = 2

    # Feature flags
    enable_ai_analysis: bool = True
    learn_from_confirmations: bool = True

    @classmethod
    def from_env(cls) -> "TransferDetectionConfig":
        """Load configuration from environment."""
        import os
        return cls(
            max_days=int(os.getenv("KASHAT_TRANSFER_MAX_DAYS", "3")),
            amount_tolerance_pct=float(os.getenv("KASHAT_TRANSFER_AMOUNT_TOL", "0.02")),
            min_heuristic_score=float(os.getenv("KASHAT_TRANSFER_MIN_SCORE", "0.5")),
            ai_confidence_threshold=float(os.getenv("KASHAT_TRANSFER_AI_THRESHOLD", "0.75")),
            enable_ai_analysis=os.getenv("KASHAT_TRANSFER_ENABLE_AI", "true").lower() == "true",
        )


# =============================================================================
# Result Dataclasses
# =============================================================================

@dataclass
class TransferCandidate:
    """A potential transfer pair for analysis."""
    left_id: str
    right_id: str
    left_description: str
    right_description: str
    left_amount: float
    right_amount: float
    left_account: str
    right_account: str
    left_date: str
    right_date: str
    left_category: Optional[str] = None
    right_category: Optional[str] = None
    heuristic_score: float = 0.0


@dataclass
class TransferAnalysisResult:
    """Result from AI analysis of a transfer pair."""
    left_id: str
    right_id: str
    is_transfer: bool
    confidence: float
    reasoning: str
    method: str  # 'heuristic', 'ai', 'ai-enhanced'
    provider: Optional[str] = None
    model: Optional[str] = None
    latency_ms: Optional[int] = None

    # Detailed scores
    amount_match_score: float = 0.0
    date_proximity_score: float = 0.0
    description_similarity: float = 0.0
    category_match_score: float = 0.0


@dataclass
class TransferDetectionJobResult:
    """Result from a bulk transfer detection job."""
    job_id: str
    total_pairs: int
    analyzed_pairs: int
    transfers_found: int
    high_confidence: int
    medium_confidence: int
    low_confidence: int
    rejected: int
    status: str
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


# =============================================================================
# AI Transfer Detection Service
# =============================================================================

class AITransferDetectionService:
    """
    AI-enhanced transfer detection service.

    Combines heuristic detection with AI analysis for better accuracy.
    """

    def __init__(self, config: Optional[TransferDetectionConfig] = None):
        self.config = config or TransferDetectionConfig.from_env()
        self._ai_service = None

    def _get_ai_service(self):
        """Lazy load AI service."""
        if self._ai_service is None:
            from .ai import get_ai_service
            self._ai_service = get_ai_service()
        return self._ai_service

    # -------------------------------------------------------------------------
    # Core Detection Methods
    # -------------------------------------------------------------------------

    def find_transfer_candidates(
        self,
        limit: int = 5000,
        include_analyzed: bool = False
    ) -> List[TransferCandidate]:
        """
        Find potential transfer pairs using heuristic pre-filtering.

        This is Phase 1: Fast heuristic scan to identify candidates.
        """
        from .db import get_conn
        conn = get_conn()

        # Get transactions with transfer indicators
        rows = conn.execute(
            """
            SELECT DISTINCT
                t.id,
                t.account_id,
                t.posted_at,
                t.amount,
                t.description_norm,
                t.is_income,
                COALESCE(c.name, '') AS category_name
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON tc.tx_id = t.id
            LEFT JOIN category c ON tc.category_id = c.id
            WHERE (
                LOWER(c.name) LIKE '%transfer%'
                OR LOWER(c.name) LIKE '%zelle%'
                OR LOWER(c.name) LIKE '%venmo%'
                OR LOWER(t.description_norm) LIKE '%transfer%'
                OR LOWER(t.description_norm) LIKE '%zelle%'
                OR LOWER(t.description_norm) LIKE '%venmo%'
                OR LOWER(t.description_norm) LIKE '%xfer%'
            )
              AND t.is_income = FALSE
            ORDER BY t.posted_at DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()

        # Build candidate transactions
        transactions = []
        for id_, acc, posted_at, amount, desc, is_income, cat_name in rows:
            if is_income or _is_income_description(desc):
                continue
            transactions.append({
                "id": id_,
                "account_id": acc,
                "posted_at": posted_at,
                "amount": float(amount),
                "description": desc or "",
                "category": cat_name or "",
            })

        # Find matching pairs
        candidates = []
        seen_pairs = set()

        for i, a in enumerate(transactions):
            for j in range(i + 1, len(transactions)):
                b = transactions[j]

                # Must be different accounts
                if a["account_id"] == b["account_id"]:
                    continue

                # Must have opposite signs
                if a["amount"] * b["amount"] >= 0:
                    continue

                # Check date proximity
                day_diff = abs((b["posted_at"] - a["posted_at"]).days)
                if day_diff > self.config.max_days:
                    continue

                # Check amount match
                abs_a = abs(a["amount"])
                abs_b = abs(b["amount"])
                avg_amt = (abs_a + abs_b) / 2.0
                amount_diff = abs(abs_a - abs_b)
                tolerance = max(0.01, avg_amt * self.config.amount_tolerance_pct)

                if amount_diff > tolerance:
                    continue

                # Calculate heuristic score
                left_id, right_id = _canonical_pair(a["id"], b["id"])
                pair_key = (left_id, right_id)

                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                # Skip if already in match_transfer (unless include_analyzed)
                if not include_analyzed:
                    exists = conn.execute(
                        "SELECT 1 FROM match_transfer WHERE left_tx_id = ? AND right_tx_id = ?",
                        [left_id, right_id],
                    ).fetchone()
                    if exists:
                        continue

                # Calculate component scores
                date_score = 1.0 - (day_diff / max(self.config.max_days, 1))
                amount_score = 1.0 - (amount_diff / max(tolerance, 0.01))
                desc_sim = jaccard_similarity(a["description"], b["description"])

                has_cat_a = _is_transfer_category(a["category"])
                has_cat_b = _is_transfer_category(b["category"])
                cat_score = 1.0 if (has_cat_a and has_cat_b) else (0.6 if (has_cat_a or has_cat_b) else 0.0)

                heuristic_score = (
                    0.25 * date_score +
                    0.30 * amount_score +
                    0.25 * cat_score +
                    0.20 * desc_sim
                )

                if heuristic_score < self.config.min_heuristic_score:
                    continue

                candidates.append(TransferCandidate(
                    left_id=left_id,
                    right_id=right_id,
                    left_description=a["description"],
                    right_description=b["description"],
                    left_amount=a["amount"],
                    right_amount=b["amount"],
                    left_account=a["account_id"],
                    right_account=b["account_id"],
                    left_date=str(a["posted_at"]),
                    right_date=str(b["posted_at"]),
                    left_category=a["category"],
                    right_category=b["category"],
                    heuristic_score=heuristic_score,
                ))

        # Sort by heuristic score (highest first)
        candidates.sort(key=lambda x: x.heuristic_score, reverse=True)
        return candidates

    async def analyze_pair_with_ai(
        self,
        candidate: TransferCandidate
    ) -> TransferAnalysisResult:
        """
        Analyze a single transfer pair using AI.

        This is Phase 2: AI analysis for ambiguous pairs.
        """
        import time
        start_time = time.time()

        # Build AI prompt
        prompt = self._build_transfer_prompt(candidate)

        try:
            ai_service = self._get_ai_service()

            # Use the AI service's analyze method with custom prompt
            response = await ai_service.analyze_with_prompt(
                prompt=prompt,
                task_type="transfer_detection"
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Parse AI response
            result = self._parse_ai_response(response, candidate)
            result.latency_ms = latency_ms
            result.method = "ai"
            result.provider = getattr(ai_service, 'current_provider', 'unknown')

            return result

        except Exception as e:
            logger.warning(f"AI analysis failed for pair {candidate.left_id}/{candidate.right_id}: {e}")

            # Fall back to heuristic result
            return TransferAnalysisResult(
                left_id=candidate.left_id,
                right_id=candidate.right_id,
                is_transfer=candidate.heuristic_score >= 0.7,
                confidence=candidate.heuristic_score,
                reasoning=f"Heuristic analysis (AI unavailable): score={candidate.heuristic_score:.2f}",
                method="heuristic-fallback",
                amount_match_score=1.0 - (abs(abs(candidate.left_amount) - abs(candidate.right_amount)) / max(abs(candidate.left_amount), 0.01)),
                description_similarity=jaccard_similarity(candidate.left_description, candidate.right_description),
            )

    def _build_transfer_prompt(self, candidate: TransferCandidate) -> str:
        """Build the prompt for AI transfer analysis."""
        return f"""Analyze these two bank transactions to determine if they represent the same internal transfer between accounts.

TRANSACTION A:
- Description: {candidate.left_description}
- Amount: ${candidate.left_amount:,.2f}
- Date: {candidate.left_date}
- Account: {candidate.left_account}
- Category: {candidate.left_category or 'Uncategorized'}

TRANSACTION B:
- Description: {candidate.right_description}
- Amount: ${candidate.right_amount:,.2f}
- Date: {candidate.right_date}
- Account: {candidate.right_account}
- Category: {candidate.right_category or 'Uncategorized'}

A transfer pair should have:
1. Opposite signs (one debit, one credit)
2. Same or very similar amounts
3. Transfer-related descriptions (e.g., "transfer to/from", "online banking transfer")
4. Close dates (typically same day or within a few days)
5. Different accounts (money moving between accounts)

Respond with ONLY valid JSON:
{{
  "is_transfer": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation",
  "transfer_type": "internal" | "external" | "unknown",
  "description_match": 0.0-1.0,
  "amount_match": 0.0-1.0
}}"""

    def _parse_ai_response(
        self,
        response: Any,
        candidate: TransferCandidate
    ) -> TransferAnalysisResult:
        """Parse AI response into TransferAnalysisResult."""
        try:
            # Handle string response
            if isinstance(response, str):
                # Extract JSON from response
                import re
                json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
            elif isinstance(response, dict):
                data = response
            else:
                data = {"is_transfer": False, "confidence": 0.5, "reasoning": "Unknown response format"}

            return TransferAnalysisResult(
                left_id=candidate.left_id,
                right_id=candidate.right_id,
                is_transfer=data.get("is_transfer", False),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                method="ai",
                description_similarity=float(data.get("description_match", 0.0)),
                amount_match_score=float(data.get("amount_match", 0.0)),
            )

        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return TransferAnalysisResult(
                left_id=candidate.left_id,
                right_id=candidate.right_id,
                is_transfer=candidate.heuristic_score >= 0.7,
                confidence=candidate.heuristic_score,
                reasoning=f"Parse error, using heuristic: {str(e)[:100]}",
                method="heuristic-fallback",
            )

    async def analyze_batch_with_ai(
        self,
        candidates: List[TransferCandidate]
    ) -> List[TransferAnalysisResult]:
        """
        Analyze multiple transfer pairs with AI in a single call.

        More efficient than individual calls for large batches.
        """
        if not candidates:
            return []

        # Build batch prompt
        prompt = self._build_batch_transfer_prompt(candidates)

        try:
            ai_service = self._get_ai_service()
            response = await ai_service.analyze_with_prompt(
                prompt=prompt,
                task_type="transfer_detection_batch"
            )

            # Parse batch response
            results = self._parse_batch_ai_response(response, candidates)
            return results

        except Exception as e:
            logger.warning(f"Batch AI analysis failed: {e}")
            # Fall back to individual heuristic results
            return [
                TransferAnalysisResult(
                    left_id=c.left_id,
                    right_id=c.right_id,
                    is_transfer=c.heuristic_score >= 0.7,
                    confidence=c.heuristic_score,
                    reasoning="Heuristic (batch AI failed)",
                    method="heuristic-fallback",
                )
                for c in candidates
            ]

    def _build_batch_transfer_prompt(self, candidates: List[TransferCandidate]) -> str:
        """Build prompt for batch transfer analysis."""
        pairs_text = []
        for i, c in enumerate(candidates, 1):
            pairs_text.append(f"""
PAIR {i}:
  Transaction A: "{c.left_description}" | ${c.left_amount:,.2f} | {c.left_date}
  Transaction B: "{c.right_description}" | ${c.right_amount:,.2f} | {c.right_date}
""")

        return f"""Analyze these transaction pairs to determine which are internal transfers.

A transfer pair should have:
- Opposite signs (one debit, one credit)
- Same/similar amounts
- Transfer-related descriptions
- Close dates (within 3 days)

{"".join(pairs_text)}

Respond with ONLY valid JSON array:
[
  {{"pair": 1, "is_transfer": true/false, "confidence": 0.0-1.0, "reasoning": "brief"}},
  ...
]"""

    def _parse_batch_ai_response(
        self,
        response: Any,
        candidates: List[TransferCandidate]
    ) -> List[TransferAnalysisResult]:
        """Parse batch AI response."""
        results = []

        try:
            if isinstance(response, str):
                import re
                json_match = re.search(r'\[[\s\S]*\]', response)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON array found")
            elif isinstance(response, list):
                data = response
            else:
                raise ValueError("Unexpected response type")

            # Map responses to candidates
            response_map = {item.get("pair", i+1): item for i, item in enumerate(data)}

            for i, candidate in enumerate(candidates, 1):
                item = response_map.get(i, {})
                results.append(TransferAnalysisResult(
                    left_id=candidate.left_id,
                    right_id=candidate.right_id,
                    is_transfer=item.get("is_transfer", False),
                    confidence=float(item.get("confidence", 0.5)),
                    reasoning=item.get("reasoning", ""),
                    method="ai-batch",
                ))

        except Exception as e:
            logger.error(f"Failed to parse batch response: {e}")
            for c in candidates:
                results.append(TransferAnalysisResult(
                    left_id=c.left_id,
                    right_id=c.right_id,
                    is_transfer=c.heuristic_score >= 0.7,
                    confidence=c.heuristic_score,
                    reasoning="Batch parse error, using heuristic",
                    method="heuristic-fallback",
                ))

        return results

    # -------------------------------------------------------------------------
    # Job-Based Bulk Processing
    # -------------------------------------------------------------------------

    def create_detection_job(self, limit: int = 5000) -> Tuple[str, List[TransferCandidate]]:
        """
        Create a new transfer detection job.

        Returns job_id and list of candidates to process.
        """
        from .db import get_conn
        conn = get_conn()

        # Find candidates
        candidates = self.find_transfer_candidates(limit=limit)

        if not candidates:
            return None, []

        # Create job record
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        conn.execute(
            """
            INSERT INTO ai_bulk_job (id, job_type, total_transactions, processed_transactions,
                                     enhanced_transactions, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [job_id, "transfer_detection", len(candidates), 0, 0, "pending", now],
        )

        return job_id, candidates

    async def process_detection_job(
        self,
        job_id: str,
        candidates: List[TransferCandidate],
        use_ai: bool = True
    ) -> TransferDetectionJobResult:
        """
        Process a transfer detection job.

        Combines heuristic filtering with optional AI analysis.
        """
        from .db import get_conn
        conn = get_conn()

        # Update status to processing
        conn.execute(
            "UPDATE ai_bulk_job SET status = 'processing' WHERE id = ?",
            [job_id],
        )

        processed = 0
        transfers_found = 0
        high_conf = 0
        medium_conf = 0
        low_conf = 0
        rejected = 0

        try:
            # Process in batches
            batch_size = self.config.batch_size

            for i in range(0, len(candidates), batch_size):
                # Check for cancellation
                status_row = conn.execute(
                    "SELECT status FROM ai_bulk_job WHERE id = ?",
                    [job_id],
                ).fetchone()
                if status_row and status_row[0] in ("cancelled", "paused"):
                    break

                batch = candidates[i:i + batch_size]

                # Analyze batch
                if use_ai and self.config.enable_ai_analysis:
                    results = await self.analyze_batch_with_ai(batch)
                else:
                    # Pure heuristic results
                    results = [
                        TransferAnalysisResult(
                            left_id=c.left_id,
                            right_id=c.right_id,
                            is_transfer=c.heuristic_score >= 0.7,
                            confidence=c.heuristic_score,
                            reasoning=f"Heuristic score: {c.heuristic_score:.2f}",
                            method="heuristic",
                        )
                        for c in batch
                    ]

                # Store results
                for result in results:
                    processed += 1

                    if result.is_transfer and result.confidence >= self.config.min_heuristic_score:
                        transfers_found += 1

                        # Categorize by confidence
                        if result.confidence >= self.config.high_confidence_threshold:
                            high_conf += 1
                        elif result.confidence >= self.config.medium_confidence_threshold:
                            medium_conf += 1
                        else:
                            low_conf += 1

                        # Store in match_transfer
                        self._store_transfer_match(result)
                    else:
                        rejected += 1

                # Update progress
                conn.execute(
                    """
                    UPDATE ai_bulk_job
                    SET processed_transactions = ?, enhanced_transactions = ?
                    WHERE id = ?
                    """,
                    [processed, transfers_found, job_id],
                )

            # Mark complete
            now = datetime.now(UTC).isoformat()
            conn.execute(
                """
                UPDATE ai_bulk_job
                SET status = 'completed', completed_at = ?,
                    processed_transactions = ?, enhanced_transactions = ?
                WHERE id = ?
                """,
                [now, processed, transfers_found, job_id],
            )

            return TransferDetectionJobResult(
                job_id=job_id,
                total_pairs=len(candidates),
                analyzed_pairs=processed,
                transfers_found=transfers_found,
                high_confidence=high_conf,
                medium_confidence=medium_conf,
                low_confidence=low_conf,
                rejected=rejected,
                status="completed",
                created_at=now,
                completed_at=now,
            )

        except Exception as e:
            logger.error(f"Transfer detection job failed: {e}")
            conn.execute(
                "UPDATE ai_bulk_job SET status = 'failed', error_message = ? WHERE id = ?",
                [str(e)[:500], job_id],
            )
            raise

    def _store_transfer_match(self, result: TransferAnalysisResult):
        """Store a detected transfer match."""
        from .db import get_conn
        conn = get_conn()

        # Check if already exists
        exists = conn.execute(
            "SELECT 1 FROM match_transfer WHERE left_tx_id = ? AND right_tx_id = ?",
            [result.left_id, result.right_id],
        ).fetchone()

        if exists:
            return

        gid = str(uuid.uuid4())
        method = f"ai-enhanced-{result.method}" if "ai" in result.method else result.method

        conn.execute(
            """
            INSERT INTO match_transfer (left_tx_id, right_tx_id, score, method, decided_at, group_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [result.left_id, result.right_id, result.confidence, method, None, gid],
        )

        # Log the AI analysis
        self._log_ai_analysis(result)

    def _log_ai_analysis(self, result: TransferAnalysisResult):
        """Log AI analysis for auditing."""
        from .db import get_conn
        conn = get_conn()

        payload = {
            "left_id": result.left_id,
            "right_id": result.right_id,
            "is_transfer": result.is_transfer,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "method": result.method,
            "provider": result.provider,
            "model": result.model,
            "latency_ms": result.latency_ms,
        }

        conn.execute(
            """
            INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(uuid.uuid4()),
                "transfer_detection",
                result.left_id,
                "ai_analysis",
                json.dumps(payload),
                datetime.now(UTC),
                "ai",
            ],
        )

    # -------------------------------------------------------------------------
    # Learning from User Feedback
    # -------------------------------------------------------------------------

    def record_feedback(
        self,
        left_id: str,
        right_id: str,
        was_correct: bool,
        user_action: str  # 'confirmed', 'rejected'
    ):
        """
        Record user feedback on transfer detection.

        Used to improve future detection accuracy.
        """
        from .db import get_conn
        conn = get_conn()

        left, right = _canonical_pair(left_id, right_id)

        # Get the original detection
        row = conn.execute(
            "SELECT score, method FROM match_transfer WHERE left_tx_id = ? AND right_tx_id = ?",
            [left, right],
        ).fetchone()

        if not row:
            return

        original_score, method = row

        # Log feedback
        payload = {
            "left_id": left,
            "right_id": right,
            "original_score": original_score,
            "method": method,
            "was_correct": was_correct,
            "user_action": user_action,
        }

        conn.execute(
            """
            INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(uuid.uuid4()),
                "transfer_feedback",
                left,
                "feedback",
                json.dumps(payload),
                datetime.now(UTC),
                "user",
            ],
        )

        # Update model knowledge (TODO: implement learning)
        if self.config.learn_from_confirmations:
            self._learn_from_feedback(left, right, was_correct, user_action)

    def _learn_from_feedback(
        self,
        left_id: str,
        right_id: str,
        was_correct: bool,
        user_action: str
    ):
        """
        Learn from user feedback to improve future detection.

        TODO: Implement pattern learning similar to category learning.
        """
        # Future: Store patterns that led to correct/incorrect matches
        # This could be used to adjust heuristic weights or train a local model
        pass

    # -------------------------------------------------------------------------
    # Status & Statistics
    # -------------------------------------------------------------------------

    def get_detection_stats(self) -> Dict[str, Any]:
        """Get transfer detection statistics."""
        from .db import get_conn
        conn = get_conn()

        # Total transfers detected
        total = conn.execute("SELECT COUNT(*) FROM match_transfer").fetchone()[0]

        # By status
        pending = conn.execute(
            "SELECT COUNT(*) FROM match_transfer WHERE decided_at IS NULL"
        ).fetchone()[0]
        confirmed = conn.execute(
            "SELECT COUNT(*) FROM match_transfer WHERE decided_at IS NOT NULL"
        ).fetchone()[0]

        # By method
        methods = conn.execute(
            """
            SELECT method, COUNT(*) as cnt
            FROM match_transfer
            GROUP BY method
            """
        ).fetchall()

        # By confidence tier
        high_conf = conn.execute(
            "SELECT COUNT(*) FROM match_transfer WHERE score >= 0.9"
        ).fetchone()[0]
        medium_conf = conn.execute(
            "SELECT COUNT(*) FROM match_transfer WHERE score >= 0.7 AND score < 0.9"
        ).fetchone()[0]
        low_conf = conn.execute(
            "SELECT COUNT(*) FROM match_transfer WHERE score < 0.7"
        ).fetchone()[0]

        # Latest job
        job = conn.execute(
            """
            SELECT id, status, total_transactions, processed_transactions,
                   enhanced_transactions, created_at, completed_at
            FROM ai_bulk_job
            WHERE job_type = 'transfer_detection'
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()

        return {
            "total_matches": total,
            "pending": pending,
            "confirmed": confirmed,
            "by_method": {m[0]: m[1] for m in methods},
            "by_confidence": {
                "high": high_conf,
                "medium": medium_conf,
                "low": low_conf,
            },
            "latest_job": {
                "job_id": job[0] if job else None,
                "status": job[1] if job else None,
                "total": job[2] if job else 0,
                "processed": job[3] if job else 0,
                "found": job[4] if job else 0,
            } if job else None,
        }


# =============================================================================
# Global Service Instance
# =============================================================================

_transfer_detection_service: Optional[AITransferDetectionService] = None


def get_transfer_detection_service() -> AITransferDetectionService:
    """Get or create the global transfer detection service."""
    global _transfer_detection_service
    if _transfer_detection_service is None:
        _transfer_detection_service = AITransferDetectionService()
    return _transfer_detection_service


def reset_transfer_detection_service():
    """Reset the global service (for testing)."""
    global _transfer_detection_service
    _transfer_detection_service = None
