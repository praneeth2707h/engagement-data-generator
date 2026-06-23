"""Stage 5 -- Journey Building.

JourneyEngine advances user journeys through the configured ad sequence.
It is the sole owner of the journey-progression fields in the user state
DataFrame and is the only module permitted to write them.

Owned state fields (Phase 4):
    current_ad, days_in_ad, journey_start_date, journey_completion_date,
    cooling_period_end, journey_status, channel, vendor, ad_click_received.

Architecture decisions implemented:
    BIZ-018 / C-001 -- Move On Click is exclusive: skip duration check if
                       click-advance fires on the same simulation day.
    C-004           -- Re-entry begins from Ad1; prior journey_completion_date
                       is preserved for TER/TCC historical calculations.
    ARCH-003        -- Stage 5 in the 11-stage simulation pipeline.
    ARCH-011        -- No iterrows(); all classification and advance logic
                       uses vectorized boolean-mask operations.

days_in_ad semantics:
    0 when a user first enters an ad (set by _start_journeys or after advance).
    Incremented by 1 at the start of every advance() call for all active users.
    Advance condition: days_in_ad >= ad.duration_days  (after increment).
    None when not in any journey (journey_status != Active).

Cooling period formula (PHASE_3_EXECUTION_PLAN.md section 7.2):
    cooling_period_end = journey_completion_date + timedelta(days=config.cooling_period_days)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd

from models.ad_config import AdConfig
from models.config_registry import ConfigRegistry
from models.enums import EligibilityStatus, JourneyStatus
from utils.exceptions import InputValidationError
from utils.logger import get_logger


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_JOURNEY_START_STATUSES: frozenset[str] = frozenset({
    EligibilityStatus.NEW.value,
    EligibilityStatus.RE_ENTRY.value,
})

_ELIGIBLE_FOR_JOURNEY: frozenset[str] = frozenset({
    EligibilityStatus.NEW.value,
    EligibilityStatus.ACTIVE.value,
    EligibilityStatus.RE_ENTRY.value,
})

_STATE_REQUIRED_COLS: tuple[str, ...] = (
    "user_id",
    "eligibility_status",
    "journey_status",
    "current_ad",
    "days_in_ad",
    "ad_click_received",
    "journey_start_date",
    "journey_completion_date",
    "cooling_period_end",
    "channel",
    "vendor",
)


# ---------------------------------------------------------------------------
# JourneyEngine
# ---------------------------------------------------------------------------

class JourneyEngine:
    """Manages journey progression through the configured ad sequence.

    Stage 5 in the 11-stage pipeline (ARCH-003).

    Each call to advance() processes one simulation day for all users:
    - NEW / RE_ENTRY users start (or restart) at Ad1.
    - Already-ACTIVE users are checked for click-advance or duration-advance.
    - Users on the last ad complete their journey and enter the cooling period.

    All operations are vectorized; no row-by-row iteration is used (ARCH-011).

    Args:
        config: ConfigRegistry containing the ad sequence, cooling period, and
                default vendor. Config is read-only after construction.

    Raises:
        InputValidationError: If config.ads is empty (no journey to run).
    """

    def __init__(self, config: ConfigRegistry) -> None:
        """Initialize JourneyEngine.

        Builds the ad-order lookup tables from config.ads so that vectorized
        map operations in advance() run in O(1) per ad rather than O(ads) per
        user.

        Args:
            config: Campaign ConfigRegistry. Must have at least one ad defined.

        Raises:
            InputValidationError: If config.ads is empty.
        """
        # config.ads is guaranteed non-empty by ConfigRegistry.__post_init__
        # (which raises ConfigError before JourneyEngine is ever constructed).
        # The guard below is retained as defense-in-depth for test injection paths.
        if not config.ads:
            raise InputValidationError(
                "config.ads",
                "JourneyEngine requires at least one ad; received empty tuple.",
            )

        self._config = config
        self._logger = get_logger(__name__)

        # Sorted ad list (ascending by ad_order)
        self._ads_sorted: list[AdConfig] = sorted(
            config.ads, key=lambda a: a.ad_order
        )

        # Fast lookup maps derived from config (built once at construction)
        self._ad_by_name: dict[str, AdConfig] = {
            a.ad_name: a for a in config.ads
        }

        # Map: ad_name -> next ad_name; None for the last ad
        self._next_ad: dict[str, str | None] = {}
        for i, ad in enumerate(self._ads_sorted):
            if i + 1 < len(self._ads_sorted):
                self._next_ad[ad.ad_name] = self._ads_sorted[i + 1].ad_name
            else:
                self._next_ad[ad.ad_name] = None  # terminal ad

        # First ad in the journey (entry point for new / re-entry users)
        self._first_ad: AdConfig = self._ads_sorted[0]

        # Derived attribute maps for vectorized operations
        self._duration_map: dict[str, int] = {
            a.ad_name: a.duration_days for a in config.ads
        }
        self._move_on_click_map: dict[str, bool] = {
            a.ad_name: a.move_on_click for a in config.ads
        }
        self._channel_map: dict[str, str] = {
            a.ad_name: a.channel for a in config.ads
        }
        self._vendor_map: dict[str, str] = {
            a.ad_name: (a.vendor if a.vendor is not None else config.default_vendor)
            for a in config.ads
        }

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def advance(
        self,
        state_df: pd.DataFrame,
        simulation_date: date,
    ) -> pd.DataFrame:
        """Advance all eligible user journeys by one simulation day.

        Processing order for each simulation day:
        1. Validate required columns are present in state_df.
        2. Start journeys for NEW and RE_ENTRY users (C-004).
        3. Increment days_in_ad for all currently-Active users.
        4. Apply click-based advance (BIZ-018/C-001) -- exclusive with duration.
        5. Apply duration-based advance where days_in_ad >= duration_days.
        6. Complete journeys for users finishing the last ad; set cooling period.
        7. Reset ad_click_received to False for all users.

        BIZ-018/C-001: When move_on_click=True and ad_click_received=True,
        the user advances immediately. The duration check is NOT evaluated for
        the same day a click-advance fires.

        C-004: Re-entry users restart at Ad1. Their prior journey_completion_date
        is preserved (not cleared) to support TER/TCC historical calculations.

        Args:
            state_df: Current user state DataFrame from Stage 4 output.
                      Not mutated -- a copy is made at the start.
            simulation_date: The simulation date being processed.

        Returns:
            New pd.DataFrame with journey fields updated for all eligible users.
            All non-journey fields are unchanged.

        Raises:
            InputValidationError: If required columns are absent from state_df.
        """
        self._validate_columns(state_df)

        if state_df.empty:
            return state_df.copy()

        df = state_df.copy()

        # Step 1: Start journeys for NEW and RE_ENTRY users
        df = self._start_journeys(df, simulation_date)

        # Steps 2-6: Increment, check advance, complete
        df = self._advance_active(df, simulation_date)

        # Step 7: Reset click flag for this day
        df["ad_click_received"] = False

        return df

    # -----------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------

    def _validate_columns(self, state_df: pd.DataFrame) -> None:
        """Assert that state_df contains all columns required by JourneyEngine.

        Args:
            state_df: DataFrame to validate.

        Raises:
            InputValidationError: If any required column is missing.
        """
        missing = [c for c in _STATE_REQUIRED_COLS if c not in state_df.columns]
        if missing:
            raise InputValidationError(
                "state_df",
                f"JourneyEngine.advance(): missing required column(s): {missing}",
            )

    def _start_journeys(
        self,
        df: pd.DataFrame,
        simulation_date: date,
    ) -> pd.DataFrame:
        """Start journeys for NEW and RE_ENTRY eligible users.

        NEW users (eligibility_status=New, journey_status=Not_Started):
            - Enter Ad1 with days_in_ad=0 (will be incremented to 1 in
              _advance_active on the same day).
            - journey_start_date is set to simulation_date.

        RE_ENTRY users (eligibility_status=Re_Entry, journey_status=Completed):
            - Restart at Ad1, resetting journey fields.
            - journey_start_date is reset to simulation_date (new journey leg).
            - journey_completion_date is NOT cleared per C-004; it is preserved
              so TER/TCC historical calculations remain accurate.
            - cooling_period_end is NOT explicitly cleared here; AudienceManager
              owns that field and will set a fresh value on the next completion.

        C-004: Re-entry begins from Ad1 after cooling period expires.

        Args:
            df: Working state DataFrame copy.
            simulation_date: Current simulation date.

        Returns:
            Updated DataFrame with journeys started for eligible users.
        """
        mask_new = (
            (df["eligibility_status"] == EligibilityStatus.NEW.value)
            & (df["journey_status"] == JourneyStatus.NOT_STARTED.value)
        )
        mask_reentry = (
            (df["eligibility_status"] == EligibilityStatus.RE_ENTRY.value)
            & (df["journey_status"] == JourneyStatus.COMPLETED.value)
        )
        mask_start = mask_new | mask_reentry
        if not mask_start.any():
            return df

        first_ad = self._first_ad
        effective_vendor = self._vendor_map[first_ad.ad_name]

        df.loc[mask_start, "current_ad"] = first_ad.ad_name
        # days_in_ad = 0: entry value before _advance_active increments it to 1
        df.loc[mask_start, "days_in_ad"] = 0
        df.loc[mask_start, "journey_status"] = JourneyStatus.ACTIVE.value
        df.loc[mask_start, "channel"] = first_ad.channel
        df.loc[mask_start, "vendor"] = effective_vendor
        df.loc[mask_start, "journey_start_date"] = simulation_date
        # ad_click_received must be False on entry (no prior click for new users)
        df.loc[mask_start, "ad_click_received"] = False

        start_count = int(mask_start.sum())
        new_count = int(
            (mask_start & (df["eligibility_status"] == EligibilityStatus.NEW.value)).sum()
        )
        reentry_count = start_count - new_count

        self._logger.debug(
            "JourneyEngine._start_journeys [%s]: %d new, %d re-entry",
            simulation_date, new_count, reentry_count,
        )
        return df

    def _advance_active(
        self,
        df: pd.DataFrame,
        simulation_date: date,
    ) -> pd.DataFrame:
        """Increment days_in_ad and check/apply advance conditions.

        Processes ALL users whose journey_status is Active and current_ad is set
        (includes users just started in _start_journeys this same day).

        Step 1 -- Increment:
            days_in_ad += 1 for every active user (vectorized).
            After increment, days_in_ad represents how many times advance()
            has been called while on the current ad (1 = first day, 2 = second, etc.).

        Step 2 -- Click advance (BIZ-018/C-001 -- exclusive):
            Fires when ad.move_on_click=True AND ad_click_received=True.
            When click-advance fires, the duration check is SKIPPED for that user
            on that day (exclusive rule).

        Step 3 -- Duration advance:
            Fires when days_in_ad >= ad.duration_days AND no click-advance.

        Step 4 -- Apply advances:
            Users advancing to a non-terminal ad: current_ad set to next ad,
            days_in_ad reset to 0, channel/vendor updated.
            Users completing the journey (terminal ad): _complete_journeys().

        Args:
            df: Working state DataFrame copy.
            simulation_date: Current simulation date.

        Returns:
            Updated DataFrame.
        """
        mask_in_journey = (
            (df["journey_status"] == JourneyStatus.ACTIVE.value)
            & df["current_ad"].notna()
        )
        if not mask_in_journey.any():
            return df

        # ── Step 1: Increment days_in_ad for all active users ────────────
        # fillna(0) handles the initial 0 set by _start_journeys and any
        # unexpected NaN values defensively.
        df.loc[mask_in_journey, "days_in_ad"] = (
            df.loc[mask_in_journey, "days_in_ad"].fillna(0).astype(int) + 1
        )

        # ── Build per-user ad attribute columns (temp, dropped before return) ──
        df["_dur"] = df["current_ad"].map(self._duration_map)
        df["_moc"] = df["current_ad"].map(self._move_on_click_map).fillna(False)
        df["_nxt"] = df["current_ad"].map(self._next_ad)
        # Note: self._next_ad maps the last ad to None, so _nxt is None/NaN for
        # terminal-ad users, making mask_complete correct.

        # ── Step 2: Click advance (BIZ-018/C-001) ────────────────────────
        mask_click_advance = (
            mask_in_journey
            & df["_moc"].astype(bool)
            & df["ad_click_received"].fillna(False).astype(bool)
        )

        # ── Step 3: Duration advance (exclusive -- skip if click fired) ──
        days_series = df["days_in_ad"].fillna(0).astype(float)
        dur_series = df["_dur"].fillna(float("inf"))
        mask_duration_advance = (
            mask_in_journey
            & ~mask_click_advance
            & (days_series >= dur_series)
        )

        mask_advance = mask_click_advance | mask_duration_advance

        if not mask_advance.any():
            df.drop(columns=["_dur", "_moc", "_nxt"], inplace=True)
            return df

        # ── Step 4a: Advance to next ad (non-terminal) ───────────────────
        mask_to_next = mask_advance & df["_nxt"].notna()
        if mask_to_next.any():
            next_names = df.loc[mask_to_next, "_nxt"]
            df.loc[mask_to_next, "current_ad"] = next_names.values
            # days_in_ad = 0: set to 0 on ad entry; _advance_active on the NEXT
            # advance() call increments it to 1, consistent with _start_journeys.
            df.loc[mask_to_next, "days_in_ad"] = 0
            df.loc[mask_to_next, "channel"] = next_names.map(self._channel_map).values
            df.loc[mask_to_next, "vendor"] = next_names.map(self._vendor_map).values

            advance_type = "click" if mask_click_advance.any() else "duration"
            self._logger.debug(
                "JourneyEngine._advance_active [%s]: %d user(s) advanced "
                "to next ad (%s-advance)",
                simulation_date, int(mask_to_next.sum()), advance_type,
            )

        # ── Step 4b: Complete journeys (terminal ad) ─────────────────────
        mask_complete = mask_advance & df["_nxt"].isna()
        if mask_complete.any():
            df = self._complete_journeys(df, mask_complete, simulation_date)

        df.drop(columns=["_dur", "_moc", "_nxt"], inplace=True)
        return df

    def _complete_journeys(
        self,
        df: pd.DataFrame,
        mask: pd.Series,
        simulation_date: date,
    ) -> pd.DataFrame:
        """Apply journey completion for users who finished the last ad.

        Sets the following fields for all users in mask:
            journey_status         = Completed
            journey_completion_date = simulation_date
            cooling_period_end     = simulation_date + timedelta(cooling_period_days)
            current_ad             = None  (no longer on any ad)
            days_in_ad             = None  (not applicable)
            channel                = None
            vendor                 = None

        Cooling formula (PHASE_3_EXECUTION_PLAN.md section 7.2):
            cooling_period_end = journey_completion_date
                                 + timedelta(days=config.cooling_period_days)

        Args:
            df: Working state DataFrame copy.
            mask: Boolean Series identifying users completing their journey.
            simulation_date: Current simulation date (= journey_completion_date).

        Returns:
            Updated DataFrame.
        """
        cooling_end = simulation_date + timedelta(
            days=self._config.cooling_period_days
        )

        df.loc[mask, "journey_status"] = JourneyStatus.COMPLETED.value
        df.loc[mask, "journey_completion_date"] = simulation_date
        df.loc[mask, "cooling_period_end"] = cooling_end
        df.loc[mask, "current_ad"] = None
        df.loc[mask, "days_in_ad"] = None
        df.loc[mask, "channel"] = None
        df.loc[mask, "vendor"] = None

        count = int(mask.sum())
        self._logger.info(
            "JourneyEngine._complete_journeys [%s]: %d user(s) completed "
            "journey; cooling_period_end=%s",
            simulation_date, count, cooling_end,
        )
        return df

    # -----------------------------------------------------------------------
    # Utility / introspection
    # -----------------------------------------------------------------------

    def get_journey_summary(self, state_df: pd.DataFrame) -> dict:
        """Return a summary dict of current journey state counts.

        Useful for logging and diagnostics. Does not mutate state_df.

        Args:
            state_df: Current user state DataFrame.

        Returns:
            Dict with keys: total_users, not_started, active, completed,
            dropped, cooling_users, re_entry_users.
        """
        if state_df.empty:
            return {
                "total_users": 0,
                "not_started": 0,
                "active": 0,
                "completed": 0,
                "dropped": 0,
                "cooling_users": 0,
                "re_entry_users": 0,
            }

        js = state_df["journey_status"]
        es = state_df["eligibility_status"]

        return {
            "total_users": len(state_df),
            "not_started": int((js == JourneyStatus.NOT_STARTED.value).sum()),
            "active": int((js == JourneyStatus.ACTIVE.value).sum()),
            "completed": int((js == JourneyStatus.COMPLETED.value).sum()),
            "dropped": int((js == JourneyStatus.DROPPED.value).sum()),
            "cooling_users": int((es == EligibilityStatus.COOLING.value).sum()),
            "re_entry_users": int((es == EligibilityStatus.RE_ENTRY.value).sum()),
        }

    @property
    def journey_length(self) -> int:
        """Total number of ads in the journey."""
        return len(self._ads_sorted)

    @property
    def total_journey_days(self) -> int:
        """Total simulation days for a user to complwithout any click-based early advances.

        Returns:
            Sum of duration_days across all ads.
        """
        return sum(a.duration_days for a in self._ads_sorted)


__all__ = ["JourneyEngine"]
