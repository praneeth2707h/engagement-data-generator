"""SimulationResult — immutable output envelope for Stage 10 Orchestrator.

Carries all intermediate DataFrames, the final workbook bytes, and execution
metadata produced by a single end-to-end simulation run.

Design decisions
----------------
* ``dataclass(frozen=True)`` — callers cannot accidentally mutate results.
* All DataFrame fields are optional (``pd.DataFrame | None``) so that partial
  runs (e.g. audience-only, no EngagementGenerator) can still be captured.
* ``execution_metadata`` is a plain dict to avoid coupling this model to any
  specific metadata schema — the orchestrator owns its format.
* ``workbook_bytes`` is ``bytes | None``; None when ExcelExporter is skipped
  (e.g. in unit tests where write=False).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class SimulationResult:
    """Immutable envelope holding all outputs of a complete simulation run.

    Attributes
    ----------
    state_df:
        Final user state DataFrame after simulation (UserStateManager output,
        finalised by ``UserStateManager.finalize_state()``).
    audience_df:
        Resolved audience state DataFrame after AudienceManager.resolve()
        has applied eligibility, triggers, and segments.
    events_df:
        Per-event log from EngagementGenerator — one row per delivered event.
    metrics_df:
        Daily aggregate metrics from EngagementGenerator — one row per
        simulation day.
    diagnostics_df:
        Requested-vs-actual diagnostic rows from EngagementGenerator.
    validation_results_df:
        Per-rule validation outcomes from ValidationEngine.
    validation_summary_df:
        Category-level validation aggregates from ValidationEngine.
    realism_report_df:
        Rate realism comparison from ValidationEngine.
    workbook_bytes:
        Raw bytes of the generated Excel workbook (.xlsx).  None if
        ``generate_excel=False`` was passed to the orchestrator.
    quality_score:
        Overall simulation quality score (0–100) from ValidationEngine.
    realism_score:
        Overall realism score (0–100) from ValidationEngine.
    feasibility_warnings:
        List of plain-text feasibility advisory strings from ValidationEngine.
    execution_metadata:
        Free-form dict of timing, counts, and configuration summary.
        Keys include: campaign_id, campaign_name, simulation_start,
        simulation_end, n_users, n_events, n_days, started_at, completed_at,
        elapsed_seconds, stage_timings.
    """

    # ── Stage outputs (ordered by pipeline stage) ────────────────────────
    state_df:               pd.DataFrame | None = field(default=None)
    audience_df:            pd.DataFrame | None = field(default=None)
    events_df:              pd.DataFrame | None = field(default=None)
    metrics_df:             pd.DataFrame | None = field(default=None)
    diagnostics_df:         pd.DataFrame | None = field(default=None)

    # ── Validation outputs ────────────────────────────────────────────────
    validation_results_df:  pd.DataFrame | None = field(default=None)
    validation_summary_df:  pd.DataFrame | None = field(default=None)
    realism_report_df:      pd.DataFrame | None = field(default=None)

    # ── Derived scores ────────────────────────────────────────────────────
    quality_score:          float = field(default=0.0)
    realism_score:          float = field(default=0.0)
    feasibility_warnings:   tuple[str, ...] = field(default_factory=tuple)

    # ── Export ────────────────────────────────────────────────────────────
    workbook_bytes:         bytes | None = field(default=None)

    # ── Run metadata ──────────────────────────────────────────────────────
    execution_metadata:     dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def n_events(self) -> int:
        """Number of events generated."""
        if self.events_df is None or self.events_df.empty:
            return 0
        return len(self.events_df)

    @property
    def n_users(self) -> int:
        """Number of users in the resolved audience."""
        if self.audience_df is None or self.audience_df.empty:
            return 0
        return len(self.audience_df)

    @property
    def succeeded(self) -> bool:
        """True when the run completed without an unhandled exception.

        Determined by presence of ``completed_at`` in execution_metadata.
        """
        return bool(self.execution_metadata.get("completed_at"))

    @property
    def elapsed_seconds(self) -> float | None:
        """Wall-clock seconds for the complete run, or None if not recorded."""
        return self.execution_metadata.get("elapsed_seconds")

    def __repr__(self) -> str:  # pragma: no cover
        meta = self.execution_metadata
        return (
            f"SimulationResult("
            f"campaign={meta.get('campaign_id', '?')!r}, "
            f"n_users={self.n_users}, "
            f"n_events={self.n_events}, "
            f"quality_score={self.quality_score:.1f}, "
            f"realism_score={self.realism_score:.1f}, "
            f"workbook={'yes' if self.workbook_bytes else 'no'}, "
            f"elapsed={self.elapsed_seconds}s"
            f")"
        )


__all__ = ["SimulationResult"]
