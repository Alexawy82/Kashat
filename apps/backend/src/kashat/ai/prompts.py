"""
AI Prompts Module - All prompt templates

This module contains all AI prompt templates used across the application:
- Categorization prompts
- Merchant intelligence prompts
- Transfer analysis prompts
- PDF extraction prompts
- Quality analysis prompts

Prompts are defined as constants for consistency and easy modification.
"""

# Transaction categorization prompt
CATEGORIZATION_PROMPT = """Analyze this financial transaction and suggest categories.

Transaction:
- Description: {description}
- Amount: ${amount:.2f}
- Date: {date}

Provide:
1. Category name (standard category like Food & Dining, Shopping, etc.)
2. Confidence score (0.0-1.0)
3. Brief reasoning

Format as JSON:
{{
    "suggestions": [
        {{"category": "...", "confidence": 0.9, "reasoning": "..."}}
    ]
}}"""

# Merchant normalization prompt
MERCHANT_PROMPT = """Extract and normalize the merchant name from this transaction description:

Description: {description}

Return the clean merchant name (e.g., "Amazon" not "AMAZON.COM*AMZN MKTP US").

Format as JSON:
{{
    "merchant_name": "...",
    "merchant_type": "...",
    "confidence": 0.9
}}"""

# Transfer detection prompt
TRANSFER_PROMPT = """Analyze if this transaction is a transfer between accounts:

Transaction 1:
- Description: {desc1}
- Amount: ${amount1:.2f}
- Date: {date1}
- Account: {account1}

Transaction 2:
- Description: {desc2}
- Amount: ${amount2:.2f}
- Date: {date2}
- Account: {account2}

Is this likely a transfer between the user's own accounts?

Format as JSON:
{{
    "is_transfer": true/false,
    "confidence": 0.9,
    "reasoning": "..."
}}"""

# PDF extraction prompt
PDF_EXTRACTION_PROMPT = """Extract transaction data from this bank statement.

For each transaction, extract:
- Date (YYYY-MM-DD format)
- Description
- Amount (positive for deposits, negative for withdrawals)
- Balance (if available)

Return as JSON array:
{{
    "transactions": [
        {{"date": "2024-01-15", "description": "...", "amount": -45.99, "balance": 1234.56}}
    ],
    "account_info": {{
        "account_number": "...",
        "statement_period": "..."
    }}
}}"""

# Quality analysis prompt
QUALITY_PROMPT = """Analyze the quality of this transaction data:

Transactions sample:
{transactions_sample}

Evaluate:
1. Data completeness (missing fields)
2. Format consistency
3. Potential duplicates
4. Anomalies or errors

Format as JSON:
{{
    "quality_score": 0.85,
    "issues": [
        {{"type": "missing_field", "field": "...", "count": 5}},
        {{"type": "format_inconsistency", "description": "..."}}
    ],
    "recommendations": ["..."]
}}"""

# Recurring detection prompt
RECURRING_PROMPT = """Analyze if these transactions form a recurring pattern:

Transactions:
{transactions_json}

Identify:
1. Is this a recurring expense/income?
2. What is the frequency (daily, weekly, monthly, yearly)?
3. Expected next date
4. Any price changes detected?

Format as JSON:
{{
    "is_recurring": true/false,
    "frequency": "monthly",
    "confidence": 0.9,
    "expected_amount": 99.99,
    "next_date": "2024-03-15",
    "price_trend": "stable/increasing/decreasing"
}}"""

__all__ = [
    "CATEGORIZATION_PROMPT",
    "MERCHANT_PROMPT",
    "TRANSFER_PROMPT",
    "PDF_EXTRACTION_PROMPT",
    "QUALITY_PROMPT",
    "RECURRING_PROMPT",
]
