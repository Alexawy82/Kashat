# LedgerLoop AI Architecture Analysis

## Executive Summary

LedgerLoop has a **comprehensive but underutilized AI layer** with 16+ AI-related files. The architecture supports multiple providers (local heuristics, LM Studio, OpenAI) with auto-escalation, but several capabilities are **not fully wired up or optimized**.

---

## AI Files Inventory

| File | Purpose | Status |
|------|---------|--------|
| `ai.py` | Core AI service - provider management, transaction analysis | ✅ Active |
| `ai_enhanced_categorization.py` | Pattern-based enhanced categorization | ✅ Active |
| `ai_smart_categorization.py` | ML-based categorization with learning | ⚠️ Partial |
| `ai_analytics.py` | Spending patterns, trends, anomalies | ✅ Active |
| `ai_insights.py` | Personalized financial insights | ✅ Active |
| `ai_forecasting.py` | Cash flow predictions | ✅ Active |
| `ai_categories.py` | Category matching logic | ✅ Active |
| `ai_category_acceptance.py` | Category approval workflow | ❓ Unclear |
| `ai_dedup.py` | Duplicate detection | ✅ Active |
| `ai_intelligent_dedup.py` | Enhanced deduplication | ❓ Unclear |
| `ai_data_quality.py` | Data quality checks | ❓ Unclear |
| `ai_alerts.py` | Alert generation | ❓ Unclear |
| `ai_import.py` | AI-enhanced import | ❓ Unclear |
| `ai_integration.py` | Transaction processor coordination | ⚠️ Partial |
| `ai_workflow.py` | Workflow orchestration | ❓ Unclear |
| `ai_auto_categorization.py` | Auto-categorization logic | ⚠️ Partial |
| `realtime_ai_analytics.py` | Real-time AI analytics | ❓ Unclear |

---

## Current AI Provider Architecture

### Provider Hierarchy (from `ai.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                        AIService                                 │
│  provider: 'local' | 'lmstudio' | 'openai' | 'auto'             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │LocalAIService│    │OpenAIService    │    │OpenAIService    │  │
│  │(heuristics) │    │(LM Studio)      │    │(OpenAI Cloud)   │  │
│  └─────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                  │
│  Auto Escalation: LM Studio → OpenAI → Local (if conf < 0.7)    │
└─────────────────────────────────────────────────────────────────┘
```

### Configuration (`settings.py`)

```python
"ai_provider": "local",              # local|lmstudio|openai|auto
"ai_openai_base_url": "",            # For proxies/Azure
"ai_lmstudio_base_url": "http://127.0.0.1:1234/v1",
"ai_model_categorize": "",           # Override per task
"ai_auto_categorize_on_import": True,
"ai_auto_categorize_min_conf": 0.7,
```

### Environment Variables

```bash
LEDGERLOOP_AI_PROVIDER=auto|local|lmstudio|openai
LEDGERLOOP_AI_LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LEDGERLOOP_AI_LMSTUDIO_API_KEY=lm-studio
LEDGERLOOP_AI_LMSTUDIO_MODEL=qwen/qwen3-vl-4b
LEDGERLOOP_AI_OPENAI_BASE_URL=
LEDGERLOOP_AI_OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=
LEDGERLOOP_AI_TEMPERATURE=0.1
LEDGERLOOP_AI_CONFIDENCE_THRESHOLD=0.7
LEDGERLOOP_AI_MAX_CONCURRENCY=2
LEDGERLOOP_AI_TIMEOUT_SEC=10
LEDGERLOOP_AI_DEBUG=false
LEDGERLOOP_AI_BATCH_SIZE=50
```

---

## The Main AI Prompt (from `ai.py`)

This is the **ONLY LLM prompt** currently in use for categorization:

```python
prompt = f"""Categorize this bank transaction.

AVAILABLE CATEGORIES: {cat_list}

MERCHANT HINTS (use these to help categorize):
- Gas stations: Sheetz, Shell, Exxon, Chevron, BP → Gas & Automotive
- Grocery: Harris Teeter, Walmart Grocery, Kroger, Safeway, Aldi, Al-Basha → Grocery
- Restaurants/Food: Starbucks, McDonald's, Chipotle, DoorDash, Wingstop → Food & Dining
- Streaming: Netflix, Spotify, YouTube, Hulu, Plex → Entertainment
- Tech/Software: OpenAI, Microsoft, Google, Apple, Canva, Replit, Leonardo.ai → Technology or Software
- Mortgage: Carrington, loan payments → Mortgage Payment
- Insurance: Geico, Progressive, State Farm → Insurance
- Utilities: Duke Energy, Google Fiber, Spectrum → Bills & Utilities
- Home Services: pest control, cleaning, lawn care, plumber → Professional Services
- Loans: Avant, Best Buy, Citi Card, auto payments → Financial Services

RULES:
- For credits (positive amounts): check if Income, Internal Transfer, or Zelle
- "zelle from/to" = Zelle
- "transfer from sav/chk" = Internal Transfer
- Payroll, salary, direct deposit = Income
- For debits: match merchant to category using hints above

Transaction: {description}
Amount: ${amount:.2f}

Respond with ONLY valid JSON:
{{"merchant_name": "extracted merchant", "category": "one category from list", "confidence": 0.8, "reasoning": "brief reason"}}"""
```

### Issues with Current Prompt

1. **Single-purpose**: Only handles categorization, not merchant extraction or anomaly detection
2. **Hardcoded hints**: Merchant hints are static, not learned
3. **No context**: Doesn't include historical patterns or user preferences
4. **Simple JSON output**: Doesn't leverage structured outputs or function calling
5. **No batch support**: Sends one transaction at a time

---

## Data Flow Analysis

### Import → Categorization Flow

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ PDF Import  │────▶│ Parse & Normalize │────▶│ Store in DB     │
│ (ingest_pdf)│     │ (normalization)   │     │ (transactions)  │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                       │
                                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI Categorization Pipeline                    │
├─────────────────────────────────────────────────────────────────┤
│  1. Check merchant_category_mapping (learned memory)            │
│  2. Try LocalAIService (pattern matching + keywords)            │
│  3. If provider=auto/lmstudio/openai, call LLM                  │
│  4. Store suggestions in ai_category_suggestions JSON           │
│  5. If auto_categorize_on_import=True & conf > 0.7, apply       │
└─────────────────────────────────────────────────────────────────┘
```

### Where AI is Called (API Routes)

| Endpoint | AI Function | Purpose |
|----------|-------------|---------|
| `POST /api/ai/analyze/transaction/{id}` | `ai_service.analyze_transaction()` | Single transaction analysis |
| `POST /api/ai/analyze/bulk` | `batch_analyze_transactions()` | Bulk analysis (background) |
| `GET /api/ai/suggestions/categories/{id}` | `analyze_transaction()` | Get category suggestions |
| `GET /api/ai/suggestions/smart-categories/{id}` | Multiple AI systems | Enhanced suggestions |
| `POST /api/ai/enhance/uncategorized` | Bulk enhancement | Process all uncategorized |
| `GET /api/ai/duplicates/detect` | `ai_deduplicator` | Find duplicates |
| `POST /api/ai/normalize/merchant` | `analyze_transaction()` | Merchant normalization |
| `GET /api/analytics/ai/*` | `ai_analytics` | AI-powered analytics |
| `GET /api/analytics/predictive/*` | `ai_forecasting` | Predictions |

---

## Underutilized Capabilities

### 1. Merchant Memory System (ai_smart_categorization.py)
- **Has**: `merchant_category_mapping` table, `learn_from_categorization()` function
- **Problem**: Only called when user manually applies a category
- **Not Using**: Automatic learning from confirmed categorizations

### 2. Smart Categorization Engine
- **Has**: ML-based prediction, confidence scoring, auto-creation
- **Problem**: Complex but not fully integrated
- **Not Using**: The full `predict_category()` with learned patterns

### 3. AI Analytics Engine (ai_analytics.py)
- **Has**: Spending patterns, trend detection, anomaly detection
- **Problem**: Endpoints exist but may not be called from frontend
- **Not Using**: Real-time anomaly alerts

### 4. AI Insights Engine (ai_insights.py)
- **Has**: Personalized insights, financial health scoring
- **Problem**: Full capabilities not exposed
- **Not Using**: Spending persona analysis, forecast warnings

### 5. AI Forecasting (ai_forecasting.py)
- **Has**: Cash flow projection, predictive models
- **Problem**: Separate from main dashboard
- **Not Using**: Integrated predictions in analytics

### 6. Real-time AI (realtime_ai_analytics.py, realtime_integration.py)
- **Has**: WebSocket event system, real-time processing
- **Problem**: `realtime_enabled: False` by default
- **Not Using**: Live categorization notifications

### 7. Duplicate Detection (ai_dedup.py, ai_intelligent_dedup.py)
- **Has**: Similarity scoring, duplicate detection
- **Problem**: Not run automatically on import
- **Not Using**: Auto-flagging during import

### 8. Data Quality (ai_data_quality.py)
- **Has**: Data quality checks
- **Problem**: Not integrated into import flow
- **Not Using**: Import-time validation

---

## The LLM Call Chain

```
User imports PDF
      │
      ▼
parse_pdf() → transactions extracted
      │
      ▼
FOR EACH transaction:
      │
      ├─── LocalAIService.normalize_merchant()     ← Pattern matching only
      │         └── Returns: MerchantInfo
      │
      ├─── LocalAIService.suggest_categories()     ← Keyword matching
      │         └── Returns: List[CategorySuggestion]
      │
      └─── IF provider != 'local':
               │
               OpenAIService.analyze_transaction()  ← ACTUAL LLM CALL
                    │
                    ├── Build prompt with categories + hints
                    ├── Call chat.completions.create()
                    ├── Parse JSON response
                    └── Returns: TransactionInsights
```

### Current LLM Usage Stats

- **Calls per transaction**: 1 (for categorization)
- **Tokens per call**: ~400-500 input, ~50-100 output
- **Batch support**: No (one call per transaction)
- **Caching**: No (no response caching)
- **Tools/Functions**: No (plain JSON output)

---

## Gaps & Improvement Opportunities

### 1. **No Multi-Transaction Context**
- Current: Each transaction analyzed independently
- Better: Send batch of 5-10 similar transactions for pattern recognition

### 2. **No User Pattern Learning**
- Current: Static merchant hints in prompt
- Better: Include user's historical categorization patterns in prompt

### 3. **No Structured Outputs**
- Current: Parse JSON from text response
- Better: Use OpenAI's `response_format` or function calling

### 4. **No Prompt Versioning**
- Current: Hardcoded prompt in code
- Better: Configurable prompts, A/B testing

### 5. **No Semantic Search**
- Current: Keyword/pattern matching
- Better: Embeddings for semantic similarity

### 6. **No Explanation Display**
- Current: `reasoning` field stored but not shown
- Better: Show AI reasoning in UI

### 7. **No Feedback Loop**
- Current: Learning only on manual categorization
- Better: Track auto-categorization accuracy, retrain

### 8. **No Cost Tracking**
- Current: No token/cost monitoring
- Better: Track API costs per import

---

## Recommended Architecture Changes

### Phase 1: Enable What Exists
```bash
# Enable better AI provider
LEDGERLOOP_AI_PROVIDER=auto

# Enable auto-categorization
ai_auto_categorize_on_import=True
ai_auto_categorize_min_conf=0.7

# Enable merchant learning
# (Already exists, just needs UI integration)
```

### Phase 2: Improve the Prompt
```python
# Enhanced prompt with context
prompt = f"""You are a personal finance AI categorizing bank transactions.

USER CONTEXT:
- Common merchants: {user_top_merchants}
- Spending patterns: {user_spending_summary}
- Recent categories used: {recent_categories}

TRANSACTION:
- Description: {description}
- Amount: ${amount:.2f}
- Date: {date}
- Similar past transactions: {similar_transactions}

AVAILABLE CATEGORIES:
{categories_with_descriptions}

Instructions:
1. Extract the merchant name
2. Determine if this is income, expense, or transfer
3. Categorize based on merchant and context
4. Flag any anomalies

Respond with JSON:
{{
  "merchant": "normalized name",
  "category": "category from list",
  "is_transfer": true/false,
  "is_recurring": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "explanation",
  "anomaly_flags": []
}}"""
```

### Phase 3: Batch Processing
```python
# Process transactions in smart batches
async def batch_categorize(transactions: List[Transaction]):
    # Group by similar merchant patterns
    groups = cluster_by_merchant(transactions)
    
    for group in groups:
        # Send batch to LLM with context
        prompt = build_batch_prompt(group)
        response = await llm.complete(prompt)
        
        # Apply categories
        for tx, category in zip(group, response.categories):
            apply_category(tx, category)
```

### Phase 4: Enable Real-time
```python
# Enable WebSocket notifications
settings["realtime_enabled"] = True

# On categorization:
await emit_event(EventType.CATEGORIZATION_COMPLETE, {
    "transaction_id": tx_id,
    "category": category_name,
    "confidence": confidence
})
```

---

## API Endpoints Summary

### Currently Working
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ai/stats` | GET | AI processing statistics |
| `/api/ai/analyze/transaction/{id}` | POST | Analyze single transaction |
| `/api/ai/suggestions/categories/{id}` | GET | Get category suggestions |
| `/api/ai/suggestions/smart-categories/{id}` | GET | Enhanced suggestions |
| `/api/ai/enhance/uncategorized` | POST | Bulk enhance uncategorized |
| `/api/ai/bulk-jobs` | GET | List bulk processing jobs |
| `/api/ai/duplicates/detect` | GET | Detect duplicates |

### Need Verification
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/ai/dashboard-summary` | GET | AI-powered summary |
| `/api/analytics/ai/trends` | GET | AI trend analysis |
| `/api/analytics/predictive/insights` | GET | Predictive insights |
| `/api/analytics/predictive/cashflow-forecast` | GET | Cash flow forecast |

---

## Quick Wins (Low Effort, High Impact)

1. **Set `ai_provider=auto`** - Enable LLM escalation
2. **Verify merchant memory is learning** - Check `merchant_category_mapping` table
3. **Display AI reasoning in UI** - Show why AI suggested category
4. **Enable auto-categorize on import** - Reduce manual work
5. **Add AI stats to dashboard** - Show categorization accuracy

## Medium Term

1. **Batch categorization** - Process 10 transactions per LLM call
2. **Improve prompt with context** - Add user patterns
3. **Cache LLM responses** - For identical merchants
4. **Add feedback UI** - Let user confirm/reject AI suggestions

## Long Term

1. **Fine-tune local model** - Train on user's data
2. **Embeddings for similarity** - Better merchant matching
3. **Real-time categorization** - Enable WebSocket notifications
4. **Cost tracking dashboard** - Monitor AI API spend
