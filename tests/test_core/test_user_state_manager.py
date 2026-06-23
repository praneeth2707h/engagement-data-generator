"""Unit tests for core/user_state_manager.py — Wave 1 Step 1.

Covers all 26 required test cases from PHASE_3_WAVE_1_BUILD_CONTRACT.md §4.3,
plus additional edge cases for full coverage.

Test numbering matches §4.3 table where applicable.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from core.user_state_manager import UserStateManager
from models.enums import EligibilityStatus, JourneyStatus, BehaviorProfile
from utils.constants import (
    DEFAULT_CHANNEL_AFFINITY,
    DEFAULT_CREATIVE_AFFINITY,
    DEFAULT_ENGAGEMENT_SCORE,
)
from utils.exceptions import InputValidationError
from utils.schema_validator import USER_STATE_REQUIRED_COLUMNS

# Import shared fixtures from conftest.py
from tests.test_core.conftest import make_config, make_trigger_df, make_state_df


# ===========================================================================
# Helpers
# ===========================================================================

def _make_mgr(**config_kwargs) -> UserStateManager:
    return UserStateManager(make_config(**config_kwargs))


# ===========================================================================
# §4.3 Test 1 — initialize_creates_one_row_per_user
# ===========================================================================

def test_initialize_creates_one_row_per_user():
    """len(state_df) == len(trigger_df['User_ID'].unique())."""
    trigger_df = make_trigger_df(n=5)
    mgr = _make_mgr()
    state_df = mgr.initialize_user_states(trigger_df, None)
    assert len(state_df) == 5
    assert state_df["user_id"].nunique() == 5


# ===========================================================================
# §4.3 Test 2 — new users get eligibility_status == "New"
# ===========================================================================

def test_initialize_new_users_get_eligibility_new():
    """All new users have eligibility_status == 'New' (ARCH-015)."""
    state_df = make_state_df(n=3)
    assert (state_df["eligibility_status"] == EligibilityStatus.NEW.value).all()


# ===========================================================================
# §4.3 Test 3 — new users get journey_status == "Not_Started"
# ===========================================================================

def test_initialize_new_users_get_journey_not_started():
    """All new users have journey_status == 'Not_Started'."""
    state_df = make_state_df(n=3)
    assert (state_df["journey_status"] == JourneyStatus.NOT_STARTED.value).all()


# ===========================================================================
# §4.3 Test 4 — new users get historical_engaged == False
# ===========================================================================

def test_initialize_new_users_get_historical_engaged_false():
    """All new users have historical_engaged == False (field 34)."""
    state_df = make_state_df(n=3)
    assert "historical_engaged" in state_df.columns
    assert not state_df["historical_engaged"].any()


# ===========================================================================
# §4.3 Test 5 — new users get is_valid == True
# ===========================================================================

def test_initialize_new_users_get_is_valid_true():
    """All new users have is_valid == True (field 35)."""
    state_df = make_state_df(n=3)
    assert "is_valid" in state_df.columns
    assert state_df["is_valid"].all()


# ===========================================================================
# §4.3 Test 6 — engagement_score uses DEFAULT_ENGAGEMENT_SCORE constant
# ===========================================================================

def test_initialize_engagement_score_uses_constant():
    """engagement_score == DEFAULT_ENGAGEMENT_SCORE for all new users."""
    state_df = make_state_df(n=3)
    assert (state_df["engagement_score"] == np.float32(DEFAULT_ENGAGEMENT_SCORE)).all()


# ===========================================================================
# §4.3 Test 7 — channel_affinity_* use DEFAULT_CHANNEL_AFFINITY constant
# ===========================================================================

def test_initialize_channel_affinity_uses_constant():
    """All three channel_affinity_* == DEFAULT_CHANNEL_AFFINITY."""
    state_df = make_state_df(n=2)
    for col in ("channel_affinity_display", "channel_affinity_email", "channel_affinity_whatsapp"):
        assert col in state_df.columns, f"missing column: {col}"
        assert (state_df[col] == np.float32(DEFAULT_CHANNEL_AFFINITY)).all(), (
            f"{col} not equal to DEFAULT_CHANNEL_AFFINITY"
        )


# ===========================================================================
# §4.3 Test 8 — Creative_Affinity_* use DEFAULT_CREATIVE_AFFINITY constant
# ===========================================================================

def test_initialize_creative_affinity_uses_constant():
    """All Creative_Affinity_* columns == DEFAULT_CREATIVE_AFFINITY."""
    config = make_config()
    state_df = make_state_df(n=2, config=config)
    ca_cols = [c for c in state_df.columns if c.startswith("Creative_Affinity_")]
    assert len(ca_cols) > 0, "No Creative_Affinity_* columns found"
    for col in ca_cols:
        assert (state_df[col] == np.float32(DEFAULT_CREATIVE_AFFINITY)).all(), (
            f"{col} not equal to DEFAULT_CREATIVE_AFFINITY"
        )


# ===========================================================================
# §4.3 Test 9 — trigger_history is None for new users
# ===========================================================================

def test_initialize_trigger_history_none_for_new_users():
    """trigger_history is None for new users — Stage 4 (AudienceManager) populates it."""
    state_df = make_state_df(n=3)
    assert state_df["trigger_history"].isna().all()


# ===========================================================================
# §4.3 Test 10 — campaign_id always comes from config (new AND returning)
# ===========================================================================

def test_initialize_campaign_id_always_from_config():
    """campaign_id == config.campaign_id for both new and returning users (FR-USM-004)."""
    config = make_config(campaign_id="CAMP_A")
    trigger_df = make_trigger_df(n=3, campaign_id="CAMP_A")
    mgr = UserStateManager(config)
    prior = mgr.initialize_user_states(trigger_df, None)

    # Simulate second run with a config that has a different campaign_id override
    # (should still use the new config's id)
    config2 = make_config(campaign_id="CAMP_B")
    mgr2 = UserStateManager(config2)
    # same users appear in new trigger_df with new campaign
    trigger_df2 = make_trigger_df(n=3, campaign_id="CAMP_B")
    state2 = mgr2.initialize_user_states(trigger_df2, prior)

    assert (state2["campaign_id"] == "CAMP_B").all()


# ===========================================================================
# §4.3 Test 11 — returning user carries forward fields
# ===========================================================================

def test_initialize_returning_user_carries_forward_fields():
    """engagement_score and other fields preserved from prior state (FR-USM-003)."""
    config = make_config()
    trigger_df = make_trigger_df(n=1, campaign_id="TEST_CAMPAIGN")
    mgr = UserStateManager(config)
    prior = mgr.initialize_user_states(trigger_df, None)

    # Manually update engagement_score in prior state
    prior = prior.copy()
    prior.loc[prior["user_id"] == "U001", "engagement_score"] = np.float32(0.9)
    prior.loc[prior["user_id"] == "U001", "total_lifetime_engagements"] = 5

    state2 = mgr.initialize_user_states(trigger_df, prior)
    row = state2[state2["user_id"] == "U001"].iloc[0]
    assert float(row["engagement_score"]) == pytest.approx(0.9, abs=1e-4)
    assert int(row["total_lifetime_engagements"]) == 5


# ===========================================================================
# §4.3 Test 12 — returning user run_count incremented by 1
# ===========================================================================

def test_initialize_returning_user_run_count_incremented():
    """run_count == prior_run_count + 1 for returning users."""
    config = make_config()
    trigger_df = make_trigger_df(n=2, campaign_id="TEST_CAMPAIGN")
    mgr = UserStateManager(config)

    prior = mgr.initialize_user_states(trigger_df, None)
    assert (prior["run_count"] == 0).all()

    state2 = mgr.initialize_user_states(trigger_df, prior)
    assert (state2["run_count"] == 1).all()

    state3 = mgr.initialize_user_states(trigger_df, state2)
    assert (state3["run_count"] == 2).all()


# ===========================================================================
# §4.3 Test 13 — departed user excluded from output
# ===========================================================================

def test_initialize_departed_user_excluded_from_output():
    """User in prior state but absent from trigger_df is excluded from output."""
    config = make_config()
    mgr = UserStateManager(config)

    # Run 1: 3 users
    trigger_df_run1 = make_trigger_df(n=3, campaign_id="TEST_CAMPAIGN")
    prior = mgr.initialize_user_states(trigger_df_run1, None)
    assert len(prior) == 3

    # Run 2: only 2 of the 3 users; U003 has departed
    trigger_df_run2 = make_trigger_df(n=2, campaign_id="TEST_CAMPAIGN")
    state2 = mgr.initialize_user_states(trigger_df_run2, prior)

    assert len(state2) == 2
    assert "U003" not in state2["user_id"].values


# ===========================================================================
# §4.3 Test 14 — no prior state → all users new
# ===========================================================================

def test_initialize_no_prior_state_all_users_new():
    """All users treated as new when previous_state_df=None (FR-USM-005)."""
    state_df = make_state_df(n=4)
    assert len(state_df) == 4
    assert (state_df["run_count"] == 0).all()
    assert (state_df["eligibility_status"] == EligibilityStatus.NEW.value).all()


# ===========================================================================
# §4.3 Test 15 — float fields are float32
# ===========================================================================

def test_initialize_float_fields_are_float32():
    """engagement_score and channel_affinity_* are dtype float32 (FR-USM-008)."""
    state_df = make_state_df(n=2)
    for col in ("engagement_score", "channel_affinity_display",
                "channel_affinity_email", "channel_affinity_whatsapp"):
        assert state_df[col].dtype == np.float32, (
            f"{col} dtype is {state_df[col].dtype}, expected float32"
        )


# ===========================================================================
# §4.3 Test 16 — categorical fields are pd.Categorical
# ===========================================================================

def test_initialize_categorical_fields_are_categorical():
    """eligibility_status, journey_status, etc. are pd.Categorical (FR-USM-009)."""
    state_df = make_state_df(n=2)
    for col in ("eligibility_status", "journey_status", "behavior_profile"):
        assert isinstance(state_df[col].dtype, pd.CategoricalDtype), (
            f"{col} dtype is {state_df[col].dtype}, expected CategoricalDtype"
        )


# ===========================================================================
# §4.3 Test 17 — Creative_Affinity_* columns reconciled for all config ads
# ===========================================================================

def test_initialize_creative_affinity_columns_reconciled():
    """Creative_Affinity_{ad_name} columns present for all ads in config (ARCH-012)."""
    config = make_config()  # has Ad_A and Ad_B
    state_df = make_state_df(n=2, config=config)

    ad_names = config.get_ad_names()
    for ad in ad_names:
        expected_col = f"Creative_Affinity_{ad}"
        assert expected_col in state_df.columns, f"Missing column {expected_col}"
        assert state_df[expected_col].dtype == np.float32


# ===========================================================================
# §4.3 Test 18 — empty trigger_df returns empty state_df with all columns
# ===========================================================================

def test_initialize_empty_trigger_df_returns_empty_state_df():
    """len(state_df) == 0 but all required columns present for empty trigger_df."""
    config = make_config()
    mgr = UserStateManager(config)
    empty_trigger = pd.DataFrame(columns=["Campaign_ID", "User_ID", "Trigger_Name", "Segment", "Trigger_Date"])
    state_df = mgr.initialize_user_states(empty_trigger, None)

    assert len(state_df) == 0
    for col in USER_STATE_REQUIRED_COLUMNS:
        assert col in state_df.columns, f"Missing required column: {col}"


# ===========================================================================
# §4.3 Test 19 — duplicate user IDs in trigger_df deduplicated
# ===========================================================================

def test_initialize_duplicate_user_ids_deduplicated():
    """One row per user even when trigger_df has duplicate User_IDs (USM-V-004)."""
    trigger_df = pd.DataFrame({
        "Campaign_ID": ["TEST_CAMPAIGN"] * 4,
        "User_ID": ["U001", "U001", "U002", "U002"],  # 2 duplicates
        "Trigger_Name": ["T1"] * 4,
        "Segment": ["Seg_A"] * 4,
        "Trigger_Date": [date(2024, 1, 1)] * 4,
    })
    mgr = _make_mgr()
    state_df = mgr.initialize_user_states(trigger_df, None)
    assert len(state_df) == 2
    assert state_df["user_id"].nunique() == 2


# ===========================================================================
# §4.3 Test 20 — output schema matches USER_STATE_REQUIRED_COLUMNS
# ===========================================================================

def test_output_schema_matches_user_state_required_columns():
    """All USER_STATE_REQUIRED_COLUMNS present in state_df.columns (USM-V-003)."""
    state_df = make_state_df(n=3)
    for col in USER_STATE_REQUIRED_COLUMNS:
        assert col in state_df.columns, (
            f"Required column '{col}' missing from state_df"
        )


# ===========================================================================
# §4.3 Test 21 — update_user modifies the target user
# ===========================================================================

def test_update_user_modifies_target_user():
    """Specified field updated for target user only."""
    config = make_config()
    mgr = UserStateManager(config)
    state_df = make_state_df(n=3, config=config)

    updated = mgr.update_user(state_df, "U001", {"total_lifetime_engagements": 42})

    assert int(updated.loc[updated["user_id"] == "U001", "total_lifetime_engagements"].iloc[0]) == 42
    # Other users unchanged
    assert int(updated.loc[updated["user_id"] == "U002", "total_lifetime_engagements"].iloc[0]) == 0


# ===========================================================================
# §4.3 Test 22 — update_user does not mutate input
# ===========================================================================

def test_update_user_does_not_mutate_input():
    """Input state_df is unchanged after update_user() (FR-USM-010)."""
    config = make_config()
    mgr = UserStateManager(config)
    state_df = make_state_df(n=2, config=config)
    original_value = int(state_df.loc[state_df["user_id"] == "U001", "total_lifetime_engagements"].iloc[0])

    _ = mgr.update_user(state_df, "U001", {"total_lifetime_engagements": 99})

    # Original DataFrame must not have changed
    assert int(state_df.loc[state_df["user_id"] == "U001", "total_lifetime_engagements"].iloc[0]) == original_value


# ===========================================================================
# §4.3 Test 23 — update_user raises KeyError for unknown user
# ===========================================================================

def test_update_user_raises_key_error_for_unknown_user():
    """KeyError raised when user_id not present in state_df."""
    config = make_config()
    mgr = UserStateManager(config)
    state_df = make_state_df(n=2, config=config)

    with pytest.raises(KeyError, match="not found"):
        mgr.update_user(state_df, "DOES_NOT_EXIST", {"total_lifetime_engagements": 1})


# ===========================================================================
# §4.3 Test 24 — update_user raises ValueError for invalid column
# ===========================================================================

def test_update_user_raises_value_error_for_invalid_column():
    """ValueError raised when updates contains a column not in state_df."""
    config = make_config()
    mgr = UserStateManager(config)
    state_df = make_state_df(n=2, config=config)

    with pytest.raises(ValueError, match="not found"):
        mgr.update_user(state_df, "U001", {"nonexistent_column": 42})


# ===========================================================================
# §4.3 Test 25 — finalize_state sets state_as_of_date on all rows
# ===========================================================================

def test_finalize_state_sets_state_as_of_date_on_all_rows():
    """All rows have state_as_of_date == as_of_date after finalize_state()."""
    config = make_config()
    mgr = UserStateManager(config)
    state_df = make_state_df(n=3, config=config)
    as_of = date(2024, 3, 15)

    finalized = mgr.finalize_state(state_df, as_of)

    assert (finalized["state_as_of_date"] == as_of).all()


# ===========================================================================
# §4.3 Test 26 — finalize_state does not mutate input
# ===========================================================================

def test_finalize_state_does_not_mutate_input():
    """Input state_df unchanged after finalize_state() (FR-USM-010)."""
    config = make_config()
    mgr = UserStateManager(config)
    state_df = make_state_df(n=2, config=config)
    original_date = state_df["state_as_of_date"].iloc[0]

    _ = mgr.finalize_state(state_df, date(2024, 6, 30))

    assert state_df["state_as_of_date"].iloc[0] == original_date


# ===========================================================================
# Additional edge cases for ≥90% coverage
# ===========================================================================

def test_initialize_raises_if_user_id_column_missing():
    """InputValidationError raised when trigger_df has no User_ID column (USM-V-001)."""
    bad_trigger = pd.DataFrame({"Campaign_ID": ["C1"], "Some_Other": ["x"]})
    mgr = _make_mgr()
    with pytest.raises(InputValidationError, match="User_ID"):
        mgr.initialize_user_states(bad_trigger, None)


def test_initialize_raises_if_previous_state_missing_required_columns():
    """InputValidationError raised when previous_state_df is missing required columns."""
    config = make_config()
    mgr = UserStateManager(config)
    trigger_df = make_trigger_df(n=2)
    bad_prior = pd.DataFrame({"user_id": ["U001"], "bogus_col": [1]})
    with pytest.raises(InputValidationError, match="Missing required columns"):
        mgr.initialize_user_states(trigger_df, bad_prior)


def test_initialize_null_user_ids_dropped():
    """Null User_IDs are dropped with WARNING; remaining users processed normally."""
    trigger_df = pd.DataFrame({
        "Campaign_ID": ["TEST_CAMPAIGN", "TEST_CAMPAIGN", "TEST_CAMPAIGN"],
        "User_ID": ["U001", None, "U003"],
        "Trigger_Name": ["T1", "T1", "T1"],
        "Segment": ["Seg_A", "Seg_A", "Seg_A"],
        "Trigger_Date": [date(2024, 1, 1)] * 3,
    })
    mgr = _make_mgr()
    state_df = mgr.initialize_user_states(trigger_df, None)
    assert len(state_df) == 2
    assert "U001" in state_df["user_id"].values
    assert "U003" in state_df["user_id"].values


def test_initialize_mix_of_new_and_returning_users():
    """Correct split between new and returning users when prior state has partial overlap."""
    config = make_config()
    mgr = UserStateManager(config)

    # Run 1: users U001, U002
    prior = mgr.initialize_user_states(make_trigger_df(n=2), None)

    # Run 2: U001 (returning) + U003 (new)
    trigger_df2 = pd.DataFrame({
        "Campaign_ID": ["TEST_CAMPAIGN", "TEST_CAMPAIGN"],
        "User_ID": ["U001", "U003"],
        "Trigger_Name": ["T1", "T1"],
        "Segment": ["Seg_A", "Seg_A"],
        "Trigger_Date": [date(2024, 1, 8)] * 2,
    })
    state2 = mgr.initialize_user_states(trigger_df2, prior)

    assert len(state2) == 2

    u001_row = state2[state2["user_id"] == "U001"].iloc[0]
    assert int(u001_row["run_count"]) == 1  # returning: incremented

    u003_row = state2[state2["user_id"] == "U003"].iloc[0]
    assert int(u003_row["run_count"]) == 0  # new: starts at 0


def test_initialize_all_returning_no_new_users():
    """All users are returning; no new rows created; run_count incremented."""
    config = make_config()
    mgr = UserStateManager(config)
    trigger_df = make_trigger_df(n=3)

    prior = mgr.initialize_user_states(trigger_df, None)
    state2 = mgr.initialize_user_states(trigger_df, prior)

    assert len(state2) == 3
    assert (state2["run_count"] == 1).all()


def test_initialize_run_count_starts_at_zero_for_new_users():
    """New users have run_count == 0 (not 1)."""
    state_df = make_state_df(n=3)
    assert (state_df["run_count"] == 0).all()


def test_initialize_behavior_profile_default_moderate():
    """New users default to BehaviorProfile.MODERATE."""
    state_df = make_state_df(n=3)
    assert (state_df["behavior_profile"] == BehaviorProfile.MODERATE.value).all()


def test_initialize_weekly_counters_all_zero():
    """All weekly counters initialised to 0 for new users (ARCH-016)."""
    state_df = make_state_df(n=2)
    for col in ("weekly_impressions", "weekly_clicks", "weekly_opens", "weekly_engagements"):
        assert (state_df[col] == 0).all(), f"{col} should be 0 for new users"


def test_initialize_lifetime_counters_all_zero():
    """total_lifetime_engagements and ad_click_received are at defaults for new users."""
    state_df = make_state_df(n=2)
    assert (state_df["total_lifetime_engagements"] == 0).all()
    assert not state_df["ad_click_received"].any()


def test_initialize_trigger_fields_null_for_new_users():
    """trigger_name, segment, first_trigger_name, first_trigger_date all None for new users."""
    state_df = make_state_df(n=2)
    for col in ("trigger_name", "first_trigger_name", "first_trigger_date"):
        assert state_df[col].isna().all(), f"{col} should be None/NaT for new users"


def test_initialize_date_fields_null_for_new_users():
    """Date fields that default to None are actually null in the DataFrame."""
    state_df = make_state_df(n=2)
    for col in (
        "journey_start_date", "journey_completion_date",
        "cooling_period_end", "last_reached_date",
        "last_engagement_date", "engagement_cooldown_end",
    ):
        assert state_df[col].isna().all(), f"{col} should be null for new users"


def test_initialize_state_as_of_date_is_simulation_start():
    """state_as_of_date defaults to simulation_start_date for new users."""
    config = make_config(simulation_start_date=date(2024, 1, 1))
    state_df = make_state_df(n=2, config=config)
    assert (state_df["state_as_of_date"] == date(2024, 1, 1)).all()


def test_update_user_only_changes_specified_columns():
    """update_user changes only the specified column; all others stay the same."""
    config = make_config()
    mgr = UserStateManager(config)
    state_df = make_state_df(n=3, config=config)

    original_scores = state_df["engagement_score"].copy()
    updated = mgr.update_user(state_df, "U002", {"total_lifetime_engagements": 10})

    # engagement_score must be unchanged for all rows
    pd.testing.assert_series_equal(
        updated["engagement_score"].reset_index(drop=True),
        original_scores.reset_index(drop=True),
    )


def test_initialize_previous_state_none_equivalent_to_all_new():
    """previous_state_df=None produces same result as passing an empty DataFrame."""
    config = make_config()
    mgr = UserStateManager(config)
    trigger_df = make_trigger_df(n=3)

    state_none = mgr.initialize_user_states(trigger_df, None)
    state_empty = mgr.initialize_user_states(trigger_df, pd.DataFrame())

    assert len(state_none) == len(state_empty)
    assert set(state_none["user_id"]) == set(state_empty["user_id"])


def test_creative_affinity_float32_after_init():
    """Creative_Affinity_* columns are float32 after initialization."""
    config = make_config()
    state_df = make_state_df(n=2, config=config)
    ca_cols = [c for c in state_df.columns if c.startswith("Creative_Affinity_")]
    assert len(ca_cols) >= 1
    for col in ca_cols:
        assert state_df[col].dtype == np.float32, f"{col} should be float32"


def test_no_iterrows_in_production_module():
    """Verify user_state_manager.py contains no .iterrows() call (ARCH-011).

    Checks for actual method calls, not docstring references.
    """
    import inspect
    from core import user_state_manager
    source = inspect.getsource(user_state_manager)
    # Only flag actual .iterrows( call patterns; docstring mentions are fine
    bad_lines = [
        line for line in source.splitlines()
        if ".iterrows(" in line and not line.strip().startswith(("#", '"""', "'''"))
    ]
    assert not bad_lines, f"iterrows() call found in user_state_manager.py — ARCH-011 violation: {bad_lines}"


def test_no_inline_pipe_literal_in_production_module():
    """Verify user_state_manager.py uses TRIGGER_HISTORY_DELIMITER, not inline '|' (ARCH-017)."""
    import inspect
    from core import user_state_manager
    source = inspect.getsource(user_state_manager)
    # The constant import is fine; actual string literal "|" should not appear
    lines_with_pipe = [
        line for line in source.splitlines()
        if '"|"' in line and "TRIGGER_HISTORY_DELIMITER" not in line
        and not line.strip().startswith("#")
    ]
    assert not lines_with_pipe, f"Inline '|' literal found: {lines_with_pipe}"


def test_no_inline_0_5_literal_in_production_module():
    """Verify user_state_manager.py uses DEFAULT_* constants, not inline 0.5 (USM-V-006)."""
    import inspect
    from core import user_state_manager
    source = inspect.getsource(user_state_manager)
    # Check lines that are not comments and contain literal 0.5
    bad_lines = [
        line for line in source.splitlines()
        if "= 0.5" in line
        and not line.strip().startswith("#")
        and "DEFAULT" not in line
    ]
    assert not bad_lines, f"Inline 0.5 literal found: {bad_lines}"


def test_finalize_state_all_35_static_cols_still_present():
    """finalize_state() preserves all columns; it only updates state_as_of_date."""
    config = make_config()
    mgr = UserStateManager(config)
    state_df = make_state_df(n=2, config=config)
    original_cols = set(state_df.columns)

    finalized = mgr.finalize_state(state_df, date(2024, 6, 1))

    assert set(finalized.columns) == original_cols
