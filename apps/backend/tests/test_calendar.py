"""
Tests for Bill Calendar API endpoints.
"""

import os
import tempfile
from datetime import date
from fastapi.testclient import TestClient


def _setup_client():
    os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="cal_test_")
    from kashat.api import create_app
    return TestClient(create_app())


class TestCalendarAPI:
    """Tests for the bill calendar endpoints."""

    def test_get_upcoming_bills(self):
        """Test getting upcoming bills for next N days."""
        client = _setup_client()
        response = client.get("/api/calendar/upcoming?days=30")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_month_calendar(self):
        """Test getting full month calendar view."""
        client = _setup_client()
        today = date.today()
        response = client.get(f"/api/calendar/month/{today.year}/{today.month}")
        assert response.status_code == 200
        data = response.json()

        assert data["year"] == today.year
        assert data["month"] == today.month
        assert "month_name" in data
        assert "days" in data
        assert "total_bills" in data
        assert "total_amount" in data

    def test_get_bill_summary(self):
        """Test getting bill summary for different time periods."""
        client = _setup_client()
        response = client.get("/api/calendar/summary")
        assert response.status_code == 200
        data = response.json()

        assert "next_7_days" in data
        assert "next_30_days" in data
        assert "next_90_days" in data
        assert "bill_count_7" in data
        assert "bill_count_30" in data
        assert "bill_count_90" in data

    def test_get_todays_bills(self):
        """Test getting bills due today."""
        client = _setup_client()
        response = client.get("/api/calendar/today")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_overdue_bills(self):
        """Test getting overdue bills."""
        client = _setup_client()
        response = client.get("/api/calendar/overdue")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_invalid_month(self):
        """Test calendar with invalid month returns error."""
        client = _setup_client()
        response = client.get("/api/calendar/month/2024/13")
        assert response.status_code == 422

    def test_invalid_year(self):
        """Test calendar with invalid year returns error."""
        client = _setup_client()
        response = client.get("/api/calendar/month/1800/1")
        assert response.status_code == 422
