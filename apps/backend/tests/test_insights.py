"""
Tests for Smart Insights API endpoints.
"""

import os
import tempfile
from fastapi.testclient import TestClient


def _setup_client():
    os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="insights_test_")
    from kashat.api import create_app
    return TestClient(create_app())


class TestInsightsAPI:
    """Tests for the smart insights endpoints."""

    def test_get_insight_cards(self):
        """Test getting insight cards for dashboard."""
        client = _setup_client()
        response = client.get("/api/insights/cards?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_spending_spikes(self):
        """Test getting spending spike analysis."""
        client = _setup_client()
        response = client.get("/api/insights/spending-spikes?threshold=0.3")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_price_increases(self):
        """Test getting price increase detection."""
        client = _setup_client()
        response = client.get("/api/insights/price-increases")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_unused_subscriptions(self):
        """Test getting unused subscription detection."""
        client = _setup_client()
        response = client.get("/api/insights/unused-subscriptions?days=45")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_top_categories(self):
        """Test getting top spending categories."""
        client = _setup_client()
        response = client.get("/api/insights/top-categories?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_insight_card_structure(self):
        """Test that insight cards have required fields."""
        client = _setup_client()
        response = client.get("/api/insights/cards")
        assert response.status_code == 200
        data = response.json()

        for card in data:
            assert "type" in card
            assert "title" in card
            assert "message" in card
            assert "severity" in card

    def test_insight_card_severity_values(self):
        """Test that insight cards have valid severity levels."""
        client = _setup_client()
        response = client.get("/api/insights/cards")
        assert response.status_code == 200
        data = response.json()

        valid_severities = {"info", "warning", "alert"}
        for card in data:
            assert card["severity"] in valid_severities

    def test_spending_spike_structure(self):
        """Test spending spike response structure."""
        client = _setup_client()
        response = client.get("/api/insights/spending-spikes")
        assert response.status_code == 200
        data = response.json()

        for spike in data:
            assert "category_id" in spike
            assert "category_name" in spike
            assert "current" in spike
            assert "average" in spike
            assert "percent_change" in spike
