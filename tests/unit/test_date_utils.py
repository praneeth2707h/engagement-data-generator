"""Tests for utils/date_utils.py — BIZ-023/C-003 compliance."""
from datetime import date
from utils.date_utils import iso_week_start


def test_midweek_returns_preceding_monday():
    """Wednesday 2024-01-17 -> Monday 2024-01-15."""
    assert iso_week_start(date(2024, 1, 17)) == date(2024, 1, 15)


def test_monday_returns_itself():
    """Monday 2024-01-15 -> same day (no offset)."""
    assert iso_week_start(date(2024, 1, 15)) == date(2024, 1, 15)


def test_sunday_returns_preceding_monday():
    """Sunday 2024-01-21 -> Monday 2024-01-15 (same ISO week)."""
    assert iso_week_start(date(2024, 1, 21)) == date(2024, 1, 15)
