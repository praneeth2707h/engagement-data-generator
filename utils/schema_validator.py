"""Schema validation utilities for the Engagement Data Generator.

Centralises qualifying action definitions, required column lists, and
validation helpers used by core/input_loader.py.

References
----------
* C-004  — QUALIFYING_ACTIONS is the single source of truth
* BIZ-011 — qualifying actions for TER and TCC calculations
* PV-001  — input_loader.py uses only vectorized operations; this module is ARCH-011 compliant
"""
from __future__ import annotations
import pandas as pd
from utils.canonical_schema import (
    TRIGGER_FILE_REQUIRED_COLUMNS,
    HISTORICAL_FILE_REQUIRED_COLUMNS,
)
from utils.exceptions import InputValidationError
from utils.logger import get_logger

logger = get_logger(__name__)

# QUALIFYING_ACTIONS: centralized here per Decision C-004.
# Display sub-types -> only Click qualifies as engagement.
# Email and WhatsApp -> Open and Click qualify.
# "Sent" and "Impression" are NEVER qualifying actions.
QUALIFYING_ACTIONS: dict[str, set[str]] = {
    "Endemic_Display":       {"Click"},
    "Programmatic_Display":  {"Click"},
    "Banner":                {"Click"},
    "Display":               {"Click"},
    "Email":                 {"Open", "Click"},
    "WhatsApp":              {"Open", "Click"},
}

# TRIGGER_FILE_REQUIRED_COLUMNS and HISTORICAL_FILE_REQUIRED_COLUMNS are
# imported from utils.canonical_schema (HIGH-001). Re-exported via __all__
# for backward compatibility with existing importers.

USER_STATE_REQUIRED_COLUMNS: list[str] = [
    "campaign_id", "user_id", "eligibility_status", "journey_status",
    "behavior_profile", "engagement_score", "state_as_of_date",
    "historical_engaged", "is_valid",
]

# ---------------------------------------------------------------------------
# Error rate tier thresholds (VAL-001 / PHASE_2_EXECUTION_PLAN.md Section Validation)
# ---------------------------------------------------------------------------
_ERROR_RATE_TIER_1_USERS: int = 1_000    # <= 1,000 users
_ERROR_RATE_TIER_2_USERS: int = 10_000   # 1,001-10,000 users
_TIER_1_PCT: float = 0.02               # 2%
_TIER_1_ABS: int = 20
_TIER_2_PCT: float = 0.01               # 1%
_TIER_2_ABS: int = 100
_TIER_3_PCT: float = 0.005              # 0.5%
_TIER_3_ABS: int = 50


def is_qualifying_action(channel: str, action: str) -> bool:
    """Return True if action is a qualifying engagement for the given channel.

    Used to count distinct engaged users for TER and TCC calculations.
    Qualifying actions by channel (C-004 / BIZ-011):
      Display-family (Endemic_Display, Programmatic_Display, Banner, Display): Click only.
      Email: Open, Click.
      WhatsApp: Open, Click.
      Unknown channel: always False (returns empty set from QUALIFYING_ACTIONS.get).

    "Sent" and "Impression" are NEVER qualifying actions for any channel.
    Matching is case-sensitive: "Email" != "email", "Click" != "click".

    Args:
        channel: Channel name (e.g., "Email", "Display", "WhatsApp").
                 An unrecognised channel always returns False.
        action:  Action name (e.g., "Click", "Open").
                 "Sent" and "Impression" always return False.

    Returns:
        True if the action qualifies for the given channel, False otherwise.
    """
    return action in QUALIFYING_ACTIONS.get(channel, set())


def compute_error_threshold(user_count: int) -> tuple[float, int]:
    """Return (pct_threshold, abs_threshold) for the given user count tier.

    Tiered thresholds:
      <= 1,000 users:    2%   / 20 absolute
      1,001-10,000:      1%   / 100 absolute
      > 10,000:          0.5% / 50 absolute

    Args:
        user_count: Total number of users being simulated.

    Returns:
        Tuple of (percentage_threshold as float, absolute_threshold as int).
    """
    if user_count <= _ERROR_RATE_TIER_1_USERS:
        return (_TIER_1_PCT, _TIER_1_ABS)
    elif user_count <= _ERROR_RATE_TIER_2_USERS:
        return (_TIER_2_PCT, _TIER_2_ABS)
    else:
        return (_TIER_3_PCT, _TIER_3_ABS)


def validate_required_columns(
    df: pd.DataFrame,
    required: list[str],
    file_name: str,
) -> None:
    """Raise InputValidationError if any required columns are missing.

    Args:
        df:       DataFrame to check.
        required: List of required column names.
        file_name: Source file name for error messages.

    Raises:
        InputValidationError: If any required columns are missing.
    """
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise InputValidationError(
            file_name=file_name,
            detail=f"Missing required columns: {missing}",
        )


def validate_no_null_primary_keys(
    df: pd.DataFrame,
    key_columns: list[str],
    file_name: str,
) -> None:
    """Raise InputValidationError if primary key columns contain nulls.

    Args:
        df:          DataFrame to check.
        key_columns: Columns forming the composite primary key.
        file_name:   Source file name for error messages.

    Raises:
        InputValidationError: If any key column has null values.
    """
    for col in key_columns:
        if col in df.columns and df[col].isna().any():
            null_count = int(df[col].isna().sum())
            raise InputValidationError(
                file_name=file_name,
                detail=f"Column '{col}' has {null_count} null value(s) in primary key.",
            )


__all__ = [
    "is_qualifying_action",
    "compute_error_threshold",
    "validate_required_columns",
    "validate_no_null_primary_keys",
    "QUALIFYING_ACTIONS",
    "TRIGGER_FILE_REQUIRED_COLUMNS",
    "HISTORICAL_FILE_REQUIRED_COLUMNS",
    "USER_STATE_REQUIRED_COLUMNS",
]
