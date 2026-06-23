"""Stage 8 — Simulation Output Validation Engine.

ValidationEngine verifies that generated simulation outputs satisfy
business requirements, producing three output DataFrames:

  1. Validation Results  — per-rule status with expected vs actual values.
  2. Validation Summary  — per-category aggregated counts and scores (0–100).
  3. Realism Report      — requested vs actual rate comparison.

Architecture references
-----------------------
* ARCH-003  — Stage 8 in the 11-stage pipeline
* ARCH-011  — No iterrows(); all processing vectorised
* HR-003..008 — Channel causal chain rules (channel dependency validation)
* TCC-001..007 — Trigger capacity consumption rules
* FAT-001..007 — Fatigue and weekly cap rules
* BIZ-011  — Qualifying action definitions
* SIM-019  — Deterministic simulation
* VAL-001..017 — Validation rule catalogue

Tolerance defaults
------------------
Pass/warn/fail thresholds are absolute percentage-point differences unless
otherwise noted.  All thresholds have named constants at module level so
they can be read and overridden easily.

Quality score
-------------
Weighted average of per-rule outcomes where Hard=3 pts, Soft=2 pts,
Advisory=1 pt.  Pass=1.0, Warning=0.5, Fail=0.0, Skip=1.0 (neutral).
Result is clamped 0–100.

Realism score
-------------
Per-metric realism = max(0, 1 − |variance| / max(requested, ε)) × 100.
Overall realism is the unweighted mean across all rate metrics.
"""
from __future__ import annotations

import math
from datetime import date
from typing import NamedTuple

import numpy as np
import pandas as pd

from models.config_registry import ConfigRegistry
from models.enums import ActionType, JourneyStatus, RuleSeverity, RuleStatus
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

# Default pass/warn absolute tolerances (percentage-point differences)
_TOL_CTR_PASS: float    = 0.05   # ±5 pp
_TOL_CTR_WARN: float    = 0.10   # ±10 pp
_TOL_OPEN_PASS: float   = 0.10   # ±10 pp
_TOL_OPEN_WARN: float   = 0.20   # ±20 pp
_TOL_TER_PASS: float    = 0.05   # ±5 pp
_TOL_TER_WARN: float    = 0.10   # ±10 pp
_TOL_SEG_PASS: float    = 0.10   # ±10 pp
_TOL_SEG_WARN: float    = 0.20   # ±20 pp

# Score constants
_SEV_WEIGHT: dict[str, float] = {
    RuleSeverity.HARD.value:     3.0,
    RuleSeverity.SOFT.value:     2.0,
    RuleSeverity.ADVISORY.value: 1.0,
}
_OUTCOME_SCORE: dict[str, float] = {
    RuleStatus.PASS.value:    1.0,
    "Warning":                0.5,
    RuleStatus.FAIL.value:    0.0,
    RuleStatus.SKIP.value:    1.0,
}

# Realism status thresholds
_REALISM_GOOD: float       = 90.0
_REALISM_ACCEPTABLE: float = 70.0

# Validation categories
_CAT_RATE      = "Rate Achievement"
_CAT_CAPACITY  = "Capacity & Frequency"
_CAT_JOURNEY   = "Journey Validation"
_CAT_TRIGGER   = "Trigger Rules"
_CAT_SEGMENT   = "Segment Rules"
_CAT_CHANNEL   = "Channel Rules"
_CAT_TCC       = "TCC Validation"
_CAT_HISTORICAL = "Historical Engagement"

# Required events_df columns
_EVENTS_REQUIRED: tuple[str, ...] = (
    "user_id", "simulation_date", "channel", "action_type",
    "current_ad",
)

# ---------------------------------------------------------------------------
# Output column tuples
# ---------------------------------------------------------------------------

_RESULTS_COLS: tuple[str, ...] = (
    "rule_id", "rule_name", "status",
    "expected_value", "actual_value", "variance",
    "severity", "message",
)
_SUMMARY_COLS: tuple[str, ...] = (
    "validation_category", "passed", "failed", "warning", "score",
)
_REALISM_COLS: tuple[str, ...] = (
    "metric", "target", "actual", "variance", "variance_pct", "status",
)


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class ValidationEngine:
    """Stage 8 — Simulation Output Validation Engine.

    Validates simulation outputs against configured business rules, producing
    three output DataFrames: results, summary, and realism report.

    Args:
        config: Campaign ConfigRegistry.
    """

    def __init__(self, config: ConfigRegistry) -> None:
        self._config = config
        _logger.info(
            "ValidationEngine: initialised campaign=%s", config.campaign_id
        )

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def validate(
        self,
        events_df: pd.DataFrame,
        state_df: pd.DataFrame,
        metrics_df: pd.DataFrame | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Run all validation rules against simulation outputs.

        Args:
            events_df: Events from EngagementGenerator with columns
                user_id, simulation_date, channel, action_type, current_ad,
                and optionally trigger_name, segment, vendor, campaign_id.
            state_df: Final user state DataFrame from simulation.
            metrics_df: Optional daily metrics DataFrame (informational).

        Returns:
            Tuple of (results_df, summary_df, realism_df).
            results_df  — one row per rule evaluation.
            summary_df  — one row per validation category.
            realism_df  — one row per rate metric.

        Raises:
            InputValidationError: If events_df is missing required columns.
        """
        _validate_events_columns(events_df)
        events_df = _normalise_events(events_df)

        _logger.info(
            "ValidationEngine.validate: events=%d state_rows=%d",
            len(events_df), len(state_df),
        )

        rows: list[dict] = []

        # ── Category 1: Rate Achievement ───────────────────────────────────
        rows.extend(self._validate_ctr(events_df))
        rows.extend(self._validate_open_rate(events_df))
        rows.extend(self._validate_trigger_engagement(events_df, state_df))
        rows.extend(self._validate_segment_engagement(events_df, state_df))

        # ── Category 2: Capacity & Frequency ──────────────────────────────
        rows.extend(self._validate_user_frequency(events_df))
        rows.extend(self._validate_weekly_engagement_caps(events_df))
        rows.extend(self._validate_weekly_impression_caps(events_df))

        # ── Category 3: Journey Validation ────────────────────────────────
        rows.extend(self._validate_journey_progression(events_df, state_df))

        # ── Category 4: Trigger Rules ─────────────────────────────────────
        rows.extend(self._validate_trigger_priority(events_df, state_df))
        rows.extend(self._validate_multi_trigger(events_df))

        # ── Category 5: Segment Rules ─────────────────────────────────────
        rows.extend(self._validate_segment_distribution(events_df, state_df))

        # ── Category 6: Channel Rules ─────────────────────────────────────
        rows.extend(self._validate_channel_dependencies(events_df))

        # ── Category 7: TCC Validation ────────────────────────────────────
        rows.extend(self._validate_tcc_calculations(events_df, state_df))

        # ── Category 8: Historical Engagement ─────────────────────────────
        rows.extend(self._validate_historical_engagement(events_df, state_df))

        # Build internal results (includes _category for summary routing)
        _internal_cols = list(_RESULTS_COLS) + ["_category"]
        results_internal = (
            pd.DataFrame(rows, columns=_internal_cols)
            if rows else _empty_results_df()
        )

        summary_df = self._build_summary(results_internal)
        realism_df = self._build_realism_report(events_df, state_df)

        # Strip _category before returning public results_df
        results_df = results_internal[list(_RESULTS_COLS)].reset_index(drop=True)

        quality  = _compute_quality_score(results_df)
        realism  = _compute_realism_score(realism_df)

        _logger.info(
            "ValidationEngine: quality_score=%.1f realism_score=%.1f "
            "rules=%d passed=%d failed=%d warnings=%d",
            quality, realism,
            len(results_df),
            int((results_df["status"] == RuleStatus.PASS.value).sum()),
            int((results_df["status"] == RuleStatus.FAIL.value).sum()),
            int((results_df["status"] == "Warning").sum()),
        )

        return results_df, summary_df, realism_df

    def generate_quality_score(
        self,
        results_df: pd.DataFrame,
    ) -> float:
        """Compute the simulation quality score (0–100) from results_df.

        Score = weighted average of per-rule outcomes.
        Hard=3, Soft=2, Advisory=1.  Pass=1.0, Warning=0.5, Fail=0.0.

        Args:
            results_df: Output of validate().

        Returns:
            Float in [0, 100].
        """
        return _compute_quality_score(results_df)

    def generate_realism_score(
        self,
        realism_df: pd.DataFrame,
    ) -> float:
        """Compute the realism score (0–100) from realism_df.

        Score = unweighted mean of per-metric realism values.

        Args:
            realism_df: Output of validate().

        Returns:
            Float in [0, 100].
        """
        return _compute_realism_score(realism_df)

    def generate_feasibility_warnings(
        self,
        events_df: pd.DataFrame,
        state_df: pd.DataFrame,
    ) -> list[str]:
        """Generate feasibility warnings for the simulation configuration.

        Checks for conditions that are technically valid but may produce
        unrealistic or unexpected results (e.g., too-low target CTR, too-high
        TCC, 0-user segments).

        Args:
            events_df: Events DataFrame.
            state_df: Final state DataFrame.

        Returns:
            List of warning strings.  Empty list = no warnings.
        """
        warnings: list[str] = []

        # Zero-user triggers
        for trig in self._config.triggers:
            mask = state_df["trigger_name"].astype(str) == trig.trigger_name
            if mask.sum() == 0:
                warnings.append(
                    f"Trigger '{trig.trigger_name}' has 0 users — "
                    "engagement target can never be met."
                )

        # Engagement target > 1.0 (would exceed 100% of users)
        for trig in self._config.triggers:
            if trig.engagement_rate_target > 1.0:
                warnings.append(
                    f"Trigger '{trig.trigger_name}' has engagement_rate_target "
                    f"{trig.engagement_rate_target:.2%} > 100% — infeasible."
                )

        # Very high weekly impression cap relative to simulation days
        sim_days = (
            self._config.simulation_end_date
            - self._config.simulation_start_date
        ).days + 1
        weekly_weeks = sim_days / 7
        if self._config.weekly_impression_cap > sim_days:
            warnings.append(
                f"weekly_impression_cap={self._config.weekly_impression_cap} "
                f"exceeds simulation_days={sim_days} — cap will never bind."
            )

        # Very low CTR targets
        for ad in self._config.ads:
            if ad.target_ctr is not None and ad.target_ctr < 0.001:
                warnings.append(
                    f"Ad '{ad.ad_name}' has target_ctr={ad.target_ctr:.4f} "
                    "which is very low — few or no clicks expected."
                )

        # Empty events
        if events_df.empty:
            warnings.append(
                "events_df is empty — no simulation output to validate. "
                "Check journey activation and user eligibility."
            )

        # No active users
        if "journey_status" in state_df.columns:
            n_active = (state_df["journey_status"] == JourneyStatus.ACTIVE.value).sum()
            if n_active == 0 and not state_df.empty:
                warnings.append(
                    "No users have journey_status=Active in final state_df. "
                    "All users may have completed or dropped journeys."
                )

        return warnings

    # -----------------------------------------------------------------------
    # Category 1: Rate Achievement
    # -----------------------------------------------------------------------

    def _validate_ctr(self, events_df: pd.DataFrame) -> list[dict]:
        """VAL-001: CTR achievement per Display ad."""
        rows: list[dict] = []
        disp_mask = events_df["channel"].isin(_DISPLAY_CHANNELS)
        disp_evs  = events_df[disp_mask]

        for i, ad in enumerate(self._config.ads, start=1):
            if not ad.is_display_channel():
                continue
            ad_mask  = disp_evs["current_ad"] == ad.ad_name
            ad_evs   = disp_evs[ad_mask]
            n_imp    = int((ad_evs["action_type"] == ActionType.IMPRESSION.value).sum())
            n_clk    = int((ad_evs["action_type"] == ActionType.CLICK.value).sum())
            actual   = n_clk / n_imp if n_imp > 0 else 0.0
            expected = ad.target_ctr if ad.target_ctr is not None else 0.05
            variance = actual - expected
            status   = _rate_status(abs(variance), _TOL_CTR_PASS, _TOL_CTR_WARN)
            rows.append(_result_row(
                rule_id=f"VAL-001-{i:02d}",
                rule_name=f"CTR Achievement — {ad.ad_name}",
                status=status,
                expected_value=expected,
                actual_value=actual,
                variance=variance,
                severity=(
                    RuleSeverity.HARD.value if status == RuleStatus.FAIL.value
                    else RuleSeverity.SOFT.value
                ),
                category=_CAT_RATE,
                message=(
                    f"Ad '{ad.ad_name}': requested CTR={expected:.4f}, "
                    f"actual={actual:.4f}, variance={variance:+.4f} "
                    f"({n_imp} impressions, {n_clk} clicks)"
                ),
            ))
        return rows

    def _validate_open_rate(self, events_df: pd.DataFrame) -> list[dict]:
        """VAL-002: Open rate achievement per Email/WhatsApp ad."""
        rows: list[dict] = []
        for i, ad in enumerate(self._config.ads, start=1):
            if not (ad.is_email_channel() or ad.is_whatsapp_channel()):
                continue
            ch_cfg    = self._config.get_channel_config(ad.channel)
            expected  = (
                ch_cfg.target_open_rate
                if ch_cfg and ch_cfg.target_open_rate is not None
                else 0.25
            )
            ad_mask  = events_df["current_ad"] == ad.ad_name
            ad_evs   = events_df[ad_mask]
            n_sent   = int((ad_evs["action_type"] == _ACTION_SENT).sum())
            n_open   = int((ad_evs["action_type"] == ActionType.OPEN.value).sum())
            actual   = n_open / n_sent if n_sent > 0 else 0.0
            variance = actual - expected
            status   = _rate_status(abs(variance), _TOL_OPEN_PASS, _TOL_OPEN_WARN)
            rows.append(_result_row(
                rule_id=f"VAL-002-{i:02d}",
                rule_name=f"Open Rate Achievement — {ad.ad_name}",
                status=status,
                expected_value=expected,
                actual_value=actual,
                variance=variance,
                severity=(
                    RuleSeverity.HARD.value if status == RuleStatus.FAIL.value
                    else RuleSeverity.SOFT.value
                ),
                category=_CAT_RATE,
                message=(
                    f"Ad '{ad.ad_name}' ({ad.channel}): requested open_rate={expected:.4f}, "
                    f"actual={actual:.4f}, variance={variance:+.4f} "
                    f"({n_sent} sent, {n_open} opened)"
                ),
            ))
        return rows

    def _validate_trigger_engagement(
        self, events_df: pd.DataFrame, state_df: pd.DataFrame
    ) -> list[dict]:
        """VAL-003: Trigger Engagement Rate (TER) achievement per trigger."""
        rows: list[dict] = []
        if "trigger_name" not in events_df.columns or events_df.empty:
            return rows

        qual_mask = _qualifying_mask(events_df)
        qual_evs  = events_df[qual_mask]

        for i, trig in enumerate(self._config.triggers, start=1):
            # Denominator: all users assigned to this trigger in state_df
            if "trigger_name" in state_df.columns:
                user_mask = state_df["trigger_name"].astype(str) == trig.trigger_name
                n_users   = int(user_mask.sum())
            else:
                n_users = 0

            if n_users == 0:
                rows.append(_result_row(
                    rule_id=f"VAL-003-{i:02d}",
                    rule_name=f"TER Achievement — {trig.trigger_name}",
                    status=RuleStatus.SKIP.value,
                    expected_value=trig.engagement_rate_target,
                    actual_value=0.0,
                    variance=0.0,
                    severity=RuleSeverity.ADVISORY.value,
                    category=_CAT_RATE,
                    message=f"Trigger '{trig.trigger_name}': 0 users — skipped.",
                ))
                continue

            trig_qual = qual_evs[qual_evs["trigger_name"].astype(str) == trig.trigger_name]
            n_engaged = int(trig_qual["user_id"].nunique())
            actual    = n_engaged / n_users
            expected  = trig.engagement_rate_target
            variance  = actual - expected
            status    = _rate_status(abs(variance), _TOL_TER_PASS, _TOL_TER_WARN)
            rows.append(_result_row(
                rule_id=f"VAL-003-{i:02d}",
                rule_name=f"TER Achievement — {trig.trigger_name}",
                status=status,
                expected_value=expected,
                actual_value=actual,
                variance=variance,
                severity=(
                    RuleSeverity.HARD.value if status == RuleStatus.FAIL.value
                    else RuleSeverity.SOFT.value
                ),
                category=_CAT_RATE,
                message=(
                    f"Trigger '{trig.trigger_name}': target TER={expected:.4f}, "
                    f"actual={actual:.4f}, variance={variance:+.4f} "
                    f"({n_engaged}/{n_users} users engaged)"
                ),
            ))
        return rows

    def _validate_segment_engagement(
        self, events_df: pd.DataFrame, state_df: pd.DataFrame
    ) -> list[dict]:
        """VAL-004: Segment engagement rate (engaged % within segment)."""
        rows: list[dict] = []
        if not self._config.segments:
            return rows
        if "segment" not in events_df.columns:
            return rows

        qual_mask = _qualifying_mask(events_df)
        qual_evs  = events_df[qual_mask]
        total_engaged = max(1, int(qual_evs["user_id"].nunique()))

        for i, seg in enumerate(self._config.segments, start=1):
            if "segment" in state_df.columns:
                seg_mask = state_df["segment"].astype(str) == seg.segment_name
                n_seg    = int(seg_mask.sum())
            else:
                n_seg = 0

            # Segment distribution: what % of all engaged come from this segment
            seg_qual  = qual_evs[qual_evs["segment"].astype(str) == seg.segment_name]
            n_engaged = int(seg_qual["user_id"].nunique())
            actual    = n_engaged / total_engaged
            expected  = seg.distribution_pct / 100.0
            variance  = actual - expected
            status    = _rate_status(abs(variance), _TOL_SEG_PASS, _TOL_SEG_WARN)
            rows.append(_result_row(
                rule_id=f"VAL-004-{i:02d}",
                rule_name=f"Segment Engagement — {seg.segment_name}",
                status=status,
                expected_value=expected,
                actual_value=actual,
                variance=variance,
                severity=RuleSeverity.SOFT.value,
                category=_CAT_RATE,
                message=(
                    f"Segment '{seg.segment_name}': requested={expected:.4f}, "
                    f"actual={actual:.4f} ({n_engaged}/{total_engaged} total engaged)"
                ),
            ))
        return rows

    # -----------------------------------------------------------------------
    # Category 2: Capacity & Frequency
    # -----------------------------------------------------------------------

    def _validate_user_frequency(self, events_df: pd.DataFrame) -> list[dict]:
        """VAL-005: No user receives more than 1 reach event per day per channel.

        Display: max 1 Impression per user per day.
        Email/WA: max 1 Sent per user per day.
        """
        if events_df.empty:
            return [_result_row(
                rule_id="VAL-005",
                rule_name="User Daily Frequency",
                status=RuleStatus.SKIP.value,
                expected_value=1.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_CAPACITY,
                message="No events — skipped.",
            )]

        # Check max reach events per user per day per channel
        reach_mask = events_df["action_type"].isin(
            {ActionType.IMPRESSION.value, _ACTION_SENT}
        )
        reach_evs = events_df[reach_mask].copy()
        if reach_evs.empty:
            return [_result_row(
                rule_id="VAL-005",
                rule_name="User Daily Frequency",
                status=RuleStatus.SKIP.value,
                expected_value=1.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_CAPACITY,
                message="No reach events — skipped.",
            )]

        daily_counts = (
            reach_evs
            .groupby(["user_id", "simulation_date", "channel"])["action_type"]
            .count()
        )
        max_daily = int(daily_counts.max())
        n_violations = int((daily_counts > 1).sum())
        status = (
            RuleStatus.PASS.value if n_violations == 0
            else (RuleStatus.FAIL.value if max_daily > 2 else "Warning")
        )
        return [_result_row(
            rule_id="VAL-005",
            rule_name="User Daily Frequency",
            status=status,
            expected_value=1.0,
            actual_value=float(max_daily),
            variance=float(max_daily - 1),
            severity=(
                RuleSeverity.HARD.value if status == RuleStatus.FAIL.value
                else RuleSeverity.SOFT.value
            ),
            category=_CAT_CAPACITY,
            message=(
                f"Max reach events per user-day-channel: {max_daily} "
                f"({n_violations} user-day-channel combinations exceed 1)"
            ),
        )]

    def _validate_weekly_engagement_caps(
        self, events_df: pd.DataFrame
    ) -> list[dict]:
        """VAL-006: No user exceeds weekly_engagement_cap per ISO week."""
        cap = self._config.weekly_engagement_cap
        if events_df.empty:
            return [_result_row(
                rule_id="VAL-006",
                rule_name="Weekly Engagement Cap",
                status=RuleStatus.SKIP.value,
                expected_value=float(cap),
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_CAPACITY,
                message="No events — skipped.",
            )]

        qual_mask = _qualifying_mask(events_df)
        qual_evs  = events_df[qual_mask].copy()
        if qual_evs.empty:
            return [_result_row(
                rule_id="VAL-006",
                rule_name="Weekly Engagement Cap",
                status=RuleStatus.PASS.value,
                expected_value=float(cap),
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.SOFT.value,
                category=_CAT_CAPACITY,
                message="No qualifying events — cap not exercised.",
            )]

        # Use ISO week as grouping key
        sim_dates = pd.to_datetime(qual_evs["simulation_date"])
        qual_evs  = qual_evs.copy()
        qual_evs["_iso_week"] = (
            sim_dates.dt.isocalendar().year.astype(str)
            + "_" + sim_dates.dt.isocalendar().week.astype(str)
        )
        weekly = (
            qual_evs
            .groupby(["user_id", "_iso_week"])["action_type"]
            .count()
        )
        max_weekly   = int(weekly.max()) if not weekly.empty else 0
        n_violations = int((weekly > cap).sum())
        status = (
            RuleStatus.PASS.value if n_violations == 0
            else (RuleStatus.FAIL.value if max_weekly > cap * 2 else "Warning")
        )
        return [_result_row(
            rule_id="VAL-006",
            rule_name="Weekly Engagement Cap",
            status=status,
            expected_value=float(cap),
            actual_value=float(max_weekly),
            variance=float(max_weekly - cap),
            severity=(
                RuleSeverity.HARD.value if status == RuleStatus.FAIL.value
                else RuleSeverity.SOFT.value
            ),
            category=_CAT_CAPACITY,
            message=(
                f"weekly_engagement_cap={cap}, "
                f"max observed weekly engagements per user={max_weekly}, "
                f"{n_violations} user-week(s) exceed cap"
            ),
        )]

    def _validate_weekly_impression_caps(
        self, events_df: pd.DataFrame
    ) -> list[dict]:
        """VAL-007: No user exceeds weekly_impression_cap per ISO week."""
        cap = self._config.weekly_impression_cap
        if events_df.empty:
            return [_result_row(
                rule_id="VAL-007",
                rule_name="Weekly Impression Cap",
                status=RuleStatus.SKIP.value,
                expected_value=float(cap),
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_CAPACITY,
                message="No events — skipped.",
            )]

        imp_mask = events_df["action_type"] == ActionType.IMPRESSION.value
        imp_evs  = events_df[imp_mask].copy()
        if imp_evs.empty:
            return [_result_row(
                rule_id="VAL-007",
                rule_name="Weekly Impression Cap",
                status=RuleStatus.PASS.value,
                expected_value=float(cap),
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.SOFT.value,
                category=_CAT_CAPACITY,
                message="No impressions — cap not exercised.",
            )]

        sim_dates = pd.to_datetime(imp_evs["simulation_date"])
        imp_evs   = imp_evs.copy()
        imp_evs["_iso_week"] = (
            sim_dates.dt.isocalendar().year.astype(str)
            + "_" + sim_dates.dt.isocalendar().week.astype(str)
        )
        weekly = (
            imp_evs
            .groupby(["user_id", "_iso_week"])["action_type"]
            .count()
        )
        max_weekly   = int(weekly.max()) if not weekly.empty else 0
        n_violations = int((weekly > cap).sum())
        status = (
            RuleStatus.PASS.value if n_violations == 0
            else (RuleStatus.FAIL.value if max_weekly > cap * 2 else "Warning")
        )
        return [_result_row(
            rule_id="VAL-007",
            rule_name="Weekly Impression Cap",
            status=status,
            expected_value=float(cap),
            actual_value=float(max_weekly),
            variance=float(max_weekly - cap),
            severity=(
                RuleSeverity.HARD.value if status == RuleStatus.FAIL.value
                else RuleSeverity.SOFT.value
            ),
            category=_CAT_CAPACITY,
            message=(
                f"weekly_impression_cap={cap}, "
                f"max observed weekly impressions per user={max_weekly}, "
                f"{n_violations} user-week(s) exceed cap"
            ),
        )]

    # -----------------------------------------------------------------------
    # Category 3: Journey Validation
    # -----------------------------------------------------------------------

    def _validate_journey_progression(
        self, events_df: pd.DataFrame, state_df: pd.DataFrame
    ) -> list[dict]:
        """VAL-008: Users in final Not_Started state should have no events."""
        if "journey_status" not in state_df.columns or events_df.empty:
            return [_result_row(
                rule_id="VAL-008",
                rule_name="Journey Progression",
                status=RuleStatus.SKIP.value,
                expected_value=0.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_JOURNEY,
                message="Required columns not available — skipped.",
            )]

        never_started = set(
            state_df.loc[
                state_df["journey_status"] == JourneyStatus.NOT_STARTED.value,
                "user_id",
            ]
        )
        events_users = set(events_df["user_id"].unique())
        violations   = never_started & events_users
        n_violations = len(violations)
        n_not_started = len(never_started)

        status = RuleStatus.PASS.value if n_violations == 0 else RuleStatus.FAIL.value
        return [_result_row(
            rule_id="VAL-008",
            rule_name="Journey Progression",
            status=status,
            expected_value=0.0,
            actual_value=float(n_violations),
            variance=float(n_violations),
            severity=(
                RuleSeverity.HARD.value if n_violations > 0
                else RuleSeverity.SOFT.value
            ),
            category=_CAT_JOURNEY,
            message=(
                f"{n_violations} users with journey_status=Not_Started "
                f"have events (of {n_not_started} not-started users)"
            ),
        )]

    # -----------------------------------------------------------------------
    # Category 4: Trigger Rules
    # -----------------------------------------------------------------------

    def _validate_trigger_priority(
        self, events_df: pd.DataFrame, state_df: pd.DataFrame
    ) -> list[dict]:
        """VAL-009: Trigger names in events/state must all be known triggers."""
        if "trigger_name" not in events_df.columns or events_df.empty:
            return [_result_row(
                rule_id="VAL-009",
                rule_name="Trigger Priority Correctness",
                status=RuleStatus.SKIP.value,
                expected_value=0.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_TRIGGER,
                message="No trigger_name column in events — skipped.",
            )]

        known = {t.trigger_name for t in self._config.triggers}
        # Unknown trigger names in events (excluding NaN/None/empty)
        ev_triggers   = events_df["trigger_name"].astype(str).dropna()
        ev_triggers   = ev_triggers[ev_triggers.str.strip() != ""]
        ev_triggers   = ev_triggers[ev_triggers != "nan"]
        unknown_set   = set(ev_triggers.unique()) - known
        n_unknown_ev  = len(unknown_set)

        # Check state_df too
        n_unknown_st = 0
        if "trigger_name" in state_df.columns and not state_df.empty:
            st_triggers = state_df["trigger_name"].astype(str).dropna()
            st_triggers = st_triggers[st_triggers.str.strip() != ""]
            st_triggers = st_triggers[st_triggers != "nan"]
            n_unknown_st = len(set(st_triggers.unique()) - known)

        n_violations = n_unknown_ev + n_unknown_st
        status = RuleStatus.PASS.value if n_violations == 0 else RuleStatus.FAIL.value
        return [_result_row(
            rule_id="VAL-009",
            rule_name="Trigger Priority Correctness",
            status=status,
            expected_value=0.0,
            actual_value=float(n_violations),
            variance=float(n_violations),
            severity=(
                RuleSeverity.HARD.value if n_violations > 0
                else RuleSeverity.SOFT.value
            ),
            category=_CAT_TRIGGER,
            message=(
                f"{n_violations} unknown trigger name(s) found "
                f"(events: {n_unknown_ev}, state: {n_unknown_st}). "
                f"Known: {sorted(known)}"
            ),
        )]

    def _validate_multi_trigger(self, events_df: pd.DataFrame) -> list[dict]:
        """VAL-010: Each user should have exactly one trigger_name in events."""
        if "trigger_name" not in events_df.columns or events_df.empty:
            return [_result_row(
                rule_id="VAL-010",
                rule_name="Multi-Trigger Consistency",
                status=RuleStatus.SKIP.value,
                expected_value=1.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_TRIGGER,
                message="No trigger_name column in events — skipped.",
            )]

        # Count distinct trigger names per user (ignoring nulls)
        ev = events_df.copy()
        ev["_trig_str"] = ev["trigger_name"].astype(str)
        ev = ev[ev["_trig_str"].str.strip() != ""]
        ev = ev[ev["_trig_str"] != "nan"]

        if ev.empty:
            return [_result_row(
                rule_id="VAL-010",
                rule_name="Multi-Trigger Consistency",
                status=RuleStatus.SKIP.value,
                expected_value=1.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_TRIGGER,
                message="No events with trigger_name — skipped.",
            )]

        per_user = ev.groupby("user_id")["_trig_str"].nunique()
        max_trigs    = int(per_user.max())
        n_violations = int((per_user > 1).sum())
        status = RuleStatus.PASS.value if n_violations == 0 else "Warning"
        return [_result_row(
            rule_id="VAL-010",
            rule_name="Multi-Trigger Consistency",
            status=status,
            expected_value=1.0,
            actual_value=float(max_trigs),
            variance=float(max_trigs - 1),
            severity=RuleSeverity.SOFT.value,
            category=_CAT_TRIGGER,
            message=(
                f"{n_violations} user(s) appear with >1 trigger name in events "
                f"(max per user: {max_trigs})"
            ),
        )]

    # -----------------------------------------------------------------------
    # Category 5: Segment Rules
    # -----------------------------------------------------------------------

    def _validate_segment_distribution(
        self, events_df: pd.DataFrame, state_df: pd.DataFrame
    ) -> list[dict]:
        """VAL-011: Actual user-level segment distribution vs requested."""
        rows: list[dict] = []
        if not self._config.segments:
            return rows

        # Use state_df for denominator (total users per segment)
        total_users = max(1, len(state_df))

        for i, seg in enumerate(self._config.segments, start=1):
            if "segment" in state_df.columns:
                seg_mask  = state_df["segment"].astype(str) == seg.segment_name
                n_in_seg  = int(seg_mask.sum())
            else:
                n_in_seg  = 0

            actual    = n_in_seg / total_users
            expected  = seg.distribution_pct / 100.0
            variance  = actual - expected
            status    = _rate_status(abs(variance), _TOL_SEG_PASS, _TOL_SEG_WARN)
            rows.append(_result_row(
                rule_id=f"VAL-011-{i:02d}",
                rule_name=f"Segment Distribution — {seg.segment_name}",
                status=status,
                expected_value=expected,
                actual_value=actual,
                variance=variance,
                severity=RuleSeverity.SOFT.value,
                category=_CAT_SEGMENT,
                message=(
                    f"Segment '{seg.segment_name}': "
                    f"requested={expected:.4f}, actual={actual:.4f} "
                    f"({n_in_seg}/{total_users} users)"
                ),
            ))
        return rows

    # -----------------------------------------------------------------------
    # Category 6: Channel Rules (Causal Chains)
    # -----------------------------------------------------------------------

    def _validate_channel_dependencies(
        self, events_df: pd.DataFrame
    ) -> list[dict]:
        """VAL-012: Validate channel causal chains (HR-003..HR-008).

        VAL-012a: Display — Click requires same-day Impression.
        VAL-012b: Email   — Open requires same-day Sent; Click requires Open.
        VAL-012c: WA      — Open requires same-day Sent; Click requires Open.
        """
        rows: list[dict] = []
        if events_df.empty:
            for sub, label in [("a", "Display Click→Impression"),
                                ("b", "Email Open→Sent / Click→Open"),
                                ("c", "WhatsApp Open→Sent / Click→Open")]:
                rows.append(_result_row(
                    rule_id=f"VAL-012{sub}",
                    rule_name=f"Channel Dependency — {label}",
                    status=RuleStatus.SKIP.value,
                    expected_value=0.0,
                    actual_value=0.0,
                    variance=0.0,
                    severity=RuleSeverity.ADVISORY.value,
                    category=_CAT_CHANNEL,
                    message="No events — skipped.",
                ))
            return rows

        key_cols = ["user_id", "simulation_date", "current_ad"]

        # ── VAL-012a: Display Click requires Impression ───────────────────
        disp_evs = events_df[events_df["channel"].isin(_DISPLAY_CHANNELS)]
        rows.append(
            self._check_prerequisite(
                child_evs=disp_evs[
                    disp_evs["action_type"] == ActionType.CLICK.value
                ],
                parent_evs=disp_evs[
                    disp_evs["action_type"] == ActionType.IMPRESSION.value
                ],
                key_cols=key_cols,
                rule_id="VAL-012a",
                rule_name="Channel Dependency — Display Click→Impression",
                child_label="Click", parent_label="Impression",
            )
        )

        # ── VAL-012b: Email causal chain ──────────────────────────────────
        em_evs = events_df[events_df["channel"] == "Email"]
        rows.append(
            self._check_prerequisite(
                child_evs=em_evs[em_evs["action_type"] == ActionType.OPEN.value],
                parent_evs=em_evs[em_evs["action_type"] == _ACTION_SENT],
                key_cols=key_cols,
                rule_id="VAL-012b-open",
                rule_name="Channel Dependency — Email Open→Sent",
                child_label="Open", parent_label="Sent",
            )
        )
        rows.append(
            self._check_prerequisite(
                child_evs=em_evs[em_evs["action_type"] == ActionType.CLICK.value],
                parent_evs=em_evs[em_evs["action_type"] == ActionType.OPEN.value],
                key_cols=key_cols,
                rule_id="VAL-012b-click",
                rule_name="Channel Dependency — Email Click→Open",
                child_label="Click", parent_label="Open",
            )
        )

        # ── VAL-012c: WhatsApp causal chain ───────────────────────────────
        wa_evs = events_df[events_df["channel"] == "WhatsApp"]
        rows.append(
            self._check_prerequisite(
                child_evs=wa_evs[wa_evs["action_type"] == ActionType.OPEN.value],
                parent_evs=wa_evs[wa_evs["action_type"] == _ACTION_SENT],
                key_cols=key_cols,
                rule_id="VAL-012c-open",
                rule_name="Channel Dependency — WhatsApp Open→Sent",
                child_label="Open", parent_label="Sent",
            )
        )
        rows.append(
            self._check_prerequisite(
                child_evs=wa_evs[wa_evs["action_type"] == ActionType.CLICK.value],
                parent_evs=wa_evs[wa_evs["action_type"] == ActionType.OPEN.value],
                key_cols=key_cols,
                rule_id="VAL-012c-click",
                rule_name="Channel Dependency — WhatsApp Click→Open",
                child_label="Click", parent_label="Open",
            )
        )

        return rows

    def _check_prerequisite(
        self,
        child_evs: pd.DataFrame,
        parent_evs: pd.DataFrame,
        key_cols: list[str],
        rule_id: str,
        rule_name: str,
        child_label: str,
        parent_label: str,
    ) -> dict:
        """Check that every child event has a corresponding parent event.

        Uses a merge (not iterrows) to find orphan child events.
        """
        if child_evs.empty:
            return _result_row(
                rule_id=rule_id,
                rule_name=rule_name,
                status=RuleStatus.PASS.value,
                expected_value=0.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.HARD.value,
                category=_CAT_CHANNEL,
                message=f"No {child_label} events — rule vacuously satisfied.",
            )

        if parent_evs.empty:
            # If there are child events but no parent events → all orphans
            n_orphan = len(child_evs)
            return _result_row(
                rule_id=rule_id,
                rule_name=rule_name,
                status=RuleStatus.FAIL.value,
                expected_value=0.0,
                actual_value=float(n_orphan),
                variance=float(n_orphan),
                severity=RuleSeverity.HARD.value,
                category=_CAT_CHANNEL,
                message=(
                    f"{n_orphan} {child_label} event(s) with no corresponding "
                    f"{parent_label} on the same day."
                ),
            )

        # Vectorised: merge child onto parent on key columns
        avail_key = [c for c in key_cols if c in child_evs.columns
                     and c in parent_evs.columns]
        parent_keys = parent_evs[avail_key].drop_duplicates()
        merged = child_evs.merge(parent_keys, on=avail_key, how="left", indicator=True)
        n_orphan = int((merged["_merge"] == "left_only").sum())
        status   = RuleStatus.PASS.value if n_orphan == 0 else RuleStatus.FAIL.value
        return _result_row(
            rule_id=rule_id,
            rule_name=rule_name,
            status=status,
            expected_value=0.0,
            actual_value=float(n_orphan),
            variance=float(n_orphan),
            severity=RuleSeverity.HARD.value,
            category=_CAT_CHANNEL,
            message=(
                f"{n_orphan}/{len(child_evs)} {child_label} event(s) missing "
                f"a same-day {parent_label}."
            ),
        )

    # -----------------------------------------------------------------------
    # Category 7: TCC Validation
    # -----------------------------------------------------------------------

    def _validate_tcc_calculations(
        self, events_df: pd.DataFrame, state_df: pd.DataFrame
    ) -> list[dict]:
        """VAL-013: Actual new engagements ≤ TCC ceiling per trigger (TCC-001..003).

        TCC ceiling = max(0, ceil(n_trigger_users × target_rate))
        New engagements = engaged users who were NOT historically engaged.
        """
        rows: list[dict] = []
        if events_df.empty or "trigger_name" not in events_df.columns:
            return [_result_row(
                rule_id="VAL-013",
                rule_name="TCC Calculation Correctness",
                status=RuleStatus.SKIP.value,
                expected_value=0.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_TCC,
                message="No events or no trigger_name — skipped.",
            )]

        qual_mask = _qualifying_mask(events_df)
        qual_evs  = events_df[qual_mask]

        for i, trig in enumerate(self._config.triggers, start=1):
            # n users in trigger
            if "trigger_name" not in state_df.columns:
                n_users = 0
            else:
                trig_mask = state_df["trigger_name"].astype(str) == trig.trigger_name
                n_users   = int(trig_mask.sum())

            if n_users == 0:
                rows.append(_result_row(
                    rule_id=f"VAL-013-{i:02d}",
                    rule_name=f"TCC Calculation — {trig.trigger_name}",
                    status=RuleStatus.SKIP.value,
                    expected_value=0.0,
                    actual_value=0.0,
                    variance=0.0,
                    severity=RuleSeverity.ADVISORY.value,
                    category=_CAT_TCC,
                    message=f"Trigger '{trig.trigger_name}': 0 users — skipped.",
                ))
                continue

            tcc_ceiling = math.ceil(n_users * trig.engagement_rate_target)

            # New engagements: qualifying events from non-historical users
            trig_qual = qual_evs[qual_evs["trigger_name"].astype(str) == trig.trigger_name]

            if "historical_engaged" in state_df.columns:
                trig_state = state_df[
                    state_df["trigger_name"].astype(str) == trig.trigger_name
                ]
                hist_users = set(
                    trig_state.loc[
                        trig_state["historical_engaged"].astype(bool), "user_id"
                    ]
                )
                new_qual   = trig_qual[~trig_qual["user_id"].isin(hist_users)]
            else:
                new_qual   = trig_qual

            n_new_engaged = int(new_qual["user_id"].nunique())
            variance      = float(n_new_engaged - tcc_ceiling)
            status = (
                RuleStatus.PASS.value if n_new_engaged <= tcc_ceiling
                else RuleStatus.FAIL.value
            )
            rows.append(_result_row(
                rule_id=f"VAL-013-{i:02d}",
                rule_name=f"TCC Calculation — {trig.trigger_name}",
                status=status,
                expected_value=float(tcc_ceiling),
                actual_value=float(n_new_engaged),
                variance=variance,
                severity=(
                    RuleSeverity.HARD.value if status == RuleStatus.FAIL.value
                    else RuleSeverity.SOFT.value
                ),
                category=_CAT_TCC,
                message=(
                    f"Trigger '{trig.trigger_name}': "
                    f"TCC ceiling={tcc_ceiling} "
                    f"(ceil({n_users}×{trig.engagement_rate_target:.4f})), "
                    f"new engagements={n_new_engaged}"
                ),
            ))
        return rows

    # -----------------------------------------------------------------------
    # Category 8: Historical Engagement
    # -----------------------------------------------------------------------

    def _validate_historical_engagement(
        self, events_df: pd.DataFrame, state_df: pd.DataFrame
    ) -> list[dict]:
        """VAL-014: Users with qualifying events must have total_lifetime_engagements > 0.

        Cross-checks events_df qualified users against state_df counters.
        """
        if events_df.empty:
            return [_result_row(
                rule_id="VAL-014",
                rule_name="Historical Engagement Tracking",
                status=RuleStatus.SKIP.value,
                expected_value=0.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_HISTORICAL,
                message="No events — skipped.",
            )]

        if "total_lifetime_engagements" not in state_df.columns:
            return [_result_row(
                rule_id="VAL-014",
                rule_name="Historical Engagement Tracking",
                status=RuleStatus.SKIP.value,
                expected_value=0.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.ADVISORY.value,
                category=_CAT_HISTORICAL,
                message="total_lifetime_engagements column absent — skipped.",
            )]

        qual_mask  = _qualifying_mask(events_df)
        qual_users = set(events_df.loc[qual_mask, "user_id"].unique())
        if not qual_users:
            return [_result_row(
                rule_id="VAL-014",
                rule_name="Historical Engagement Tracking",
                status=RuleStatus.PASS.value,
                expected_value=0.0,
                actual_value=0.0,
                variance=0.0,
                severity=RuleSeverity.SOFT.value,
                category=_CAT_HISTORICAL,
                message="No qualifying events — nothing to cross-check.",
            )]

        # Vectorised: filter state_df to users who qualified
        engaged_state = state_df[state_df["user_id"].isin(qual_users)]
        n_zero_counter = int(
            (engaged_state["total_lifetime_engagements"] == 0).sum()
        )
        n_qualified   = len(qual_users)
        variance      = float(n_zero_counter)
        status = RuleStatus.PASS.value if n_zero_counter == 0 else "Warning"
        return [_result_row(
            rule_id="VAL-014",
            rule_name="Historical Engagement Tracking",
            status=status,
            expected_value=0.0,
            actual_value=float(n_zero_counter),
            variance=variance,
            severity=RuleSeverity.SOFT.value,
            category=_CAT_HISTORICAL,
            message=(
                f"{n_zero_counter}/{n_qualified} users with qualifying events "
                "have total_lifetime_engagements=0 in final state."
            ),
        )]

    # -----------------------------------------------------------------------
    # Summary and Realism
    # -----------------------------------------------------------------------

    def _build_summary(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """Build per-category validation summary."""
        if results_df.empty:
            return _empty_summary_df()

        categories = [
            _CAT_RATE, _CAT_CAPACITY, _CAT_JOURNEY, _CAT_TRIGGER,
            _CAT_SEGMENT, _CAT_CHANNEL, _CAT_TCC, _CAT_HISTORICAL,
        ]
        # Map rule_id to category via prefix or severity
        cat_map = _build_category_map(results_df)
        results_df = results_df.copy()
        results_df["_cat"] = results_df["rule_id"].map(cat_map).fillna("Other")

        rows = []
        for cat in categories:
            sub = results_df[results_df["_cat"] == cat]
            if sub.empty:
                rows.append({
                    "validation_category": cat,
                    "passed": 0,
                    "failed": 0,
                    "warning": 0,
                    "score": 100.0,
                })
                continue
            n_pass = int((sub["status"] == RuleStatus.PASS.value).sum())
            n_fail = int((sub["status"] == RuleStatus.FAIL.value).sum())
            n_warn = int((sub["status"] == "Warning").sum())
            score  = _compute_quality_score(sub)
            rows.append({
                "validation_category": cat,
                "passed": n_pass,
                "failed": n_fail,
                "warning": n_warn,
                "score": round(score, 2),
            })

        # Overall row
        n_pass = int((results_df["status"] == RuleStatus.PASS.value).sum())
        n_fail = int((results_df["status"] == RuleStatus.FAIL.value).sum())
        n_warn = int((results_df["status"] == "Warning").sum())
        overall_score = _compute_quality_score(results_df)
        rows.append({
            "validation_category": "OVERALL",
            "passed": n_pass,
            "failed": n_fail,
            "warning": n_warn,
            "score": round(overall_score, 2),
        })

        return pd.DataFrame(rows, columns=list(_SUMMARY_COLS))

    def _build_realism_report(
        self, events_df: pd.DataFrame, state_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Build realism report comparing requested vs actual rates."""
        rows: list[dict] = []

        # CTR metrics
        disp_evs = (
            events_df[events_df["channel"].isin(_DISPLAY_CHANNELS)]
            if not events_df.empty else events_df
        )
        for ad in self._config.ads:
            if not ad.is_display_channel():
                continue
            target   = ad.target_ctr if ad.target_ctr is not None else 0.05
            ad_evs   = disp_evs[disp_evs["current_ad"] == ad.ad_name] if not disp_evs.empty else disp_evs
            n_imp    = int((ad_evs["action_type"] == ActionType.IMPRESSION.value).sum()) if not ad_evs.empty else 0
            n_clk    = int((ad_evs["action_type"] == ActionType.CLICK.value).sum()) if not ad_evs.empty else 0
            actual   = n_clk / n_imp if n_imp > 0 else 0.0
            rows.append(_realism_row(f"CTR — {ad.ad_name}", target, actual))

        # Open rate metrics
        for ad in self._config.ads:
            if not (ad.is_email_channel() or ad.is_whatsapp_channel()):
                continue
            ch_cfg  = self._config.get_channel_config(ad.channel)
            target  = (
                ch_cfg.target_open_rate
                if ch_cfg and ch_cfg.target_open_rate is not None
                else 0.25
            )
            ad_evs  = events_df[events_df["current_ad"] == ad.ad_name] if not events_df.empty else events_df
            n_sent  = int((ad_evs["action_type"] == _ACTION_SENT).sum()) if not ad_evs.empty else 0
            n_open  = int((ad_evs["action_type"] == ActionType.OPEN.value).sum()) if not ad_evs.empty else 0
            actual  = n_open / n_sent if n_sent > 0 else 0.0
            rows.append(_realism_row(f"Open Rate — {ad.ad_name}", target, actual))

        # TER metrics
        if not events_df.empty and "trigger_name" in events_df.columns:
            qual_evs = events_df[_qualifying_mask(events_df)]
            for trig in self._config.triggers:
                if "trigger_name" in state_df.columns:
                    n_users = int(
                        (state_df["trigger_name"].astype(str) == trig.trigger_name).sum()
                    )
                else:
                    n_users = 0
                if n_users == 0:
                    continue
                n_engaged = int(
                    qual_evs[qual_evs["trigger_name"].astype(str) == trig.trigger_name]
                    ["user_id"].nunique()
                )
                actual = n_engaged / n_users
                rows.append(_realism_row(
                    f"TER — {trig.trigger_name}", trig.engagement_rate_target, actual
                ))

        if not rows:
            return _empty_realism_df()

        return pd.DataFrame(rows, columns=list(_REALISM_COLS))


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


def _rate_status(abs_variance: float, pass_tol: float, warn_tol: float) -> str:
    """Map absolute variance to Pass/Warning/Fail."""
    if abs_variance <= pass_tol:
        return RuleStatus.PASS.value
    elif abs_variance <= warn_tol:
        return "Warning"
    return RuleStatus.FAIL.value


def _result_row(
    rule_id: str,
    rule_name: str,
    status: str,
    expected_value: float,
    actual_value: float,
    variance: float,
    severity: str,
    category: str,     # used internally for summary building
    message: str,
) -> dict:
    """Build a single validation result row."""
    return {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "status": status,
        "expected_value": expected_value,
        "actual_value": actual_value,
        "variance": variance,
        "severity": severity,
        "message": message,
        "_category": category,   # internal — stripped before output
    }


def _realism_row(metric: str, target: float, actual: float) -> dict:
    """Build a single realism report row."""
    variance     = actual - target
    eps          = 1e-10
    variance_pct = (variance / target * 100.0) if abs(target) > eps else 0.0
    realism_val  = max(0.0, 1.0 - abs(variance) / max(abs(target), eps)) * 100.0
    status = (
        "Good" if realism_val >= _REALISM_GOOD
        else ("Acceptable" if realism_val >= _REALISM_ACCEPTABLE else "Poor")
    )
    return {
        "metric": metric,
        "target": target,
        "actual": actual,
        "variance": variance,
        "variance_pct": variance_pct,
        "status": status,
    }


def _compute_quality_score(results_df: pd.DataFrame) -> float:
    """Weighted quality score 0–100.

    Hard=3, Soft=2, Advisory=1.  Pass=1.0, Warning=0.5, Fail=0.0, Skip=1.0.
    Fully vectorised — no iterrows().
    """
    if results_df.empty:
        return 100.0
    non_skip = results_df[results_df["status"] != RuleStatus.SKIP.value].copy()
    if non_skip.empty:
        return 100.0
    non_skip["_w"] = non_skip["severity"].map(_SEV_WEIGHT).fillna(1.0)
    non_skip["_s"] = non_skip["status"].map(_OUTCOME_SCORE).fillna(0.0)
    total_weight = float(non_skip["_w"].sum())
    if total_weight == 0.0:
        return 100.0
    weighted = float((non_skip["_w"] * non_skip["_s"]).sum())
    return round(min(100.0, max(0.0, weighted / total_weight * 100.0)), 2)


def _compute_realism_score(realism_df: pd.DataFrame) -> float:
    """Unweighted mean of per-metric realism status scores. Fully vectorised."""
    if realism_df.empty:
        return 100.0
    eps = 1e-10
    target_abs   = realism_df["target"].abs().clip(lower=eps)
    variance_abs = realism_df["variance"].abs()
    scores       = (1.0 - variance_abs / target_abs).clip(lower=0.0) * 100.0
    # Zero-target metrics: perfect score (no target to miss)
    zero_mask    = realism_df["target"].abs() < eps
    scores       = scores.where(~zero_mask, 100.0)
    return round(float(scores.mean()), 2)


def _build_category_map(results_df: pd.DataFrame) -> dict[str, str]:
    """Map rule_id → category string from internal _category column if present."""
    if "_category" in results_df.columns:
        return dict(zip(results_df["rule_id"], results_df["_category"]))
    # Fallback: infer from rule_id prefix
    prefix_map = {
        "VAL-001": _CAT_RATE,
        "VAL-002": _CAT_RATE,
        "VAL-003": _CAT_RATE,
        "VAL-004": _CAT_RATE,
        "VAL-005": _CAT_CAPACITY,
        "VAL-006": _CAT_CAPACITY,
        "VAL-007": _CAT_CAPACITY,
        "VAL-008": _CAT_JOURNEY,
        "VAL-009": _CAT_TRIGGER,
        "VAL-010": _CAT_TRIGGER,
        "VAL-011": _CAT_SEGMENT,
        "VAL-012": _CAT_CHANNEL,
        "VAL-013": _CAT_TCC,
        "VAL-014": _CAT_HISTORICAL,
    }
    cat_map = {}
    for rid in results_df["rule_id"]:
        prefix = rid[:7]
        cat_map[rid] = prefix_map.get(prefix, "Other")
    return cat_map


def _normalise_events(events_df: pd.DataFrame) -> pd.DataFrame:
    """Ensure events_df uses string simulation_date for consistency."""
    df = events_df.copy()
    # Ensure channel and action_type are strings
    df["channel"]     = df["channel"].astype(str)
    df["action_type"] = df["action_type"].astype(str)
    df["user_id"]     = df["user_id"].astype(str)
    if "current_ad" in df.columns:
        df["current_ad"] = df["current_ad"].astype(str)
    return df


def _validate_events_columns(events_df: pd.DataFrame) -> None:
    """Raise InputValidationError if events_df is missing required columns."""
    missing = [c for c in _EVENTS_REQUIRED if c not in events_df.columns]
    if missing:
        raise InputValidationError(
            "events_df",
            f"ValidationEngine: missing required column(s): {missing}",
        )


def _empty_results_df() -> pd.DataFrame:
    """Return empty results DataFrame including internal _category column."""
    cols = list(_RESULTS_COLS) + ["_category"]
    return pd.DataFrame(columns=cols)


def _empty_summary_df() -> pd.DataFrame:
    return pd.DataFrame(columns=list(_SUMMARY_COLS))


def _empty_realism_df() -> pd.DataFrame:
    return pd.DataFrame(columns=list(_REALISM_COLS))


__all__ = ["ValidationEngine"]
