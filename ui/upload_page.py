"""Page 1 — File Upload.

Lets the user upload:
  * Trigger file (CSV / Excel, required)
  * Historical engagement file (CSV / Excel, optional)

Validates required columns on upload and surfaces clear error messages.
"""
from __future__ import annotations
import io
import logging

import pandas as pd
import streamlit as st

from ui.state import (
    get_trigger_df, set_trigger_df,
    get_historical_df, set_historical_df,
)
from utils.canonical_schema import (
    TRIGGER_FILE_REQUIRED_COLUMNS,
    HISTORICAL_FILE_REQUIRED_COLUMNS,
)

logger = logging.getLogger(__name__)

# HIGH-001/HIGH-002: column sets now sourced from CanonicalSchema
_TRIGGER_REQUIRED_COLS = set(TRIGGER_FILE_REQUIRED_COLUMNS)
_HISTORICAL_REQUIRED_COLS = set(HISTORICAL_FILE_REQUIRED_COLUMNS)


def _read_upload(uploaded_file) -> pd.DataFrame | None:
    """Parse an uploaded CSV or Excel file into a DataFrame."""
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(uploaded_file, dtype=str)
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file, dtype=str)
        else:
            st.error(f"Unsupported file type: {uploaded_file.name}. Upload CSV or Excel.")
            return None
    except Exception as exc:
        st.error(f"Could not parse {uploaded_file.name}: {exc}")
        return None


def render() -> None:
    """Render the Upload page."""
    st.header("📁 Upload Files")
    st.markdown(
        "Upload your **trigger file** (required) and optionally a "
        "**historical engagement file** to seed prior engagement data."
    )

    # ── Trigger File ──────────────────────────────────────────────────────
    st.subheader("Trigger File (required)")
    st.caption(f"Required columns: {', '.join(sorted(_TRIGGER_REQUIRED_COLS))}")

    trigger_upload = st.file_uploader(
        "Choose trigger file",
        type=["csv", "xlsx", "xls"],
        key="trigger_uploader",
    )

    if trigger_upload:
        df = _read_upload(trigger_upload)
        if df is not None:
            missing = _TRIGGER_REQUIRED_COLS - set(df.columns)
            if missing:
                st.error(f"Trigger file is missing required columns: {sorted(missing)}")
                set_trigger_df(None)
            else:
                set_trigger_df(df)
                st.success(
                    f"✅ Trigger file loaded — **{len(df):,}** users, "
                    f"{df['Campaign_ID'].nunique()} campaign(s)"
                )
                with st.expander("Preview trigger file (first 10 rows)"):
                    st.dataframe(df.head(10), use_container_width=True)
                logger.info("Trigger file loaded: %d rows", len(df))

    # Show current state if already loaded
    elif get_trigger_df() is not None:
        df = get_trigger_df()
        st.info(f"✅ Trigger file already loaded — **{len(df):,}** users.")

    # ── Historical Engagement File ────────────────────────────────────────
    st.subheader("Historical Engagement File (optional)")
    st.caption(
        "If supplied, this file seeds prior engagement counts for TCC calculations. "
        f"Minimum columns: {', '.join(sorted(_HISTORICAL_REQUIRED_COLS))}"
    )

    hist_upload = st.file_uploader(
        "Choose historical engagement file",
        type=["csv", "xlsx", "xls"],
        key="historical_uploader",
    )

    if hist_upload:
        df = _read_upload(hist_upload)
        if df is not None:
            missing = _HISTORICAL_REQUIRED_COLS - set(df.columns)
            if missing:
                st.warning(
                    f"Historical file is missing recommended columns: {sorted(missing)}. "
                    "File accepted but TCC seeding may be incomplete."
                )
            set_historical_df(df)
            st.success(f"✅ Historical file loaded — **{len(df):,}** rows.")
            with st.expander("Preview historical file (first 10 rows)"):
                st.dataframe(df.head(10), use_container_width=True)
            logger.info("Historical file loaded: %d rows", len(df))

    elif get_historical_df() is not None:
        df = get_historical_df()
        st.info(f"✅ Historical file already loaded — **{len(df):,}** rows.")

    # ── Status summary ────────────────────────────────────────────────────
    st.divider()
    trig_ok = get_trigger_df() is not None
    hist_ok = get_historical_df() is not None

    col1, col2 = st.columns(2)
    col1.metric("Trigger File", "✅ Loaded" if trig_ok else "⚠️ Not Loaded")
    col2.metric("Historical File", "✅ Loaded" if hist_ok else "➖ Not Uploaded")

    if not trig_ok:
        st.warning("Upload a trigger file before proceeding to Campaign Setup.")


__all__ = ["render"]
