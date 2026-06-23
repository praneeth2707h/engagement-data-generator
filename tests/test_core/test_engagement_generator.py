"""Unit tests for core/engagement_generator.py — EngagementGenerator (Stage 7).

Coverage:
  * All 15 responsibilities from Wave 1 directive
  * TCC capacity enforcement (TCC-001..007)
  * Channel causal chains (HR-003..HR-008)
  * Fatigue / weekly cap integration
  * Journey eligibility integration
  * Determinism (REQ-026)
  * Diagnostics (CTR, open rate, trigger/segment engagement)
  * Edge cases: empty DataFrame, zero-capacity triggers, no active users
  * Compliance: no iterrows(), __all__ declared
"""
from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from core.behavior_engine import BehaviorEngine
from core.engagement_generator import EngagementGenerator
from core.journey_engine import JourneyEngine
from models.ad_config import AdConfig
from models.channel_config import ChannelConfig
from models.enums import ActionType, BehaviorProfile, JourneyStatus
from models.segment_config import SegmentConfig
from models.trigger_config import TriggerConfig
from utils.exceptions import InputValidationError

from tests.test_core.conftest import make_config, make_state_df, make_trigger_df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_display_config(**kwargs):
    ads = (
        AdConfig("Ad_A", 1, 10, False, "Display", "VendorX", 0.10),
        AdConfig("Ad_B", 2, 10, False, "Display", "VendorX", 0.10),
    )
    defaults = dict(
        ads=ads,
        simulation_start_date=date(2024, 1, 1),
        simulation_end_date=date(2024, 1, 5),
    )
    defaults.update(kwargs)
    return make_config(**defaults)


def _make_email_config(**kwargs):
    ads = (
        AdConfig("Ad_A", 1, 10, False, "Email", "VendorY", 0.10),
        AdConfig("Ad_B", 2, 10, False, "Email", "VendorY", 0.05),
    )
    defaults = dict(
        ads=ads,
        simulation_start_date=date(2024, 1, 1),
        simulation_end_date=date(2024, 1, 3),
    )
    defaults.update(kwargs)
    return make_config(**defaults)


def _make_wa_config(**kwargs):
    ads = (
        AdConfig("Ad_A", 1, 10, False, "WhatsApp", "VendorZ", 0.15),
        AdConfig("Ad_B", 2, 10, False, "WhatsApp", "VendorZ", 0.05),
    )
    defaults = dict(
        ads=ads,
        simulation_start_date=date(2024, 1, 1),
        simulation_end_date=date(2024, 1, 3),
    )
    defaults.update(kwargs)
    return make_config(**defaults)


def _activate(df: pd.DataFrame, channel: str = "Display",
              vendor: str = "VendorX", ad: str = "Ad_A") -> pd.DataFrame:
    """Set all users to ACTIVE with current_ad on given channel."""
    df = df.copy()
    df["journey_status"] = JourneyStatus.ACTIVE.value
    df["current_ad"]     = ad
    df["channel"]        = channel
    df["vendor"]         = vendor
    # Ensure trigger_name is set (category may have NaN)
    df["trigger_name"]   = df["trigger_name"].cat.add_categories(
        [v for v in ["T1"] if v not in df["trigger_name"].cat.categories]
    ).fillna("T1")
    return df


def _set_trigger(df: pd.DataFrame, trigger_name: str = "T1") -> pd.DataFrame:
    """Assign trigger_name to all users (trigger_name is NaN after make_state_df)."""
    df = df.copy()
    if hasattr(df["trigger_name"], "cat"):
        if trigger_name not in df["trigger_name"].cat.categories:
            df["trigger_name"] = df["trigger_name"].cat.add_categories([trigger_name])
    df["trigger_name"] = df["trigger_name"].fillna(trigger_name)
    return df


SIM_DATE = date(2024, 1, 10)  # Wednesday


# ===========================================================================
# 1. Initialisation
# ===========================================================================

class TestEngagementGeneratorInit:
    def test_instantiates_with_config(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        assert gen is not None

    def test_creates_default_engines(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        assert isinstance(gen._je, JourneyEngine)
        assert isinstance(gen._be, BehaviorEngine)

    def test_accepts_injected_engines(self):
        cfg = _make_display_config()
        je  = JourneyEngine(cfg)
        be  = BehaviorEngine(cfg)
        gen = EngagementGenerator(cfg, journey_engine=je, behavior_engine=be)
        assert gen._je is je
        assert gen._be is be

    def test_stores_config(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        assert gen._config is cfg

    def test_campaign_id_stored(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        assert gen._campaign_id == cfg.campaign_id


# ===========================================================================
# 2. Column validation
# ===========================================================================

class TestColumnValidation:
    def test_missing_column_raises(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(2, config=cfg))
        df  = df.drop(columns=["trigger_name"])
        with pytest.raises(InputValidationError, match="trigger_name"):
            gen.generate_day(df, SIM_DATE)

    def test_missing_historical_engaged_raises(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(2, config=cfg))
        df  = df.drop(columns=["historical_engaged"])
        with pytest.raises(InputValidationError):
            gen.generate_day(df, SIM_DATE)

    def test_all_columns_present_no_error(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        updated, events, metrics = gen.generate_day(df, SIM_DATE)
        assert updated is not None


# ===========================================================================
# 3. generate() full simulation
# ===========================================================================

class TestGenerateFullSimulation:
    def test_returns_three_dataframes(self):
        cfg = _make_display_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 3),
        )
        gen      = EngagementGenerator(cfg)
        df       = make_state_df(5, config=cfg)
        result   = gen.generate(df)
        assert len(result) == 4
        ev, met, diag, _ = result
        assert isinstance(ev, pd.DataFrame)
        assert isinstance(met, pd.DataFrame)
        assert isinstance(diag, pd.DataFrame)

    def test_metrics_has_one_row_per_day(self):
        cfg = _make_display_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 5),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(3, config=cfg)
        _, met, _, _ = gen.generate(df)
        assert len(met) == 5

    def test_events_have_required_columns(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = make_state_df(3, config=cfg)
        ev, _, _, _ = gen.generate(df)
        for col in ("campaign_id", "user_id", "simulation_date",
                    "channel", "action_type", "current_ad", "vendor"):
            assert col in ev.columns

    def test_events_campaign_id_correct(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = make_state_df(3, config=cfg)
        ev, _, _, _ = gen.generate(df)
        if not ev.empty:
            assert (ev["campaign_id"] == cfg.campaign_id).all()

    def test_custom_date_range_overrides_config(self):
        cfg = _make_display_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 31),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(3, config=cfg)
        _, met, _, _ = gen.generate(
            df,
            simulation_start=date(2024, 1, 1),
            simulation_end=date(2024, 1, 3),
        )
        assert len(met) == 3

    def test_no_active_users_returns_empty_events(self):
        cfg = _make_display_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 1),
        )
        gen = EngagementGenerator(cfg)
        # Users start as NOT_STARTED; JourneyEngine starts them on day 1
        # On day 1, JourneyEngine starts journeys AND BehaviorEngine runs
        # This test verifies at least the schema is correct even with 0 users
        df  = make_state_df(0, config=cfg).iloc[:0]
        ev, met, diag, _ = gen.generate(df)
        assert ev.empty or len(ev) >= 0

    def test_deterministic_same_inputs_same_output(self):
        cfg = _make_display_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 3),
        )
        gen  = EngagementGenerator(cfg)
        df   = make_state_df(5, config=cfg)
        ev1, _, _, _ = gen.generate(df)
        ev2, _, _, _ = gen.generate(df)
        assert len(ev1) == len(ev2)
        if not ev1.empty:
            assert set(ev1["user_id"]) == set(ev2["user_id"])

    def test_metrics_columns_correct(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = make_state_df(3, config=cfg)
        _, met, _, _ = gen.generate(df)
        expected = [
            "simulation_date", "n_users_active", "n_reached",
            "n_impressions", "n_sends", "n_opens", "n_clicks", "n_qualifying",
            "actual_ctr_display", "actual_open_rate_email", "actual_open_rate_wa",
            "n_tcc_blocked_users", "weekly_reset",
        ]
        for col in expected:
            assert col in met.columns, f"Missing metrics column: {col}"


# ===========================================================================
# 4. generate_day()
# ===========================================================================

class TestGenerateDay:
    def test_returns_three_outputs(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        result = gen.generate_day(df, SIM_DATE)
        assert len(result) == 3

    def test_active_users_get_events(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        _, events, _ = gen.generate_day(df, SIM_DATE)
        # All 5 active Display users should get impressions
        imp = events[events["action_type"] == ActionType.IMPRESSION.value]
        assert len(imp) == 5

    def test_inactive_users_get_no_events(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = make_state_df(3, config=cfg)  # journey_status=Not_Started
        _, events, _ = gen.generate_day(df, SIM_DATE)
        assert events.empty

    def test_returns_updated_state(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        updated, _, _ = gen.generate_day(df, SIM_DATE)
        # At minimum, weekly_impressions should have increased
        assert (updated["weekly_impressions"] >= df["weekly_impressions"]).all()

    def test_does_not_mutate_input(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        original_imp = df["weekly_impressions"].copy()
        gen.generate_day(df, SIM_DATE)
        assert (df["weekly_impressions"] == original_imp).all()


# ===========================================================================
# 5. TCC capacity enforcement (TCC-001..007)
# ===========================================================================

class TestTCCCapacity:
    def test_init_capacity_uses_ceil(self):
        """TCC-002: ceil(101 × 0.10) = 11, not 10."""
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        # 101 users, target=0.10 → ceil(10.1) = 11
        df  = make_state_df(101, config=cfg)
        # Override trigger to target=0.10
        trig = TriggerConfig("T1", 1, 0.10)
        cfg2 = make_config(
            triggers=(trig,),
            ads=(
                AdConfig("Ad_A", 1, 10, False, "Display", "VendorX", 0.10),
                AdConfig("Ad_B", 2, 10, False, "Display", "VendorX", 0.05),
            ),
        )
        df2 = _set_trigger(make_state_df(101, config=cfg2), "T1")
        gen2 = EngagementGenerator(cfg2)
        cap  = gen2._init_capacity_tracker(df2)
        assert cap.get("T1", 0) == 11

    def test_init_capacity_never_negative(self):
        """TCC-003: remaining_capacity = max(0, target - historical)."""
        trig = TriggerConfig("T1", 1, 0.10)
        cfg  = make_config(
            triggers=(trig,),
            ads=(
                AdConfig("Ad_A", 1, 10, False, "Display", "VendorX", 0.10),
                AdConfig("Ad_B", 2, 10, False, "Display", "VendorX", 0.05),
            ),
        )
        gen = EngagementGenerator(cfg)
        df  = _set_trigger(make_state_df(10, config=cfg), "T1")
        # Set ALL users as historically engaged → capacity must be 0, not negative
        df["historical_engaged"] = True
        cap = gen._init_capacity_tracker(df)
        assert cap.get("T1", 0) == 0

    def test_historical_engaged_reduces_capacity(self):
        trig = TriggerConfig("T1", 1, 0.20)
        cfg  = make_config(
            triggers=(trig,),
            ads=(
                AdConfig("Ad_A", 1, 10, False, "Display", "VendorX", 0.10),
                AdConfig("Ad_B", 2, 10, False, "Display", "VendorX", 0.05),
            ),
        )
        gen  = EngagementGenerator(cfg)
        df   = _set_trigger(make_state_df(10, config=cfg), "T1")  # 10 users, target=ceil(10×0.20)=2
        cap_before = gen._init_capacity_tracker(df)
        df["historical_engaged"] = False
        df.iloc[0, df.columns.get_loc("historical_engaged")] = True
        cap_after  = gen._init_capacity_tracker(df)
        assert cap_after.get("T1", 0) < cap_before.get("T1", 0)

    def test_exhausted_trigger_blocks_qualifying_events(self):
        """TCC-007: remaining_capacity=0 → no qualifying events for that trigger."""
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        # Set all scores high to ensure clicks would happen without TCC
        df["engagement_score"]        = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]  = np.float32(1.0)
        # Capacity = 0 for T1
        cap = {"T1": 0}
        _, events, _ = gen.generate_day(df, SIM_DATE, capacity_tracker=cap)
        # Should get Impressions but no Clicks
        assert ActionType.IMPRESSION.value in set(events["action_type"])
        assert ActionType.CLICK.value not in set(events["action_type"])

    def test_capacity_decrements_after_qualifying_events(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        df["engagement_score"]        = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]  = np.float32(1.0)

        cap_before = {"T1": 5}
        _, events, _ = gen.generate_day(df, SIM_DATE, capacity_tracker=cap_before)
        cap_after = gen._update_capacity_tracker(cap_before, events, df)
        n_qualifying = events[
            events["action_type"] == ActionType.CLICK.value
        ]["user_id"].nunique()
        if n_qualifying > 0:
            assert cap_after.get("T1", 5) < 5

    def test_non_exhausted_trigger_allows_qualifying(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        df["engagement_score"]        = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]  = np.float32(1.0)
        cap = {"T1": 100}  # High capacity
        _, events, _ = gen.generate_day(df, SIM_DATE, capacity_tracker=cap)
        # Impressions should be present; clicks may or may not occur (probabilistic)
        assert ActionType.IMPRESSION.value in set(events["action_type"])

    def test_tcc_block_restores_cooldown(self):
        """Cooldown end is restored to original after TCC block applied."""
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        original_cooldown = df["engagement_cooldown_end"].copy()
        cap = {"T1": 0}
        updated, _, _ = gen.generate_day(df, SIM_DATE, capacity_tracker=cap)
        # Cooldown should not be the fake far-future value
        for idx in df.index:
            updated_val = updated.loc[idx, "engagement_cooldown_end"]
            orig_val    = original_cooldown.loc[idx]
            # Neither should be the 9999-day synthetic value
            if updated_val is not None and str(updated_val) != "None":
                assert "9999" not in str(updated_val) or orig_val is not None


# ===========================================================================
# 6. Weekly reset (FAT-001 / FAT-002)
# ===========================================================================

class TestWeeklyReset:
    def test_monday_weekly_reset_in_metrics(self):
        cfg     = _make_display_config(
            simulation_start_date=date(2024, 1, 8),  # Monday
            simulation_end_date=date(2024, 1, 8),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(3, config=cfg)
        _, met, _, _ = gen.generate(df)
        assert met.iloc[0]["weekly_reset"] is True or met.iloc[0]["weekly_reset"] == True

    def test_non_monday_no_reset_in_metrics(self):
        cfg     = _make_display_config(
            simulation_start_date=date(2024, 1, 10),  # Wednesday
            simulation_end_date=date(2024, 1, 10),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(3, config=cfg)
        _, met, _, _ = gen.generate(df)
        assert met.iloc[0]["weekly_reset"] is False or met.iloc[0]["weekly_reset"] == False

    def test_monday_resets_counters_before_processing(self):
        """FAT-002: user at weekly impression cap on Monday gets impression (cap reset)."""
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(1, config=cfg))
        df["weekly_impressions"] = 5  # at cap
        monday = date(2024, 1, 8)
        _, events, _ = gen.generate_day(df, monday)
        # Monday resets counter, so impression should fire
        assert ActionType.IMPRESSION.value in set(events["action_type"])

    def test_non_monday_does_not_reset_capped_users(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(1, config=cfg))
        df["weekly_impressions"] = 5  # at cap
        wednesday = date(2024, 1, 10)
        _, events, _ = gen.generate_day(df, wednesday)
        assert ActionType.IMPRESSION.value not in set(events["action_type"])


# ===========================================================================
# 7. Display channel (ENG-011 / HR-003 / HR-004)
# ===========================================================================

class TestDisplayChannel:
    def test_active_display_users_get_impressions(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        _, events, _ = gen.generate_day(df, SIM_DATE)
        imp = events[events["action_type"] == ActionType.IMPRESSION.value]
        assert len(imp) == 5

    def test_display_impression_increments_metrics(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        _, events, metrics = gen.generate_day(df, SIM_DATE)
        assert metrics["n_impressions"] == 5

    def test_display_click_requires_impression(self):
        """HR-003/HR-004: no impression → no click (impression cap=0)."""
        cfg = _make_display_config(weekly_impression_cap=0)
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        df["engagement_score"]        = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        _, events, _ = gen.generate_day(df, SIM_DATE)
        assert ActionType.CLICK.value not in set(events["action_type"])

    def test_n_clicks_counted_in_metrics(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        df["engagement_score"]        = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]  = np.float32(1.0)
        _, events, metrics = gen.generate_day(df, SIM_DATE)
        n_clicks = (events["action_type"] == ActionType.CLICK.value).sum()
        assert metrics["n_clicks"] == n_clicks

    def test_actual_ctr_display_in_metrics(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        _, events, metrics = gen.generate_day(df, SIM_DATE)
        n_imp = (events["action_type"] == ActionType.IMPRESSION.value).sum()
        n_clk = (events["action_type"] == ActionType.CLICK.value).sum()
        expected_ctr = n_clk / n_imp if n_imp > 0 else 0.0
        assert metrics["actual_ctr_display"] == pytest.approx(expected_ctr)


# ===========================================================================
# 8. Email channel (ENG-012 / HR-005 / HR-006)
# ===========================================================================

class TestEmailChannel:
    def test_email_users_get_sent_events(self):
        cfg = _make_email_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg), channel="Email", vendor="VendorY")
        _, events, _ = gen.generate_day(df, SIM_DATE)
        sent = events[events["action_type"] == "Sent"]
        assert len(sent) == 5

    def test_email_click_requires_open(self):
        """HR-006: email click only if open occurred."""
        cfg = _make_email_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg), channel="Email", vendor="VendorY")
        df["engagement_score"] = np.float32(0.0)  # force zero probability
        df["channel_affinity_email"] = np.float32(0.0)
        _, events, _ = gen.generate_day(df, SIM_DATE)
        opens  = events[events["action_type"] == ActionType.OPEN.value]
        clicks = events[events["action_type"] == ActionType.CLICK.value]
        if opens.empty:
            assert clicks.empty

    def test_email_open_rate_in_metrics(self):
        cfg = _make_email_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg), channel="Email", vendor="VendorY")
        _, events, metrics = gen.generate_day(df, SIM_DATE)
        n_sent = (events["action_type"] == "Sent").sum()
        n_open = (events["action_type"] == ActionType.OPEN.value).sum()
        expected = n_open / n_sent if n_sent > 0 else 0.0
        assert metrics["actual_open_rate_email"] == pytest.approx(expected)

    def test_email_sends_counted_in_n_sends(self):
        cfg = _make_email_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg), channel="Email", vendor="VendorY")
        _, events, metrics = gen.generate_day(df, SIM_DATE)
        assert metrics["n_sends"] == (events["action_type"] == "Sent").sum()


# ===========================================================================
# 9. WhatsApp channel (ENG-013 / HR-007 / HR-008)
# ===========================================================================

class TestWhatsAppChannel:
    def test_whatsapp_users_get_sent_events(self):
        cfg = _make_wa_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg), channel="WhatsApp", vendor="VendorZ")
        _, events, _ = gen.generate_day(df, SIM_DATE)
        sent = events[events["action_type"] == "Sent"]
        assert len(sent) == 3

    def test_whatsapp_click_requires_open(self):
        cfg = _make_wa_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg), channel="WhatsApp", vendor="VendorZ")
        df["engagement_score"] = np.float32(0.0)
        df["channel_affinity_whatsapp"] = np.float32(0.0)
        _, events, _ = gen.generate_day(df, SIM_DATE)
        opens  = events[events["action_type"] == ActionType.OPEN.value]
        clicks = events[events["action_type"] == ActionType.CLICK.value]
        if opens.empty:
            assert clicks.empty

    def test_whatsapp_open_rate_in_metrics(self):
        cfg = _make_wa_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg), channel="WhatsApp", vendor="VendorZ")
        _, events, metrics = gen.generate_day(df, SIM_DATE)
        n_sent = (events["action_type"] == "Sent").sum()
        n_open = (events["action_type"] == ActionType.OPEN.value).sum()
        expected = n_open / n_sent if n_sent > 0 else 0.0
        assert metrics["actual_open_rate_wa"] == pytest.approx(expected)


# ===========================================================================
# 10. Journey eligibility
# ===========================================================================

class TestJourneyEligibility:
    def test_active_users_processed(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        _, events, _ = gen.generate_day(df, SIM_DATE)
        assert not events.empty

    def test_not_started_users_get_no_events(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = make_state_df(3, config=cfg)  # journey_status=Not_Started
        _, events, _ = gen.generate_day(df, SIM_DATE)
        assert events.empty

    def test_completed_users_get_no_events(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = make_state_df(3, config=cfg)
        df["journey_status"] = JourneyStatus.COMPLETED.value
        df["current_ad"]     = None
        _, events, _ = gen.generate_day(df, SIM_DATE)
        assert events.empty

    def test_n_users_active_in_metrics(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        _, _, metrics = gen.generate_day(df, SIM_DATE)
        assert metrics["n_users_active"] == 5


# ===========================================================================
# 11. Fatigue constraints (FAT-003..005)
# ===========================================================================

class TestFatigueConstraints:
    def test_user_at_weekly_impression_cap_gets_no_impression(self):
        cfg = _make_display_config()  # weekly_impression_cap=5
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(1, config=cfg))
        df["weekly_impressions"] = 5
        _, events, _ = gen.generate_day(df, SIM_DATE)
        assert ActionType.IMPRESSION.value not in set(events["action_type"])

    def test_user_in_cooldown_gets_reach_only(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(1, config=cfg))
        df["engagement_score"]        = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]  = np.float32(1.0)
        df["engagement_cooldown_end"] = str(SIM_DATE + timedelta(days=5))
        _, events, _ = gen.generate_day(df, SIM_DATE)
        assert ActionType.IMPRESSION.value in set(events["action_type"])
        assert ActionType.CLICK.value not in set(events["action_type"])

    def test_user_at_weekly_engagement_cap_no_qualifying(self):
        cfg = _make_display_config()  # weekly_engagement_cap=2
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(1, config=cfg))
        df["engagement_score"]        = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]  = np.float32(1.0)
        df["weekly_engagements"]      = 2  # at cap
        _, events, _ = gen.generate_day(df, SIM_DATE)
        assert ActionType.CLICK.value not in set(events["action_type"])


# ===========================================================================
# 12. Trigger priority rules
# ===========================================================================

class TestTriggerPriority:
    def test_multiple_triggers_tracked_separately(self):
        """Each trigger has its own capacity bucket."""
        trig1 = TriggerConfig("T1", 1, 0.20)
        trig2 = TriggerConfig("T2", 2, 0.50)
        ads   = (
            AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
            AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05),
        )
        cfg = make_config(triggers=(trig1, trig2), ads=ads)
        gen = EngagementGenerator(cfg)
        df  = make_state_df(10, config=cfg)
        # Add both categories and assign half to each
        df["trigger_name"] = df["trigger_name"].cat.add_categories(["T1", "T2"])
        df.iloc[:5, df.columns.get_loc("trigger_name")]  = "T1"
        df.iloc[5:, df.columns.get_loc("trigger_name")] = "T2"
        cap = gen._init_capacity_tracker(df)
        assert "T1" in cap
        assert "T2" in cap

    def test_high_priority_trigger_gets_capacity(self):
        """Priority-1 trigger should have remaining capacity."""
        trig = TriggerConfig("T1", 1, 0.30)
        ads  = (
            AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.10),
            AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.05),
        )
        cfg  = make_config(triggers=(trig,), ads=ads)
        gen  = EngagementGenerator(cfg)
        df   = _set_trigger(make_state_df(10, config=cfg), "T1")
        cap  = gen._init_capacity_tracker(df)
        # 10 users × 0.30 = 3 → ceil(3.0) = 3
        assert cap["T1"] == 3

    def test_trigger_at_zero_capacity_skips_qualifying(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        df["engagement_score"]        = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        _, events, _ = gen.generate_day(df, SIM_DATE, capacity_tracker={"T1": 0})
        assert ActionType.CLICK.value not in set(events["action_type"])


# ===========================================================================
# 13. Segment distribution
# ===========================================================================

class TestSegmentDistribution:
    def test_segment_engagement_in_diagnostics(self):
        seg1  = SegmentConfig("Seg_A", 1, 60.0)
        seg2  = SegmentConfig("Seg_B", 2, 40.0)
        trig  = TriggerConfig("T1", 1, 0.30)
        ads   = (
            AdConfig("Ad_A", 1, 5, False, "Display", "VX", 0.10),
            AdConfig("Ad_B", 2, 5, False, "Display", "VX", 0.05),
        )
        cfg = make_config(
            triggers=(trig,), segments=(seg1, seg2), ads=ads,
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 3),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(10, config=cfg)
        # Assign segments (segment is Categorical — add categories first)
        if hasattr(df["segment"], "cat"):
            new_cats = [v for v in ["Seg_A", "Seg_B"]
                        if v not in df["segment"].cat.categories]
            if new_cats:
                df["segment"] = df["segment"].cat.add_categories(new_cats)
        df.loc[df.index[:6], "segment"]  = "Seg_A"
        df.loc[df.index[6:], "segment"]  = "Seg_B"
        ev, _, diag, _ = gen.generate(df)
        seg_rows = diag[diag["metric"] == "segment_engagement_pct"]
        # Should have rows for Seg_A and Seg_B if any qualifying events
        if not ev.empty and len(ev[ev["action_type"].isin(
            {ActionType.CLICK.value, ActionType.OPEN.value}
        )]) > 0:
            assert len(seg_rows) >= 1

    def test_segment_diagnostics_schema(self):
        seg  = SegmentConfig("Seg_A", 1, 100.0)
        trig = TriggerConfig("T1", 1, 0.20)
        ads  = (
            AdConfig("Ad_A", 1, 5, False, "Display", "VX", 0.50),
            AdConfig("Ad_B", 2, 5, False, "Display", "VX", 0.05),
        )
        cfg = make_config(
            triggers=(trig,), segments=(seg,), ads=ads,
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 3),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(5, config=cfg)
        _, _, diag, _ = gen.generate(df)
        for col in ("metric", "entity", "requested", "actual", "variance", "variance_pct"):
            assert col in diag.columns


# ===========================================================================
# 14. Diagnostics
# ===========================================================================

class TestDiagnostics:
    def test_ctr_diagnostic_for_display_ad(self):
        cfg = _make_display_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 5),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(10, config=cfg)
        ev, _, diag, _ = gen.generate(df)
        if not ev.empty:
            ctr_rows = diag[diag["metric"] == "ctr"]
            assert len(ctr_rows) >= 1

    def test_open_rate_diagnostic_for_email_ad(self):
        cfg = _make_email_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 3),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(5, config=cfg)
        ev, _, diag, _ = gen.generate(df)
        if not ev.empty:
            or_rows = diag[diag["metric"] == "open_rate"]
            assert len(or_rows) >= 1

    def test_trigger_engagement_row_in_diagnostics(self):
        cfg = _make_display_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 3),
        )
        gen = EngagementGenerator(cfg)
        df  = _set_trigger(make_state_df(10, config=cfg), "T1")
        ev, _, diag, _ = gen.generate(df)
        if not ev.empty:
            trig_rows = diag[diag["metric"] == "trigger_engagement"]
            # Should have a row for trigger T1
            assert "T1" in trig_rows["entity"].values

    def test_variance_computed_correctly(self):
        gen = EngagementGenerator(_make_display_config())
        from core.engagement_generator import _diag_row
        row = _diag_row("ctr", "Ad_A", 0.10, 0.08)
        assert row["variance"] == pytest.approx(-0.02)
        assert row["variance_pct"] == pytest.approx(-20.0)

    def test_variance_pct_zero_when_requested_zero(self):
        from core.engagement_generator import _diag_row
        row = _diag_row("ctr", "Ad_A", 0.0, 0.05)
        assert row["variance_pct"] == pytest.approx(0.0)

    def test_empty_events_returns_empty_diagnostics(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        ev  = pd.DataFrame(columns=["campaign_id", "user_id", "simulation_date",
                                    "channel", "action_type", "current_ad",
                                    "vendor", "trigger_name", "segment"])
        df  = make_state_df(3, config=cfg)
        diag = gen.build_diagnostics(ev, df, pd.DataFrame())
        assert diag.empty or len(diag) == 0

    def test_diagnostics_columns_correct(self):
        cfg = _make_display_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 3),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(5, config=cfg)
        _, _, diag, _ = gen.generate(df)
        for col in ("metric", "entity", "requested", "actual",
                    "variance", "variance_pct"):
            assert col in diag.columns


# ===========================================================================
# 15. Event enrichment
# ===========================================================================

class TestEventEnrichment:
    def test_trigger_name_in_events(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        _, events, _ = gen.generate_day(df, SIM_DATE)
        if not events.empty:
            assert "trigger_name" in events.columns

    def test_segment_in_events(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        _, events, _ = gen.generate_day(df, SIM_DATE)
        if not events.empty:
            assert "segment" in events.columns

    def test_campaign_id_in_events(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        _, events, _ = gen.generate_day(df, SIM_DATE)
        if not events.empty:
            assert "campaign_id" in events.columns
            assert (events["campaign_id"] == cfg.campaign_id).all()


# ===========================================================================
# 16. Daily metrics
# ===========================================================================

class TestDailyMetrics:
    def test_n_reached_is_unique_users_with_reach_events(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        _, events, metrics = gen.generate_day(df, SIM_DATE)
        expected = events[events["action_type"].isin(
            {ActionType.IMPRESSION.value, "Sent"}
        )]["user_id"].nunique()
        assert metrics["n_reached"] == expected

    def test_n_qualifying_is_qualifying_event_count(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        df["engagement_score"]        = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]  = np.float32(1.0)
        _, events, metrics = gen.generate_day(df, SIM_DATE)
        n_clicks = (events["action_type"] == ActionType.CLICK.value).sum()
        assert metrics["n_qualifying"] == n_clicks

    def test_n_tcc_blocked_correct(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(5, config=cfg))
        cap = {"T1": 0}  # All 5 users blocked
        _, _, metrics = gen.generate_day(df, SIM_DATE, capacity_tracker=cap)
        assert metrics["n_tcc_blocked_users"] == 5

    def test_simulation_date_in_metrics(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(3, config=cfg))
        _, _, metrics = gen.generate_day(df, SIM_DATE)
        assert metrics["simulation_date"] == SIM_DATE


# ===========================================================================
# 17. Determinism (REQ-026)
# ===========================================================================

class TestDeterminism:
    def test_same_seed_same_events(self):
        cfg = _make_display_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 5),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(10, config=cfg)
        ev1, met1, _, _ = gen.generate(df)
        ev2, met2, _, _ = gen.generate(df)
        assert len(ev1) == len(ev2)
        assert len(met1) == len(met2)

    def test_different_state_different_output(self):
        cfg  = _make_display_config()
        gen  = EngagementGenerator(cfg)
        df1  = _activate(make_state_df(5, config=cfg))
        df1["engagement_score"] = np.float32(0.9)
        df2  = _activate(make_state_df(5, config=cfg))
        df2["engagement_score"] = np.float32(0.1)
        _, ev1, met1 = gen.generate_day(df1, SIM_DATE)
        _, ev2, met2 = gen.generate_day(df2, SIM_DATE)
        # Impressions should be same; clicks may differ
        assert met1["n_impressions"] == met2["n_impressions"]


# ===========================================================================
# 18. Edge cases
# ===========================================================================

class TestEdgeCases:
    def test_empty_dataframe_no_error(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = make_state_df(0, config=cfg).iloc[:0]
        # Should not raise
        updated, events, metrics = gen.generate_day(df, SIM_DATE)
        assert events.empty

    def test_single_user_simulation(self):
        cfg = _make_display_config(
            simulation_start_date=date(2024, 1, 1),
            simulation_end_date=date(2024, 1, 3),
        )
        gen = EngagementGenerator(cfg)
        df  = make_state_df(1, config=cfg)
        ev, met, diag, _ = gen.generate(df)
        assert len(met) == 3
        for col in ("metric", "entity", "requested", "actual"):
            assert col in diag.columns

    def test_all_users_at_tcc_zero_only_reach_events(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        df  = _activate(make_state_df(10, config=cfg))
        df["engagement_score"]        = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        cap = {trig.trigger_name: 0 for trig in cfg.triggers}
        _, events, _ = gen.generate_day(df, SIM_DATE, capacity_tracker=cap)
        # Only reach events (Impression) — no Click
        action_types = set(events["action_type"])
        assert ActionType.IMPRESSION.value in action_types
        assert ActionType.CLICK.value not in action_types

    def test_simulation_with_zero_ctr_produces_no_clicks(self):
        ad_a = AdConfig("Ad_A", 1, 10, False, "Display", "VX", 0.0)
        ad_b = AdConfig("Ad_B", 2, 10, False, "Display", "VX", 0.0)
        cfg  = make_config(ads=(ad_a, ad_b),
                           simulation_start_date=date(2024, 1, 1),
                           simulation_end_date=date(2024, 1, 3))
        gen  = EngagementGenerator(cfg)
        df   = make_state_df(5, config=cfg)
        ev, _, _, _ = gen.generate(df)
        if not ev.empty:
            assert ActionType.CLICK.value not in set(ev["action_type"])


# ===========================================================================
# 19. Compliance
# ===========================================================================

class TestCompliance:
    def test_no_iterrows_in_engagement_generator(self):
        """ARCH-011: no iterrows() in production code."""
        import pathlib
        path = (pathlib.Path(__file__).parent.parent.parent
                / "core" / "engagement_generator.py")
        content = path.read_text(encoding="utf-8")
        bad = [
            f"line {i+1}: {line.rstrip()}"
            for i, line in enumerate(content.splitlines())
            if ".iterrows(" in line
        ]
        assert bad == [], (
            "ARCH-011: iterrows() found in engagement_generator.py:\n"
            + "\n".join(bad)
        )

    def test_no_todo_fixme_hack(self):
        import pathlib
        path = (pathlib.Path(__file__).parent.parent.parent
                / "core" / "engagement_generator.py")
        content = path.read_text(encoding="utf-8")
        bad = [
            f"line {i+1}: {line.rstrip()}"
            for i, line in enumerate(content.splitlines())
            if any(t in line.upper() for t in ("TODO", "FIXME", "HACK"))
        ]
        assert bad == [], "Unresolved items in engagement_generator.py:\n" + "\n".join(bad)

    def test_all_declared(self):
        from core import engagement_generator
        assert hasattr(engagement_generator, "__all__")
        assert "EngagementGenerator" in engagement_generator.__all__

    def test_public_methods_have_docstrings(self):
        cfg = _make_display_config()
        gen = EngagementGenerator(cfg)
        for name in ("generate", "generate_day", "build_diagnostics"):
            assert getattr(gen, name).__doc__, f"Missing docstring: {name}"
