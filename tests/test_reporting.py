"""Tests for monthly aggregation logic in reporting service."""
import pytest
from unittest.mock import MagicMock, patch
from app.services.reporting import MONTH_NAMES


def test_month_names_length():
    assert len(MONTH_NAMES) == 13  # index 0 unused


def test_month_names_values():
    assert MONTH_NAMES[1] == "Jan"
    assert MONTH_NAMES[12] == "Dec"
    assert MONTH_NAMES[6] == "Jun"


def test_month_names_index_zero_empty():
    assert MONTH_NAMES[0] == ""
