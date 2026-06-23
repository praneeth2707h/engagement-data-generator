# CLAUDE.md — Engagement Data Generator
## AI Session Context File

**Last Updated:** 2026-06-24  
**App Version:** 1.0.0 (certified) | Remediation Target: 2.0.0  
**Test Suite:** 1,111 tests — all passing as of v1.0.0 tag  
**Entry Point:** `app.py` (Streamlit) | Run: `streamlit run app.py`

---

## WHAT THIS PROJECT IS

A Streamlit desktop application that generates synthetic pharmaceutical marketing
engagement data. Users upload a trigger file (list of HCPs/patients), configure
a multi-channel ad campaign, and receive a simulated engagement dataset as an
Excel workbook.

Stack: Python 3.10, Streamlit, pandas, openpyxl. No database — pure in-memory
simulation with file-based state persistence via Excel/CSV.

---

## CURRENT STATE

**v1.0.0 is production-certified.** Stages 12–16 certified. 1,111 tests pass.

**13 production defects were identified post-deployment.** No source code has been
changed yet. All remediation is in the planning phase.

**You are most likely here to implement one of the 5 remediation waves.**

---

## CRITICAL FILES — READ THESE FIRST

| File | When to Read |
|------|-------------|
| `docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md` | **ALWAYS first** — 35 binding business rule decisions. Never make an assumption without checking here. |
| `docs/remediation/ARCHITECTURE_REMEDIATION_PACKAGE.md` | Before any implementation — full defect register, pipeline changes, new components |
| `docs/remediation/IMPLEMENTATION_WAVES.md` | To understand which wave you're in and what exit criteria apply |
| `docs/governance/PROJECT_DECISIONS.md` | For any architectural decision — highest-authority document |
| `docs/governance/USER_STATE_DICTIONARY.md` | Before touching any UserState field — authoritative field definitions |

---

## THE 13 DEFECTS — QUICK REFERENCE

| ID | Title | Wave | Architecture Doc |
|----|-------|------|-----------------|
| CRIT-001 | Historical journey continuation | 3 | `HISTORICAL_PROCESSING_REMEDIATION.md` |
| CRIT-002 | Trigger-specific journeys | 2 | `TRIGGER_JOURNEY_REMEDIATION.md` |
| CRIT-003 | Historical audience continuity | 3 | `USER_STATE_REMEDIATION.md` |
| CRIT-004 | Historical state reconstruction | 3 | `HISTORICAL_PROCESSING_REMEDIATION.md` |
| CRIT-005 | Cooling period from history | 3 | `USER_STATE_REMEDIATION.md` |
| CRIT-006 | Cooling period override | 4 | `USER_STATE_REMEDIATION.md` |
| CRIT-007 | CTR/TER accuracy at low targets | 4 | `TRIGGER_JOURNEY_REMEDIATION.md` |
| CRIT-008 | Journey progression gating | 4 | `TRIGGER_JOURNEY_REMEDIATION.md` |
| HIGH-001 | Canonical schema | 1 | `DATA_MODEL_REMEDIATION.md` |
| HIGH-002 | Upload validation alignment | 1 | `DATA_MODEL_REMEDIATION.md` |
| HIGH-003 | User_ID type safety (dtype=str) | 1 | `DATA_MODEL_REMEDIATION.md` |
| HIGH-004 | Journey status gate in events | 2 | `TRIGGER_JOURNEY_REMEDIATION.md` |
| HIGH-005 | Historical schema extension | 1 | `DATA_MODEL_REMEDIATION.md` |

All architecture docs are in `docs/remediation/`.

---

## SIMULATION PIPELINE (6 STAGES)

```
Pre-Stage 1 [NEW]:  HistoricalStateReconstructor.reconstruct()   → reconstructed_state_df
Stage 1:            UserStateManager.initialize_user_states()     → state_df  (3-way merge)
  [NEW injection]:  Augment audience with historically-active users absent from trigger_df
Stage 2:            AudienceManager.resolve()                     → audience_df
Post-Stage 2 [NEW]: CoolingOverrideService.apply()               → audience_df
Stage 3:            EngagementGenerator.generate()               → (events_df, metrics_df, diag_df, df)
Stage 4:            ValidationEngine.validate()                   → validation_result
Stage 5:            ExcelExporter.export()                        [optional]
Stage 6:            UserStateManager.finalize_state()             → final_state_df
```

---

## NEW COMPONENTS TO CREATE (none exist yet)

| File | Wave | Purpose |
|------|------|---------|
| `utils/canonical_schema.py` | 1 | Authoritative column name registry |
| `core/trigger_journey_resolver.py` | 2 | Per-trigger JourneyEngine factory |
| `core/historical_state_reconstructor.py` | 3 | Reconstruct UserState from 8-col historical file |
| `core/cooling_override_service.py` | 4 | Force COOLING → RE_ENTRY when `cooling_override=True` |
| `tests/test_utils/test_canonical_schema.py` | 1 | CanonicalSchema unit tests |
| `tests/test_core/test_trigger_journey_resolver.py` | 2 | TriggerJourneyResolver unit tests |
| `tests/test_core/test_historical_state_reconstructor.py` | 3 | Reconstructor unit tests |
| `tests/test_core/test_cooling_override_service.py` | 4 | CoolingOverrideService unit tests |
| `tests/test_e2e/test_remediation_certification.py` | 5 | Acceptance criteria for all 13 defects |

---

## KEY DATA MODEL FACTS

- `ConfigRegistry` is a **frozen dataclass**. `ads: tuple[AdConfig, ...]` is the global campaign-level ad journey.
- `TriggerConfig` currently has 4 fields only. Gets a new `ads: tuple[AdConfig, ...] | None = None` field (CRIT-002).
- `UserState` gets 3 new fields: `journey_step: int | None`, `trigger_ads_key: str | None`, `cooling_override_applied: bool`.
- `TRIGGER_HISTORY_DELIMITER = "|"` — defined in `utils/constants.py`.
- All `User_ID` values must be `str` throughout the pipeline. `upload_page.py` currently reads without `dtype=str` (HIGH-003 bug).
- `EligibilityStatus`: NEW, ACTIVE, COOLING, RE_ENTRY, SKIPPED, EXCLUDED (+ deprecated ELIGIBLE, INELIGIBLE, COMPLETED).
- `JourneyStatus`: NOT_STARTED, ACTIVE, COMPLETED, DROPPED.

---

## BINDING BUSINESS RULES — TOP 10

Full 35-decision register: `docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md`

Most likely to cause implementation errors:

1. **Priority tie-break** → alphabetic by trigger_name (case-insensitive, ascending). Decision 1.1.
2. **Multi-trigger conflict** → one journey per user; highest priority wins; lower-priority entry discarded. Decision 2.1.
3. **Active user re-triggered same trigger** → new entry discarded; journey continues. Decision 4.1.
4. **Active user re-triggered higher-priority trigger** → current journey DROPPED; new journey starts Ad_1. Decision 4.2.
5. **DROPPED journey** → NO cooling; immediately re-triggerable; allow_reentry does NOT apply. Decision 5.3.
6. **Cooling boundary** → `as_of_date >= cooling_period_end` → RE_ENTRY (inclusive). Decision 7.1.
7. **allow_reentry=False order** → evaluated BEFORE cooling; EXCLUDED immediately. Decision 7.2.
8. **cooling_override + allow_reentry=False** → no-op; state unchanged. Decision 8.1.
9. **previous_state_df priority** → absolute; historical reconstruction NEVER overrides it. Decision 14.1.
10. **trigger_ads_key drift** → ad sequence changed between runs → reset journey to Ad_1 with WARNING. Decision 14.3.

---

## TEST SUITE

```bash
# Run all tests
cd engagement_data_generator
pytest tests/ -x

# Run E2E only
pytest tests/test_e2e/ -x

# Run fast (skip scale tests)
pytest tests/ -x -m "not slow"
```

Current state: 1,111 tests, all passing. Do NOT break any existing test without explicit justification tied to a defect fix.

The only test fixture update that is EXPECTED when implementing HIGH-003: change integer User_IDs to string User_IDs across all test fixtures.

---

## WAVE IMPLEMENTATION ORDER

**Never skip a wave. Each wave has an exit criteria checklist in `docs/remediation/IMPLEMENTATION_WAVES.md`.**

| Wave | Defects | Key New File |
|------|---------|-------------|
| 1 | HIGH-001, 002, 003, 005 | `utils/canonical_schema.py` |
| 2 | CRIT-002, HIGH-004 | `core/trigger_journey_resolver.py` |
| 3 | CRIT-001, 003, 004, 005 | `core/historical_state_reconstructor.py` |
| 4 | CRIT-006, 007, 008 | `core/cooling_override_service.py` |
| 5 | All (validation + UI + tests) | `tests/test_e2e/test_remediation_certification.py` |

Wave 1 entry gate: confirm awareness of TDM-001 Decisions 1.1, 1.2, 3.1, 3.2.

---

## BACKWARD COMPATIBILITY

Only **one breaking change** across all 5 waves: `dtype=str` in `upload_page.py` (HIGH-003).

Action required: update all test fixtures using integer User_IDs to use string User_IDs.

All other changes are additive — new optional fields with defaults, new modules, new optional parameters.

---

## PERFORMANCE BASELINE (DO NOT REGRESS)

From Stage 16 certification:
- 1,000 users × 30-day simulation: < 3.0 seconds
- 10,000 users × 30-day simulation: < 25 seconds
- Full regression: 1,111 tests in < 120 seconds

Guard: `tests/test_e2e/test_scale_certification.py` — must pass after every wave.

---

## COLUMN NAME QUICK REFERENCE

Current (broken) state: column names defined independently in 4 places.  
After Wave 1: all column names come from `utils/canonical_schema.py`.

Key external (file-facing) names: `User_ID`, `Trigger_Name`, `Trigger_Date`, `Segment`, `Campaign_ID`, `Ad_Name`, `Journey_Step`, `Completion_Date`  
Key internal (DataFrame) names: `user_id`, `trigger_name`, `segment`, `campaign_id`, `journey_step`

---

*CLAUDE.md | Engagement Data Generator | v2.0.0-planning | 2026-06-24*
