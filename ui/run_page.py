"""Page 4 — Run Simulation.

Pre-flight checklist, then executes SimulationOrchestrator.run()
with a live progress indicator. Stores result in session_state.
"""
from __future__ import annotations
import logging
import traceback

import streamlit as st

from ui.state import (
    get_trigger_df, get_historical_df, get_config_dict,
    get_result, set_result, set_run_error, get_run_error,
)

logger = logging.getLogger(__name__)


def _build_config_registry(cfg: dict):
    """Convert session-state config dict to ConfigRegistry."""
    from core.config_loader import load_config_from_dict
    return load_config_from_dict(cfg)


def _preflight_checks() -> list[str]:
    """Return list of error strings; empty list means ready to run."""
    errors: list[str] = []
    if get_trigger_df() is None:
        errors.append("No trigger file uploaded (go to Upload Files).")
    if get_config_dict() is None:
        errors.append("No campaign config saved (go to Campaign Setup).")
    cfg = get_config_dict() or {}
    if not cfg.get("campaign_id","").strip():
        errors.append("Campaign ID is empty.")
    if not cfg.get("ads"):
        errors.append("No ads configured.")
    if not cfg.get("triggers"):
        errors.append("No triggers configured.")
    return errors


def render() -> None:
    """Render the Run Simulation page."""
    st.header("🚀 Run Simulation")

    # ── Pre-flight ────────────────────────────────────────────────────────
    st.subheader("Pre-flight Checks")
    errors = _preflight_checks()

    if errors:
        for e in errors:
            st.error(f"❌ {e}")
        st.stop()
    else:
        cfg = get_config_dict()
        tdf = get_trigger_df()
        n_users = len(tdf) if tdf is not None else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Users",     f"{n_users:,}")
        col2.metric("Campaign",  cfg.get("campaign_id",""))
        col3.metric("Start",     cfg.get("simulation_start_date",""))
        col4.metric("End",       cfg.get("simulation_end_date",""))

        # Days
        try:
            from datetime import date
            s = date.fromisoformat(cfg["simulation_start_date"])
            e = date.fromisoformat(cfg["simulation_end_date"])
            st.caption(f"Simulation length: **{(e-s).days+1}** days | "
                       f"**{len(cfg.get('ads',[]))}** ads | "
                       f"**{len(cfg.get('triggers',[]))}** triggers")
        except Exception:
            pass

        st.success("✅ All pre-flight checks passed. Ready to run.")

    # Show previous result summary if available
    if get_result() is not None:
        r = get_result()
        meta = r.execution_metadata
        st.info(
            f"Previous run: {meta.get('n_events',0):,} events — "
            f"Quality {r.quality_score:.1f}/100 — "
            f"Realism {r.realism_score:.1f}/100"
        )

    # Show previous error if any
    if get_run_error():
        st.error(f"Previous run failed: {get_run_error()}")

    st.divider()

    # ── Run button ────────────────────────────────────────────────────────
    if st.button("▶️ Run Simulation", type="primary", use_container_width=True):
        set_run_error(None)
        cfg = get_config_dict()
        tdf = get_trigger_df()
        hdf = get_historical_df()

        progress  = st.progress(0, text="Initialising…")
        status_ph = st.empty()

        try:
            # Build ConfigRegistry
            status_ph.info("⚙️ Building configuration…")
            config = _build_config_registry(cfg)
            progress.progress(10, text="Configuration built.")

            from core.simulation_orchestrator import SimulationOrchestrator

            # Stage 1: UserStateManager
            status_ph.info("👥 Stage 1/6 — Initialising user states…")
            progress.progress(20, text="Stage 1: User States")

            # Stage 2-6 run inside orchestrator; we instrument with a simple
            # progress ladder since orchestrator is synchronous
            status_ph.info("🎯 Stage 2/6 — Resolving audience…")
            progress.progress(30, text="Stage 2: Audience")

            status_ph.info("📊 Stage 3/6 — Running engagement simulation…")
            progress.progress(40, text="Stage 3: Engagement")

            orch   = SimulationOrchestrator(config)
            result = orch.run(
                trigger_df=tdf,
                historical_df=hdf,
                generate_excel=True,
            )

            progress.progress(70, text="Stage 4: Validation")
            status_ph.info("✅ Stage 4/6 — Validating outputs…")
            progress.progress(85, text="Stage 5: Excel Export")
            status_ph.info("📥 Stage 5/6 — Generating Excel workbook…")
            progress.progress(95, text="Stage 6: Finalizing")
            status_ph.info("💾 Stage 6/6 — Finalising state…")

            set_result(result)
            progress.progress(100, text="Complete!")
            status_ph.success(
                f"✅ Simulation complete — "
                f"**{result.n_events:,}** events | "
                f"**{result.n_users:,}** users | "
                f"Quality **{result.quality_score:.1f}**/100 | "
                f"Elapsed **{result.elapsed_seconds:.1f}s**"
            )
            logger.info(
                "Simulation complete: campaign=%s users=%d events=%d quality=%.1f elapsed=%.1fs",
                cfg.get("campaign_id"), result.n_users, result.n_events,
                result.quality_score, result.elapsed_seconds or 0,
            )

            st.info("👉 Go to **Results** to review outputs and download the Excel report.")

        except Exception as exc:
            progress.progress(100, text="Failed")
            status_ph.error(f"❌ Simulation failed: {exc}")
            error_detail = traceback.format_exc()
            set_run_error(str(exc))
            logger.error("Simulation failed: %s\n%s", exc, error_detail)
            with st.expander("Error details"):
                st.code(error_detail)


__all__ = ["render"]
