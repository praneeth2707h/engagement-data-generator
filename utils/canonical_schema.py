"""Canonical column name registry — single source of truth for all column names.

Wave 1 / HIGH-001: Eliminates scattered local column definitions across
schema_validator.py, simulation_orchestrator.py, upload_page.py, and
input_loader.py.

Import rule: this module imports only Python stdlib and pandas (a third-party
dependency, not a project-relative module). No project-relative imports are
permitted here to prevent circular dependency chains per ARCH-005.
"""
from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# External column names — user-facing, Title_Case
# Used in: trigger files, historical files, Excel export
# ---------------------------------------------------------------------------
EXTERNAL_CAMPAIGN_ID     = "Campaign_ID"
EXTERNAL_USER_ID         = "User_ID"
EXTERNAL_TRIGGER_NAME    = "Trigger_Name"
EXTERNAL_TRIGGER_DATE    = "Trigger_Date"
EXTERNAL_SEGMENT         = "Segment"
EXTERNAL_DATE            = "Date"
EXTERNAL_ACTION          = "Action"
EXTERNAL_CHANNEL         = "Channel"
EXTERNAL_AD_NAME         = "Ad_Name"
EXTERNAL_JOURNEY_STEP    = "Journey_Step"
EXTERNAL_COMPLETION_DATE = "Completion_Date"

# ---------------------------------------------------------------------------
# Internal column names — simulation DataFrames, snake_case
# Used in: state_df, audience_df, events_df
# ---------------------------------------------------------------------------
INTERNAL_CAMPAIGN_ID  = "campaign_id"
INTERNAL_USER_ID      = "user_id"
INTERNAL_TRIGGER_NAME = "trigger_name"
INTERNAL_SEGMENT      = "segment"
INTERNAL_JOURNEY_STEP = "journey_step"

# ---------------------------------------------------------------------------
# Authoritative required column lists
# ---------------------------------------------------------------------------
TRIGGER_FILE_REQUIRED_COLUMNS: list[str] = [
    EXTERNAL_USER_ID,
    EXTERNAL_TRIGGER_NAME,
    EXTERNAL_TRIGGER_DATE,
    EXTERNAL_SEGMENT,
]

HISTORICAL_FILE_REQUIRED_COLUMNS: list[str] = [
    EXTERNAL_USER_ID,
    EXTERNAL_DATE,
    EXTERNAL_ACTION,
    EXTERNAL_CHANNEL,
]

# HIGH-005: Extended historical schema columns (Wave 1 — definition only)
# Presence of all four columns signals an 8-column extended historical file
# that carries journey reconstruction data for Wave 3.
HISTORICAL_FILE_EXTENDED_COLUMNS: list[str] = [
    EXTERNAL_AD_NAME,
    EXTERNAL_JOURNEY_STEP,
    EXTERNAL_TRIGGER_NAME,
    EXTERNAL_COMPLETION_DATE,
]


def historical_file_has_extended_schema(df: pd.DataFrame) -> bool:
    """Return True if all four extended columns are present in df.

    Args:
        df: Historical engagement DataFrame to inspect.

    Returns:
        True if the DataFrame contains Ad_Name, Journey_Step, Trigger_Name,
        and Completion_Date columns; False otherwise.
    """
    return all(c in df.columns for c in HISTORICAL_FILE_EXTENDED_COLUMNS)


__all__ = [
    "EXTERNAL_CAMPAIGN_ID",
    "EXTERNAL_USER_ID",
    "EXTERNAL_TRIGGER_NAME",
    "EXTERNAL_TRIGGER_DATE",
    "EXTERNAL_SEGMENT",
    "EXTERNAL_DATE",
    "EXTERNAL_ACTION",
    "EXTERNAL_CHANNEL",
    "EXTERNAL_AD_NAME",
    "EXTERNAL_JOURNEY_STEP",
    "EXTERNAL_COMPLETION_DATE",
    "INTERNAL_CAMPAIGN_ID",
    "INTERNAL_USER_ID",
    "INTERNAL_TRIGGER_NAME",
    "INTERNAL_SEGMENT",
    "INTERNAL_JOURNEY_STEP",
    "TRIGGER_FILE_REQUIRED_COLUMNS",
    "HISTORICAL_FILE_REQUIRED_COLUMNS",
    "HISTORICAL_FILE_EXTENDED_COLUMNS",
    "historical_file_has_extended_schema",
]
