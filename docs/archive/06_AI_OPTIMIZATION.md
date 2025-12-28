# LedgerLoop AI Layer Optimization

## YOUR ROLE

You are an **AI/ML Engineer** specializing in LLM integration and financial applications. Your task is to audit, fix, and optimize LedgerLoop's AI layer to achieve maximum categorization accuracy with minimal cost.

## CONTEXT

LedgerLoop has an extensive AI layer (16+ files) that is **underutilized**. Key findings from the architecture analysis:

1. **Single LLM prompt** handles all categorization (not optimized)
2. **Merchant memory system** exists but not fully utilized
3. **Batch processing** not implemented (one LLM call per transaction)
4. **No context** from user history in prompts
5. **Auto-escalation** (local → LM Studio → OpenAI) exists but may not be working
6. **Many AI features** disabled or not wired up

## YOUR OBJECTIVES

### Objective 1: Verify AI Provider Chain Works
```bash
# Test the ping endpoint
curl http://localhost:8000/api/ai/status

# Check current provider
curl http://localhost:8000/api/settings | jq '.ai_provider'

# Test LM Studio connectivity (if configured)
curl http://127.0.0.1:1234/v1/models

# Test actual categorization
curl -X POST http://localhost:8000/api/ai/analyze/transaction/{any_transaction_id}
```

**Fix if needed**: Ensure the provider chain actually works and escalates properly.

### Objective 2: Optimize the Main Categorization Prompt

Location: `apps/backend/src/ledgerloop/ai.py` (around line 355)

Current prompt is basic. Improve it to:

1. **Add user context** (top categories, recent patterns)
2. **Add transaction context** (day of week, similar past transactions)
3. **Better merchant extraction** (handle PayPal*, SQ*, etc.)
4. **Structured output** (use response_format if OpenAI)

**Create improved prompt** that:
- Extracts merchant name more accurately
- Considers amount patterns ($5.99 = subscription, $47.82 = restaurant tip)
- Uses historical data for context
- Handles edge cases (refunds, transfers, etc.)

### Objective 3: Enable Merchant Memory Learning

Location: `apps/backend/src/ledgerloop/ai_smart_categorization.py`

The merchant memory system (`merchant_category_mapping` table) should:
1. Learn every time a user categorizes a transaction
2. Learn when AI categorization is confirmed (not rejected)
3. Use learned mappings BEFORE calling LLM

**Verify the flow**:
```python
# When user categorizes:
learn_from_categorization(transaction_id, category_id)

# When AI suggests and gets applied:
learn_from_transaction_categorization(transaction_id, category_id)
```

**Check the table**:
```sql
SELECT * FROM merchant_category_mapping ORDER BY usage_count DESC LIMIT 20;
```

### Objective 4: Implement Batch Processing

Current: One LLM call per transaction (expensive, slow)
Better: Batch 5-10 transactions per call

**Create or fix** batch processing in `ai.py`:

```python
async def batch_categorize_transactions(transactions: List[Tuple[str, str, float]]) -> List[TransactionInsights]:
    """
    Batch categorize transactions in a single LLM call.
    
    Args:
        transactions: List of (id, description, amount) tuples
    """
    # Group similar transactions
    # Build batch prompt
    # Single LLM call
    # Parse results
    # Return insights
```

### Objective 5: Wire Up Auto-Categorization on Import

Location: `apps/backend/src/ledgerloop/ingest_pdf.py` or `ingest_csv.py`

Ensure that when transactions are imported:
1. Each transaction gets AI analyzed
2. High-confidence categories get auto-applied
3. Low-confidence ones get stored as suggestions

**Check settings**:
```python
# Should be enabled
"ai_auto_categorize_on_import": True,
"ai_auto_categorize_min_conf": 0.7,
```

### Objective 6: Enable and Test Analytics AI

Test all AI analytics endpoints:
```bash
# Dashboard summary
curl http://localhost:8000/api/analytics/ai/dashboard-summary

# Spending patterns
curl http://localhost:8000/api/analytics/ai/spending-patterns

# Trends
curl http://localhost:8000/api/analytics/ai/trends

# Predictive insights
curl http://localhost:8000/api/analytics/predictive/insights

# Cash flow forecast
curl http://localhost:8000/api/analytics/predictive/cashflow-forecast

# Anomaly detection
curl http://localhost:8000/api/ai/duplicates/detect
```

Fix any 404s or 500s.

### Objective 7: Create AI Configuration Endpoint

Allow runtime configuration of AI settings:
```python
# Endpoint: PUT /api/settings/ai
{
    "ai_provider": "auto",
    "ai_auto_categorize_on_import": true,
    "ai_auto_categorize_min_conf": 0.7,
    "ai_debug": true
}
```

---

## FILES TO EXAMINE

Priority order:

1. `apps/backend/src/ledgerloop/ai.py` - Main AI service
2. `apps/backend/src/ledgerloop/ai_enhanced_categorization.py` - Pattern matching
3. `apps/backend/src/ledgerloop/ai_smart_categorization.py` - ML categorization
4. `apps/backend/src/ledgerloop/api/routes/ai.py` - API endpoints
5. `apps/backend/src/ledgerloop/settings.py` - Configuration
6. `apps/backend/src/ledgerloop/ai_analytics.py` - Analytics
7. `apps/backend/src/ledgerloop/ai_insights.py` - Insights
8. `apps/backend/src/ledgerloop/ai_forecasting.py` - Forecasting
9. `apps/backend/src/ledgerloop/ingest_pdf.py` - Import integration

---

## TESTING PROTOCOL

After each change:

1. **Restart backend**:
   ```bash
   docker-compose restart ledgerloop-backend
   ```

2. **Check health**:
   ```bash
   curl http://localhost:8000/api/health
   curl http://localhost:8000/api/ai/stats
   ```

3. **Test categorization**:
   ```bash
   # Get an uncategorized transaction
   TX_ID=$(curl -s "http://localhost:8000/api/transactions?has_category=false&limit=1" | jq -r '.data[0].id')
   
   # Analyze it
   curl -X POST "http://localhost:8000/api/ai/analyze/transaction/$TX_ID" | jq .
   ```

4. **Check logs**:
   ```bash
   docker logs ledgerloop-backend --tail 50
   ```

---

## DELIVERABLES

### 1. `AI_OPTIMIZATION_LOG.md`
Document every change made:
- File modified
- What was changed
- Why
- Test results

### 2. `AI_PROMPT_V2.md`
The improved categorization prompt with:
- User context integration
- Better merchant extraction
- Batch support design

### 3. `AI_ENDPOINTS_VERIFIED.md`
Status of every AI endpoint:
- URL
- Working: Yes/No
- Response sample or error

### 4. Code Changes
Apply fixes directly to the codebase.

---

## RULES

1. **Test after every change** - Don't break what works
2. **Preserve backward compatibility** - Existing API contracts must work
3. **Log everything** - Use LEDGERLOOP_AI_DEBUG=true
4. **Don't remove features** - Fix them, don't delete
5. **Consider cost** - Batch calls, cache responses
6. **Focus on accuracy** - Goal is 90%+ categorization accuracy

---

## SUCCESS CRITERIA

- [ ] AI provider chain works (local → LM Studio → OpenAI)
- [ ] Categorization prompt improved with context
- [ ] Merchant memory is learning from user actions
- [ ] Batch processing implemented (5+ transactions per call)
- [ ] Auto-categorization works on import
- [ ] All AI analytics endpoints return data
- [ ] AI debug logging shows clear request/response

---

## BEGIN

Start by checking current AI status:

```bash
# 1. Check what's configured
curl http://localhost:8000/api/settings | jq '{ai_provider, ai_auto_categorize_on_import, ai_auto_categorize_min_conf}'

# 2. Check AI stats
curl http://localhost:8000/api/ai/stats | jq .

# 3. Test the ping
curl http://localhost:8000/api/ai/status 2>/dev/null || curl http://localhost:8000/api/health

# 4. Check merchant memory
# (via direct DB query if possible)
```

Then systematically work through each objective.

**GO.**
