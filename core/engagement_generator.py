"""Stage 7 — Campaign-Level Engagement Generation.

EngagementGenerator orchestrates the full simulation loop for a campaign run.
For each simulation day it:
  1. Advances user journeys via JourneyEngine (Stage 5).
  2. Enforces campaign-level TCC capacity constraints per trigger (TCC-001..007).
  3. Generates per-user engagement events via BehaviorEngine (Stage 6).
  4. Accumulates daily metrics and enriches events with trigger/segment context.
  5. Produces three output DataFrames: events, daily metrics, and diagnostics.

Architecture references
-----------------------
* ARCH-003  — Stage 7 in the 11-stage pipeline
* ARCH-011  — No iterrows(); vectorised operations only
* TCC-001..009 — Trigger capacity consumption rules
* FAT-001..007 — Fatigue, weekly cap, and cooldown rules
* ENG-011..015 — Causal chain rules (HR-003..HR-008)
* SIM-019   — Deterministic simulation reproducibility (REQ-026)

TCC enforcement strategy
------------------------
When a trigger's remaining_capacity reaches 0 the generator prevents
qualifying events for those users by setting a far-future
engagement_cooldown_end before calling BehaviorEngine.  BehaviorEngine then
produces only reach events (Impression/Sent) for those users, which is
correct per TCC-007.  The synthetic cooldown is restored to its original
value after BehaviorEngine returns — BehaviorEngine never mutates
engagement_cooldown_end for users it cannot give qualifying events.

No iterrows() — all user-level operations use boolean masks and
vectorised DataFrame operations.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd

from core.behavior_engine import BehaviorEngine
from core.journey_engine import JourneyEngine
from models.config_registry import ConfigRegistry
from models.enums import ActionType, JourneyStatus
from utils.exceptions import InputValidationError
from utils.logger import get_logger

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DISPLAY_CHANNELS: frozenset[str] = frozenset(
    {"Display", "Endemic_Display", "Programmatic_Display", "Banner"}
)
_ACTION_SENT = "Sent"

# Far-future sentinel for TCC cooldown suppression (9999 days ≈ 27 years)
_TCC_BLOCK_DAYS: int = 9999

# Required state_df columns
_STATE_REQUIRED_COLS: tuple[str, ...] = (
    "user_id", "journey_status", "current_ad", "channel", "vendor",
    "behavior_profile", "engagement_score", "trigger_name", "segment",
    "channel_affinity_display", "channel_affinity_email",
    "channel_affinity_whatsapp",
    "weekly_impressions", "weekly_clicks", "weekly_opens", "weekly_engagements",
    "total_lifetime_engagements", "last_reached_date", "last_engagement_date",
    "engagement_cooldown_end", "ad_click_received", "historical_engaged",
)

# Output DataFrame column orders
_EVENT_OUT_COLS: tuple[str, ...] = (
    "campaign_id", "user_id", "simulation_date", "channel",
    "action_type", "current_ad", "vendor", "trigger_name", "segment",
)
_METRICS_COLS: tuple[str, ...] = (
    "simulation_date", "n_users_active", "n_reached",
    "n_impressions", "n_sends", "n_opens", "n_clicks", "n_qualifying",
    "actual_ctr_display", "actual_open_rate_email", "actual_open_rate_wa",
    "n_tcc_blocked_users", "weekly_reset",
)
_DIAG_COLS: tuple[str, ...] = (
    "metric", "entity", "requested", "actual", "variance", "variance_pct",
)


class EngagementGenerator:
    """Stage 7 — Campaign-Level Engagement Generation.

    Orchestrates the full simulation loop.  For each day: advances journeys,
    enforces TCC capacity, runs BehaviorEngine, accumulates metrics.

    Args:
        config: Campaign ConfigRegistry.
        journey_engine: JourneyEngine instance.  Created from config if None.
        behavior_engine: BehaviorEngine instance.  Created from config if None.
    """

    def __init__(
        self,
        config: ConfigRegistry,
        journey_engine: JourneyEngine | None = None,
        behavior_engine: BehaviorEngine | None = None,
    ) -> None:
        self._config = config
        self._je = journey_engine or JourneyEngine(config)
        self._be = behavior_engine or BehaviorEngine(config)
        self._campaign_id = config.campaign_id

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def generate(
        self,
        state_df: pd.DataFrame,
        simulation_start: date | None = None,
        simulation_end: date | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Run the full simulation loop.

        For each day from simulation_start to simulation_end (inclusive):
        advances journeys (JourneyEngine), enforces TCC capacity, generates
        events (BehaviorEngine), and accumulates metrics.

        Args:
            state_df: Initial user state DataFrame.  NOT mutated.
            simulation_start: Override start date.  Defaults to
                config.simulation_start_date.
            simulation_end: Override end date.  Defaults to
                config.simulation_end_date.

        Returns:
            Tuple of (events_df, metrics_df, diagnostics_df, final_state_df).
            final_state_df is the post-simulation state DataFrame reflecting all
            journey progressions, cooling periods, and engagement counter updates
            accumulated across all simulation days.  Pass this as
            ``previous_state_df`` to the next run to achieve correct multi-run
            persistence (ARCH-RISK-005 fix).

        Raises:
            InputValidationError: If required columns are missing.
        """
        self._validate_columns(state_df)
        start  = simulation_start or self._config.simulation_start_date
        end    = simulation_end   or self._config.simulation_end_date
        n_days = (end - start).days + 1

        df             = state_df.copy()
        capacity       = self._init_capacity_tracker(df)
        all_events:    list[pd.DataFrame] = []
        daily_metrics: list[dict]         = []

        _logger.info(
            "EngagementGenerator: run campaign=%s days=%d start=%s end=%s",
            self._campaign_id, n_days, start, end,
        )

        for i in range(n_days):
            sim_date = start + timedelta(days=i)

            # Stage 5: advance journeys
            df = self._je.advance(df, sim_date)

            # Stage 6: generate events (with TCC enforcement)
            df, day_events, day_metrics = self._process_day(
                df, sim_date, capacity
            )

            if not day_events.empty:
                day_events = self._enrich_events(day_events, df)
                all_events.append(day_events)

            daily_metrics.append(day_metrics)
            capacity = self._update_capacity_tracker(capacity, day_events, df)

            _logger.debug(
                "EngagementGenerator: date=%s events=%d active=%d blocked=%d",
                sim_date, len(day_events),
                day_metrics.get("n_users_active", 0),
                day_metrics.get("n_tcc_blocked_users", 0),
            )

        events_df  = (
            pd.concat(all_events, ignore_index=True)
            if all_events else _empty_events_df()
        )
        metrics_df = (
            pd.DataFrame(daily_metrics)
            if daily_metrics else _empty_metrics_df()
        )
        diag_df    = self.build_diagnostics(events_df, df, metrics_df)

        _logger.info(
            "EngagementGenerator: complete total_events=%d total_days=%d",
            len(events_df), n_days,
        )
        # ARCH-RISK-005 fix: return final simulation state so callers can
        # persist journey completions, cooling periods, and engagement counters
        # across multi-run chains.  df is the post-simulation state after all
        # JourneyEngine.advance() and BehaviorEngine.process() calls.
        return events_df, metrics_df, diag_df, df

    def generate_day(
        self,
        state_df: pd.DataFrame,
        simulation_date: date,
        capacity_tracker: dict[str, int] | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
        """Process a single simulation day without advancing journeys.

        Public entry point for testing and incremental processing.
        Assumes journey state is already up-to-date (caller manages
        JourneyEngine if needed).

        Args:
            state_df: Current user state DataFrame.  NOT mutated.
            simulation_date: Simulation date.
            capacity_tracker: TCC remaining capacity per trigger_name.
                Initialised from state_df if None.

        Returns:
            Tuple of (updated_state_df, events_df, day_metrics_dict).
        """
        self._validate_columns(state_df)
        df  = state_df.copy()
        cap = (
            capacity_tracker
            if capacity_tracker is not None
            else self._init_capacity_tracker(df)
        )
        df, events, metrics = self._process_day(df, simulation_date, cap)
        if not events.empty:
            events = self._enrich_events(events, df)
        return df, events, metrics

    def build_diagnostics(
        self,
        events_df: pd.DataFrame,
        state_df: pd.DataFrame,
        metrics_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Compute allocation diagnostics: requested vs actual rates.

        Produces one row per (metric, entity) combination covering:
        CTR per Display ad, open rate per Email/WA ad, trigger engagement
        rate per trigger, segment engagement distribution per segment.

        Args:
            events_df: All engagement events from generate().
            state_df: Initial user state (for trigger/segment lookups).
            metrics_df: Daily metrics DataFrame (currently informational).

        Returns:
            diagnostics_df with columns:
            metric, entity, requested, actual, variance, variance_pct.
        """
        if events_df.empty:
            return _empty_diagnostics_df()

        rows: list[dict] = []
        qual_events = events_df[_qualifying_mask(events_df)]

        # ── CTR per Display ad ────────────────────────────────────────────
        for ad in self._config.ads:
            if not ad.is_display_channel():
                continue
            req_ctr  = ad.target_ctr if ad.target_ctr is not None else 0.05
            ad_evs   = events_df[events_df["current_ad"] == ad.ad_name]
            n_imp    = (ad_evs["action_type"] == ActionType.IMPRESSION.value).sum()
            n_clk    = (ad_evs["action_type"] == ActionType.CLICK.value).sum()
            actual   = n_clk / n_imp if n_imp > 0 else 0.0
            rows.append(_diag_row("ctr", ad.ad_name, req_ctr, actual))

        # ── Open rate per Email / WhatsApp ad ─────────────────────────────
        for ad in self._config.ads:
            if not (ad.is_email_channel() or ad.is_whatsapp_channel()):
                continue
            ch_cfg   = self._config.get_channel_config(ad.channel)
            req_or   = (
                ch_cfg.target_open_rate
                if ch_cfg and ch_cfg.target_open_rate is not None
                else 0.25
            )
            ad_evs   = events_df[events_df["current_ad"] == ad.ad_name]
            n_sent   = (ad_evs["action_type"] == _ACTION_SENT).sum()
            n_open   = (ad_evs["action_type"] == ActionType.OPEN.value).sum()
            actual   = n_open / n_sent if n_sent > 0 else 0.0
            rows.append(_diag_row("open_rate", ad.ad_name, req_or, actual))

        # ── Trigger engagement rate ───────────────────────────────────────
        for trig in self._config.triggers:
            trig_uids  = set(
                state_df.loc[
                    state_df["trigger_name"].astype(str) == trig.trigger_name,
                    "user_id",
                ]
            )
            n_trig = len(trig_uids)
            if n_trig == 0:
                continue
            engaged  = qual_events[
                qual_events["user_id"].isin(trig_uids)
            ]["user_id"].nunique()
            actual   = engaged / n_trig
            rows.append(
                _diag_row("trigger_engagement", trig.trigger_name,
                          trig.engagement_rate_target, actual)
            )

        # ── Segment engagement distribution ───────────────────────────────
        total_engaged = qual_events["user_id"].nunique() or 1
        for seg in self._config.segments:
            req_pct  = seg.distribution_pct / 100.0
            seg_uids = set(
                state_df.loc[
                    state_df["segment"].astype(str) == seg.segment_name,
                    "user_id",
                ]
            )
            n_seg = len(seg_uids)
            if n_seg == 0:
                continue
            engaged  = qual_events[
                qual_events["user_id"].isin(seg_uids)
            ]["user_id"].nunique()
            actual   = engaged / total_engaged
            rows.append(
                _diag_row("segment_engagement_pct", seg.segment_name,
                          req_pct, actual)
            )

        return (
            pd.DataFrame(rows, columns=list(_DIAG_COLS))
            if rows else _empty_diagnostics_df()
        )

    # -----------------------------------------------------------------------
    # Private: day processing
    # -----------------------------------------------------------------------

    def _process_day(
        self,
        df: pd.DataFrame,
        sim_date: date,
        capacity: dict[str, int],
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
        """TCC block → BehaviorEngine → restore → metrics."""
        weekly_reset = sim_date.weekday() == 0
        n_active = int(
            (df["journey_status"] == JourneyStatus.ACTIVE.value).sum()
        )

        df_in, blocked_mask, orig_cooldown = self._apply_tcc_block(
            df, capacity, sim_date
        )
        n_tcc_blocked = int(blocked_mask.sum())

        df_out, events = self._be.process(df_in, sim_date)
        df_out = self._restore_tcc_state(df_out, blocked_mask, orig_cooldown)

        metrics = self._compute_day_metrics(
            events, sim_date, n_active, n_tcc_blocked, weekly_reset
        )
        return df_out, events, metrics

    # -----------------------------------------------------------------------
    # Private: TCC capacity enforcement
    # -----------------------------------------------------------------------

    def _init_capacity_tracker(
        self, state_df: pd.DataFrame
    ) -> dict[str, int]:
        """Compute initial TCC remaining capacity per trigger (TCC-001..006).

        TCC = max(0, ceil(n_trigger_users × target_rate) − historical_engaged)
        """
        tracker: dict[str, int] = {}
        for trig in self._config.triggers:
            mask = state_df["trigger_name"].astype(str) == trig.trigger_name
            n_users   = int(mask.sum())
            target    = math.ceil(n_users * trig.engagement_rate_target)
            hist_col  = "historical_engaged"
            hist_eng  = int(
                state_df.loc[mask, hist_col].sum()
            ) if hist_col in state_df.columns else 0
            remaining = max(0, target - hist_eng)
            tracker[trig.trigger_name] = remaining
            _logger.debug(
                "TCC init trigger=%s n=%d target=%d hist=%d remaining=%d",
                trig.trigger_name, n_users, target, hist_eng, remaining,
            )
        return tracker

    def _apply_tcc_block(
        self,
        df: pd.DataFrame,
        capacity: dict[str, int],
        sim_date: date,
    ) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
        """Block qualifying events for exhausted triggers via synthetic cooldown.

        Returns:
            (modified_df, blocked_mask, original_cooldown_series)
        """
        blocked = {t for t, cap in capacity.items() if cap <= 0}
        empty_cooldown = df.get(
            "engagement_cooldown_end",
            pd.Series([None] * len(df), index=df.index),
        )

        if not blocked or "trigger_name" not in df.columns:
            return df, pd.Series(False, index=df.index), empty_cooldown.copy()

        mask = df["trigger_name"].astype(str).isin(blocked)
        orig = df["engagement_cooldown_end"].copy()

        if mask.any():
            df_mod = df.copy()
            far = str(sim_date + timedelta(days=_TCC_BLOCK_DAYS))
            df_mod.loc[mask, "engagement_cooldown_end"] = far
            return df_mod, mask, orig

        return df, mask, orig

    def _restore_tcc_state(
        self,
        df: pd.DataFrame,
        blocked_mask: pd.Series,
        original_cooldown: pd.Series,
    ) -> pd.DataFrame:
        """Restore engagement_cooldown_end for TCC-blocked users."""
        if not blocked_mask.any():
            return df
        df = df.copy()
        df.loc[blocked_mask, "engagement_cooldown_end"] = (
            original_cooldown.loc[blocked_mask]
        )
        return df

    def _update_capacity_tracker(
        self,
        tracker: dict[str, int],
        events_df: pd.DataFrame,
        state_df: pd.DataFrame,
    ) -> dict[str, int]:
        """Decrement remaining capacity per trigger for each newly engaged user."""
        if events_df.empty or "trigger_name" not in state_df.columns:
            return tracker

        qual_mask = _qualifying_mask(events_df)
        if not qual_mask.any():
            return tracker

        qual_users = set(events_df.loc[qual_mask, "user_id"])
        uid_trigger = dict(
            zip(state_df["user_id"], state_df["trigger_name"].astype(str))
        )

        engaged_per_trigger: dict[str, set[str]] = {}
        for uid in qual_users:
            trig = uid_trigger.get(uid, "")
            if trig and trig in tracker:
                engaged_per_trigger.setdefault(trig, set()).add(uid)

        new_tracker = dict(tracker)
        for trig, users in engaged_per_trigger.items():
            new_tracker[trig] = max(0, new_tracker[trig] - len(users))

        return new_tracker

    # -----------------------------------------------------------------------
    # Private: metrics
    # -----------------------------------------------------------------------

    def _compute_day_metrics(
        self,
        events: pd.DataFrame,
        sim_date: date,
        n_active: int,
        n_tcc_blocked: int,
        weekly_reset: bool,
    ) -> dict:
        """Compute per-day campaign metrics from events DataFrame."""
        base: dict = {
            "simulation_date": sim_date,
            "n_users_active": n_active,
            "n_reached": 0,
            "n_impressions": 0,
            "n_sends": 0,
            "n_opens": 0,
            "n_clicks": 0,
            "n_qualifying": 0,
            "actual_ctr_display": 0.0,
            "actual_open_rate_email": 0.0,
            "actual_open_rate_wa": 0.0,
            "n_tcc_blocked_users": n_tcc_blocked,
            "weekly_reset": weekly_reset,
        }
        if events.empty:
            return base

        n_imp  = int((events["action_type"] == ActionType.IMPRESSION.value).sum())
        n_sent = int((events["action_type"] == _ACTION_SENT).sum())
        n_open = int((events["action_type"] == ActionType.OPEN.value).sum())
        n_clk  = int((events["action_type"] == ActionType.CLICK.value).sum())
        n_qual = int(_qualifying_mask(events).sum())

        reached = events[events["action_type"].isin(
            {ActionType.IMPRESSION.value, _ACTION_SENT}
        )]["user_id"].nunique()

        # Display CTR
        disp    = events["channel"].isin(_DISPLAY_CHANNELS)
        d_imp   = int((disp & (events["action_type"] == ActionType.IMPRESSION.value)).sum())
        d_clk   = int((disp & (events["action_type"] == ActionType.CLICK.value)).sum())
        ctr_d   = d_clk / d_imp if d_imp > 0 else 0.0

        # Email open rate
        em      = events["channel"] == "Email"
        em_sent = int((em & (events["action_type"] == _ACTION_SENT)).sum())
        em_open = int((em & (events["action_type"] == ActionType.OPEN.value)).sum())
        or_em   = em_open / em_sent if em_sent > 0 else 0.0

        # WhatsApp open rate
        wa      = events["channel"] == "WhatsApp"
        wa_sent = int((wa & (events["action_type"] == _ACTION_SENT)).sum())
        wa_open = int((wa & (events["action_type"] == ActionType.OPEN.value)).sum())
        or_wa   = wa_open / wa_sent if wa_sent > 0 else 0.0

        return {
            **base,
            "n_reached": int(reached),
            "n_impressions": n_imp,
            "n_sends": n_sent,
            "n_opens": n_open,
            "n_clicks": n_clk,
            "n_qualifying": n_qual,
            "actual_ctr_display": float(ctr_d),
            "actual_open_rate_email": float(or_em),
            "actual_open_rate_wa": float(or_wa),
        }

    # -----------------------------------------------------------------------
    # Private: event enrichment
    # -----------------------------------------------------------------------

    def _enrich_events(
        self, events_df: pd.DataFrame, state_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Add campaign_id, trigger_name, segment to events_df."""
        lookup = (
            state_df[["user_id", "trigger_name", "segment"]]
            .drop_duplicates("user_id")
            .copy()
        )
        lookup["trigger_name"] = lookup["trigger_name"].astype(str)
        lookup["segment"]      = lookup["segment"].astype(str)

        enriched = events_df.merge(lookup, on="user_id", how="left")
        enriched["campaign_id"] = self._campaign_id
        cols = [c for c in _EVENT_OUT_COLS if c in enriched.columns]
        return enriched[cols].reset_index(drop=True)

    # -----------------------------------------------------------------------
    # Private: validation
    # -----------------------------------------------------------------------

    def _validate_columns(self, state_df: pd.DataFrame) -> None:
        missing = [c for c in _STATE_REQUIRED_COLS if c not in state_df.columns]
        if missing:
            raise InputValidationError(
                "state_df",
                f"EngagementGenerator: missing required column(s): {missing}",
            )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _qualifying_mask(events_df: pd.DataFrame) -> pd.Series:
    """Boolean mask for qualifying events (BIZ-011 / ENG-014)."""
    if events_df.empty:
        return pd.Series(dtype=bool)
    disp  = events_df["channel"].isin(_DISPLAY_CHANNELS) & (
        events_df["action_type"] == ActionType.CLICK.value
    )
    email = (events_df["channel"] == "Email") & events_df["action_type"].isin(
        {ActionType.OPEN.value, ActionType.CLICK.value}
    )
    wa    = (events_df["channel"] == "WhatsApp") & events_df["action_type"].isin(
        {ActionType.OPEN.value, ActionType.CLICK.value}
    )
    return disp | email | wa


def _diag_row(
    metric: str, entity: str, requested: float, actual: float
) -> dict:
    """Build a single diagnostics row with variance."""
    var     = actual - requested
    var_pct = (var / abs(requested)) * 100.0 if abs(requested) > 1e-10 else 0.0
    return {
        "metric":       metric,
        "entity":       entity,
        "requested":    requested,
        "actual":       actual,
        "variance":     var,
        "variance_pct": var_pct,
    }


def _empty_events_df() -> pd.DataFrame:
    return pd.DataFrame(columns=list(_EVENT_OUT_COLS))


def _empty_metrics_df() -> pd.DataFrame:
    return pd.DataFrame(columns=list(_METRICS_COLS))


def _empty_diagnostics_df() -> pd.DataFrame:
    return pd.DataFrame(columns=list(_DIAG_COLS))


__all__ = ["EngagementGenerator"]
