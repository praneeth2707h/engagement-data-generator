"""Tests for core/input_loader.py — includes MT-012 ARCH-011 regression test."""
import pathlib
import pytest
import pandas as pd
from datetime import date
from pathlib import Path

from core.input_loader import (
    load_trigger_file,
    load_historical_file,
    count_historical_engaged_users,
    _per_user_seed,
)
from utils.exceptions import InputValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_csv(tmp_path, name, data: dict) -> Path:
    df = pd.DataFrame(data)
    p = tmp_path / name
    df.to_csv(p, index=False)
    return p


# ---------------------------------------------------------------------------
# MT-012 — ARCH-011 regression: no row-by-row iteration in input_loader.py
# ---------------------------------------------------------------------------

def test_no_iterrows_in_input_loader():
    """Regression test: input_loader.py must never contain iterrows (ARCH-011)."""
    source = pathlib.Path(__file__).parent.parent.parent / "core" / "input_loader.py"
    content = source.read_text()
    assert "iterrows" not in content, (
        "iterrows() found in input_loader.py — ARCH-011 violation"
    )


# ---------------------------------------------------------------------------
# _per_user_seed
# ---------------------------------------------------------------------------

def test_per_user_seed_deterministic():
    assert _per_user_seed("user_abc") == _per_user_seed("user_abc")


def test_per_user_seed_range():
    s = _per_user_seed("some_user")
    assert 0 <= s < 2**32


def test_per_user_seed_different_users_differ():
    assert _per_user_seed("A") != _per_user_seed("B")


# ---------------------------------------------------------------------------
# load_trigger_file
# ---------------------------------------------------------------------------

def test_load_trigger_file_basic(tmp_path):
    p = write_csv(tmp_path, "triggers.csv", {
        "User_ID": ["U1", "U2"],
        "Trigger_Name": ["T1", "T1"],
        "Trigger_Date": ["2024-01-01", "2024-01-02"],
        "Segment": ["Seg1", "Seg2"],
    })
    df = load_trigger_file(p)
    assert len(df) == 2
    assert "Campaign_ID" in df.columns
    assert (df["Campaign_ID"] == "Default").all()


def test_load_trigger_file_campaign_id_preserved(tmp_path):
    p = write_csv(tmp_path, "triggers.csv", {
        "Campaign_ID": ["CAMP-001", "CAMP-001"],
        "User_ID": ["U1", "U2"],
        "Trigger_Name": ["T1", "T1"],
        "Trigger_Date": ["2024-01-01", "2024-01-02"],
        "Segment": ["Seg1", "Seg2"],
    })
    df = load_trigger_file(p)
    assert (df["Campaign_ID"] == "CAMP-001").all()


def test_load_trigger_file_missing_columns(tmp_path):
    p = write_csv(tmp_path, "triggers.csv", {"User_ID": ["U1"]})
    with pytest.raises(InputValidationError):
        load_trigger_file(p)


def test_load_trigger_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_trigger_file(tmp_path / "nonexistent.csv")


# ---------------------------------------------------------------------------
# load_historical_file
# ---------------------------------------------------------------------------

def test_load_historical_file_dedup(tmp_path):
    p = write_csv(tmp_path, "hist.csv", {
        "Campaign_ID": ["C1", "C1", "C1"],
        "User_ID": ["U1", "U1", "U2"],
        "Date": ["2024-01-01", "2024-01-01", "2024-01-01"],
        "Action": ["Click", "Click", "Click"],
        "Channel": ["Email", "Email", "Email"],
    })
    df = load_historical_file(p, campaign_match_mode="Strict", campaign_id="C1")
    assert df["User_ID"].nunique() == 2


def test_load_historical_file_cutoff(tmp_path):
    p = write_csv(tmp_path, "hist.csv", {
        "Campaign_ID": ["C1", "C1"],
        "User_ID": ["U1", "U2"],
        "Date": ["2024-01-01", "2024-06-01"],
        "Action": ["Click", "Click"],
        "Channel": ["Email", "Email"],
    })
    df = load_historical_file(
        p, campaign_match_mode="Any", cutoff_date=date(2024, 3, 1)
    )
    assert len(df) == 1
    assert df.iloc[0]["User_ID"] == "U2"


def test_load_historical_file_qualifying_filter(tmp_path):
    p = write_csv(tmp_path, "hist.csv", {
        "Campaign_ID": ["C1", "C1"],
        "User_ID": ["U1", "U2"],
        "Date": ["2024-01-01", "2024-01-01"],
        "Action": ["Impression", "Click"],
        "Channel": ["Display", "Display"],
    })
    df = load_historical_file(p, campaign_match_mode="Any")
    assert len(df) == 1


def test_strict_mode_requires_campaign_id(tmp_path):
    p = write_csv(tmp_path, "hist.csv", {
        "User_ID": ["U1"],
        "Date": ["2024-01-01"],
        "Action": ["Click"],
        "Channel": ["Email"],
    })
    with pytest.raises(ValueError):
        load_historical_file(p, campaign_match_mode="Strict", campaign_id=None)


# ---------------------------------------------------------------------------
# count_historical_engaged_users
# ---------------------------------------------------------------------------

def test_count_historical_engaged_users_empty():
    df = pd.DataFrame(columns=["User_ID", "Date", "Action", "Channel"])
    assert count_historical_engaged_users(df, "C1") == 0


def test_count_historical_engaged_users():
    df = pd.DataFrame({
        "User_ID": ["U1", "U1", "U2"],
        "Date": ["2024-01-01", "2024-01-02", "2024-01-01"],
        "Action": ["Click", "Click", "Open"],
        "Channel": ["Email", "Email", "Email"],
    })
    assert count_historical_engaged_users(df, "C1") == 2
