"""Tests for models/user_state.py — MT-004, MT-005, MT-011, REM-010."""
import pytest
from datetime import date, timedelta
from models.user_state import UserState
from models.enums import EligibilityStatus, JourneyStatus, BehaviorProfile


# ---------------------------------------------------------------------------
# Test factory — REM-010 FIX: eligibility_status=EligibilityStatus.NEW.value
# ---------------------------------------------------------------------------

def make_state(**kwargs) -> UserState:
    defaults = dict(
        campaign_id="CAMP-001",
        user_id="U001",
        trigger_name=None,
        segment=None,
        eligibility_status=EligibilityStatus.NEW.value,  # REM-010: was .ELIGIBLE.value
        journey_status=JourneyStatus.NOT_STARTED.value,
        journey_start_date=None,
        current_ad=None,
        days_in_ad=None,
        ad_click_received=False,
        journey_completion_date=None,
        cooling_period_end=None,
        behavior_profile=BehaviorProfile.MODERATE.value,
        engagement_score=0.5,
        channel_affinity_display=0.5,
        channel_affinity_email=0.5,
        channel_affinity_whatsapp=0.5,
        last_engagement_date=None,
        engagement_cooldown_end=None,
        weekly_impressions=0,
        weekly_clicks=0,
        weekly_opens=0,
        weekly_engagements=0,
        total_lifetime_engagements=0,
        last_reached_date=None,
        run_count=0,
        state_as_of_date=date(2024, 1, 15),
        trigger_history=None,
        first_trigger_name=None,
        first_trigger_date=None,
        total_trigger_appearances=0,
        channel=None,
        vendor=None,
        historical_engaged=False,
        is_valid=True,
        creative_affinities={},
    )
    defaults.update(kwargs)
    return UserState(**defaults)


TODAY = date(2024, 1, 15)

# ---------------------------------------------------------------------------
# Basic construction
# ---------------------------------------------------------------------------

def test_user_state_basic_construction():
    s = make_state()
    assert s.campaign_id == "CAMP-001"
    assert s.user_id == "U001"
    assert s.eligibility_status == EligibilityStatus.NEW.value


def test_user_state_primary_key():
    s = make_state(campaign_id="C1", user_id="U99")
    assert s.primary_key() == ("C1", "U99")


# ---------------------------------------------------------------------------
# MT-011 — engagement_score boundary values
# ---------------------------------------------------------------------------

def test_user_state_accepts_engagement_score_zero():
    s = make_state(engagement_score=0.0)
    assert s.engagement_score == 0.0


def test_user_state_accepts_engagement_score_one():
    s = make_state(engagement_score=1.0)
    assert s.engagement_score == 1.0


# ---------------------------------------------------------------------------
# MT-004 — is_in_journey_cooling
# ---------------------------------------------------------------------------

def test_is_in_journey_cooling_active():
    future = TODAY + timedelta(days=5)
    s = make_state(cooling_period_end=future)
    assert s.is_in_journey_cooling(TODAY) is True


def test_is_in_journey_cooling_expired():
    past = TODAY - timedelta(days=1)
    s = make_state(cooling_period_end=past)
    assert s.is_in_journey_cooling(TODAY) is False


def test_is_in_journey_cooling_not_set():
    s = make_state(cooling_period_end=None)
    assert s.is_in_journey_cooling(TODAY) is False


# ---------------------------------------------------------------------------
# MT-005 — get_creative_affinity
# ---------------------------------------------------------------------------

def test_get_creative_affinity_known_ad():
    s = make_state(creative_affinities={"Ad1": 0.75})
    assert s.get_creative_affinity("Ad1") == 0.75


def test_get_creative_affinity_unknown_ad():
    s = make_state(creative_affinities={"Ad1": 0.75})
    assert s.get_creative_affinity("Unknown") == 0.5  # default


# ---------------------------------------------------------------------------
# reset_weekly_counters
# ---------------------------------------------------------------------------

def test_reset_weekly_counters():
    s = make_state(weekly_impressions=3, weekly_clicks=1, weekly_opens=2, weekly_engagements=1)
    s.reset_weekly_counters()
    assert s.weekly_impressions == 0
    assert s.weekly_clicks == 0
    assert s.weekly_opens == 0
    assert s.weekly_engagements == 0


# ---------------------------------------------------------------------------
# get_channel_affinity
# ---------------------------------------------------------------------------

def test_get_channel_affinity_email():
    s = make_state(channel_affinity_email=0.8)
    assert s.get_channel_affinity("Email") == 0.8


def test_get_channel_affinity_display():
    s = make_state(channel_affinity_display=0.3)
    assert s.get_channel_affinity("Display") == 0.3


def test_get_channel_affinity_whatsapp():
    s = make_state(channel_affinity_whatsapp=0.9)
    assert s.get_channel_affinity("WhatsApp") == 0.9


def test_get_channel_affinity_unknown_returns_default():
    s = make_state()
    assert s.get_channel_affinity("UnknownChannel") == 0.5


# ---------------------------------------------------------------------------
# UserState.new() classmethod
# ---------------------------------------------------------------------------

def test_user_state_new_defaults():
    s = UserState.new("C1", "U1", date(2024, 1, 1), ["Ad_A", "Ad_B"])
    assert s.eligibility_status == EligibilityStatus.NEW.value
    assert s.journey_status == JourneyStatus.NOT_STARTED.value
    assert s.engagement_score == 0.5
    assert s.creative_affinities == {"Ad_A": 0.5, "Ad_B": 0.5}


def test_user_state_new_no_ads():
    s = UserState.new("C1", "U1", date(2024, 1, 1), [])
    assert s.creative_affinities == {}


def test_historical_engaged_defaults_to_false():
    """historical_engaged must default to False for new UserState instances."""
    s = make_state()
    assert s.historical_engaged is False


def test_is_valid_defaults_to_true():
    """is_valid must default to True for new UserState instances."""
    s = make_state()
    assert s.is_valid is True


def test_new_user_defaults_use_canonical_constants():
    """UserState.new() must use canonical constant values from utils.constants."""
    from utils.constants import (
        DEFAULT_ENGAGEMENT_SCORE,
        DEFAULT_CHANNEL_AFFINITY,
        DEFAULT_CREATIVE_AFFINITY,
    )
    from datetime import date as _date
    s = UserState.new("C1", "U1", _date(2024, 1, 1), ["Ad1"])
    assert s.engagement_score == DEFAULT_ENGAGEMENT_SCORE
    assert s.channel_affinity_display == DEFAULT_CHANNEL_AFFINITY
    assert s.channel_affinity_email == DEFAULT_CHANNEL_AFFINITY
    assert s.channel_affinity_whatsapp == DEFAULT_CHANNEL_AFFINITY
    assert s.creative_affinities["Ad1"] == DEFAULT_CREATIVE_AFFINITY
