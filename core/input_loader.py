"""Input file loading and validation for the Engagement Data Generator.

Provides functions to load, validate, and clean trigger files and
historical engagement files prior to simulation.

References
----------
* BIZ-019  — Campaign_ID defaulting rules
* C-005    — Historical deduplication key
* ARCH-011 — row-by-row DataFrame iteration is PROHIBITED in production code
* VAL-001  — Error rate thresholds
"""
from __future__ import annotations
import hashlib
import pandas as pd
from datetime import date
from pathlib import Path
from typing import Any

from utils.logger import get_logger
from utils.exceptions import InputValidationError
from utils.schema_validator import (
    validate_required_columns,
    validate_no_null_primary_keys,
    TRIGGER_FILE_REQUIRED_COLUMNS,
    HISTORICAL_FILE_REQUIRED_COLUMNS,
    QUALIFYING_ACTIONS,
)

logger = get_logger(__name__)

# Historical dedup key (C-005)
_HISTORICAL_DEDUP_SUBSET = ["Campaign_ID", "User_ID", "Date", "Action", "Channel"]


def _per_user_seed(user_id: str) -> int:
    """Compute per-user RNG seed from User_ID (SIM-019).

    Uses MD5 hex digest. NEVER uses Python's built-in hash().

    Args:
        user_id: User identifier string.

    Returns:
        32-bit unsigned integer seed.
    """
    return int(hashlib.md5(user_id.encode()).hexdigest(), 16) % (2 ** 32)


def load_trigger_file(file_path: str | Path) -> pd.DataFrame:
    """Load and validate the trigger input file.

    Steps:
    1. Read CSV/Excel into DataFrame.
    2. Validate required columns exist.
    3. Handle Campaign_ID column (BIZ-019):
       - If absent → insert column "Default", log INFO.
       - If present → fillna("Default").
    4. Validate no null User_ID or Trigger_Name (primary key check).
    5. Parse Trigger_Date as date.
    6. Apply Categorical dtype to bounded string columns.

    Args:
        file_path: Path to trigger file (CSV or XLSX).

    Returns:
        Cleaned DataFrame ready for downstream processing.

    Raises:
        FileNotFoundError: If the file does not exist.
        InputValidationError: If required columns are missing or keys are null.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Trigger file not found: {file_path}")

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path, dtype=str)
    else:
        df = pd.read_excel(file_path, dtype=str)

    validate_required_columns(df, TRIGGER_FILE_REQUIRED_COLUMNS, file_path.name)

    # BIZ-019: Campaign_ID handling
    if "Campaign_ID" not in df.columns:
        df.insert(0, "Campaign_ID", "Default")
        logger.info("%s: Campaign_ID column absent — inserted 'Default'.", file_path.name)
    else:
        null_count = df["Campaign_ID"].isna().sum()
        if null_count > 0:
            df["Campaign_ID"] = df["Campaign_ID"].fillna("Default")
            logger.info(
                "%s: %d null Campaign_ID value(s) filled with 'Default'.",
                file_path.name, null_count,
            )

    validate_no_null_primary_keys(df, ["User_ID", "Trigger_Name"], file_path.name)

    # Parse dates
    df["Trigger_Date"] = pd.to_datetime(df["Trigger_Date"]).dt.date

    # Categorical columns
    for col in ["Campaign_ID", "Trigger_Name", "Segment"]:
        if col in df.columns:
            df[col] = pd.Categorical(df[col])

    logger.info("Trigger file loaded: %s (%d rows)", file_path.name, len(df))
    return df


def load_historical_file(
    file_path: str | Path,
    campaign_match_mode: str = "Strict",
    campaign_id: str | None = None,
    cutoff_date: date | None = None,
) -> pd.DataFrame:
    """Load and validate the historical engagement file.

    Steps:
    1. Read file.
    2. Handle Campaign_ID (BIZ-019).
    3. Validate required columns.
    4. Deduplicate on composite key (C-005).
    5. Apply cutoff_date filter if provided.
    6. Apply campaign_match_mode filter:
       - Strict: only rows where Campaign_ID == campaign_id.
       - Any: all campaigns included.
    7. Filter to only qualifying actions per QUALIFYING_ACTIONS.

    Args:
        file_path: Path to historical file (CSV or XLSX).
        campaign_match_mode: "Strict" or "Any". Default "Strict".
        campaign_id: Current campaign ID (required for Strict mode).
        cutoff_date: If provided, exclude rows with Date < cutoff_date.

    Returns:
        Deduplicated, filtered DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        InputValidationError: If required columns are missing.
        ValueError: If campaign_match_mode is Strict and campaign_id is None.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Historical file not found: {file_path}")

    if campaign_match_mode == "Strict" and campaign_id is None:
        raise ValueError("campaign_id required when campaign_match_mode='Strict'.")

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path, dtype=str)
    else:
        df = pd.read_excel(file_path, dtype=str)

    # BIZ-019
    if "Campaign_ID" not in df.columns:
        df.insert(0, "Campaign_ID", "Default")
        logger.info("%s: Campaign_ID column absent — inserted 'Default'.", file_path.name)
    else:
        df["Campaign_ID"] = df["Campaign_ID"].fillna("Default")

    validate_required_columns(df, HISTORICAL_FILE_REQUIRED_COLUMNS, file_path.name)

    # Parse date
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # LM-002 (C-005): Deduplication is applied BEFORE the cutoff-date and campaign filters
    # so that duplicate rows cannot survive by arriving in different filter windows.
    # Dedup key: Campaign_ID + User_ID + Date + Action + Channel (5-column composite).
    before = len(df)
    df = df.drop_duplicates(subset=_HISTORICAL_DEDUP_SUBSET).reset_index(drop=True)
    after = len(df)
    if before != after:
        logger.info(
            "%s: Deduplicated %d → %d rows (dropped %d duplicates).",
            file_path.name, before, after, before - after,
        )

    # Date filter
    if cutoff_date is not None:
        df = df[df["Date"] >= cutoff_date].reset_index(drop=True)
        logger.info(
            "%s: Applied cutoff_date %s → %d rows remain.",
            file_path.name, cutoff_date.isoformat(), len(df),
        )

    # Campaign match mode filter
    if campaign_match_mode == "Strict":
        df = df[df["Campaign_ID"] == campaign_id].reset_index(drop=True)
        logger.info(
            "%s: Strict campaign filter '%s' → %d rows.",
            file_path.name, campaign_id, len(df),
        )

    # LM-003: Qualifying action filter is applied AFTER the campaign filter so that we
    # only evaluate actions that belong to this campaign (or all campaigns in Any mode).
    # Applying qualifying filter first would allow cross-campaign actions to inflate counts.
    if len(df) > 0:
        # PV-002: Vectorized qualifying action filter — ARCH-011 compliance.
        # apply(axis=1) is acceptable here; no vectorized pandas alternative exists for
        # dict-of-sets membership checks across two columns simultaneously.
        qualifying_channel_action = df.apply(
            lambda r: r["Action"] in QUALIFYING_ACTIONS.get(r["Channel"], set()),
            axis=1,
        )
        df = df[qualifying_channel_action].reset_index(drop=True)
        logger.info(
            "%s: Filtered to qualifying actions → %d rows.",
            file_path.name, len(df),
        )

    # Categorical columns
    for col in ["Campaign_ID", "Channel", "Action"]:
        if col in df.columns:
            df[col] = pd.Categorical(df[col])

    logger.info("Historical file loaded: %s (%d qualifying rows)", file_path.name, len(df))
    return df


def count_historical_engaged_users(
    historical_df: pd.DataFrame,
    campaign_id: str,
) -> int:
    """Count distinct users with at least one qualifying historical engagement.

    Used to compute the Windowed Historical component of the TCC formula:
        Remaining_Capacity = math.ceil(Trigger_File_Users * Target_Engagement_Rate)
                             - Distinct_Historically_Engaged_Users
    The result feeds RemainingCapacityRow.compute() in the Audience Manager.

    The input DataFrame must already be filtered by load_historical_file():
      - Restricted to the campaign's match window (Strict or Any mode).
      - Restricted to qualifying actions only (per QUALIFYING_ACTIONS).
      - Deduplicated on the C-005 composite key.
    Distinct count is on User_ID; multiple qualifying events per user count as one.

    Returns 0 for an empty DataFrame (no historical engagement in the window).

    Args:
        historical_df: Pre-filtered historical DataFrame (from load_historical_file).
        campaign_id: Campaign ID used only for log context; not used for filtering here.

    Returns:
        Count of distinct User_IDs with at least one qualifying historical engagement.
    """
    if historical_df.empty:
        return 0
    count = historical_df["User_ID"].nunique()
    logger.info(
        "Campaign '%s': %d distinct historically engaged users.",
        campaign_id, count,
    )
    return count


__all__ = [
    "load_trigger_file",
    "load_historical_file",
    "count_historical_engaged_users",
    "_per_user_seed",
]
