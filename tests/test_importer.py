"""Tests for CSV parsing and ImportResult structure."""
import pytest
from unittest.mock import MagicMock, patch
from app.services.importer import _parse_date, ImportResult
from datetime import date


class TestParseDate:
    def test_iso_format(self):
        assert _parse_date("2023-04-27") == date(2023, 4, 27)

    def test_dmy_slash(self):
        assert _parse_date("27/04/2023") == date(2023, 4, 27)

    def test_mdy_slash(self):
        assert _parse_date("04/27/2023") == date(2023, 4, 27)

    def test_compact(self):
        assert _parse_date("20230427") == date(2023, 4, 27)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_date("not-a-date")

    def test_strips_whitespace(self):
        assert _parse_date("  2023-04-27  ") == date(2023, 4, 27)


class TestImportResult:
    def test_default_failed(self):
        r = ImportResult(success=False, errors=["oops"])
        assert not r.success
        assert r.row_count == 0

    def test_success(self):
        r = ImportResult(success=True, row_count=42)
        assert r.success
        assert r.errors == []
