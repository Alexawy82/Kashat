"""
Test suite for merchant memory API endpoints

This module tests all the merchant memory related API endpoints:
- Learning from categorizations
- Getting merchant memory stats
- Extracting merchant names
- Managing learned mappings
"""

import pytest
import uuid
import json
from datetime import datetime, UTC

from kashat.db import get_conn


# Uses authenticated_client from conftest.py


@pytest.fixture
def sample_data():
    """Create sample data for testing"""
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
        INSERT INTO transaction (id, account_id, posted_at, amount, description_norm, fingerprint, created_at)
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
        "description": "SHEETZ #1234 PURCHASE"
    }
    
    # Cleanup
    conn.execute("DELETE FROM merchant_category_mapping WHERE merchant_pattern = ?", ["Sheetz"])
    conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [tx_id])
    conn.execute("DELETE FROM transaction WHERE id = ?", [tx_id])
    conn.execute("DELETE FROM category WHERE id = ?", [category_id])
    conn.execute("DELETE FROM account WHERE id = ?", [account_id])


class TestMerchantMemoryAPIEndpoints:
    """Test merchant memory API endpoints"""
    
    def test_learn_from_categorization_success(self, authenticated_client, sample_data):
        """Test successful learning from categorization"""
        tx_id = sample_data["transaction_id"]
        category_id = sample_data["category_id"]
        
        response = authenticated_client.post(
            "/ai/merchant-memory/learn",
            json={
                "transaction_id": tx_id,
                "category_id": category_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["transaction_id"] == tx_id
        assert data["category_id"] == category_id
        assert data["category_name"] == "Gas & Automotive"
        assert data["merchant_learned"] == "Sheetz"
        assert "Sheetz" in data["message"]
    
    def test_learn_from_categorization_invalid_transaction(self, authenticated_client):
        """Test learning with invalid transaction ID"""
        fake_tx_id = str(uuid.uuid4())
        fake_category_id = str(uuid.uuid4())
        
        response = authenticated_client.post(
            "/ai/merchant-memory/learn",
            json={
                "transaction_id": fake_tx_id,
                "category_id": fake_category_id
            }
        )
        
        assert response.status_code == 404
        assert "Transaction not found" in response.json()["detail"]
    
    def test_learn_from_categorization_invalid_category(self, authenticated_client, sample_data):
        """Test learning with invalid category ID"""
        tx_id = sample_data["transaction_id"]
        fake_category_id = str(uuid.uuid4())
        
        response = authenticated_client.post(
            "/ai/merchant-memory/learn",
            json={
                "transaction_id": tx_id,
                "category_id": fake_category_id
            }
        )
        
        assert response.status_code == 404
        assert "Category not found" in response.json()["detail"]
    
    def test_get_merchant_memory_stats(self, authenticated_client):
        """Test getting merchant memory statistics"""
        response = authenticated_client.get("/ai/merchant-memory/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "merchant_memory" in data
        assert "top_merchants" in data
        assert "recent_activity" in data
        assert "benefits" in data
        
        merchant_memory = data["merchant_memory"]
        assert "total_learned_merchants" in merchant_memory
        assert "learning_enabled" in merchant_memory
        assert "auto_categorization" in merchant_memory
        assert merchant_memory["learning_enabled"] is True
        assert merchant_memory["auto_categorization"] is True
        
        assert isinstance(data["top_merchants"], list)
        assert isinstance(data["recent_activity"], list)
        assert isinstance(data["benefits"], list)
    
    def test_extract_merchant_name(self, authenticated_client):
        """Test merchant name extraction endpoint"""
        test_cases = [
            ("SHEETZ #1234 PURCHASE", "Sheetz"),
            ("STARBUCKS STORE #5678", "Starbucks"),
            ("AMAZON.COM*123456789", "Amazon"),
            ("UNKNOWN MERCHANT #123", "UNKNOWN MERCHANT"),
        ]
        
        for description, expected in test_cases:
            response = authenticated_client.post(
                "/ai/merchant-memory/extract",
                json={"description": description}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["original_description"] == description
            assert data["extracted_merchant"] == expected
    
    def test_get_learned_mappings_empty(self, authenticated_client):
        """Test getting learned mappings when none exist"""
        response = authenticated_client.get("/ai/merchant-memory/learned-mappings")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "learned_mappings" in data
        assert "total_mappings" in data
        assert isinstance(data["learned_mappings"], list)
        assert isinstance(data["total_mappings"], int)
    
    def test_get_learned_mappings_with_data(self, authenticated_client, sample_data):
        """Test getting learned mappings after learning"""
        tx_id = sample_data["transaction_id"]
        category_id = sample_data["category_id"]
        
        # First learn from categorization
        learn_response = authenticated_client.post(
            "/ai/merchant-memory/learn",
            json={
                "transaction_id": tx_id,
                "category_id": category_id
            }
        )
        assert learn_response.status_code == 200
        
        # Then get learned mappings
        response = authenticated_client.get("/ai/merchant-memory/learned-mappings?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_mappings"] >= 1
        assert len(data["learned_mappings"]) >= 1
        
        # Check structure of mapping
        mapping = data["learned_mappings"][0]
        assert "merchant_name" in mapping
        assert "category_name" in mapping
        assert "confidence" in mapping
        assert "usage_count" in mapping
        assert "last_used" in mapping
        
        # Should have our learned mapping
        sheetz_mapping = next(
            (m for m in data["learned_mappings"] if m["merchant_name"] == "Sheetz"),
            None
        )
        assert sheetz_mapping is not None
        assert sheetz_mapping["category_name"] == "Gas & Automotive"
        assert sheetz_mapping["usage_count"] >= 1
        assert sheetz_mapping["confidence"] > 0


class TestMerchantMemoryManagementEndpoints:
    """Test merchant memory management endpoints (admin only)"""
    
    def test_delete_merchant_mapping_success(self, authenticated_client, sample_data):
        """Test successful deletion of merchant mapping"""
        tx_id = sample_data["transaction_id"]
        category_id = sample_data["category_id"]
        
        # First learn from categorization
        learn_response = authenticated_client.post(
            "/ai/merchant-memory/learn",
            json={
                "transaction_id": tx_id,
                "category_id": category_id
            }
        )
        assert learn_response.status_code == 200
        
        # Then delete the mapping
        response = authenticated_client.request(
            "DELETE",
            "/ai/merchant-memory/mapping",
            json={"merchant_pattern": "Sheetz"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["merchant_pattern"] == "Sheetz"
        assert "successfully" in data["message"]
    
    def test_delete_merchant_mapping_not_found(self, authenticated_client):
        """Test deletion of non-existent merchant mapping"""
        response = authenticated_client.request(
            "DELETE",
            "/ai/merchant-memory/mapping",
            json={"merchant_pattern": "NonExistentMerchant"}
        )
        
        assert response.status_code == 404
        assert "Merchant mapping not found" in response.json()["detail"]
    
    def test_clear_all_merchant_mappings(self, authenticated_client, sample_data):
        """Test clearing all merchant mappings"""
        tx_id = sample_data["transaction_id"]
        category_id = sample_data["category_id"]
        
        # First learn from categorization
        learn_response = authenticated_client.post(
            "/ai/merchant-memory/learn",
            json={
                "transaction_id": tx_id,
                "category_id": category_id
            }
        )
        assert learn_response.status_code == 200
        
        # Then clear all mappings
        response = authenticated_client.post("/ai/merchant-memory/clear-all")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "mappings_deleted" in data
        assert isinstance(data["mappings_deleted"], int)
        assert "Cleared" in data["message"]


class TestMerchantMemoryIntegration:
    """Test integration between different merchant memory endpoints"""
    
    def test_full_merchant_learning_flow(self, authenticated_client, sample_data):
        """Test complete flow: learn -> stats -> mappings -> delete"""
        tx_id = sample_data["transaction_id"]
        category_id = sample_data["category_id"]
        
        # Step 1: Learn from categorization
        learn_response = authenticated_client.post(
            "/ai/merchant-memory/learn",
            json={
                "transaction_id": tx_id,
                "category_id": category_id
            }
        )
        assert learn_response.status_code == 200
        assert learn_response.json()["merchant_learned"] == "Sheetz"
        
        # Step 2: Check stats reflect the learning
        stats_response = authenticated_client.get("/ai/merchant-memory/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["merchant_memory"]["total_learned_merchants"] >= 1
        
        # Step 3: Get learned mappings
        mappings_response = authenticated_client.get("/ai/merchant-memory/learned-mappings")
        assert mappings_response.status_code == 200
        mappings_data = mappings_response.json()
        assert mappings_data["total_mappings"] >= 1
        
        sheetz_mapping = next(
            (m for m in mappings_data["learned_mappings"] if m["merchant_name"] == "Sheetz"),
            None
        )
        assert sheetz_mapping is not None
        
        # Step 4: Extract merchant from description
        extract_response = authenticated_client.post(
            "/ai/merchant-memory/extract",
            json={"description": "SHEETZ #9999 DIFFERENT LOCATION"}
        )
        assert extract_response.status_code == 200
        assert extract_response.json()["extracted_merchant"] == "Sheetz"
        
        # Step 5: Delete the mapping
        delete_response = authenticated_client.request(
            "DELETE",
            "/ai/merchant-memory/mapping",
            json={"merchant_pattern": "Sheetz"}
        )
        assert delete_response.status_code == 200
        
        # Step 6: Verify mapping is gone
        final_mappings_response = authenticated_client.get("/ai/merchant-memory/learned-mappings")
        final_mappings_data = final_mappings_response.json()
        
        remaining_sheetz = [
            m for m in final_mappings_data["learned_mappings"] 
            if m["merchant_name"] == "Sheetz"
        ]
        assert len(remaining_sheetz) == 0
    
    def test_multiple_learnings_increment_usage(self, authenticated_client, sample_data):
        """Test that multiple learnings for same merchant increment usage count"""
        tx_id = sample_data["transaction_id"]
        category_id = sample_data["category_id"]
        
        # Learn multiple times
        for i in range(3):
            response = authenticated_client.post(
                "/ai/merchant-memory/learn",
                json={
                    "transaction_id": tx_id,
                    "category_id": category_id
                }
            )
            assert response.status_code == 200
        
        # Check that usage count increased
        mappings_response = authenticated_client.get("/ai/merchant-memory/learned-mappings")
        mappings_data = mappings_response.json()
        
        sheetz_mapping = next(
            (m for m in mappings_data["learned_mappings"] if m["merchant_name"] == "Sheetz"),
            None
        )
        assert sheetz_mapping is not None
        assert sheetz_mapping["usage_count"] == 3
        assert sheetz_mapping["confidence"] > 1.0  # Should increase with usage


class TestMerchantMemoryErrorHandling:
    """Test error handling in merchant memory API endpoints"""
    
    def test_learn_invalid_json(self, authenticated_client):
        """Test learning endpoint with invalid JSON"""
        response = authenticated_client.post(
            "/ai/merchant-memory/learn",
            json={"invalid": "data"}
        )
        
        # Should return validation error (422)
        assert response.status_code == 422
    
    def test_extract_missing_description(self, authenticated_client):
        """Test extraction endpoint with missing description"""
        response = authenticated_client.post(
            "/ai/merchant-memory/extract",
            json={}
        )
        
        # Should return validation error (422)
        assert response.status_code == 422
    
    def test_delete_mapping_invalid_json(self, authenticated_client):
        """Test delete mapping with invalid JSON"""
        response = authenticated_client.request(
            "DELETE",
            "/ai/merchant-memory/mapping",
            json={"invalid": "data"}
        )
        
        # Should return validation error (422)
        assert response.status_code == 422
    
    def test_endpoints_handle_db_errors_gracefully(self, authenticated_client):
        """Test that endpoints handle database errors gracefully"""
        # Test with malformed merchant pattern that might cause DB issues
        response = authenticated_client.post(
            "/ai/merchant-memory/extract",
            json={"description": ""}
        )
        
        # Should still return 200 with empty merchant
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["extracted_merchant"] == ""


class TestMerchantMemoryPerformance:
    """Test performance aspects of merchant memory system"""
    
    def test_large_description_handling(self, authenticated_client):
        """Test handling of very large transaction descriptions"""
        large_description = "SHEETZ #1234 " + "A" * 10000  # 10KB description
        
        response = authenticated_client.post(
            "/ai/merchant-memory/extract",
            json={"description": large_description}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["extracted_merchant"] == "Sheetz"
    
    def test_stats_endpoint_performance(self, authenticated_client):
        """Test that stats endpoint responds quickly"""
        import time
        
        start_time = time.time()
        response = authenticated_client.get("/ai/merchant-memory/stats")
        end_time = time.time()
        
        assert response.status_code == 200
        # Should respond within 5 seconds (generous for CI environments)
        assert (end_time - start_time) < 5.0
    
    def test_mappings_endpoint_with_limit(self, authenticated_client):
        """Test that mappings endpoint respects limit parameter"""
        response = authenticated_client.get("/ai/merchant-memory/learned-mappings?limit=1")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should respect the limit
        assert len(data["learned_mappings"]) <= 1


if __name__ == "__main__":
    pytest.main([__file__])