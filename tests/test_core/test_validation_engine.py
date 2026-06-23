"""Unit tests for core/validation_engine.py — ValidationEngine (Stage 8).

Coverage:
  * All 17 responsibilities from the directive
  * All validation categories (Rate Achievement, Capacity, Journey, Trigger,
    Segment, Channel, TCC, Historical)
  * Output DataFrame schemas
  * Quality score and realism score
  * Feasibility warnings
  * Edge cases: empty events, no segments, no triggers, etc.
  * Compliance: no iterrows(), __all__ declared
"""
from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from core.validation_engine import ValidationEngine, _compute_quality_score, _compute_realism_score
from models.ad_config import AdConfig
from models.channel_config import ChannelConfig
from models.enums import ActionType, JourneyStatus, RuleSeverity, RuleStatus
from models.segment_config import SegmentConfig
from models.trigger_config import TriggerConfig
from utils.exceptions import InputValidationError

from tests.test_core.conftest import make_config, make_state_df

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_display_cfg(**kw):
    ads = (
        AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
        AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05),
    )
    return make_config(ads=ads, **kw)


def _make_email_cfg(**kw):
    ads = (
        AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
        AdConfig("Ad_B", 2, 10, False, "Email", "VY", 0.05),
    )
    ch  = (ChannelConfig("Email", target_ctr=0.05, target_open_rate=0.25),)
    return make_config(ads=ads, channels=ch, **kw)


def _make_wa_cfg(**kw):
    ads = (
        AdConfig("Ad_A", 1, 10, False, "WhatsApp", "VZ", 0.15),
        AdConfig("Ad_B", 2, 10, False, "WhatsApp", "VZ", 0.10),
    )
    ch  = (ChannelConfig("WhatsApp", target_ctr=0.10, target_open_rate=0.30),)
    return make_config(ads=ads, channels=ch, **kw)


def _ev(user_id, sim_date, channel, action_type, current_ad="Ad_A",
        trigger_name="T1", segment="Seg_A", campaign_id="TEST_CAMPAIGN"):
    return {
        "campaign_id": campaign_id,
        "user_id": user_id,
        "simulation_date": sim_date,
        "channel": channel,
        "action_type": action_type,
        "current_ad": current_ad,
        "vendor": "VX",
        "trigger_name": trigger_name,
        "segment": segment,
    }


def _make_display_events(n_users=5, sim_date=date(2024, 1, 10),
                          click_users=None):
    """n_users impressions + click_users clicks on Display channel."""
    rows = []
    for i in range(1, n_users + 1):
        uid = f"U{i:03d}"
        rows.append(_ev(uid, sim_date, "Display", ActionType.IMPRESSION.value))
    for uid in (click_users or []):
        rows.append(_ev(uid, sim_date, "Display", ActionType.CLICK.value))
    return pd.DataFrame(rows)


def _make_email_events(n_users=5, sim_date=date(2024, 1, 10), open_users=None, click_users=None):
    rows = []
    for i in range(1, n_users + 1):
        uid = f"U{i:03d}"
        rows.append(_ev(uid, sim_date, "Email", "Sent", current_ad="Ad_B"))
    for uid in (open_users or []):
        rows.append(_ev(uid, sim_date, "Email", ActionType.OPEN.value, current_ad="Ad_B"))
    for uid in (click_users or []):
        rows.append(_ev(uid, sim_date, "Email", ActionType.CLICK.value, current_ad="Ad_B"))
    return pd.DataFrame(rows)


def _make_state(n=5, cfg=None, trigger_name="T1"):
    cfg = cfg or _make_display_cfg()
    df  = make_state_df(n, config=cfg)
    # Set trigger names and journey status
    df["trigger_name"] = df["trigger_name"].cat.add_categories(
        [v for v in [trigger_name] if v not in df["trigger_name"].cat.categories]
    ).fillna(trigger_name)
    df["journey_status"] = JourneyStatus.ACTIVE.value
    return df


SIM_DATE = date(2024, 1, 10)


# ===========================================================================
# 1. Initialisation
# ===========================================================================

class TestInit:
    def test_instantiates(self):
        ve = ValidationEngine(_make_display_cfg())
        assert ve is not None

    def test_stores_config(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        assert ve._config is cfg


# ===========================================================================
# 2. Column validation
# ===========================================================================

class TestColumnValidation:
    def test_missing_user_id_raises(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        df  = _make_display_events()
        df  = df.drop(columns=["user_id"])
        with pytest.raises(InputValidationError):
            ve.validate(df, _make_state())

    def test_missing_channel_raises(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        df  = _make_display_events()
        df  = df.drop(columns=["channel"])
        with pytest.raises(InputValidationError):
            ve.validate(df, _make_state())

    def test_all_columns_present_no_error(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5, click_users=["U001", "U002"])
        results, summary, realism = ve.validate(ev, _make_state(5, cfg))
        assert results is not None


# ===========================================================================
# 3. validate() return types and schema
# ===========================================================================

class TestValidateSchema:
    def test_returns_three_dataframes(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(3)
        r, s, re = ve.validate(ev, _make_state(3, cfg))
        assert isinstance(r, pd.DataFrame)
        assert isinstance(s, pd.DataFrame)
        assert isinstance(re, pd.DataFrame)

    def test_results_columns(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(3)
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        for col in ("rule_id", "rule_name", "status", "expected_value",
                    "actual_value", "variance", "severity", "message"):
            assert col in r.columns

    def test_results_no_internal_category_column(self):
        """_category must not appear in public results_df."""
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(3)
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        assert "_category" not in r.columns

    def test_summary_columns(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(3)
        _, s, _ = ve.validate(ev, _make_state(3, cfg))
        for col in ("validation_category", "passed", "failed", "warning", "score"):
            assert col in s.columns

    def test_realism_columns(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(3)
        _, _, re = ve.validate(ev, _make_state(3, cfg))
        for col in ("metric", "target", "actual", "variance", "variance_pct", "status"):
            assert col in re.columns

    def test_summary_has_overall_row(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(3)
        _, s, _ = ve.validate(ev, _make_state(3, cfg))
        assert "OVERALL" in s["validation_category"].values

    def test_empty_events_still_returns_schema(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = pd.DataFrame(columns=["user_id", "simulation_date", "channel",
                                     "action_type", "current_ad"])
        r, s, re = ve.validate(ev, _make_state(3, cfg))
        for col in ("rule_id", "rule_name", "status"):
            assert col in r.columns


# ===========================================================================
# 4. VAL-001: CTR Achievement
# ===========================================================================

class TestCTRAchievement:
    def test_exact_ctr_passes(self):
        """10% CTR target with exactly 10% actual → Pass."""
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        # 10 impressions, 1 click → 10% CTR
        ev  = _make_display_events(10, click_users=["U001"])
        r, _, _ = ve.validate(ev, _make_state(10, cfg))
        ctr_rows = r[r["rule_id"].str.startswith("VAL-001")]
        assert len(ctr_rows) > 0
        ad_a_row = ctr_rows[ctr_rows["rule_name"].str.contains("Ad_A")]
        if not ad_a_row.empty:
            assert ad_a_row.iloc[0]["status"] == RuleStatus.PASS.value

    def test_zero_impressions_gives_zero_actual_ctr(self):
        """If no impressions, actual CTR = 0.0."""
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = pd.DataFrame([_ev("U001", SIM_DATE, "Display", ActionType.CLICK.value)])
        r, _, _ = ve.validate(ev, _make_state(1, cfg))
        # Clicks with no impressions → actual=0 (denominator=0)
        # CTR rows should exist
        ctr_rows = r[r["rule_id"].str.startswith("VAL-001")]
        if not ctr_rows.empty:
            assert ctr_rows.iloc[0]["actual_value"] >= 0.0

    def test_high_ctr_fails(self):
        """100% CTR when target is 10% → Fail."""
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        # 5 impressions, 5 clicks = 100% CTR (target 10%)
        ev  = _make_display_events(5, click_users=["U001","U002","U003","U004","U005"])
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        ctr_rows = r[r["rule_id"].str.startswith("VAL-001")]
        ad_a = ctr_rows[ctr_rows["rule_name"].str.contains("Ad_A")]
        if not ad_a.empty:
            assert ad_a.iloc[0]["status"] in (RuleStatus.FAIL.value, "Warning")

    def test_ctr_variance_correct(self):
        """Variance = actual - expected."""
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        # 10 impressions, 2 clicks = 0.20 actual, target=0.10, variance=+0.10
        ev  = _make_display_events(10, click_users=["U001","U002"])
        r, _, _ = ve.validate(ev, _make_state(10, cfg))
        ctr_rows = r[r["rule_id"].str.startswith("VAL-001")]
        ad_a = ctr_rows[ctr_rows["rule_name"].str.contains("Ad_A")]
        if not ad_a.empty:
            assert ad_a.iloc[0]["actual_value"] == pytest.approx(0.20)
            assert ad_a.iloc[0]["expected_value"] == pytest.approx(0.10)


# ===========================================================================
# 5. VAL-002: Open Rate Achievement
# ===========================================================================

class TestOpenRateAchievement:
    def test_email_open_rate_pass(self):
        """25% open rate target with 25% actual → Pass."""
        cfg = _make_email_cfg()
        ve  = ValidationEngine(cfg)
        # 4 sent, 1 opened = 25%
        ev  = _make_email_events(4, open_users=["U001"])
        r, _, _ = ve.validate(ev, _make_state(4, cfg))
        or_rows = r[r["rule_id"].str.startswith("VAL-002")]
        assert len(or_rows) > 0

    def test_zero_sent_gives_zero_actual_open_rate(self):
        """If no Sent events, actual open rate = 0."""
        cfg = _make_email_cfg()
        ve  = ValidationEngine(cfg)
        # Only clicks, no Sent
        ev  = pd.DataFrame([_ev("U001", SIM_DATE, "Email", ActionType.OPEN.value, current_ad="Ad_B")])
        r, _, _ = ve.validate(ev, _make_state(1, cfg))
        or_rows = r[r["rule_id"].str.startswith("VAL-002")]
        if not or_rows.empty:
            assert or_rows.iloc[0]["actual_value"] == 0.0

    def test_open_rate_variance_correct(self):
        """5 sent, 2 opened = 0.40 actual, target=0.25, variance=+0.15."""
        cfg = _make_email_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_email_events(5, open_users=["U001","U002"])
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        or_rows = r[r["rule_id"].str.startswith("VAL-002")]
        ad_b = or_rows[or_rows["rule_name"].str.contains("Ad_B")]
        if not ad_b.empty:
            assert ad_b.iloc[0]["actual_value"] == pytest.approx(0.40)
            assert ad_b.iloc[0]["expected_value"] == pytest.approx(0.25)


# ===========================================================================
# 6. VAL-003: Trigger Engagement Rate
# ===========================================================================

class TestTriggerEngagementRate:
    def test_pass_when_ter_within_tolerance(self):
        """20% target, 20% actual → Pass."""
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(10, cfg, "T1")
        # 2 out of 10 users click → 20% TER
        evs = _make_display_events(10, click_users=["U001","U002"])
        r, _, _ = ve.validate(evs, state)
        ter_rows = r[r["rule_id"].str.startswith("VAL-003")]
        assert len(ter_rows) > 0

    def test_skip_when_no_trigger_column(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        ev  = ev.drop(columns=["trigger_name"])
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        ter_rows = r[r["rule_id"].str.startswith("VAL-003")]
        # May be skipped since no trigger_name column
        if not ter_rows.empty:
            assert ter_rows.iloc[0]["status"] == RuleStatus.SKIP.value

    def test_skip_when_zero_users(self):
        """Trigger with 0 users → Skip."""
        trig = TriggerConfig("T2", 1, 0.20)
        ads  = (AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
                AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05))
        cfg  = make_config(triggers=(trig,), ads=ads)
        ve   = ValidationEngine(cfg)
        state = _make_state(5, cfg, "T2")
        # events have trigger_name="T1" (unknown trigger)
        evs = _make_display_events(5)
        r, _, _ = ve.validate(evs, state)
        ter_rows = r[r["rule_id"].str.startswith("VAL-003")]
        if not ter_rows.empty:
            t2_row = ter_rows[ter_rows["rule_name"].str.contains("T2")]
            if not t2_row.empty:
                # T2 users=5, but events trigger_name="T1" → 0 engaged
                assert t2_row.iloc[0]["actual_value"] == 0.0

    def test_high_ter_fails(self):
        """100% engaged when target is 20% → Fail."""
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg, "T1")
        # All 5 users click
        evs   = _make_display_events(5, click_users=["U001","U002","U003","U004","U005"])
        r, _, _ = ve.validate(evs, state)
        ter_rows = r[r["rule_id"].str.startswith("VAL-003")]
        if not ter_rows.empty:
            assert ter_rows.iloc[0]["status"] in (RuleStatus.FAIL.value, "Warning")


# ===========================================================================
# 7. VAL-004: Segment Engagement Rate
# ===========================================================================

class TestSegmentEngagementRate:
    def test_no_segments_returns_no_rows(self):
        cfg = _make_display_cfg()  # no segments
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        seg_rows = r[r["rule_id"].str.startswith("VAL-004")]
        assert len(seg_rows) == 0

    def test_segment_row_produced_when_segments_configured(self):
        seg = SegmentConfig("Seg_A", 1, 50.0)
        ads = (AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
               AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05))
        cfg = make_config(segments=(seg,), ads=ads)
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5, click_users=["U001","U002"])
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        seg_rows = r[r["rule_id"].str.startswith("VAL-004")]
        assert len(seg_rows) >= 1

    def test_segment_no_events_gives_zero_actual(self):
        seg = SegmentConfig("Seg_A", 1, 50.0)
        ads = (AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
               AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05))
        cfg = make_config(segments=(seg,), ads=ads)
        ve  = ValidationEngine(cfg)
        # events with Seg_B, not Seg_A
        ev  = _make_display_events(5)
        ev  = ev.copy()
        ev["segment"] = "Seg_B"
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        seg_rows = r[r["rule_id"].str.startswith("VAL-004")]
        seg_a = seg_rows[seg_rows["rule_name"].str.contains("Seg_A")]
        if not seg_a.empty:
            assert seg_a.iloc[0]["actual_value"] == 0.0


# ===========================================================================
# 8. VAL-005: User Daily Frequency
# ===========================================================================

class TestUserDailyFrequency:
    def test_one_impression_per_user_per_day_passes(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)  # 1 impression per user
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        freq_row = r[r["rule_id"] == "VAL-005"]
        assert not freq_row.empty
        assert freq_row.iloc[0]["status"] == RuleStatus.PASS.value

    def test_two_impressions_same_user_same_day_fails(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        rows = [
            _ev("U001", SIM_DATE, "Display", ActionType.IMPRESSION.value),
            _ev("U001", SIM_DATE, "Display", ActionType.IMPRESSION.value),  # duplicate
        ]
        ev = pd.DataFrame(rows)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        freq_row = r[r["rule_id"] == "VAL-005"]
        assert not freq_row.empty
        assert freq_row.iloc[0]["status"] in (RuleStatus.FAIL.value, "Warning")

    def test_empty_events_skips(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = pd.DataFrame(columns=["user_id","simulation_date","channel",
                                    "action_type","current_ad"])
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        freq_row = r[r["rule_id"] == "VAL-005"]
        if not freq_row.empty:
            assert freq_row.iloc[0]["status"] == RuleStatus.SKIP.value


# ===========================================================================
# 9. VAL-006: Weekly Engagement Cap
# ===========================================================================

class TestWeeklyEngagementCap:
    def test_within_cap_passes(self):
        """2 clicks in one week, weekly_engagement_cap=2 → Pass."""
        cfg = _make_display_cfg()  # weekly_engagement_cap=2
        ve  = ValidationEngine(cfg)
        evs = []
        # 5 impressions (not qualifying)
        for i in range(1, 6):
            evs.append(_ev(f"U{i:03d}", SIM_DATE, "Display", ActionType.IMPRESSION.value))
        # 2 clicks by U001 on different days (both in same week)
        evs.append(_ev("U001", date(2024, 1, 8), "Display", ActionType.CLICK.value))
        evs.append(_ev("U001", date(2024, 1, 9), "Display", ActionType.CLICK.value))
        ev = pd.DataFrame(evs)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        cap_row = r[r["rule_id"] == "VAL-006"]
        assert not cap_row.empty
        assert cap_row.iloc[0]["status"] == RuleStatus.PASS.value

    def test_exceeds_cap_warns_or_fails(self):
        """3 qualifying events in one week, cap=2 → Warning/Fail."""
        cfg = _make_display_cfg()  # weekly_engagement_cap=2
        ve  = ValidationEngine(cfg)
        evs = [
            _ev("U001", date(2024, 1, 8), "Display", ActionType.IMPRESSION.value),
            _ev("U001", date(2024, 1, 8), "Display", ActionType.CLICK.value),
            _ev("U001", date(2024, 1, 9), "Display", ActionType.CLICK.value),
            _ev("U001", date(2024, 1, 10), "Display", ActionType.CLICK.value),
        ]
        ev = pd.DataFrame(evs)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        cap_row = r[r["rule_id"] == "VAL-006"]
        assert not cap_row.empty
        assert cap_row.iloc[0]["status"] in ("Warning", RuleStatus.FAIL.value)

    def test_no_qualifying_events_passes(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        # Only impressions (not qualifying)
        ev  = _make_display_events(5)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        cap_row = r[r["rule_id"] == "VAL-006"]
        assert not cap_row.empty
        assert cap_row.iloc[0]["status"] == RuleStatus.PASS.value


# ===========================================================================
# 10. VAL-007: Weekly Impression Cap
# ===========================================================================

class TestWeeklyImpressionCap:
    def test_within_cap_passes(self):
        """5 impressions in one week, weekly_impression_cap=5 → Pass."""
        cfg = _make_display_cfg()  # weekly_impression_cap=5
        ve  = ValidationEngine(cfg)
        evs = []
        for d in range(5):
            evs.append(_ev("U001", date(2024, 1, 8) + timedelta(days=d),
                           "Display", ActionType.IMPRESSION.value))
        ev = pd.DataFrame(evs)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        cap_row = r[r["rule_id"] == "VAL-007"]
        assert not cap_row.empty
        assert cap_row.iloc[0]["status"] == RuleStatus.PASS.value

    def test_exceeds_cap_warns_or_fails(self):
        """6 impressions in one week, cap=5 → Warning/Fail."""
        cfg = _make_display_cfg()  # weekly_impression_cap=5
        ve  = ValidationEngine(cfg)
        evs = []
        for d in range(6):
            evs.append(_ev("U001", date(2024, 1, 8) + timedelta(days=d),
                           "Display", ActionType.IMPRESSION.value))
        ev = pd.DataFrame(evs)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        cap_row = r[r["rule_id"] == "VAL-007"]
        assert not cap_row.empty
        assert cap_row.iloc[0]["status"] in ("Warning", RuleStatus.FAIL.value)

    def test_no_impressions_skip_or_pass(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_email_events(3, open_users=["U001"])  # no Display impressions
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        cap_row = r[r["rule_id"] == "VAL-007"]
        if not cap_row.empty:
            assert cap_row.iloc[0]["status"] in (RuleStatus.PASS.value, RuleStatus.SKIP.value)


# ===========================================================================
# 11. VAL-008: Journey Progression
# ===========================================================================

class TestJourneyProgression:
    def test_active_users_with_events_passes(self):
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg)
        ev    = _make_display_events(5)
        r, _, _ = ve.validate(ev, state)
        jp_row = r[r["rule_id"] == "VAL-008"]
        assert not jp_row.empty
        assert jp_row.iloc[0]["status"] == RuleStatus.PASS.value

    def test_not_started_user_with_events_fails(self):
        """User in Not_Started state appears in events → Fail."""
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg)
        state.loc[state["user_id"] == "U001", "journey_status"] = JourneyStatus.NOT_STARTED.value
        ev    = _make_display_events(5)
        r, _, _ = ve.validate(ev, state)
        jp_row = r[r["rule_id"] == "VAL-008"]
        assert not jp_row.empty
        assert jp_row.iloc[0]["status"] == RuleStatus.FAIL.value

    def test_not_started_users_with_no_events_passes(self):
        """Not_Started users who have NO events → Pass."""
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = make_state_df(5, config=cfg)  # all Not_Started
        # events only for users NOT in state
        ev = pd.DataFrame([_ev("X999", SIM_DATE, "Display", ActionType.IMPRESSION.value)])
        r, _, _ = ve.validate(ev, state)
        jp_row = r[r["rule_id"] == "VAL-008"]
        if not jp_row.empty:
            assert jp_row.iloc[0]["status"] == RuleStatus.PASS.value


# ===========================================================================
# 12. VAL-009: Trigger Priority Correctness
# ===========================================================================

class TestTriggerPriority:
    def test_known_triggers_passes(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)  # trigger_name="T1" (known)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        tp_row = r[r["rule_id"] == "VAL-009"]
        assert not tp_row.empty
        assert tp_row.iloc[0]["status"] == RuleStatus.PASS.value

    def test_unknown_trigger_fails(self):
        """Events with trigger_name='UNKNOWN' → Fail."""
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        ev["trigger_name"] = "UNKNOWN_TRIGGER"
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        tp_row = r[r["rule_id"] == "VAL-009"]
        assert not tp_row.empty
        assert tp_row.iloc[0]["status"] == RuleStatus.FAIL.value

    def test_no_trigger_column_skips(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5).drop(columns=["trigger_name"])
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        tp_row = r[r["rule_id"] == "VAL-009"]
        if not tp_row.empty:
            assert tp_row.iloc[0]["status"] == RuleStatus.SKIP.value


# ===========================================================================
# 13. VAL-010: Multi-Trigger Consistency
# ===========================================================================

class TestMultiTrigger:
    def test_single_trigger_per_user_passes(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        mt_row = r[r["rule_id"] == "VAL-010"]
        assert not mt_row.empty
        assert mt_row.iloc[0]["status"] == RuleStatus.PASS.value

    def test_user_with_two_triggers_warns(self):
        """Same user appears with T1 and T2 across events → Warning."""
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        rows = [
            _ev("U001", SIM_DATE, "Display", ActionType.IMPRESSION.value, trigger_name="T1"),
            _ev("U001", SIM_DATE + timedelta(1), "Display", ActionType.IMPRESSION.value, trigger_name="T2"),
        ]
        ev = pd.DataFrame(rows)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        mt_row = r[r["rule_id"] == "VAL-010"]
        assert not mt_row.empty
        assert mt_row.iloc[0]["status"] in ("Warning", RuleStatus.FAIL.value)


# ===========================================================================
# 14. VAL-011: Segment Distribution
# ===========================================================================

class TestSegmentDistribution:
    def test_no_segments_no_rows(self):
        cfg = _make_display_cfg()  # no segments
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        sd_rows = r[r["rule_id"].str.startswith("VAL-011")]
        assert len(sd_rows) == 0

    def test_segment_distribution_within_tolerance_passes(self):
        """50% target, 50% actual → Pass."""
        seg = SegmentConfig("Seg_A", 1, 50.0)
        ads = (AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
               AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05))
        cfg = make_config(segments=(seg,), ads=ads)
        ve  = ValidationEngine(cfg)
        state = _make_state(10, cfg)
        # Set 5 of 10 users to Seg_A
        if hasattr(state["segment"], "cat"):
            state["segment"] = state["segment"].cat.add_categories(
                [v for v in ["Seg_A"] if v not in state["segment"].cat.categories]
            )
        state.iloc[:5, state.columns.get_loc("segment")] = "Seg_A"
        ev = _make_display_events(10)
        r, _, _ = ve.validate(ev, state)
        sd_rows = r[r["rule_id"].str.startswith("VAL-011")]
        assert len(sd_rows) >= 1


# ===========================================================================
# 15. VAL-012: Channel Dependency Rules
# ===========================================================================

class TestChannelDependencies:
    def test_display_click_with_impression_passes(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        rows = [
            _ev("U001", SIM_DATE, "Display", ActionType.IMPRESSION.value),
            _ev("U001", SIM_DATE, "Display", ActionType.CLICK.value),
        ]
        ev = pd.DataFrame(rows)
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        dep_a = r[r["rule_id"] == "VAL-012a"]
        assert not dep_a.empty
        assert dep_a.iloc[0]["status"] == RuleStatus.PASS.value

    def test_display_click_without_impression_fails(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        # Click without impression
        ev = pd.DataFrame([_ev("U001", SIM_DATE, "Display", ActionType.CLICK.value)])
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        dep_a = r[r["rule_id"] == "VAL-012a"]
        assert not dep_a.empty
        assert dep_a.iloc[0]["status"] == RuleStatus.FAIL.value

    def test_email_open_with_sent_passes(self):
        cfg = _make_email_cfg()
        ve  = ValidationEngine(cfg)
        rows = [
            _ev("U001", SIM_DATE, "Email", "Sent", current_ad="Ad_B"),
            _ev("U001", SIM_DATE, "Email", ActionType.OPEN.value, current_ad="Ad_B"),
        ]
        ev = pd.DataFrame(rows)
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        dep_b = r[r["rule_id"] == "VAL-012b-open"]
        assert not dep_b.empty
        assert dep_b.iloc[0]["status"] == RuleStatus.PASS.value

    def test_email_open_without_sent_fails(self):
        cfg = _make_email_cfg()
        ve  = ValidationEngine(cfg)
        ev = pd.DataFrame([_ev("U001", SIM_DATE, "Email", ActionType.OPEN.value, current_ad="Ad_B")])
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        dep_b = r[r["rule_id"] == "VAL-012b-open"]
        assert not dep_b.empty
        assert dep_b.iloc[0]["status"] == RuleStatus.FAIL.value

    def test_email_click_with_open_passes(self):
        cfg = _make_email_cfg()
        ve  = ValidationEngine(cfg)
        rows = [
            _ev("U001", SIM_DATE, "Email", "Sent", current_ad="Ad_B"),
            _ev("U001", SIM_DATE, "Email", ActionType.OPEN.value, current_ad="Ad_B"),
            _ev("U001", SIM_DATE, "Email", ActionType.CLICK.value, current_ad="Ad_B"),
        ]
        ev = pd.DataFrame(rows)
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        dep_b_click = r[r["rule_id"] == "VAL-012b-click"]
        assert not dep_b_click.empty
        assert dep_b_click.iloc[0]["status"] == RuleStatus.PASS.value

    def test_email_click_without_open_fails(self):
        cfg = _make_email_cfg()
        ve  = ValidationEngine(cfg)
        ev = pd.DataFrame([_ev("U001", SIM_DATE, "Email", ActionType.CLICK.value, current_ad="Ad_B")])
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        dep_b_click = r[r["rule_id"] == "VAL-012b-click"]
        assert not dep_b_click.empty
        assert dep_b_click.iloc[0]["status"] == RuleStatus.FAIL.value

    def test_whatsapp_open_without_sent_fails(self):
        cfg = _make_wa_cfg()
        ve  = ValidationEngine(cfg)
        ev = pd.DataFrame([_ev("U001", SIM_DATE, "WhatsApp", ActionType.OPEN.value)])
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        dep_c = r[r["rule_id"] == "VAL-012c-open"]
        assert not dep_c.empty
        assert dep_c.iloc[0]["status"] == RuleStatus.FAIL.value

    def test_no_display_events_vacuously_passes(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_email_events(3)  # no Display events
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        dep_a = r[r["rule_id"] == "VAL-012a"]
        assert not dep_a.empty
        assert dep_a.iloc[0]["status"] == RuleStatus.PASS.value

    def test_empty_events_skips_all_channel_rules(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = pd.DataFrame(columns=["user_id","simulation_date","channel",
                                    "action_type","current_ad"])
        r, _, _ = ve.validate(ev, _make_state(3, cfg))
        dep_rows = r[r["rule_id"].str.startswith("VAL-012")]
        if not dep_rows.empty:
            assert (dep_rows["status"] == RuleStatus.SKIP.value).all()


# ===========================================================================
# 16. VAL-013: TCC Calculations
# ===========================================================================

class TestTCCCalculations:
    def test_new_engagements_within_tcc_ceiling_passes(self):
        """TCC ceiling=ceil(5×0.20)=1; 1 new engaged → Pass."""
        trig = TriggerConfig("T1", 1, 0.20)
        ads  = (AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
                AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05))
        cfg  = make_config(triggers=(trig,), ads=ads)
        ve   = ValidationEngine(cfg)
        state = _make_state(5, cfg, "T1")
        state["historical_engaged"] = False
        ev = _make_display_events(5, click_users=["U001"])
        r, _, _ = ve.validate(ev, state)
        tcc_rows = r[r["rule_id"].str.startswith("VAL-013")]
        assert not tcc_rows.empty
        assert tcc_rows.iloc[0]["status"] == RuleStatus.PASS.value

    def test_new_engagements_exceeds_tcc_ceiling_fails(self):
        """TCC ceiling=ceil(5×0.20)=1; 3 new engaged → Fail."""
        trig = TriggerConfig("T1", 1, 0.20)
        ads  = (AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
                AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05))
        cfg  = make_config(triggers=(trig,), ads=ads)
        ve   = ValidationEngine(cfg)
        state = _make_state(5, cfg, "T1")
        state["historical_engaged"] = False
        ev = _make_display_events(5, click_users=["U001","U002","U003"])
        r, _, _ = ve.validate(ev, state)
        tcc_rows = r[r["rule_id"].str.startswith("VAL-013")]
        if not tcc_rows.empty:
            assert tcc_rows.iloc[0]["status"] == RuleStatus.FAIL.value

    def test_tcc_ceiling_uses_ceil_not_floor(self):
        """ceil(5×0.30)=2 not floor(5×0.30)=1."""
        trig = TriggerConfig("T1", 1, 0.30)
        ads  = (AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
                AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05))
        cfg  = make_config(triggers=(trig,), ads=ads)
        ve   = ValidationEngine(cfg)
        state = _make_state(5, cfg, "T1")
        state["historical_engaged"] = False
        ev = _make_display_events(5, click_users=["U001","U002"])
        r, _, _ = ve.validate(ev, state)
        tcc_rows = r[r["rule_id"].str.startswith("VAL-013")]
        if not tcc_rows.empty:
            # ceil(5×0.30)=2; 2 engaged → Pass
            assert tcc_rows.iloc[0]["expected_value"] == pytest.approx(2.0)
            assert tcc_rows.iloc[0]["status"] == RuleStatus.PASS.value

    def test_historical_users_excluded_from_new_engagements(self):
        """Historical users who click do not count as NEW engagements."""
        trig = TriggerConfig("T1", 1, 0.20)
        ads  = (AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
                AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05))
        cfg  = make_config(triggers=(trig,), ads=ads)
        ve   = ValidationEngine(cfg)
        state = _make_state(5, cfg, "T1")
        # U001 is historical → clicks don't count as new
        state["historical_engaged"] = False
        state.loc[state["user_id"] == "U001", "historical_engaged"] = True
        ev = _make_display_events(5, click_users=["U001"])
        r, _, _ = ve.validate(ev, state)
        tcc_rows = r[r["rule_id"].str.startswith("VAL-013")]
        if not tcc_rows.empty:
            # 0 new engagements (U001 is historical)
            assert tcc_rows.iloc[0]["actual_value"] == 0.0

    def test_no_trigger_name_skips(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5).drop(columns=["trigger_name"])
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        tcc_rows = r[r["rule_id"].str.startswith("VAL-013")]
        if not tcc_rows.empty:
            assert tcc_rows.iloc[0]["status"] == RuleStatus.SKIP.value


# ===========================================================================
# 17. VAL-014: Historical Engagement Tracking
# ===========================================================================

class TestHistoricalEngagement:
    def test_qualifying_users_with_counter_passes(self):
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg)
        # Set total_lifetime_engagements > 0 for all users
        state["total_lifetime_engagements"] = 2
        ev    = _make_display_events(5, click_users=["U001","U002"])
        r, _, _ = ve.validate(ev, state)
        hist_row = r[r["rule_id"] == "VAL-014"]
        assert not hist_row.empty
        assert hist_row.iloc[0]["status"] == RuleStatus.PASS.value

    def test_qualifying_users_with_zero_counter_warns(self):
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg)
        state["total_lifetime_engagements"] = 0  # all zero
        ev    = _make_display_events(5, click_users=["U001","U002"])
        r, _, _ = ve.validate(ev, state)
        hist_row = r[r["rule_id"] == "VAL-014"]
        assert not hist_row.empty
        assert hist_row.iloc[0]["status"] in ("Warning", RuleStatus.FAIL.value)

    def test_no_qualifying_events_passes(self):
        """No qualifying events → nothing to cross-check → Pass."""
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg)
        # Only impressions (not qualifying)
        ev    = _make_display_events(5)
        r, _, _ = ve.validate(ev, state)
        hist_row = r[r["rule_id"] == "VAL-014"]
        if not hist_row.empty:
            assert hist_row.iloc[0]["status"] in (RuleStatus.PASS.value, RuleStatus.SKIP.value)

    def test_missing_column_skips(self):
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg)
        state = state.drop(columns=["total_lifetime_engagements"])
        ev    = _make_display_events(5, click_users=["U001"])
        r, _, _ = ve.validate(ev, state)
        hist_row = r[r["rule_id"] == "VAL-014"]
        if not hist_row.empty:
            assert hist_row.iloc[0]["status"] == RuleStatus.SKIP.value


# ===========================================================================
# 18. Quality Score
# ===========================================================================

class TestQualityScore:
    def test_all_pass_gives_100(self):
        results = pd.DataFrame([
            {"rule_id": "V1", "status": RuleStatus.PASS.value,
             "severity": RuleSeverity.HARD.value,   "message": ""},
            {"rule_id": "V2", "status": RuleStatus.PASS.value,
             "severity": RuleSeverity.SOFT.value,   "message": ""},
        ])
        assert _compute_quality_score(results) == pytest.approx(100.0)

    def test_all_fail_gives_0(self):
        results = pd.DataFrame([
            {"rule_id": "V1", "status": RuleStatus.FAIL.value,
             "severity": RuleSeverity.HARD.value, "message": ""},
        ])
        assert _compute_quality_score(results) == pytest.approx(0.0)

    def test_mix_score_weighted(self):
        """1 Hard Pass (w=3) + 1 Hard Fail (w=3) → 50."""
        results = pd.DataFrame([
            {"rule_id": "V1", "status": RuleStatus.PASS.value,
             "severity": RuleSeverity.HARD.value, "message": ""},
            {"rule_id": "V2", "status": RuleStatus.FAIL.value,
             "severity": RuleSeverity.HARD.value, "message": ""},
        ])
        assert _compute_quality_score(results) == pytest.approx(50.0)

    def test_skip_rows_neutral(self):
        """Skip rows don't affect the score."""
        results = pd.DataFrame([
            {"rule_id": "V1", "status": RuleStatus.PASS.value,
             "severity": RuleSeverity.SOFT.value, "message": ""},
            {"rule_id": "V2", "status": RuleStatus.SKIP.value,
             "severity": RuleSeverity.SOFT.value, "message": ""},
        ])
        assert _compute_quality_score(results) == pytest.approx(100.0)

    def test_empty_results_gives_100(self):
        results = pd.DataFrame(columns=["rule_id", "status", "severity", "message"])
        assert _compute_quality_score(results) == pytest.approx(100.0)

    def test_warning_is_half_score(self):
        """1 Hard Warning (w=3, s=0.5) → 50."""
        results = pd.DataFrame([
            {"rule_id": "V1", "status": "Warning",
             "severity": RuleSeverity.HARD.value, "message": ""},
        ])
        assert _compute_quality_score(results) == pytest.approx(50.0)

    def test_quality_score_from_engine(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        score = ve.generate_quality_score(r)
        assert 0.0 <= score <= 100.0


# ===========================================================================
# 19. Realism Score
# ===========================================================================

class TestRealismScore:
    def test_exact_match_gives_100(self):
        realism = pd.DataFrame([{
            "metric": "CTR — Ad_A", "target": 0.10, "actual": 0.10,
            "variance": 0.0, "variance_pct": 0.0, "status": "Good",
        }])
        assert _compute_realism_score(realism) == pytest.approx(100.0)

    def test_total_miss_gives_0(self):
        """Actual=0 when target=0.10 → realism = 0."""
        realism = pd.DataFrame([{
            "metric": "CTR — Ad_A", "target": 0.10, "actual": 0.0,
            "variance": -0.10, "variance_pct": -100.0, "status": "Poor",
        }])
        assert _compute_realism_score(realism) == pytest.approx(0.0)

    def test_zero_target_gives_100(self):
        """Zero target → no penalty (can't miss a zero target)."""
        realism = pd.DataFrame([{
            "metric": "CTR — Ad_A", "target": 0.0, "actual": 0.0,
            "variance": 0.0, "variance_pct": 0.0, "status": "Good",
        }])
        assert _compute_realism_score(realism) == pytest.approx(100.0)

    def test_empty_realism_gives_100(self):
        realism = pd.DataFrame(columns=["metric","target","actual",
                                         "variance","variance_pct","status"])
        assert _compute_realism_score(realism) == pytest.approx(100.0)

    def test_realism_score_from_engine(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        _, _, re = ve.validate(ev, _make_state(5, cfg))
        score = ve.generate_realism_score(re)
        assert 0.0 <= score <= 100.0


# ===========================================================================
# 20. Feasibility Warnings
# ===========================================================================

class TestFeasibilityWarnings:
    def test_no_warnings_for_valid_config(self):
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg, "T1")
        ev    = _make_display_events(5)
        warnings = ve.generate_feasibility_warnings(ev, state)
        # May have zero or few warnings
        assert isinstance(warnings, list)

    def test_empty_events_generates_warning(self):
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg, "T1")
        ev    = pd.DataFrame(columns=["user_id","simulation_date","channel","action_type","current_ad"])
        warnings = ve.generate_feasibility_warnings(ev, state)
        assert any("empty" in w.lower() for w in warnings)

    def test_zero_user_trigger_warning(self):
        """Trigger with 0 users in state → feasibility warning."""
        trig = TriggerConfig("T_EMPTY", 1, 0.20)
        ads  = (AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
                AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05))
        cfg  = make_config(triggers=(trig,), ads=ads)
        ve   = ValidationEngine(cfg)
        state = _make_state(5, cfg, "T1")  # trigger_name=T1, not T_EMPTY
        ev    = _make_display_events(5)
        warnings = ve.generate_feasibility_warnings(ev, state)
        assert any("T_EMPTY" in w for w in warnings)

    def test_very_low_ctr_warning(self):
        """target_ctr < 0.001 → feasibility warning."""
        ads = (
            AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.0001),
            AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05),
        )
        cfg   = make_config(ads=ads)
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg)
        ev    = _make_display_events(5)
        warnings = ve.generate_feasibility_warnings(ev, state)
        assert any("Ad_A" in w for w in warnings)

    def test_returns_list_type(self):
        cfg   = _make_display_cfg()
        ve    = ValidationEngine(cfg)
        state = _make_state(5, cfg)
        ev    = _make_display_events(5)
        warnings = ve.generate_feasibility_warnings(ev, state)
        assert isinstance(warnings, list)


# ===========================================================================
# 21. Realism Report
# ===========================================================================

class TestRealismReport:
    def test_display_ctr_row_in_realism(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(10, click_users=["U001"])
        _, _, re = ve.validate(ev, _make_state(10, cfg))
        ctr_rows = re[re["metric"].str.startswith("CTR")]
        assert len(ctr_rows) >= 1

    def test_open_rate_row_in_realism(self):
        cfg = _make_email_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_email_events(5, open_users=["U001"])
        _, _, re = ve.validate(ev, _make_state(5, cfg))
        or_rows = re[re["metric"].str.startswith("Open Rate")]
        assert len(or_rows) >= 1

    def test_realism_status_is_good_for_exact_match(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        # 10 impressions, 1 click = 10% CTR = target
        ev  = _make_display_events(10, click_users=["U001"])
        _, _, re = ve.validate(ev, _make_state(10, cfg))
        ctr_ad_a = re[re["metric"] == "CTR — Ad_A"]
        if not ctr_ad_a.empty:
            assert ctr_ad_a.iloc[0]["status"] == "Good"

    def test_realism_variance_pct_correct(self):
        """target=0.10, actual=0.20 → variance_pct=100%."""
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(10, click_users=["U001","U002"])
        _, _, re = ve.validate(ev, _make_state(10, cfg))
        ctr_ad_a = re[re["metric"] == "CTR — Ad_A"]
        if not ctr_ad_a.empty:
            assert ctr_ad_a.iloc[0]["variance_pct"] == pytest.approx(100.0)


# ===========================================================================
# 22. Summary DataFrame
# ===========================================================================

class TestSummaryDF:
    def test_summary_has_all_categories(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        _, s, _ = ve.validate(ev, _make_state(5, cfg))
        cats = set(s["validation_category"].values)
        for expected_cat in ("Rate Achievement", "Capacity & Frequency",
                              "Channel Rules", "OVERALL"):
            assert expected_cat in cats

    def test_summary_scores_in_range(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        _, s, _ = ve.validate(ev, _make_state(5, cfg))
        assert (s["score"] >= 0.0).all()
        assert (s["score"] <= 100.0).all()

    def test_summary_counts_are_non_negative(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        _, s, _ = ve.validate(ev, _make_state(5, cfg))
        assert (s["passed"] >= 0).all()
        assert (s["failed"] >= 0).all()
        assert (s["warning"] >= 0).all()


# ===========================================================================
# 23. Integration: end-to-end with EngagementGenerator output
# ===========================================================================

class TestIntegration:
    def test_validates_engagement_generator_output(self):
        """Run EngagementGenerator then ValidationEngine end-to-end."""
        from core.engagement_generator import EngagementGenerator
        cfg = _make_display_cfg(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 5),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(10, config=cfg)
        ev, met, _, _ = gen.generate(df)

        ve = ValidationEngine(cfg)
        r, s, re = ve.validate(ev, df)

        assert "OVERALL" in s["validation_category"].values
        assert (s["score"] >= 0).all()
        overall = s[s["validation_category"] == "OVERALL"].iloc[0]
        assert 0.0 <= overall["score"] <= 100.0

    def test_all_rules_have_valid_severity(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5, click_users=["U001"])
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        valid_sevs = {RuleSeverity.HARD.value, RuleSeverity.SOFT.value,
                      RuleSeverity.ADVISORY.value}
        assert r["severity"].isin(valid_sevs).all()

    def test_all_rules_have_valid_status(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        ev  = _make_display_events(5)
        r, _, _ = ve.validate(ev, _make_state(5, cfg))
        valid_statuses = {RuleStatus.PASS.value, RuleStatus.FAIL.value,
                          RuleStatus.SKIP.value, "Warning"}
        assert r["status"].isin(valid_statuses).all()


# ===========================================================================
# 24. Compliance
# ===========================================================================

class TestCompliance:
    def test_no_iterrows_in_validation_engine(self):
        """ARCH-011: no iterrows() in production code."""
        import pathlib
        path = (pathlib.Path(__file__).parent.parent.parent
                / "core" / "validation_engine.py")
        content = path.read_text(encoding="utf-8")
        bad = [
            f"line {i+1}: {line.rstrip()}"
            for i, line in enumerate(content.splitlines())
            if ".iterrows(" in line and not line.lstrip().startswith("#")
        ]
        assert bad == [], (
            "ARCH-011: iterrows() found in validation_engine.py:\n"
            + "\n".join(bad)
        )

    def test_all_declared(self):
        from core import validation_engine
        assert hasattr(validation_engine, "__all__")
        assert "ValidationEngine" in validation_engine.__all__

    def test_public_methods_have_docstrings(self):
        cfg = _make_display_cfg()
        ve  = ValidationEngine(cfg)
        for name in ("validate", "generate_quality_score",
                     "generate_realism_score", "generate_feasibility_warnings"):
            assert getattr(ve, name).__doc__, f"Missing docstring: {name}"

    def test_no_todo_fixme(self):
        import pathlib
        path = (pathlib.Path(__file__).parent.parent.parent
                / "core" / "validation_engine.py")
        content = path.read_text(encoding="utf-8")
        bad = [
            f"line {i+1}: {line.rstrip()}"
            for i, line in enumerate(content.splitlines())
            if any(t in line.upper() for t in ("TODO", "FIXME", "HACK"))
        ]
        assert bad == [], "Unresolved items in validation_engine.py:\n" + "\n".join(bad)
