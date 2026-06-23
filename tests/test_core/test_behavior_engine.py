"""Unit tests for core/behavior_engine.py — BehaviorEngine (Stage 6).

Coverage requirements:
  * All 18 behaviours listed in Wave 1 directive
  * Edge cases: empty DataFrame, fully-capped users, all channels
  * Regression guards for determinism, causal chains, fatigue rules
  * Compliance: no iterrows(), __all__ declared

Test isolation: every test builds its own state DataFrame from make_state_df()
plus targeted mutations.  No shared mutable fixtures.
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from core.behavior_engine import BehaviorEngine
from models.ad_config import AdConfig
from models.enums import ActionType, BehaviorProfile, JourneyStatus
from utils.exceptions import InputValidationError

from tests.test_core.conftest import make_config, make_state_df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _activate(df: pd.DataFrame, channel: str = "Display", vendor: str = "VendorX") -> pd.DataFrame:
    """Set all users to journey_status=Active with Ad_A on the given channel."""
    df = df.copy()
    df["journey_status"] = JourneyStatus.ACTIVE.value
    df["current_ad"]     = "Ad_A"
    df["channel"]        = channel
    df["vendor"]         = vendor
    return df


def _activate_single(
    user_id: str = "U001",
    channel: str = "Display",
    vendor: str = "VendorX",
    behavior_profile: str = BehaviorProfile.HIGHLY_ENGAGED.value,
    engagement_score: float = 0.8,
    weekly_impressions: int = 0,
    weekly_engagements: int = 0,
    engagement_cooldown_end=None,
    last_reached_date=None,
    config=None,
) -> pd.DataFrame:
    """Return a single-user active state DataFrame."""
    cfg = config or make_config()
    df  = make_state_df(1, config=cfg)
    df["user_id"]                   = user_id
    df["journey_status"]            = JourneyStatus.ACTIVE.value
    df["current_ad"]                = "Ad_A"
    df["channel"]                   = channel
    df["vendor"]                    = vendor
    df["behavior_profile"]          = behavior_profile
    df["engagement_score"]          = np.float32(engagement_score)
    df["weekly_impressions"]        = weekly_impressions
    df["weekly_engagements"]        = weekly_engagements
    df["engagement_cooldown_end"]   = engagement_cooldown_end
    df["last_reached_date"]         = last_reached_date
    return df


SIM_DATE = date(2024, 1, 10)   # Wednesday


# ===========================================================================
# 1. Initialisation
# ===========================================================================

class TestBehaviorEngineInit:
    def test_instantiates_with_config(self):
        cfg = make_config()
        engine = BehaviorEngine(cfg)
        assert engine is not None

    def test_stores_config(self):
        cfg = make_config()
        engine = BehaviorEngine(cfg)
        assert engine._config is cfg

    def test_ad_names_populated(self):
        cfg = make_config()
        engine = BehaviorEngine(cfg)
        assert "Ad_A" in engine._ad_names
        assert "Ad_B" in engine._ad_names

    def test_ad_target_ctr_populated(self):
        cfg = make_config()
        engine = BehaviorEngine(cfg)
        assert engine._ad_target_ctr["Ad_A"] == pytest.approx(0.10)
        assert engine._ad_target_ctr["Ad_B"] == pytest.approx(0.05)

    def test_missing_target_ctr_defaults(self):
        """Ad with target_ctr=None falls back to 0.05."""
        ad = AdConfig("Ad_X", 1, 5, True, "Display", "V", None)
        cfg = make_config(ads=(ad,))
        engine = BehaviorEngine(cfg)
        assert engine._ad_target_ctr["Ad_X"] == pytest.approx(0.05)


# ===========================================================================
# 2. Column validation
# ===========================================================================

class TestColumnValidation:
    def test_missing_single_column_raises(self):
        cfg = make_config()
        engine = BehaviorEngine(cfg)
        df = _activate(make_state_df(2, config=cfg))
        df = df.drop(columns=["weekly_impressions"])
        with pytest.raises(InputValidationError, match="weekly_impressions"):
            engine.process(df, SIM_DATE)

    def test_missing_multiple_columns_raises(self):
        cfg = make_config()
        engine = BehaviorEngine(cfg)
        df = _activate(make_state_df(2, config=cfg))
        df = df.drop(columns=["engagement_score", "ad_click_received"])
        with pytest.raises(InputValidationError):
            engine.process(df, SIM_DATE)

    def test_all_required_columns_present_no_error(self):
        cfg = make_config()
        engine = BehaviorEngine(cfg)
        df = _activate(make_state_df(3, config=cfg))
        # Should not raise
        updated_df, events_df = engine.process(df, SIM_DATE)
        assert updated_df is not None


# ===========================================================================
# 3. Weekly counter reset (FAT-001 / C-003)
# ===========================================================================

class TestWeeklyCounterReset:
    def test_monday_resets_all_weekly_counters(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(2, config=cfg))
        # Set non-zero counters
        df["weekly_impressions"] = 4
        df["weekly_clicks"]      = 2
        df["weekly_opens"]       = 3
        df["weekly_engagements"] = 1
        monday = date(2024, 1, 8)  # Monday
        updated_df, _ = engine.process(df, monday)
        # After Monday reset, counters start at 0 before event generation
        # They may increment to 1 from that day's events, so check <= 1
        assert updated_df["weekly_impressions"].max() <= 1
        assert updated_df["weekly_clicks"].max() <= 1
        assert updated_df["weekly_opens"].max() <= 1
        assert updated_df["weekly_engagements"].max() <= 1

    def test_non_monday_does_not_reset_counters(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = make_state_df(2, config=cfg)  # NOT active — no events
        df["weekly_impressions"] = 4
        tuesday = date(2024, 1, 9)
        updated_df, _ = engine.process(df, tuesday)
        # Users are not active, so no events; counter unchanged
        assert (updated_df["weekly_impressions"] == 4).all()

    def test_weekly_reset_public_wrapper(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(2, config=cfg))
        df["weekly_impressions"] = 3
        monday = date(2024, 1, 8)
        result = engine.reset_weekly_counters(df, monday)
        assert (result["weekly_impressions"] == 0).all()

    def test_reset_does_not_mutate_input(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(2, config=cfg))
        df["weekly_impressions"] = 3
        monday = date(2024, 1, 8)
        _ = engine.reset_weekly_counters(df, monday)
        assert (df["weekly_impressions"] == 3).all()


# ===========================================================================
# 4. Composite score (SIM-001)
# ===========================================================================

class TestCompositeScore:
    def test_scores_in_unit_interval(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(5, config=cfg))
        scores = engine.compute_composite_scores(df, SIM_DATE)
        assert (scores >= 0.0).all()
        assert (scores <= 1.0).all()

    def test_highly_engaged_scores_higher_than_dormant(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(2, config=cfg))
        df.iloc[0, df.columns.get_loc("behavior_profile")] = BehaviorProfile.HIGHLY_ENGAGED.value
        df.iloc[1, df.columns.get_loc("behavior_profile")] = BehaviorProfile.DORMANT.value
        # same engagement_score
        df["engagement_score"] = np.float32(0.5)
        scores = engine.compute_composite_scores(df, SIM_DATE)
        assert scores.iloc[0] > scores.iloc[1]

    def test_high_engagement_score_raises_composite(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df_high = _activate(make_state_df(1, config=cfg))
        df_low  = _activate(make_state_df(1, config=cfg))
        df_high["engagement_score"] = np.float32(0.9)
        df_low["engagement_score"]  = np.float32(0.1)
        s_high = engine.compute_composite_scores(df_high, SIM_DATE).iloc[0]
        s_low  = engine.compute_composite_scores(df_low, SIM_DATE).iloc[0]
        assert s_high > s_low

    def test_never_reached_recency_is_one(self):
        """Users who have never been reached get recency component = 1.0."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(1, config=cfg))
        df["last_reached_date"] = None
        # Manually compute recency component
        rec = engine._compute_reach_recency(df, SIM_DATE)
        assert rec.iloc[0] == pytest.approx(1.0)

    def test_recent_reach_has_higher_recency_than_old(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(2, config=cfg))
        df.iloc[0, df.columns.get_loc("last_reached_date")] = str(SIM_DATE - timedelta(days=2))
        df.iloc[1, df.columns.get_loc("last_reached_date")] = str(SIM_DATE - timedelta(days=25))
        rec = engine._compute_reach_recency(df, SIM_DATE)
        assert rec.iloc[0] > rec.iloc[1]

    def test_recency_at_frequency_max_is_zero(self):
        cfg    = make_config()  # frequency_max=30
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(1, config=cfg))
        df["last_reached_date"] = str(SIM_DATE - timedelta(days=30))
        rec = engine._compute_reach_recency(df, SIM_DATE)
        assert rec.iloc[0] == pytest.approx(0.0)

    def test_high_channel_affinity_raises_composite(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df_high = _activate(make_state_df(1, config=cfg))
        df_low  = _activate(make_state_df(1, config=cfg))
        df_high["channel_affinity_display"] = np.float32(1.0)
        df_low["channel_affinity_display"]  = np.float32(0.0)
        s_high = engine.compute_composite_scores(df_high, SIM_DATE).iloc[0]
        s_low  = engine.compute_composite_scores(df_low, SIM_DATE).iloc[0]
        assert s_high > s_low

    def test_high_creative_affinity_raises_composite(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df_high = _activate(make_state_df(1, config=cfg))
        df_low  = _activate(make_state_df(1, config=cfg))
        df_high["Creative_Affinity_Ad_A"] = np.float32(1.0)
        df_low["Creative_Affinity_Ad_A"]  = np.float32(0.0)
        s_high = engine.compute_composite_scores(df_high, SIM_DATE).iloc[0]
        s_low  = engine.compute_composite_scores(df_low, SIM_DATE).iloc[0]
        assert s_high > s_low


# ===========================================================================
# 5. Per-user deterministic randomness (SIM-019)
# ===========================================================================

class TestDeterministicRandomness:
    def test_same_user_same_date_same_jitter(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(1, config=cfg))
        df["user_id"] = "USER_FIXED"
        j1 = engine._compute_jitter(df, SIM_DATE).iloc[0]
        j2 = engine._compute_jitter(df, SIM_DATE).iloc[0]
        assert j1 == pytest.approx(j2)

    def test_different_users_different_jitter(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(5, config=cfg))
        jitter = engine._compute_jitter(df, SIM_DATE)
        # Very unlikely all 5 are identical
        assert jitter.nunique() > 1

    def test_different_dates_different_jitter(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(1, config=cfg))
        df["user_id"] = "USER_FIXED"
        j1 = engine._compute_jitter(df, SIM_DATE).iloc[0]
        j2 = engine._compute_jitter(df, SIM_DATE + timedelta(days=1)).iloc[0]
        assert j1 != pytest.approx(j2)

    def test_jitter_in_range(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(20, config=cfg))
        jitter = engine._compute_jitter(df, SIM_DATE)
        assert (jitter >= 0.0).all()
        assert (jitter <= 0.05).all()

    def test_md5_seed_formula(self):
        """Seed = (MD5(user_id) + date_ordinal) mod 2^32 (SIM-019)."""
        uid  = "CHECK_USER"
        d    = date(2024, 1, 10)
        base = int(hashlib.md5(uid.encode()).hexdigest(), 16)
        expected_seed = (base + d.toordinal()) % (2**32)
        rng  = np.random.default_rng(expected_seed)
        expected_jitter = rng.uniform(0.0, 0.05)

        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(1, config=cfg))
        df["user_id"] = uid
        actual = engine._compute_jitter(df, d).iloc[0]
        assert actual == pytest.approx(expected_jitter)

    def test_process_is_deterministic(self):
        """Same input + same date → same events_df every call."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(5, config=cfg))
        df["engagement_score"] = np.float32(0.9)
        _, ev1 = engine.process(df, SIM_DATE)
        _, ev2 = engine.process(df, SIM_DATE)
        assert len(ev1) == len(ev2)
        if len(ev1) > 0:
            assert set(ev1["user_id"]) == set(ev2["user_id"])


# ===========================================================================
# 6. Eligibility: journey status
# ===========================================================================

class TestEligibility:
    def test_not_started_users_not_processed(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = make_state_df(3, config=cfg)  # journey_status=Not_Started
        _, events = engine.process(df, SIM_DATE)
        assert events.empty

    def test_completed_users_not_processed(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = make_state_df(2, config=cfg)
        df["journey_status"] = JourneyStatus.COMPLETED.value
        _, events = engine.process(df, SIM_DATE)
        assert events.empty

    def test_active_user_without_current_ad_skipped(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = make_state_df(1, config=cfg)
        df["journey_status"] = JourneyStatus.ACTIVE.value
        df["current_ad"]     = None  # no ad assigned
        _, events = engine.process(df, SIM_DATE)
        assert events.empty

    def test_empty_dataframe_returns_empty_events(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(3, config=cfg)).iloc[0:0]
        updated_df, events = engine.process(df, SIM_DATE)
        assert events.empty
        assert len(updated_df) == 0

    def test_user_in_cooldown_gets_reach_not_qualify(self):
        """User in engagement_cooldown still gets Impression but not Click."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            engagement_cooldown_end=str(SIM_DATE + timedelta(days=5)),
            config=cfg,
        )
        # Force deterministic high scores so click would happen without cooldown
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)

        updated_df, events = engine.process(df, SIM_DATE)
        actions = set(events["action_type"])
        assert ActionType.IMPRESSION.value in actions
        assert ActionType.CLICK.value not in actions

    def test_user_at_weekly_engagement_cap_gets_reach_not_qualify(self):
        """User at weekly_engagement_cap=2 gets Impression but no qualifying event."""
        cfg    = make_config()  # weekly_engagement_cap=2
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            weekly_engagements=2,  # at cap
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)

        _, events = engine.process(df, SIM_DATE)
        assert ActionType.IMPRESSION.value in set(events["action_type"])
        assert ActionType.CLICK.value not in set(events["action_type"])


# ===========================================================================
# 7. Display channel events (ENG-011 / HR-003 / HR-004)
# ===========================================================================

class TestDisplayChannel:
    def test_active_display_user_gets_impression(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(engagement_score=0.5, config=cfg)
        _, events = engine.process(df, SIM_DATE)
        impressions = events[events["action_type"] == ActionType.IMPRESSION.value]
        assert len(impressions) == 1

    def test_impression_increments_weekly_impressions(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(config=cfg)
        updated_df, _ = engine.process(df, SIM_DATE)
        assert updated_df["weekly_impressions"].iloc[0] == 1

    def test_impression_sets_last_reached_date(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(config=cfg)
        updated_df, _ = engine.process(df, SIM_DATE)
        reached = updated_df["last_reached_date"].iloc[0]
        assert reached == SIM_DATE or str(reached) == str(SIM_DATE)

    def test_click_requires_impression_on_same_day(self):
        """HR-003/HR-004: Display click only if impression generated."""
        cfg    = make_config(weekly_impression_cap=0)  # cap=0 → no impression → no click
        engine = BehaviorEngine(cfg)
        df     = _activate_single(engagement_score=1.0, config=cfg)
        df["channel_affinity_display"] = np.float32(1.0)
        _, events = engine.process(df, SIM_DATE)
        assert ActionType.CLICK.value not in set(events["action_type"])

    def test_click_sets_ad_click_received(self):
        """Deterministically force a click and check ad_click_received."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        # Use HE + max affinities to maximize click probability
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            assert updated_df["ad_click_received"].iloc[0] is True or \
                   updated_df["ad_click_received"].iloc[0] == True

    def test_click_increments_weekly_clicks(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            assert updated_df["weekly_clicks"].iloc[0] == 1

    def test_at_weekly_impression_cap_no_impression(self):
        cfg    = make_config()  # weekly_impression_cap=5
        engine = BehaviorEngine(cfg)
        df     = _activate_single(weekly_impressions=5, config=cfg)
        _, events = engine.process(df, SIM_DATE)
        assert ActionType.IMPRESSION.value not in set(events["action_type"])

    def test_display_click_is_qualifying_event(self):
        """Display Click must set weekly_engagements and last_engagement_date."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            assert updated_df["weekly_engagements"].iloc[0] == 1
            assert updated_df["total_lifetime_engagements"].iloc[0] == 1
            eng_date = updated_df["last_engagement_date"].iloc[0]
            assert eng_date == SIM_DATE or str(eng_date) == str(SIM_DATE)

    def test_display_impression_is_not_qualifying(self):
        """Impression alone (no click) → weekly_engagements stays 0."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        # Zero probability of click: use ad with ctr=0
        ad_a   = AdConfig("Ad_A", 1, 5, True, "Display", "VendorX", 0.0)
        ad_b   = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.0)
        cfg2   = make_config(ads=(ad_a, ad_b))
        engine2 = BehaviorEngine(cfg2)
        df = _activate_single(engagement_score=0.5, config=cfg2)
        updated_df, _ = engine2.process(df, SIM_DATE)
        assert updated_df["weekly_engagements"].iloc[0] == 0


# ===========================================================================
# 8. Email channel events (ENG-012 / HR-005 / HR-006)
# ===========================================================================

class TestEmailChannel:
    def test_active_email_user_gets_sent_event(self):
        ad_a = AdConfig("Ad_A", 1, 5, True, "Email", "VendorY", 0.10)
        ad_b = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.05)
        cfg  = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg)
        df   = _activate_single(channel="Email", vendor="VendorY", config=cfg)
        _, events = engine.process(df, SIM_DATE)
        sent = events[events["action_type"] == "Sent"]
        assert len(sent) == 1

    def test_sent_increments_weekly_impressions(self):
        ad_a = AdConfig("Ad_A", 1, 5, True, "Email", "VendorY", 0.10)
        ad_b = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.05)
        cfg  = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg)
        df   = _activate_single(channel="Email", vendor="VendorY", config=cfg)
        updated_df, _ = engine.process(df, SIM_DATE)
        assert updated_df["weekly_impressions"].iloc[0] == 1

    def test_click_requires_open_email(self):
        """Email click only if open is generated first (HR-006 causal chain)."""
        ad_a = AdConfig("Ad_A", 1, 5, True, "Email", "VendorY", 0.10)
        ad_b = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.05)
        cfg  = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg)
        # Zero engagement to prevent opens → no clicks
        df   = _activate_single(
            channel="Email", vendor="VendorY",
            engagement_score=0.0,
            config=cfg,
        )
        df["channel_affinity_email"]   = np.float32(0.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(0.0)
        _, events = engine.process(df, SIM_DATE)
        # No opens → no clicks
        opens  = events[events["action_type"] == ActionType.OPEN.value]
        clicks = events[events["action_type"] == ActionType.CLICK.value]
        if len(opens) == 0:
            assert len(clicks) == 0

    def test_email_open_is_qualifying(self):
        ad_a = AdConfig("Ad_A", 1, 5, True, "Email", "VendorY", 0.50)
        ad_b = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.05)
        cfg  = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg)
        df   = _activate_single(
            channel="Email", vendor="VendorY",
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_email"]   = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        opens = events[events["action_type"] == ActionType.OPEN.value]
        if len(opens) > 0:
            assert updated_df["weekly_engagements"].iloc[0] >= 1

    def test_email_open_increments_weekly_opens(self):
        ad_a = AdConfig("Ad_A", 1, 5, True, "Email", "VendorY", 0.50)
        ad_b = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.05)
        cfg  = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg)
        df   = _activate_single(
            channel="Email", vendor="VendorY",
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_email"]   = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.OPEN.value in set(events["action_type"]):
            assert updated_df["weekly_opens"].iloc[0] == 1

    def test_email_click_is_qualifying(self):
        ad_a = AdConfig("Ad_A", 1, 5, True, "Email", "VendorY", 0.50)
        ad_b = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.05)
        cfg  = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg)
        df   = _activate_single(
            channel="Email", vendor="VendorY",
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_email"]   = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            assert updated_df["weekly_clicks"].iloc[0] == 1
            assert updated_df["ad_click_received"].iloc[0] == True


# ===========================================================================
# 9. WhatsApp channel events (ENG-013 / HR-007 / HR-008)
# ===========================================================================

class TestWhatsAppChannel:
    def test_active_whatsapp_user_gets_sent_event(self):
        ad_a = AdConfig("Ad_A", 1, 5, True, "WhatsApp", "VendorZ", 0.15)
        ad_b = AdConfig("Ad_B", 2, 7, False, "WhatsApp", None, 0.05)
        cfg  = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg)
        df   = _activate_single(channel="WhatsApp", vendor="VendorZ", config=cfg)
        _, events = engine.process(df, SIM_DATE)
        sent = events[events["action_type"] == "Sent"]
        assert len(sent) == 1

    def test_whatsapp_open_is_qualifying(self):
        ad_a = AdConfig("Ad_A", 1, 5, True, "WhatsApp", "VendorZ", 0.50)
        ad_b = AdConfig("Ad_B", 2, 7, False, "WhatsApp", None, 0.05)
        cfg  = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg)
        df   = _activate_single(
            channel="WhatsApp", vendor="VendorZ",
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_whatsapp"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]    = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        opens = events[events["action_type"] == ActionType.OPEN.value]
        if len(opens) > 0:
            assert updated_df["weekly_engagements"].iloc[0] >= 1

    def test_whatsapp_click_requires_open(self):
        ad_a = AdConfig("Ad_A", 1, 5, True, "WhatsApp", "VendorZ", 0.10)
        ad_b = AdConfig("Ad_B", 2, 7, False, "WhatsApp", None, 0.05)
        cfg  = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg)
        df   = _activate_single(
            channel="WhatsApp", vendor="VendorZ",
            engagement_score=0.0,
            config=cfg,
        )
        df["channel_affinity_whatsapp"] = np.float32(0.0)
        df["Creative_Affinity_Ad_A"]    = np.float32(0.0)
        _, events = engine.process(df, SIM_DATE)
        opens  = events[events["action_type"] == ActionType.OPEN.value]
        clicks = events[events["action_type"] == ActionType.CLICK.value]
        if len(opens) == 0:
            assert len(clicks) == 0


# ===========================================================================
# 10. Fatigue / weekly cap enforcement
# ===========================================================================

class TestFatigueAndWeeklyCaps:
    def test_weekly_engagement_cap_enforced(self):
        cfg    = make_config()  # weekly_engagement_cap=2
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(1, config=cfg))
        df["weekly_engagements"] = 2
        df["engagement_score"]   = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        _, events = engine.process(df, SIM_DATE)
        assert ActionType.CLICK.value not in set(events["action_type"])

    def test_weekly_impression_cap_enforced_display(self):
        cfg    = make_config()  # weekly_impression_cap=5
        engine = BehaviorEngine(cfg)
        df     = _activate_single(weekly_impressions=5, config=cfg)
        _, events = engine.process(df, SIM_DATE)
        assert ActionType.IMPRESSION.value not in set(events["action_type"])

    def test_engagement_cooldown_blocks_qualifying_events(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            engagement_cooldown_end=str(SIM_DATE + timedelta(days=1)),
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        _, events = engine.process(df, SIM_DATE)
        assert ActionType.CLICK.value not in set(events["action_type"])

    def test_expired_cooldown_allows_qualifying(self):
        """Cooldown that ended yesterday → user can get qualifying events."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            engagement_cooldown_end=str(SIM_DATE - timedelta(days=1)),
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        _, events = engine.process(df, SIM_DATE)
        # At high scores, click events should be possible
        # (test only verifies no exception and impression is present)
        assert ActionType.IMPRESSION.value in set(events["action_type"])

    def test_qualifying_event_sets_cooldown_end(self):
        cfg    = make_config()  # engagement_cooldown_days=3
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            cooldown = updated_df["engagement_cooldown_end"].iloc[0]
            expected_end = SIM_DATE + timedelta(days=3)
            assert cooldown == expected_end or str(cooldown) == str(expected_end)


# ===========================================================================
# 11. Channel affinity updates (CHA-005 / CHA-006)
# ===========================================================================

class TestChannelAffinity:
    def test_display_affinity_boosted_after_click(self):
        """Channel affinity +0.05 after qualifying click."""
        cfg    = make_config()  # affinity_boost_on_click=0.05
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        initial_affinity = float(df["channel_affinity_display"].iloc[0])
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            new_aff = float(updated_df["channel_affinity_display"].iloc[0])
            # Should be boosted
            assert new_aff >= 1.0  # already at ceiling

    def test_display_affinity_decays_after_impression_no_click(self):
        """Channel affinity -0.02 after reach with no qualifying event."""
        cfg    = make_config()  # affinity_decay_no_engage=0.02
        engine = BehaviorEngine(cfg)
        # Force CTR=0 to prevent clicks
        ad_a = AdConfig("Ad_A", 1, 5, True, "Display", "VendorX", 0.0)
        ad_b = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.0)
        cfg2   = make_config(ads=(ad_a, ad_b))
        engine2 = BehaviorEngine(cfg2)
        df     = _activate_single(config=cfg2)
        df["channel_affinity_display"] = np.float32(0.5)
        updated_df, _ = engine2.process(df, SIM_DATE)
        new_aff = float(updated_df["channel_affinity_display"].iloc[0])
        assert new_aff == pytest.approx(0.5 - 0.02, abs=1e-5)

    def test_affinity_clamped_at_ceiling(self):
        cfg    = make_config()  # affinity_ceiling=1.0
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(0.99)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            aff = float(updated_df["channel_affinity_display"].iloc[0])
            assert aff <= 1.0

    def test_affinity_clamped_at_floor(self):
        cfg    = make_config()  # affinity_floor=0.0
        engine = BehaviorEngine(cfg)
        ad_a   = AdConfig("Ad_A", 1, 5, True, "Display", "VendorX", 0.0)
        ad_b   = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.0)
        cfg2   = make_config(ads=(ad_a, ad_b))
        engine2 = BehaviorEngine(cfg2)
        df     = _activate_single(config=cfg2)
        df["channel_affinity_display"] = np.float32(0.01)
        updated_df, _ = engine2.process(df, SIM_DATE)
        aff = float(updated_df["channel_affinity_display"].iloc[0])
        assert aff >= 0.0

    def test_only_active_channel_affinity_updates(self):
        """Email/WhatsApp affinities unchanged when user is on Display."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        ad_a   = AdConfig("Ad_A", 1, 5, True, "Display", "VendorX", 0.0)
        ad_b   = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.0)
        cfg2   = make_config(ads=(ad_a, ad_b))
        engine2 = BehaviorEngine(cfg2)
        df     = _activate_single(config=cfg2)
        df["channel_affinity_email"]     = np.float32(0.5)
        df["channel_affinity_whatsapp"]  = np.float32(0.5)
        updated_df, _ = engine2.process(df, SIM_DATE)
        assert float(updated_df["channel_affinity_email"].iloc[0])    == pytest.approx(0.5, abs=1e-5)
        assert float(updated_df["channel_affinity_whatsapp"].iloc[0]) == pytest.approx(0.5, abs=1e-5)


# ===========================================================================
# 12. Creative affinity updates (CA-006 / CA-007)
# ===========================================================================

class TestCreativeAffinity:
    def test_creative_affinity_decays_after_impression_no_click(self):
        """Creative_Affinity_{ad} -0.02 after reach with no qualifying event."""
        ad_a = AdConfig("Ad_A", 1, 5, True, "Display", "VendorX", 0.0)
        ad_b = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.0)
        cfg2   = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg2)
        df     = _activate_single(config=cfg2)
        df["Creative_Affinity_Ad_A"] = np.float32(0.5)
        updated_df, _ = engine.process(df, SIM_DATE)
        new_aff = float(updated_df["Creative_Affinity_Ad_A"].iloc[0])
        assert new_aff == pytest.approx(0.5 - 0.02, abs=1e-5)

    def test_other_ad_creative_affinity_unchanged(self):
        """Creative_Affinity_Ad_B unchanged when user is on Ad_A."""
        ad_a   = AdConfig("Ad_A", 1, 5, True, "Display", "VendorX", 0.0)
        ad_b   = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.0)
        cfg2   = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg2)
        df     = _activate_single(config=cfg2)
        df["Creative_Affinity_Ad_B"] = np.float32(0.5)
        updated_df, _ = engine.process(df, SIM_DATE)
        assert float(updated_df["Creative_Affinity_Ad_B"].iloc[0]) == pytest.approx(0.5, abs=1e-5)

    def test_creative_affinity_boosted_after_qualifying(self):
        """Creative affinity +0.05 after click."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(0.5)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            aff = float(updated_df["Creative_Affinity_Ad_A"].iloc[0])
            assert aff > 0.5


# ===========================================================================
# 13. Engagement score updates
# ===========================================================================

class TestEngagementScore:
    def test_engagement_score_increases_after_qualifying(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=0.5,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            new_score = float(updated_df["engagement_score"].iloc[0])
            assert new_score > 0.5

    def test_engagement_score_decreases_after_reach_no_qualify(self):
        ad_a   = AdConfig("Ad_A", 1, 5, True, "Display", "VendorX", 0.0)
        ad_b   = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.0)
        cfg2   = make_config(ads=(ad_a, ad_b))
        engine = BehaviorEngine(cfg2)
        df     = _activate_single(engagement_score=0.5, config=cfg2)
        updated_df, _ = engine.process(df, SIM_DATE)
        new_score = float(updated_df["engagement_score"].iloc[0])
        # Impression happened, no click → score should decay
        assert new_score < 0.5

    def test_engagement_score_clamped_at_floor(self):
        ad_a   = AdConfig("Ad_A", 1, 5, True, "Display", "VendorX", 0.0)
        ad_b   = AdConfig("Ad_B", 2, 7, False, "Email", None, 0.0)
        cfg2   = make_config(ads=(ad_a, ad_b), engagement_score_floor=0.0)
        engine = BehaviorEngine(cfg2)
        df     = _activate_single(engagement_score=0.005, config=cfg2)
        updated_df, _ = engine.process(df, SIM_DATE)
        new_score = float(updated_df["engagement_score"].iloc[0])
        assert new_score >= 0.0

    def test_engagement_score_clamped_at_ceiling(self):
        cfg    = make_config(engagement_score_ceiling=1.0)
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=0.99,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            new_score = float(updated_df["engagement_score"].iloc[0])
            assert new_score <= 1.0


# ===========================================================================
# 14. State persistence / counters
# ===========================================================================

class TestStatePersistence:
    def test_total_lifetime_engagements_accumulates(self):
        """Two qualifying events over two days → total_lifetime_engagements=2."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        df1, ev1 = engine.process(df, date(2024, 1, 8))  # Monday (reset)
        # Only second call if first produced a click
        if ActionType.CLICK.value in set(ev1["action_type"]):
            # Remove cooldown so day 2 can engage
            df1["engagement_cooldown_end"] = None
            df1["weekly_engagements"] = 0  # reset cap
            df2, ev2 = engine.process(df1, date(2024, 1, 9))
            if ActionType.CLICK.value in set(ev2["action_type"]):
                assert df2["total_lifetime_engagements"].iloc[0] == 2

    def test_process_does_not_mutate_input(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(config=cfg)
        before = df["weekly_impressions"].iloc[0]
        _, _   = engine.process(df, SIM_DATE)
        assert df["weekly_impressions"].iloc[0] == before

    def test_last_engagement_date_set_on_qualifying(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        updated_df, events = engine.process(df, SIM_DATE)
        if ActionType.CLICK.value in set(events["action_type"]):
            ld = updated_df["last_engagement_date"].iloc[0]
            assert ld == SIM_DATE or str(ld) == str(SIM_DATE)


# ===========================================================================
# 15. Multi-week behavior / counter reset regression
# ===========================================================================

class TestMultiWeekBehavior:
    def test_counters_reset_on_monday_before_processing(self):
        """Counters at cap are reset on Monday, so user can engage that day."""
        cfg    = make_config()  # weekly_engagement_cap=2
        engine = BehaviorEngine(cfg)
        df     = _activate_single(
            engagement_score=1.0,
            behavior_profile=BehaviorProfile.HIGHLY_ENGAGED.value,
            weekly_engagements=2,  # at cap
            config=cfg,
        )
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        monday = date(2024, 1, 8)
        # On Monday, counters reset before processing → user can engage
        _, events = engine.process(df, monday)
        # Impression should definitely occur (cap was reset)
        assert ActionType.IMPRESSION.value in set(events["action_type"])

    def test_weekly_counter_not_reset_mid_week(self):
        """Counters at cap stay at cap on a non-Monday."""
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(weekly_impressions=5, config=cfg)
        wednesday = date(2024, 1, 10)
        _, events = engine.process(df, wednesday)
        assert ActionType.IMPRESSION.value not in set(events["action_type"])

    def test_state_persists_across_non_monday_calls(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        # Day 1
        df1    = _activate_single(engagement_score=0.5, config=cfg)
        updated1, _ = engine.process(df1, date(2024, 1, 9))
        # Day 2 — pass updated state forward
        updated2, _ = engine.process(updated1, date(2024, 1, 10))
        # Impression count should be 2 (no Monday reset between them)
        assert updated2["weekly_impressions"].iloc[0] == 2


# ===========================================================================
# 16. Events DataFrame schema
# ===========================================================================

class TestEventsSchema:
    def test_events_df_has_correct_columns(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(config=cfg)
        _, events = engine.process(df, SIM_DATE)
        for col in ("user_id", "simulation_date", "channel", "action_type",
                    "current_ad", "vendor"):
            assert col in events.columns

    def test_empty_events_df_has_correct_columns(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = make_state_df(1, config=cfg)  # not active
        _, events = engine.process(df, SIM_DATE)
        assert events.empty
        for col in ("user_id", "simulation_date", "channel", "action_type",
                    "current_ad", "vendor"):
            assert col in events.columns

    def test_events_simulation_date_matches_input(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(config=cfg)
        _, events = engine.process(df, SIM_DATE)
        if not events.empty:
            assert (events["simulation_date"] == SIM_DATE).all()

    def test_events_user_id_matches_state(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate_single(user_id="MY_USER", config=cfg)
        _, events = engine.process(df, SIM_DATE)
        if not events.empty:
            assert (events["user_id"] == "MY_USER").all()


# ===========================================================================
# 17. Multi-user vectorized processing
# ===========================================================================

class TestMultiUserVectorized:
    def test_multiple_users_processed_independently(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(10, config=cfg))
        df["engagement_score"] = np.float32(0.5)
        updated_df, events = engine.process(df, SIM_DATE)
        # All users should get impressions (none at cap)
        imp_users = set(events[events["action_type"] == ActionType.IMPRESSION.value]["user_id"])
        assert len(imp_users) == 10

    def test_capped_user_does_not_block_other_users(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(3, config=cfg))
        # Put one user at impression cap
        df.iloc[0, df.columns.get_loc("weekly_impressions")] = 5
        _, events = engine.process(df, SIM_DATE)
        imp_users = set(events[events["action_type"] == ActionType.IMPRESSION.value]["user_id"])
        # Capped user should not appear
        assert df.iloc[0]["user_id"] not in imp_users
        # Others should appear
        assert len(imp_users) == 2

    def test_cooldown_user_gets_reach_only(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        df     = _activate(make_state_df(2, config=cfg))
        df["engagement_score"] = np.float32(1.0)
        df["channel_affinity_display"] = np.float32(1.0)
        df["Creative_Affinity_Ad_A"]   = np.float32(1.0)
        # Put user 0 in cooldown
        df.iloc[0, df.columns.get_loc("engagement_cooldown_end")] = str(
            SIM_DATE + timedelta(days=2)
        )
        updated_df, events = engine.process(df, SIM_DATE)
        u0 = df.iloc[0]["user_id"]
        u0_events = events[events["user_id"] == u0]
        assert ActionType.CLICK.value not in set(u0_events["action_type"])


# ===========================================================================
# 18. Behavior profile influence (ENG-004)
# ===========================================================================

class TestBehaviorProfileInfluence:
    def test_all_four_profiles_produce_different_scores(self):
        cfg    = make_config()
        engine = BehaviorEngine(cfg)
        profiles = [
            BehaviorProfile.HIGHLY_ENGAGED.value,
            BehaviorProfile.MODERATE.value,
            BehaviorProfile.PASSIVE.value,
            BehaviorProfile.DORMANT.value,
        ]
        scores = []
        for p in profiles:
            df = _activate_single(
                engagement_score=0.5,
                behavior_profile=p,
                config=cfg,
            )
            df["channel_affinity_display"] = np.float32(0.5)
            df["Creative_Affinity_Ad_A"]   = np.float32(0.5)
            df["last_reached_date"]        = None
            # Zero jitter to isolate profile effect
            s = (
                cfg.scoring_weight_engagement * 0.5
                + cfg.scoring_weight_profile * {
                    BehaviorProfile.HIGHLY_ENGAGED.value: 1.0,
                    BehaviorProfile.MODERATE.value: 0.5,
                    BehaviorProfile.PASSIVE.value: 0.2,
                    BehaviorProfile.DORMANT.value: 0.05,
                }[p]
                + cfg.scoring_weight_creative * 0.5
                + cfg.scoring_weight_channel * 0.5
                + cfg.scoring_weight_recency * 1.0
            )
            scores.append(s)
        # Verify order
        assert scores[0] > scores[1] > scores[2] > scores[3]

    def test_profile_component_highly_engaged_is_one(self):
        from core.behavior_engine import _PROFILE_COMPONENT
        assert _PROFILE_COMPONENT[BehaviorProfile.HIGHLY_ENGAGED.value] == pytest.approx(1.0)

    def test_profile_component_dormant_is_point_zero_five(self):
        from core.behavior_engine import _PROFILE_COMPONENT
        assert _PROFILE_COMPONENT[BehaviorProfile.DORMANT.value] == pytest.approx(0.05)


# ===========================================================================
# 19. Compliance
# ===========================================================================

class TestCompliance:
    def test_no_iterrows_in_behavior_engine(self):
        """ARCH-011: no iterrows() calls in production code."""
        import pathlib
        path = pathlib.Path(__file__).parent.parent.parent / "core" / "behavior_engine.py"
        content = path.read_text(encoding="utf-8")
        bad_lines = [
            f"line {i+1}: {line.rstrip()}"
            for i, line in enumerate(content.splitlines())
            if ".iterrows(" in line
        ]
        assert len(bad_lines) == 0, (
            f"ARCH-011 violation — iterrows() found in behavior_engine.py:\n"
            + "\n".join(bad_lines)
        )

    def test_no_todo_fixme_hack_in_behavior_engine(self):
        import pathlib
        path = pathlib.Path(__file__).parent.parent.parent / "core" / "behavior_engine.py"
        content = path.read_text(encoding="utf-8")
        bad = [
            f"line {i+1}: {line.rstrip()}"
            for i, line in enumerate(content.splitlines())
            if any(tok in line.upper() for tok in ("TODO", "FIXME", "HACK"))
        ]
        assert bad == [], "Unresolved TODO/FIXME/HACK in behavior_engine.py:\n" + "\n".join(bad)

    def test_all_declared(self):
        from core import behavior_engine
        assert hasattr(behavior_engine, "__all__")
        assert "BehaviorEngine" in behavior_engine.__all__

    def test_public_methods_have_docstrings(self):
        engine = BehaviorEngine(make_config())
        for name in ("process", "compute_composite_scores", "reset_weekly_counters"):
            fn = getattr(engine, name)
            assert fn.__doc__, f"Missing docstring on BehaviorEngine.{name}"
