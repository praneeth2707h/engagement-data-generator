"""Stage 10 — Simulation Orchestrator.

SimulationOrchestrator executes the complete simulation pipeline from a
single entry point, passing outputs between stages in the correct order,
centralising error handling and logging, and returning a single immutable
SimulationResult.

Pipeline execution order
------------------------
  Stage 1 — UserStateManager.initialize_user_states()
  Stage 2 — AudienceManager.resolve()
  Stage 3 — EngagementGenerator.generate()
  Stage 4 — ValidationEngine.validate()
  Stage 5 — ExcelExporter.export()           (optional, generate_excel=True)
  Stage 6 — UserStateManager.finalize_state()

All stage timings are recorded in SimulationResult.execution_metadata.

Integration surface
-------------------
Streamlit:
    result = SimulationOrchestrator(config).run(trigger_df)
    st.download_button(data=result.workbook_bytes, ...)

API:
    result = SimulationOrchestrator(config).run(trigger_df)
    return result.events_df.to_dict(orient="records")

Architecture references
-----------------------
* ARCH-003 — 11-stage pipeline; Stage 10 = Orchestrator
* ARCH-011 — No iterrows() in orchestration logic
"""
from __future__ import annotations

import time
from datetime import date, datetime
from typing import Any

import pandas as pd

from core.audience_manager    import AudienceManager
from core.engagement_generator import EngagementGenerator
from core.excel_exporter       import ExcelExporter
from core.user_state_manager   import UserStateManager
from core.validation_engine    import ValidationEngine
from models.config_registry    import ConfigRegistry
from models.simulation_result  import SimulationResult
from utils.canonical_schema    import TRIGGER_FILE_REQUIRED_COLUMNS
from utils.exceptions          import SimulationError
from utils.logger              import get_logger

logger = get_logger(__name__)

# Column names the trigger DataFrame must contain — sourced from CanonicalSchema (HIGH-001)
_TRIGGER_REQUIRED_COLS: frozenset[str] = frozenset(TRIGGER_FILE_REQUIRED_COLUMNS)


class SimulationOrchestrator:
    """Stage 10 — End-to-end simulation pipeline controller.

    Accepts a ConfigRegistry and a trigger DataFrame, executes all pipeline
    stages in sequence, and returns a single SimulationResult containing
    every intermediate artifact plus the final Excel workbook.

    Args:
        config: Fully validated ConfigRegistry for the current campaign run.

    Example::

        from core.simulation_orchestrator import SimulationOrchestrator
        result = SimulationOrchestrator(config).run(trigger_df)
        print(result.quality_score)          # 0–100
        open("report.xlsx", "wb").write(result.workbook_bytes)
    """

    def __init__(self, config: ConfigRegistry) -> None:
        """Initialise the orchestrator.

        Args:
            config: ConfigRegistry for the campaign run.
        """
        self._config = config
        logger.info(
            "SimulationOrchestrator initialised — campaign=%s start=%s end=%s",
            config.campaign_id,
            config.simulation_start_date,
            config.simulation_end_date,
        )

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def run(
        self,
        trigger_df: pd.DataFrame,
        historical_df: pd.DataFrame | None = None,
        previous_state_df: pd.DataFrame | None = None,
        generate_excel: bool = True,
        simulation_start: date | None = None,
        simulation_end: date | None = None,
    ) -> SimulationResult:
        """Execute the full simulation pipeline.

        Args:
            trigger_df: Audience trigger file.  Must contain columns:
                Campaign_ID, User_ID, Trigger_Name, Segment.
            historical_df: Historical engagement DataFrame for TCC seeding.
                Pass None on first-run campaigns.
            previous_state_df: Prior-run state DataFrame for returning users.
                Pass None on first runs.
            generate_excel: If True (default), run ExcelExporter and populate
                ``SimulationResult.workbook_bytes``.  Set False in unit tests
                or lightweight API calls to skip the export step.
            simulation_start: Override simulation start date.  Defaults to
                ``config.simulation_start_date``.
            simulation_end: Override simulation end date.  Defaults to
                ``config.simulation_end_date``.

        Returns:
            SimulationResult with all intermediate DataFrames, scores, and
            (optionally) the Excel workbook bytes.

        Raises:
            SimulationError: If a critical pipeline stage fails.  The
                exception message identifies the failing stage and wraps the
                original cause.
        """
        run_start = time.perf_counter()
        started_at = datetime.utcnow().isoformat() + "Z"
        stage_timings: dict[str, float] = {}

        logger.info(
            "SimulationOrchestrator.run() — campaign=%s trigger_rows=%d",
            self._config.campaign_id,
            len(trigger_df),
        )

        _validate_trigger_columns(trigger_df)

        cfg = self._config
        sim_start = simulation_start or cfg.simulation_start_date
        sim_end   = simulation_end   or cfg.simulation_end_date

        # ── Stage 1: UserStateManager ──────────────────────────────────────
        state_df = self._run_stage(
            "UserStateManager",
            stage_timings,
            lambda: UserStateManager(cfg).initialize_user_states(
                trigger_df, previous_state_df=previous_state_df
            ),
        )

        # ── Stage 2: AudienceManager ───────────────────────────────────────
        audience_df, _capacity = self._run_stage(
            "AudienceManager",
            stage_timings,
            lambda: AudienceManager(cfg).resolve(
                trigger_df,
                historical_df=historical_df,
                state_df=state_df,
                as_of_date=sim_start,
            ),
        )

        # ── ARCH-RISK-003 fix: stamp historical_engaged from historical_df ─
        # AudienceManager.compute_remaining_capacity() correctly filters the
        # historical window but the orchestrator previously discarded its
        # capacity output and never wired historical users into audience_df.
        # We now directly mark matching users as historical_engaged=True so
        # EngagementGenerator._init_capacity_tracker() reduces TCC correctly.
        if historical_df is not None and len(historical_df) > 0:
            _cutoff = cfg.get_historical_cutoff_date(sim_start)
            _h = historical_df.copy()
            if _cutoff is not None and "Date" in _h.columns:
                _h = _h[
                    pd.to_datetime(_h["Date"], errors="coerce")
                    >= pd.Timestamp(_cutoff)
                ]
            _hist_uids = set(_h["User_ID"].unique())
            if _hist_uids:
                audience_df = audience_df.copy()
                audience_df.loc[
                    audience_df["user_id"].isin(_hist_uids), "historical_engaged"
                ] = True
                logger.info(
                    "SimulationOrchestrator: ARCH-RISK-003 fix — stamped "
                    "historical_engaged=True for %d users from historical_df "
                    "(window=%s cutoff=%s)",
                    len(_hist_uids),
                    cfg.historical_engagement_window,
                    _cutoff,
                )

        # ── Stage 3: EngagementGenerator ──────────────────────────────────
        # ARCH-RISK-005 fix: generate() now returns a 4-tuple including the
        # final simulation state (journey completions, cooling, counters).
        events_df, metrics_df, diagnostics_df, _final_sim_state = self._run_stage(
            "EngagementGenerator",
            stage_timings,
            lambda: EngagementGenerator(cfg).generate(
                audience_df,
                simulation_start=sim_start,
                simulation_end=sim_end,
            ),
        )

        # ── Stage 4: ValidationEngine ──────────────────────────────────────
        validation_results_df, validation_summary_df, realism_report_df = self._run_stage(
            "ValidationEngine",
            stage_timings,
            lambda: ValidationEngine(cfg).validate(
                events_df, audience_df
            ),
        )

        # Derive scores
        ve = ValidationEngine(cfg)
        quality_score = ve.generate_quality_score(validation_results_df)
        realism_score = ve.generate_realism_score(realism_report_df)
        feasibility_warnings = tuple(
            ve.generate_feasibility_warnings(events_df, audience_df)
        )

        # ── Stage 5 (optional): ExcelExporter ─────────────────────────────
        workbook_bytes: bytes | None = None
        if generate_excel:
            workbook_bytes = self._run_stage(
                "ExcelExporter",
                stage_timings,
                lambda: ExcelExporter(cfg).export(
                    events_df=events_df,
                    state_df=audience_df,
                    metrics_df=metrics_df,
                    validation_results_df=validation_results_df,
                    validation_summary_df=validation_summary_df,
                    realism_report_df=realism_report_df,
                ),
            )

        # ── Stage 6: finalize state ────────────────────────────────────────
        # ARCH-RISK-005 fix: use _final_sim_state (post-simulation) instead of
        # audience_df (pre-simulation) so that journey completions, cooling
        # periods, and engagement counters are captured in SimulationResult.state_df.
        final_state_df = self._run_stage(
            "finalize_state",
            stage_timings,
            lambda: UserStateManager(cfg).finalize_state(
                _final_sim_state, as_of_date=sim_end
            ),
        )

        # ── Build metadata ─────────────────────────────────────────────────
        elapsed = round(time.perf_counter() - run_start, 3)
        completed_at = datetime.utcnow().isoformat() + "Z"

        metadata: dict[str, Any] = {
            "campaign_id":      cfg.campaign_id,
            "campaign_name":    cfg.campaign_name,
            "simulation_start": sim_start.isoformat(),
            "simulation_end":   sim_end.isoformat(),
            "n_users":          len(audience_df),
            "n_events":         len(events_df),
            "n_days":           (sim_end - sim_start).days + 1,
            "started_at":       started_at,
            "completed_at":     completed_at,
            "elapsed_seconds":  elapsed,
            "stage_timings":    stage_timings,
            "generate_excel":   generate_excel,
            "n_validation_rules": len(validation_results_df),
            "quality_score":    quality_score,
            "realism_score":    realism_score,
            "n_feasibility_warnings": len(feasibility_warnings),
        }

        logger.info(
            "SimulationOrchestrator.run() complete — "
            "campaign=%s n_users=%d n_events=%d quality=%.1f realism=%.1f elapsed=%.2fs",
            cfg.campaign_id,
            len(audience_df),
            len(events_df),
            quality_score,
            realism_score,
            elapsed,
        )

        return SimulationResult(
            state_df=final_state_df,
            audience_df=audience_df,
            events_df=events_df,
            metrics_df=metrics_df,
            diagnostics_df=diagnostics_df,
            validation_results_df=validation_results_df,
            validation_summary_df=validation_summary_df,
            realism_report_df=realism_report_df,
            quality_score=quality_score,
            realism_score=realism_score,
            feasibility_warnings=feasibility_warnings,
            workbook_bytes=workbook_bytes,
            execution_metadata=metadata,
        )

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _run_stage(
        self,
        stage_name: str,
        timings: dict[str, float],
        fn: Any,
    ) -> Any:
        """Execute one pipeline stage, recording timing and wrapping errors.

        Args:
            stage_name: Human-readable stage identifier for logging/errors.
            timings: Mutable dict to accumulate per-stage elapsed seconds.
            fn: Zero-argument callable that executes the stage.

        Returns:
            Whatever ``fn()`` returns.

        Raises:
            SimulationError: Wraps any exception raised by ``fn()``.
        """
        logger.debug("SimulationOrchestrator: starting stage=%s", stage_name)
        t0 = time.perf_counter()
        try:
            result = fn()
        except Exception as exc:
            elapsed = round(time.perf_counter() - t0, 3)
            timings[stage_name] = elapsed
            logger.error(
                "SimulationOrchestrator: stage=%s FAILED after %.3fs — %s: %s",
                stage_name, elapsed, type(exc).__name__, exc,
            )
            raise SimulationError(
                f"Pipeline stage '{stage_name}' failed: {type(exc).__name__}: {exc}"
            ) from exc
        elapsed = round(time.perf_counter() - t0, 3)
        timings[stage_name] = elapsed
        logger.debug(
            "SimulationOrchestrator: stage=%s OK elapsed=%.3fs", stage_name, elapsed
        )
        return result


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _validate_trigger_columns(trigger_df: pd.DataFrame) -> None:
    """Raise SimulationError if trigger_df is missing required columns."""
    missing = _TRIGGER_REQUIRED_COLS - set(trigger_df.columns)
    if missing:
        raise SimulationError(
            f"trigger_df is missing required columns: {sorted(missing)}"
        )


__all__ = ["SimulationOrchestrator"]
