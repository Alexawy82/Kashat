"""
Tests for Budget System API endpoints.
"""

import os
import tempfile
from fastapi.testclient import TestClient


def _setup_client():
    os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="budget_test_")
    from kashat.api import create_app
    return TestClient(create_app())


class TestBudgetAPI:
    """Tests for the budget system endpoints."""

    def test_list_budgets_empty(self):
        """Test listing budgets when none exist."""
        client = _setup_client()
        response = client.get("/api/budgets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_budget(self):
        """Test creating a new budget."""
        client = _setup_client()
        response = client.post("/api/budgets", json={
            "name": "Monthly Expenses",
            "period": "monthly",
            "categories": []
        })
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Monthly Expenses"
        assert data["period"] == "monthly"
        assert "id" in data
        assert "is_active" in data
        assert data["is_active"] is True

    def test_get_budget(self):
        """Test getting a specific budget."""
        client = _setup_client()
        # Create a budget first
        create_resp = client.post("/api/budgets", json={
            "name": "Test Budget",
            "period": "monthly",
            "categories": []
        })
        budget_id = create_resp.json()["id"]

        response = client.get(f"/api/budgets/{budget_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == budget_id
        assert data["name"] == "Test Budget"

    def test_get_budget_not_found(self):
        """Test getting a non-existent budget."""
        client = _setup_client()
        response = client.get("/api/budgets/non-existent-id")
        assert response.status_code == 404

    def test_update_budget(self):
        """Test updating a budget."""
        client = _setup_client()
        # Create a budget first
        create_resp = client.post("/api/budgets", json={
            "name": "Old Name",
            "period": "monthly",
            "categories": []
        })
        budget_id = create_resp.json()["id"]

        response = client.put(f"/api/budgets/{budget_id}", json={
            "name": "New Name"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    def test_delete_budget(self):
        """Test deleting a budget."""
        client = _setup_client()
        # Create a budget first
        create_resp = client.post("/api/budgets", json={
            "name": "To Delete",
            "period": "monthly",
            "categories": []
        })
        budget_id = create_resp.json()["id"]

        response = client.delete(f"/api/budgets/{budget_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True

        # Verify it's gone
        response = client.get(f"/api/budgets/{budget_id}")
        assert response.status_code == 404

    def test_get_budget_progress(self):
        """Test getting budget progress with spending calculations."""
        client = _setup_client()
        # Create budget
        create_resp = client.post("/api/budgets", json={
            "name": "Progress Test",
            "period": "monthly",
            "categories": []
        })
        budget_id = create_resp.json()["id"]

        response = client.get(f"/api/budgets/{budget_id}/progress")
        assert response.status_code == 200
        data = response.json()

        assert data["budget_id"] == budget_id
        assert "period_start" in data
        assert "period_end" in data
        assert "days_remaining" in data
        assert "total_limit" in data
        assert "total_spent" in data
        assert "percent_used" in data
        assert "on_track" in data

    def test_set_category_limit(self):
        """Test setting a category limit in a budget."""
        client = _setup_client()
        # Create budget
        create_resp = client.post("/api/budgets", json={
            "name": "Category Test",
            "period": "monthly",
            "categories": []
        })
        budget_id = create_resp.json()["id"]

        # Create category
        cat_resp = client.post("/api/categories", json={"name": "Food"})
        cat_id = cat_resp.json()["id"]

        response = client.put(
            f"/api/budgets/{budget_id}/categories/{cat_id}?amount_limit=500&rollover=false"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["category_id"] == cat_id
        assert data["amount_limit"] == 500
        assert data["rollover"] is False

    def test_remove_category_limit(self):
        """Test removing a category from a budget."""
        client = _setup_client()
        # Create budget
        create_resp = client.post("/api/budgets", json={
            "name": "Remove Test",
            "period": "monthly",
            "categories": []
        })
        budget_id = create_resp.json()["id"]

        # Create category and add to budget
        cat_resp = client.post("/api/categories", json={"name": "Entertainment"})
        cat_id = cat_resp.json()["id"]
        client.put(f"/api/budgets/{budget_id}/categories/{cat_id}?amount_limit=200")

        response = client.delete(f"/api/budgets/{budget_id}/categories/{cat_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
