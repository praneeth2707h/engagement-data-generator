"""Tests for utils/canonical_schema.py — Wave 1 / HIGH-001.

Covers:
* All EXTERNAL_* constants are Title_Case strings
* All INTERNAL_* constants are snake_case strings
* TRIGGER_FILE_REQUIRED_COLUMNS matches schema_validator
* HISTORICAL_FILE_REQUIRED_COLUMNS matches schema_validator
* HISTORICAL_FILE_EXTENDED_COLUMNS contains all four extended columns
* historical_file_has_extended_schema() returns True/False correctly
* No circular import cycles introduced by canonical_schema.py

References: HIGH-001, HIGH-002, HIGH-005, DMR-001 Section 4.1
"""
from __future__ import annotations

import importlib
import re

import pandas as pd
import pytest

from utils.canonical_schema import (
    EXTERNAL_CAMPAIGN_ID,
    EXTERNAL_USER_ID,
    EXTERNAL_TRIGGER_NAME,
    EXTERNAL_TRIGGER_DATE,
    EXTERNAL_SEGMENT,
    EXTERNAL_DATE,
    EXTERNAL_ACTION,
    EXTERNAL_CHANNEL,
    EXTERNAL_AD_NAME,
    EXTERNAL_JOURNEY_STEP,
    EXTERNAL_COMPLETION_DATE,
    INTERNAL_CAMPAIGN_ID,
    INTERNAL_USER_ID,
    INTERNAL_TRIGGER_NAME,
    INTERNAL_SEGMENT,
    INTERNAL_JOURNEY_STEP,
    TRIGGER_FILE_REQUIRED_COLUMNS,
    HISTORICAL_FILE_REQUIRED_COLUMNS,
    HISTORICAL_FILE_EXTENDED_COLUMNS,
    historical_file_has_extended_schema,
)

_TITLE_CASE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*(_[A-Z][A-Za-z0-9]*)*$")
_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z][a-z0-9]*)*$")

_ALL_EXTERNAL = [
    EXTERNAL_CAMPAIGN_ID,
    EXTERNAL_USER_ID,
    EXTERNAL_TRIGGER_NAME,
    EXTERNAL_TRIGGER_DATE,
    EXTERNAL_SEGMENT,
    EXTERNAL_DATE,
    EXTERNAL_ACTION,
    EXTERNAL_CHANNEL,
    EXTERNAL_AD_NAME,
    EXTERNAL_JOURNEY_STEP,
    EXTERNAL_COMPLETION_DATE,
]

_ALL_INTERNAL = [
    INTERNAL_CAMPAIGN_ID,
    INTERNAL_USER_ID,
    INTERNAL_TRIGGER_NAME,
    INTERNAL_SEGMENT,
    INTERNAL_JOURNEY_STEP,
]


# ---------------------------------------------------------------------------
# TestExternalConstants
# ---------------------------------------------------------------------------

class TestExternalConstants:
    """All EXTERNAL_* constants must be non-empty Title_Case strings."""

    def test_all_external_constants_are_strings(self):
        for val in _ALL_EXTERNAL:
            assert isinstance(val, str), f"Expected str, got {type(val)} for {val!r}"

    def test_all_external_constants_non_empty(self):
        for val in _ALL_EXTERNAL:
            assert val, f"External constant must not be empty"

    def test_all_external_constants_title_case(self):
        for val in _ALL_EXTERNAL:
            assert _TITLE_CASE_RE.match(val), (
                f"{val!r} does not match Title_Case pattern"
            )

    def test_external_campaign_id_value(self):
        assert EXTERNAL_CAMPAIGN_ID == "Campaign_ID"

    def test_external_user_id_value(self):
        assert EXTERNAL_USER_ID == "User_ID"

    def test_external_trigger_name_value(self):
        assert EXTERNAL_TRIGGER_NAME == "Trigger_Name"

    def test_external_trigger_date_value(self):
        assert EXTERNAL_TRIGGER_DATE == "Trigger_Date"

    def test_external_segment_value(self):
        assert EXTERNAL_SEGMENT == "Segment"

    def test_external_date_value(self):
        assert EXTERNAL_DATE == "Date"

    def test_external_action_value(self):
        assert EXTERNAL_ACTION == "Action"

    def test_external_channel_value(self):
        assert EXTERNAL_CHANNEL == "Channel"

    def test_external_ad_name_value(self):
        assert EXTERNAL_AD_NAME == "Ad_Name"

    def test_external_journey_step_value(self):
        assert EXTERNAL_JOURNEY_STEP == "Journey_Step"

    def test_external_completion_date_value(self):
        assert EXTERNAL_COMPLETION_DATE == "Completion_Date"

    def test_eleven_external_constants(self):
        assert len(_ALL_EXTERNAL) == 11


# ---------------------------------------------------------------------------
# TestInternalConstants
# ---------------------------------------------------------------------------

class TestInternalConstants:
    """All INTERNAL_* constants must be non-empty snake_case strings."""

    def test_all_internal_constants_are_strings(self):
        for val in _ALL_INTERNAL:
            assert isinstance(val, str), f"Expected str, got {type(val)} for {val!r}"

    def test_all_internal_constants_non_empty(self):
        for val in _ALL_INTERNAL:
            assert val, f"Internal constant must not be empty"

    def test_all_internal_constants_snake_case(self):
        for val in _ALL_INTERNAL:
            assert _SNAKE_CASE_RE.match(val), (
                f"{val!r} does not match snake_case pattern"
            )

    def test_internal_campaign_id_value(self):
        assert INTERNAL_CAMPAIGN_ID == "campaign_id"

    def test_internal_user_id_value(self):
        assert INTERNAL_USER_ID == "user_id"

    def test_internal_trigger_name_value(self):
        assert INTERNAL_TRIGGER_NAME == "trigger_name"

    def test_internal_segment_value(self):
        assert INTERNAL_SEGMENT == "segment"

    def test_internal_journey_step_value(self):
        assert INTERNAL_JOURNEY_STEP == "journey_step"

    def test_five_internal_constants(self):
        assert len(_ALL_INTERNAL) == 5


# ---------------------------------------------------------------------------
# TestRequiredColumnLists
# ---------------------------------------------------------------------------

class TestTriggerFileRequiredColumns:
    """TRIGGER_FILE_REQUIRED_COLUMNS matches schema_validator."""

    def test_is_list(self):
        assert isinstance(TRIGGER_FILE_REQUIRED_COLUMNS, list)

    def test_has_four_columns(self):
        assert len(TRIGGER_FILE_REQUIRED_COLUMNS) == 4

    def test_contains_user_id(self):
        assert "User_ID" in TRIGGER_FILE_REQUIRED_COLUMNS

    def test_contains_trigger_name(self):
        assert "Trigger_Name" in TRIGGER_FILE_REQUIRED_COLUMNS

    def test_contains_trigger_date(self):
        assert "Trigger_Date" in TRIGGER_FILE_REQUIRED_COLUMNS

    def test_contains_segment(self):
        assert "Segment" in TRIGGER_FILE_REQUIRED_COLUMNS

    def test_matches_schema_validator(self):
        from utils.schema_validator import TRIGGER_FILE_REQUIRED_COLUMNS as sv_cols
        assert set(TRIGGER_FILE_REQUIRED_COLUMNS) == set(sv_cols)

    def test_all_elements_are_strings(self):
        for col in TRIGGER_FILE_REQUIRED_COLUMNS:
            assert isinstance(col, str)


class TestHistoricalFileRequiredColumns:
    """HISTORICAL_FILE_REQUIRED_COLUMNS matches schema_validator."""

    def test_is_list(self):
        assert isinstance(HISTORICAL_FILE_REQUIRED_COLUMNS, list)

    def test_has_four_columns(self):
        assert len(HISTORICAL_FILE_REQUIRED_COLUMNS) == 4

    def test_contains_user_id(self):
        assert "User_ID" in HISTORICAL_FILE_REQUIRED_COLUMNS

    def test_contains_date(self):
        assert "Date" in HISTORICAL_FILE_REQUIRED_COLUMNS

    def test_contains_action(self):
        assert "Action" in HISTORICAL_FILE_REQUIRED_COLUMNS

    def test_contains_channel(self):
        assert "Channel" in HISTORICAL_FILE_REQUIRED_COLUMNS

    def test_matches_schema_validator(self):
        from utils.schema_validator import HISTORICAL_FILE_REQUIRED_COLUMNS as sv_cols
        assert set(HISTORICAL_FILE_REQUIRED_COLUMNS) == set(sv_cols)

    def test_all_elements_are_strings(self):
        for col in HISTORICAL_FILE_REQUIRED_COLUMNS:
            assert isinstance(col, str)


# ---------------------------------------------------------------------------
# TestExtendedColumns
# ---------------------------------------------------------------------------

class TestHistoricalFileExtendedColumns:
    """HISTORICAL_FILE_EXTENDED_COLUMNS defines the four Wave 3 extension columns."""

    def test_is_list(self):
        assert isinstance(HISTORICAL_FILE_EXTENDED_COLUMNS, list)

    def test_has_four_columns(self):
        assert len(HISTORICAL_FILE_EXTENDED_COLUMNS) == 4

    def test_contains_ad_name(self):
        assert "Ad_Name" in HISTORICAL_FILE_EXTENDED_COLUMNS

    def test_contains_journey_step(self):
        assert "Journey_Step" in HISTORICAL_FILE_EXTENDED_COLUMNS

    def test_contains_trigger_name(self):
        assert "Trigger_Name" in HISTORICAL_FILE_EXTENDED_COLUMNS

    def test_contains_completion_date(self):
        assert "Completion_Date" in HISTORICAL_FILE_EXTENDED_COLUMNS

    def test_no_overlap_with_required_columns(self):
        # Ad_Name, Journey_Step, Completion_Date are new; Trigger_Name overlaps — allowed
        new_cols = {"Ad_Name", "Journey_Step", "Completion_Date"}
        assert new_cols.isdisjoint(set(HISTORICAL_FILE_REQUIRED_COLUMNS))


# ---------------------------------------------------------------------------
# TestHasExtendedSchema
# ---------------------------------------------------------------------------

class TestHistoricalFileHasExtendedSchema:
    """historical_file_has_extended_schema() returns True/False correctly."""

    def _base_df(self) -> pd.DataFrame:
        return pd.DataFrame(columns=["User_ID", "Date", "Action", "Channel"])

    def _extended_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "User_ID", "Date", "Action", "Channel",
                "Ad_Name", "Journey_Step", "Trigger_Name", "Completion_Date",
            ]
        )

    def test_returns_true_when_all_extended_cols_present(self):
        assert historical_file_has_extended_schema(self._extended_df()) is True

    def test_returns_false_for_base_schema(self):
        assert historical_file_has_extended_schema(self._base_df()) is False

    def test_returns_false_missing_one_extended_col(self):
        df = pd.DataFrame(
            columns=[
                "User_ID", "Date", "Action", "Channel",
                "Ad_Name", "Journey_Step", "Trigger_Name",
                # Completion_Date absent
            ]
        )
        assert historical_file_has_extended_schema(df) is False

    def test_returns_false_for_empty_dataframe(self):
        assert historical_file_has_extended_schema(pd.DataFrame()) is False

    def test_returns_true_with_extra_columns(self):
        df = pd.DataFrame(
            columns=[
                "User_ID", "Date", "Action", "Channel",
                "Ad_Name", "Journey_Step", "Trigger_Name", "Completion_Date",
                "Extra_Col",
            ]
        )
        assert historical_file_has_extended_schema(df) is True

    def test_returns_false_missing_ad_name(self):
        df = pd.DataFrame(
            columns=[
                "User_ID", "Date", "Action", "Channel",
                "Journey_Step", "Trigger_Name", "Completion_Date",
            ]
        )
        assert historical_file_has_extended_schema(df) is False

    def test_returns_false_missing_journey_step(self):
        df = pd.DataFrame(
            columns=[
                "User_ID", "Date", "Action", "Channel",
                "Ad_Name", "Trigger_Name", "Completion_Date",
            ]
        )
        assert historical_file_has_extended_schema(df) is False


# ---------------------------------------------------------------------------
# TestNoImportCycles
# ---------------------------------------------------------------------------

class TestNoImportCycles:
    """canonical_schema.py must be importable without project-level side effects."""

    def test_canonical_schema_importable(self):
        mod = importlib.import_module("utils.canonical_schema")
        assert mod is not None

    def test_no_import_cycles(self):
        """Re-importing after clearing should not raise ImportError."""
        import sys
        # Remove cached module to force a fresh import attempt
        cached = sys.modules.pop("utils.canonical_schema", None)
        try:
            mod = importlib.import_module("utils.canonical_schema")
            assert mod is not None
        finally:
            if cached is not None:
                sys.modules["utils.canonical_schema"] = cached
