"""Unit tests for core/audience_manager.py — Wave 1 Step 2.

Covers all 33 required test cases from PHASE_3_WAVE_1_BUILD_CONTRACT.md §4.4,
plus additional edge cases and the Wave 1 integration test from §4.6.

Test numbering matches §4.4 table where applicable.
"""
from __future__ import annotations

import logging
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from core.audience_manager import AudienceManager
from core.user_state_manager import UserStateManager
from models.capacity_row import RemainingCapacityRow
from models.enums import EligibilityStatus, JourneyStatus
from utils.constants import TRIGGER_HISTORY_DELIMITER
from utils.exceptions import InputValidationError

from tests.test_core.conftest import make_config, make_state_df, make_trigger_df


# ===========================================================================
# Helpers
# ===========================================================================

def _make_mgr(**config_kwargs) -> AudienceManager:
    return AudienceManager(make_config(**config_kwargs))


def _make_state_with_journey(journey_status: str, n: int = 3, **config_kwargs) -> pd.DataFrame:
    """Return a state_df with all users set to the given journey_status."""
    config = make_config(**config_kwargs)
    df = make_state_df(n=n, config=config)
    df = df.copy()
    df["journey_status"] = journey_status
    return df


def _make_state_with_cooling(
    cooling_end: date,
    n: int = 3,
    **config_kwargs,
) -> pd.DataFrame:
    """Return a state_df with cooling_period_end set to cooling_end for all users."""
    config = make_config(**config_kwargs)
    df = make_state_df(n=n, config=config)
    df = df.copy()
    df["cooling_period_end"] = cooling_end
    return df


def _make_trigger_df_with_priority(rows: list[dict]) -> pd.DataFrame:
    """Build a trigger DataFrame that already has a _priority column (for apply_tiebreak_sort tests)."""
    return pd.DataFrame(rows)


AS_OF = date(2024, 2, 1)


# ===========================================================================
# §4.4 Test 1 — classify_eligibility: NOT_STARTED → New
# ===========================================================================

def test_classify_eligibility_new_users():
    """journey_status=Not_Started → eligibility_status='New' (ARCH-015)."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = make_state_df(n=3, config=config)
    # All new users default to NOT_STARTED
    result = mgr.classify_eligibility(state_df, AS_OF)
    assert (result["eligibility_status"] == EligibilityStatus.NEW.value).all()


# ===========================================================================
# §4.4 Test 2 — classify_eligibility: ACTIVE journey → Active
# ===========================================================================

def test_classify_eligibility_active_users():
    """journey_status=Active → eligibility_status='Active'."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = _make_state_with_journey(JourneyStatus.ACTIVE.value)
    result = mgr.classify_eligibility(state_df, AS_OF)
    assert (result["eligibility_status"] == EligibilityStatus.ACTIVE.value).all()


# ===========================================================================
# §4.4 Test 3 — classify_eligibility: cooling active → Cooling
# ===========================================================================

def test_classify_eligibility_cooling_users():
    """cooling_period_end > as_of_date → eligibility_status='Cooling'."""
    config = make_config(allow_reentry=True)
    mgr = AudienceManager(config)
    future_end = AS_OF + timedelta(days=7)
    state_df = _make_state_with_cooling(future_end, allow_reentry=True)
    result = mgr.classify_eligibility(state_df, AS_OF)
    assert (result["eligibility_status"] == EligibilityStatus.COOLING.value).all()


# ===========================================================================
# §4.4 Test 4 — classify_eligibility: cooling expired + allow_reentry=True → Re_Entry
# ===========================================================================

def test_classify_eligibility_reentry_when_allow_reentry_true():
    """Cooling expired + allow_reentry=True → eligibility_status='Re_Entry' (ARCH-020)."""
    config = make_config(allow_reentry=True)
    mgr = AudienceManager(config)
    past_end = AS_OF - timedelta(days=1)
    state_df = _make_state_with_cooling(past_end, allow_reentry=True)
    result = mgr.classify_eligibility(state_df, AS_OF)
    assert (result["eligibility_status"] == EligibilityStatus.RE_ENTRY.value).all()


# ===========================================================================
# §4.4 Test 5 — classify_eligibility: cooling expired + allow_reentry=False → Excluded
# ===========================================================================

def test_classify_eligibility_excluded_when_allow_reentry_false():
    """Cooling expired + allow_reentry=False → eligibility_status='Excluded' (ARCH-020)."""
    config = make_config(allow_reentry=False)
    mgr = AudienceManager(config)
    past_end = AS_OF - timedelta(days=1)
    state_df = _make_state_with_cooling(past_end, allow_reentry=False)
    result = mgr.classify_eligibility(state_df, AS_OF)
    assert (result["eligibility_status"] == EligibilityStatus.EXCLUDED.value).all()


# ===========================================================================
# §4.4 Test 6 — classify_eligibility: DROPPED → Excluded (ARCH-018)
# ===========================================================================

def test_classify_eligibility_dropped_maps_to_excluded():
    """journey_status=Dropped → eligibility_status='Excluded' (ARCH-018)."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = _make_state_with_journey(JourneyStatus.DROPPED.value)
    result = mgr.classify_eligibility(state_df, AS_OF)
    assert (result["eligibility_status"] == EligibilityStatus.EXCLUDED.value).all()


# ===========================================================================
# §4.4 Test 7 — classify_eligibility: DROPPED beats cooling (ARCH-018 highest priority)
# ===========================================================================

def test_classify_eligibility_dropped_beats_cooling():
    """User with DROPPED journey AND active cooling → EXCLUDED, not COOLING (ARCH-018)."""
    config = make_config(allow_reentry=True)
    mgr = AudienceManager(config)
    future_end = AS_OF + timedelta(days=10)
    state_df = _make_state_with_journey(JourneyStatus.DROPPED.value, allow_reentry=True)
    state_df = state_df.copy()
    state_df["cooling_period_end"] = future_end
    result = mgr.classify_eligibility(state_df, AS_OF)
    # Condition 1 (DROPPED→EXCLUDED) beats Condition 2 (cooling→COOLING)
    assert (result["eligibility_status"] == EligibilityStatus.EXCLUDED.value).all()


# ===========================================================================
# §4.4 Test 8 — classify_eligibility: default → Skipped
# ===========================================================================

def test_classify_eligibility_default_maps_to_skipped():
    """Completed journey (no cooling) → eligibility_status='Skipped' (np.select default)."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = _make_state_with_journey(JourneyStatus.COMPLETED.value)
    # COMPLETED with no cooling_period_end — falls to default
    result = mgr.classify_eligibility(state_df, AS_OF)
    assert (result["eligibility_status"] == EligibilityStatus.SKIPPED.value).all()


# ===========================================================================
# §4.4 Test 9 — RE_ENTRY value uses underscore (ARCH-015)
# ===========================================================================

def test_classify_eligibility_reentry_value_has_underscore():
    """eligibility_status == 'Re_Entry' (underscore, not hyphen) (ARCH-015)."""
    config = make_config(allow_reentry=True)
    mgr = AudienceManager(config)
    past_end = AS_OF - timedelta(days=3)
    state_df = _make_state_with_cooling(past_end, allow_reentry=True)
    result = mgr.classify_eligibility(state_df, AS_OF)
    val = str(result["eligibility_status"].iloc[0])
    assert val == "Re_Entry", f"Expected 'Re_Entry' got {val!r}"
    assert "-" not in val, "RE_ENTRY must use underscore, not hyphen"


# ===========================================================================
# §4.4 Test 10 — tiebreak: lower _priority number wins (ARCH-013)
# ===========================================================================

def test_tiebreak_sort_lower_priority_wins():
    """Priority 1 beats priority 2 — lower number = higher priority (ARCH-013)."""
    mgr = _make_mgr()
    trigger_df = _make_trigger_df_with_priority([
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U001",
         "Trigger_Name": "T1", "Segment": "S1", "_priority": 2},
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U001",
         "Trigger_Name": "T_Priority1", "Segment": "S1", "_priority": 1},
    ])
    result = mgr.apply_tiebreak_sort(trigger_df)
    assert len(result) == 1
    assert result.iloc[0]["Trigger_Name"] == "T_Priority1"


# ===========================================================================
# §4.4 Test 11 — tiebreak: alphabetical Trigger_Name on priority tie (ARCH-013)
# ===========================================================================

def test_tiebreak_sort_alphabetical_on_tie():
    """Equal priority → alphabetically first Trigger_Name wins (ARCH-013)."""
    mgr = _make_mgr()
    trigger_df = _make_trigger_df_with_priority([
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U001",
         "Trigger_Name": "Trigger_Z", "Segment": "S1", "_priority": 1},
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U001",
         "Trigger_Name": "Trigger_A", "Segment": "S1", "_priority": 1},
    ])
    result = mgr.apply_tiebreak_sort(trigger_df)
    assert len(result) == 1
    assert result.iloc[0]["Trigger_Name"] == "Trigger_A"


# ===========================================================================
# §4.4 Test 12 — tiebreak: Segment tiebreak when priority AND name equal (ARCH-014)
# ===========================================================================

def test_tiebreak_sort_segment_on_trigger_name_tie():
    """Priority AND Trigger_Name equal → alphabetically first Segment wins (ARCH-014)."""
    mgr = _make_mgr()
    trigger_df = _make_trigger_df_with_priority([
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U001",
         "Trigger_Name": "T1", "Segment": "Segment_Z", "_priority": 1},
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U001",
         "Trigger_Name": "T1", "Segment": "Segment_A", "_priority": 1},
    ])
    result = mgr.apply_tiebreak_sort(trigger_df)
    assert len(result) == 1
    assert result.iloc[0]["Segment"] == "Segment_A"


# ===========================================================================
# §4.4 Test 13 — segment follows WINNING trigger, not alphabetical segment alone
# ===========================================================================

def test_segment_follows_winning_trigger_not_alphabet():
    """Segment comes from the priority-winner row, not alphabetically (ARCH-014)."""
    mgr = _make_mgr()
    # T_Z has priority 1 (winner) with Segment "Z_Seg"
    # T_A has priority 2 (loser) with Segment "A_Seg"
    # After resolution: winner is T_Z; segment should be "Z_Seg" (from winner),
    # NOT "A_Seg" (which is alphabetically first but comes from the loser)
    trigger_df = _make_trigger_df_with_priority([
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U001",
         "Trigger_Name": "T_Z", "Segment": "Z_Seg", "_priority": 1},
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U001",
         "Trigger_Name": "T_A", "Segment": "A_Seg", "_priority": 2},
    ])
    result = mgr.apply_tiebreak_sort(trigger_df)
    assert len(result) == 1
    assert result.iloc[0]["Trigger_Name"] == "T_Z"
    assert result.iloc[0]["Segment"] == "Z_Seg"


# ===========================================================================
# §4.4 Test 14 — tiebreak removes duplicate (Campaign_ID, User_ID) pairs
# ===========================================================================

def test_tiebreak_removes_duplicate_campaign_user_pairs():
    """apply_tiebreak_sort returns exactly one row per (Campaign_ID, User_ID)."""
    mgr = _make_mgr()
    trigger_df = _make_trigger_df_with_priority([
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U001",
         "Trigger_Name": "T1", "Segment": "S1", "_priority": 1},
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U001",
         "Trigger_Name": "T2", "Segment": "S2", "_priority": 2},
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U002",
         "Trigger_Name": "T1", "Segment": "S1", "_priority": 1},
        {"Campaign_ID": "TEST_CAMPAIGN", "User_ID": "U002",
         "Trigger_Name": "T2", "Segment": "S2", "_priority": 2},
    ])
    result = mgr.apply_tiebreak_sort(trigger_df)
    assert len(result) == 2
    assert result.duplicated(subset=["Campaign_ID", "User_ID"]).sum() == 0


# ===========================================================================
# §4.4 Test 15 — tiebreak emits WARNING log (AUD-V-005)
# ===========================================================================

def test_tiebreak_emits_warning_log(caplog):
    """ARCH-013 tiebreak fires a WARNING log when equal-priority triggers exist."""
    from models.trigger_config import TriggerConfig
    # Config with two equal-priority triggers
    from tests.test_core.conftest import make_config as _mc
    from models.ad_config import AdConfig
    from models.config_registry import ConfigRegistry
    from models.enums import HistoricalWindow, RuleSeverity
    from models.rule_config import RuleConfig

    triggers = (
        TriggerConfig(trigger_name="Alpha_T", priority=1, engagement_rate_target=0.20),
        TriggerConfig(trigger_name="Beta_T", priority=1, engagement_rate_target=0.20),
    )
    config = make_config(triggers=triggers)
    mgr = AudienceManager(config)
    state_df = make_state_df(n=1, config=config)

    trigger_df = pd.DataFrame({
        "Campaign_ID": ["TEST_CAMPAIGN", "TEST_CAMPAIGN"],
        "User_ID": ["U001", "U001"],
        "Trigger_Name": ["Beta_T", "Alpha_T"],
        "Segment": ["S1", "S1"],
        "Trigger_Date": [date(2024, 1, 1), date(2024, 1, 1)],
    })

    with caplog.at_level(logging.WARNING, logger="core.audience_manager"):
        mgr.resolve(trigger_df, None, state_df, AS_OF)

    warning_msgs = [r.message for r in caplog.records if r.levelname == "WARNING"]
    tiebreak_msgs = [m for m in warning_msgs if "ARCH-013 tiebreak" in m]
    assert len(tiebreak_msgs) >= 1, f"Expected ARCH-013 tiebreak WARNING; got: {warning_msgs}"


# ===========================================================================
# §4.4 Test 16 — compute_remaining_capacity formula correctness
# ===========================================================================

def test_compute_remaining_capacity_formula():
    """remaining_capacity == max(0, math.ceil(n * rate) - historical)."""
    from models.trigger_config import TriggerConfig
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.25),
    )
    config = make_config(triggers=triggers)
    mgr = AudienceManager(config)

    # 4 users, rate=0.25 → target=ceil(4*0.25)=1, historical=0 → remaining=1
    trigger_df = make_trigger_df(n=4, trigger_name="T1")
    capacity = mgr.compute_remaining_capacity(None, trigger_df)

    assert len(capacity) == 1
    assert capacity[0].total_users == 4
    assert capacity[0].target_engaged_users == math.ceil(4 * 0.25)
    assert capacity[0].historical_engaged_users == 0
    assert capacity[0].remaining_capacity == max(0, math.ceil(4 * 0.25) - 0)


# ===========================================================================
# §4.4 Test 17 — compute_remaining_capacity uses math.ceil not int
# ===========================================================================

def test_compute_remaining_capacity_uses_math_ceil_not_int():
    """math.ceil(5 * 0.3) = 2, not 1 — ceil differs from int/floor (TCC-001)."""
    from models.trigger_config import TriggerConfig
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.30),
    )
    config = make_config(triggers=triggers)
    mgr = AudienceManager(config)

    # 5 users × 0.3 = 1.5 → ceil = 2, int = 1
    trigger_df = make_trigger_df(n=5, trigger_name="T1")
    capacity = mgr.compute_remaining_capacity(None, trigger_df)

    assert capacity[0].target_engaged_users == 2, (
        f"Expected ceil(5*0.3)=2, got {capacity[0].target_engaged_users}"
    )
    assert capacity[0].target_engaged_users != 1, "int() would return 1 — must use math.ceil()"


# ===========================================================================
# §4.4 Test 18 — compute_remaining_capacity never negative
# ===========================================================================

def test_compute_remaining_capacity_never_negative():
    """remaining_capacity == max(0, ...) — never negative even when historical > target."""
    from models.trigger_config import TriggerConfig
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.10),
    )
    config = make_config(triggers=triggers)
    mgr = AudienceManager(config)

    # 5 users × 0.10 → target = 1
    trigger_df = make_trigger_df(n=5, trigger_name="T1")

    # Historical has 10 users already engaged (more than target)
    historical_df = pd.DataFrame({
        "User_ID": [f"H{i}" for i in range(10)],
        "Date": [date(2024, 1, 1)] * 10,
        "Action": ["Click"] * 10,
        "Channel": ["Email"] * 10,
        "Trigger_Name": ["T1"] * 10,
    })
    capacity = mgr.compute_remaining_capacity(historical_df, trigger_df)

    assert capacity[0].remaining_capacity >= 0, (
        f"remaining_capacity must be >= 0, got {capacity[0].remaining_capacity}"
    )
    assert capacity[0].remaining_capacity == 0


# ===========================================================================
# §4.4 Test 19 — compute_remaining_capacity subtracts historical engaged users
# ===========================================================================

def test_compute_remaining_capacity_subtracts_historical_engaged():
    """historical_engaged_users counted from historical_df for this trigger."""
    from models.trigger_config import TriggerConfig
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.50),
    )
    config = make_config(triggers=triggers)
    mgr = AudienceManager(config)

    # 10 users × 0.5 → target = 5
    trigger_df = make_trigger_df(n=10, trigger_name="T1")

    # 3 users historically engaged for T1
    historical_df = pd.DataFrame({
        "User_ID": ["H001", "H002", "H003"],
        "Date": [date(2024, 1, 1)] * 3,
        "Action": ["Click"] * 3,
        "Channel": ["Email"] * 3,
        "Trigger_Name": ["T1"] * 3,
    })
    capacity = mgr.compute_remaining_capacity(historical_df, trigger_df)

    assert capacity[0].historical_engaged_users == 3
    assert capacity[0].target_engaged_users == 5
    assert capacity[0].remaining_capacity == 2  # 5 - 3


# ===========================================================================
# §4.4 Test 20 — compute_remaining_capacity: historical_df=None → 0
# ===========================================================================

def test_compute_remaining_capacity_none_historical_df():
    """historical_engaged_users = 0 when historical_df=None."""
    from models.trigger_config import TriggerConfig
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.20),
    )
    config = make_config(triggers=triggers)
    mgr = AudienceManager(config)

    trigger_df = make_trigger_df(n=5, trigger_name="T1")
    capacity = mgr.compute_remaining_capacity(None, trigger_df)

    assert capacity[0].historical_engaged_users == 0
    assert capacity[0].remaining_capacity == capacity[0].target_engaged_users


# ===========================================================================
# §4.4 Test 21 — apply_capacity_cap marks excess users SKIPPED
# ===========================================================================

def test_apply_capacity_cap_marks_excess_users_skipped():
    """Users beyond per-trigger remaining_capacity are reclassified SKIPPED."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = make_state_df(n=4, config=config)
    # Classify all as NEW first
    state_df = mgr.classify_eligibility(state_df, AS_OF)
    assert (state_df["eligibility_status"] == EligibilityStatus.NEW.value).all()

    # Assign trigger_name to all users
    state_df = state_df.copy()
    state_df["trigger_name"] = "T1"

    # Capacity = 2 for T1
    from models.trigger_config import TriggerConfig
    cap = RemainingCapacityRow(
        total_users=4,
        target_engagement_rate=0.50,
        historical_engaged_users=0,
        target_engaged_users=2,
        remaining_capacity=2,
    )
    result = mgr.apply_capacity_cap(state_df, [cap])

    n_skipped = int((result["eligibility_status"] == EligibilityStatus.SKIPPED.value).sum())
    n_new = int((result["eligibility_status"] == EligibilityStatus.NEW.value).sum())
    assert n_new == 2
    assert n_skipped == 2


# ===========================================================================
# §4.4 Test 22 — apply_capacity_cap: zero capacity marks all eligible SKIPPED
# ===========================================================================

def test_apply_capacity_cap_zero_capacity_marks_all_eligible_skipped():
    """remaining_capacity=0 → all NEW/ACTIVE/RE_ENTRY users become SKIPPED."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = make_state_df(n=3, config=config)
    state_df = mgr.classify_eligibility(state_df, AS_OF)
    state_df = state_df.copy()
    state_df["trigger_name"] = "T1"

    cap = RemainingCapacityRow(
        total_users=3,
        target_engagement_rate=0.0,
        historical_engaged_users=0,
        target_engaged_users=0,
        remaining_capacity=0,
    )
    result = mgr.apply_capacity_cap(state_df, [cap])

    assert (result["eligibility_status"] == EligibilityStatus.SKIPPED.value).all(), (
        f"All should be SKIPPED, got: {result['eligibility_status'].value_counts().to_dict()}"
    )


# ===========================================================================
# §4.4 Test 23 — apply_capacity_cap preserves COOLING and EXCLUDED
# ===========================================================================

def test_apply_capacity_cap_preserves_cooling_and_excluded():
    """COOLING and EXCLUDED users are not reclassified by capacity cap."""
    config = make_config(allow_reentry=True)
    mgr = AudienceManager(config)
    state_df = make_state_df(n=4, config=config)
    state_df = state_df.copy()

    # User 0: NEW, User 1: COOLING, User 2: EXCLUDED, User 3: NEW
    state_df["journey_status"] = [
        JourneyStatus.NOT_STARTED.value,
        JourneyStatus.NOT_STARTED.value,
        JourneyStatus.DROPPED.value,
        JourneyStatus.NOT_STARTED.value,
    ]
    future_end = AS_OF + timedelta(days=5)
    state_df.loc[1, "cooling_period_end"] = future_end

    state_df = mgr.classify_eligibility(state_df, AS_OF)
    state_df = state_df.copy()
    state_df["trigger_name"] = "T1"

    # Zero capacity — would mark all eligible SKIPPED
    cap = RemainingCapacityRow(
        total_users=4,
        target_engagement_rate=0.0,
        historical_engaged_users=0,
        target_engaged_users=0,
        remaining_capacity=0,
    )
    result = mgr.apply_capacity_cap(state_df, [cap])

    # Users 1 (COOLING) and 2 (EXCLUDED) must be unchanged
    assert str(result.loc[1, "eligibility_status"]) == EligibilityStatus.COOLING.value
    assert str(result.loc[2, "eligibility_status"]) == EligibilityStatus.EXCLUDED.value


# ===========================================================================
# §4.4 Test 24 — _priority column absent from resolved_df output (AUD-V-007)
# ===========================================================================

def test_priority_column_absent_from_resolved_df():
    """'_priority' must not appear in resolve() output. (AUD-V-007)"""
    config = make_config()
    mgr = AudienceManager(config)
    trigger_df = make_trigger_df(n=3)
    state_df = make_state_df(n=3, config=config)

    resolved_df, _ = mgr.resolve(trigger_df, None, state_df, AS_OF)
    assert "_priority" not in resolved_df.columns, (
        "_priority working column must be dropped from resolve() output"
    )


# ===========================================================================
# §4.4 Test 25 — campaign filter excludes other campaigns (C-002)
# ===========================================================================

def test_campaign_filter_excludes_other_campaigns():
    """Rows with Campaign_ID != config.campaign_id (and != 'Default') are excluded."""
    config = make_config(campaign_id="CAMP_A")
    mgr = AudienceManager(config)

    trigger_df = pd.DataFrame({
        "Campaign_ID": ["CAMP_A", "CAMP_A", "CAMP_B"],
        "User_ID": ["U001", "U002", "U003"],
        "Trigger_Name": ["T1", "T1", "T1"],
        "Segment": ["S1", "S1", "S1"],
        "Trigger_Date": [date(2024, 1, 1)] * 3,
    })

    filtered = mgr.apply_campaign_filter(trigger_df)
    assert len(filtered) == 2
    assert "U003" not in filtered["User_ID"].values


# ===========================================================================
# §4.4 Test 26 — campaign filter keeps "Default" rows (C-002)
# ===========================================================================

def test_campaign_filter_keeps_default_campaign():
    """Rows with Campaign_ID='Default' are retained by the C-002 filter."""
    config = make_config(campaign_id="CAMP_A")
    mgr = AudienceManager(config)

    trigger_df = pd.DataFrame({
        "Campaign_ID": ["CAMP_A", "Default", "CAMP_B"],
        "User_ID": ["U001", "U002", "U003"],
        "Trigger_Name": ["T1", "T1", "T1"],
        "Segment": ["S1", "S1", "S1"],
        "Trigger_Date": [date(2024, 1, 1)] * 3,
    })

    filtered = mgr.apply_campaign_filter(trigger_df)
    assert len(filtered) == 2
    assert "U001" in filtered["User_ID"].values
    assert "U002" in filtered["User_ID"].values
    assert "U003" not in filtered["User_ID"].values


# ===========================================================================
# §4.4 Test 27 — unknown Trigger_Name excluded with WARNING (AUD-V-003)
# ===========================================================================

def test_unknown_trigger_name_excluded_with_warning(caplog):
    """Unknown Trigger_Name excluded from resolution; WARNING logged (AUD-V-003)."""
    config = make_config()  # has trigger T1 only
    mgr = AudienceManager(config)
    state_df = make_state_df(n=2, config=config)

    trigger_df = pd.DataFrame({
        "Campaign_ID": ["TEST_CAMPAIGN", "TEST_CAMPAIGN"],
        "User_ID": ["U001", "U002"],
        "Trigger_Name": ["T1", "UNKNOWN_TRIGGER"],
        "Segment": ["S1", "S1"],
        "Trigger_Date": [date(2024, 1, 1)] * 2,
    })

    with caplog.at_level(logging.WARNING, logger="core.audience_manager"):
        mgr.resolve(trigger_df, None, state_df, AS_OF)

    warning_msgs = [r.message for r in caplog.records if r.levelname == "WARNING"]
    aud_004_msgs = [m for m in warning_msgs if "UNKNOWN_TRIGGER" in m]
    assert len(aud_004_msgs) >= 1, f"Expected AUD-004 warning for UNKNOWN_TRIGGER; got: {warning_msgs}"


# ===========================================================================
# §4.4 Test 28 — user with all triggers excluded → SKIPPED (AUD-005)
# ===========================================================================

def test_user_all_triggers_excluded_classified_skipped():
    """User whose only trigger row has an unknown name → SKIPPED + WARNING."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = make_state_df(n=1, config=config)

    trigger_df = pd.DataFrame({
        "Campaign_ID": ["TEST_CAMPAIGN"],
        "User_ID": ["U001"],
        "Trigger_Name": ["COMPLETELY_UNKNOWN"],
        "Segment": ["S1"],
        "Trigger_Date": [date(2024, 1, 1)],
    })

    resolved_df, _ = mgr.resolve(trigger_df, None, state_df, AS_OF)
    # User has no valid trigger → classified SKIPPED by np.select default
    assert str(resolved_df.loc[0, "eligibility_status"]) == EligibilityStatus.SKIPPED.value


# ===========================================================================
# §4.4 Test 29 — trigger_history uses TRIGGER_HISTORY_DELIMITER (ARCH-017)
# ===========================================================================

def test_trigger_history_pipe_delimiter_used():
    """TRIGGER_HISTORY_DELIMITER ('|') used when appending to trigger_history (ARCH-017)."""
    config = make_config()
    mgr = AudienceManager(config)

    # Run 1: initialize and resolve
    trigger_df = make_trigger_df(n=1, trigger_name="T1")
    state_df = make_state_df(n=1, config=config)
    resolved1, _ = mgr.resolve(trigger_df, None, state_df, AS_OF)

    # Run 2: same user reappears — trigger_history should append with delimiter
    resolved2, _ = mgr.resolve(trigger_df, None, resolved1, AS_OF)

    history = str(resolved2.loc[0, "trigger_history"])
    assert TRIGGER_HISTORY_DELIMITER in history, (
        f"Expected '|' delimiter in trigger_history; got: {history!r}"
    )
    parts = history.split(TRIGGER_HISTORY_DELIMITER)
    assert len(parts) == 2
    assert all(p == "T1" for p in parts)


# ===========================================================================
# §4.4 Test 30 — trigger_history set from None for first-time users
# ===========================================================================

def test_trigger_history_none_for_first_appearance():
    """First run: trigger_history is set from None to the trigger name."""
    config = make_config()
    mgr = AudienceManager(config)

    trigger_df = make_trigger_df(n=2, trigger_name="T1")
    state_df = make_state_df(n=2, config=config)
    assert state_df["trigger_history"].isna().all()  # pre-condition

    resolved_df, _ = mgr.resolve(trigger_df, None, state_df, AS_OF)

    assert (resolved_df["trigger_history"] == "T1").all(), (
        f"Expected 'T1' in trigger_history; got: {resolved_df['trigger_history'].tolist()}"
    )


# ===========================================================================
# §4.4 Test 31 — first_trigger_name set once, not overwritten (idempotent)
# ===========================================================================

def test_first_trigger_name_set_once():
    """first_trigger_name set on first run; subsequent runs do not overwrite it."""
    from models.trigger_config import TriggerConfig
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.20),
        TriggerConfig(trigger_name="T2", priority=2, engagement_rate_target=0.15),
    )
    config = make_config(triggers=triggers)
    mgr = AudienceManager(config)

    # Run 1 with T1
    trigger_df_1 = make_trigger_df(n=1, trigger_name="T1")
    state_df = make_state_df(n=1, config=config)
    resolved1, _ = mgr.resolve(trigger_df_1, None, state_df, AS_OF)
    assert str(resolved1.loc[0, "first_trigger_name"]) == "T1"

    # Run 2 with T2 — first_trigger_name should remain "T1"
    trigger_df_2 = make_trigger_df(n=1, trigger_name="T2")
    resolved2, _ = mgr.resolve(trigger_df_2, None, resolved1, AS_OF)
    assert str(resolved2.loc[0, "first_trigger_name"]) == "T1", (
        f"first_trigger_name must not be overwritten; got: {resolved2.loc[0, 'first_trigger_name']!r}"
    )


# ===========================================================================
# §4.4 Test 32 — total_trigger_appearances incremented by 1 per call
# ===========================================================================

def test_total_trigger_appearances_incremented():
    """total_trigger_appearances += 1 per resolve() call (FR-AUD-013)."""
    config = make_config()
    mgr = AudienceManager(config)
    trigger_df = make_trigger_df(n=2, trigger_name="T1")
    state_df = make_state_df(n=2, config=config)
    assert (state_df["total_trigger_appearances"] == 0).all()

    resolved1, _ = mgr.resolve(trigger_df, None, state_df, AS_OF)
    assert (resolved1["total_trigger_appearances"] == 1).all()

    resolved2, _ = mgr.resolve(trigger_df, None, resolved1, AS_OF)
    assert (resolved2["total_trigger_appearances"] == 2).all()


# ===========================================================================
# §4.4 Test 33 — full pipeline happy path
# ===========================================================================

def test_resolve_audience_full_pipeline_happy_path():
    """Full resolve() returns valid state_df + capacity_list (§4.4 #33)."""
    config = make_config()
    mgr = AudienceManager(config)
    trigger_df = make_trigger_df(n=3, trigger_name="T1")
    state_df = make_state_df(n=3, config=config)

    resolved_df, capacity_list = mgr.resolve(trigger_df, None, state_df, AS_OF)

    assert len(resolved_df) == 3
    assert len(capacity_list) == len(config.triggers)
    assert "_priority" not in resolved_df.columns
    assert "trigger_name" in resolved_df.columns
    assert "segment" in resolved_df.columns
    assert "eligibility_status" in resolved_df.columns
    # All new users with valid trigger → NEW
    assert (resolved_df["eligibility_status"] == EligibilityStatus.NEW.value).all()


# ===========================================================================
# §4.6 Wave 1 Integration Test: UserStateManager → AudienceManager
# ===========================================================================

def test_wave_1_integration_user_state_then_audience_resolve():
    """Full Stage 3 → Stage 4 integration (§4.6)."""
    config = make_config()
    as_of = date(2024, 2, 1)

    trigger_df = pd.DataFrame({
        "Campaign_ID": ["TEST_CAMPAIGN"] * 3,
        "User_ID": ["U001", "U002", "U003"],
        "Trigger_Name": ["T1", "T1", "T1"],
        "Segment": ["Seg_A", "Seg_A", "Seg_A"],
        "Trigger_Date": [date(2024, 1, 1)] * 3,
    })

    # Stage 3: UserStateManager
    usm = UserStateManager(config)
    state_df = usm.initialize_user_states(trigger_df, None)

    # §4.6 Assert 1: valid state_df with correct schema
    assert len(state_df) == 3
    assert "eligibility_status" in state_df.columns
    assert "trigger_name" in state_df.columns

    # Stage 4: AudienceManager
    aud = AudienceManager(config)
    resolved_df, capacity_list = aud.resolve(trigger_df, None, state_df, as_of)

    # §4.6 Assert 2: returns tuple
    assert isinstance(resolved_df, pd.DataFrame)
    assert isinstance(capacity_list, list)

    # §4.6 Assert 3: all users present
    assert len(resolved_df) == 3

    # §4.6 Assert 4: only canonical EligibilityStatus values
    canonical = set(EligibilityStatus.NEW.value for e in [EligibilityStatus.NEW]) | {
        EligibilityStatus.ACTIVE.value,
        EligibilityStatus.COOLING.value,
        EligibilityStatus.RE_ENTRY.value,
        EligibilityStatus.SKIPPED.value,
        EligibilityStatus.EXCLUDED.value,
    }
    result_statuses = set(resolved_df["eligibility_status"].dropna().unique())
    assert result_statuses.issubset(canonical), (
        f"Non-canonical eligibility values: {result_statuses - canonical}"
    )

    # §4.6 Assert 5: one capacity row per trigger
    assert len(capacity_list) == len(config.triggers)

    # §4.6 Assert 6: no _priority column
    assert "_priority" not in resolved_df.columns

    # §4.6 Assert 7: all 35 static columns present
    from utils.schema_validator import USER_STATE_REQUIRED_COLUMNS
    for col in USER_STATE_REQUIRED_COLUMNS:
        assert col in resolved_df.columns, f"Missing required column: {col}"


# ===========================================================================
# Additional edge cases for ≥90% coverage
# ===========================================================================

def test_resolve_raises_if_trigger_df_missing_required_columns():
    """InputValidationError raised if trigger_df missing required columns."""
    config = make_config()
    mgr = AudienceManager(config)
    bad_trigger = pd.DataFrame({"User_ID": ["U001"]})
    state_df = make_state_df(n=1, config=config)
    with pytest.raises(InputValidationError, match="Campaign_ID"):
        mgr.resolve(bad_trigger, None, state_df, AS_OF)


def test_resolve_raises_if_state_df_missing_required_columns():
    """InputValidationError raised if state_df missing required columns."""
    config = make_config()
    mgr = AudienceManager(config)
    trigger_df = make_trigger_df(n=1)
    bad_state = pd.DataFrame({"user_id": ["U001"]})
    with pytest.raises(InputValidationError, match="journey_status"):
        mgr.resolve(trigger_df, None, bad_state, AS_OF)


def test_resolve_returns_empty_capacity_list_when_no_rows_after_filter():
    """resolve() returns (state_df, []) when all rows excluded by C-002 filter."""
    config = make_config(campaign_id="CAMP_A")
    mgr = AudienceManager(config)
    # All rows have wrong campaign_id
    trigger_df = pd.DataFrame({
        "Campaign_ID": ["CAMP_B", "CAMP_B"],
        "User_ID": ["U001", "U002"],
        "Trigger_Name": ["T1", "T1"],
        "Segment": ["S1", "S1"],
        "Trigger_Date": [date(2024, 1, 1)] * 2,
    })
    state_df = make_state_df(n=2, config=config)
    resolved_df, capacity_list = mgr.resolve(trigger_df, None, state_df, AS_OF)
    assert capacity_list == []


def test_resolve_segments_raises_assertion_on_duplicate_users():
    """resolve_segments raises AssertionError on duplicate (Campaign_ID, User_ID)."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = make_state_df(n=2, config=config)
    dup_trigger = pd.DataFrame({
        "Campaign_ID": ["TEST_CAMPAIGN", "TEST_CAMPAIGN"],
        "User_ID": ["U001", "U001"],
        "Trigger_Name": ["T1", "T1"],
        "Segment": ["S1", "S2"],
    })
    with pytest.raises(AssertionError, match="duplicate"):
        mgr.resolve_segments(dup_trigger, state_df)


def test_classify_eligibility_mixed_statuses():
    """Multiple users with different statuses classified correctly in one call."""
    config = make_config(allow_reentry=True)
    mgr = AudienceManager(config)
    state_df = make_state_df(n=4, config=config)
    state_df = state_df.copy()

    future_end = AS_OF + timedelta(days=5)
    past_end = AS_OF - timedelta(days=3)

    state_df["journey_status"] = [
        JourneyStatus.NOT_STARTED.value,
        JourneyStatus.ACTIVE.value,
        JourneyStatus.DROPPED.value,
        JourneyStatus.NOT_STARTED.value,
    ]
    state_df["cooling_period_end"] = [None, None, None, future_end]

    result = mgr.classify_eligibility(state_df, AS_OF)

    assert str(result.loc[0, "eligibility_status"]) == EligibilityStatus.NEW.value
    assert str(result.loc[1, "eligibility_status"]) == EligibilityStatus.ACTIVE.value
    assert str(result.loc[2, "eligibility_status"]) == EligibilityStatus.EXCLUDED.value
    assert str(result.loc[3, "eligibility_status"]) == EligibilityStatus.COOLING.value


def test_classify_eligibility_returns_categorical():
    """eligibility_status is pd.Categorical after classify_eligibility()."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = make_state_df(n=2, config=config)
    result = mgr.classify_eligibility(state_df, AS_OF)
    assert isinstance(result["eligibility_status"].dtype, pd.CategoricalDtype), (
        f"Expected CategoricalDtype, got {result['eligibility_status'].dtype}"
    )


def test_classify_eligibility_does_not_mutate_input():
    """Input state_df unchanged after classify_eligibility()."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = make_state_df(n=2, config=config)
    original_status = state_df["eligibility_status"].copy()
    _ = mgr.classify_eligibility(state_df, AS_OF)
    pd.testing.assert_series_equal(state_df["eligibility_status"], original_status)


def test_compute_remaining_capacity_returns_one_per_trigger():
    """compute_remaining_capacity returns exactly one row per trigger in config."""
    from models.trigger_config import TriggerConfig
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.20),
        TriggerConfig(trigger_name="T2", priority=2, engagement_rate_target=0.15),
    )
    config = make_config(triggers=triggers)
    mgr = AudienceManager(config)
    trigger_df = make_trigger_df(n=5, trigger_name="T1")
    capacity = mgr.compute_remaining_capacity(None, trigger_df)
    assert len(capacity) == 2


def test_compute_remaining_capacity_historical_window_filters_old_dates():
    """Historical records outside the window are excluded from historical_engaged count."""
    from models.trigger_config import TriggerConfig
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.50),
    )
    # Last 90 days window
    config = make_config(triggers=triggers)
    mgr = AudienceManager(config)

    trigger_df = make_trigger_df(n=10, trigger_name="T1")

    # One old record (way outside 90-day window) and one recent
    cutoff = config.simulation_start_date - timedelta(days=90)
    old_date = cutoff - timedelta(days=30)  # before cutoff
    recent_date = cutoff + timedelta(days=1)  # after cutoff

    historical_df = pd.DataFrame({
        "User_ID": ["H_OLD", "H_RECENT"],
        "Date": [old_date, recent_date],
        "Action": ["Click", "Click"],
        "Channel": ["Email", "Email"],
        "Trigger_Name": ["T1", "T1"],
    })
    capacity = mgr.compute_remaining_capacity(historical_df, trigger_df)
    # Only H_RECENT should count (H_OLD is outside window)
    assert capacity[0].historical_engaged_users == 1


def test_resolve_triggers_does_not_overwrite_first_trigger_on_rerun():
    """first_trigger_name is set once and preserved on subsequent runs."""
    config = make_config()
    mgr = AudienceManager(config)
    trigger_df = make_trigger_df(n=2, trigger_name="T1")
    state_df = make_state_df(n=2, config=config)

    resolved1 = mgr.resolve_triggers(trigger_df, state_df)
    # Manually change trigger_name to simulate run 2 with different trigger
    from models.trigger_config import TriggerConfig
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.20),
        TriggerConfig(trigger_name="T2", priority=2, engagement_rate_target=0.15),
    )
    config2 = make_config(triggers=triggers)
    mgr2 = AudienceManager(config2)
    trigger_df2 = make_trigger_df(n=2, trigger_name="T2")

    resolved2 = mgr2.resolve_triggers(trigger_df2, resolved1)
    # first_trigger_name should still be T1
    assert (resolved2["first_trigger_name"] == "T1").all()


def test_campaign_filter_returns_copy():
    """apply_campaign_filter returns a copy and does not mutate input."""
    config = make_config()
    mgr = AudienceManager(config)
    trigger_df = make_trigger_df(n=3)
    original_len = len(trigger_df)
    _ = mgr.apply_campaign_filter(trigger_df)
    assert len(trigger_df) == original_len


def test_no_iterrows_in_audience_manager():
    """Verify audience_manager.py contains no .iterrows() call (ARCH-011)."""
    import inspect
    from core import audience_manager
    source = inspect.getsource(audience_manager)
    bad_lines = [
        line for line in source.splitlines()
        if ".iterrows(" in line
        and not line.strip().startswith(("#", '"""', "'''"))
    ]
    assert not bad_lines, (
        f"iterrows() call found in audience_manager.py — ARCH-011 violation: {bad_lines}"
    )


def test_no_inline_pipe_literal_in_audience_manager():
    """Verify audience_manager.py uses TRIGGER_HISTORY_DELIMITER, not inline '|' (ARCH-017)."""
    import inspect
    from core import audience_manager
    source = inspect.getsource(audience_manager)
    bad_lines = [
        line for line in source.splitlines()
        if '"|"' in line
        and "TRIGGER_HISTORY_DELIMITER" not in line
        and not line.strip().startswith("#")
    ]
    assert not bad_lines, f"Inline '|' literal found: {bad_lines}"


def test_no_inline_0_5_literal_in_audience_manager():
    """Verify audience_manager.py uses no inline 0.5 literals (USM-V-006 extended)."""
    import inspect
    from core import audience_manager
    source = inspect.getsource(audience_manager)
    bad_lines = [
        line for line in source.splitlines()
        if "= 0.5" in line
        and not line.strip().startswith("#")
        and "DEFAULT" not in line
    ]
    assert not bad_lines, f"Inline 0.5 literal found: {bad_lines}"


def test_np_select_used_in_classify_eligibility():
    """classify_eligibility() uses np.select — not apply() or map() (AUD-V-010)."""
    import inspect
    from core import audience_manager
    source = inspect.getsource(audience_manager)
    assert "np.select(" in source, "np.select() must be used in classify_eligibility()"


def test_resolve_does_not_leave_priority_in_state_df():
    """_priority must not appear in any output DataFrame column (AUD-V-007)."""
    config = make_config()
    mgr = AudienceManager(config)
    trigger_df = make_trigger_df(n=5, trigger_name="T1")
    state_df = make_state_df(n=5, config=config)
    resolved_df, _ = mgr.resolve(trigger_df, None, state_df, AS_OF)
    assert "_priority" not in resolved_df.columns


def test_apply_capacity_cap_does_not_mutate_input():
    """apply_capacity_cap returns a new DataFrame; input is unchanged."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = make_state_df(n=3, config=config)
    state_df = mgr.classify_eligibility(state_df, AS_OF)
    state_df = state_df.copy()
    state_df["trigger_name"] = "T1"

    original_statuses = state_df["eligibility_status"].copy()
    cap = RemainingCapacityRow(
        total_users=3, target_engagement_rate=0.0,
        historical_engaged_users=0, target_engaged_users=0, remaining_capacity=0,
    )
    _ = mgr.apply_capacity_cap(state_df, [cap])
    pd.testing.assert_series_equal(state_df["eligibility_status"], original_statuses)


def test_resolve_trigger_history_accumulates_correctly_over_three_runs():
    """trigger_history accumulates run1|run2|run3 with pipe delimiter over 3 runs."""
    config = make_config()
    mgr = AudienceManager(config)
    trigger_df = make_trigger_df(n=1, trigger_name="T1")
    state_df = make_state_df(n=1, config=config)

    r1, _ = mgr.resolve(trigger_df, None, state_df, AS_OF)
    assert r1.loc[0, "trigger_history"] == "T1"

    r2, _ = mgr.resolve(trigger_df, None, r1, AS_OF)
    assert r2.loc[0, "trigger_history"] == "T1|T1"

    r3, _ = mgr.resolve(trigger_df, None, r2, AS_OF)
    assert r3.loc[0, "trigger_history"] == "T1|T1|T1"


def test_segment_assigned_in_full_pipeline():
    """After resolve(), segment matches the Segment from the trigger_df."""
    config = make_config()
    mgr = AudienceManager(config)
    trigger_df = pd.DataFrame({
        "Campaign_ID": ["TEST_CAMPAIGN"] * 2,
        "User_ID": ["U001", "U002"],
        "Trigger_Name": ["T1", "T1"],
        "Segment": ["Pharma_Seg", "Pharma_Seg"],
        "Trigger_Date": [date(2024, 1, 1)] * 2,
    })
    state_df = make_state_df(n=2, config=config)
    resolved_df, _ = mgr.resolve(trigger_df, None, state_df, AS_OF)

    assert (resolved_df["segment"] == "Pharma_Seg").all(), (
        f"Segment should be 'Pharma_Seg'; got: {resolved_df['segment'].tolist()}"
    )


def test_apply_capacity_cap_no_cap_needed_when_eligible_lte_capacity():
    """No users are SKIPPED when eligible count <= remaining_capacity."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = make_state_df(n=2, config=config)
    state_df = mgr.classify_eligibility(state_df, AS_OF)
    state_df = state_df.copy()
    state_df["trigger_name"] = "T1"

    # Capacity = 10, only 2 eligible → no cap applied
    cap = RemainingCapacityRow(
        total_users=2,
        target_engagement_rate=1.0,
        historical_engaged_users=0,
        target_engaged_users=10,
        remaining_capacity=10,
    )
    result = mgr.apply_capacity_cap(state_df, [cap])
    # All 2 users remain NEW
    assert (result["eligibility_status"] == EligibilityStatus.NEW.value).all()


def test_arch014_pathological_tiebreak_emits_warning(caplog):
    """[ARCH-014] WARNING logged when same user has same priority+trigger, different segments."""
    from models.trigger_config import TriggerConfig
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.20),
    )
    config = make_config(triggers=triggers)
    mgr = AudienceManager(config)
    state_df = make_state_df(n=1, config=config)

    # Same user, same trigger, same priority, different segments
    trigger_df = pd.DataFrame({
        "Campaign_ID": ["TEST_CAMPAIGN", "TEST_CAMPAIGN"],
        "User_ID": ["U001", "U001"],
        "Trigger_Name": ["T1", "T1"],
        "Segment": ["Seg_Z", "Seg_A"],
        "Trigger_Date": [date(2024, 1, 1), date(2024, 1, 1)],
    })

    with caplog.at_level(logging.WARNING, logger="core.audience_manager"):
        mgr.resolve(trigger_df, None, state_df, AS_OF)

    all_msgs = [r.message for r in caplog.records]
    arch014_msgs = [m for m in all_msgs if "ARCH-014" in m]
    assert len(arch014_msgs) >= 1, f"Expected ARCH-014 warning; got: {all_msgs}"
    # Winner should be alphabetically first segment
    result_df, _ = mgr.resolve(trigger_df, None, state_df, AS_OF)
    assert str(result_df.loc[0, "segment"]) == "Seg_A"


def test_resolve_triggers_with_empty_filtered_df():
    """resolve_triggers with an empty filtered_df returns state_df unchanged."""
    config = make_config()
    mgr = AudienceManager(config)
    state_df = make_state_df(n=2, config=config)
    empty_trigger = pd.DataFrame(columns=["Campaign_ID", "User_ID", "Trigger_Name", "Segment", "Trigger_Date"])
    result = mgr.resolve_triggers(empty_trigger, state_df)
    # State unchanged, trigger fields still None
    assert result["trigger_name"].isna().all()
    assert (result["total_trigger_appearances"] == 0).all()
