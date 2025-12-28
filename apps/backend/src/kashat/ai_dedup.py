"""
AI-Enhanced Deduplication

Provides intelligent duplicate detection beyond simple fingerprinting:
- Semantic similarity analysis for descriptions
- Amount tolerance with intelligent thresholds
- Time-window based clustering
- Confidence scoring for duplicate suggestions
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, UTC

from .ai import get_ai_service
from .db import get_conn


@dataclass
class DuplicateCandidate:
    """A potential duplicate transaction pair"""
    transaction_id_1: str
    transaction_id_2: str
    similarity_score: float
    matching_factors: List[str]
    confidence: float
    recommendation: str  # 'merge', 'review', 'ignore'


@dataclass
class SimilarityAnalysis:
    """Analysis of similarity between two transactions"""
    description_similarity: float
    amount_similarity: float
    time_proximity: float
    merchant_similarity: float
    overall_score: float


class AIDeduplicator:
    """Enhanced deduplication using AI similarity analysis"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
    
    def find_potential_duplicates(
        self, 
        account_id: Optional[str] = None,
        days_window: int = 30,
        min_confidence: float = 0.7
    ) -> List[DuplicateCandidate]:
        """Find potential duplicate transactions using AI similarity"""
        conn = get_conn()
        # Load default thresholds from settings if not provided explicitly
        try:
            from .settings import load_settings
            s = load_settings()
            if days_window == 30:
                days_window = int(s.get("dedup_days_window", 30))
            if min_confidence == 0.7:
                min_confidence = float(s.get("dedup_min_confidence", 0.7))
        except Exception:
            pass
        
        # Get transactions for analysis
        where_clause = "WHERE t.created_at >= ?" 
        params = [datetime.now(UTC) - timedelta(days=days_window)]
        
        if account_id:
            where_clause += " AND t.account_id = ?"
            params.append(account_id)
        
        transactions = conn.execute(f"""
            SELECT t.id, t.description_norm, t.amount, t.posted_at, 
                   t.ai_merchant_name, t.fingerprint, t.account_id
            FROM [transaction] t
            {where_clause}
            ORDER BY t.posted_at DESC
        """, params).fetchall()
        
        duplicates = []
        
        # Compare each transaction with others in a reasonable time window
        for i, tx1 in enumerate(transactions):
            for tx2 in transactions[i+1:]:
                # Skip if same transaction or too far apart in time
                time_diff = abs((tx1[3] - tx2[3]).days) if tx1[3] and tx2[3] else 999
                if time_diff > 7:  # Only check within 7 days
                    continue
                
                # Skip if already flagged as duplicates by fingerprint
                if tx1[5] == tx2[5] and tx1[5]:  # Same fingerprint
                    continue
                
                # Analyze similarity
                similarity = self._analyze_transaction_similarity(tx1, tx2)
                
                if similarity.overall_score >= min_confidence:
                    candidate = self._create_duplicate_candidate(tx1, tx2, similarity)
                    duplicates.append(candidate)
        
        # Sort by confidence (highest first)
        duplicates.sort(key=lambda d: d.confidence, reverse=True)
        
        return duplicates[:50]  # Return top 50 candidates
    
    def _analyze_transaction_similarity(self, tx1: tuple, tx2: tuple) -> SimilarityAnalysis:
        """Analyze similarity between two transactions"""
        
        # Description similarity using AI normalization
        desc1 = tx1[1] or ""  # description_norm
        desc2 = tx2[1] or ""
        merchant1 = tx1[4] or desc1  # ai_merchant_name or fallback to description
        merchant2 = tx2[4] or desc2
        
        description_sim = self._calculate_text_similarity(desc1, desc2)
        merchant_sim = self._calculate_text_similarity(merchant1, merchant2)
        
        # Amount similarity
        amount1 = float(tx1[2]) if tx1[2] else 0.0
        amount2 = float(tx2[2]) if tx2[2] else 0.0
        amount_sim = self._calculate_amount_similarity(amount1, amount2)
        
        # Time proximity (closer in time = higher score)
        time1 = tx1[3]  # posted_at
        time2 = tx2[3]
        time_sim = self._calculate_time_proximity(time1, time2)
        
        # Overall score with weighted factors
        overall_score = (
            description_sim * 0.4 +
            merchant_sim * 0.3 +
            amount_sim * 0.2 +
            time_sim * 0.1
        )
        
        return SimilarityAnalysis(
            description_similarity=description_sim,
            amount_similarity=amount_sim,
            time_proximity=time_sim,
            merchant_similarity=merchant_sim,
            overall_score=overall_score
        )
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        if not text1 or not text2:
            return 0.0
        
        # Normalize for comparison
        text1 = self._normalize_for_comparison(text1)
        text2 = self._normalize_for_comparison(text2)
        
        if text1 == text2:
            return 1.0
        
        # Calculate Jaccard similarity using word sets
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Boost score if one string contains the other
        if text1 in text2 or text2 in text1:
            jaccard = max(jaccard, 0.8)
        
        return jaccard
    
    def _normalize_for_comparison(self, text: str) -> str:
        """Normalize text for similarity comparison"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove common noise words and patterns
        noise_patterns = [
            r'\b(transaction|payment|purchase|charge|debit)\b',
            r'\b(pos|online|mobile|app)\b',
            r'\b\d{4,}\b',  # Remove long numbers
            r'[#*\-]+'  # Remove special characters
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, ' ', text)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _calculate_amount_similarity(self, amount1: float, amount2: float) -> float:
        """Calculate similarity between two amounts"""
        if amount1 == 0.0 and amount2 == 0.0:
            return 1.0
        
        if amount1 == 0.0 or amount2 == 0.0:
            return 0.0
        
        # Exact match
        if amount1 == amount2:
            return 1.0
        
        # Calculate percentage difference
        diff = abs(amount1 - amount2)
        avg = (abs(amount1) + abs(amount2)) / 2
        
        if avg == 0:
            return 0.0
        
        percentage_diff = diff / avg
        
        # High similarity for small differences
        if percentage_diff < 0.01:  # Less than 1% difference
            return 0.95
        elif percentage_diff < 0.05:  # Less than 5% difference
            return 0.8
        elif percentage_diff < 0.1:  # Less than 10% difference
            return 0.6
        else:
            return max(0.0, 1.0 - percentage_diff)
    
    def _calculate_time_proximity(self, time1: datetime, time2: datetime) -> float:
        """Calculate time proximity score"""
        if not time1 or not time2:
            return 0.0
        
        diff_days = abs((time1 - time2).days)
        
        if diff_days == 0:
            return 1.0
        elif diff_days == 1:
            return 0.8
        elif diff_days <= 3:
            return 0.6
        elif diff_days <= 7:
            return 0.3
        else:
            return 0.0
    
    def _create_duplicate_candidate(
        self, 
        tx1: tuple, 
        tx2: tuple, 
        similarity: SimilarityAnalysis
    ) -> DuplicateCandidate:
        """Create a duplicate candidate from similarity analysis"""
        
        matching_factors = []
        
        if similarity.description_similarity > 0.8:
            matching_factors.append("High description similarity")
        if similarity.merchant_similarity > 0.8:
            matching_factors.append("Merchant match")
        if similarity.amount_similarity > 0.95:
            matching_factors.append("Exact amount match")
        elif similarity.amount_similarity > 0.8:
            matching_factors.append("Similar amount")
        if similarity.time_proximity > 0.8:
            matching_factors.append("Posted on same day")
        elif similarity.time_proximity > 0.3:
            matching_factors.append("Posted within few days")
        
        # Determine recommendation based on confidence
        if similarity.overall_score > 0.9:
            recommendation = "merge"
        elif similarity.overall_score > 0.7:
            recommendation = "review"
        else:
            recommendation = "ignore"
        
        return DuplicateCandidate(
            transaction_id_1=tx1[0],
            transaction_id_2=tx2[0],
            similarity_score=similarity.overall_score,
            matching_factors=matching_factors,
            confidence=similarity.overall_score,
            recommendation=recommendation
        )
    
    async def merge_duplicate_transactions(
        self, 
        keep_id: str, 
        remove_id: str, 
        user_confirmed: bool = False
    ) -> Dict[str, any]:
        """Merge two duplicate transactions"""
        conn = get_conn()
        
        # Get both transactions
        keep_tx = conn.execute("SELECT * FROM [transaction] WHERE id = ?", [keep_id]).fetchone()
        remove_tx = conn.execute("SELECT * FROM [transaction] WHERE id = ?", [remove_id]).fetchone()
        
        if not keep_tx or not remove_tx:
            raise ValueError("One or both transactions not found")
        
        # Verify they could be duplicates
        if not user_confirmed:
            similarity = self._analyze_transaction_similarity(keep_tx, remove_tx)
            # Use settings threshold for merge recommendation when not user confirmed
            try:
                from .settings import load_settings
                s = load_settings()
                threshold = float(s.get("dedup_min_confidence", 0.7))
            except Exception:
                threshold = 0.7
            if similarity.overall_score < threshold:
                raise ValueError("Transactions have low similarity score - merge not recommended")
        
        try:
            # Start transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Transfer any categorization from remove_tx to keep_tx if keep_tx isn't categorized
            keep_categories = conn.execute(
                "SELECT category_id FROM transaction_category WHERE tx_id = ?", [keep_id]
            ).fetchall()
            
            if not keep_categories:
                remove_categories = conn.execute(
                    "SELECT category_id, applied_by FROM transaction_category WHERE tx_id = ?", [remove_id]
                ).fetchall()
                
                for cat in remove_categories:
                    conn.execute(
                        "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
                        [keep_id, cat[0], cat[1] + "_from_merged"]
                    )
            
            # Log the merge operation
            import json
            import uuid
            from datetime import datetime
            
            conn.execute(
                "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    str(uuid.uuid4()),
                    "transaction",
                    keep_id,
                    "merge_duplicate",
                    json.dumps({
                        "merged_transaction_id": remove_id,
                        "user_confirmed": user_confirmed,
                        "merge_method": "ai_deduplication"
                    }),
                    datetime.now(UTC),
                    "ai_system"
                ]
            )
            
            # Delete the duplicate transaction and its relations
            conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [remove_id])
            conn.execute("DELETE FROM [transaction] WHERE id = ?", [remove_id])
            
            # Commit transaction
            conn.execute("COMMIT")
            
            return {
                "success": True,
                "kept_transaction_id": keep_id,
                "removed_transaction_id": remove_id,
                "message": "Transactions merged successfully"
            }
        
        except Exception as e:
            conn.execute("ROLLBACK")
            raise e


# Global instance
_ai_deduplicator = None

def get_ai_deduplicator() -> AIDeduplicator:
    """Get the global AI deduplicator instance"""
    global _ai_deduplicator
    if _ai_deduplicator is None:
        _ai_deduplicator = AIDeduplicator()
    return _ai_deduplicator
