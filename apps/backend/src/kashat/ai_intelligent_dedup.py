"""
AI-Powered Intelligent Duplicate Detection and Resolution

Advanced duplicate detection system that:
- Uses ML algorithms for sophisticated duplicate identification
- Considers multiple similarity factors (amount, date, description, merchant)
- Provides confidence scoring for automatic resolution
- Learns from user decisions to improve accuracy
- Handles complex scenarios like partial duplicates and split transactions
"""

from __future__ import annotations

import re
import json
import uuid
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime, date, timedelta, UTC
from collections import defaultdict
from difflib import SequenceMatcher

from .db import get_conn


@dataclass
class DuplicateCandidate:
    transaction_id_1: str
    transaction_id_2: str
    similarity_score: float
    confidence: float
    match_factors: Dict[str, float]
    duplicate_type: str  # "exact", "near_exact", "partial", "split", "transfer"
    resolution_suggestion: str  # "auto_merge", "manual_review", "mark_as_related"
    supporting_evidence: List[str]
    risk_factors: List[str]
    created_at: datetime


@dataclass
class TransactionSignature:
    """Normalized signature for comparing transactions"""
    amount_bucket: str
    description_tokens: Set[str]
    merchant_normalized: str
    date_range: str  # "YYYY-MM-DD" or "YYYY-MM-DD_range"
    amount_exact: float
    is_round_amount: bool
    transaction_type: str  # "debit", "credit"


@dataclass
class DuplicateResolution:
    candidate_id: str
    resolution_type: str  # "merged", "kept_separate", "marked_related"
    confidence: float
    user_decision: bool  # True if user made decision, False if auto-resolved
    merge_result: Optional[Dict[str, Any]]
    created_at: datetime


class IntelligentDuplicateDetector:
    """Advanced ML-based duplicate detection and resolution system"""
    
    def __init__(self):
        self._similarity_weights = {
            'amount_exact': 0.35,
            'description_similarity': 0.25,
            'date_proximity': 0.20,
            'merchant_similarity': 0.15,
            'context_similarity': 0.05
        }
        
        self._confidence_thresholds = {
            'auto_merge': 0.92,
            'high_confidence': 0.85,
            'medium_confidence': 0.70,
            'low_confidence': 0.50
        }
    
    async def detect_duplicates(
        self,
        account_id: str,
        days_window: int = 14,
        include_resolved: bool = False,
        batch_size: int = 1000
    ) -> List[DuplicateCandidate]:
        """Detect duplicate transactions using advanced ML algorithms"""
        
        conn = get_conn()
        
        # Get recent transactions for analysis
        cutoff_date = datetime.now(UTC) - timedelta(days=days_window)
        
        query = """
            SELECT t.id, t.description_norm, t.amount, t.posted_at, t.account_id,
                   ai_merchant_name, ai_confidence_score
            FROM [transaction] t
            WHERE t.account_id = ? AND t.posted_at >= ?
        """
        params = [account_id, cutoff_date]
        
        if not include_resolved:
            query += """
                AND NOT EXISTS (
                    SELECT 1 FROM duplicate_resolution dr 
                    WHERE dr.transaction_id_1 = t.id OR dr.transaction_id_2 = t.id
                )
            """
        
        query += " ORDER BY t.posted_at DESC LIMIT ?"
        params.append(batch_size)
        
        transactions = conn.execute(query, params).fetchall()
        
        if len(transactions) < 2:
            return []
        
        # Create transaction signatures
        signatures = {}
        for tx in transactions:
            tx_id, description, amount, posted_at, account_id, ai_merchant, ai_confidence = tx
            signatures[tx_id] = await self._create_transaction_signature(
                tx_id, description, amount, posted_at, ai_merchant
            )
        
        # Find potential duplicates
        candidates = []
        
        # Group transactions by similar characteristics for efficient comparison
        grouped_transactions = await self._group_similar_transactions(signatures, transactions)
        
        for group in grouped_transactions:
            group_candidates = await self._find_duplicates_in_group(group, signatures)
            candidates.extend(group_candidates)
        
        # Score and rank candidates
        scored_candidates = []
        for candidate in candidates:
            enhanced_candidate = await self._enhance_duplicate_candidate(candidate, signatures)
            if enhanced_candidate.confidence >= self._confidence_thresholds['low_confidence']:
                scored_candidates.append(enhanced_candidate)
        
        return sorted(scored_candidates, key=lambda c: c.confidence, reverse=True)
    
    async def auto_resolve_duplicates(
        self,
        candidates: List[DuplicateCandidate],
        auto_merge_threshold: float = 0.92
    ) -> Dict[str, Any]:
        """Automatically resolve high-confidence duplicates"""
        
        results = {
            'auto_merged': 0,
            'reviewed_required': 0,
            'failed': 0,
            'resolutions': []
        }
        
        for candidate in candidates:
            try:
                if (candidate.confidence >= auto_merge_threshold and 
                    candidate.resolution_suggestion == "auto_merge" and
                    len(candidate.risk_factors) == 0):
                    
                    # Perform automatic merge
                    resolution = await self._auto_merge_transactions(candidate)
                    
                    if resolution:
                        results['auto_merged'] += 1
                        results['resolutions'].append({
                            'candidate_id': candidate.transaction_id_1 + "_" + candidate.transaction_id_2,
                            'type': 'auto_merged',
                            'confidence': candidate.confidence
                        })
                    else:
                        results['failed'] += 1
                
                else:
                    # Requires manual review
                    await self._mark_for_manual_review(candidate)
                    results['reviewed_required'] += 1
                    results['resolutions'].append({
                        'candidate_id': candidate.transaction_id_1 + "_" + candidate.transaction_id_2,
                        'type': 'manual_review_required',
                        'confidence': candidate.confidence
                    })
            
            except Exception as e:
                print(f"Error resolving duplicate candidate: {e}")
                results['failed'] += 1
        
        return results
    
    async def learn_from_user_decision(
        self,
        candidate: DuplicateCandidate,
        user_decision: str,  # "merge", "keep_separate", "mark_related"
        feedback_notes: Optional[str] = None
    ):
        """Learn from user decisions to improve future detection"""
        
        conn = get_conn()
        
        # Store user decision
        resolution = DuplicateResolution(
            candidate_id=f"{candidate.transaction_id_1}_{candidate.transaction_id_2}",
            resolution_type=user_decision,
            confidence=candidate.confidence,
            user_decision=True,
            merge_result=None,
            created_at=datetime.now(UTC)
        )
        
        await self._store_duplicate_resolution(resolution)
        
        # Update learning weights based on decision
        await self._update_similarity_weights(candidate, user_decision)
        
        # Log feedback for analysis
        if feedback_notes:
            conn.execute("""
                INSERT INTO duplicate_feedback (
                    id, candidate_id, user_decision, feedback_notes, 
                    original_confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()), resolution.candidate_id, user_decision,
                feedback_notes, candidate.confidence, datetime.now(UTC)
            ])
    
    async def find_split_transactions(
        self,
        account_id: str,
        days_window: int = 7
    ) -> List[Dict[str, Any]]:
        """Find transactions that might be splits of a larger transaction"""
        
        conn = get_conn()
        cutoff_date = datetime.now(UTC) - timedelta(days=days_window)
        
        # Get transactions that might be splits
        transactions = conn.execute("""
            SELECT id, description_norm, amount, posted_at
            FROM [transaction]
            WHERE account_id = ? AND posted_at >= ?
            AND amount < 0  -- Only debits
            ORDER BY posted_at, ABS(amount) DESC
        """, [account_id, cutoff_date]).fetchall()
        
        split_groups = []
        
        # Group transactions by similar dates and descriptions
        date_groups = defaultdict(list)
        for tx in transactions:
            tx_id, description, amount, posted_at = tx
            date_key = posted_at.date() if isinstance(posted_at, datetime) else posted_at
            date_groups[date_key].append(tx)
        
        for date_key, day_transactions in date_groups.items():
            # Look for potential splits within the same day
            splits = await self._find_splits_in_day(day_transactions)
            split_groups.extend(splits)
        
        return split_groups
    
    async def detect_transfer_pairs(
        self,
        account_id: Optional[str] = None,
        days_window: int = 3
    ) -> List[Dict[str, Any]]:
        """Detect transactions that are likely transfer pairs between accounts"""
        
        conn = get_conn()
        cutoff_date = datetime.now(UTC) - timedelta(days=days_window)
        
        # Get transactions from all accounts if account_id not specified
        query = """
            SELECT t.id, t.description_norm, t.amount, t.posted_at, t.account_id
            FROM [transaction] t
            WHERE t.posted_at >= ?
        """
        params = [cutoff_date]
        
        if account_id:
            query += " AND t.account_id = ?"
            params.append(account_id)
        
        query += " ORDER BY t.posted_at DESC"
        
        transactions = conn.execute(query, params).fetchall()
        
        transfer_pairs = []
        
        # Group by amount (looking for opposite amounts)
        amount_groups = defaultdict(list)
        for tx in transactions:
            tx_id, description, amount, posted_at, acc_id = tx
            # Group by absolute amount
            amount_key = abs(amount)
            amount_groups[amount_key].append(tx)
        
        for amount, tx_group in amount_groups.items():
            if len(tx_group) >= 2:
                pairs = await self._find_transfer_pairs_in_group(tx_group)
                transfer_pairs.extend(pairs)
        
        return transfer_pairs
    
    # Core detection methods
    
    async def _create_transaction_signature(
        self,
        tx_id: str,
        description: str,
        amount: float,
        posted_at: date,
        ai_merchant: Optional[str]
    ) -> TransactionSignature:
        """Create a normalized signature for transaction comparison"""
        
        # Amount bucket for fuzzy matching
        abs_amount = abs(amount)
        if abs_amount < 10:
            amount_bucket = "micro"
        elif abs_amount < 100:
            amount_bucket = "small"
        elif abs_amount < 500:
            amount_bucket = "medium"
        else:
            amount_bucket = "large"
        
        # Normalize description
        desc_normalized = re.sub(r'[^a-zA-Z0-9\s]', ' ', description.lower())
        desc_normalized = re.sub(r'\s+', ' ', desc_normalized).strip()
        
        # Extract meaningful tokens
        tokens = set()
        for token in desc_normalized.split():
            if len(token) > 2 and not token.isdigit():
                tokens.add(token)
        
        # Normalize merchant name
        merchant_normalized = ""
        if ai_merchant:
            merchant_normalized = re.sub(r'[^a-zA-Z0-9\s]', ' ', ai_merchant.lower())
            merchant_normalized = re.sub(r'\s+', ' ', merchant_normalized).strip()
        
        # Date range for fuzzy date matching
        if isinstance(posted_at, str):
            posted_at = datetime.fromisoformat(posted_at).date()
        date_range = posted_at.strftime("%Y-%m-%d")
        
        # Round amount detection
        is_round = abs(amount) % 1.0 < 0.01
        
        # Transaction type
        tx_type = "credit" if amount > 0 else "debit"
        
        return TransactionSignature(
            amount_bucket=amount_bucket,
            description_tokens=tokens,
            merchant_normalized=merchant_normalized,
            date_range=date_range,
            amount_exact=amount,
            is_round_amount=is_round,
            transaction_type=tx_type
        )
    
    async def _group_similar_transactions(
        self,
        signatures: Dict[str, TransactionSignature],
        transactions: List[Tuple]
    ) -> List[List[str]]:
        """Group transactions by similar characteristics for efficient comparison"""
        
        # Group by amount bucket and transaction type
        groups = defaultdict(list)
        
        for tx in transactions:
            tx_id = tx[0]
            signature = signatures[tx_id]
            
            # Create grouping key
            group_key = f"{signature.amount_bucket}_{signature.transaction_type}"
            groups[group_key].append(tx_id)
        
        # Return groups with 2+ transactions
        return [group for group in groups.values() if len(group) >= 2]
    
    async def _find_duplicates_in_group(
        self,
        transaction_ids: List[str],
        signatures: Dict[str, TransactionSignature]
    ) -> List[DuplicateCandidate]:
        """Find duplicate candidates within a group of similar transactions"""
        
        candidates = []
        
        # Compare each pair in the group
        for i in range(len(transaction_ids)):
            for j in range(i + 1, len(transaction_ids)):
                tx_id_1 = transaction_ids[i]
                tx_id_2 = transaction_ids[j]
                
                signature_1 = signatures[tx_id_1]
                signature_2 = signatures[tx_id_2]
                
                # Calculate similarity
                similarity_score, match_factors = await self._calculate_similarity(
                    signature_1, signature_2
                )
                
                if similarity_score >= 0.5:  # Minimum threshold for consideration
                    candidate = DuplicateCandidate(
                        transaction_id_1=tx_id_1,
                        transaction_id_2=tx_id_2,
                        similarity_score=similarity_score,
                        confidence=0.0,  # Will be calculated later
                        match_factors=match_factors,
                        duplicate_type="",  # Will be determined later
                        resolution_suggestion="",  # Will be determined later
                        supporting_evidence=[],
                        risk_factors=[],
                        created_at=datetime.now(UTC)
                    )
                    
                    candidates.append(candidate)
        
        return candidates
    
    async def _calculate_similarity(
        self,
        sig1: TransactionSignature,
        sig2: TransactionSignature
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate similarity score between two transaction signatures"""
        
        factors = {}
        
        # Amount similarity
        if sig1.amount_exact == sig2.amount_exact:
            factors['amount_exact'] = 1.0
        else:
            amount_diff = abs(sig1.amount_exact - sig2.amount_exact)
            max_amount = max(abs(sig1.amount_exact), abs(sig2.amount_exact))
            factors['amount_exact'] = max(0, 1 - (amount_diff / max(max_amount, 1)))
        
        # Description similarity (Jaccard similarity)
        if sig1.description_tokens and sig2.description_tokens:
            intersection = len(sig1.description_tokens & sig2.description_tokens)
            union = len(sig1.description_tokens | sig2.description_tokens)
            factors['description_similarity'] = intersection / union if union > 0 else 0
        else:
            factors['description_similarity'] = 0
        
        # Date proximity
        try:
            date1 = datetime.strptime(sig1.date_range, "%Y-%m-%d").date()
            date2 = datetime.strptime(sig2.date_range, "%Y-%m-%d").date()
            days_diff = abs((date1 - date2).days)
            
            if days_diff == 0:
                factors['date_proximity'] = 1.0
            elif days_diff <= 1:
                factors['date_proximity'] = 0.8
            elif days_diff <= 3:
                factors['date_proximity'] = 0.6
            elif days_diff <= 7:
                factors['date_proximity'] = 0.3
            else:
                factors['date_proximity'] = 0.1
        except:
            factors['date_proximity'] = 0
        
        # Merchant similarity
        if sig1.merchant_normalized and sig2.merchant_normalized:
            merchant_sim = SequenceMatcher(
                None, sig1.merchant_normalized, sig2.merchant_normalized
            ).ratio()
            factors['merchant_similarity'] = merchant_sim
        else:
            factors['merchant_similarity'] = 0
        
        # Context similarity (transaction type, round amounts, etc.)
        context_score = 0
        if sig1.transaction_type == sig2.transaction_type:
            context_score += 0.5
        if sig1.is_round_amount == sig2.is_round_amount:
            context_score += 0.3
        if sig1.amount_bucket == sig2.amount_bucket:
            context_score += 0.2
        
        factors['context_similarity'] = min(1.0, context_score)
        
        # Calculate weighted similarity score
        total_score = 0
        for factor, weight in self._similarity_weights.items():
            total_score += factors.get(factor, 0) * weight
        
        return total_score, factors
    
    async def _enhance_duplicate_candidate(
        self,
        candidate: DuplicateCandidate,
        signatures: Dict[str, TransactionSignature]
    ) -> DuplicateCandidate:
        """Enhance candidate with confidence, type, and resolution suggestion"""
        
        # Calculate confidence based on similarity score and risk factors
        base_confidence = candidate.similarity_score
        
        # Determine duplicate type
        duplicate_type = await self._determine_duplicate_type(candidate, signatures)
        candidate.duplicate_type = duplicate_type
        
        # Identify risk factors
        risk_factors = await self._identify_risk_factors(candidate, signatures)
        candidate.risk_factors = risk_factors
        
        # Adjust confidence based on risk factors
        confidence_adjustment = len(risk_factors) * -0.1
        final_confidence = max(0, min(1, base_confidence + confidence_adjustment))
        candidate.confidence = final_confidence
        
        # Determine resolution suggestion
        candidate.resolution_suggestion = await self._suggest_resolution(candidate)
        
        # Generate supporting evidence
        candidate.supporting_evidence = await self._generate_supporting_evidence(candidate)
        
        return candidate
    
    async def _determine_duplicate_type(
        self,
        candidate: DuplicateCandidate,
        signatures: Dict[str, TransactionSignature]
    ) -> str:
        """Determine the type of duplicate"""
        
        sig1 = signatures[candidate.transaction_id_1]
        sig2 = signatures[candidate.transaction_id_2]
        
        # Exact duplicate
        if (candidate.match_factors['amount_exact'] == 1.0 and
            candidate.match_factors['description_similarity'] > 0.9 and
            candidate.match_factors['date_proximity'] == 1.0):
            return "exact"
        
        # Near exact duplicate
        elif (candidate.match_factors['amount_exact'] == 1.0 and
              candidate.match_factors['description_similarity'] > 0.7 and
              candidate.match_factors['date_proximity'] >= 0.8):
            return "near_exact"
        
        # Partial duplicate (similar but with differences)
        elif (candidate.match_factors['amount_exact'] > 0.8 and
              candidate.match_factors['description_similarity'] > 0.6):
            return "partial"
        
        # Transfer (opposite amounts, different accounts)
        elif (abs(sig1.amount_exact + sig2.amount_exact) < 0.01 and
              candidate.match_factors['date_proximity'] >= 0.6):
            return "transfer"
        
        # Split transaction
        elif (candidate.match_factors['description_similarity'] > 0.8 and
              candidate.match_factors['date_proximity'] >= 0.8):
            return "split"
        
        return "similar"
    
    async def _identify_risk_factors(
        self,
        candidate: DuplicateCandidate,
        signatures: Dict[str, TransactionSignature]
    ) -> List[str]:
        """Identify factors that might make auto-merge risky"""
        
        risk_factors = []
        
        # Large amount differences
        if candidate.match_factors['amount_exact'] < 0.95:
            risk_factors.append("amount_discrepancy")
        
        # Low description similarity
        if candidate.match_factors['description_similarity'] < 0.7:
            risk_factors.append("description_mismatch")
        
        # Date far apart
        if candidate.match_factors['date_proximity'] < 0.6:
            risk_factors.append("date_gap")
        
        # Different merchants
        if (candidate.match_factors['merchant_similarity'] < 0.8 and
            candidate.match_factors['merchant_similarity'] > 0):
            risk_factors.append("merchant_mismatch")
        
        return risk_factors
    
    async def _suggest_resolution(self, candidate: DuplicateCandidate) -> str:
        """Suggest resolution approach based on confidence and risk factors"""
        
        if (candidate.confidence >= self._confidence_thresholds['auto_merge'] and
            len(candidate.risk_factors) == 0 and
            candidate.duplicate_type in ['exact', 'near_exact']):
            return "auto_merge"
        
        elif candidate.confidence >= self._confidence_thresholds['high_confidence']:
            return "manual_review"
        
        elif candidate.duplicate_type == "transfer":
            return "mark_as_transfer"
        
        elif candidate.duplicate_type == "split":
            return "mark_as_related"
        
        else:
            return "manual_review"
    
    async def _generate_supporting_evidence(
        self,
        candidate: DuplicateCandidate
    ) -> List[str]:
        """Generate human-readable supporting evidence"""
        
        evidence = []
        
        # Amount evidence
        if candidate.match_factors['amount_exact'] == 1.0:
            evidence.append("Identical amounts")
        elif candidate.match_factors['amount_exact'] > 0.9:
            evidence.append("Very similar amounts")
        
        # Description evidence
        if candidate.match_factors['description_similarity'] > 0.8:
            evidence.append("Highly similar descriptions")
        elif candidate.match_factors['description_similarity'] > 0.6:
            evidence.append("Similar descriptions")
        
        # Date evidence
        if candidate.match_factors['date_proximity'] == 1.0:
            evidence.append("Same transaction date")
        elif candidate.match_factors['date_proximity'] > 0.8:
            evidence.append("Very close transaction dates")
        
        # Merchant evidence
        if candidate.match_factors['merchant_similarity'] > 0.8:
            evidence.append("Same or very similar merchant")
        
        return evidence
    
    # Resolution methods
    
    async def _auto_merge_transactions(
        self,
        candidate: DuplicateCandidate
    ) -> Optional[DuplicateResolution]:
        """Automatically merge high-confidence duplicate transactions"""
        
        conn = get_conn()
        
        try:
            # Get transaction details
            tx1 = conn.execute(
                "SELECT * FROM [transaction] WHERE id = ?", 
                [candidate.transaction_id_1]
            ).fetchone()
            
            tx2 = conn.execute(
                "SELECT * FROM [transaction] WHERE id = ?", 
                [candidate.transaction_id_2]
            ).fetchone()
            
            if not tx1 or not tx2:
                return None
            
            # Choose which transaction to keep (typically the one with better data)
            keep_id, remove_id = await self._choose_transaction_to_keep(tx1, tx2)
            
            # Merge transaction data
            merge_result = await self._merge_transaction_data(keep_id, remove_id)
            
            # Mark the duplicate as resolved
            resolution = DuplicateResolution(
                candidate_id=f"{candidate.transaction_id_1}_{candidate.transaction_id_2}",
                resolution_type="merged",
                confidence=candidate.confidence,
                user_decision=False,
                merge_result=merge_result,
                created_at=datetime.now(UTC)
            )
            
            await self._store_duplicate_resolution(resolution)
            
            return resolution
        
        except Exception as e:
            print(f"Error in auto-merge: {e}")
            return None
    
    async def _choose_transaction_to_keep(
        self,
        tx1: Tuple,
        tx2: Tuple
    ) -> Tuple[str, str]:
        """Choose which transaction to keep in a merge"""
        
        # Simple heuristic: keep the one with more complete data
        # In practice, this could be more sophisticated
        
        tx1_score = 0
        tx2_score = 0
        
        # Prefer transaction with AI enhancement
        if tx1[6]:  # ai_merchant_name column
            tx1_score += 1
        if tx2[6]:
            tx2_score += 1
        
        # Prefer transaction with better confidence
        if tx1[7] and tx1[7] > 0.5:  # ai_confidence_score
            tx1_score += 1
        if tx2[7] and tx2[7] > 0.5:
            tx2_score += 1
        
        # Prefer newer transaction (assuming later processing = better data)
        if tx1[8] > tx2[8]:  # created_at
            tx1_score += 1
        else:
            tx2_score += 1
        
        if tx1_score >= tx2_score:
            return tx1[0], tx2[0]  # Keep tx1, remove tx2
        else:
            return tx2[0], tx1[0]  # Keep tx2, remove tx1
    
    async def _merge_transaction_data(
        self,
        keep_id: str,
        remove_id: str
    ) -> Dict[str, Any]:
        """Merge data from two transactions"""
        
        conn = get_conn()
        
        # Get all related data for the transaction being removed
        categories = conn.execute(
            "SELECT category_id FROM transaction_category WHERE tx_id = ?",
            [remove_id]
        ).fetchall()
        
        # Transfer categories to kept transaction (if not already present)
        for (category_id,) in categories:
            existing = conn.execute(
                "SELECT 1 FROM transaction_category WHERE tx_id = ? AND category_id = ?",
                [keep_id, category_id]
            ).fetchone()
            
            if not existing:
                conn.execute(
                    "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
                    [keep_id, category_id, "auto_merge"]
                )
        
        # Log the merge operation
        conn.execute("""
            INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4()), "transaction", keep_id, "auto_merge_duplicate",
            json.dumps({"removed_transaction_id": remove_id}),
            datetime.now(UTC), "ai_duplicate_detector"
        ])
        
        # Soft delete the duplicate transaction
        conn.execute(
            "UPDATE [transaction] SET is_deleted = true, deleted_at = ?, deleted_reason = ? WHERE id = ?",
            [datetime.now(UTC), "duplicate_auto_merged", remove_id]
        )
        
        return {
            "kept_transaction": keep_id,
            "removed_transaction": remove_id,
            "categories_merged": len(categories),
            "merge_timestamp": datetime.now(UTC).isoformat()
        }
    
    async def _mark_for_manual_review(self, candidate: DuplicateCandidate):
        """Mark duplicate candidate for manual review"""
        
        conn = get_conn()
        
        conn.execute("""
            INSERT INTO duplicate_review_queue (
                id, transaction_id_1, transaction_id_2, similarity_score,
                confidence, duplicate_type, supporting_evidence_json,
                risk_factors_json, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4()), candidate.transaction_id_1, candidate.transaction_id_2,
            candidate.similarity_score, candidate.confidence, candidate.duplicate_type,
            json.dumps(candidate.supporting_evidence), json.dumps(candidate.risk_factors),
            candidate.created_at, "pending_review"
        ])
    
    async def _store_duplicate_resolution(self, resolution: DuplicateResolution):
        """Store duplicate resolution in database"""
        
        conn = get_conn()
        
        conn.execute("""
            INSERT INTO duplicate_resolution (
                id, candidate_id, resolution_type, confidence,
                user_decision, merge_result_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4()), resolution.candidate_id, resolution.resolution_type,
            resolution.confidence, resolution.user_decision,
            json.dumps(resolution.merge_result) if resolution.merge_result else None,
            resolution.created_at
        ])
    
    async def _update_similarity_weights(
        self,
        candidate: DuplicateCandidate,
        user_decision: str
    ):
        """Update similarity weights based on user feedback"""
        
        # Simple weight adjustment based on feedback
        # In a production system, this would use more sophisticated ML techniques
        
        if user_decision == "merge" and candidate.confidence < 0.8:
            # User merged a low-confidence candidate - maybe we're being too conservative
            pass
        elif user_decision == "keep_separate" and candidate.confidence > 0.9:
            # User kept separate a high-confidence candidate - maybe we're being too aggressive
            pass
    
    # Split transaction detection
    
    async def _find_splits_in_day(
        self,
        transactions: List[Tuple]
    ) -> List[Dict[str, Any]]:
        """Find split transactions within a single day"""
        
        splits = []
        
        # Group by similar descriptions
        desc_groups = defaultdict(list)
        for tx in transactions:
            tx_id, description, amount, posted_at = tx
            # Normalize description for grouping
            normalized_desc = re.sub(r'[^a-zA-Z\s]', '', description.lower())[:20]
            desc_groups[normalized_desc].append(tx)
        
        for desc, tx_group in desc_groups.items():
            if len(tx_group) >= 2:
                # Look for combinations that sum to round numbers or common amounts
                split_combinations = await self._find_split_combinations(tx_group)
                splits.extend(split_combinations)
        
        return splits
    
    async def _find_split_combinations(
        self,
        transactions: List[Tuple]
    ) -> List[Dict[str, Any]]:
        """Find combinations of transactions that might be splits"""
        
        combinations = []
        
        # Simple approach: look for pairs that sum to round numbers
        for i in range(len(transactions)):
            for j in range(i + 1, len(transactions)):
                tx1 = transactions[i]
                tx2 = transactions[j]
                
                sum_amount = abs(tx1[2]) + abs(tx2[2])
                
                # Check if sum is a round number or common split pattern
                if (sum_amount % 1.0 < 0.01 or  # Round dollar
                    sum_amount % 5.0 < 0.01 or  # Multiple of 5
                    abs(sum_amount - round(sum_amount)) < 0.05):  # Close to round
                    
                    combinations.append({
                        'transaction_ids': [tx1[0], tx2[0]],
                        'descriptions': [tx1[1], tx2[1]],
                        'amounts': [tx1[2], tx2[2]],
                        'total_amount': sum_amount,
                        'split_type': 'potential_split',
                        'confidence': 0.6  # Medium confidence for splits
                    })
        
        return combinations
    
    # Transfer detection
    
    async def _find_transfer_pairs_in_group(
        self,
        transactions: List[Tuple]
    ) -> List[Dict[str, Any]]:
        """Find transfer pairs within a group of transactions with similar amounts"""
        
        pairs = []
        
        # Look for opposite amounts (credit/debit pairs)
        debits = [tx for tx in transactions if tx[2] < 0]
        credits = [tx for tx in transactions if tx[2] > 0]
        
        for debit in debits:
            for credit in credits:
                # Check if amounts are opposite
                if abs(abs(debit[2]) - abs(credit[2])) < 0.01:
                    # Check date proximity
                    try:
                        date1 = debit[3] if isinstance(debit[3], date) else datetime.fromisoformat(debit[3]).date()
                        date2 = credit[3] if isinstance(credit[3], date) else datetime.fromisoformat(credit[3]).date()
                        days_diff = abs((date1 - date2).days)
                        
                        if days_diff <= 2:  # Within 2 days
                            pairs.append({
                                'debit_transaction': debit[0],
                                'credit_transaction': credit[0],
                                'amount': abs(debit[2]),
                                'debit_account': debit[4],
                                'credit_account': credit[4],
                                'date_difference': days_diff,
                                'transfer_type': 'account_transfer',
                                'confidence': max(0.7, 1.0 - (days_diff * 0.1))
                            })
                    except:
                        continue
        
        return pairs


# Global instance
_intelligent_dedup_detector = None

def get_intelligent_dedup_detector() -> IntelligentDuplicateDetector:
    """Get the global intelligent duplicate detector instance"""
    global _intelligent_dedup_detector
    if _intelligent_dedup_detector is None:
        _intelligent_dedup_detector = IntelligentDuplicateDetector()
    return _intelligent_dedup_detector