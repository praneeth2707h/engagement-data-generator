"""Unit tests for core/journey_engine.py -- Stage 5 Journey Building.

Covers:
    - Journey start for NEW and RE_ENTRY users
    - Move-on-click advance (BIZ-018/C-001 exclusive rule)
    - Stay-until-duration-expiry advance
    - Ad1 -> Ad2 -> ... -> AdN full progression
    - Configurable journey lengths
    - Terminal journey completion and cooling period creation
    - Re-entry handling (C-004): restart from Ad1, preserve completion date
    - Journey state persistence across multiple advance() calls
    - Multi-week simulation continuity
    - Historical state continuity (returning users)
    - Ineligible users (COOLING, EXCLUDED, SKIPPED) are untouched
    - Edge cases: empty state_df, single-ad journey, cooling_period_days=0
    - Compliance: no iterrows(), no inline "|" literals
"""
from __future__ import annotations

import inspect
from datetime import date, timedelta

import pandas as pd
import pytest

from core.journey_engine import JourneyEngine
from models.ad_config import AdConfig
from models.enums import EligibilityStatus, JourneyStatus
from utils.exceptions import InputValidationError

from tests.test_core.conftest import make_config, make_state_df


# ---------------------------------------------------------------------------
# Test-local helpers
# ---------------------------------------------------------------------------

SIM_DATE = date(2024, 2, 1)


def _make_je(
    *,
    duration_a: int = 3,
    duration_b: int = 2,
    move_on_click_a: bool = False,
    move_on_click_b: bool = False,
    cooling_days: int = 14,
    allow_reentry: bool = True,
    n_ads: int = 2,
) -> JourneyEngine:
    """Return a JourneyEngine backed by a freshly constructed ConfigRegistry.

    By default: 2-ad journey, neither ad uses move_on_click.
    """
    ads: list[AdConfig] = [
        AdConfig(
            ad_name="Ad_A",
            ad_order=1,
            duration_days=duration_a,
            move_on_click=move_on_click_a,
            channel="Display",
            vendor="VendorX",
            target_ctr=0.10,
        ),
    ]
    if n_ads >= 2:
        ads.append(
            AdConfig(
                ad_name="Ad_B",
                ad_order=2,
                duration_days=duration_b,
                move_on_click=move_on_click_b,
                channel="Email",
                vendor=None,      # falls back to default_vendor
                target_ctr=0.05,
            )
        )
    if n_ads >= 3:
        ads.append(
            AdConfig(
                ad_name="Ad_C",
                ad_order=3,
                duration_days=2,
                move_on_click=False,
                channel="WhatsApp",
                vendor="VendorZ",
                target_ctr=0.08,
            )
        )
    if n_ads >= 4:
        ads.append(
            AdConfig(
                ad_name="Ad_D",
                ad_order=4,
                duration_days=1,
                move_on_click=False,
                channel="Display",
                vendor=None,
                target_ctr=0.04,
            )
        )

    config = make_config(
        ads=tuple(ads),
        cooling_period_days=cooling_days,
        allow_reentry=allow_reentry,
    )
    return JourneyEngine(config)


def _advance_n(
    engine: JourneyEngine,
    state_df: pd.DataFrame,
    start_date: date,
    n: int,
    click_on_days: set[int] | None = None,
) -> pd.DataFrame:
    """Run advance() for n consecutive days starting from start_date.

    Args:
        engine: JourneyEngine instance.
        state_df: Initial state DataFrame.
        start_date: Date of the first advance() call.
        n: Number of days to simulate.
        click_on_days: 1-based day numbers on which ALL users have
                       ad_click_received=True before the advance call.

    Returns:
        Final state_df after n advance() calls.
    """
    df = state_df.copy()
    click_on_days = click_on_days or set()
    for i in range(n):
        sim_day = start_date + timedelta(days=i)
        if (i + 1) in click_on_days:
            df["ad_click_received"] = True
        df = engine.advance(df, sim_day)
    return df


# ===========================================================================
# 1. Initialisation
# ===========================================================================

def test_init_empty_ads_raises():
    """ConfigRegistry already raises ConfigError when ads is empty (defense-in-depth).

    JourneyEngine cannot receive a config with no ads via normal construction
    because ConfigRegistry.__post_init__ validates ads is non-empty first.
    Verify the combined system raises any error when ads=() is attempted.
    """
    from utils.exceptions import ConfigError
    with pytest.raises(ConfigError, match="at least one AdConfig"):
        make_config(ads=())


def test_init_journey_length():
    """journey_length property equals number of ads in config."""
    je = _make_je(n_ads=3)
    assert je.journey_length == 3


def test_init_total_journey_days():
    """total_journey_days returns sum of all ad duration_days."""
    je = _make_je(duration_a=3, duration_b=2, n_ads=2)
    assert je.total_journey_days == 5


def test_init_single_ad():
    """JourneyEngine initialises correctly with a single ad."""
    je = _make_je(n_ads=1)
    assert je.journey_length == 1


# ===========================================================================
# 2. Column validation
# ===========================================================================

def test_advance_raises_on_missing_required_column():
    """advance() raises InputValidationError if required column is absent."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=2, config=config)
    df_bad = df.drop(columns=["current_ad"])
    with pytest.raises(InputValidationError, match="current_ad"):
        je.advance(df_bad, SIM_DATE)


def test_advance_empty_df_returns_copy():
    """advance() on an empty DataFrame returns an empty copy without error."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=2, config=config).iloc[0:0].copy()
    result = je.advance(df, SIM_DATE)
    assert len(result) == 0
    assert result is not df


# ===========================================================================
# 3. Journey start -- NEW users
# ===========================================================================

def test_new_user_starts_journey_at_ad1():
    """NEW user: after first advance(), current_ad = first ad, journey = Active."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=1, config=config)
    # Ensure user is NEW
    df["eligibility_status"] = EligibilityStatus.NEW.value
    df["journey_status"] = JourneyStatus.NOT_STARTED.value

    result = je.advance(df, SIM_DATE)

    assert result.loc[0, "current_ad"] == "Ad_A"
    assert result.loc[0, "journey_status"] == JourneyStatus.ACTIVE.value
    assert result.loc[0, "journey_start_date"] == SIM_DATE


def test_new_user_days_in_ad_is_1_after_start():
    """NEW user: days_in_ad = 1 on the first day (entry day counts as day 1)."""
    je = _make_je(duration_a=5)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    result = je.advance(df, SIM_DATE)
    assert int(result.loc[0, "days_in_ad"]) == 1


def test_new_user_channel_set_from_ad_config():
    """NEW user: channel field is set from the first ad's channel."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    result = je.advance(df, SIM_DATE)
    assert result.loc[0, "channel"] == "Display"


def test_new_user_vendor_uses_per_ad_vendor():
    """NEW user: vendor field is set from Ad_A.vendor (not default_vendor)."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    result = je.advance(df, SIM_DATE)
    # Ad_A.vendor = "VendorX"
    assert result.loc[0, "vendor"] == "VendorX"


def test_new_user_vendor_falls_back_to_default():
    """When per-ad vendor is None, default_vendor is used."""
    je = _make_je(n_ads=1)
    # Use a single-ad config where the ad has no vendor
    from models.ad_config import AdConfig
    config = make_config(
        ads=(AdConfig("Ad_A", 1, 3, False, "Display", None, 0.10),),
    )
    je2 = JourneyEngine(config)
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    result = je2.advance(df, SIM_DATE)
    assert result.loc[0, "vendor"] == config.default_vendor


def test_skipped_user_journey_not_started():
    """SKIPPED user: journey_status and current_ad unchanged after advance()."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.SKIPPED.value
    df["journey_status"] = JourneyStatus.NOT_STARTED.value
    df["current_ad"] = None

    result = je.advance(df, SIM_DATE)

    assert result.loc[0, "journey_status"] == JourneyStatus.NOT_STARTED.value
    assert pd.isna(result.loc[0, "current_ad"])


def test_excluded_user_not_touched():
    """EXCLUDED user: all journey fields unchanged after advance()."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.EXCLUDED.value
    df["journey_status"] = JourneyStatus.NOT_STARTED.value

    result = je.advance(df, SIM_DATE)
    assert result.loc[0, "journey_status"] == JourneyStatus.NOT_STARTED.value
    assert pd.isna(result.loc[0, "current_ad"])


def test_cooling_user_not_touched():
    """COOLING user: journey fields unchanged after advance()."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.COOLING.value
    df["journey_status"] = JourneyStatus.COMPLETED.value
    df["cooling_period_end"] = SIM_DATE + timedelta(days=5)

    result = je.advance(df, SIM_DATE)
    assert result.loc[0, "journey_status"] == JourneyStatus.COMPLETED.value


# ===========================================================================
# 4. Duration-based advance
# ===========================================================================

def test_user_stays_on_ad_before_duration_expires():
    """User stays on Ad_A while days_in_ad < duration_days."""
    je = _make_je(duration_a=5)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # Advance for 4 days (duration = 5, should still be on Ad_A)
    result = _advance_n(je, df, SIM_DATE, n=4)

    assert result.loc[0, "current_ad"] == "Ad_A"
    assert int(result.loc[0, "days_in_ad"]) == 4


def test_user_advances_on_duration_expiry():
    """User advances to Ad_B exactly when days_in_ad reaches duration_days."""
    je = _make_je(duration_a=3)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # Day 3: days_in_ad reaches 3 = duration → advance to Ad_B; new ad entry = 0
    result = _advance_n(je, df, SIM_DATE, n=3)

    assert result.loc[0, "current_ad"] == "Ad_B"
    assert int(result.loc[0, "days_in_ad"]) == 0


def test_one_day_ad_advances_same_day():
    """User on a 1-day ad advances on the same day they enter (duration=1)."""
    je = _make_je(duration_a=1)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    result = _advance_n(je, df, SIM_DATE, n=1)

    assert result.loc[0, "current_ad"] == "Ad_B"


def test_duration_based_advance_updates_channel():
    """Channel is updated to the next ad's channel on duration-based advance."""
    je = _make_je(duration_a=1)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    result = _advance_n(je, df, SIM_DATE, n=1)

    # Ad_B.channel = "Email"
    assert result.loc[0, "channel"] == "Email"


def test_duration_based_advance_resets_days_in_ad():
    """days_in_ad resets after duration-based advance to next ad."""
    je = _make_je(duration_a=2)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # 2 days on Ad_A, then 1 day on Ad_B
    result = _advance_n(je, df, SIM_DATE, n=3)

    assert result.loc[0, "current_ad"] == "Ad_B"
    assert int(result.loc[0, "days_in_ad"]) == 1


# ===========================================================================
# 5. Click-based advance (BIZ-018/C-001)
# ===========================================================================

def test_click_advance_fires_when_move_on_click_true():
    """move_on_click=True + ad_click_received=True --> user advances to next ad."""
    je = _make_je(duration_a=10, move_on_click_a=True)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # Day 1: start journey (days_in_ad becomes 1, no click)
    result = _advance_n(je, df, SIM_DATE, n=1)
    assert result.loc[0, "current_ad"] == "Ad_A"

    # Day 2: click fires -> advance
    result["ad_click_received"] = True
    result = je.advance(result, SIM_DATE + timedelta(days=1))

    assert result.loc[0, "current_ad"] == "Ad_B"


def test_click_advance_does_not_fire_when_move_on_click_false():
    """move_on_click=False: ad_click_received=True does NOT cause early advance."""
    je = _make_je(duration_a=5, move_on_click_a=False)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # Advance for 2 days, simulating a click on day 2
    result = _advance_n(je, df, SIM_DATE, n=2, click_on_days={2})

    # Should still be on Ad_A (duration=5, no click-advance)
    assert result.loc[0, "current_ad"] == "Ad_A"
    assert int(result.loc[0, "days_in_ad"]) == 2


def test_click_advance_exclusive_skips_duration_check(monkeypatch):
    """BIZ-018/C-001: click-advance fires -> duration check skipped same day.

    A user on a 1-day ad (duration=1, move_on_click=True) clicks on day 1.
    Both click-advance and duration-advance would trigger.
    Only click-advance fires (exclusive). They still advance only ONCE.
    """
    je = _make_je(duration_a=1, move_on_click_a=True, n_ads=2)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # Day 1 with click -- both conditions would fire, but advance is counted once
    df["ad_click_received"] = True
    result = je.advance(df, SIM_DATE)

    # User advanced exactly once to Ad_B
    assert result.loc[0, "current_ad"] == "Ad_B"


def test_click_advance_resets_days_in_ad():
    """After click-advance, days_in_ad is reset (= 0 + 1 on next advance call)."""
    je = _make_je(duration_a=10, duration_b=5, move_on_click_a=True)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # Day 1-3: on Ad_A, no click
    result = _advance_n(je, df, SIM_DATE, n=3)
    assert int(result.loc[0, "days_in_ad"]) == 3

    # Day 4: click fires -- advance to Ad_B
    result["ad_click_received"] = True
    result = je.advance(result, SIM_DATE + timedelta(days=3))

    # On Ad_B with days_in_ad = 0 (will be 1 on next advance)
    assert result.loc[0, "current_ad"] == "Ad_B"
    assert int(result.loc[0, "days_in_ad"]) == 0

    # Day 5: days_in_ad incremented to 1 on Ad_B
    result = je.advance(result, SIM_DATE + timedelta(days=4))
    assert int(result.loc[0, "days_in_ad"]) == 1


# ===========================================================================
# 6. Full ad progression (Ad1 -> Ad2 -> Ad3 -> Ad4)
# ===========================================================================

def test_full_4_ad_progression():
    """User progresses through all 4 ads in order then completes."""
    je = _make_je(
        duration_a=1, duration_b=1, n_ads=4
    )
    config = make_config(
        ads=(
            AdConfig("Ad_A", 1, 1, False, "Display", None, 0.10),
            AdConfig("Ad_B", 2, 1, False, "Email", None, 0.05),
            AdConfig("Ad_C", 3, 1, False, "WhatsApp", None, 0.08),
            AdConfig("Ad_D", 4, 1, False, "Display", None, 0.04),
        )
    )
    je2 = JourneyEngine(config)
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # Day 1: start Ad_A, advance to Ad_B (duration=1)
    r1 = je2.advance(df, SIM_DATE)
    assert r1.loc[0, "current_ad"] == "Ad_B"

    # Day 2: on Ad_B -> advance to Ad_C
    r2 = je2.advance(r1, SIM_DATE + timedelta(1))
    assert r2.loc[0, "current_ad"] == "Ad_C"

    # Day 3: on Ad_C -> advance to Ad_D
    r3 = je2.advance(r2, SIM_DATE + timedelta(2))
    assert r3.loc[0, "current_ad"] == "Ad_D"

    # Day 4: on Ad_D (duration=1) -> complete
    r4 = je2.advance(r3, SIM_DATE + timedelta(3))
    assert r4.loc[0, "journey_status"] == JourneyStatus.COMPLETED.value
    assert pd.isna(r4.loc[0, "current_ad"])


def test_3_ad_journey_channel_sequence():
    """Channel field tracks the current ad's channel through a 3-ad journey."""
    config = make_config(
        ads=(
            AdConfig("Ad_A", 1, 3, False, "Display", None, 0.10),
            AdConfig("Ad_B", 2, 1, False, "Email", None, 0.05),
            AdConfig("Ad_C", 3, 1, False, "WhatsApp", None, 0.08),
        )
    )
    je = JourneyEngine(config)
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    r1 = je.advance(df, SIM_DATE)
    assert r1.loc[0, "channel"] == "Display"

    r2 = je.advance(r1, SIM_DATE + timedelta(1))
    assert r2.loc[0, "channel"] == "Display"   # still on Ad_A (duration=3)

    r3 = je.advance(r2, SIM_DATE + timedelta(2))
    assert r3.loc[0, "channel"] == "Email"     # now on Ad_B

    r4 = je.advance(r3, SIM_DATE + timedelta(3))
    assert r4.loc[0, "channel"] == "WhatsApp"  # now on Ad_C


# ===========================================================================
# 7. Journey completion and cooling period
# ===========================================================================

def test_journey_completion_sets_completed_status():
    """User completing the last ad gets journey_status = Completed."""
    je = _make_je(duration_a=1, duration_b=1)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # 2 days: Day 1 advances through Ad_A to Ad_B; Day 2 completes Ad_B
    result = _advance_n(je, df, SIM_DATE, n=2)

    assert result.loc[0, "journey_status"] == JourneyStatus.COMPLETED.value


def test_journey_completion_sets_completion_date():
    """journey_completion_date = simulation_date of the completion day."""
    je = _make_je(duration_a=1, duration_b=1)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    completion_day = SIM_DATE + timedelta(days=1)
    result = _advance_n(je, df, SIM_DATE, n=2)

    assert result.loc[0, "journey_completion_date"] == completion_day


def test_journey_completion_sets_cooling_period_end():
    """cooling_period_end = completion_date + config.cooling_period_days."""
    cooling_days = 30
    je = _make_je(duration_a=1, duration_b=1, cooling_days=cooling_days)
    config = make_config(cooling_period_days=cooling_days)
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    completion_day = SIM_DATE + timedelta(days=1)
    expected_cooling_end = completion_day + timedelta(days=cooling_days)

    result = _advance_n(je, df, SIM_DATE, n=2)

    assert result.loc[0, "cooling_period_end"] == expected_cooling_end


def test_journey_completion_clears_ad_fields():
    """current_ad, days_in_ad, channel, vendor are None after journey completion."""
    je = _make_je(duration_a=1, duration_b=1)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    result = _advance_n(je, df, SIM_DATE, n=2)

    assert pd.isna(result.loc[0, "current_ad"])
    assert pd.isna(result.loc[0, "days_in_ad"])
    assert pd.isna(result.loc[0, "channel"])
    assert pd.isna(result.loc[0, "vendor"])


def test_cooling_period_days_zero():
    """cooling_period_days=0: cooling_period_end equals journey_completion_date."""
    je = _make_je(duration_a=1, duration_b=1, cooling_days=0)
    config = make_config(cooling_period_days=0)
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    result = _advance_n(je, df, SIM_DATE, n=2)
    completion_day = SIM_DATE + timedelta(days=1)

    assert result.loc[0, "cooling_period_end"] == completion_day
    assert result.loc[0, "journey_completion_date"] == completion_day


def test_single_ad_journey_completion():
    """Single-ad journey: user completes immediately after duration_days."""
    je = _make_je(duration_a=2, n_ads=1)
    config = make_config(
        ads=(AdConfig("Ad_A", 1, 2, False, "Display", None, 0.10),)
    )
    je2 = JourneyEngine(config)
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    result = _advance_n(je2, df, SIM_DATE, n=2)

    assert result.loc[0, "journey_status"] == JourneyStatus.COMPLETED.value


def test_click_completes_last_ad():
    """Click advance on the last ad completes the journey."""
    config = make_config(
        ads=(
            AdConfig("Ad_A", 1, 1, False, "Display", None, 0.10),
            AdConfig("Ad_B", 2, 10, True, "Email", None, 0.05),
        )
    )
    je = JourneyEngine(config)
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # Day 1: enter Ad_A (duration=1) -> advance to Ad_B
    r = je.advance(df, SIM_DATE)
    assert r.loc[0, "current_ad"] == "Ad_B"

    # Day 2: click on Ad_B (move_on_click=True) -> complete journey
    r["ad_click_received"] = True
    r = je.advance(r, SIM_DATE + timedelta(1))

    assert r.loc[0, "journey_status"] == JourneyStatus.COMPLETED.value
    assert r.loc[0, "journey_completion_date"] == SIM_DATE + timedelta(1)


# ===========================================================================
# 8. Re-entry handling (C-004)
# ===========================================================================

def test_reentry_user_restarts_at_ad1():
    """RE_ENTRY user: journey restarts from Ad1 (C-004)."""
    je = _make_je(duration_a=3, duration_b=2)
    config = make_config()
    df = make_state_df(n=1, config=config)

    # Simulate user who previously completed a journey
    df["eligibility_status"] = EligibilityStatus.RE_ENTRY.value
    df["journey_status"] = JourneyStatus.COMPLETED.value
    df["journey_completion_date"] = SIM_DATE - timedelta(days=20)
    df["cooling_period_end"] = SIM_DATE - timedelta(days=6)  # expired

    result = je.advance(df, SIM_DATE)

    assert result.loc[0, "current_ad"] == "Ad_A"
    assert result.loc[0, "journey_status"] == JourneyStatus.ACTIVE.value


def test_reentry_preserves_prior_journey_completion_date():
    """C-004: RE_ENTRY restart does NOT clear prior journey_completion_date."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=1, config=config)

    prior_completion = SIM_DATE - timedelta(days=20)
    df["eligibility_status"] = EligibilityStatus.RE_ENTRY.value
    df["journey_status"] = JourneyStatus.COMPLETED.value
    df["journey_completion_date"] = prior_completion
    df["cooling_period_end"] = SIM_DATE - timedelta(days=6)

    result = je.advance(df, SIM_DATE)

    # Prior completion date must be preserved for TER/TCC calculations
    assert result.loc[0, "journey_completion_date"] == prior_completion


def test_reentry_sets_new_journey_start_date():
    """RE_ENTRY: journey_start_date is reset to simulation_date of re-entry."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=1, config=config)

    df["eligibility_status"] = EligibilityStatus.RE_ENTRY.value
    df["journey_status"] = JourneyStatus.COMPLETED.value
    df["journey_completion_date"] = SIM_DATE - timedelta(20)
    df["cooling_period_end"] = SIM_DATE - timedelta(6)

    result = je.advance(df, SIM_DATE)

    assert result.loc[0, "journey_start_date"] == SIM_DATE


def test_reentry_full_cycle():
    """RE_ENTRY user completes a new journey leg and gets a new cooling period."""
    cooling_days = 14
    je = _make_je(duration_a=1, duration_b=1, cooling_days=cooling_days)
    config = make_config(cooling_period_days=cooling_days)
    df = make_state_df(n=1, config=config)

    # Simulate prior completion
    prior_completion = SIM_DATE - timedelta(20)
    df["eligibility_status"] = EligibilityStatus.RE_ENTRY.value
    df["journey_status"] = JourneyStatus.COMPLETED.value
    df["journey_completion_date"] = prior_completion
    df["cooling_period_end"] = SIM_DATE - timedelta(6)

    # Re-enter and complete the new journey leg (2 days: Ad_A + Ad_B)
    result = _advance_n(je, df, SIM_DATE, n=2)

    new_completion = SIM_DATE + timedelta(1)
    assert result.loc[0, "journey_status"] == JourneyStatus.COMPLETED.value
    assert result.loc[0, "journey_completion_date"] == new_completion
    assert result.loc[0, "cooling_period_end"] == new_completion + timedelta(cooling_days)


# ===========================================================================
# 9. Journey state persistence
# ===========================================================================

def test_journey_state_preserved_between_calls():
    """days_in_ad persists correctly across multiple advance() calls."""
    je = _make_je(duration_a=5)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    states = []
    cur = df.copy()
    for i in range(4):
        cur = je.advance(cur, SIM_DATE + timedelta(days=i))
        states.append(int(cur.loc[0, "days_in_ad"]))

    assert states == [1, 2, 3, 4]


def test_immutability_of_input_df():
    """advance() does not mutate the input state_df."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=2, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value
    original_journey = df["journey_status"].copy()

    je.advance(df, SIM_DATE)

    pd.testing.assert_series_equal(df["journey_status"], original_journey)


def test_ad_click_received_reset_after_advance():
    """ad_click_received is always reset to False at end of each advance()."""
    je = _make_je(duration_a=10, move_on_click_a=True)
    config = make_config()
    df = make_state_df(n=2, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    df["ad_click_received"] = True
    result = je.advance(df, SIM_DATE)

    assert (result["ad_click_received"] == False).all()


# ===========================================================================
# 10. Multi-user vectorized correctness
# ===========================================================================

def test_mixed_user_states_processed_independently():
    """NEW, ACTIVE, COOLING, SKIPPED users each receive correct treatment."""
    je = _make_je(duration_a=3, duration_b=2)
    config = make_config()
    df = make_state_df(n=4, config=config)

    # User 0: NEW
    df.loc[0, "eligibility_status"] = EligibilityStatus.NEW.value
    df.loc[0, "journey_status"] = JourneyStatus.NOT_STARTED.value

    # User 1: ACTIVE (already in journey on Ad_A day 2)
    df.loc[1, "eligibility_status"] = EligibilityStatus.ACTIVE.value
    df.loc[1, "journey_status"] = JourneyStatus.ACTIVE.value
    df.loc[1, "current_ad"] = "Ad_A"
    df.loc[1, "days_in_ad"] = 2

    # User 2: COOLING
    df.loc[2, "eligibility_status"] = EligibilityStatus.COOLING.value
    df.loc[2, "journey_status"] = JourneyStatus.COMPLETED.value
    df.loc[2, "cooling_period_end"] = SIM_DATE + timedelta(5)
    df.loc[2, "current_ad"] = None

    # User 3: SKIPPED
    df.loc[3, "eligibility_status"] = EligibilityStatus.SKIPPED.value
    df.loc[3, "journey_status"] = JourneyStatus.NOT_STARTED.value

    result = je.advance(df, SIM_DATE)

    # User 0: started journey
    assert result.loc[0, "current_ad"] == "Ad_A"
    assert result.loc[0, "journey_status"] == JourneyStatus.ACTIVE.value

    # User 1: days_in_ad 2+1=3 >= duration 3 → advances to Ad_B
    assert result.loc[1, "current_ad"] == "Ad_B"
    assert int(result.loc[1, "days_in_ad"]) == 0

    # User 2: unchanged (COOLING)
    assert result.loc[2, "journey_status"] == JourneyStatus.COMPLETED.value
    assert pd.isna(result.loc[2, "current_ad"])

    # User 3: unchanged (SKIPPED)
    assert result.loc[3, "journey_status"] == JourneyStatus.NOT_STARTED.value


def test_active_user_duration_advance():
    """ACTIVE user (from prior day) advances correctly via duration."""
    je = _make_je(duration_a=3)
    config = make_config()
    df = make_state_df(n=1, config=config)

    # Simulate user already at day 2 on Ad_A
    df.loc[0, "eligibility_status"] = EligibilityStatus.ACTIVE.value
    df.loc[0, "journey_status"] = JourneyStatus.ACTIVE.value
    df.loc[0, "current_ad"] = "Ad_A"
    df.loc[0, "days_in_ad"] = 2

    result = je.advance(df, SIM_DATE)

    # day 2+1=3 >= duration 3 -> advance to Ad_B
    assert result.loc[0, "current_ad"] == "Ad_B"


def test_multiple_users_advance_independently():
    """Two users on different ads advance independently per their own durations."""
    config = make_config(
        ads=(
            AdConfig("Ad_A", 1, 2, False, "Display", None, 0.10),
            AdConfig("Ad_B", 2, 3, False, "Email", None, 0.05),
        )
    )
    je = JourneyEngine(config)
    df = make_state_df(n=2, config=config)

    # User 0: on Ad_A, day 1 -> needs 1 more day to advance
    df.loc[0, "eligibility_status"] = EligibilityStatus.ACTIVE.value
    df.loc[0, "journey_status"] = JourneyStatus.ACTIVE.value
    df.loc[0, "current_ad"] = "Ad_A"
    df.loc[0, "days_in_ad"] = 1

    # User 1: on Ad_B, day 2 -> needs 1 more day to complete
    df.loc[1, "eligibility_status"] = EligibilityStatus.ACTIVE.value
    df.loc[1, "journey_status"] = JourneyStatus.ACTIVE.value
    df.loc[1, "current_ad"] = "Ad_B"
    df.loc[1, "days_in_ad"] = 2

    result = je.advance(df, SIM_DATE)

    # User 0: 1+1=2 >= 2 -> advance to Ad_B
    assert result.loc[0, "current_ad"] == "Ad_B"

    # User 1: 2+1=3 >= 3 -> complete journey
    assert result.loc[1, "journey_status"] == JourneyStatus.COMPLETED.value


# ===========================================================================
# 11. Multi-week simulation
# ===========================================================================

def test_multi_week_simulation_full_journey():
    """User completes full journey over 7 days across week boundary."""
    je = _make_je(duration_a=4, duration_b=3, cooling_days=14)
    config = make_config(cooling_period_days=14)
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # Run for 7 days
    result = _advance_n(je, df, SIM_DATE, n=7)

    assert result.loc[0, "journey_status"] == JourneyStatus.COMPLETED.value
    completion_day = SIM_DATE + timedelta(days=6)
    assert result.loc[0, "journey_completion_date"] == completion_day
    assert result.loc[0, "cooling_period_end"] == completion_day + timedelta(14)


def test_multi_week_state_continuity():
    """Journey state is preserved correctly when advance() called daily for 3 weeks."""
    je = _make_je(duration_a=14, duration_b=7, cooling_days=7)
    config = make_config(cooling_period_days=7)
    df = make_state_df(n=2, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    result = _advance_n(je, df, SIM_DATE, n=21)

    # Both users complete (14 + 7 = 21 days)
    assert (result["journey_status"] == JourneyStatus.COMPLETED.value).all()


def test_daily_days_in_ad_increments_are_monotone():
    """days_in_ad increments by exactly 1 per day while on the same ad."""
    je = _make_je(duration_a=10)
    config = make_config()
    df = make_state_df(n=1, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    cur = df.copy()
    prev_days = 0
    for i in range(5):
        cur = je.advance(cur, SIM_DATE + timedelta(i))
        new_days = int(cur.loc[0, "days_in_ad"])
        assert new_days == prev_days + 1
        prev_days = new_days


# ===========================================================================
# 12. Historical state continuity
# ===========================================================================

def test_returning_user_with_prior_state_continues_journey():
    """User who was mid-journey in a prior run continues from where they left off."""
    je = _make_je(duration_a=5, duration_b=5)
    config = make_config()
    df = make_state_df(n=1, config=config)

    # Simulate prior-run state: 3 days into Ad_A
    df.loc[0, "eligibility_status"] = EligibilityStatus.ACTIVE.value
    df.loc[0, "journey_status"] = JourneyStatus.ACTIVE.value
    df.loc[0, "current_ad"] = "Ad_A"
    df.loc[0, "days_in_ad"] = 3
    df.loc[0, "journey_start_date"] = SIM_DATE - timedelta(3)

    # 2 more days: days_in_ad goes 4, then 5 -> advance to Ad_B; entry = 0
    result = _advance_n(je, df, SIM_DATE, n=2)

    assert result.loc[0, "current_ad"] == "Ad_B"
    assert int(result.loc[0, "days_in_ad"]) == 0


def test_journey_start_date_preserved_for_active_user():
    """journey_start_date is NOT overwritten for already-Active users."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=1, config=config)

    original_start = SIM_DATE - timedelta(5)
    df.loc[0, "eligibility_status"] = EligibilityStatus.ACTIVE.value
    df.loc[0, "journey_status"] = JourneyStatus.ACTIVE.value
    df.loc[0, "current_ad"] = "Ad_A"
    df.loc[0, "days_in_ad"] = 2
    df.loc[0, "journey_start_date"] = original_start

    result = je.advance(df, SIM_DATE)

    assert result.loc[0, "journey_start_date"] == original_start


# ===========================================================================
# 13. get_journey_summary
# ===========================================================================

def test_get_journey_summary_empty():
    """get_journey_summary on empty DataFrame returns all-zero dict."""
    je = _make_je()
    config = make_config()
    df = make_state_df(n=0, config=config)
    summary = je.get_journey_summary(df)
    assert summary["total_users"] == 0
    assert summary["active"] == 0


def test_get_journey_summary_counts():
    """get_journey_summary returns correct counts by journey_status."""
    je = _make_je(duration_a=1, duration_b=1)
    config = make_config()
    df = make_state_df(n=3, config=config)
    df["eligibility_status"] = EligibilityStatus.NEW.value

    # Advance for 2 days: all 3 users complete
    result = _advance_n(je, df, SIM_DATE, n=2)
    summary = je.get_journey_summary(result)

    assert summary["total_users"] == 3
    assert summary["completed"] == 3
    assert summary["active"] == 0


# ===========================================================================
# 14. Wave 1 integration -- audience_manager -> journey_engine
# ===========================================================================

def test_wave_1_integration_audience_then_journey():
    """Integration: AudienceManager output feeds directly into JourneyEngine."""
    from core.audience_manager import AudienceManager

    config = make_config()
    from tests.test_core.conftest import make_trigger_df
    trigger_df = make_trigger_df(n=3, campaign_id="TEST_CAMPAIGN")
    state_df = make_state_df(n=3, config=config)

    # Stage 4: AudienceManager
    am = AudienceManager(config)
    audience_state, _ = am.resolve(trigger_df, None, state_df, SIM_DATE)

    # Stage 5: JourneyEngine
    je = JourneyEngine(config)
    journey_state = je.advance(audience_state, SIM_DATE)

    # All eligible users should now be in an active journey
    eligible = journey_state[
        journey_state["eligibility_status"].isin([
            EligibilityStatus.NEW.value,
            EligibilityStatus.ACTIVE.value,
            EligibilityStatus.RE_ENTRY.value,
        ])
    ]
    assert (eligible["journey_status"] == JourneyStatus.ACTIVE.value).all()
    assert eligible["current_ad"].notna().all()


# ===========================================================================
# 15. Compliance tests
# ===========================================================================

def test_no_iterrows_in_journey_engine():
    """ARCH-011 compliance: iterrows() must not appear in journey_engine.py source."""
    import importlib.util
    spec = importlib.util.find_spec("core.journey_engine")
    with open(spec.origin) as f:
        content = f.read()
    bad_lines = [
        f"line {i+1}: {line.rstrip()}"
        for i, line in enumerate(content.splitlines())
        if ".iterrows(" in line
    ]
    assert len(bad_lines) == 0, (
        f"journey_engine.py contains .iterrows() call -- ARCH-011 violation: {bad_lines}"
    )


def test_no_inline_pipe_literal_in_journey_engine():
    """ARCH-017 compliance: no inline '|' string literals in journey_engine.py."""
    import importlib.util
    spec = importlib.util.find_spec("core.journey_engine")
    with open(spec.origin) as f:
        content = f.read()
    # Allow the pipe character in comments and docstrings but not as a bare literal
    # Check that the forbidden pattern "|" (pipe as string literal) does not appear
    import re
    # Detect patterns like = "|" or .split("|") or f"...{|}..." etc.
    forbidden = re.findall(r'(?<!["\'])"\|"(?!["\'])', content)
    assert len(forbidden) == 0, (
        f"journey_engine.py contains inline pipe literal -- ARCH-017 violation: {forbidden}"
    )


def test_no_todo_fixme_hack_in_journey_engine():
    """Code quality: no TODO/FIXME/HACK in journey_engine.py source."""
    import importlib.util
    spec = importlib.util.find_spec("core.journey_engine")
    with open(spec.origin) as f:
        content = f.read()
    for marker in ("TODO", "FIXME", "HACK"):
        assert marker not in content, (
            f"journey_engine.py contains '{marker}' comment"
        )
