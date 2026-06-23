"""Stage 3 — User State Initialization.

UserStateManager is responsible for producing a state DataFrame with exactly
one row per unique User_ID in the trigger file, merging new users (initialised
to canonical defaults) with returning users (carried forward from a previous
simulation run).

Architecture references
-----------------------
* ARCH-002  — composite primary key (campaign_id, user_id)
* ARCH-003  — Stage 3 in the 11-stage pipeline
* ARCH-011 / PV-001 — no iterrows(); vectorised operations only
* ARCH-012  — dynamic Creative_Affinity_{ad_name} columns via reconcile_creative_affinity_columns()
* ARCH-015  — EligibilityStatus.NEW is the only value set at init; AudienceManager owns transitions
* ARCH-016  — weekly counters owned by FatigueEngine; UserStateManager initialises to 0
* ARCH-017  — TRIGGER_HISTORY_DELIMITER from utils/constants.py
* FR-USM-001 through FR-USM-011 — functional requirements for this module
* USER_STATE_DICTIONARY.md — authoritative 35-field reference
* PHASE_3_WAVE_1_BUILD_CONTRACT.md §2 — method signatures and contracts
"""
from __future__ import annotations

import dataclasses
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from models.config_registry import ConfigRegistry
from models.enums import BehaviorProfile, EligibilityStatus, JourneyStatus
from models.user_state import UserState
from utils.constants import (
    DEFAULT_CHANNEL_AFFINITY,
    DEFAULT_CREATIVE_AFFINITY,
    DEFAULT_ENGAGEMENT_SCORE,
    TRIGGER_HISTORY_DELIMITER,
)
from utils.excel_utils import reconcile_creative_affinity_columns
from utils.exceptions import InputValidationError
from utils.logger import get_logger
from utils.schema_validator import USER_STATE_REQUIRED_COLUMNS

logger = get_logger(__name__)

# Columns that must be float32 in the pipeline state DataFrame
_FLOAT32_COLS: tuple[str, ...] = (
    "engagement_score",
    "channel_affinity_display",
    "channel_affinity_email",
    "channel_affinity_whatsapp",
)

# Columns that must be pd.Categorical in the pipeline state DataFrame
_CATEGORICAL_COLS: tuple[str, ...] = (
    "eligibility_status",
    "journey_status",
    "behavior_profile",
    "trigger_name",
    "segment",
)


class UserStateManager:
    """Stage 3 — User State Initialization.

    Produces a state DataFrame with one row per unique User_ID in trigger_df.

    New users receive canonical defaults (UserState.new()).
    Returning users carry forward all fields from previous_state_df, with
    campaign_id overwritten from config and run_count incremented by 1.
    Users in previous_state_df who are absent from trigger_df are excluded
    (departed users) and a WARNING is logged for each.

    This class owns NO eligibility transitions, NO trigger assignment, NO
    weekly counter management, and NEVER sets is_valid=False.

    Args:
        config: The ConfigRegistry for the current campaign run.

    References:
        PHASE_3_WAVE_1_BUILD_CONTRACT.md §2
        USER_STATE_DICTIONARY.md
    """

    def __init__(self, config: ConfigRegistry) -> None:
        """Initialise with the campaign ConfigRegistry.

        Args:
            config: Fully constructed ConfigRegistry for this run.
                Stored as self._config for use in reconcile_creative_affinity_columns().

        Returns:
            None

        Raises:
            Nothing.
        """
        self._config = config

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def initialize_user_states(
        self,
        trigger_df: pd.DataFrame,
        previous_state_df: pd.DataFrame | None,
    ) -> pd.DataFrame:
        """Produce the initial state DataFrame for Stage 3.

        Merges new users (initialised to defaults) with returning users
        (carried forward from previous_state_df) to produce exactly one row
        per unique User_ID present in trigger_df.

        Args:
            trigger_df: Pre-validated trigger file DataFrame.
                Must contain a ``User_ID`` column at minimum.
            previous_state_df: Prior run state DataFrame, or ``None`` on the
                first simulation run. If supplied, must contain at minimum the
                columns listed in USER_STATE_REQUIRED_COLUMNS and a
                ``user_id`` column.

        Returns:
            pd.DataFrame with:
            - Exactly one row per unique User_ID in trigger_df.
            - All 35 static columns present with correct dtypes.
            - float32 on engagement_score, channel_affinity_*, and
              Creative_Affinity_* columns.
            - pd.Categorical on eligibility_status, journey_status,
              behavior_profile, trigger_name, segment.
            - Dynamic Creative_Affinity_{ad_name} columns reconciled via
              reconcile_creative_affinity_columns().

        Raises:
            InputValidationError: If trigger_df is missing the User_ID column.
            InputValidationError: If previous_state_df is supplied but missing
                required columns.

        Notes:
            ARCH-015: eligibility_status is set to EligibilityStatus.NEW for
            all new users. AudienceManager owns all eligibility transitions.
            FR-USM-004: campaign_id is always sourced from self._config.campaign_id,
            including for returning users.
            ARCH-011/PV-001: no iterrows(); all operations are vectorised.
        """
        # ── Validate trigger_df ─────────────────────────────────────────
        if "User_ID" not in trigger_df.columns:
            raise InputValidationError(
                "trigger_df",
                "Missing required column: User_ID",
            )

        # ── Validate previous_state_df schema if supplied ───────────────
        if previous_state_df is not None and len(previous_state_df) > 0:
            missing = [
                c for c in USER_STATE_REQUIRED_COLUMNS
                if c not in previous_state_df.columns
            ]
            if missing:
                raise InputValidationError(
                    "previous_state_df",
                    f"Missing required columns: {missing}",
                )

        # ── Drop null User_IDs ──────────────────────────────────────────
        null_mask = trigger_df["User_ID"].isna()
        if null_mask.any():
            n_null = int(null_mask.sum())
            logger.warning(
                "UserStateManager: %d row(s) with null User_ID dropped from trigger_df",
                n_null,
            )
            trigger_df = trigger_df[~null_mask].copy()

        # ── Deduplicate User_IDs in trigger_df ─────────────────────────
        dup_mask = trigger_df["User_ID"].duplicated(keep=False)
        if dup_mask.any():
            n_dup = int(trigger_df.loc[dup_mask, "User_ID"].nunique())
            logger.warning(
                "UserStateManager: %d duplicate User_ID(s) in trigger_df — deduplicated",
                n_dup,
            )
            trigger_df = trigger_df.drop_duplicates(subset=["User_ID"])

        trigger_user_ids: set[str] = set(trigger_df["User_ID"])

        # ── Determine user sets ─────────────────────────────────────────
        if previous_state_df is not None and len(previous_state_df) > 0:
            prior_user_ids: set[str] = set(previous_state_df["user_id"])
        else:
            prior_user_ids = set()

        new_user_ids = trigger_user_ids - prior_user_ids
        returning_ids = trigger_user_ids & prior_user_ids
        departed_ids = prior_user_ids - trigger_user_ids

        for uid in sorted(departed_ids):
            logger.warning(
                "UserStateManager: user '%s' in previous_state_df not in trigger_df"
                " — excluded from output",
                uid,
            )

        # ── Build new-user rows ─────────────────────────────────────────
        new_rows_df = self._build_new_user_records(list(new_user_ids))

        # ── Build returning-user rows ───────────────────────────────────
        if returning_ids:
            returning_rows_df = (
                previous_state_df[previous_state_df["user_id"].isin(returning_ids)]
                .copy()
            )
            returning_rows_df["campaign_id"] = self._config.campaign_id  # FR-USM-004
            returning_rows_df["run_count"] = returning_rows_df["run_count"] + 1
        else:
            returning_rows_df = pd.DataFrame()

        # ── Concat ─────────────────────────────────────────────────────
        parts = [df for df in (new_rows_df, returning_rows_df) if len(df) > 0]
        if parts:
            state_df = pd.concat(parts, ignore_index=True)
        else:
            state_df = new_rows_df  # empty with correct columns

        # ── Cast float columns to float32 (FR-USM-008) ─────────────────
        for col in _FLOAT32_COLS:
            if col in state_df.columns:
                logger.debug("UserStateManager: cast %s to float32", col)
                state_df[col] = state_df[col].astype("float32")

        # ── Apply pd.Categorical dtype (FR-USM-009) ─────────────────────
        elig_cats = [e.value for e in EligibilityStatus]
        journey_cats = [j.value for j in JourneyStatus]
        profile_cats = [b.value for b in BehaviorProfile]

        _cat_categories = {
            "eligibility_status": elig_cats,
            "journey_status": journey_cats,
            "behavior_profile": profile_cats,
            "trigger_name": None,
            "segment": None,
        }
        for col, cats in _cat_categories.items():
            if col in state_df.columns:
                state_df[col] = pd.Categorical(state_df[col], categories=cats)

        # ── Reconcile Creative_Affinity_* columns (ARCH-012) ───────────
        state_df = reconcile_creative_affinity_columns(state_df, self._config)

        # ── Validate required columns are present (USM-V-003) ──────────
        missing_cols = [c for c in USER_STATE_REQUIRED_COLUMNS if c not in state_df.columns]
        assert not missing_cols, (
            f"UserStateManager: output is missing required columns: {missing_cols}"
        )

        n_new = len(new_user_ids)
        n_ret = len(returning_ids)
        n_total = len(state_df)
        logger.info(
            "UserStateManager: initialized %d users (%d new, %d returning)",
            n_total, n_new, n_ret,
        )

        return state_df

    def update_user(
        self,
        state_df: pd.DataFrame,
        user_id: str,
        updates: dict[str, Any],
    ) -> pd.DataFrame:
        """Apply field updates to a single user without mutating the input.

        Args:
            state_df: Current state DataFrame. **Not mutated.**
            user_id: The ``user_id`` value to locate in state_df.
            updates: Mapping of column name → new value. Only the specified
                columns are changed; all others are unaffected.

        Returns:
            New pd.DataFrame identical to state_df except the target user's
            specified columns carry the new values.

        Raises:
            KeyError: If user_id is not found in state_df["user_id"].
            ValueError: If any key in updates is not a column in state_df.

        Notes:
            ARCH-011/FR-USM-010: uses boolean mask + .copy() + .loc[] — no iterrows().
        """
        # Validate columns
        invalid_cols = [k for k in updates if k not in state_df.columns]
        if invalid_cols:
            raise ValueError(
                f"update_user: column(s) {invalid_cols} not found in state_df"
            )

        # Validate user exists
        mask = state_df["user_id"] == user_id
        if not mask.any():
            raise KeyError(f"update_user: user_id '{user_id}' not found in state_df")

        df = state_df.copy()
        for col, val in updates.items():
            df.loc[mask, col] = val

        return df

    def finalize_state(
        self,
        state_df: pd.DataFrame,
        as_of_date: date,
    ) -> pd.DataFrame:
        """Set state_as_of_date on every row to the given simulation date.

        Called by the run controller as the last operation before passing state
        to the export engine (FR-USM-011). Does not mutate the input.

        Args:
            state_df: The state DataFrame to finalise.
            as_of_date: The simulation's as-of date (typically the last
                simulation date in the current run).

        Returns:
            New pd.DataFrame with state_as_of_date set to as_of_date on
            every row.

        Raises:
            Nothing.
        """
        df = state_df.copy()
        df["state_as_of_date"] = as_of_date
        return df

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    def _build_new_user_records(
        self,
        new_user_ids: list[str],
    ) -> pd.DataFrame:
        """Build a DataFrame of new-user state records at canonical defaults.

        Calls UserState.new() for each user_id and converts the resulting
        dataclass instances to a DataFrame via pd.DataFrame.from_records().
        Immediately calls reconcile_creative_affinity_columns() to expand
        the creative_affinities dict column to individual columns.

        Args:
            new_user_ids: List of user ID strings for which new state records
                must be created.

        Returns:
            pd.DataFrame with one row per user_id, all fields at canonical
            defaults from UserState.new(). creative_affinities column has
            been expanded to Creative_Affinity_{ad_name} columns.

        Notes:
            ARCH-011/PV-001: the list comprehension over new_user_ids is the
            ONLY approved construction path — it constructs dataclass instances
            (not raw dicts) and converts in bulk via pd.DataFrame.from_records().
            This is O(n) and does not iterate over DataFrame rows.
            If new_user_ids is empty, returns an empty DataFrame with the
            correct column structure (including all 35 static columns).
        """
        ad_names = self._config.get_ad_names()

        if not new_user_ids:
            # Build a dummy record to capture the column schema, then slice to 0 rows
            dummy = UserState.new(
                campaign_id=self._config.campaign_id,
                user_id="__schema_probe__",
                state_as_of_date=self._config.simulation_start_date,
                ad_names=ad_names,
            )
            df = pd.DataFrame.from_records([dataclasses.asdict(dummy)])
            df = df.iloc[0:0].copy()
        else:
            records = [
                UserState.new(
                    campaign_id=self._config.campaign_id,
                    user_id=uid,
                    state_as_of_date=self._config.simulation_start_date,
                    ad_names=ad_names,
                )
                for uid in new_user_ids
            ]
            df = pd.DataFrame.from_records(
                [dataclasses.asdict(r) for r in records]
            )

        # Expand creative_affinities dict column → Creative_Affinity_* columns
        df = reconcile_creative_affinity_columns(df, self._config)
        return df


__all__ = ["UserStateManager"]
