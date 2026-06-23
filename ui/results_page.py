"""Page 5 — Results.

Displays Quality Score, Realism Score, event / user counts,
Validation Summary, Feasibility Warnings, and a Download Excel button.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd

from ui.state import get_result, get_run_error


def _score_colour(score: float) -> str:
    if score >= 80:
        return "normal"
    if score >= 60:
        return "off"
    return "inverse"


def _validation_badge(status: str) -> str:
    status_lower = str(status).lower()
    if status_lower == "pass":
        return "🟢"
    if status_lower == "fail":
        return "🔴"
    if status_lower == "skip":
        return "⚪"
    return "🟡"   # warning / unknown


def render() -> None:
    """Render the Results page."""
    st.header("📊 Results")

    result = get_result()

    if result is None:
        if get_run_error():
            st.error(f"Last run failed: {get_run_error()}")
        else:
            st.info("No simulation results yet. Go to **Run Simulation** first.")
        return

    # ── Top-line KPIs ─────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quality Score",  f"{result.quality_score:.1f} / 100")
    c2.metric("Realism Score",  f"{result.realism_score:.1f} / 100")
    c3.metric("Total Users",    f"{result.n_users:,}")
    c4.metric("Total Events",   f"{result.n_events:,}")

    meta = result.execution_metadata
    _elapsed = (
        f"Elapsed: **{result.elapsed_seconds:.2f}s**"
        if result.elapsed_seconds is not None
        else "Elapsed: N/A"
    )
    st.caption(f"{_elapsed} | {'✅ Succeeded' if result.succeeded else '❌ Failed'}")

    st.divider()

    # ── Score gauges ─────────────────────────────────────────────────────
    st.subheader("Score Breakdown")
    qcol, rcol = st.columns(2)

    with qcol:
        st.markdown("**Quality Score**")
        qval = result.quality_score / 100.0
        st.progress(qval)
        if result.quality_score >= 80:
            st.success(f"✅ {result.quality_score:.1f} — Good quality")
        elif result.quality_score >= 60:
            st.warning(f"⚠️ {result.quality_score:.1f} — Acceptable quality")
        else:
            st.error(f"❌ {result.quality_score:.1f} — Below threshold")

    with rcol:
        st.markdown("**Realism Score**")
        rval = result.realism_score / 100.0
        st.progress(rval)
        if result.realism_score >= 80:
            st.success(f"✅ {result.realism_score:.1f} — Realistic outputs")
        elif result.realism_score >= 60:
            st.warning(f"⚠️ {result.realism_score:.1f} — Moderate realism")
        else:
            st.error(f"❌ {result.realism_score:.1f} — Low realism")

    st.divider()

    # ── Feasibility Warnings ──────────────────────────────────────────────
    if result.feasibility_warnings:
        st.subheader("⚠️ Feasibility Warnings")
        for w in result.feasibility_warnings:
            st.warning(w)
        st.divider()

    # ── Validation Summary ────────────────────────────────────────────────
    st.subheader("✅ Validation Summary")
    vsdf = result.validation_summary_df

    if vsdf is not None and not vsdf.empty:
        # Aggregate by severity
        try:
            if "severity" in vsdf.columns and "status" in vsdf.columns:
                pass_count = int((vsdf["status"].astype(str).str.lower() == "pass").sum())
                fail_count = int((vsdf["status"].astype(str).str.lower() == "fail").sum())
                skip_count = int((vsdf["status"].astype(str).str.lower() == "skip").sum())
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Passed", pass_count, delta=None)
                sc2.metric("Failed", fail_count, delta=None)
                sc3.metric("Skipped", skip_count, delta=None)
        except Exception:
            pass

        # Show summary table with status badges
        try:
            display_df = vsdf.copy()
            if "status" in display_df.columns:
                display_df[""] = display_df["status"].astype(str).apply(_validation_badge)
                cols = [""] + [c for c in display_df.columns if c != ""]
                display_df = display_df[cols]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.dataframe(vsdf, use_container_width=True, hide_index=True)
            st.caption(f"(Display note: {exc})")
    else:
        st.info("No validation summary available.")

    # Validation details expander
    vdf = result.validation_results_df
    if vdf is not None and not vdf.empty:
        with st.expander("📋 Full Validation Details"):
            st.dataframe(vdf, use_container_width=True, hide_index=True)

    # Realism report expander
    rdf = result.realism_report_df
    if rdf is not None and not rdf.empty:
        with st.expander("📈 Realism Report"):
            st.dataframe(rdf, use_container_width=True, hide_index=True)

    st.divider()

    # ── Event / Metrics preview ───────────────────────────────────────────
    with st.expander("📂 Campaign Metrics Preview"):
        mdf = result.metrics_df
        if mdf is not None and not mdf.empty:
            st.dataframe(mdf.head(100), use_container_width=True, hide_index=True)
            if len(mdf) > 100:
                st.caption(f"Showing first 100 of {len(mdf):,} rows.")
        else:
            st.info("No metrics data.")

    with st.expander("📂 Events Preview (first 500 rows)"):
        edf = result.events_df
        if edf is not None and not edf.empty:
            st.dataframe(edf.head(500), use_container_width=True, hide_index=True)
            if len(edf) > 500:
                st.caption(f"Showing first 500 of {len(edf):,} rows.")
        else:
            st.info("No events data.")

    st.divider()

    # ── Download ──────────────────────────────────────────────────────────
    st.subheader("📥 Download Excel Report")

    if result.workbook_bytes:
        campaign_id = (meta.get("campaign_id","simulation") or "simulation").replace(" ","_")
        filename = f"{campaign_id}_engagement_report.xlsx"
        st.download_button(
            label="⬇️ Download Excel Workbook",
            data=result.workbook_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
        st.caption(
            f"6-sheet workbook: Event Data, Campaign Metrics, Validation Results, "
            f"Validation Summary, Realism Report, Diagnostics. "
            f"Size: {len(result.workbook_bytes)/1024:.1f} KB"
        )
    else:
        st.warning("Excel workbook was not generated for this run.")


__all__ = ["render"]
