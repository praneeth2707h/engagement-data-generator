# IMPLEMENTATION WAVES
## Engagement Data Generator — Phased Implementation Plan

**Document ID:** IWP-001  
**Version:** 1.0  
**Date:** 2026-06-23  
**Parent:** ARCHITECTURE_REMEDIATION_PACKAGE.md (ARP-001)

---

## OVERVIEW

The 13 defects are remediated across five sequential waves. Each wave builds on the previous one. No wave may begin until the prior wave's exit criteria are fully satisfied and verified. Each wave has a dedicated test run requirement — all existing tests must continue to pass at the end of every wave.

| Wave | Name | Defects | Est. Effort |
|------|------|---------|-------------|
| Wave 1 | Foundation — Schema & Type Safety | HIGH-001, HIGH-002, HIGH-003, HIGH-005 | 2–3 days |
| Wave 2 | Data Model — Trigger Journeys & State Fields | CRIT-002, HIGH-004 | 2–3 days |
| Wave 3 | Historical Processing | CRIT-001, CRIT-003, CRIT-004, CRIT-005 | 4–5 days |
| Wave 4 | Business Logic — CTR, Cooling Override, Gating | CRIT-006, CRIT-007, CRIT-008 | 3–4 days |
| Wave 5 | Validation, UI, Testing | All (validation rules + UI) | 2–3 days |

**Total estimated effort:** 13–18 engineering days (solo full-time engineer).

---

## WAVE 1 — FOUNDATION: SCHEMA & TYPE SAFETY

### Objective

Establish the canonical schema authority and eliminate type safety gaps. No simulation logic changes in this wave. All changes are purely structural — imports, constants, and file-read parameters.

### Defects Addressed

- **HIGH-001:** Canonical schema missing
- **HIGH-002:** Upload validation inconsistency
- **HIGH-003:** User_ID type safety
- **HIGH-005:** Historical schema extension (schema definition only; implementation in Wave 3)

### Files to Create

| File | Action | Purpose |
|------|--------|---------|
| `utils/canonical_schema.py` | CREATE | Authoritative column name registry |
| `tests/test_utils/test_canonical_schema.py` | CREATE | Full unit coverage |

### Files to Modify

| File | Change | Defect |
|------|--------|--------|
| `utils/schema_validator.py` | Replace local column lists with imports from `CanonicalSchema` | HIGH-001 |
| `core/simulation_orchestrator.py` | Replace `_TRIGGER_REQUIRED_COLS` with `CanonicalSchema` import | HIGH-001 |
| `core/engagement_generator.py` | Replace `_STATE_REQUIRED_COLS` with `CanonicalSchema` import | HIGH-001 |
| `ui/upload_page.py` | Replace local column defs; add `dtype=str` to all reads | HIGH-002, HIGH-003 |
| `core/input_loader.py` | Add extended schema detection and column parsing | HIGH-005 |

### Complexity

LOW. Pure refactoring — no algorithmic changes. Risk of import cycles is low if `canonical_schema.py` imports nothing from the project.

### Validation Gate

After Wave 1 completes:
1. Run `grep -r '"Campaign_ID"\|"User_ID"\|"Trigger_Name"\|"Trigger_Date"\|"Segment"\|"Date"\|"Action"\|"Channel"' --include="*.py" engagement_data_generator/` — result must contain ONLY `canonical_schema.py` and test files.
2. Run `pytest tests/ -x` — all existing tests pass (1,111 tests, 0 failures).
3. `upload_page._read_upload()` with CSV containing integer User_IDs returns str-typed User_ID column.
4. `input_loader.load_historical_file()` correctly parses extended schema columns when present.

### Exit Criteria

- [ ] `utils/canonical_schema.py` exists and exports all constants defined in `DATA_MODEL_REMEDIATION.md` Section 4.1.
- [ ] `schema_validator.py` has zero local column name string literals (verified by grep).
- [ ] `upload_page.py` uses `dtype=str` in both CSV and Excel reads.
- [ ] `upload_page.py` validates against `CanonicalSchema.TRIGGER_FILE_REQUIRED_COLUMNS` and `HISTORICAL_FILE_REQUIRED_COLUMNS`.
- [ ] `tests/test_utils/test_canonical_schema.py` all tests pass.
- [ ] Full regression 1,111/1,111 PASS.

### Risks

| Risk | Mitigation |
|------|-----------|
| `canonical_schema.py` import creates circular dependency | Ensure `canonical_schema.py` imports only Python stdlib (no project imports) |
| `dtype=str` breaks existing upload page tests | Update test fixtures to use str User_IDs |
| `schema_validator.py` column lists change length | Run full test suite; any broken validation tests surface immediately |

---

## WAVE 2 — DATA MODEL: TRIGGER JOURNEYS & STATE FIELDS

### Objective

Add trigger-specific journey capability to the data model and fix the journey-status event generation bug. At the end of this wave, the engine correctly partitions users into per-trigger cohorts during journey advancement.

### Defects Addressed

- **CRIT-002:** Trigger-specific journeys (data model + engine routing)
- **HIGH-004:** Journey status in events (BehaviorEngine gate)

### Files to Create

| File | Action | Purpose |
|------|--------|---------|
| `core/trigger_journey_resolver.py` | CREATE | Per-trigger JourneyEngine factory |
| `tests/test_core/test_trigger_journey_resolver.py` | CREATE | Full unit coverage |

### Files to Modify

| File | Change | Defect |
|------|--------|--------|
| `models/trigger_config.py` | Add `ads: tuple[AdConfig, ...] | None = None` field | CRIT-002 |
| `models/user_state.py` | Add `journey_step`, `trigger_ads_key`, `cooling_override_applied` fields | CRIT-002 |
| `core/journey_engine.py` | Add `ads_override` parameter; write `journey_step` on advance | CRIT-002 |
| `core/engagement_generator.py` | Use `TriggerJourneyResolver`; per-trigger cohort loop | CRIT-002 |
| `core/behavior_engine.py` | Add `journey_status=Active` gate at entry of `generate_events()` | HIGH-004 |
| `core/user_state_manager.py` | Reconcile new UserState fields in `_reconcile_columns()` | CRIT-002 |
| `models/config_registry.py` | Add per-trigger ad validation in `__post_init__` | CRIT-002 |
| `core/config_loader.py` | Parse trigger-level ads from config dict | CRIT-002 |
| `ui/campaign_page.py` | Add per-trigger custom ad sequence UI | CRIT-002 |

### Complexity

MEDIUM. JourneyEngine change is additive (optional parameter). EngagementGenerator daily loop refactoring requires care to preserve state DataFrame integrity across the cohort reassembly step.

### Critical Path

1. `models/trigger_config.py` — add `ads` field (no tests break)
2. `models/user_state.py` — add 3 fields with defaults (no tests break)
3. `core/journey_engine.py` — add `ads_override` param (backward compatible)
4. `core/trigger_journey_resolver.py` — new service (no tests break)
5. `core/engagement_generator.py` — refactor daily loop (may break existing generator tests)
6. `core/behavior_engine.py` — add journey_status gate (may break tests asserting NOT_STARTED events)
7. Fix any broken tests.

### Validation Gate

After Wave 2 completes:
1. `pytest tests/test_models/ -x` — all model tests pass.
2. `pytest tests/test_core/test_journey_engine.py -x` — all engine tests pass.
3. `pytest tests/test_core/test_engagement_generator.py -x` — all tests pass.
4. `pytest tests/ -x` — full regression 1,111+new PASS.
5. End-to-end test: given Trigger_A with custom ads [Ad_A1, Ad_A2] and Trigger_B with campaign-level ads [Ad_B], confirm Trigger_A users never receive events on Ad_B.

### Exit Criteria

- [ ] `TriggerConfig.ads = None` by default; triggers with custom ads work end-to-end.
- [ ] `JourneyEngine(config, ads_override=(...))` uses override ads in all lookups.
- [ ] `TriggerJourneyResolver` builds one engine per trigger; returns correct engine per trigger_name.
- [ ] EngagementGenerator per-trigger cohort reassembly preserves row count: `len(after) == len(before)` on every day.
- [ ] `BehaviorEngine.generate_events()` produces zero events for NOT_STARTED users.
- [ ] `events_df` contains zero rows with `journey_status=Not_Started` in any simulation.
- [ ] `UserState.new()` initializes all three new fields.
- [ ] `UserStateManager` reconciliation fills new fields from legacy state_df.
- [ ] Full regression PASS.

### Risks

| Risk | Mitigation |
|------|-----------|
| Per-trigger cohort groupby drops rows with null trigger_name | `groupby(dropna=False)` handles null; routes to default engine |
| State DataFrame index corrupted after groupby/concat | Use `sort_index()` after `pd.concat`; assert index integrity |
| config_loader fails to parse trigger-level ads | Add explicit test for config dict with trigger ads; fallback to None gracefully |

---

## WAVE 3 — HISTORICAL PROCESSING

### Objective

Implement the full historical data pipeline: state reconstruction from extended historical schema, audience augmentation with historically-active users, and cooling period derivation from historical completion records.

### Defects Addressed

- **CRIT-001:** Historical Journey Continuation
- **CRIT-003:** Historical Audience Continuity
- **CRIT-004:** Historical State Reconstruction
- **CRIT-005:** Cooling Period from History

### Files to Create

| File | Action | Purpose |
|------|--------|---------|
| `core/historical_state_reconstructor.py` | CREATE | Full HistoricalStateReconstructor implementation |
| `tests/test_core/test_historical_state_reconstructor.py` | CREATE | Full unit coverage |

### Files to Modify

| File | Change | Defect |
|------|--------|--------|
| `core/simulation_orchestrator.py` | Pre-Stage 1 reconstruction; audience augmentation | CRIT-001, CRIT-003 |
| `core/user_state_manager.py` | Three-way merge; `reconstructed_state_df` parameter | CRIT-004 |
| `models/simulation_result.py` | Add `reconstruction_summary: dict | None` field | CRIT-001 |
| `ui/upload_page.py` | Show extended schema detection message | CRIT-001 |
| `ui/results_page.py` | Show reconstruction summary | CRIT-001 |

### Complexity

HIGH. The `HistoricalStateReconstructor` involves complex per-user reconstruction logic. The three-way merge priority must be implemented correctly. Audience augmentation requires synthesizing trigger_df rows that satisfy all downstream validation.

### Critical Path

1. `core/historical_state_reconstructor.py` — implement and test in isolation.
2. `core/user_state_manager.py` — three-way merge (can be unit-tested independently).
3. `core/simulation_orchestrator.py` — wire pre-Stage 1; wire audience augmentation.
4. `models/simulation_result.py` — add `reconstruction_summary` field.
5. UI updates (upload_page, results_page) — low risk.

### Validation Gate

After Wave 3 completes:
1. `pytest tests/test_core/test_historical_state_reconstructor.py -x` — all pass.
2. `pytest tests/test_e2e/test_historical_window_certification.py -x` — all pass including new HW-011 through HW-015.
3. End-to-end test: simulation with 8-column historical file containing 5 active users; `events_df` contains records for all 5 historical users.
4. End-to-end test: simulation with 4-column historical file; behavior identical to pre-Wave-3 baseline.
5. Full regression PASS.

### Exit Criteria

- [ ] `HistoricalStateReconstructor.reconstruct()` correctly classifies Active/Cooling/RE_ENTRY users.
- [ ] `days_in_ad` capped correctly at `ad.duration_days - 1`.
- [ ] Three-way merge: previous_state_df > reconstructed_state_df > UserState.new().
- [ ] Historically-active users absent from trigger_df appear in simulation output.
- [ ] 4-column historical file produces identical results to pre-Wave-3 baseline.
- [ ] `SimulationResult.reconstruction_summary` populated when reconstruction runs.
- [ ] Full regression PASS (1,111 + new tests).

### Risks

| Risk | Mitigation |
|------|-----------|
| Reconstruction classifies user incorrectly (Active when should be Cooling) | Deterministic unit tests with exact dates and cooling_period_days values |
| Audience augmentation synthetic trigger rows fail validation | Include all required columns in `_augment_trigger_df`; test against pipeline validation |
| Three-way merge introduces duplicate user_id rows | Assert uniqueness of `user_id` after merge; raise SimulationError if violated |
| Performance regression from historical groupby on large files | Benchmark 100k historical rows; cap warning at >30s |

---

## WAVE 4 — BUSINESS LOGIC: CTR ACCURACY, COOLING OVERRIDE, GATING

### Objective

Fix CTR/TER accuracy at low targets, implement cooling period override, and add journey progression gating validation.

### Defects Addressed

- **CRIT-006:** Cooling Period Override
- **CRIT-007:** CTR/TER Accuracy
- **CRIT-008:** Journey Progression Gating (ValidationEngine rules)

### Files to Create

| File | Action | Purpose |
|------|--------|---------|
| `core/cooling_override_service.py` | CREATE | CoolingOverrideService implementation |
| `tests/test_core/test_cooling_override_service.py` | CREATE | Full unit coverage |

### Files to Modify

| File | Change | Defect |
|------|--------|--------|
| `core/engagement_generator.py` | TCC floor `max(1,...)`; boost cohort selection | CRIT-007 |
| `core/behavior_engine.py` | Accept `boost_user_ids`; apply `boost_multiplier=3.0` | CRIT-007 |
| `core/simulation_orchestrator.py` | Wire CoolingOverrideService post-Stage 2 | CRIT-006 |
| `core/validation_engine.py` | Add VR-J001 through VR-J005 | CRIT-008 |
| `models/config_registry.py` | Add `cooling_override: bool = False` field | CRIT-006 |
| `core/config_loader.py` | Parse `cooling_override` from config dict | CRIT-006 |
| `ui/business_rules_page.py` | Add "Override Cooling Period" toggle | CRIT-006 |

### Complexity

MEDIUM. CTR redesign is the most complex change — requires careful calibration of the boost multiplier to achieve ±20% CTR accuracy without over-generating events. CoolingOverrideService is simple. ValidationEngine rules are straightforward.

### Critical Path

1. `core/cooling_override_service.py` — simple; implement and test first.
2. `core/simulation_orchestrator.py` — wire CoolingOverrideService (low risk).
3. `core/engagement_generator.py` TCC floor — one-line change; test immediately.
4. `core/engagement_generator.py` boost cohort — implement and calibrate.
5. `core/behavior_engine.py` boost multiplier — implement and calibrate.
6. `core/validation_engine.py` VR-J001 through VR-J005.

### CTR Calibration Protocol

After implementing boost cohort + multiplier:
1. Run simulation with N=1,000 users, TER=2%, 7-day window, Display channel.
2. Measure observed CTR = n_clicks / n_impressions.
3. Target: CTR ∈ [1.6%, 2.4%] (±20% of 2%).
4. If CTR < 1.6%: increase `boost_multiplier` or `capacity * 2` cohort selection factor.
5. If CTR > 2.4%: decrease multiplier.
6. Repeat at TER=5%, TER=10%, TER=20% to ensure calibration holds across the range.

The calibration target for `boost_multiplier` is expected to be in the range 2.5–4.0. Document the chosen value and calibration run results in the STAGE_17_REMEDIATION_CERTIFICATION report.

### Validation Gate

After Wave 4 completes:
1. `pytest tests/test_core/test_cooling_override_service.py -x` — all pass.
2. `pytest tests/test_core/test_validation_engine.py -x` — all pass including new VR-J001 through VR-J005 tests.
3. CTR calibration: observed CTR ∈ [target×0.8, target×1.2] for TER ∈ {2%, 5%, 10%, 20%}.
4. `pytest tests/ -x` — full regression PASS.

### Exit Criteria

- [ ] `CoolingOverrideService.apply(df, True)` converts all COOLING+Completed users to RE_ENTRY.
- [ ] `ConfigRegistry.cooling_override = False` default; UI toggle correctly sets it.
- [ ] TCC floor: `remaining_capacity ≥ 1` when `engagement_rate_target > 0`.
- [ ] Observed CTR ≥ 1% (non-zero) at TER=2% with historically engaged users filling TCC.
- [ ] VR-J001 fires for click-gated journeys with causal chain violations.
- [ ] VR-J002 fires for NOT_STARTED events (should be zero after HIGH-004 fix).
- [ ] VR-J003, VR-J004 fire as Soft rules when CTR/TER outside ±20%.
- [ ] VR-J005 fires for duplicate event rows.
- [ ] Full regression PASS.

### Risks

| Risk | Mitigation |
|------|-----------|
| Boost multiplier too high → CTR dramatically overshoots target | Calibrate with CTR validation tests; assert upper bound |
| Boost cohort selection non-deterministic | Sort by `(engagement_score DESC, user_id ASC)` for determinism |
| VR-J001 false positive on valid journeys | Extensive test coverage; gate explicitly on `move_on_click=True` per ad |
| Cooling override and allow_reentry interaction | Unit test all 4 combinations explicitly |

---

## WAVE 5 — VALIDATION, UI, TESTING

### Objective

Complete the UI changes, write all end-to-end certification tests, verify full performance regression, and produce the Stage 17 certification report.

### Defects Addressed

All 13 defects — validation rules, UI, end-to-end acceptance tests.

### Files to Create

| File | Action | Purpose |
|------|--------|---------|
| `tests/test_e2e/test_remediation_certification.py` | CREATE | Acceptance-criteria tests for all 13 defects |
| `STAGE_17_REMEDIATION_CERTIFICATION.md` | CREATE | Final certification report |

### Files to Modify

| File | Change | Scope |
|------|--------|-------|
| `ui/results_page.py` | Add reconstruction summary display | CRIT-001 |
| `ui/upload_page.py` | Add extended schema detection message | CRIT-001 |
| `tests/test_core/test_engagement_generator.py` | Update TCC assertions for floor change | CRIT-007 |
| `tests/test_e2e/test_historical_window_certification.py` | Add HW-011 through HW-015 | CRIT-001..005 |
| `tests/test_e2e/test_multitrigger_certification.py` | Add MT-011, MT-012 | CRIT-002 |
| All existing tests with int User_ID fixtures | Update to str User_IDs | HIGH-003 |

### Wave 5 Test Design Requirements

`tests/test_e2e/test_remediation_certification.py` must include one test class per defect:

| Class | Defect | Tests |
|-------|--------|-------|
| `TestRC001HistoricalJourneyContinuation` | CRIT-001 | 5 tests |
| `TestRC002TriggerSpecificJourneys` | CRIT-002 | 5 tests |
| `TestRC003HistoricalAudienceContinuity` | CRIT-003 | 4 tests |
| `TestRC004HistoricalStateReconstruction` | CRIT-004 | 5 tests |
| `TestRC005CoolingFromHistory` | CRIT-005 | 4 tests |
| `TestRC006CoolingOverride` | CRIT-006 | 4 tests |
| `TestRC007CTRTERAccuracy` | CRIT-007 | 5 tests |
| `TestRC008JourneyGating` | CRIT-008 | 4 tests |
| `TestRC009CanonicalSchema` | HIGH-001 | 3 tests |
| `TestRC010UploadValidation` | HIGH-002 | 3 tests |
| `TestRC011UserIDTypeSafety` | HIGH-003 | 3 tests |
| `TestRC012JourneyStatusEvents` | HIGH-004 | 3 tests |
| `TestRC013HistoricalSchemaExtension` | HIGH-005 | 4 tests |

Total: 57 new end-to-end acceptance-criteria tests.

### Performance Regression Gate

Before producing the certification report:
1. Re-run `pytest tests/test_e2e/test_scale_certification.py -x`.
2. Assert all 50 existing scale tests pass.
3. Assert no SLA is degraded (PF-001 through PF-010 all pass).
4. If any SLA is exceeded, identify the responsible Wave 2–4 change and optimize before certifying.

### Exit Criteria

- [ ] `test_remediation_certification.py` 57/57 tests PASS.
- [ ] Full regression (1,111 + 57 + new unit tests) PASS with 0 failures.
- [ ] `test_scale_certification.py` 50/50 PASS with no SLA degradation.
- [ ] No grep hits for local column-name string literals in production code.
- [ ] `STAGE_17_REMEDIATION_CERTIFICATION.md` written and filed with:
  - Pass/fail status for all 13 defects
  - CTR calibration data (observed vs target for each TER level)
  - Performance regression data (before/after for each PF class)
  - Sign-off: REMEDIATION CERTIFIED: YES/NO

### Risks

| Risk | Mitigation |
|------|-----------|
| Performance regression from per-trigger cohort loop | Profile with `tracemalloc` + `perf_counter`; optimize groupby if needed |
| Test count exceeds 45s bash timeout for large E2E tests | Apply class-level caching (same pattern as Stage 16) |
| New Hard validation rules fail existing E2E test simulations | Add `allow_validation_failures=True` option to existing E2E tests where appropriate |

---

## IMPLEMENTATION ORDER — STRICT SEQUENCE

```
Wave 1 → EXIT CRITERIA MET → Wave 2 → EXIT CRITERIA MET → Wave 3
→ EXIT CRITERIA MET → Wave 4 → EXIT CRITERIA MET → Wave 5
→ EXIT CRITERIA MET → REMEDIATION CERTIFIED
```

No parallel execution across waves. Within a wave, changes may be implemented in any order, but the wave's validation gate must pass before the next wave begins.

---

## FILE CHANGE SUMMARY

| File | Wave(s) | Action |
|------|---------|--------|
| `utils/canonical_schema.py` | 1 | CREATE |
| `utils/schema_validator.py` | 1 | MODIFY |
| `core/simulation_orchestrator.py` | 1, 3, 4 | MODIFY |
| `ui/upload_page.py` | 1, 3 | MODIFY |
| `core/input_loader.py` | 1 | MODIFY |
| `models/trigger_config.py` | 2 | MODIFY |
| `models/user_state.py` | 2 | MODIFY |
| `models/config_registry.py` | 2, 4 | MODIFY |
| `core/journey_engine.py` | 2 | MODIFY |
| `core/trigger_journey_resolver.py` | 2 | CREATE |
| `core/engagement_generator.py` | 2, 4 | MODIFY |
| `core/behavior_engine.py` | 2, 4 | MODIFY |
| `core/user_state_manager.py` | 2, 3 | MODIFY |
| `core/config_loader.py` | 2, 4 | MODIFY |
| `ui/campaign_page.py` | 2 | MODIFY |
| `core/historical_state_reconstructor.py` | 3 | CREATE |
| `models/simulation_result.py` | 3 | MODIFY |
| `ui/results_page.py` | 3, 5 | MODIFY |
| `core/cooling_override_service.py` | 4 | CREATE |
| `core/validation_engine.py` | 4 | MODIFY |
| `ui/business_rules_page.py` | 4 | MODIFY |
| `tests/test_utils/test_canonical_schema.py` | 1 | CREATE |
| `tests/test_core/test_trigger_journey_resolver.py` | 2 | CREATE |
| `tests/test_core/test_historical_state_reconstructor.py` | 3 | CREATE |
| `tests/test_core/test_cooling_override_service.py` | 4 | CREATE |
| `tests/test_e2e/test_remediation_certification.py` | 5 | CREATE |

---

## ACCEPTANCE SIGN-OFF CHECKLIST

After Wave 5 exits:

- [ ] Wave 1 exit criteria: verified
- [ ] Wave 2 exit criteria: verified
- [ ] Wave 3 exit criteria: verified
- [ ] Wave 4 exit criteria: verified
- [ ] Wave 5 exit criteria: verified
- [ ] 13 defects: all PASS in `test_remediation_certification.py`
- [ ] Full regression: 0 failures
- [ ] Scale tests: 50/50 PASS, no SLA degradation
- [ ] CTR calibration: documented
- [ ] `STAGE_17_REMEDIATION_CERTIFICATION.md`: filed and signed

**REMEDIATION COMPLETE: YES / NO** (to be determined after Wave 5)

---

*Document: IWP-001 | IMPLEMENTATION_WAVES.md | v1.0 | 2026-06-23*
