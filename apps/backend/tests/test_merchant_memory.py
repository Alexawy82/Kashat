"""
Test suite for the merchant memory system

This test module validates:
- Merchant name extraction and normalization
- Learning from categorizations
- Memory-based predictions
- API endpoints for merchant memory management
"""

import pytest
import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch

from kashat.db import get_conn
from kashat.ai_smart_categorization import (
    get_smart_categorization_engine,
    learn_from_transaction_categorization,
    get_merchant_memory_statistics,
    extract_merchant_from_description
)


@pytest.fixture
def sample_transaction():
    """Create a sample transaction for testing"""
    conn = get_conn()
    
    # Create test account
    account_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO account (id, name, type) VALUES (?, ?, ?)",
        [account_id, "Test Account", "checking"]
    )
    
    # Create test transaction
    tx_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO "transaction" (id, account_id, posted_at, amount, description_norm, fingerprint, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [tx_id, account_id, "2024-01-01", -25.50, "SHEETZ #1234 PURCHASE", f"test-{tx_id}", datetime.now(UTC)])
    
    # Create test category
    category_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO category (id, name) VALUES (?, ?)",
        [category_id, "Gas & Automotive"]
    )
    
    yield {
        "transaction_id": tx_id,
        "account_id": account_id,
        "category_id": category_id,
        "description": "SHEETZ #1234 PURCHASE",
        "amount": -25.50
    }
    
    # Cleanup
    conn.execute("DELETE FROM merchant_category_mapping WHERE merchant_pattern = ?", ["Sheetz"])
    conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [tx_id])
    conn.execute('DELETE FROM "transaction" WHERE id = ?', [tx_id])
    conn.execute("DELETE FROM category WHERE id = ?", [category_id])
    conn.execute("DELETE FROM account WHERE id = ?", [account_id])


class TestMerchantExtraction:
    """Test merchant name extraction and normalization"""
    
    def test_extract_known_merchant(self):
        """Test extraction of known merchant from transaction description"""
        engine = get_smart_categorization_engine()
        
        test_cases = [
            ("SHEETZ #1234 PURCHASE 01/01/24", "Sheetz"),
            ("STARBUCKS STORE #5678", "Starbucks"),
            ("AMAZON.COM*123456789", "Amazon"),
            ("HARRIS TEETER #0123", "Harris Teeter"),
            ("AL-BASHA MARKET PURCHASE", "Al-Basha Market"),
            ("MCDONALD'S #0987", "McDonald's"),
            ("GOOGLE *SERVICES", "Google Services"),
            ("NETFLIX.COM MONTHLY", "Netflix"),
            ("SPOTIFY PREMIUM", "Spotify"),
        ]
        
        for description, expected in test_cases:
            result = engine._extract_merchant_name(description)
            assert result == expected, f"Expected {expected} for {description}, got {result}"
    
    def test_extract_unknown_merchant(self):
        """Test extraction of unknown merchant - should return cleaned description"""
        engine = get_smart_categorization_engine()
        
        test_cases = [
            ("UNKNOWN MERCHANT #123", "UNKNOWN MERCHANT"),
            ("CHECKCARD 1234 RANDOM STORE", "RANDOM STORE"),
            ("PURCHASE 5678 LOCAL CAFE", "LOCAL CAFE"),
            ("Some Random Store Name", "Some Random Store"),
        ]
        
        for description, expected in test_cases:
            result = engine._extract_merchant_name(description)
            assert result == expected, f"Expected {expected} for {description}, got {result}"
    
    def test_clean_transaction_artifacts(self):
        """Test removal of transaction artifacts"""
        engine = get_smart_categorization_engine()
        
        test_cases = [
            ("CHECKCARD 1234 STORE NAME", "STORE NAME"),
            ("PURCHASE 5678 MERCHANT", "MERCHANT"),  
            ("STORE #123 01/01/24", "STORE"),
            ("MERCHANT https://example.com", "MERCHANT"),
            ("STORE 555-123-4567", "STORE"),
        ]
        
        for description, expected in test_cases:
            result = engine._extract_merchant_name(description)
            assert result == expected, f"Expected {expected} for {description}, got {result}"
    
    def test_convenience_function(self):
        """Test the convenience function for merchant extraction"""
        result = extract_merchant_from_description("SHEETZ #1234 PURCHASE")
        assert result == "Sheetz"


class TestMerchantLearning:
    """Test learning from transaction categorizations"""
    
    @pytest.mark.asyncio
    async def test_learn_from_new_merchant(self, sample_transaction):
        """Test learning from a new merchant categorization"""
        tx_id = sample_transaction["transaction_id"]
        category_id = sample_transaction["category_id"]
        
        # Learn from categorization
        await learn_from_transaction_categorization(tx_id, category_id)
        
        # Verify the mapping was created
        conn = get_conn()
        result = conn.execute("""
            SELECT merchant_name, merchant_pattern, category_id, usage_count, confidence
            FROM merchant_category_mapping 
            WHERE merchant_pattern = ?
        """, ["Sheetz"]).fetchone()
        
        assert result is not None
        assert result[0] == "Sheetz"  # merchant_name
        assert result[1] == "Sheetz"  # merchant_pattern  
        assert result[2] == category_id
        assert result[3] == 1  # usage_count
        assert result[4] == 1.0  # confidence
    
    @pytest.mark.asyncio
    async def test_learn_from_existing_merchant(self, sample_transaction):
        """Test learning from an existing merchant (should increment usage)"""
        tx_id = sample_transaction["transaction_id"]
        category_id = sample_transaction["category_id"]
        
        # Learn twice from the same merchant
        await learn_from_transaction_categorization(tx_id, category_id)
        await learn_from_transaction_categorization(tx_id, category_id)
        
        # Verify usage count incremented and confidence increased
        conn = get_conn()
        result = conn.execute("""
            SELECT usage_count, confidence
            FROM merchant_category_mapping 
            WHERE merchant_pattern = ?
        """, ["Sheetz"]).fetchone()
        
        assert result is not None
        assert result[0] == 2  # usage_count
        assert result[1] > 1.0  # confidence should increase
    
    @pytest.mark.asyncio
    async def test_learn_nonexistent_transaction(self):
        """Test learning from non-existent transaction"""
        fake_tx_id = str(uuid.uuid4())
        fake_category_id = str(uuid.uuid4())
        
        # Should not raise exception, just return silently
        await learn_from_transaction_categorization(fake_tx_id, fake_category_id)
    
    @pytest.mark.asyncio
    async def test_convenience_function_learning(self, sample_transaction):
        """Test the convenience function for learning"""
        tx_id = sample_transaction["transaction_id"]
        category_id = sample_transaction["category_id"]
        
        await learn_from_transaction_categorization(tx_id, category_id)
        
        # Verify learning occurred
        conn = get_conn()
        result = conn.execute(
            "SELECT COUNT(*) FROM merchant_category_mapping WHERE merchant_pattern = ?",
            ["Sheetz"]
        ).fetchone()
        assert result[0] == 1


class TestMerchantPredictions:
    """Test predictions based on learned merchant mappings"""
    
    @pytest.mark.asyncio
    async def test_predict_learned_merchant(self, sample_transaction):
        """Test prediction for a learned merchant"""
        tx_id = sample_transaction["transaction_id"]
        category_id = sample_transaction["category_id"]
        account_id = sample_transaction["account_id"]
        
        # First learn from a categorization
        await learn_from_transaction_categorization(tx_id, category_id)
        
        # Now test prediction for same merchant
        engine = get_smart_categorization_engine()
        predictions = await engine.predict_category(
            transaction_id=str(uuid.uuid4()),
            description="SHEETZ #5678 DIFFERENT LOCATION",
            amount=-30.00,
            account_id=account_id
        )
        
        # Should have a high-confidence prediction from learned mapping
        assert len(predictions) > 0
        learned_prediction = next(
            (p for p in predictions if p.match_type == "learned_merchant"), 
            None
        )
        assert learned_prediction is not None
        assert learned_prediction.category_id == category_id
        assert learned_prediction.confidence > 0.9
        assert "Sheetz" in learned_prediction.reasoning
    
    @pytest.mark.asyncio
    async def test_no_prediction_for_unknown_merchant(self, sample_transaction):
        """Test no learned prediction for unknown merchant"""
        account_id = sample_transaction["account_id"]
        
        engine = get_smart_categorization_engine()
        predictions = await engine.predict_category(
            transaction_id=str(uuid.uuid4()),
            description="UNKNOWN MERCHANT #123",
            amount=-15.00,
            account_id=account_id
        )
        
        # Should not have any learned merchant predictions
        learned_predictions = [p for p in predictions if p.match_type == "learned_merchant"]
        assert len(learned_predictions) == 0
    
    @pytest.mark.asyncio
    async def test_learned_mapping_check(self, sample_transaction):
        """Test the learned mapping check method directly"""
        tx_id = sample_transaction["transaction_id"]
        category_id = sample_transaction["category_id"]
        
        # Learn from categorization
        await learn_from_transaction_categorization(tx_id, category_id)
        
        # Test the learned mapping check
        engine = get_smart_categorization_engine()
        prediction = await engine._check_learned_merchant_mapping("SHEETZ #9999 NEW LOCATION")
        
        assert prediction is not None
        assert prediction.category_id == category_id
        assert prediction.match_type == "learned_merchant"
        assert prediction.confidence > 0.9
        assert "Sheetz" in prediction.supporting_evidence[0]


class TestMerchantMemoryStats:
    """Test merchant memory statistics"""
    
    @pytest.mark.asyncio
    async def test_memory_stats_empty(self):
        """Test stats when no merchants learned"""
        stats = get_merchant_memory_statistics()
        
        assert "total_learned_merchants" in stats
        assert "top_merchants" in stats
        assert "recent_activity" in stats
        assert isinstance(stats["total_learned_merchants"], int)
        assert isinstance(stats["top_merchants"], list)
        assert isinstance(stats["recent_activity"], list)
    
    @pytest.mark.asyncio
    async def test_memory_stats_with_data(self, sample_transaction):
        """Test stats after learning from transactions"""
        tx_id = sample_transaction["transaction_id"]
        category_id = sample_transaction["category_id"]
        
        # Learn from categorization
        await learn_from_transaction_categorization(tx_id, category_id)
        
        stats = get_merchant_memory_statistics()
        
        assert stats["total_learned_merchants"] >= 1
        assert len(stats["top_merchants"]) >= 1
        
        # Check structure of top merchants
        if stats["top_merchants"]:
            merchant = stats["top_merchants"][0]
            assert "merchant_name" in merchant
            assert "category_id" in merchant
            assert "usage_count" in merchant
            assert "confidence" in merchant


class TestMerchantRules:
    """Test comprehensive merchant category rules"""
    
    def test_merchant_category_rules(self):
        """Test the comprehensive merchant category rules"""
        engine = get_smart_categorization_engine()
        rules = engine._get_merchant_category_rules()
        
        # Test gas stations
        assert rules["sheetz"] == "Gas & Automotive"
        assert rules["shell"] == "Gas & Automotive"
        assert rules["exxon"] == "Gas & Automotive"
        
        # Test food & dining
        assert rules["starbucks"] == "Coffee Shops"
        assert rules["mcdonald"] == "Fast Food"
        assert rules["harris teeter"] == "Grocery"
        
        # Test subscriptions
        assert rules["netflix"] == "Entertainment Subscriptions"
        assert rules["spotify"] == "Entertainment Subscriptions"
        
        # Test transfers
        assert rules["zelle"] == "Personal Transfers"
        assert rules["venmo"] == "Personal Transfers"


class TestDatabaseIntegration:
    """Test database integration for merchant memory"""
    
    def test_merchant_mapping_table_exists(self):
        """Test that the merchant mapping table exists and has correct structure"""
        conn = get_conn()
        
        # Test table exists
        result = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='merchant_category_mapping'
        """).fetchone()
        
        if not result:
            # Try DuckDB syntax
            try:
                conn.execute("SELECT 1 FROM merchant_category_mapping LIMIT 1")
            except Exception:
                pytest.fail("merchant_category_mapping table does not exist")
    
    def test_merchant_mapping_schema(self):
        """Test that the merchant mapping table has the correct schema"""
        conn = get_conn()
        
        # Test we can insert and retrieve a mapping
        test_id = str(uuid.uuid4())
        test_merchant = f"test_merchant_{uuid.uuid4().hex[:8]}"
        test_category = str(uuid.uuid4())
        
        try:
            conn.execute("""
                INSERT INTO merchant_category_mapping 
                (id, merchant_name, merchant_pattern, category_id, confidence, usage_count, last_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                test_id, test_merchant, test_merchant, test_category,
                0.8, 1, datetime.now(UTC), datetime.now(UTC)
            ])
            
            result = conn.execute(
                "SELECT merchant_name, confidence, usage_count FROM merchant_category_mapping WHERE id = ?",
                [test_id]
            ).fetchone()
            
            assert result is not None
            assert result[0] == test_merchant
            assert result[1] == 0.8
            assert result[2] == 1
            
        finally:
            # Cleanup
            conn.execute("DELETE FROM merchant_category_mapping WHERE id = ?", [test_id])


class TestErrorHandling:
    """Test error handling in merchant memory system"""
    
    @pytest.mark.asyncio
    async def test_learning_with_invalid_transaction(self):
        """Test learning gracefully handles invalid transaction ID"""
        # Should not raise exception
        await learn_from_transaction_categorization("invalid-id", "invalid-category")
    
    def test_stats_with_db_error(self):
        """Test stats function handles database errors gracefully"""
        with patch('kashat.ai_smart_categorization.get_conn') as mock_conn:
            mock_conn.side_effect = Exception("Database error")
            
            stats = get_merchant_memory_statistics()
            
            # Should return default empty stats
            assert stats["total_learned_merchants"] == 0
            assert stats["top_merchants"] == []
            assert stats["recent_activity"] == []
    
    def test_merchant_extraction_with_empty_description(self):
        """Test merchant extraction with empty or invalid descriptions"""
        engine = get_smart_categorization_engine()
        
        test_cases = ["", "   ", None]
        
        for description in test_cases:
            try:
                result = engine._extract_merchant_name(description or "")
                # Should return empty string or handle gracefully
                assert isinstance(result, str)
            except Exception:
                # Should not raise exceptions
                pytest.fail(f"Merchant extraction failed for: {description}")


# Integration test combining multiple features
@pytest.mark.asyncio
async def test_end_to_end_merchant_learning_flow(sample_transaction):
    """Test complete flow from transaction to learning to prediction"""
    tx_id = sample_transaction["transaction_id"]
    category_id = sample_transaction["category_id"]
    account_id = sample_transaction["account_id"]
    
    # Step 1: Learn from categorization
    await learn_from_transaction_categorization(tx_id, category_id)
    
    # Step 2: Verify learning occurred
    stats = get_merchant_memory_statistics()
    assert stats["total_learned_merchants"] >= 1
    
    # Step 3: Test prediction on similar transaction
    engine = get_smart_categorization_engine()
    predictions = await engine.predict_category(
        transaction_id=str(uuid.uuid4()),
        description="SHEETZ #9999 ANOTHER LOCATION",
        amount=-40.00,
        account_id=account_id
    )
    
    # Step 4: Verify high-confidence prediction
    learned_pred = next(
        (p for p in predictions if p.match_type == "learned_merchant"),
        None
    )
    assert learned_pred is not None
    assert learned_pred.category_id == category_id
    assert learned_pred.confidence > 0.9
    
    # Step 5: Learn from another transaction (should increment usage)
    tx_id2 = str(uuid.uuid4())
    conn = get_conn()
    conn.execute("""
        INSERT INTO "transaction" (id, account_id, posted_at, amount, description_norm, fingerprint, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [tx_id2, account_id, "2024-01-02", -35.00, "SHEETZ #5555 DIFFERENT STORE", f"test-{tx_id2}", datetime.now(UTC)])
    
    try:
        await learn_from_transaction_categorization(tx_id2, category_id)
        
        # Step 6: Verify usage count increased
        result = conn.execute("""
            SELECT usage_count, confidence
            FROM merchant_category_mapping 
            WHERE merchant_pattern = ?
        """, ["Sheetz"]).fetchone()
        
        assert result[0] == 2  # usage_count should be 2
        assert result[1] > 1.0  # confidence should increase
        
    finally:
        # Cleanup second transaction
        conn.execute('DELETE FROM "transaction" WHERE id = ?', [tx_id2])


if __name__ == "__main__":
    pytest.main([__file__])