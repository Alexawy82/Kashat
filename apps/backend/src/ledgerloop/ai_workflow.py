"""
AI-Powered Automated Workflow System

Provides end-to-end automation for statement processing:
- Import → AI Enhancement → Rule Application → Duplicate Detection
- Smart categorization with confidence thresholds
- Quality validation and error handling
- Progress tracking and reporting
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from enum import Enum

from .ai_import import get_ai_import_processor
from .ai_dedup import get_ai_deduplicator
from .ai_categories import get_category_matcher
from .db import get_conn


class WorkflowStage(Enum):
    IMPORT = "import"
    AI_ENHANCEMENT = "ai_enhancement"
    RULE_APPLICATION = "rule_application"
    DUPLICATE_DETECTION = "duplicate_detection"
    QUALITY_VALIDATION = "quality_validation"
    COMPLETION = "completion"


@dataclass
class WorkflowProgress:
    """Progress tracking for automated workflow"""
    workflow_id: str
    current_stage: WorkflowStage
    total_transactions: int
    processed_transactions: int
    enhanced_transactions: int
    categorized_transactions: int
    duplicates_found: int
    duplicates_merged: int
    errors: List[str]
    started_at: datetime
    completed_at: Optional[datetime]
    success_rate: float


@dataclass
class WorkflowConfig:
    """Configuration for automated workflow"""
    enable_ai_enhancement: bool = True
    enable_auto_categorization: bool = True
    enable_duplicate_detection: bool = True
    enable_auto_merge_duplicates: bool = False
    ai_confidence_threshold: float = 0.7
    duplicate_confidence_threshold: float = 0.9
    auto_rule_creation: bool = True
    quality_threshold: float = 0.6


class AIWorkflowEngine:
    """Automated workflow engine for statement processing"""
    
    def __init__(self):
        self.ai_import_processor = get_ai_import_processor()
        self.ai_deduplicator = get_ai_deduplicator()
        self.category_matcher = get_category_matcher()
    
    async def process_import_workflow(
        self,
        import_run_id: str,
        account_id: str,
        config: WorkflowConfig = None
    ) -> WorkflowProgress:
        """Run complete automated workflow for an import"""
        
        if config is None:
            # Derive defaults from settings
            from .settings import load_settings
            s = load_settings()
            config = WorkflowConfig(
                enable_ai_enhancement=True,
                enable_auto_categorization=bool(s.get("ai_auto_categorize_on_import", True)),
                enable_duplicate_detection=True,
                enable_auto_merge_duplicates=False,
                ai_confidence_threshold=float(s.get("ai_auto_categorize_min_conf", 0.7)),
                duplicate_confidence_threshold=0.9,
                auto_rule_creation=bool(s.get("ai_auto_create_rules", True)),
                quality_threshold=0.6,
            )
        
        import uuid
        workflow_id = str(uuid.uuid4())
        
        conn = get_conn()
        
        # Initialize workflow tracking
        progress = WorkflowProgress(
            workflow_id=workflow_id,
            current_stage=WorkflowStage.IMPORT,
            total_transactions=0,
            processed_transactions=0,
            enhanced_transactions=0,
            categorized_transactions=0,
            duplicates_found=0,
            duplicates_merged=0,
            errors=[],
            started_at=datetime.now(UTC),
            completed_at=None,
            success_rate=0.0
        )
        
        try:
            # Stage 1: Get imported transactions
            progress.current_stage = WorkflowStage.IMPORT
            transactions = await self._get_import_transactions(import_run_id, account_id)
            progress.total_transactions = len(transactions)
            
            if not transactions:
                progress.errors.append("No transactions found in import")
                return await self._complete_workflow(progress)
            
            # Stage 2: AI Enhancement
            if config.enable_ai_enhancement:
                progress.current_stage = WorkflowStage.AI_ENHANCEMENT
                enhanced_count = await self._enhance_transactions_with_ai(
                    transactions, import_run_id, config
                )
                progress.enhanced_transactions = enhanced_count
                progress.processed_transactions = len(transactions)
            
            # Stage 3: Rule Application and Auto-Categorization
            if config.enable_auto_categorization:
                progress.current_stage = WorkflowStage.RULE_APPLICATION
                categorized_count = await self._apply_smart_categorization(
                    transactions, config
                )
                progress.categorized_transactions = categorized_count
            
            # Stage 4: Duplicate Detection
            if config.enable_duplicate_detection:
                progress.current_stage = WorkflowStage.DUPLICATE_DETECTION
                duplicates_info = await self._detect_and_handle_duplicates(
                    account_id, config
                )
                progress.duplicates_found = duplicates_info['found']
                progress.duplicates_merged = duplicates_info['merged']
            
            # Stage 5: Quality Validation
            progress.current_stage = WorkflowStage.QUALITY_VALIDATION
            quality_report = await self._validate_workflow_quality(
                transactions, config
            )
            progress.success_rate = quality_report['overall_score']
            
            if quality_report['overall_score'] < config.quality_threshold:
                progress.errors.append(f"Quality score {quality_report['overall_score']:.1%} below threshold {config.quality_threshold:.1%}")
            
            # Stage 6: Completion
            progress.current_stage = WorkflowStage.COMPLETION
            progress = await self._complete_workflow(progress)
            
            # Store workflow results
            await self._store_workflow_results(progress, config, quality_report)
            
        except Exception as e:
            progress.errors.append(f"Workflow error: {str(e)}")
            progress = await self._complete_workflow(progress)
        
        return progress
    
    async def _get_import_transactions(self, import_run_id: str, account_id: str) -> List[Dict[str, Any]]:
        """Get transactions from an import run"""
        conn = get_conn()
        
        transactions = conn.execute("""
            SELECT t.id, t.description_norm, t.amount, t.posted_at, t.account_id
            FROM [transaction] t
            JOIN import_run ir ON ir.id = ?
            WHERE t.account_id = ?
            AND t.created_at >= ir.started_at
            ORDER BY t.posted_at DESC
        """, [import_run_id, account_id]).fetchall()
        
        return [
            {
                'id': tx[0],
                'description': tx[1],
                'amount': tx[2],
                'posted_at': tx[3],
                'account_id': tx[4]
            }
            for tx in transactions
        ]
    
    async def _enhance_transactions_with_ai(
        self, 
        transactions: List[Dict[str, Any]], 
        import_run_id: str,
        config: WorkflowConfig
    ) -> int:
        """Enhance transactions with AI analysis"""
        
        # Use the existing AI import processor
        analysis = await self.ai_import_processor.process_import_batch(
            transactions, 
            transactions[0]['account_id'] if transactions else None,
            import_run_id
        )
        
        return analysis.ai_enhanced_count
    
    async def _apply_smart_categorization(
        self, 
        transactions: List[Dict[str, Any]], 
        config: WorkflowConfig
    ) -> int:
        """Apply smart categorization to transactions"""
        conn = get_conn()
        categorized_count = 0
        
        for tx in transactions:
            # Skip if already categorized
            existing_cat = conn.execute(
                "SELECT category_id FROM transaction_category WHERE tx_id = ?", 
                [tx['id']]
            ).fetchone()
            
            if existing_cat:
                categorized_count += 1
                continue
            
            # Provider-driven category suggestions mapped to existing categories
            from .ai import get_ai_service
            ai_service = get_ai_service()
            insights = await ai_service.analyze_transaction(tx['description'], float(tx['amount']))
            ai_suggestions = insights.category_suggestions
            # Provider mapping first
            from .db import get_conn as _get_conn
            conn = _get_conn()
            mapped_id = None
            mapped_name = None
            for s in ai_suggestions:
                src = s.category_name
                prov = insights.provider_name or None
                row = conn.execute("SELECT category_id FROM ai_category_mapping WHERE provider IS ? AND source_label = ?", [prov, src]).fetchone()
                if not row and prov is not None:
                    row = conn.execute("SELECT category_id FROM ai_category_mapping WHERE provider IS NULL AND source_label = ?", [src]).fetchone()
                if row:
                    mapped_id = row[0]
                    nrow = conn.execute("SELECT name FROM category WHERE id = ?", [mapped_id]).fetchone()
                    mapped_name = nrow[0] if nrow else None
                    break
            exact = self.category_matcher.find_exact_matches(ai_suggestions)
            fuzzy = self.category_matcher.find_fuzzy_matches(ai_suggestions)
            suggestions = []
            used_ids = set()
            from .ai_categories import SmartCategorySuggestion
            if mapped_id and mapped_name:
                suggestions.append(SmartCategorySuggestion(
                    category_id=mapped_id,
                    category_name=mapped_name,
                    confidence=insights.confidence_score,
                    reasoning='Mapped provider label',
                    match_type='mapped'
                ))
                used_ids.add(mapped_id)
            for m in exact + fuzzy:
                if m.category_id not in used_ids:
                    suggestions.append(SmartCategorySuggestion(
                        category_id=m.category_id,
                        category_name=m.category_name,
                        confidence=m.confidence,
                        reasoning=m.reasoning,
                        match_type=m.match_type
                    ))
                    used_ids.add(m.category_id)
            
            # Auto-apply if confidence is high enough
            if suggestions and suggestions[0].confidence >= config.ai_confidence_threshold:
                best_suggestion = suggestions[0]
                
                try:
                    # Apply category
                    conn.execute(
                        "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
                        [tx['id'], best_suggestion.category_id, "ai_workflow"]
                    )
                    categorized_count += 1
                    
                    # Log the action
                    import json
                    import uuid
                    conn.execute(
                        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [
                            str(uuid.uuid4()),
                            [transaction],
                            tx['id'],
                            "ai_auto_categorized",
                            json.dumps({
                                "category_id": best_suggestion.category_id,
                                "category_name": best_suggestion.category_name,
                                "confidence": best_suggestion.confidence,
                                "match_type": best_suggestion.match_type
                            }),
                            datetime.now(UTC),
                            "ai_workflow"
                        ]
                    )
                except Exception as e:
                    print(f"Error auto-categorizing transaction {tx['id']}: {e}")
        
        return categorized_count
    
    async def _detect_and_handle_duplicates(
        self, 
        account_id: str, 
        config: WorkflowConfig
    ) -> Dict[str, int]:
        """Detect and optionally merge duplicate transactions"""
        
        duplicates = self.ai_deduplicator.find_potential_duplicates(
            account_id=account_id,
            days_window=7,  # Check recent imports
            min_confidence=config.duplicate_confidence_threshold
        )
        
        merged_count = 0
        
        if config.enable_auto_merge_duplicates:
            for duplicate in duplicates:
                if duplicate.confidence >= config.duplicate_confidence_threshold:
                    try:
                        await self.ai_deduplicator.merge_duplicate_transactions(
                            keep_id=duplicate.transaction_id_1,
                            remove_id=duplicate.transaction_id_2,
                            user_confirmed=False  # Auto-merge based on high confidence
                        )
                        merged_count += 1
                    except Exception as e:
                        print(f"Error auto-merging duplicates: {e}")
        
        return {
            'found': len(duplicates),
            'merged': merged_count
        }
    
    async def _validate_workflow_quality(
        self, 
        transactions: List[Dict[str, Any]], 
        config: WorkflowConfig
    ) -> Dict[str, Any]:
        """Validate the quality of workflow results"""
        conn = get_conn()
        
        if not transactions:
            return {'overall_score': 0.0, 'metrics': {}}
        
        total_transactions = len(transactions)
        
        # Check AI enhancement coverage
        ai_enhanced = conn.execute("""
            SELECT COUNT(*) FROM [transaction] 
            WHERE id IN ({}) AND ai_merchant_name IS NOT NULL
        """.format(','.join(['?' for _ in transactions])), 
        [tx['id'] for tx in transactions]).fetchone()[0]
        
        # Check categorization coverage
        categorized = conn.execute("""
            SELECT COUNT(DISTINCT tc.tx_id) FROM transaction_category tc
            WHERE tc.tx_id IN ({})
        """.format(','.join(['?' for _ in transactions])), 
        [tx['id'] for tx in transactions]).fetchone()[0]
        
        # Check average AI confidence
        avg_confidence = conn.execute("""
            SELECT AVG(ai_confidence_score) FROM [transaction] 
            WHERE id IN ({}) AND ai_confidence_score IS NOT NULL
        """.format(','.join(['?' for _ in transactions])), 
        [tx['id'] for tx in transactions]).fetchone()[0] or 0.0
        
        # Calculate metrics
        ai_coverage = ai_enhanced / total_transactions
        categorization_coverage = categorized / total_transactions
        confidence_quality = avg_confidence
        
        # Overall score (weighted average)
        overall_score = (
            ai_coverage * 0.3 +
            categorization_coverage * 0.4 +
            confidence_quality * 0.3
        )
        
        return {
            'overall_score': overall_score,
            'metrics': {
                'ai_coverage': ai_coverage,
                'categorization_coverage': categorization_coverage,
                'average_confidence': confidence_quality,
                'total_transactions': total_transactions,
                'ai_enhanced': ai_enhanced,
                'categorized': categorized
            }
        }
    
    async def _complete_workflow(self, progress: WorkflowProgress) -> WorkflowProgress:
        """Mark workflow as completed"""
        progress.completed_at = datetime.now(UTC)
        progress.current_stage = WorkflowStage.COMPLETION
        return progress
    
    async def _store_workflow_results(
        self, 
        progress: WorkflowProgress, 
        config: WorkflowConfig,
        quality_report: Dict[str, Any]
    ):
        """Store workflow results in database"""
        conn = get_conn()
        
        import json
        
        conn.execute("""
            INSERT INTO ai_workflow_run (
                id, started_at, completed_at, total_transactions,
                enhanced_transactions, categorized_transactions,
                duplicates_found, duplicates_merged, success_rate,
                config_json, quality_report_json, errors_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            progress.workflow_id,
            progress.started_at,
            progress.completed_at,
            progress.total_transactions,
            progress.enhanced_transactions,
            progress.categorized_transactions,
            progress.duplicates_found,
            progress.duplicates_merged,
            progress.success_rate,
            json.dumps(config.__dict__),
            json.dumps(quality_report),
            json.dumps(progress.errors)
        ])


# Global instance
_workflow_engine = None

def get_workflow_engine() -> AIWorkflowEngine:
    """Get the global workflow engine instance"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = AIWorkflowEngine()
    return _workflow_engine
