"""
AI-Powered Smart Transaction Categorization

Advanced ML-based categorization system that:
- Learns from user behavior and patterns
- Uses semantic similarity for intelligent matching
- Provides confidence-based auto-categorization
- Continuously improves through feedback loops
- Handles edge cases and ambiguous transactions
- AUTOMATIC CATEGORY CREATION - Solves AI suggestion gaps
- Smart parent hierarchy management
- Pending category approval workflow
"""

from __future__ import annotations

import re
import json
import math
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, UTC
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import logging

from .db import get_conn

logger = logging.getLogger(__name__)


@dataclass
class CategoryPrediction:
    category_id: str
    category_name: str
    confidence: float
    reasoning: str
    match_type: str  # "exact", "pattern", "semantic", "historical", "ml"
    supporting_evidence: List[str]


@dataclass
class CategorizationFeatures:
    """Features extracted from a transaction for ML categorization"""
    description_tokens: List[str]
    amount_bucket: str  # "micro", "small", "medium", "large", "huge"
    amount_value: float
    is_round_amount: bool
    day_of_week: int
    hour_of_day: Optional[int]
    merchant_indicators: List[str]
    amount_patterns: List[str]
    description_length: int
    has_numbers: bool
    has_special_chars: bool
    frequency_in_account: int


@dataclass
class LearningFeedback:
    """Feedback for improving categorization accuracy"""
    transaction_id: str
    predicted_category: str
    actual_category: str
    prediction_confidence: float
    was_correct: bool
    user_correction_time: Optional[datetime]
    feedback_type: str  # "immediate", "delayed", "batch_correction"


@dataclass
class CategoryGapAnalysis:
    """Analysis of gaps between AI suggestions and available categories"""
    total_ai_suggestions: int
    available_categories: int
    missing_categories: List[str]
    success_rate: float
    suggested_actions: List[str]


@dataclass
class CategoryCreationResult:
    """Result of category creation process"""
    category_id: Optional[str]
    category_name: str
    parent_id: Optional[str]
    created: bool
    reason: str
    confidence: float


class SmartCategorizationEngine:
    """Advanced ML-based transaction categorization engine with automatic category creation"""
    
    def __init__(self):
        try:
            from .ai_analytics import get_ai_analytics_engine
            self.analytics_engine = get_ai_analytics_engine()
        except ImportError:
            self.analytics_engine = None
            logger.warning("AI analytics engine not available")
        
        self._category_cache = {}
        self._merchant_patterns = {}
        self._amount_patterns = {}
        
        # Category management settings
        self.auto_create_threshold = 0.8  # Minimum confidence for auto-creation
        self.parent_hierarchy = self._load_parent_hierarchy()
        self.category_synonyms = self._load_category_synonyms()
        
        # Initialize missing categories tracking
        self._ensure_category_management_tables()
        
        # Initialize merchant memory system
        self._ensure_merchant_mapping_table()
    
    # ========================================
    # CATEGORY MANAGEMENT & AUTO-CREATION
    # ========================================
    
    def _load_parent_hierarchy(self) -> Dict[str, str]:
        """Define the parent category hierarchy for AI suggestions"""
        return {
            # Food & Dining
            'food': 'Food & Dining',
            'food & dining': 'Food & Dining', 
            'food & beverage': 'Food & Dining',
            'beverage': 'Food & Dining',
            'groceries': 'Food & Dining',
            'grocery': 'Food & Dining',
            'restaurant': 'Food & Dining',
            
            # Shopping & Retail
            'shopping': 'Shopping',
            'retail': 'Shopping',
            'purchase': 'Shopping',
            'electronics': 'Shopping',
            
            # Transportation
            'transportation': 'Transportation',
            'gas & convenience': 'Transportation',
            'automotive': 'Transportation',
            
            # Utilities & Bills
            'utilities': 'Bills & Utilities',
            'insurance': 'Bills & Utilities',
            'mortgage payment': 'Bills & Utilities',
            
            # Technology & Services
            'technology': 'Technology',
            'software': 'Technology',
            'internet services': 'Technology',
            'online services': 'Technology',
            'subscription': 'Technology',
            
            # Entertainment
            'entertainment': 'Entertainment',
            'gaming': 'Entertainment',
            'online_gaming': 'Entertainment',
            
            # Health
            'healthcare': 'Healthcare',
            
            # Finance & Transfers
            'income': 'Income',
            'transfer': 'Transfers',
            'internal transfer': 'Transfers',
            'external transfer': 'Transfers', 
            'personal transfer': 'Transfers',
            'zelle': 'Transfers',
            'banking': 'Financial Services',
            'payments': 'Financial Services',
            
            # Professional Services
            'services': 'Professional Services',
            'advertising': 'Professional Services',
            
            # Other
            'uncategorized': 'Other',
        }
    
    def _load_category_synonyms(self) -> Dict[str, str]:
        """Map AI suggestion synonyms to canonical category names"""
        return {
            'food & beverage': 'Food & Dining',
            'food & dining': 'Food & Dining',
            'groceries': 'Grocery',
            'grocery': 'Grocery',
            'gas & convenience': 'Gas & Automotive',
            'online_gaming': 'Gaming',
            'internet services': 'Online Services',
            'personal transfer': 'Internal Transfer',
            'external transfer': 'External Transfer',
        }
    
    def _ensure_category_management_tables(self):
        """Ensure tables for category management exist"""
        conn = get_conn()
        
        try:
            # Pending category suggestions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_category_suggestions (
                    id TEXT PRIMARY KEY,
                    category_name TEXT NOT NULL,
                    confidence FLOAT NOT NULL,
                    suggestion_count INTEGER DEFAULT 1,
                    first_suggested_at TIMESTAMP NOT NULL,
                    last_suggested_at TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    recommended_parent TEXT,
                    created_by TEXT DEFAULT 'ai_system'
                )
            """)
            
            # Auto-categorization log table  
            conn.execute("""
                CREATE TABLE IF NOT EXISTS auto_categorization_log (
                    id TEXT PRIMARY KEY,
                    transaction_id TEXT NOT NULL,
                    category_id TEXT NOT NULL,
                    confidence FLOAT NOT NULL,
                    reasoning TEXT,
                    match_type TEXT,
                    evidence_json TEXT,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            
            # Categorization feedback table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categorization_feedback (
                    id TEXT PRIMARY KEY,
                    transaction_id TEXT NOT NULL,
                    predicted_category TEXT NOT NULL,
                    actual_category TEXT NOT NULL,
                    prediction_confidence FLOAT NOT NULL,
                    was_correct BOOLEAN NOT NULL,
                    user_correction_time TIMESTAMP,
                    feedback_type TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            
        except Exception as e:
            logger.warning(f"Could not create category management tables: {e}")
    
    def analyze_category_gaps(self, limit: int = 1000) -> CategoryGapAnalysis:
        """Analyze gaps between AI suggestions and available categories"""
        conn = get_conn()
        
        # Get all existing categories
        existing_categories = conn.execute("SELECT LOWER(name) FROM category").fetchall()
        existing_set = {cat[0] for cat in existing_categories}
        
        # Get all AI suggestions from transactions
        ai_suggestions = set()
        missing_categories = set()
        
        transactions = conn.execute(f"""
            SELECT ai_category_suggestions 
            FROM [transaction] 
            WHERE ai_category_suggestions IS NOT NULL 
            LIMIT {limit}
        """).fetchall()
        
        for tx in transactions:
            try:
                suggestions = json.loads(tx[0])
                for suggestion in suggestions:
                    cat_name = suggestion.get('category_name', '').lower().strip()
                    if cat_name:
                        ai_suggestions.add(cat_name)
                        if cat_name not in existing_set:
                            missing_categories.add(cat_name)
            except (json.JSONDecodeError, KeyError):
                continue
        
        total_suggestions = len(ai_suggestions)
        available_count = total_suggestions - len(missing_categories)
        success_rate = (available_count / max(total_suggestions, 1)) * 100
        
        # Generate suggested actions
        suggested_actions = []
        if success_rate < 50:
            suggested_actions.append("Critical: Bootstrap standard categories immediately")
        if len(missing_categories) > 20:
            suggested_actions.append("Consider bulk category creation")
        if success_rate < 80:
            suggested_actions.append("Enable automatic category creation")
        
        return CategoryGapAnalysis(
            total_ai_suggestions=total_suggestions,
            available_categories=available_count,
            missing_categories=sorted(list(missing_categories)),
            success_rate=success_rate,
            suggested_actions=suggested_actions
        )
    
    def find_or_create_category(self, ai_category_name: str, confidence: float = 0.8, 
                               auto_create: bool = True) -> CategoryCreationResult:
        """Find existing category or create new one if needed - SOLVES THE CORE ISSUE"""
        
        # Step 1: Try exact match (case-insensitive)
        existing_id = self._find_exact_category(ai_category_name)
        if existing_id:
            return CategoryCreationResult(
                category_id=existing_id,
                category_name=ai_category_name,
                parent_id=None,
                created=False,
                reason="Found exact match",
                confidence=confidence
            )
        
        # Step 2: Try synonym mapping
        canonical_name = self.category_synonyms.get(ai_category_name.lower())
        if canonical_name:
            existing_id = self._find_exact_category(canonical_name)
            if existing_id:
                return CategoryCreationResult(
                    category_id=existing_id,
                    category_name=canonical_name,
                    parent_id=None,
                    created=False,
                    reason="Found via synonym mapping",
                    confidence=confidence
                )
            ai_category_name = canonical_name  # Use canonical name for creation
        
        # Step 3: Try fuzzy matching to avoid near-duplicates
        similar_id, similar_name = self._find_similar_category(ai_category_name)
        if similar_id:
            return CategoryCreationResult(
                category_id=similar_id,
                category_name=similar_name,
                parent_id=None,
                created=False,
                reason="Found similar existing category",
                confidence=confidence * 0.9
            )
        
        # Step 4: Auto-create if confidence is high enough
        if auto_create and confidence >= self.auto_create_threshold:
            category_id = self._create_category(ai_category_name, confidence)
            if category_id:
                return CategoryCreationResult(
                    category_id=category_id,
                    category_name=ai_category_name,
                    parent_id=self._find_parent_category_id(ai_category_name),
                    created=True,
                    reason=f"Auto-created (confidence: {confidence:.2f})",
                    confidence=confidence
                )
        
        # Step 5: Store as pending suggestion for manual review
        self._store_pending_suggestion(ai_category_name, confidence)
        return CategoryCreationResult(
            category_id=None,
            category_name=ai_category_name,
            parent_id=None,
            created=False,
            reason="Stored as pending suggestion for review",
            confidence=confidence
        )
    
    def _find_exact_category(self, category_name: str) -> Optional[str]:
        """Find exact category match using normalized form (case-insensitive, trimmed)"""
        conn = get_conn()
        try:
            result = conn.execute(
                "SELECT id FROM category WHERE normalized_name = lower(trim(?))",
                [category_name]
            ).fetchone()
        except Exception:
            # Fallback for older schemas without normalized_name
            result = conn.execute(
                "SELECT id FROM category WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))",
                [category_name]
            ).fetchone()
        return result[0] if result else None
    
    def _find_similar_category(self, category_name: str, threshold: float = 0.85) -> Tuple[Optional[str], Optional[str]]:
        """Find similar category to avoid near-duplicates"""
        conn = get_conn()
        categories = conn.execute("SELECT id, name FROM category").fetchall()
        
        best_match = None
        best_name = None
        best_score = 0
        
        for cat_id, cat_name in categories:
            # Check name similarity
            similarity = SequenceMatcher(None, 
                category_name.lower(), 
                cat_name.lower()
            ).ratio()
            
            if similarity > threshold and similarity > best_score:
                best_score = similarity
                best_match = cat_id
                best_name = cat_name
        
        return best_match, best_name
    
    def _create_category(self, category_name: str, confidence: float) -> Optional[str]:
        """Create a new category with proper parent hierarchy (idempotent)."""
        conn = get_conn()
        
        try:
            # Find appropriate parent
            parent_id = self._find_parent_category_id(category_name)
            
            # Idempotent creation: check again via normalized name, then insert
            norm = category_name.strip().lower()
            existing = None
            try:
                existing = conn.execute(
                    "SELECT id FROM category WHERE normalized_name = ?",
                    [norm]
                ).fetchone()
            except Exception:
                existing = conn.execute(
                    "SELECT id FROM category WHERE LOWER(TRIM(name)) = ?",
                    [norm]
                ).fetchone()
            if existing:
                return existing[0]

            category_id = str(uuid.uuid4())
            try:
                conn.execute(
                    "INSERT INTO category (id, name, parent_id, normalized_name) VALUES (?, ?, ?, lower(trim(?)))",
                    [category_id, category_name, parent_id, category_name]
                )
            except Exception:
                # Fallback insert for older schemas
                conn.execute(
                    "INSERT INTO category (id, name, parent_id) VALUES (?, ?, ?)",
                    [category_id, category_name, parent_id]
                )
            
            
            # Log the creation
            conn.execute(
                "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    str(uuid.uuid4()),
                    "category",
                    category_id,
                    "ai_auto_create",
                    json.dumps({
                        "name": category_name,
                        "parent_id": parent_id,
                        "confidence": confidence,
                        "method": "smart_categorization"
                    }),
                    datetime.now(UTC),
                    "ai_smart_system"
                ]
            )
            
            logger.info(f"Auto-created category: {category_name} (confidence: {confidence:.2f})")
            return category_id
            
        except Exception as e:
            logger.error(f"Failed to create category {category_name}: {e}")
            return None
    
    def _find_parent_category_id(self, category_name: str, _depth: int = 0) -> Optional[str]:
        """Find the appropriate parent category ID (with recursion guard)"""
        # Prevent infinite recursion - max 2 levels of parent lookup
        if _depth > 2:
            return None

        conn = get_conn()
        category_lower = category_name.lower()

        # Check direct mapping
        parent_name = self.parent_hierarchy.get(category_lower)
        if parent_name:
            try:
                result = conn.execute(
                    "SELECT id FROM category WHERE normalized_name = lower(trim(?))",
                    [parent_name]
                ).fetchone()
            except Exception:
                result = conn.execute(
                    "SELECT id FROM category WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))",
                    [parent_name]
                ).fetchone()
            if result:
                return result[0]
            else:
                # Create parent WITHOUT recursive parent lookup to avoid infinite recursion
                return self._create_category_simple(parent_name)

        # Check keyword-based mapping
        for keyword, parent_name in self.parent_hierarchy.items():
            if keyword in category_lower or category_lower in keyword:
                try:
                    result = conn.execute(
                        "SELECT id FROM category WHERE normalized_name = lower(trim(?))",
                        [parent_name]
                    ).fetchone()
                except Exception:
                    result = conn.execute(
                        "SELECT id FROM category WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))",
                        [parent_name]
                    ).fetchone()
                if result:
                    return result[0]
                else:
                    # Create parent WITHOUT recursive parent lookup
                    return self._create_category_simple(parent_name)

        return None  # No parent (root category)

    def _create_category_simple(self, category_name: str) -> Optional[str]:
        """Create a category without recursively looking up parents (prevents infinite recursion)"""
        conn = get_conn()

        try:
            # Check if already exists
            norm = category_name.strip().lower()
            try:
                existing = conn.execute(
                    "SELECT id FROM category WHERE normalized_name = ?",
                    [norm]
                ).fetchone()
            except Exception:
                existing = conn.execute(
                    "SELECT id FROM category WHERE LOWER(TRIM(name)) = ?",
                    [norm]
                ).fetchone()
            if existing:
                return existing[0]

            category_id = str(uuid.uuid4())
            try:
                conn.execute(
                    "INSERT INTO category (id, name, parent_id, normalized_name) VALUES (?, ?, NULL, lower(trim(?)))",
                    [category_id, category_name, category_name]
                )
            except Exception:
                conn.execute(
                    "INSERT INTO category (id, name, parent_id) VALUES (?, ?, NULL)",
                    [category_id, category_name]
                )

            logger.info(f"Created parent category: {category_name}")
            return category_id

        except Exception as e:
            logger.error(f"Failed to create parent category {category_name}: {e}")
            return None
    
    def _store_pending_suggestion(self, category_name: str, confidence: float):
        """Store category suggestion for manual review"""
        conn = get_conn()
        
        try:
            # Check if already exists
            existing = conn.execute(
                "SELECT id FROM pending_category_suggestions WHERE LOWER(category_name) = ?",
                [category_name.lower()]
            ).fetchone()
            
            if not existing:
                conn.execute("""
                    INSERT INTO pending_category_suggestions 
                    (id, category_name, confidence, first_suggested_at, last_suggested_at, recommended_parent)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    str(uuid.uuid4()),
                    category_name,
                    confidence,
                    datetime.now(UTC),
                    datetime.now(UTC),
                    self.parent_hierarchy.get(category_name.lower())
                ])
            else:
                # Update existing suggestion - use CASE instead of MAX() aggregate
                conn.execute("""
                    UPDATE pending_category_suggestions
                    SET suggestion_count = suggestion_count + 1,
                        confidence = CASE WHEN confidence < ? THEN ? ELSE confidence END,
                        last_suggested_at = ?
                    WHERE LOWER(category_name) = ?
                """, [confidence, confidence, datetime.now(UTC), category_name.lower()])
                
        except Exception as e:
            logger.warning(f"Could not store pending suggestion: {e}")
    
    def bootstrap_standard_categories(self) -> int:
        """Create standard categories that AI commonly suggests - FIXES THE 9.1% SUCCESS RATE"""
        standard_categories = [
            # Core categories that AI suggests most
            ("Income", None),
            ("Food & Dining", None),
            ("Shopping", None),
            ("Transportation", None),
            ("Bills & Utilities", None),
            ("Entertainment", None),
            ("Healthcare", None),
            ("Financial Services", None),
            ("Professional Services", None),
            ("Transfers", None),
            ("Other", None),
            
            # Sub-categories commonly suggested by AI
            ("Grocery", "Food & Dining"),
            ("Food", "Food & Dining"),
            ("Groceries", "Food & Dining"),
            ("Restaurant", "Food & Dining"),
            ("Gas & Convenience", "Transportation"),
            ("Gas & Automotive", "Transportation"),
            ("Utilities", "Bills & Utilities"),
            ("Insurance", "Bills & Utilities"),
            ("Mortgage Payment", "Bills & Utilities"),
            ("Gaming", "Entertainment"),
            ("Software", "Technology"),
            ("Subscription", "Technology"),
            ("Internet Services", "Technology"),
            ("Electronics", "Shopping"),
            ("Internal Transfer", "Transfers"),
            ("External Transfer", "Transfers"),
            ("Personal Transfer", "Transfers"),
            ("Zelle", "Transfers"),
            ("Banking", "Financial Services"),
            ("Payments", "Financial Services"),
            ("Advertising", "Professional Services"),
            ("Purchase", "Shopping"),
            ("Uncategorized", "Other"),
        ]
        
        conn = get_conn()
        created_count = 0
        
        for category_name, parent_name in standard_categories:
            # Check if exists
            existing = conn.execute(
                "SELECT id FROM category WHERE LOWER(name) = ?",
                [category_name.lower()]
            ).fetchone()
            
            if not existing:
                try:
                    # Find parent ID
                    parent_id = None
                    if parent_name:
                        parent_row = conn.execute(
                            "SELECT id FROM category WHERE LOWER(name) = ?",
                            [parent_name.lower()]
                        ).fetchone()
                        parent_id = parent_row[0] if parent_row else None
                    
                    # Create category
                    category_id = str(uuid.uuid4())
                    conn.execute(
                        "INSERT INTO category (id, name, parent_id) VALUES (?, ?, ?)",
                        [category_id, category_name, parent_id]
                    )
                    
                    created_count += 1
                    logger.info(f"Created standard category: {category_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to create category {category_name}: {e}")
        
        return created_count
    
    def get_pending_suggestions(self, limit: int = 50) -> List[Dict]:
        """Get pending category suggestions for review"""
        conn = get_conn()
        
        try:
            rows = conn.execute("""
                SELECT id, category_name, confidence, suggestion_count, 
                       first_suggested_at, last_suggested_at, status, recommended_parent
                FROM pending_category_suggestions
                WHERE status = 'pending'
                ORDER BY suggestion_count DESC, confidence DESC
                LIMIT ?
            """, [limit]).fetchall()
            
            return [
                {
                    "id": row[0],
                    "category_name": row[1],
                    "confidence": row[2],
                    "suggestion_count": row[3],
                    "first_suggested_at": row[4],
                    "last_suggested_at": row[5],
                    "status": row[6],
                    "recommended_parent": row[7]
                }
                for row in rows
            ]
        except Exception:
            return []
    
    def approve_pending_category(self, suggestion_id: str) -> Optional[str]:
        """Approve a pending category suggestion and create it"""
        conn = get_conn()
        
        try:
            # Get suggestion details
            row = conn.execute(
                "SELECT category_name, confidence FROM pending_category_suggestions WHERE id = ?",
                [suggestion_id]
            ).fetchone()
            
            if not row:
                return None
            
            category_name, confidence = row
            
            # Create the category
            category_id = self._create_category(category_name, confidence)
            
            if category_id:
                # Mark as approved
                conn.execute(
                    "UPDATE pending_category_suggestions SET status = 'approved' WHERE id = ?",
                    [suggestion_id]
                )
            
            return category_id
            
        except Exception as e:
            logger.error(f"Failed to approve pending category: {e}")
            return None
    
    # ========================================
    # MERCHANT MEMORY SYSTEM
    # ========================================
    
    def _ensure_merchant_mapping_table(self):
        """Create table to remember merchant-category mappings"""
        conn = get_conn()
        # Table is already created in db.py schema upgrade, but ensure it exists
        try:
            conn.execute("SELECT 1 FROM merchant_category_mapping LIMIT 1")
        except Exception:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS merchant_category_mapping (
                    id TEXT PRIMARY KEY,
                    merchant_name TEXT NOT NULL,
                    merchant_pattern TEXT NOT NULL,
                    category_id TEXT NOT NULL,
                    confidence FLOAT DEFAULT 1.0,
                    usage_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP,
                    created_at TIMESTAMP,
                    UNIQUE(merchant_pattern, category_id)
                )
            """)
    
    def _extract_merchant_name(self, description: str) -> str:
        """Extract normalized merchant name from transaction description"""
        # Common patterns to remove
        remove_patterns = [
            r'CHECKCARD \d{4}',
            r'PURCHASE \d{4}',
            r'#\d+',
            r'\d{2}/\d{2}/\d{2}',
            r'\d{24,}',  # Long transaction IDs
            r'https?://\S+',
            r'\b\d{3}-\d{3}-\d{4}\b',  # Phone numbers
        ]
        
        merchant = description
        for pattern in remove_patterns:
            merchant = re.sub(pattern, '', merchant, flags=re.IGNORECASE)
        
        # Extract key merchant identifiers
        merchant_keywords = {
            'SHEETZ': 'Sheetz',
            'STARBUCKS': 'Starbucks',
            'AMAZON': 'Amazon',
            'HARRIS TE': 'Harris Teeter',
            'AL-BASHA': 'Al-Basha Market',
            'MCDONALD': "McDonald's",
            'GOOGLE': 'Google Services',
            'PAYPAL': 'PayPal',
            'NETFLIX': 'Netflix',
            'SPOTIFY': 'Spotify',
            'NETFLIX': 'Netflix',
            'CLAUDE.AI': 'Claude AI',
            'OPENAI': 'OpenAI',
            'DUKE ENERGY': 'Duke Energy',
            'DOMINION': 'Dominion Energy',
            'GEICO': 'Geico',
            'CARRINGTON': 'Carrington Mortgage',
            'WALMART': 'Walmart',
            'TARGET': 'Target',
            'BEST BUY': 'Best Buy',
            'ZELLE': 'Zelle Transfer',
            'VENMO': 'Venmo',
            'CASH APP': 'Cash App',
        }
        
        merchant_upper = merchant.upper()
        for keyword, normalized_name in merchant_keywords.items():
            if keyword in merchant_upper:
                return normalized_name
        
        # Clean up remaining text
        merchant = re.sub(r'\s+', ' ', merchant).strip()
        # Take first meaningful part
        parts = merchant.split()
        if parts:
            return ' '.join(parts[:3])  # First 3 words usually contain merchant name
        return merchant

    async def learn_from_categorization(self, transaction_id: str, category_id: str):
        """Learn from user's manual categorization"""
        conn = get_conn()
        
        # Get transaction details
        tx = conn.execute(
            "SELECT description_norm, amount FROM [transaction] WHERE id = ?",
            [transaction_id]
        ).fetchone()
        
        if not tx:
            return
        
        description, amount = tx
        merchant_name = self._extract_merchant_name(description)
        
        # Store or update merchant mapping
        existing = conn.execute(
            "SELECT id, usage_count, confidence FROM merchant_category_mapping WHERE merchant_pattern = ?",
            [merchant_name]
        ).fetchone()
        
        if existing:
            # Safe upsert: delete then insert with incremented usage to avoid rare PK/constraint issues on UPDATE
            try:
                current_usage = int(existing[1] or 1)
            except Exception:
                current_usage = 1
            try:
                current_conf = float(existing[2] or 1.0)
            except Exception:
                current_conf = 1.0
            new_usage = current_usage + 1
            new_conf = current_conf + 0.05
            try:
                conn.execute(
                    "DELETE FROM merchant_category_mapping WHERE merchant_pattern = ?",
                    [merchant_name],
                )
            except Exception:
                pass
            conn.execute(
                """
                INSERT INTO merchant_category_mapping
                (id, merchant_name, merchant_pattern, category_id, confidence, confidence_i, usage_count, last_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(uuid.uuid4()),
                    merchant_name,
                    merchant_name,
                    category_id,
                    new_conf,
                    int(round(new_conf * 100)),
                    new_usage,
                    datetime.now(UTC),
                    datetime.now(UTC),
                ],
            )
        else:
            # Create new mapping
            base_conf = 1.0
            conn.execute("""
                INSERT INTO merchant_category_mapping 
                (id, merchant_name, merchant_pattern, category_id, confidence, confidence_i, usage_count, last_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(uuid.uuid4()),
                merchant_name,
                merchant_name,
                category_id,
                base_conf,
                int(round(base_conf * 100)),
                1,
                datetime.now(UTC),
                datetime.now(UTC)
            ])
        
        logger.info(f"Learned: {merchant_name} -> category {category_id}")

    async def _check_learned_merchant_mapping(self, description: str) -> Optional[CategoryPrediction]:
        """Check if we've seen this merchant before"""
        conn = get_conn()
        merchant_name = self._extract_merchant_name(description)
        
        result = conn.execute("""
            SELECT mcm.category_id, c.name,
                   COALESCE(mcm.confidence_i / 100.0, mcm.confidence) AS eff_conf,
                   mcm.usage_count
            FROM merchant_category_mapping mcm
            JOIN category c ON c.id = mcm.category_id
            WHERE mcm.merchant_pattern = ?
            ORDER BY eff_conf DESC, mcm.usage_count DESC
            LIMIT 1
        """, [merchant_name]).fetchone()
        
        if result:
            cat_id, cat_name, confidence, usage_count = result
            # Boost confidence based on usage
            adjusted_confidence = min(0.99, confidence + (usage_count * 0.01))
            
            return CategoryPrediction(
                category_id=cat_id,
                category_name=cat_name,
                confidence=adjusted_confidence,
                reasoning=f"Previously categorized merchant '{merchant_name}' (used {usage_count} times)",
                match_type="learned_merchant",
                supporting_evidence=[f"Merchant: {merchant_name}", f"Previous uses: {usage_count}"]
            )
        return None

    def _get_merchant_category_rules(self) -> Dict[str, str]:
        """Comprehensive merchant to category mapping"""
        return {
            # Gas Stations
            'sheetz': 'Gas & Automotive',
            'shell': 'Gas & Automotive',
            'exxon': 'Gas & Automotive',
            'bp': 'Gas & Automotive',
            
            # Food & Dining
            'starbucks': 'Coffee Shops',
            'mcdonald': 'Fast Food',
            'burger king': 'Fast Food',
            'chick-fil-a': 'Fast Food',
            'bojangles': 'Fast Food',
            'pizza hut': 'Restaurants',
            'outback': 'Restaurants',
            'red robin': 'Restaurants',
            'al-basha': 'Grocery',
            'harris teeter': 'Grocery',
            'food lion': 'Grocery',
            
            # Subscriptions
            'netflix': 'Entertainment Subscriptions',
            'spotify': 'Entertainment Subscriptions',
            'claude.ai': 'Software Subscriptions',
            'openai': 'Software Subscriptions',
            
            # Utilities & Bills
            'duke energy': 'Utilities',
            'dominion energy': 'Utilities',
            'google fiber': 'Internet & Phone',
            'geico': 'Insurance',
            'carrington': 'Mortgage & Rent',
            
            # Shopping
            'amazon': 'Online Shopping',
            'walmart': 'General Merchandise',
            'target': 'General Merchandise',
            'best buy': 'Electronics',
            
            # Transfers
            'zelle': 'Personal Transfers',
            'venmo': 'Personal Transfers',
            'cash app': 'Personal Transfers',
        }

    def get_merchant_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the merchant memory system"""
        try:
            conn = get_conn()
            # Get total learned merchants
            total_merchants = conn.execute("SELECT COUNT(*) FROM merchant_category_mapping").fetchone()[0]
            
            # Get most used merchants
            top_merchants = conn.execute("""
                SELECT merchant_name, category_id, usage_count, confidence
                FROM merchant_category_mapping
                ORDER BY usage_count DESC
                LIMIT 10
            """).fetchall()
            
            # Get recent learning activity
            recent_activity = conn.execute("""
                SELECT merchant_name, category_id, usage_count, last_used
                FROM merchant_category_mapping
                WHERE last_used >= ?
                ORDER BY last_used DESC
                LIMIT 5
            """, [datetime.now(UTC) - timedelta(days=7)]).fetchall()
            
            return {
                "total_learned_merchants": total_merchants,
                "top_merchants": [
                    {
                        "merchant_name": row[0],
                        "category_id": row[1],
                        "usage_count": row[2],
                        "confidence": row[3]
                    }
                    for row in top_merchants
                ],
                "recent_activity": [
                    {
                        "merchant_name": row[0],
                        "category_id": row[1],
                        "usage_count": row[2],
                        "last_used": row[3]
                    }
                    for row in recent_activity
                ]
            }
        except Exception as e:
            logger.error(f"Error getting merchant memory stats: {e}")
            return {"total_learned_merchants": 0, "top_merchants": [], "recent_activity": []}

    # ========================================
    # ENHANCED CATEGORIZATION WITH AUTO-CREATION
    # ========================================
    
    async def predict_category(
        self,
        transaction_id: str,
        description: str,
        amount: float,
        account_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[CategoryPrediction]:
        """Predict category for a transaction using multiple ML approaches"""
        
        # Extract features
        features = await self._extract_features(transaction_id, description, amount, account_id, context)
        
        predictions = []
        
        # 0. Check learned merchant mappings FIRST (highest priority)
        learned_prediction = await self._check_learned_merchant_mapping(description)
        if learned_prediction:
            predictions.append(learned_prediction)
        
        # 1. Exact pattern matching (highest confidence)
        exact_predictions = await self._exact_pattern_matching(description, amount, account_id)
        predictions.extend(exact_predictions)
        
        # 2. Semantic similarity matching
        semantic_predictions = await self._semantic_similarity_matching(description, features, account_id)
        predictions.extend(semantic_predictions)
        
        # 3. Historical pattern analysis
        historical_predictions = await self._historical_pattern_analysis(features, account_id)
        predictions.extend(historical_predictions)
        
        # 4. ML-based prediction using learned models
        ml_predictions = await self._ml_based_prediction(features, account_id)
        predictions.extend(ml_predictions)
        
        # 5. Merchant and amount-based heuristics
        heuristic_predictions = await self._heuristic_categorization(description, amount, features)
        predictions.extend(heuristic_predictions)
        
        # Combine and rank predictions
        final_predictions = await self._combine_and_rank_predictions(predictions, features)
        
        return final_predictions[:5]  # Return top 5 predictions
    
    async def auto_categorize_transaction(
        self,
        transaction_id: str,
        description: str,
        amount: float,
        account_id: str,
        confidence_threshold: float = 0.85
    ) -> Optional[CategoryPrediction]:
        """Automatically categorize transaction if confidence is high enough"""
        
        predictions = await self.predict_category(transaction_id, description, amount, account_id)
        
        if predictions and predictions[0].confidence >= confidence_threshold:
            best_prediction = predictions[0]
            
            # Apply the categorization
            conn = get_conn()
            conn.execute(
                "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?) ON CONFLICT (tx_id) DO UPDATE SET category_id = EXCLUDED.category_id, applied_by = EXCLUDED.applied_by",
                [transaction_id, best_prediction.category_id, "ai_smart_categorization"]
            )
            
            # Log the auto-categorization
            await self._log_auto_categorization(transaction_id, best_prediction)
            
            return best_prediction
        
        return None
    
    async def learn_from_feedback(
        self,
        feedback: LearningFeedback
    ):
        """Learn from user feedback to improve future predictions"""
        
        conn = get_conn()
        
        # Store feedback
        conn.execute("""
            INSERT INTO categorization_feedback (
                id, transaction_id, predicted_category, actual_category,
                prediction_confidence, was_correct, user_correction_time,
                feedback_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4()), feedback.transaction_id, feedback.predicted_category,
            feedback.actual_category, feedback.prediction_confidence, feedback.was_correct,
            feedback.user_correction_time, feedback.feedback_type, datetime.now(UTC)
        ])
        
        # Update learning models
        await self._update_learning_models(feedback)
    
    async def batch_categorize_transactions(
        self,
        account_id: str,
        confidence_threshold: float = 0.8,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Batch categorize uncategorized transactions"""
        
        conn = get_conn()
        
        # Get uncategorized transactions
        uncategorized = conn.execute("""
            SELECT t.id, t.description_norm, t.amount
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON tc.tx_id = t.id
            WHERE t.account_id = ? AND tc.tx_id IS NULL
            ORDER BY t.posted_at DESC
            LIMIT ?
        """, [account_id, limit]).fetchall()
        
        results = {
            'total_processed': 0,
            'auto_categorized': 0,
            'failed': 0,
            'low_confidence': 0,
            'categorizations': []
        }
        
        for tx_id, description, amount in uncategorized:
            try:
                results['total_processed'] += 1
                
                prediction = await self.auto_categorize_transaction(
                    tx_id, description, amount, account_id, confidence_threshold
                )
                
                if prediction:
                    results['auto_categorized'] += 1
                    results['categorizations'].append({
                        'transaction_id': tx_id,
                        'category_id': prediction.category_id,
                        'category_name': prediction.category_name,
                        'confidence': prediction.confidence,
                        'reasoning': prediction.reasoning
                    })
                else:
                    results['low_confidence'] += 1
                    
            except Exception as e:
                results['failed'] += 1
                print(f"Error categorizing transaction {tx_id}: {e}")
        
        return results
    
    async def analyze_categorization_accuracy(
        self,
        account_id: Optional[str] = None,
        days_lookback: int = 30
    ) -> Dict[str, Any]:
        """Analyze the accuracy of AI categorization"""
        
        conn = get_conn()
        cutoff_date = datetime.now(UTC) - timedelta(days=days_lookback)
        
        # Get feedback data
        query = """
            SELECT predicted_category, actual_category, prediction_confidence, was_correct,
                   feedback_type, created_at
            FROM categorization_feedback
            WHERE created_at >= ?
        """
        params = [cutoff_date]
        
        if account_id:
            query += """
                AND transaction_id IN (
                    SELECT id FROM [transaction] WHERE account_id = ?
                )
            """
            params.append(account_id)
        
        feedback_data = conn.execute(query, params).fetchall()
        
        if not feedback_data:
            return {
                'total_predictions': 0,
                'accuracy': 0.0,
                'confidence_distribution': {},
                'category_accuracy': {},
                'recommendations': []
            }
        
        # Calculate overall accuracy
        correct_predictions = sum(1 for fb in feedback_data if fb[3])  # was_correct
        total_predictions = len(feedback_data)
        overall_accuracy = correct_predictions / total_predictions
        
        # Confidence distribution
        confidence_buckets = defaultdict(int)
        for fb in feedback_data:
            confidence = fb[2]  # prediction_confidence
            bucket = f"{int(confidence * 10) * 10}-{int(confidence * 10) * 10 + 10}%"
            confidence_buckets[bucket] += 1
        
        # Category-specific accuracy
        category_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
        for fb in feedback_data:
            predicted_cat = fb[0]
            was_correct = fb[3]
            category_stats[predicted_cat]['total'] += 1
            if was_correct:
                category_stats[predicted_cat]['correct'] += 1
        
        category_accuracy = {
            cat: stats['correct'] / stats['total'] if stats['total'] > 0 else 0
            for cat, stats in category_stats.items()
        }
        
        # Generate recommendations
        recommendations = []
        if overall_accuracy < 0.8:
            recommendations.append("Consider lowering auto-categorization confidence threshold")
        
        low_accuracy_categories = [cat for cat, acc in category_accuracy.items() if acc < 0.7]
        if low_accuracy_categories:
            recommendations.append(f"Review categorization rules for: {', '.join(low_accuracy_categories[:3])}")
        
        return {
            'total_predictions': total_predictions,
            'accuracy': overall_accuracy,
            'confidence_distribution': dict(confidence_buckets),
            'category_accuracy': category_accuracy,
            'recommendations': recommendations
        }
    
    # Feature extraction methods
    
    async def _extract_features(
        self,
        transaction_id: str,
        description: str,
        amount: float,
        account_id: str,
        context: Optional[Dict[str, Any]]
    ) -> CategorizationFeatures:
        """Extract ML features from transaction"""
        
        conn = get_conn()
        
        # Tokenize description
        tokens = self._tokenize_description(description)
        
        # Amount bucket
        amount_bucket = self._get_amount_bucket(amount)
        
        # Amount patterns
        is_round = abs(amount) % 1.0 < 0.01 or abs(amount) % 5.0 < 0.01
        
        # Time features (if available)
        day_of_week = context.get('day_of_week', 0) if context else 0
        hour_of_day = context.get('hour_of_day', None) if context else None
        
        # Merchant indicators
        merchant_indicators = self._extract_merchant_indicators(description)
        
        # Amount patterns
        amount_patterns = self._extract_amount_patterns(amount)
        
        # Description features
        description_length = len(description)
        has_numbers = bool(re.search(r'\d', description))
        has_special_chars = bool(re.search(r'[^a-zA-Z0-9\s]', description))
        
        # Frequency in account
        frequency = conn.execute("""
            SELECT COUNT(*) FROM [transaction] 
            WHERE account_id = ? AND description_norm LIKE ?
        """, [account_id, f"%{description[:20]}%"]).fetchone()[0]
        
        return CategorizationFeatures(
            description_tokens=tokens,
            amount_bucket=amount_bucket,
            amount_value=amount,
            is_round_amount=is_round,
            day_of_week=day_of_week,
            hour_of_day=hour_of_day,
            merchant_indicators=merchant_indicators,
            amount_patterns=amount_patterns,
            description_length=description_length,
            has_numbers=has_numbers,
            has_special_chars=has_special_chars,
            frequency_in_account=frequency
        )
    
    def _tokenize_description(self, description: str) -> List[str]:
        """Tokenize transaction description"""
        # Clean and normalize
        desc = re.sub(r'[^a-zA-Z0-9\s]', ' ', description.lower())
        desc = re.sub(r'\s+', ' ', desc).strip()
        
        # Split into tokens
        tokens = desc.split()
        
        # Remove common stopwords
        stopwords = {'the', 'and', 'or', 'in', 'at', 'on', 'for', 'to', 'of', 'a', 'an'}
        tokens = [t for t in tokens if t not in stopwords and len(t) > 1]
        
        return tokens
    
    def _get_amount_bucket(self, amount: float) -> str:
        """Categorize amount into buckets"""
        abs_amount = abs(amount)
        
        if abs_amount < 5:
            return "micro"
        elif abs_amount < 50:
            return "small"
        elif abs_amount < 200:
            return "medium"
        elif abs_amount < 1000:
            return "large"
        else:
            return "huge"
    
    def _extract_merchant_indicators(self, description: str) -> List[str]:
        """Extract merchant type indicators from description"""
        indicators = []
        
        # Common merchant patterns
        patterns = {
            'restaurant': ['restaurant', 'cafe', 'coffee', 'pizza', 'burger', 'food', 'diner'],
            'gas_station': ['shell', 'exxon', 'bp', 'chevron', 'gas', 'fuel'],
            'grocery': ['grocery', 'market', 'food', 'whole foods', 'kroger', 'safeway'],
            'retail': ['store', 'shop', 'walmart', 'target', 'amazon', 'best buy'],
            'bank': ['bank', 'atm', 'fee', 'transfer', 'payment'],
            'utility': ['electric', 'water', 'gas', 'internet', 'phone', 'cable'],
            'healthcare': ['medical', 'doctor', 'pharmacy', 'hospital', 'dental'],
            'transportation': ['uber', 'lyft', 'taxi', 'bus', 'metro', 'parking']
        }
        
        desc_lower = description.lower()
        for category, keywords in patterns.items():
            if any(keyword in desc_lower for keyword in keywords):
                indicators.append(category)
        
        return indicators
    
    def _extract_amount_patterns(self, amount: float) -> List[str]:
        """Extract patterns from transaction amount"""
        patterns = []
        
        abs_amount = abs(amount)
        
        # Round numbers
        if abs_amount % 1.0 < 0.01:
            patterns.append("whole_dollar")
        
        if abs_amount % 5.0 < 0.01:
            patterns.append("five_dollar_multiple")
        
        if abs_amount % 10.0 < 0.01:
            patterns.append("ten_dollar_multiple")
        
        # Common subscription amounts
        if 9.99 <= abs_amount <= 10.01 or 4.99 <= abs_amount <= 5.01:
            patterns.append("subscription_like")
        
        # Odd cents (might indicate tips)
        cents = abs_amount % 1.0
        if 0.01 <= cents <= 0.99 and cents not in [0.25, 0.50, 0.75]:
            patterns.append("has_tip_like_cents")
        
        return patterns
    
    # Prediction methods
    
    async def _exact_pattern_matching(
        self,
        description: str,
        amount: float,
        account_id: str
    ) -> List[CategoryPrediction]:
        """Find exact or near-exact matches in transaction history"""
        
        conn = get_conn()
        predictions = []
        
        # Exact description match
        exact_matches = conn.execute("""
            SELECT c.id, c.name, COUNT(*) as frequency
            FROM [transaction] t
            JOIN transaction_category tc ON tc.tx_id = t.id
            JOIN category c ON c.id = tc.category_id
            WHERE t.account_id = ? AND t.description_norm = ?
            GROUP BY c.id, c.name
            ORDER BY frequency DESC
            LIMIT 3
        """, [account_id, description]).fetchall()
        
        for cat_id, cat_name, frequency in exact_matches:
            confidence = min(0.95, 0.7 + (frequency * 0.05))  # Higher frequency = higher confidence
            
            predictions.append(CategoryPrediction(
                category_id=cat_id,
                category_name=cat_name,
                confidence=confidence,
                reasoning=f"Exact match found ({frequency} previous occurrences)",
                match_type="exact",
                supporting_evidence=[f"Description: '{description}'", f"Previous occurrences: {frequency}"]
            ))
        
        # Fuzzy description match with similar amounts
        if not exact_matches:
            fuzzy_matches = conn.execute("""
                SELECT c.id, c.name, t.description_norm, AVG(ABS(t.amount - ?)) as avg_amount_diff, COUNT(*) as frequency
                FROM [transaction] t
                JOIN transaction_category tc ON tc.tx_id = t.id
                JOIN category c ON c.id = tc.category_id
                WHERE t.account_id = ? 
                AND (t.description_norm LIKE ? OR ? LIKE t.description_norm)
                AND ABS(t.amount - ?) < ?
                GROUP BY c.id, c.name, t.description_norm
                HAVING frequency >= 2
                ORDER BY frequency DESC, avg_amount_diff ASC
                LIMIT 2
            """, [amount, account_id, f"%{description[:15]}%", f"%{description[:15]}%", amount, abs(amount) * 0.1 + 5]).fetchall()
            
            for cat_id, cat_name, similar_desc, avg_diff, frequency in fuzzy_matches:
                confidence = 0.6 + (frequency * 0.03) - (avg_diff * 0.01)
                confidence = max(0.3, min(0.85, confidence))
                
                predictions.append(CategoryPrediction(
                    category_id=cat_id,
                    category_name=cat_name,
                    confidence=confidence,
                    reasoning=f"Similar pattern found: '{similar_desc}' ({frequency} occurrences)",
                    match_type="pattern",
                    supporting_evidence=[f"Similar description: '{similar_desc}'", f"Amount difference: ${avg_diff:.2f}"]
                ))
        
        return predictions
    
    async def _semantic_similarity_matching(
        self,
        description: str,
        features: CategorizationFeatures,
        account_id: str
    ) -> List[CategoryPrediction]:
        """Use semantic similarity to find matching categories"""
        
        conn = get_conn()
        predictions = []
        
        # Get categories with their typical descriptions
        categories_with_descriptions = conn.execute("""
            SELECT c.id, c.name, GROUP_CONCAT(DISTINCT t.description_norm) as descriptions
            FROM category c
            JOIN transaction_category tc ON tc.category_id = c.id
            JOIN [transaction] t ON t.id = tc.tx_id
            WHERE t.account_id = ?
            GROUP BY c.id, c.name
            HAVING COUNT(*) >= 2
        """, [account_id]).fetchall()
        
        description_tokens = set(features.description_tokens)
        
        for cat_id, cat_name, descriptions_str in categories_with_descriptions:
            # Calculate semantic similarity
            all_descriptions = descriptions_str.split(',') if descriptions_str else []
            similarity_scores = []
            
            for existing_desc in all_descriptions:
                existing_tokens = set(self._tokenize_description(existing_desc))
                
                # Jaccard similarity
                intersection = len(description_tokens & existing_tokens)
                union = len(description_tokens | existing_tokens)
                
                if union > 0:
                    jaccard_sim = intersection / union
                    similarity_scores.append(jaccard_sim)
            
            if similarity_scores:
                max_similarity = max(similarity_scores)
                
                if max_similarity > 0.3:  # Threshold for considering semantic match
                    confidence = min(0.8, max_similarity * 0.8 + 0.2)
                    
                    predictions.append(CategoryPrediction(
                        category_id=cat_id,
                        category_name=cat_name,
                        confidence=confidence,
                        reasoning=f"Semantic similarity ({max_similarity:.2f}) with existing transactions",
                        match_type="semantic",
                        supporting_evidence=[f"Token overlap: {description_tokens & existing_tokens}"]
                    ))
        
        return sorted(predictions, key=lambda p: p.confidence, reverse=True)[:3]
    
    async def _historical_pattern_analysis(
        self,
        features: CategorizationFeatures,
        account_id: str
    ) -> List[CategoryPrediction]:
        """Analyze historical patterns for categorization"""
        
        conn = get_conn()
        predictions = []
        
        # Merchant indicator patterns
        for merchant_type in features.merchant_indicators:
            merchant_categories = conn.execute("""
                SELECT c.id, c.name, COUNT(*) as frequency
                FROM [transaction] t
                JOIN transaction_category tc ON tc.tx_id = t.id
                JOIN category c ON c.id = tc.category_id
                WHERE t.account_id = ? AND LOWER(t.description_norm) LIKE ?
                GROUP BY c.id, c.name
                ORDER BY frequency DESC
                LIMIT 2
            """, [account_id, f"%{merchant_type}%"]).fetchall()
            
            for cat_id, cat_name, frequency in merchant_categories:
                confidence = min(0.75, 0.4 + (frequency * 0.05))
                
                predictions.append(CategoryPrediction(
                    category_id=cat_id,
                    category_name=cat_name,
                    confidence=confidence,
                    reasoning=f"Historical pattern for {merchant_type} merchants",
                    match_type="historical",
                    supporting_evidence=[f"Merchant type: {merchant_type}", f"Historical frequency: {frequency}"]
                ))
        
        # Amount bucket patterns
        amount_bucket_categories = conn.execute("""
            SELECT c.id, c.name, COUNT(*) as frequency
            FROM [transaction] t
            JOIN transaction_category tc ON tc.tx_id = t.id
            JOIN category c ON c.id = tc.category_id
            WHERE t.account_id = ? 
            AND CASE 
                WHEN ABS(t.amount) < 5 THEN 'micro'
                WHEN ABS(t.amount) < 50 THEN 'small'
                WHEN ABS(t.amount) < 200 THEN 'medium'
                WHEN ABS(t.amount) < 1000 THEN 'large'
                ELSE 'huge'
            END = ?
            GROUP BY c.id, c.name
            HAVING frequency >= 3
            ORDER BY frequency DESC
            LIMIT 2
        """, [account_id, features.amount_bucket]).fetchall()
        
        for cat_id, cat_name, frequency in amount_bucket_categories:
            confidence = min(0.6, 0.3 + (frequency * 0.02))
            
            predictions.append(CategoryPrediction(
                category_id=cat_id,
                category_name=cat_name,
                confidence=confidence,
                reasoning=f"Common category for {features.amount_bucket} amounts",
                match_type="historical",
                supporting_evidence=[f"Amount bucket: {features.amount_bucket}", f"Historical frequency: {frequency}"]
            ))
        
        return predictions
    
    async def _ml_based_prediction(
        self,
        features: CategorizationFeatures,
        account_id: str
    ) -> List[CategoryPrediction]:
        """ML-based prediction using learned patterns"""
        
        # This would implement actual ML models in a real system
        # For now, implementing a simplified heuristic-based approach
        
        predictions = []
        
        # Simple keyword-based ML simulation
        keyword_weights = {
            'grocery': {'food', 'market', 'grocery', 'store'},
            'restaurant': {'restaurant', 'cafe', 'pizza', 'burger'},
            'gas': {'gas', 'fuel', 'shell', 'exxon', 'bp'},
            'utilities': {'electric', 'water', 'internet', 'phone'},
            'entertainment': {'movie', 'theater', 'netflix', 'spotify'},
            'healthcare': {'medical', 'doctor', 'pharmacy', 'dental'}
        }
        
        description_tokens = set(features.description_tokens)
        
        for category_type, keywords in keyword_weights.items():
            keyword_matches = len(description_tokens & keywords)
            
            if keyword_matches > 0:
                confidence = min(0.7, 0.4 + (keyword_matches * 0.2))
                
                predictions.append(CategoryPrediction(
                    category_id=f"ml_{category_type}",
                    category_name=category_type.title(),
                    confidence=confidence,
                    reasoning=f"ML keyword matching ({keyword_matches} matches)",
                    match_type="ml",
                    supporting_evidence=[f"Matched keywords: {description_tokens & keywords}"]
                ))
        
        return predictions
    
    async def _heuristic_categorization(
        self,
        description: str,
        amount: float,
        features: CategorizationFeatures
    ) -> List[CategoryPrediction]:
        """Heuristic-based categorization rules"""
        
        predictions = []
        desc_lower = description.lower()
        
        # ATM/Bank fees
        if any(word in desc_lower for word in ['atm', 'fee', 'bank', 'charge']):
            predictions.append(CategoryPrediction(
                category_id="bank_fees",
                category_name="Bank Fees",
                confidence=0.8,
                reasoning="ATM or bank fee detected",
                match_type="heuristic",
                supporting_evidence=["Contains fee/bank keywords"]
            ))
        
        # Subscriptions (common amounts)
        if features.is_round_amount and 5 <= abs(amount) <= 50:
            if any(word in desc_lower for word in ['netflix', 'spotify', 'subscription', 'monthly']):
                predictions.append(CategoryPrediction(
                    category_id="subscriptions",
                    category_name="Subscriptions",
                    confidence=0.75,
                    reasoning="Subscription-like amount and keywords",
                    match_type="heuristic",
                    supporting_evidence=["Round amount", "Subscription keywords"]
                ))
        
        # Large round amounts (likely rent/mortgage)
        if features.is_round_amount and abs(amount) > 500:
            predictions.append(CategoryPrediction(
                category_id="housing",
                category_name="Housing",
                confidence=0.6,
                reasoning="Large round amount suggests rent/mortgage",
                match_type="heuristic",
                supporting_evidence=["Large round amount"]
            ))
        
        return predictions
    
    async def _combine_and_rank_predictions(
        self,
        predictions: List[CategoryPrediction],
        features: CategorizationFeatures
    ) -> List[CategoryPrediction]:
        """Combine and rank all predictions"""
        
        # Group by category
        category_predictions = defaultdict(list)
        for pred in predictions:
            category_predictions[pred.category_id].append(pred)
        
        # Combine predictions for same category
        final_predictions = []
        for category_id, preds in category_predictions.items():
            if not preds:
                continue
            
            # Use the highest confidence prediction as base
            best_pred = max(preds, key=lambda p: p.confidence)
            
            # Boost confidence if multiple prediction types agree
            if len(preds) > 1:
                confidence_boost = min(0.15, len(preds) * 0.05)
                best_pred.confidence = min(0.95, best_pred.confidence + confidence_boost)
                
                # Combine reasoning
                all_reasoning = [p.reasoning for p in preds]
                best_pred.reasoning = f"Multiple factors: {'; '.join(all_reasoning[:3])}"
                
                # Combine evidence
                all_evidence = []
                for p in preds:
                    all_evidence.extend(p.supporting_evidence)
                best_pred.supporting_evidence = list(set(all_evidence))[:5]
            
            final_predictions.append(best_pred)
        
        # Sort by confidence
        return sorted(final_predictions, key=lambda p: p.confidence, reverse=True)
    
    # Helper methods
    
    async def _log_auto_categorization(
        self,
        transaction_id: str,
        prediction: CategoryPrediction
    ):
        """Log automatic categorization for tracking"""
        
        conn = get_conn()
        
        conn.execute("""
            INSERT INTO auto_categorization_log (
                id, transaction_id, category_id, confidence, reasoning,
                match_type, evidence_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4()), transaction_id, prediction.category_id,
            prediction.confidence, prediction.reasoning, prediction.match_type,
            json.dumps(prediction.supporting_evidence), datetime.now(UTC)
        ])
    
    async def _update_learning_models(
        self,
        feedback: LearningFeedback
    ):
        """Update ML models based on feedback"""
        
        # In a real implementation, this would update actual ML models
        # For now, we can update heuristic weights or pattern caches
        
        conn = get_conn()
        
        # Update pattern effectiveness
        if feedback.was_correct:
            # Reinforce successful patterns
            pass
        else:
            # Adjust patterns that led to incorrect predictions
            pass


# Global instance
_smart_categorization_engine = None

def get_smart_categorization_engine() -> SmartCategorizationEngine:
    """Get the global smart categorization engine instance"""
    global _smart_categorization_engine
    if _smart_categorization_engine is None:
        _smart_categorization_engine = SmartCategorizationEngine()
    return _smart_categorization_engine


# ========================================
# CONVENIENCE FUNCTIONS FOR API INTEGRATION
# ========================================

def process_ai_category_suggestion(ai_category_name: str, confidence: float = 0.8, 
                                 auto_create: bool = True) -> CategoryCreationResult:
    """Process an AI category suggestion and return result - MAIN FUNCTION TO USE"""
    engine = get_smart_categorization_engine()
    return engine.find_or_create_category(ai_category_name, confidence, auto_create)


def analyze_category_gaps() -> CategoryGapAnalysis:
    """Analyze the gap between AI suggestions and available categories"""
    engine = get_smart_categorization_engine()
    return engine.analyze_category_gaps()


def bootstrap_missing_categories() -> int:
    """Bootstrap standard categories to fix the 9.1% success rate issue"""
    engine = get_smart_categorization_engine()
    return engine.bootstrap_standard_categories()


def get_pending_category_suggestions(limit: int = 50) -> List[Dict]:
    """Get pending category suggestions for manual review"""
    engine = get_smart_categorization_engine()
    return engine.get_pending_suggestions(limit)


def approve_category_suggestion(suggestion_id: str) -> Optional[str]:
    """Approve a pending category suggestion"""
    engine = get_smart_categorization_engine()
    return engine.approve_pending_category(suggestion_id)


def bulk_process_ai_suggestions(transaction_limit: int = 1000) -> Dict[str, Any]:
    """Bulk process AI suggestions and create missing categories"""
    engine = get_smart_categorization_engine()
    
    # First, analyze the gaps
    gap_analysis = engine.analyze_category_gaps(transaction_limit)
    
    # Bootstrap standard categories
    created_count = engine.bootstrap_standard_categories()
    
    # Process pending suggestions with high confidence
    processed_suggestions = 0
    pending = engine.get_pending_suggestions()
    
    for suggestion in pending:
        if suggestion['confidence'] >= 0.8 and suggestion['suggestion_count'] >= 2:
            category_id = engine.approve_pending_category(suggestion['id'])
            if category_id:
                processed_suggestions += 1
    
    return {
        "gap_analysis": gap_analysis,
        "standard_categories_created": created_count,
        "pending_suggestions_processed": processed_suggestions,
        "total_categories_added": created_count + processed_suggestions
    }


# ========================================
# MERCHANT MEMORY CONVENIENCE FUNCTIONS
# ========================================

async def learn_from_transaction_categorization(transaction_id: str, category_id: str):
    """Learn from user's manual categorization - MAIN INTEGRATION POINT"""
    engine = get_smart_categorization_engine()
    await engine.learn_from_categorization(transaction_id, category_id)


def get_merchant_memory_statistics() -> Dict[str, Any]:
    """Get merchant memory system statistics"""
    engine = get_smart_categorization_engine()
    return engine.get_merchant_memory_stats()


def extract_merchant_from_description(description: str) -> str:
    """Extract normalized merchant name from transaction description"""
    engine = get_smart_categorization_engine()
    return engine._extract_merchant_name(description)


# ========================================
# TRAINING DATASET & BACKFILL FUNCTIONS
# ========================================

def build_training_dataset(min_occurrences: int = 2) -> List[Dict]:
    """
    Extract categorized transactions as a training dataset.

    Returns a list of {description, amount, category_name, category_id, source, occurrence_count}
    for all manually categorized transactions (excluding AI-applied).
    """
    conn = get_conn()

    rows = conn.execute("""
        SELECT
            t.description_norm,
            t.amount,
            c.name AS category_name,
            c.id AS category_id,
            tc.applied_by,
            COUNT(*) OVER (PARTITION BY c.id) AS category_count
        FROM [transaction] t
        JOIN transaction_category tc ON tc.tx_id = t.id
        JOIN category c ON tc.category_id = c.id
        WHERE tc.applied_by NOT LIKE 'ai_%'  -- Exclude AI-applied to avoid circular learning
           OR tc.applied_by IS NULL
        ORDER BY category_count DESC
    """).fetchall()

    dataset = []
    for desc, amount, cat_name, cat_id, source, cat_count in rows:
        dataset.append({
            "description": desc,
            "amount": float(amount),
            "category_name": cat_name,
            "category_id": cat_id,
            "source": source or "unknown",
            "occurrence_count": int(cat_count),
        })

    logger.info(f"Built training dataset with {len(dataset)} entries")
    return dataset


def build_merchant_category_map(min_occurrences: int = 2, min_confidence: float = 0.6) -> List[Dict]:
    """
    Build merchant→category mapping from existing categorized transactions.

    Returns a list of {merchant_pattern, category_id, category_name, occurrence_count, confidence}
    """
    conn = get_conn()
    engine = get_smart_categorization_engine()

    # Get all categorized transactions
    rows = conn.execute("""
        SELECT
            t.description_norm,
            c.id AS category_id,
            c.name AS category_name,
            tc.applied_by
        FROM [transaction] t
        JOIN transaction_category tc ON tc.tx_id = t.id
        JOIN category c ON tc.category_id = c.id
        WHERE (tc.applied_by NOT LIKE 'ai_%' OR tc.applied_by IS NULL)
    """).fetchall()

    # Build merchant → category counts
    merchant_categories: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    merchant_cat_names: Dict[str, str] = {}

    for desc, cat_id, cat_name, source in rows:
        merchant = engine._extract_merchant_name(desc or "")
        if len(merchant.strip()) >= 3:
            merchant_categories[merchant][cat_id] += 1
            merchant_cat_names[cat_id] = cat_name

    # Calculate confidence and filter
    mappings = []
    for merchant, category_counts in merchant_categories.items():
        total_count = sum(category_counts.values())

        for cat_id, count in category_counts.items():
            if count >= min_occurrences:
                confidence = count / total_count
                if confidence >= min_confidence:
                    mappings.append({
                        "merchant_pattern": merchant.strip(),
                        "category_id": cat_id,
                        "category_name": merchant_cat_names.get(cat_id, "Unknown"),
                        "occurrence_count": count,
                        "confidence": round(confidence, 3),
                    })

    # Sort by occurrence count
    mappings.sort(key=lambda x: x["occurrence_count"], reverse=True)

    logger.info(f"Built merchant category map with {len(mappings)} entries")
    return mappings


def backfill_merchant_memory(min_occurrences: int = 2, min_confidence: float = 0.6) -> Dict[str, int]:
    """
    Populate merchant_category_mapping table from historical categorized transactions.

    This bootstraps the merchant memory system so it can categorize similar future transactions.
    """
    conn = get_conn()

    # Get mappings
    mappings = build_merchant_category_map(min_occurrences, min_confidence)

    inserted = 0
    updated = 0
    skipped = 0

    for mapping in mappings:
        merchant = mapping["merchant_pattern"]
        cat_id = mapping["category_id"]
        confidence = mapping["confidence"]
        count = mapping["occurrence_count"]

        try:
            # Check if exists
            existing = conn.execute(
                "SELECT id, usage_count, confidence FROM merchant_category_mapping WHERE merchant_pattern = ?",
                [merchant]
            ).fetchone()

            if existing:
                # Update if this has higher confidence
                existing_conf = float(existing[2] or 0)
                if confidence > existing_conf:
                    conn.execute("""
                        UPDATE merchant_category_mapping
                        SET category_id = ?, confidence = ?, confidence_i = ?,
                            usage_count = usage_count + ?, last_used = ?
                        WHERE merchant_pattern = ?
                    """, [cat_id, confidence, int(round(confidence * 100)), count, datetime.now(UTC), merchant])
                    updated += 1
                else:
                    skipped += 1
            else:
                # Insert new mapping
                conn.execute("""
                    INSERT INTO merchant_category_mapping
                    (id, merchant_name, merchant_pattern, category_id, confidence, confidence_i, usage_count, last_used, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    str(uuid.uuid4()),
                    merchant,
                    merchant,
                    cat_id,
                    confidence,
                    int(round(confidence * 100)),
                    count,
                    datetime.now(UTC),
                    datetime.now(UTC),
                ])
                inserted += 1

        except Exception as e:
            logger.warning(f"Error backfilling merchant {merchant}: {e}")
            skipped += 1

    logger.info(f"Backfilled merchant memory: {inserted} inserted, {updated} updated, {skipped} skipped")
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "total_mappings": len(mappings)}


def categorize_with_training_data(
    confidence_threshold: float = 0.6,
    limit: int = 500,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Use merchant memory and training data to categorize uncategorized transactions.

    This re-processes uncategorized transactions using:
    1. Merchant memory lookups (from backfilled data)
    2. Description similarity matching

    Args:
        confidence_threshold: Minimum confidence to auto-apply category
        limit: Maximum transactions to process
        dry_run: If True, don't actually apply categories

    Returns:
        Stats about the categorization run
    """
    conn = get_conn()
    engine = get_smart_categorization_engine()

    # Get uncategorized transactions
    uncategorized = conn.execute("""
        SELECT t.id, t.description_norm, t.amount, t.account_id
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON tc.tx_id = t.id
        WHERE tc.tx_id IS NULL
        ORDER BY t.posted_at DESC
        LIMIT ?
    """, [limit]).fetchall()

    stats = {
        "total_processed": 0,
        "categorized_by_merchant_memory": 0,
        "categorized_by_similarity": 0,
        "low_confidence": 0,
        "errors": 0,
        "categorizations": [],
    }

    for tx_id, description, amount, account_id in uncategorized:
        stats["total_processed"] += 1

        try:
            # Step 1: Try merchant memory lookup
            merchant = engine._extract_merchant_name(description or "")

            result = conn.execute("""
                SELECT mcm.category_id, c.name,
                       COALESCE(mcm.confidence_i / 100.0, mcm.confidence) AS eff_conf,
                       mcm.usage_count
                FROM merchant_category_mapping mcm
                JOIN category c ON c.id = mcm.category_id
                WHERE mcm.merchant_pattern = ?
                ORDER BY eff_conf DESC, mcm.usage_count DESC
                LIMIT 1
            """, [merchant]).fetchone()

            if result:
                cat_id, cat_name, confidence, usage_count = result
                adjusted_confidence = min(0.99, float(confidence) + (int(usage_count) * 0.01))

                if adjusted_confidence >= confidence_threshold:
                    if not dry_run:
                        # Check if category already exists for this tx
                        existing = conn.execute(
                            "SELECT 1 FROM transaction_category WHERE tx_id = ?", [tx_id]
                        ).fetchone()
                        if existing:
                            conn.execute(
                                "UPDATE transaction_category SET category_id = ?, applied_by = ? WHERE tx_id = ?",
                                [cat_id, "training_data_backfill", tx_id]
                            )
                        else:
                            conn.execute(
                                "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
                                [tx_id, cat_id, "training_data_backfill"]
                            )

                    stats["categorized_by_merchant_memory"] += 1
                    stats["categorizations"].append({
                        "tx_id": tx_id,
                        "category_id": cat_id,
                        "category_name": cat_name,
                        "confidence": adjusted_confidence,
                        "method": "merchant_memory",
                        "merchant": merchant,
                    })
                    continue

            # Step 2: Try description similarity
            similar = conn.execute("""
                SELECT c.id, c.name, t.description_norm,
                       COUNT(*) as frequency
                FROM [transaction] t
                JOIN transaction_category tc ON tc.tx_id = t.id
                JOIN category c ON tc.category_id = c.id
                WHERE t.description_norm LIKE ?
                  AND (tc.applied_by NOT LIKE 'ai_%' OR tc.applied_by IS NULL)
                GROUP BY c.id, c.name, t.description_norm
                ORDER BY frequency DESC
                LIMIT 1
            """, [f"%{(description or '')[:20]}%"]).fetchone()

            if similar:
                cat_id, cat_name, similar_desc, frequency = similar
                # Calculate similarity confidence
                sim_confidence = min(0.85, 0.5 + (int(frequency) * 0.1))

                if sim_confidence >= confidence_threshold:
                    if not dry_run:
                        # Check if category already exists for this tx
                        existing = conn.execute(
                            "SELECT 1 FROM transaction_category WHERE tx_id = ?", [tx_id]
                        ).fetchone()
                        if existing:
                            conn.execute(
                                "UPDATE transaction_category SET category_id = ?, applied_by = ? WHERE tx_id = ?",
                                [cat_id, "similarity_match", tx_id]
                            )
                        else:
                            conn.execute(
                                "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
                                [tx_id, cat_id, "similarity_match"]
                            )

                    stats["categorized_by_similarity"] += 1
                    stats["categorizations"].append({
                        "tx_id": tx_id,
                        "category_id": cat_id,
                        "category_name": cat_name,
                        "confidence": sim_confidence,
                        "method": "similarity",
                        "similar_to": similar_desc,
                    })
                    continue

            stats["low_confidence"] += 1

        except Exception as e:
            logger.warning(f"Error categorizing tx {tx_id}: {e}")
            stats["errors"] += 1

    return stats
