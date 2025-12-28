"""
Integration tests for full Kashat workflows.
"""

import os
import tempfile
from datetime import date
from fastapi.testclient import TestClient


def _setup_client():
    os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="integ_test_")
    from kashat.api import create_app
    return TestClient(create_app())


class TestBudgetTrackingWorkflow:
    """Integration tests for budget tracking workflow."""

    def test_budget_creation_to_progress(self):
        """Test full budget workflow: create → add category → track progress."""
        client = _setup_client()

        # 1. Create a budget
        response = client.post("/api/budgets", json={
            "name": "Integration Test Budget",
            "period": "monthly",
            "categories": []
        })
        assert response.status_code == 200
        budget = response.json()
        budget_id = budget["id"]

        # 2. Create a category
        cat_resp = client.post("/api/categories", json={"name": "Integration Food"})
        cat_id = cat_resp.json()["id"]

        # 3. Set category limit
        response = client.put(
            f"/api/budgets/{budget_id}/categories/{cat_id}?amount_limit=300&rollover=false"
        )
        assert response.status_code == 200

        # 4. Verify budget progress
        response = client.get(f"/api/budgets/{budget_id}/progress")
        assert response.status_code == 200
        progress = response.json()

        assert progress["total_limit"] == 300
        assert len(progress["categories"]) == 1
        assert progress["categories"][0]["category_name"] == "Integration Food"


class TestNetWorthWorkflow:
    """Integration tests for net worth calculation workflow."""

    def test_networth_calculation(self):
        """Test net worth calculation with snapshot."""
        client = _setup_client()

        # Get net worth (empty)
        response = client.get("/api/networth")
        assert response.status_code == 200
        data = response.json()
        assert data["net_worth"] == 0

        # Create snapshot
        response = client.post("/api/networth/snapshot")
        assert response.status_code == 200

        # Get snapshots
        response = client.get("/api/networth/snapshots")
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestCalendarWorkflow:
    """Integration tests for calendar functionality."""

    def test_calendar_full_flow(self):
        """Test calendar endpoints work together."""
        client = _setup_client()
        today = date.today()

        # Get summary
        response = client.get("/api/calendar/summary")
        assert response.status_code == 200
        summary = response.json()
        assert "next_7_days" in summary

        # Get month calendar
        response = client.get(f"/api/calendar/month/{today.year}/{today.month}")
        assert response.status_code == 200
        calendar = response.json()
        assert len(calendar["days"]) > 0

        # Get upcoming
        response = client.get("/api/calendar/upcoming?days=30")
        assert response.status_code == 200

        # Get today's bills
        response = client.get("/api/calendar/today")
        assert response.status_code == 200


class TestTransactionReviewWorkflow:
    """Integration tests for transaction review workflow."""

    def test_review_endpoints(self):
        """Test transaction review endpoints exist and respond."""
        client = _setup_client()

        # Get unreviewed transactions
        response = client.get("/api/transactions/unreviewed/list?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_bulk_review_empty(self):
        """Test bulk review with empty list."""
        client = _setup_client()

        response = client.post("/api/transactions/bulk/review", json={
            "tx_ids": [],
            "reviewed_by": "test"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["reviewed"] == 0


class TestInsightsWorkflow:
    """Integration tests for insights functionality."""

    def test_insights_full_flow(self):
        """Test all insight endpoints work."""
        client = _setup_client()

        # Get insight cards
        response = client.get("/api/insights/cards")
        assert response.status_code == 200

        # Get spending spikes
        response = client.get("/api/insights/spending-spikes")
        assert response.status_code == 200

        # Get price increases
        response = client.get("/api/insights/price-increases")
        assert response.status_code == 200

        # Get unused subscriptions
        response = client.get("/api/insights/unused-subscriptions")
        assert response.status_code == 200

        # Get top categories
        response = client.get("/api/insights/top-categories")
        assert response.status_code == 200
