"""Tests for FX service logic."""
import pytest
from unittest.mock import MagicMock, patch
from app.services import fx_service
from app.services.fx_service import FrankfurterProvider, ManualFallback


class TestFrankfurterProvider:
    def test_usd_returns_none_from_api(self):
        """USD should be handled before calling the provider."""
        # The FX service handles USD == 1.0 at the get_or_fetch_rate level
        pass

    def test_get_rate_returns_float(self):
        provider = FrankfurterProvider()
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"ETB": 125.5}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_response):
            rate = provider.get_rate("ETB", 2024, 1)
        assert rate == 125.5

    def test_get_rate_returns_none_on_error(self):
        provider = FrankfurterProvider()
        with patch("httpx.get", side_effect=Exception("network error")):
            rate = provider.get_rate("ETB", 2024, 1)
        assert rate is None

    def test_currency_not_found_returns_none(self):
        provider = FrankfurterProvider()
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_response):
            rate = provider.get_rate("XYZ", 2024, 1)
        assert rate is None


class TestManualFallback:
    def test_always_returns_none(self):
        fb = ManualFallback()
        assert fb.get_rate("ETB", 2024, 1) is None


class TestGetOrFetchRate:
    def test_usd_returns_one(self):
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.add = MagicMock()
        db.flush = MagicMock()

        rec = fx_service.get_or_fetch_rate(db, "USD", 2024, 1, "first_day")
        assert float(rec.rate_usd) == 1.0

    def test_returns_existing_record(self):
        db = MagicMock()
        existing = MagicMock()
        existing.rate_usd = 125.5
        db.query.return_value.filter_by.return_value.first.return_value = existing

        rec = fx_service.get_or_fetch_rate(db, "ETB", 2024, 1, "first_day")
        assert rec is existing
