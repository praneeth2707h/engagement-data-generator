"""Stage 4 — Audience Resolution.

AudienceManager is responsible for resolving trigger assignments, segment
assignments, eligibility classifications, and per-trigger remaining capacity
(TCC) for all users in the initialized state DataFrame.

Architecture references
-----------------------
* ARCH-003   — Stage 4 in the 11-stage pipeline
* ARCH-011 / PV-001 — no iterrows(); vectorised operations only
* ARCH-013   — alphabetical Trigger_Name tiebreak for equal-priority triggers
* ARCH-014   — segment follows winning trigger row (same sort chain)
* ARCH-015   — EligibilityStatus canonical values (6 values)
* ARCH-018   — JourneyStatus.DROPPED → EligibilityStatus.EXCLUDED (highest priority)
* ARCH-020   — allow_reentry controls RE_ENTRY vs EXCLUDED for cooling-expired users
* C-002      — campaign filter (keep Campaign_ID == config.campaign_id or "Default")
* BIZ-010    — TCC formula with math.ceil() (REM-003 / TCC-001 fix)
* FR-AUD-001 through FR-AUD-013 — functional requirements
* PHASE_3_WAVE_1_BUILD_CONTRACT.md §3 — method signatures and contracts
"""
from __future__ import annotations

import math
import pandas as pd
import numpy as np
from datetime import date

from models.config_registry import ConfigRegistry
from models.capacity_row import RemainingCapacityRow
from models.enums import EligibilityStatus, JourneyStatus
from utils.constants import TRIGGER_HISTORY_DELIMITER
from utils.exceptions import InputValidationError
from utils.logger import get_logger

logger = get_logger(__name__)

# Required columns for trigger_df input (AUD-V-001)
_TRIGGER_REQUIRED_COLS: tuple[str, ...] = (
    "Campaign_ID", "User_ID", "Trigger_Name", "Segment"
)

# Required columns for state_df input
_STATE_REQUIRED_COLS: tuple[str, ...] = (
    "user_id", "campaign_id", "journey_status", "cooling_period_end"
)

# Canonical Phase 3 EligibilityStatus values (in display order)
_CANONICAL_ELIGIBILITY: list[str] = [
    EligibilityStatus.NEW.value,
    EligibilityStatus.ACTIVE.value,
    EligibilityStatus.COOLING.value,
    EligibilityStatus.RE_ENTRY.value,
    EligibilityStatus.SKIPPED.value,
    EligibilityStatus.EXCLUDED.value,
]

# Statuses that count as "eligible" for capacity cap purposes
_ELIGIBLE_STATUSES: frozenset[str] = frozenset({
    EligibilityStatus.NEW.value,
    EligibilityStatus.ACTIVE.value,
    EligibilityStatus.RE_ENTRY.value,
})


class AudienceManager:
    """Stage 4 — Audience Resolution.

    Resolves trigger assignments, segment assignments, eligibility
    classifications, and per-trigger remaining capacity (TCC) for all users
    in the initialized state DataFrame.

    New users with ``journey_status = Not_Started`` are classified NEW.
    Users with active cooling periods are classified COOLING.
    Users whose cooling period expired are classified RE_ENTRY (allow_reentry=True)
    or EXCLUDED (allow_reentry=False, ARCH-020).
    Users with ``journey_status = Dropped`` are always EXCLUDED (ARCH-018).
    All other users default to SKIPPED.

    Args:
        config: The ConfigRegistry for the current campaign run.

    References:
        PHASE_3_WAVE_1_BUILD_CONTRACT.md §3
        ARCH-013, ARCH-014, ARCH-015, ARCH-018, ARCH-020
    """

    def __init__(self, config: ConfigRegistry) -> None:
        """Initialize with the campaign ConfigRegistry.

        Args:
            config: Fully constructed ConfigRegistry for this run.
                Stored as self._config.

        Returns:
            None

        Raises:
            Nothing.
        """
        self._config = config

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def resolve(
        self,
        trigger_df: pd.DataFrame,
        historical_df: pd.DataFrame | None,
        state_df: pd.DataFrame,
        as_of_date: date,
    ) -> tuple[pd.DataFrame, list[RemainingCapacityRow]]:
        """Resolve audience: triggers, segments, eligibility, and capacity.

        Orchestrates the full Stage 4 pipeline in the mandated call order:
        1. apply_campaign_filter(trigger_df)
        2. resolve_triggers(filtered_df, state_df)
        3. resolve_segments(winner_df, state_df)
        4. classify_eligibility(state_df, as_of_date)
        5. compute_remaining_capacity(historical_df, filtered_df)

        Args:
            trigger_df: Raw (unfiltered) trigger DataFrame from Stage 2.
                Must have columns: Campaign_ID, User_ID, Trigger_Name, Segment.
            historical_df: Historical engagement DataFrame or None.
                If None, historical_engaged_users = 0 for all triggers.
            state_df: Initialized state DataFrame from UserStateManager.
                Must have columns: user_id, campaign_id, journey_status,
                cooling_period_end.
            as_of_date: Simulation date for eligibility classification.

        Returns:
            Tuple of (resolved_df, capacity_list):
                - resolved_df: state_df with all audience fields populated
                  and _priority working column removed.
                - capacity_list: list[RemainingCapacityRow], one per trigger
                  in config.triggers.

        Raises:
            InputValidationError: If trigger_df or state_df is missing required
                columns.
        """
        # ── Validate inputs ─────────────────────────────────────────────
        missing_t = [c for c in _TRIGGER_REQUIRED_COLS if c not in trigger_df.columns]
        if missing_t:
            raise InputValidationError(
                "trigger_df", f"Missing required columns: {missing_t}"
            )
        missing_s = [c for c in _STATE_REQUIRED_COLS if c not in state_df.columns]
        if missing_s:
            raise InputValidationError(
                "state_df", f"Missing required columns: {missing_s}"
            )

        # ── 1. Campaign filter (C-002) ───────────────────────────────────
        filtered_df = self.apply_campaign_filter(trigger_df)

        if len(filtered_df) == 0:
            logger.warning(
                "AudienceManager: zero rows remain after C-002 campaign filter"
                " — returning state_df unchanged with empty capacity list."
            )
            return state_df, []

        # ── Pre-compute winner_df once (used by resolve_triggers + resolve_segments) ──
        winner_df = self._compute_winner_df(filtered_df)

        # ── 2. Resolve triggers ──────────────────────────────────────────
        state_df = self.resolve_triggers(filtered_df, state_df)

        # ── 3. Resolve segments ──────────────────────────────────────────
        # resolve_segments requires deduplicated (one-row-per-user) input
        state_df = self.resolve_segments(winner_df, state_df)

        # ── 4. Classify eligibility ──────────────────────────────────────
        state_df = self.classify_eligibility(state_df, as_of_date)

        # ── Post-classification: users with no valid trigger → SKIPPED ───
        # §3.19: "User with no valid trigger: Classified SKIPPED by np.select default."
        # trigger_name is None for users whose only rows were unknown/excluded (AUD-V-003).
        # journey_status=NOT_STARTED would otherwise make condition 6 fire → NEW,
        # so we override here after classification.
        no_trigger_mask = state_df["trigger_name"].isna()
        if no_trigger_mask.any():
            state_df.loc[no_trigger_mask, "eligibility_status"] = (
                EligibilityStatus.SKIPPED.value
            )

        # ── 5. Compute remaining capacity ────────────────────────────────
        capacity = self.compute_remaining_capacity(historical_df, filtered_df)

        # ── Log summary ──────────────────────────────────────────────────
        sc = state_df["eligibility_status"].value_counts()
        logger.info(
            "AudienceManager: resolved %d users. Eligibility: "
            "New=%d, Active=%d, Cooling=%d, Re_Entry=%d, Skipped=%d, Excluded=%d",
            len(state_df),
            int(sc.get(EligibilityStatus.NEW.value, 0)),
            int(sc.get(EligibilityStatus.ACTIVE.value, 0)),
            int(sc.get(EligibilityStatus.COOLING.value, 0)),
            int(sc.get(EligibilityStatus.RE_ENTRY.value, 0)),
            int(sc.get(EligibilityStatus.SKIPPED.value, 0)),
            int(sc.get(EligibilityStatus.EXCLUDED.value, 0)),
        )

        return state_df, capacity

    def classify_eligibility(
        self,
        state_df: pd.DataFrame,
        as_of_date: date,
    ) -> pd.DataFrame:
        """Classify each user into one of six canonical EligibilityStatus values.

        Uses np.select() with 7 conditions in mandated priority order
        (ARCH-015, ARCH-018, ARCH-020). The FIRST matching condition wins.

        Condition priority (highest → lowest):
        1. DROPPED journey → EXCLUDED (ARCH-018, always highest)
        2. cooling_period_end > as_of_date → COOLING
        3. cooling_period_end <= as_of_date AND allow_reentry=True → RE_ENTRY
        4. cooling_period_end <= as_of_date AND allow_reentry=False → EXCLUDED
        5. journey_status = Active → ACTIVE
        6. journey_status = Not_Started → NEW
        7. Default → SKIPPED

        Args:
            state_df: State DataFrame with journey_status and cooling_period_end
                populated.
            as_of_date: The simulation date as of which eligibility is assessed.

        Returns:
            New pd.DataFrame with eligibility_status set for all rows as
            pd.Categorical using canonical EligibilityStatus values as categories.

        Raises:
            Nothing.

        References:
            ARCH-015, ARCH-018, ARCH-020, FR-AUD-009, FR-AUD-010
        """
        df = state_df.copy()

        # ── Coerce cooling_period_end for consistent comparisons ─────────
        as_of_ts = pd.Timestamp(as_of_date)
        cooling_ts = pd.to_datetime(df["cooling_period_end"], errors="coerce")

        # ── Prerequisite masks ───────────────────────────────────────────
        mask_dropped = df["journey_status"] == JourneyStatus.DROPPED.value
        mask_cooling_active = cooling_ts.notna() & (cooling_ts > as_of_ts)
        mask_cooling_expired = cooling_ts.notna() & (cooling_ts <= as_of_ts)

        # ── Condition 1 — DROPPED → EXCLUDED (ARCH-018, highest priority) ─
        cond_dropped_excluded = mask_dropped

        # ── Condition 2 — Cooling still active → COOLING ─────────────────
        cond_cooling = (~mask_dropped) & mask_cooling_active

        # ── Condition 3 — Cooling expired + allow_reentry=True → RE_ENTRY ─
        cond_reentry = (
            (~mask_dropped)
            & mask_cooling_expired
            & (self._config.allow_reentry is True)
        )

        # ── Condition 4 — Cooling expired + allow_reentry=False → EXCLUDED ─
        cond_expired_excluded = (
            (~mask_dropped)
            & mask_cooling_expired
            & (self._config.allow_reentry is not True)
        )

        # ── Condition 5 — Active journey → ACTIVE ────────────────────────
        cond_active = (
            (~mask_dropped)
            & (~mask_cooling_active)
            & (~mask_cooling_expired)
            & (df["journey_status"] == JourneyStatus.ACTIVE.value)
        )

        # ── Condition 6 — Never started → NEW ────────────────────────────
        cond_new = (
            (~mask_dropped)
            & (~mask_cooling_active)
            & (~mask_cooling_expired)
            & (df["journey_status"] == JourneyStatus.NOT_STARTED.value)
        )

        # ── np.select — 7-condition vectorized classification (AUD-V-010) ─
        df["eligibility_status"] = np.select(
            condlist=[
                cond_dropped_excluded,
                cond_cooling,
                cond_reentry,
                cond_expired_excluded,
                cond_active,
                cond_new,
            ],
            choicelist=[
                EligibilityStatus.EXCLUDED.value,   # "Excluded"
                EligibilityStatus.COOLING.value,    # "Cooling"
                EligibilityStatus.RE_ENTRY.value,   # "Re_Entry"  ← underscore (ARCH-015)
                EligibilityStatus.EXCLUDED.value,   # "Excluded"
                EligibilityStatus.ACTIVE.value,     # "Active"
                EligibilityStatus.NEW.value,        # "New"
            ],
            default=EligibilityStatus.SKIPPED.value,  # "Skipped"
        )

        # ── Cast to pd.Categorical ───────────────────────────────────────
        df["eligibility_status"] = pd.Categorical(
            df["eligibility_status"],
            categories=_CANONICAL_ELIGIBILITY,
        )

        return df

    def apply_tiebreak_sort(
        self,
        trigger_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Sort trigger_df by priority → Trigger_Name → Segment, keep first per user.

        Implements ARCH-013 (alphabetical Trigger_Name tiebreak for equal-priority
        triggers) and ARCH-014 (segment follows winning trigger; alphabetical Segment
        resolves the pathological same-priority/same-name case).

        All three sort keys are ascending:
        - _priority ascending: lower number = higher priority (1 > 2).
        - Trigger_Name ascending: alphabetically first wins on priority tie.
        - Segment ascending: alphabetically first wins on priority+name tie.

        Args:
            trigger_df: Trigger DataFrame with _priority, Trigger_Name, and
                Segment columns present. _priority must be added upstream before
                calling this method.

        Returns:
            Sorted and deduplicated pd.DataFrame with exactly one row per
            (Campaign_ID, User_ID) pair — the winning row. Still contains the
            _priority working column; caller is responsible for dropping it from
            the final state_df output.

        Raises:
            Nothing.

        References:
            ARCH-013, ARCH-014, FR-AUD-002, FR-AUD-007, §3.11
        """
        winner_df = (
            trigger_df
            .sort_values(
                ["_priority", "Trigger_Name", "Segment"],
                ascending=[True, True, True],
            )
            .drop_duplicates(subset=["Campaign_ID", "User_ID"], keep="first")
        )
        return winner_df.reset_index(drop=True)

    def compute_remaining_capacity(
        self,
        historical_df: pd.DataFrame | None,
        filtered_trigger_df: pd.DataFrame,
    ) -> list[RemainingCapacityRow]:
        """Compute per-trigger remaining TCC capacity.

        For each trigger in config.triggers:
            total_users = rows in filtered_trigger_df for this trigger name
            target_engaged_users = math.ceil(total_users × engagement_rate_target)
            historical_engaged_users = distinct User_IDs in windowed historical_df
            remaining_capacity = max(0, target_engaged_users − historical_engaged_users)

        Args:
            historical_df: Historical engagement DataFrame or None.
                Optional columns: Date (for window filter), Trigger_Name (for
                per-trigger filtering). If None, historical_engaged_users = 0.
            filtered_trigger_df: Campaign-filtered trigger DataFrame (C-002 applied).

        Returns:
            list[RemainingCapacityRow], one entry per trigger in config.triggers,
            in the same order as config.triggers.

        Raises:
            Nothing.

        References:
            FR-AUD-011, BIZ-010, TCC-001 (math.ceil is mandatory — not int()),
            BRC-009 (historical window applied using simulation_start_date)
        """
        # Compute historical window cutoff using simulation_start_date as reference
        cutoff_date = self._config.get_historical_cutoff_date(
            self._config.simulation_start_date
        )

        capacity_list: list[RemainingCapacityRow] = []

        for trigger in self._config.triggers:
            # Total users for this trigger in the current run (§3.10)
            trig_mask = filtered_trigger_df["Trigger_Name"] == trigger.trigger_name
            total_users = int(trig_mask.sum())

            # Historical engaged users
            historical_engaged = 0
            if historical_df is not None and len(historical_df) > 0:
                h = historical_df.copy()

                # Apply historical window filter (BRC-009)
                if cutoff_date is not None and "Date" in h.columns:
                    h = h[pd.to_datetime(h["Date"], errors="coerce") >= pd.Timestamp(cutoff_date)]

                # Filter by Trigger_Name if available (§3.10)
                if "Trigger_Name" in h.columns:
                    h = h[h["Trigger_Name"] == trigger.trigger_name]

                historical_engaged = int(h["User_ID"].nunique())

            row = RemainingCapacityRow.compute(
                total_users=total_users,
                target_engagement_rate=trigger.engagement_rate_target,
                historical_engaged_users=historical_engaged,
            )

            logger.debug(
                "AudienceManager: trigger '%s': total=%d, target=%d, "
                "historical=%d, remaining=%d",
                trigger.trigger_name,
                total_users,
                row.target_engaged_users,
                historical_engaged,
                row.remaining_capacity,
            )

            capacity_list.append(row)

        return capacity_list

    def apply_capacity_cap(
        self,
        state_df: pd.DataFrame,
        capacity_list: list[RemainingCapacityRow],
    ) -> pd.DataFrame:
        """Reclassify excess eligible users as SKIPPED based on per-trigger capacity.

        For each trigger, retains at most remaining_capacity users in
        NEW/ACTIVE/RE_ENTRY status. Users beyond that count are reclassified
        to SKIPPED in the order they appear in state_df (tiebreak sort already
        applied upstream).

        Users already COOLING or EXCLUDED are never affected.

        Args:
            state_df: State DataFrame post-eligibility classification.
            capacity_list: Capacity rows from compute_remaining_capacity(),
                aligned with config.triggers order.

        Returns:
            Updated pd.DataFrame with excess eligible users marked SKIPPED.
            Input is not mutated.

        Raises:
            Nothing.

        References:
            FR-AUD-011, §3.19 edge cases
        """
        df = state_df.copy()

        # Build trigger_name → RemainingCapacityRow map aligned with config.triggers
        trigger_to_cap: dict[str, RemainingCapacityRow] = {}
        for i, trig in enumerate(self._config.triggers):
            if i < len(capacity_list):
                trigger_to_cap[trig.trigger_name] = capacity_list[i]

        for trig_name, cap_row in trigger_to_cap.items():
            # Eligible users for this trigger
            is_this_trigger = df["trigger_name"] == trig_name
            is_eligible = df["eligibility_status"].isin(_ELIGIBLE_STATUSES)
            eligible_mask = is_this_trigger & is_eligible

            n_eligible = int(eligible_mask.sum())
            n_capacity = cap_row.remaining_capacity

            if n_eligible <= n_capacity:
                continue  # All fit within capacity

            # Rows beyond capacity → SKIPPED
            eligible_indices = df.index[eligible_mask].tolist()
            skip_indices = eligible_indices[n_capacity:]
            df.loc[skip_indices, "eligibility_status"] = EligibilityStatus.SKIPPED.value

        return df

    def resolve_triggers(
        self,
        filtered_trigger_df: pd.DataFrame,
        state_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Assign each user their winning trigger and update trigger history fields.

        Steps:
        1. Compute winner_df (priority map → filter unknowns → sort → dedup).
        2. Log unknown Trigger_Name exclusions (AUD-V-003).
        3. Log ARCH-013 tiebreaks (AUD-V-005, FR-AUD-003).
        4. Merge winning trigger_name and trigger_date into state_df.
        5. Update trigger_history (append with TRIGGER_HISTORY_DELIMITER).
        6. Set first_trigger_name and first_trigger_date (idempotent — set once).
        7. Increment total_trigger_appearances.
        8. Log users with no valid trigger (AUD-005).

        Args:
            filtered_trigger_df: Campaign-filtered trigger DataFrame (C-002 applied).
            state_df: Initialized state DataFrame.

        Returns:
            Updated state_df with trigger fields populated. No _priority column
            is written to state_df — it exists only on the internal working copy.

        Raises:
            Nothing. All anomalies produce WARNING logs.

        References:
            ARCH-013, FR-AUD-002, FR-AUD-003, FR-AUD-004, FR-AUD-013
        """
        df = state_df.copy()

        winner_df = self._compute_winner_df(filtered_trigger_df)

        if len(winner_df) == 0:
            # No valid trigger rows — log users with no assignment
            for uid in sorted(df["user_id"].unique()):
                logger.warning(
                    "[AUD-005] User '%s' has no valid trigger assignments"
                    " — classified SKIPPED.",
                    uid,
                )
            return df

        # ── Users with no valid trigger ──────────────────────────────────
        users_with_trigger = set(winner_df["User_ID"])
        users_without_trigger = set(df["user_id"]) - users_with_trigger
        for uid in sorted(users_without_trigger):
            logger.warning(
                "[AUD-005] User '%s' has no valid trigger assignments"
                " — classified SKIPPED.",
                uid,
            )

        # ── Merge winning trigger info into state_df (vectorized join) ───
        # winner_df uses Pascal_Case; state_df uses snake_case
        trigger_date_col = "Trigger_Date" if "Trigger_Date" in winner_df.columns else None
        cols = ["User_ID", "Trigger_Name"]
        if trigger_date_col:
            cols.append(trigger_date_col)

        winner_lookup = winner_df[cols].rename(
            columns={
                "User_ID": "user_id",
                "Trigger_Name": "_win_trigger",
                **({"Trigger_Date": "_win_date"} if trigger_date_col else {}),
            }
        )

        df = df.merge(winner_lookup, on="user_id", how="left")

        mask_new = df["_win_trigger"].notna()
        mask_hist = df["trigger_history"].notna()

        # ── Update trigger_history ───────────────────────────────────────
        # ARCH-017: TRIGGER_HISTORY_DELIMITER constant — no inline "|"
        df["trigger_history"] = np.where(
            mask_new & mask_hist,
            df["trigger_history"].astype(str)
            + TRIGGER_HISTORY_DELIMITER
            + df["_win_trigger"].astype(str),
            np.where(
                mask_new & ~mask_hist,
                df["_win_trigger"],
                df["trigger_history"],
            ),
        )

        # ── first_trigger_name: set only if currently None (idempotent) ──
        first_name_unset = df["first_trigger_name"].isna()
        df.loc[first_name_unset & mask_new, "first_trigger_name"] = (
            df.loc[first_name_unset & mask_new, "_win_trigger"]
        )

        # ── first_trigger_date: set only if currently None (idempotent) ──
        if trigger_date_col:
            first_date_unset = df["first_trigger_date"].isna()
            df.loc[first_date_unset & mask_new, "first_trigger_date"] = (
                df.loc[first_date_unset & mask_new, "_win_date"]
            )

        # ── total_trigger_appearances: increment by 1 for users with a trigger ──
        df.loc[mask_new, "total_trigger_appearances"] = (
            df.loc[mask_new, "total_trigger_appearances"] + 1
        )

        # ── trigger_name ─────────────────────────────────────────────────
        df["trigger_name"] = df["_win_trigger"]

        # ── Cast trigger_name to Categorical ─────────────────────────────
        df["trigger_name"] = pd.Categorical(df["trigger_name"])

        # ── Drop working columns ─────────────────────────────────────────
        drop_cols = ["_win_trigger"]
        if trigger_date_col:
            drop_cols.append("_win_date")
        df = df.drop(columns=drop_cols)

        return df.reset_index(drop=True)

    def resolve_segments(
        self,
        resolved_trigger_df: pd.DataFrame,
        state_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Assign each user their segment from the winning trigger row (ARCH-014).

        Segment follows the winning trigger, not an independent alphabetical sort.
        The resolved_trigger_df must already be deduplicated (one row per user);
        call apply_tiebreak_sort() before this method.

        Args:
            resolved_trigger_df: One row per user — output of apply_tiebreak_sort().
                Must not contain duplicate (Campaign_ID, User_ID) pairs.
            state_df: State DataFrame after resolve_triggers().

        Returns:
            Updated state_df with segment populated from the winning trigger row
            as pd.Categorical.

        Raises:
            AssertionError: If resolved_trigger_df contains duplicate
                (Campaign_ID, User_ID) pairs — this indicates a logic error in
                resolve_triggers(). (AUD-V-006)

        References:
            ARCH-014, FR-AUD-006, FR-AUD-007, AUD-V-006
        """
        # AUD-V-006: assert no duplicate (Campaign_ID, User_ID) pairs
        dupes = resolved_trigger_df.duplicated(subset=["Campaign_ID", "User_ID"])
        assert not dupes.any(), (
            "resolve_segments: resolved_trigger_df contains duplicate "
            "(Campaign_ID, User_ID) pairs — logic error in resolve_triggers(). "
            f"Duplicated users: {resolved_trigger_df.loc[dupes, 'User_ID'].tolist()}"
        )

        if len(resolved_trigger_df) == 0:
            return state_df.copy()

        df = state_df.copy()

        # Vectorized segment assignment via merge
        seg_lookup = resolved_trigger_df[["User_ID", "Segment"]].rename(
            columns={"User_ID": "user_id", "Segment": "_win_segment"}
        )
        df = df.merge(seg_lookup, on="user_id", how="left")
        df["segment"] = df["_win_segment"]
        df = df.drop(columns=["_win_segment"])

        # Cast to Categorical
        df["segment"] = pd.Categorical(df["segment"])

        return df.reset_index(drop=True)

    def apply_campaign_filter(
        self,
        trigger_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Apply C-002 campaign filter — keep only matching Campaign_ID rows.

        Retains rows where Campaign_ID == config.campaign_id or == "Default".
        Logs a WARNING if any rows are excluded.

        Args:
            trigger_df: Raw trigger DataFrame.

        Returns:
            Filtered pd.DataFrame with only matching Campaign_ID rows.

        Raises:
            Nothing.

        References:
            C-002, FR-AUD-001
        """
        campaign_id = self._config.campaign_id
        mask = (trigger_df["Campaign_ID"] == campaign_id) | (
            trigger_df["Campaign_ID"] == "Default"
        )
        filtered = trigger_df[mask].copy().reset_index(drop=True)

        n_excluded = len(trigger_df) - len(filtered)
        if n_excluded > 0:
            logger.warning(
                "AudienceManager: C-002 campaign filter excluded %d rows "
                "(campaign_id=%r).",
                n_excluded,
                campaign_id,
            )

        return filtered

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    def _compute_winner_df(
        self,
        filtered_trigger_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Add _priority, filter unknown triggers, sort, and deduplicate.

        Used internally by both resolve_triggers() and resolve() so that
        resolve_segments() always receives one-row-per-user data.

        Steps:
        1. Map Trigger_Name → priority from config.
        2. Log WARNING and remove unknown Trigger_Name values (AUD-V-003).
        3. Detect and log ARCH-013 tiebreaks (AUD-V-005).
        4. Detect and log ARCH-014 pathological duplicate-segment case.
        5. Call apply_tiebreak_sort() to produce one winner per user.

        Args:
            filtered_trigger_df: Campaign-filtered trigger DataFrame.

        Returns:
            pd.DataFrame with one row per (Campaign_ID, User_ID), with
            _priority column still present (dropped at state_df write time).

        References:
            ARCH-013, ARCH-014, §3.11, AUD-V-003, AUD-V-005
        """
        if len(filtered_trigger_df) == 0:
            return filtered_trigger_df.copy()

        working = filtered_trigger_df.copy()

        # ── Add _priority working column ─────────────────────────────────
        priority_map = {t.trigger_name: t.priority for t in self._config.triggers}
        working["_priority"] = working["Trigger_Name"].map(priority_map)

        # ── Exclude unknown triggers (AUD-V-003) ─────────────────────────
        unknown_mask = working["_priority"].isna()
        if unknown_mask.any():
            for name in sorted(working.loc[unknown_mask, "Trigger_Name"].unique()):
                n = int((working["Trigger_Name"] == name).sum())
                logger.warning(
                    "[C-002/AUD-004] Trigger_Name '%s' not found in "
                    "ConfigRegistry — %d rows excluded.",
                    name, n,
                )
            working = working[~unknown_mask].copy()

        if len(working) == 0:
            return working

        # ── Detect ARCH-013 tiebreaks ────────────────────────────────────
        # A tiebreak fires when ≥2 rows for the same user share the same priority
        dup_pri = working.duplicated(
            subset=["Campaign_ID", "User_ID", "_priority"], keep=False
        )
        if dup_pri.any():
            tied = working[dup_pri]
            tied_names = sorted(tied["Trigger_Name"].unique())
            n_tied_users = int(tied["User_ID"].nunique())
            winner_name = tied_names[0] if tied_names else ""
            logger.warning(
                "[ARCH-013 tiebreak] %d user(s) had equal-priority triggers. "
                "Tied: %s. Winner: %s (alphabetical).",
                n_tied_users, tied_names, winner_name,
            )

        # ── Detect ARCH-014 pathological: same priority+name, multiple segments ──
        dup_trig = working.duplicated(
            subset=["Campaign_ID", "User_ID", "_priority", "Trigger_Name"], keep=False
        )
        if dup_trig.any():
            patho = working[dup_trig]
            # Group by (User_ID, Trigger_Name) — small number of groups
            grp = patho.groupby(["User_ID", "Trigger_Name"])["Segment"].apply(
                lambda s: sorted(s.unique())
            )
            for (uid, tname), segs in grp.items():
                if len(segs) > 1:
                    logger.warning(
                        "[ARCH-014] User '%s' has multiple segment values for "
                        "trigger '%s' — selected '%s' (alphabetical).",
                        uid, tname, segs[0],
                    )

        # ── Apply tiebreak sort and deduplicate ──────────────────────────
        winner_df = self.apply_tiebreak_sort(working)

        return winner_df


__all__ = ["AudienceManager"]
