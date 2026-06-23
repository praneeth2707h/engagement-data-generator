"""Tests for utils/schema_validator.py — BL-NEW-001 / EX-P2-001.

Covers:
* QUALIFYING_ACTIONS structure and completeness
* is_qualifying_action() — all supported channel/action combinations
* is_qualifying_action() — unknown channel, unknown action, Sent, Impression
* compute_error_threshold() — all three tiers (Tier 1 ≤1000, Tier 2 1001–10000, Tier 3 >10000)
* compute_error_threshold() — boundary values at tier transitions
* validate_required_columns() — all columns present, one missing, several missing
* validate_no_null_primary_keys() — no nulls, one null, column absent (no error)

References: C-004, BIZ-011, VAL-001
"""
from __future__ import annotations

import pandas as pd
import pytest

from utils.schema_validator import (
    QUALIFYING_ACTIONS,
    TRIGGER_FILE_REQUIRED_COLUMNS,
    HISTORICAL_FILE_REQUIRED_COLUMNS,
    USER_STATE_REQUIRED_COLUMNS,
    is_qualifying_action,
    compute_error_threshold,
    validate_required_columns,
    validate_no_null_primary_keys,
)
from utils.exceptions import InputValidationError


# ---------------------------------------------------------------------------
# TestQualifyingActionsStructure
# ---------------------------------------------------------------------------

class TestQualifyingActionsStructure:
    """QUALIFYING_ACTIONS dict shape and completeness (C-004)."""

    def test_qualifying_actions_is_dict(self):
        assert isinstance(QUALIFYING_ACTIONS, dict)

    def test_qualifying_actions_has_six_channels(self):
        assert len(QUALIFYING_ACTIONS) == 6

    def test_all_channel_values_are_sets(self):
        for channel, actions in QUALIFYING_ACTIONS.items():
            assert isinstance(actions, set), f"channel '{channel}' value is not a set"

    def test_display_channels_present(self):
        for ch in ("Endemic_Display", "Programmatic_Display", "Banner", "Display"):
            assert ch in QUALIFYING_ACTIONS, f"'{ch}' missing from QUALIFYING_ACTIONS"

    def test_email_and_whatsapp_present(self):
        assert "Email" in QUALIFYING_ACTIONS
        assert "WhatsApp" in QUALIFYING_ACTIONS

    def test_display_channels_click_only(self):
        for ch in ("Endemic_Display", "Programmatic_Display", "Banner", "Display"):
            assert QUALIFYING_ACTIONS[ch] == {"Click"}, (
                f"channel '{ch}' should only qualify 'Click'"
            )

    def test_email_qualifies_open_and_click(self):
        assert QUALIFYING_ACTIONS["Email"] == {"Open", "Click"}

    def test_whatsapp_qualifies_open_and_click(self):
        assert QUALIFYING_ACTIONS["WhatsApp"] == {"Open", "Click"}

    def test_sent_not_in_any_channel(self):
        for ch, actions in QUALIFYING_ACTIONS.items():
            assert "Sent" not in actions, f"'Sent' should never qualify (found in '{ch}')"

    def test_impression_not_in_any_channel(self):
        for ch, actions in QUALIFYING_ACTIONS.items():
            assert "Impression" not in actions, (
                f"'Impression' should never qualify (found in '{ch}')"
            )


# ---------------------------------------------------------------------------
# TestIsQualifyingAction — Display channels
# ---------------------------------------------------------------------------

class TestIsQualifyingActionDisplay:
    """is_qualifying_action() for Display-family channels — Click qualifies, Open does not."""

    def test_endemic_display_click_qualifies(self):
        assert is_qualifying_action("Endemic_Display", "Click") is True

    def test_endemic_display_open_does_not_qualify(self):
        assert is_qualifying_action("Endemic_Display", "Open") is False

    def test_endemic_display_sent_does_not_qualify(self):
        assert is_qualifying_action("Endemic_Display", "Sent") is False

    def test_endemic_display_impression_does_not_qualify(self):
        assert is_qualifying_action("Endemic_Display", "Impression") is False

    def test_programmatic_display_click_qualifies(self):
        assert is_qualifying_action("Programmatic_Display", "Click") is True

    def test_programmatic_display_open_does_not_qualify(self):
        assert is_qualifying_action("Programmatic_Display", "Open") is False

    def test_banner_click_qualifies(self):
        assert is_qualifying_action("Banner", "Click") is True

    def test_banner_open_does_not_qualify(self):
        assert is_qualifying_action("Banner", "Open") is False

    def test_display_click_qualifies(self):
        assert is_qualifying_action("Display", "Click") is True

    def test_display_open_does_not_qualify(self):
        assert is_qualifying_action("Display", "Open") is False

    def test_display_sent_does_not_qualify(self):
        assert is_qualifying_action("Display", "Sent") is False

    def test_display_impression_does_not_qualify(self):
        assert is_qualifying_action("Display", "Impression") is False


# ---------------------------------------------------------------------------
# TestIsQualifyingAction — Email
# ---------------------------------------------------------------------------

class TestIsQualifyingActionEmail:
    """is_qualifying_action() for Email channel."""

    def test_email_click_qualifies(self):
        assert is_qualifying_action("Email", "Click") is True

    def test_email_open_qualifies(self):
        assert is_qualifying_action("Email", "Open") is True

    def test_email_sent_does_not_qualify(self):
        assert is_qualifying_action("Email", "Sent") is False

    def test_email_impression_does_not_qualify(self):
        assert is_qualifying_action("Email", "Impression") is False


# ---------------------------------------------------------------------------
# TestIsQualifyingAction — WhatsApp
# ---------------------------------------------------------------------------

class TestIsQualifyingActionWhatsApp:
    """is_qualifying_action() for WhatsApp channel."""

    def test_whatsapp_click_qualifies(self):
        assert is_qualifying_action("WhatsApp", "Click") is True

    def test_whatsapp_open_qualifies(self):
        assert is_qualifying_action("WhatsApp", "Open") is True

    def test_whatsapp_sent_does_not_qualify(self):
        assert is_qualifying_action("WhatsApp", "Sent") is False

    def test_whatsapp_impression_does_not_qualify(self):
        assert is_qualifying_action("WhatsApp", "Impression") is False


# ---------------------------------------------------------------------------
# TestIsQualifyingAction — unknown / edge cases
# ---------------------------------------------------------------------------

class TestIsQualifyingActionEdgeCases:
    """is_qualifying_action() for unknown channels and actions."""

    def test_unknown_channel_click_returns_false(self):
        assert is_qualifying_action("SMS", "Click") is False

    def test_unknown_channel_open_returns_false(self):
        assert is_qualifying_action("TV_Ad", "Open") is False

    def test_empty_channel_returns_false(self):
        assert is_qualifying_action("", "Click") is False

    def test_empty_action_returns_false(self):
        assert is_qualifying_action("Email", "") is False

    def test_case_sensitive_channel_wrong_case_returns_false(self):
        # "email" is not "Email"
        assert is_qualifying_action("email", "Click") is False

    def test_case_sensitive_action_wrong_case_returns_false(self):
        # "click" is not "Click"
        assert is_qualifying_action("Email", "click") is False

    def test_sent_always_false_regardless_of_channel(self):
        for ch in QUALIFYING_ACTIONS:
            assert is_qualifying_action(ch, "Sent") is False, (
                f"'Sent' must never qualify for channel '{ch}'"
            )

    def test_impression_always_false_regardless_of_channel(self):
        for ch in QUALIFYING_ACTIONS:
            assert is_qualifying_action(ch, "Impression") is False, (
                f"'Impression' must never qualify for channel '{ch}'"
            )

    def test_unknown_channel_unknown_action_returns_false(self):
        assert is_qualifying_action("Fax", "Delete") is False


# ---------------------------------------------------------------------------
# TestComputeErrorThreshold
# ---------------------------------------------------------------------------

class TestComputeErrorThreshold:
    """compute_error_threshold() — all three tiers plus boundary values."""

    # Tier 1: ≤ 1,000 users → 2% / 20 absolute

    def test_tier1_one_user(self):
        pct, abs_ = compute_error_threshold(1)
        assert pct == 0.02
        assert abs_ == 20

    def test_tier1_500_users(self):
        pct, abs_ = compute_error_threshold(500)
        assert pct == 0.02
        assert abs_ == 20

    def test_tier1_boundary_1000_users(self):
        pct, abs_ = compute_error_threshold(1_000)
        assert pct == 0.02
        assert abs_ == 20

    # Tier 2: 1,001–10,000 users → 1% / 100 absolute

    def test_tier2_boundary_1001_users(self):
        pct, abs_ = compute_error_threshold(1_001)
        assert pct == 0.01
        assert abs_ == 100

    def test_tier2_5000_users(self):
        pct, abs_ = compute_error_threshold(5_000)
        assert pct == 0.01
        assert abs_ == 100

    def test_tier2_boundary_10000_users(self):
        pct, abs_ = compute_error_threshold(10_000)
        assert pct == 0.01
        assert abs_ == 100

    # Tier 3: > 10,000 users → 0.5% / 50 absolute

    def test_tier3_boundary_10001_users(self):
        pct, abs_ = compute_error_threshold(10_001)
        assert pct == 0.005
        assert abs_ == 50

    def test_tier3_50000_users(self):
        pct, abs_ = compute_error_threshold(50_000)
        assert pct == 0.005
        assert abs_ == 50

    def test_tier3_one_million_users(self):
        pct, abs_ = compute_error_threshold(1_000_000)
        assert pct == 0.005
        assert abs_ == 50

    def test_return_type_is_tuple(self):
        result = compute_error_threshold(100)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_pct_is_float(self):
        pct, _ = compute_error_threshold(100)
        assert isinstance(pct, float)

    def test_abs_is_int(self):
        _, abs_ = compute_error_threshold(100)
        assert isinstance(abs_, int)


# ---------------------------------------------------------------------------
# TestValidateRequiredColumns
# ---------------------------------------------------------------------------

class TestValidateRequiredColumns:
    """validate_required_columns() — present, missing, multiple missing."""

    def _make_df(self, columns: list[str]) -> pd.DataFrame:
        return pd.DataFrame(columns=columns)

    def test_all_columns_present_no_error(self):
        df = self._make_df(["User_ID", "Trigger_Name", "Trigger_Date", "Segment"])
        validate_required_columns(df, TRIGGER_FILE_REQUIRED_COLUMNS, "trigger.csv")

    def test_extra_columns_present_no_error(self):
        df = self._make_df(["User_ID", "Trigger_Name", "Trigger_Date", "Segment", "Extra"])
        validate_required_columns(df, TRIGGER_FILE_REQUIRED_COLUMNS, "trigger.csv")

    def test_one_column_missing_raises(self):
        df = self._make_df(["User_ID", "Trigger_Name", "Trigger_Date"])  # Segment missing
        with pytest.raises(InputValidationError):
            validate_required_columns(df, TRIGGER_FILE_REQUIRED_COLUMNS, "trigger.csv")

    def test_error_message_contains_missing_column_name(self):
        df = self._make_df(["User_ID", "Trigger_Name", "Trigger_Date"])
        with pytest.raises(InputValidationError) as exc_info:
            validate_required_columns(df, TRIGGER_FILE_REQUIRED_COLUMNS, "trigger.csv")
        assert "Segment" in str(exc_info.value)

    def test_multiple_missing_raises_once(self):
        df = self._make_df(["User_ID"])
        with pytest.raises(InputValidationError):
            validate_required_columns(df, TRIGGER_FILE_REQUIRED_COLUMNS, "trigger.csv")

    def test_empty_dataframe_all_required_missing_raises(self):
        df = pd.DataFrame()
        with pytest.raises(InputValidationError):
            validate_required_columns(df, TRIGGER_FILE_REQUIRED_COLUMNS, "empty.csv")

    def test_empty_required_list_no_error(self):
        df = self._make_df(["User_ID"])
        validate_required_columns(df, [], "any.csv")

    def test_historical_file_columns_present_no_error(self):
        df = self._make_df(["User_ID", "Date", "Action", "Channel"])
        validate_required_columns(df, HISTORICAL_FILE_REQUIRED_COLUMNS, "historical.csv")

    def test_historical_missing_action_raises(self):
        df = self._make_df(["User_ID", "Date", "Channel"])
        with pytest.raises(InputValidationError):
            validate_required_columns(df, HISTORICAL_FILE_REQUIRED_COLUMNS, "historical.csv")


# ---------------------------------------------------------------------------
# TestValidateNoNullPrimaryKeys
# ---------------------------------------------------------------------------

class TestValidateNoNullPrimaryKeys:
    """validate_no_null_primary_keys() — no nulls, null present, absent column."""

    def test_no_nulls_no_error(self):
        df = pd.DataFrame({"User_ID": ["U001", "U002"], "Trigger_Name": ["T1", "T2"]})
        validate_no_null_primary_keys(df, ["User_ID", "Trigger_Name"], "trigger.csv")

    def test_null_in_user_id_raises(self):
        df = pd.DataFrame({"User_ID": ["U001", None], "Trigger_Name": ["T1", "T2"]})
        with pytest.raises(InputValidationError):
            validate_no_null_primary_keys(df, ["User_ID"], "trigger.csv")

    def test_error_message_contains_column_name(self):
        df = pd.DataFrame({"User_ID": [None, "U001"]})
        with pytest.raises(InputValidationError) as exc_info:
            validate_no_null_primary_keys(df, ["User_ID"], "trigger.csv")
        assert "User_ID" in str(exc_info.value)

    def test_null_count_reported_in_message(self):
        df = pd.DataFrame({"User_ID": [None, None, "U001"]})
        with pytest.raises(InputValidationError) as exc_info:
            validate_no_null_primary_keys(df, ["User_ID"], "trigger.csv")
        assert "2" in str(exc_info.value)

    def test_absent_column_silently_skipped(self):
        # Column not in df → no error (column may be added later by caller)
        df = pd.DataFrame({"Other_Col": ["A", "B"]})
        validate_no_null_primary_keys(df, ["User_ID"], "trigger.csv")

    def test_second_key_column_null_raises(self):
        df = pd.DataFrame({"User_ID": ["U001", "U002"], "Trigger_Name": ["T1", None]})
        with pytest.raises(InputValidationError):
            validate_no_null_primary_keys(df, ["User_ID", "Trigger_Name"], "trigger.csv")

    def test_empty_key_columns_list_no_error(self):
        df = pd.DataFrame({"User_ID": [None, None]})
        validate_no_null_primary_keys(df, [], "trigger.csv")

    def test_all_nulls_raises(self):
        df = pd.DataFrame({"User_ID": [None, None, None]})
        with pytest.raises(InputValidationError):
            validate_no_null_primary_keys(df, ["User_ID"], "trigger.csv")
