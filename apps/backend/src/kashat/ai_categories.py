"""
Enhanced AI Category Management

Provides intelligent category suggestions, automatic category creation,
and smart category matching based on existing categories and transaction patterns.
"""

from __future__ import annotations

import re
import json
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from difflib import SequenceMatcher

from .db import get_conn
from .ai import CategorySuggestion, get_ai_service


@dataclass
class CategoryMatch:
    """Result of category matching"""
    category_id: str
    category_name: str
    match_type: str  # 'exact', 'fuzzy', 'parent', 'ai_suggested'
    confidence: float
    reasoning: str


@dataclass
class SmartCategorySuggestion:
    """Enhanced category suggestion with database integration"""
    category_id: Optional[str]
    category_name: str
    confidence: float
    reasoning: str
    match_type: str
    is_new_category: bool = False
    parent_category_id: Optional[str] = None
    auto_create_confidence: float = 0.0


class CategoryMatcher:
    """Smart category matching and suggestion service"""
    
    def __init__(self):
        self.categories_cache = None
        self.category_keywords_cache = None
        self._refresh_cache()
    
    def _refresh_cache(self):
        """Refresh category cache from database"""
        conn = get_conn()
        
        # Load all categories
        rows = conn.execute("SELECT id, name, parent_id FROM category ORDER BY name").fetchall()
        self.categories_cache = {}
        self.category_tree = {}
        
        for row in rows:
            cat_id, name, parent_id = row
            self.categories_cache[cat_id] = {
                'name': name,
                'parent_id': parent_id,
                'name_lower': name.lower(),
                'keywords': self._extract_keywords(name)
            }
            
            # Build tree structure
            if parent_id not in self.category_tree:
                self.category_tree[parent_id] = []
            self.category_tree[parent_id].append(cat_id)
    
    def _extract_keywords(self, category_name: str) -> List[str]:
        """Extract searchable keywords from category name"""
        # Remove common words and split
        stop_words = {'and', 'or', 'the', 'a', 'an', 'for', 'to', 'of', 'in', 'on', 'at'}
        words = re.findall(r'\w+', category_name.lower())
        return [word for word in words if word not in stop_words and len(word) > 2]
    
    def find_exact_matches(self, ai_suggestions: List[CategorySuggestion]) -> List[CategoryMatch]:
        """Find exact category name matches"""
        matches = []
        
        for suggestion in ai_suggestions:
            for cat_id, cat_info in self.categories_cache.items():
                if cat_info['name_lower'] == suggestion.category_name.lower():
                    matches.append(CategoryMatch(
                        category_id=cat_id,
                        category_name=cat_info['name'],
                        match_type='exact',
                        confidence=min(0.95, suggestion.confidence + 0.2),
                        reasoning=f"Exact match for '{suggestion.category_name}'"
                    ))
                    break
        
        return matches
    
    def find_fuzzy_matches(self, ai_suggestions: List[CategorySuggestion], threshold: float = 0.8) -> List[CategoryMatch]:
        """Find fuzzy/similar category name matches"""
        matches = []
        
        for suggestion in ai_suggestions:
            best_match = None
            best_score = 0
            
            for cat_id, cat_info in self.categories_cache.items():
                # Check direct name similarity
                similarity = SequenceMatcher(None, 
                    suggestion.category_name.lower(), 
                    cat_info['name_lower']
                ).ratio()
                
                if similarity > threshold and similarity > best_score:
                    best_score = similarity
                    best_match = (cat_id, cat_info, similarity)
                
                # Check keyword overlap
                suggestion_keywords = self._extract_keywords(suggestion.category_name)
                category_keywords = cat_info['keywords']
                
                if suggestion_keywords and category_keywords:
                    keyword_overlap = len(set(suggestion_keywords) & set(category_keywords))
                    keyword_score = keyword_overlap / max(len(suggestion_keywords), len(category_keywords))
                    
                    if keyword_score > 0.5 and keyword_score > best_score:
                        best_score = keyword_score
                        best_match = (cat_id, cat_info, keyword_score)
            
            if best_match:
                cat_id, cat_info, score = best_match
                confidence = min(0.9, suggestion.confidence * score)
                matches.append(CategoryMatch(
                    category_id=cat_id,
                    category_name=cat_info['name'],
                    match_type='fuzzy',
                    confidence=confidence,
                    reasoning=f"Similar to '{suggestion.category_name}' (similarity: {score:.2f})"
                ))
        
        return matches
    
    def find_parent_category_matches(self, ai_suggestions: List[CategorySuggestion]) -> List[CategoryMatch]:
        """Find suitable parent categories for new suggestions"""
        matches = []
        
        # Define parent category mappings
        parent_mappings = {
            'food': ['Food & Dining', 'Dining', 'Food', 'Restaurant'],
            'transport': ['Transportation', 'Travel', 'Transport'],
            'shopping': ['Shopping', 'Retail', 'Purchase'],
            'entertainment': ['Entertainment', 'Recreation', 'Fun'],
            'utility': ['Utilities', 'Bills', 'Services'],
            'health': ['Healthcare', 'Medical', 'Health'],
            'finance': ['Financial', 'Banking', 'Investment'],
            'gas': ['Gas & Automotive', 'Automotive', 'Car', 'Vehicle']
        }
        
        for suggestion in ai_suggestions:
            suggestion_lower = suggestion.category_name.lower()
            
            for category_type, parent_names in parent_mappings.items():
                if any(keyword in suggestion_lower for keyword in [category_type]):
                    # Find matching parent category
                    for cat_id, cat_info in self.categories_cache.items():
                        if any(parent_name.lower() in cat_info['name_lower'] 
                               for parent_name in parent_names):
                            matches.append(CategoryMatch(
                                category_id=cat_id,
                                category_name=cat_info['name'],
                                match_type='parent',
                                confidence=suggestion.confidence * 0.7,
                                reasoning=f"Parent category for '{suggestion.category_name}'"
                            ))
                            break
                    break
        
        return matches
    
    def suggest_smart_categories(self, description: str, amount: float, 
                               existing_category_id: Optional[str] = None) -> List[SmartCategorySuggestion]:
        """Get smart category suggestions with database integration"""
        
        # Get AI suggestions via provider; fall back to local on error
        ai_insights_list = []
        try:
            ai_service = get_ai_service()
            import anyio
            async def _call():
                res = await ai_service.analyze_transaction(description, float(amount))
                return res.category_suggestions
            ai_insights_list = anyio.run(_call)
        except Exception:
            # Fallback to local heuristic suggestions
            ai_insights_list = get_ai_service().local_service.suggest_categories(description, amount)
        
        # Find matches in existing categories
        exact_matches = self.find_exact_matches(ai_insights_list)
        fuzzy_matches = self.find_fuzzy_matches(ai_insights_list)
        parent_matches = self.find_parent_category_matches(ai_insights_list)
        
        # Combine and rank suggestions
        suggestions = []
        used_category_ids = set()
        
        # Add exact matches first (highest priority)
        for match in exact_matches:
            if match.category_id not in used_category_ids:
                suggestions.append(SmartCategorySuggestion(
                    category_id=match.category_id,
                    category_name=match.category_name,
                    confidence=match.confidence,
                    reasoning=match.reasoning,
                    match_type=match.match_type
                ))
                used_category_ids.add(match.category_id)
        
        # Add fuzzy matches
        for match in fuzzy_matches:
            if match.category_id not in used_category_ids:
                suggestions.append(SmartCategorySuggestion(
                    category_id=match.category_id,
                    category_name=match.category_name,
                    confidence=match.confidence,
                    reasoning=match.reasoning,
                    match_type=match.match_type
                ))
                used_category_ids.add(match.category_id)
        
        # Add suggestions for new categories (if confidence is high enough)
        for ai_suggestion in ai_insights_list:
            # Check if we already have a match for this suggestion
            suggestion_matched = any(
                ai_suggestion.category_name.lower() in s.category_name.lower() 
                for s in suggestions
            )
            
            if not suggestion_matched and ai_suggestion.confidence > 0.7:
                # Find suitable parent
                parent_id = None
                for match in parent_matches:
                    if ai_suggestion.category_name.lower() in match.reasoning.lower():
                        parent_id = match.category_id
                        break
                
                suggestions.append(SmartCategorySuggestion(
                    category_id=None,
                    category_name=ai_suggestion.category_name,
                    confidence=ai_suggestion.confidence,
                    reasoning=f"AI suggested new category: {ai_suggestion.reasoning}",
                    match_type='ai_suggested',
                    is_new_category=True,
                    parent_category_id=parent_id,
                    auto_create_confidence=ai_suggestion.confidence
                ))
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def analyze_transaction_patterns(self, merchant_name: str, amount: float) -> Dict:
        """Analyze patterns for similar transactions to improve suggestions"""
        conn = get_conn()
        
        # Find similar transactions by merchant name
        similar_transactions = conn.execute("""
            SELECT t.id, t.description_norm, tc.category_id, c.name as category_name
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
            LEFT JOIN category c ON tc.category_id = c.id
            WHERE (
                LOWER(t.description_norm) LIKE ? 
                OR LOWER(COALESCE(t.ai_merchant_name, '')) LIKE ?
            )
            AND tc.category_id IS NOT NULL
            LIMIT 10
        """, [f"%{merchant_name.lower()}%", f"%{merchant_name.lower()}%"]).fetchall()
        
        if not similar_transactions:
            return {"similar_count": 0, "common_categories": []}
        
        # Analyze common categories
        category_counts = {}
        for tx in similar_transactions:
            if tx[2]:  # category_id exists
                cat_name = tx[3]  # category_name
                category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        
        # Get most common categories
        common_categories = sorted(
            category_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        return {
            "similar_count": len(similar_transactions),
            "common_categories": [
                {
                    "category_name": cat_name,
                    "usage_count": count,
                    "confidence": count / len(similar_transactions)
                }
                for cat_name, count in common_categories
            ]
        }
    
    def get_category_usage_stats(self) -> Dict:
        """Get category usage statistics for better suggestions"""
        conn = get_conn()
        
        stats = conn.execute("""
            SELECT 
                c.id,
                c.name,
                COUNT(tc.tx_id) as usage_count,
                SUM(ABS(t.amount)) as total_amount,
                AVG(ABS(t.amount)) as avg_amount
            FROM category c
            LEFT JOIN transaction_category tc ON c.id = tc.category_id
            LEFT JOIN [transaction] t ON tc.tx_id = t.id
            GROUP BY c.id, c.name
            ORDER BY usage_count DESC
        """).fetchall()
        
        return {
            row[0]: {  # category_id
                "name": row[1],
                "usage_count": row[2] or 0,
                "total_amount": float(row[3] or 0),
                "avg_amount": float(row[4] or 0)
            }
            for row in stats
        }


# Global category matcher instance
_category_matcher: Optional[CategoryMatcher] = None


def get_category_matcher() -> CategoryMatcher:
    """Get or create the global category matcher instance"""
    global _category_matcher
    
    if _category_matcher is None:
        _category_matcher = CategoryMatcher()
    
    return _category_matcher


def refresh_category_cache():
    """Refresh the category cache (call when categories are added/modified)"""
    global _category_matcher
    if _category_matcher:
        _category_matcher._refresh_cache()


async def auto_create_category(category_name: str, parent_id: Optional[str] = None, confidence_threshold: float = 0.8) -> Optional[str]:
    """Automatically create a new category if confidence is high enough"""
    import uuid
    from datetime import datetime, UTC

    conn = get_conn()

    # Check if category already exists (case-insensitive)
    existing = conn.execute(
        "SELECT id FROM category WHERE LOWER(name) = ?",
        [category_name.lower()]
    ).fetchone()

    if existing:
        return existing[0]

    # Find appropriate parent category if not specified
    if not parent_id:
        parent_id = _find_best_parent_category(category_name, conn)

    # Create new category
    category_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO category (id, name, parent_id) VALUES (?, ?, ?)",
        [category_id, category_name, parent_id]
    )

    # Log the auto-creation
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            str(uuid.uuid4()),
            "category",
            category_id,
            "auto_create",
            json.dumps({"name": category_name, "parent_id": parent_id, "confidence_threshold": confidence_threshold}),
            datetime.now(UTC),
            "ai_system"
        ]
    )
    
    # Refresh cache
    refresh_category_cache()
    
    return category_id


def _find_best_parent_category(category_name: str, conn) -> Optional[str]:
    """Find the best parent category for a new category"""
    category_lower = category_name.lower()
    
    # Define parent mappings
    parent_mappings = {
        'expenses': ['food', 'dining', 'restaurant', 'shopping', 'gas', 'fuel', 'entertainment', 'health', 'medical', 'grocery', 'store'],
        'income': ['salary', 'wage', 'payroll', 'freelance', 'contract', 'income'],
        'transfers': ['transfer', 'zelle', 'venmo', 'internal'],
        'utilities': ['electric', 'gas', 'water', 'internet', 'phone', 'cable', 'utility'],
        'transportation': ['uber', 'lyft', 'taxi', 'gas', 'fuel', 'parking', 'metro', 'bus'],
        'fees': ['fee', 'charge', 'overdraft', 'service', 'maintenance']
    }
    
    # Check which parent category fits best
    for parent_cat, keywords in parent_mappings.items():
        if any(keyword in category_lower for keyword in keywords):
            # Find the parent category ID
            parent_row = conn.execute(
                "SELECT id FROM category WHERE LOWER(name) = ? OR LOWER(name) LIKE ?",
                [parent_cat, f'%{parent_cat}%']
            ).fetchone()
            if parent_row:
                return parent_row[0]
    
    # Default to expenses for most categories
    expenses_row = conn.execute(
        "SELECT id FROM category WHERE LOWER(name) LIKE '%expense%' LIMIT 1"
    ).fetchone()
    return expenses_row[0] if expenses_row else None
