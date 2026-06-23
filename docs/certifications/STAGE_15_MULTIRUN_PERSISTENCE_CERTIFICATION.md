# Stage 15 — Multi-Run Persistence Certification

**Report Date:** 2026-06-23  
**Certification Author:** CTO / Principal Architect / QA Director / Independent Auditor / Release Manager  
**Verdict:** ✅ CERTIFIED — PASS  

---

## 1. Scope

This report certifies that the PharmaForce IQ engagement simulation platform correctly persists all user state across multi-run campaign chains. A "multi-run chain" is defined as two or more sequential calls to `SimulationOrchestrator.run()` where each run passes its `SimulationResult.state_df` as the `previous_state_df` of the next run.

Persistence dimensions certified:

1. **State schema** — required columns present and populated across all runs  
2. **Run count** — `run_count` increments correctly for returning users  
3. **Journey persistence** — `journey_status`, `current_ad`, `days_in_ad`, `cooling_period_end` survive handoff  
4. **Cooling persistence** — cooling users correctly classified and excluded from qualifying events  
5. **Re-entry persistence** — `allow_reentry` flag governs re-classification after cooling expires  
6. **Trigger history** — `trigger_history`, `first_trigger_name`, `total_trigger_appearances` accumulate correctly  
7. **Engagement counters** — `total_lifetime_engagements`, `historical_engaged`, `engagement_score` are non-decreasing and survive handoff  
8. **Workbook multi-run** — Excel export is valid in run N+1 with `previous_state_df`  
9. **Determinism** — identical input chains produce bit-identical `events_df`, `state_df`, and `workbook_bytes`  
10. **New user coexistence** — new users introduced in run N+1 initialize correctly alongside returning users  

---

## 2. Architecture Findings

Two architectural defects were discovered during Stage 15 investigation and remediated before certification. Both defects directly impacted multi-run correctness.

### ARCH-RISK-003 — Historical Engagement Not Wired Into Simulation

**File:** `core/simulation_orchestrator.py`  
**Root cause:** `AudienceManager.resolve()` returns `(audience_df, capacity)`. The orchestrator discarded `capacity` and never stamped `historical_engaged=True` on `audience_df` rows matching the windowed `historical_df`. Every user was treated as a first-time user regardless of prior engagement history.  
**Fix:** Post-Stage 2, orchestrator filters `historical_df` to the configured window and directly sets `audience_df.loc[..., "historical_engaged"] = True` for matching users.  
**Full details:** `ARCH_RISK_003_REMEDIATION_REPORT.md`

### ARCH-RISK-005 — Post-Simulation State Discarded

**File:** `core/engagement_generator.py` + `core/simulation_orchestrator.py`  
**Root cause:** `EngagementGenerator.generate()` returned a 3-tuple `(events_df, metrics_df, diag_df)` and discarded the internal `df` variable containing the post-simulation state (journey completions, updated cooling periods, updated lifetime counters). The orchestrator then passed the pre-simulation `audience_df` to `finalize_state()`, so `SimulationResult.state_df` never reflected any simulation activity.  
**Fix:** `generate()` extended to 4-tuple `(events_df, metrics_df, diag_df, df)`. Orchestrator captures 4th element as `_final_sim_state` and passes it to `finalize_state()`.  
**Full details:** `ARCH_RISK_003_REMEDIATION_REPORT.md`

---

## 3. Test Suite — MR-001 through MR-010

### Test Infrastructure

**File:** `tests/test_e2e/test_multirun_persistence_certification.py`  
**Total scenarios:** 10 classes × 5 tests = **50 tests**  
**Run configuration:**

- Campaign: `TEST_CAMPAIGN`, 20 users (`U001`–`U020`)
- Journey: 2 ads (Ad_A: Display, 2 days, move_on_click=True; Ad_B: Email, 2 days)
- Run 1: 2024-01-01 → 2024-01-07
- Run 2: 2024-01-08 → 2024-01-14
- Run 3: 2024-01-15 → 2024-01-21
- Default: cooling_period_days=5, target_rate=0.50, allow_reentry=True

---

### MR-001: State Schema Persistence

| Test | Description | Result |
|---|---|---|
| S01 | Run 1 state_df has all required columns | PASS |
| S02 | Run 2 state_df has all required columns | PASS |
| S03 | Run 3 state_df has all required columns | PASS |
| S04 | All run-1 user_ids present in run-2 state | PASS |
| S05 | campaign_id consistent across all runs | PASS |

All 9 required columns (`campaign_id`, `user_id`, `eligibility_status`, `journey_status`, `behavior_profile`, `engagement_score`, `state_as_of_date`, `historical_engaged`, `is_valid`) present in state_df after every run.

---

### MR-002: Run Count Persistence

| Test | Description | Result |
|---|---|---|
| S01 | run_count = 0 in run-1 state (first exposure) | PASS |
| S02 | Returning users have run_count = 1 after run 2 | PASS |
| S03 | Returning users have run_count = 2 after run 3 | PASS |
| S04 | New users added in run 2 have run_count = 0 | PASS |
| S05 | total_trigger_appearances increments each run | PASS |

`run_count` increments exactly once per run for returning users and initializes to 0 for users appearing for the first time.

---

### MR-003: Journey Persistence

| Test | Description | Result |
|---|---|---|
| S01 | journey_status present in run-1 state | PASS |
| S02 | Journey state carries forward to run 2 audience | PASS |
| S03 | Post-sim state includes journey completions (ARCH-RISK-005 verified) | PASS |
| S04 | cooling_period_end set for users who completed journey | PASS |
| S05 | current_ad / days_in_ad survive run boundary | PASS |

ARCH-RISK-005 fix confirmed: `SimulationResult.state_df` now reflects post-simulation journey status, including completions triggered during the run. Users who enter cooling have non-null `cooling_period_end` in the returned `state_df`.

---

### MR-004: Cooling Persistence

| Test | Description | Result |
|---|---|---|
| S01 | cooling_period_end survives state handoff | PASS |
| S02 | Users with cooling_period_end > sim_start classified as COOLING | PASS |
| S03 | COOLING users receive no qualifying events | PASS |
| S04 | cooling_period_end does not reset to null after run | PASS |
| S05 | Cooling users excluded from engagement count | PASS |

Cooling state is deterministically preserved across the run boundary. The `AudienceManager` correctly reads `cooling_period_end` from `previous_state_df` and classifies returning users as COOLING when the current `sim_start` precedes `cooling_period_end`.

---

### MR-005: Re-Entry Persistence

| Test | Description | Result |
|---|---|---|
| S01 | Users with allow_reentry=True re-enter after cooling expires | PASS |
| S02 | Users with allow_reentry=False remain EXCLUDED after cooling | PASS |
| S03 | Re-entry users can receive engagement events | PASS |
| S04 | Re-entry classification is consistent across multiple runs | PASS |
| S05 | allow_reentry=False forces permanent exclusion | PASS |

The `allow_reentry` configuration flag correctly governs post-cooling fate. When `cooling_period_end <= sim_start` and `allow_reentry=True`, users are classified RE_ENTRY and become eligible for new engagement. When `allow_reentry=False`, they are EXCLUDED for all subsequent runs.

---

### MR-006: Trigger History Persistence

| Test | Description | Result |
|---|---|---|
| S01 | trigger_history contains trigger name after run 1 | PASS |
| S02 | trigger_history accumulates with delimiter after run 2 | PASS |
| S03 | first_trigger_name is idempotent across all runs | PASS |
| S04 | total_trigger_appearances increments each run | PASS |
| S05 | Three-run chain: trigger_history = T1\|T1\|T1 | PASS |

Trigger history uses `TRIGGER_HISTORY_DELIMITER = "|"` (from `utils/constants.py`). After run N, `trigger_history` contains N pipe-delimited trigger names. `first_trigger_name` is stamped on first exposure and never overwritten. `total_trigger_appearances` equals the run index + 1 for continuously-triggered users.

---

### MR-007: Engagement Counter Persistence

| Test | Description | Result |
|---|---|---|
| S01 | total_lifetime_engagements > 0 for engaged users in run-1 state | PASS |
| S02 | TLE is non-decreasing across run boundary (run2 TLE >= run1 TLE) | PASS |
| S03 | historical_engaged flag survives state handoff | PASS |
| S04 | engagement_score carries forward from previous state | PASS |
| S05 | TLE accumulates additively across 3-run chain | PASS |

Engagement counters are cumulative and strictly non-decreasing. No counter resets to zero for returning users.

---

### MR-008: Workbook Multi-Run

| Test | Description | Result |
|---|---|---|
| S01 | Run 2 with previous_state_df produces non-null workbook_bytes | PASS |
| S02 | workbook_bytes is valid ZIP / XLSX | PASS |
| S03 | Run 2 events_df non-empty when users re-qualify (cooling_period_days=3) | PASS |
| S04 | quality_score in range [0, 100] | PASS |
| S05 | events_df contains trigger_name column | PASS |

`ExcelExporter` operates correctly on the post-ARCH-RISK-005 pipeline. Workbook generation succeeds when run with `previous_state_df` populated.

---

### MR-009: Determinism

| Test | Description | Result |
|---|---|---|
| S01 | Two identical run-1 executions produce identical events_df | PASS |
| S02 | Two identical run-1 executions produce identical state_df | PASS |
| S03 | Two identical 2-run chains produce identical run-2 events_df | PASS |
| S04 | Two identical 2-run chains produce identical run-2 state_df | PASS |
| S05 | workbook_bytes are byte-identical for identical inputs | PASS |

The `BehaviorEngine` seeds RNG from `MD5(user_id) + date.toordinal() + offset` (SIM-019). Given identical `trigger_df`, `previous_state_df`, and `ConfigRegistry`, outputs are bit-identical across independent invocations.

---

### MR-010: New User Coexistence

| Test | Description | Result |
|---|---|---|
| S01 | New users introduced in run 2 have run_count = 0 | PASS |
| S02 | New users classified NEW or SKIPPED, not COOLING/RE_ENTRY | PASS |
| S03 | Returning users continue to show run_count = 1 | PASS |
| S04 | New users have no prior trigger_history delimiter | PASS |
| S05 | first_trigger_name set for new users in run 2 | PASS |

`UserStateManager.initialize_user_states()` correctly segregates new users (not in `previous_state_df`) from returning users. New users receive fresh state initialization; returning users receive merged state from the prior run.

---

## 4. Stage 14 Re-Certification

Stage 14 historical window tests re-run after ARCH-RISK-003 and ARCH-RISK-005 fixes:

**`tests/test_e2e/test_historical_window_certification.py`**: **52/52 PASS**

ARCH-RISK-003 fix does not regress any HW-series test. Historical window filtering is correctly applied prior to `historical_engaged` stamping.

---

## 5. Full Regression Results — Post-Certification

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

## 6. Known Limitations

1. **FutureWarning — pandas fillna downcasting** in `core/journey_engine.py` lines 347, 352, 365. These are pandas deprecation notices, not failures. The behavior is correct under current pandas version. Resolution deferred to a pandas upgrade cycle.

2. **FutureWarning — DataFrame concatenation with all-NA entries** in `core/user_state_manager.py` line 222. Non-critical; behavior is correct. Deferred.

Both issues are pre-existing and unrelated to ARCH-RISK-003 or ARCH-RISK-005.

---

## 7. Release Readiness Decision — Part C

### PASS ✅

The platform is **approved for Stage 16 — Performance Certification**.

**Basis:**

- All 1,061 tests pass with 0 failures across all 4 certification suites and the full unit suite.
- ARCH-RISK-003 and ARCH-RISK-005 — both root causes of multi-run chain incorrectness — are fully remediated and regression-verified.
- `SimulationResult.state_df` now correctly reflects post-simulation state (journey completions, cooling periods, lifetime counters), making the multi-run chain architecturally sound.
- Determinism certification (MR-009) confirms the simulation engine is stable and reproducible under identical inputs, a prerequisite for performance benchmarking.
- Stage 14 historical window certification re-verified clean after ARCH-RISK-003 fix.
- No open defects. No conditional items blocking Stage 16.

**Signed:** Stage 15 Release Manager — 2026-06-23
