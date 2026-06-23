"""Centralised session-state keys and typed accessors.

All session_state keys are defined here as constants.  Importing from this
module instead of using raw strings prevents key-name drift across pages.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import Any


# ── Key constants ──────────────────────────────────────────────────────────
KEY_TRIGGER_DF          = "trigger_df"
KEY_HISTORICAL_DF       = "historical_df"
KEY_CONFIG_DICT         = "config_dict"
KEY_CAMPAIGN_OVERRIDES  = "campaign_overrides"
KEY_RESULT              = "simulation_result"
KEY_RUN_ERROR           = "run_error"
KEY_ACTIVE_PAGE         = "active_page"

_DEFAULTS: dict[str, Any] = {
    KEY_TRIGGER_DF:         None,
    KEY_HISTORICAL_DF:      None,
    KEY_CONFIG_DICT:        None,
    KEY_CAMPAIGN_OVERRIDES: {},
    KEY_RESULT:             None,
    KEY_RUN_ERROR:          None,
    KEY_ACTIVE_PAGE:        "Upload",
}


def init_session_state() -> None:
    """Seed session_state keys with defaults on first load."""
    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def get_trigger_df() -> pd.DataFrame | None:
    return st.session_state.get(KEY_TRIGGER_DF)

def set_trigger_df(df: pd.DataFrame | None) -> None:
    st.session_state[KEY_TRIGGER_DF] = df

def get_historical_df() -> pd.DataFrame | None:
    return st.session_state.get(KEY_HISTORICAL_DF)

def set_historical_df(df: pd.DataFrame | None) -> None:
    st.session_state[KEY_HISTORICAL_DF] = df

def get_config_dict() -> dict | None:
    return st.session_state.get(KEY_CONFIG_DICT)

def set_config_dict(d: dict) -> None:
    st.session_state[KEY_CONFIG_DICT] = d

def get_campaign_overrides() -> dict:
    return st.session_state.get(KEY_CAMPAIGN_OVERRIDES, {})

def set_campaign_overrides(d: dict) -> None:
    st.session_state[KEY_CAMPAIGN_OVERRIDES] = d

def get_result():
    return st.session_state.get(KEY_RESULT)

def set_result(r) -> None:
    st.session_state[KEY_RESULT] = r

def get_run_error() -> str | None:
    return st.session_state.get(KEY_RUN_ERROR)

def set_run_error(msg: str | None) -> None:
    st.session_state[KEY_RUN_ERROR] = msg


__all__ = [
    "init_session_state",
    "get_trigger_df", "set_trigger_df",
    "get_historical_df", "set_historical_df",
    "get_config_dict", "set_config_dict",
    "get_campaign_overrides", "set_campaign_overrides",
    "get_result", "set_result",
    "get_run_error", "set_run_error",
    "KEY_TRIGGER_DF", "KEY_HISTORICAL_DF", "KEY_CONFIG_DICT",
    "KEY_CAMPAIGN_OVERRIDES", "KEY_RESULT", "KEY_RUN_ERROR",
]
