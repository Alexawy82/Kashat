"""
Tests for Net Worth API endpoints.
"""

import os
import tempfile
from datetime import date, datetime, UTC
import uuid
from fastapi.testclient import TestClient


def _setup_client():
    os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="nw_test_")
    from kashat.api import create_app
    return TestClient(create_app())


class TestNetWorthAPI:
    """Tests for the net worth calculation and tracking endpoints."""

    def test_get_networth_empty(self):
        """Test net worth calculation with no accounts."""
        client = _setup_client()
        response = client.get("/api/networth")
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert "liabilities" in data
        assert "net_worth" in data
        assert "by_type" in data
        assert "accounts" in data

    def test_get_networth_history(self):
        """Test getting historical net worth data."""
        client = _setup_client()
        response = client.get("/api/networth/history?months=6")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for point in data:
            assert "date" in point
            assert "assets" in point
            assert "liabilities" in point
            assert "net_worth" in point

    def test_create_snapshot(self):
        """Test creating a net worth snapshot."""
        client = _setup_client()
        response = client.post("/api/networth/snapshot")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["created", "updated"]
        assert "date" in data

    def test_get_snapshots(self):
        """Test retrieving stored snapshots."""
        client = _setup_client()
        # First create a snapshot
        client.post("/api/networth/snapshot")
        response = client.get("/api/networth/snapshots?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_networth_breakdown_by_type(self):
        """Test that net worth includes breakdown by account type."""
        client = _setup_client()
        response = client.get("/api/networth")
        assert response.status_code == 200
        data = response.json()
        by_type = data.get("by_type", {})
        expected_types = ["checking", "savings", "investment", "asset", "credit_card", "loan"]
        for t in expected_types:
            assert t in by_type
