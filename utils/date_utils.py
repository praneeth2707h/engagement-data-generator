"""Date utility functions for the Engagement Data Generator.

All date arithmetic uses the standard library only — no third-party imports.

References
----------
* PROJECT_DECISIONS.md BIZ-023/C-003 — ISO Monday boundary for weekly counter reset.
"""
from __future__ import annotations
from datetime import date, timedelta


def iso_week_start(reference_date: date) -> date:
    """Return the Monday that starts the ISO week containing reference_date.

    ISO weeks run Monday (weekday 0) through Sunday (weekday 6). This function
    returns the Monday of the same week as reference_date — which may be
    reference_date itself if reference_date is a Monday.

    The correct check is d.weekday() == 0 (Monday), NOT d.isoweekday() == 7.
    This distinction is enforced per BIZ-023/C-003.

    Args:
        reference_date: Any calendar date.

    Returns:
        The Monday of the ISO week that contains reference_date.

    Examples:
        iso_week_start(date(2024, 1, 17))  # Wednesday -> date(2024, 1, 15)
        iso_week_start(date(2024, 1, 15))  # Monday    -> date(2024, 1, 15)
        iso_week_start(date(2024, 1, 21))  # Sunday    -> date(2024, 1, 15)
    """
    return reference_date - timedelta(days=reference_date.weekday())


__all__ = ["iso_week_start"]
