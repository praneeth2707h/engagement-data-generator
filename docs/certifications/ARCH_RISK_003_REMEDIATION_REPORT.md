# ARCH-RISK-003 + ARCH-RISK-005 Remediation Report

**Report Date:** 2026-06-23  
**Stage:** 15 — Multi-Run Persistence Certification  
**Status:** REMEDIATED — All regression tests pass  

---

## 1. Executive Summary

Two architectural defects were identified and remediated during Stage 15 work. Both defects caused the `SimulationResult.state_df` returned by `SimulationOrchestrator.run()` to be incorrect or incomplete, breaking the multi-run chain that downstream consumers depend on for campaign re-engagement campaigns.

| Risk ID | Component | Defect | Status |
|---|---|---|---|
| ARCH-RISK-003 | `SimulationOrchestrator` | `historical_df` window filtering discarded; `historical_engaged` never stamped on `audience_df` | FIXED |
| ARCH-RISK-005 | `EngagementGenerator` + `SimulationOrchestrator` | Post-simulation state `df` discarded; `finalize_state()` received pre-simulation `audience_df` | FIXED |

---

## 2. ARCH-RISK-003: Historical Engagement Window Not Wired into Simulation

### 2.1 Root Cause

`AudienceManager.compute_remaining_capacity()` correctly filters `historical_df` by the configured window and counts historically-engaged users. However, the orchestrator discarded the second element of the return tuple:

```python
# BEFORE (broken): _capacity silently discarded
audience_df, _capacity = self._run_stage(
    "AudienceManager", ...
)
```

The `_capacity` list was never used. More critically, there was no code path that stamped `historical_engaged=True` on `audience_df` rows corresponding to users who appeared in the windowed `historical_df`. As a result:

- `EngagementGenerator._init_capacity_tracker()` saw `historical_engaged=False` for all users.
- Total campaign capacity (TCC) was not reduced by prior engagements.
- Historical users were treated identically to first-time users regardless of their engagement history.

### 2.2 Fix — `core/simulation_orchestrator.py` lines 168–195

After `AudienceManager.resolve()` completes, the orchestrator now performs a direct window-filtered stamp:

```python
# ARCH-RISK-003 fix: stamp historical_engaged from historical_df
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
```

**Why this location:** The orchestrator owns the data handoff between stages. Placing the fix here avoids coupling `AudienceManager` to the orchestrator's state representation and keeps Stage 2's return contract unchanged (tuple of `audience_df, capacity`).

### 2.3 Before / After Behavior

| Condition | Before Fix | After Fix |
|---|---|---|
| User in `historical_df` within window | `historical_engaged=False` | `historical_engaged=True` |
| TCC reduction for historical users | None | Correctly reduced |
| Users outside window | `historical_engaged=False` | `historical_engaged=False` (unchanged) |
| `historical_df=None` | No change | No change |

### 2.4 Regression Coverage

- **Stage 14 historical window certification:** 52 tests — all pass  
- **`tests/test_e2e/test_historical_window_certification.py`**: HW-001 through HW-005 (52 tests) — all pass  
- **Total E2E regression:** 216 tests pass  

---

## 3. ARCH-RISK-005: Post-Simulation State Discarded (Discovered During Stage 15)

### 3.1 Root Cause

`EngagementGenerator.generate()` ran the full simulation loop — advancing journeys, recording cooling periods, updating lifetime engagement counters — but returned only a 3-tuple:

```python
# BEFORE (broken): final simulation state df silently discarded
return events_df, metrics_df, diag_df
```

The local variable `df` holding the post-simulation state (with updated `journey_status`, `cooling_period_end`, `total_lifetime_engagements`) was discarded at return time.

The orchestrator then passed the pre-simulation `audience_df` to `finalize_state()`:

```python
# BEFORE (broken): audience_df is PRE-simulation state
final_state_df = self._run_stage(
    "finalize_state", stage_timings,
    lambda: UserStateManager(cfg).finalize_state(audience_df, as_of_date=sim_end),
)
```

Consequence: `SimulationResult.state_df` reflected user state as it was at the start of the simulation, not the end. Multi-run chains passing `result.state_df` as `previous_state_df` to the next run would carry no journey completions, no cooling periods, and no updated engagement counters.

### 3.2 Fix — Two-part change

**Part 1: `core/engagement_generator.py` — extend return tuple**

```python
# AFTER: 4-tuple, df is the post-simulation state
def generate(
    self,
    state_df: pd.DataFrame,
    simulation_start: date | None = None,
    simulation_end: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ...
    return events_df, metrics_df, diag_df, df  # df = post-simulation state
```

**Part 2: `core/simulation_orchestrator.py` — capture and use 4th return**

```python
# AFTER: capture _final_sim_state; pass it to finalize_state
events_df, metrics_df, diagnostics_df, _final_sim_state = self._run_stage(
    "EngagementGenerator", stage_timings,
    lambda: EngagementGenerator(cfg).generate(
        audience_df, simulation_start=sim_start, simulation_end=sim_end,
    ),
)

# ... later ...

final_state_df = self._run_stage(
    "finalize_state", stage_timings,
    lambda: UserStateManager(cfg).finalize_state(
        _final_sim_state, as_of_date=sim_end
    ),
)
```

### 3.3 Before / After Behavior

| State Field | Before Fix | After Fix |
|---|---|---|
| `journey_status` in state_df | Pre-simulation value | Post-simulation (COMPLETED, COOLING, etc.) |
| `cooling_period_end` in state_df | NaT / pre-sim value | Correctly set from JourneyEngine |
| `total_lifetime_engagements` | Pre-simulation value | Incremented by all events in the run |
| Multi-run chain correctness | Broken — run N+1 received stale state | Correct — run N+1 receives live post-sim state |

### 3.4 Call-Site Updates

All `generate()` call sites updated from 3-tuple to 4-tuple unpacking:

| File | Sites Updated |
|---|---|
| `tests/test_core/test_engagement_generator.py` | 22 |
| `tests/test_core/test_excel_exporter.py` | 1 |
| `tests/test_core/test_validation_engine.py` | 1 |
| `tests/test_e2e/test_historical_window_certification.py` | 4 |

---

## 4. Full Regression Results — Post-Remediation

| Suite | Tests | Pass | Fail |
|---|---|---|---|
| `tests/test_core/` | 743 | 743 | 0 |
| `tests/test_models/` | 57 | 57 | 0 |
| `tests/test_utils/` | 45 | 45 | 0 |
| `tests/test_e2e/test_business_rule_certification.py` | 68 | 68 | 0 |
| `tests/test_e2e/test_multitrigger_certification.py` | 46 | 46 | 0 |
| `tests/test_e2e/test_historical_window_certification.py` | 52 | 52 | 0 |
| `tests/test_e2e/test_multirun_persistence_certification.py` | 50 | 50 | 0 |
| **TOTAL** | **1,061** | **1,061** | **0** |

---

## 5. Sign-Off

Both defects are closed. The simulation pipeline now correctly propagates historical engagement status into capacity calculations (ARCH-RISK-003) and returns post-simulation state that accurately reflects journey completions, cooling periods, and lifetime engagement counters (ARCH-RISK-005). The multi-run chain is certified correct by 50 new tests across 10 scenario classes (MR-001 through MR-010).

**Remediation Author:** Stage 15 CTO / Principal Architect  
**Regression Verified:** 2026-06-23 — 1,061/1,061 pass  
