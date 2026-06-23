# GITHUB SYNC PACKAGE
## Engagement Data Generator — Repository Synchronization

**Document ID:** GSP-001  
**Version:** 1.0  
**Date:** 2026-06-24  
**Classification:** Release Engineering — Pre-Implementation Baseline  
**Status:** EXECUTE BEFORE WAVE 1 BEGINS  
**Prepared by:** Product Owner / Release Manager / CTO

---

## PURPOSE

This document is the authoritative checklist for synchronizing the local workspace with the GitHub repository before Wave 1 implementation begins. After execution, GitHub must be the single source of truth for:

- The certified v1.0 application source code (already on GitHub)
- All 8 v2.0 remediation architecture documents
- The TRIGGER_AND_REENTRY_DECISION_MATRIX.md (35 binding business rules)
- All stage certification reports (Stages 12–16)
- All project governance documents
- A `CLAUDE.md` context file for all future AI-assisted implementation sessions

**No source code changes are included in this sync.** Source code modifications begin in Wave 1. This commit is documentation-only.

---

## SECTION 1 — NEW FILES TO ADD

All files listed here are new additions. None exist on GitHub currently.

### 1.1 Remediation Architecture Package (8 documents — REQUIRED)

These are the binding engineering reference documents for the entire v2.0 remediation. Engineering must not begin Wave 1 without all 8 on GitHub.

| Local Path | GitHub Destination | Doc ID | Purpose |
|-----------|-------------------|--------|---------|
| `ARCHITECTURE_REMEDIATION_PACKAGE.md` | `docs/remediation/ARCHITECTURE_REMEDIATION_PACKAGE.md` | ARP-001 | Master document: 13 defects, pipeline changes, new components, acceptance criteria |
| `DATA_MODEL_REMEDIATION.md` | `docs/remediation/DATA_MODEL_REMEDIATION.md` | DMR-001 | CanonicalSchema, TriggerConfig.ads, UserState 3 new fields, extended historical schema |
| `USER_STATE_REMEDIATION.md` | `docs/remediation/USER_STATE_REMEDIATION.md` | USR-001 | HistoricalStateReconstructor, three-way merge, CoolingOverrideService, BehaviorEngine gate |
| `HISTORICAL_PROCESSING_REMEDIATION.md` | `docs/remediation/HISTORICAL_PROCESSING_REMEDIATION.md` | HPR-001 | 8-column historical schema, `_augment_trigger_df`, days_in_ad capping algorithm |
| `TRIGGER_JOURNEY_REMEDIATION.md` | `docs/remediation/TRIGGER_JOURNEY_REMEDIATION.md` | TJR-001 | TriggerJourneyResolver, JourneyEngine ads_override, TCC floor, boost cohort, VR-J001–J005 |
| `IMPLEMENTATION_WAVES.md` | `docs/remediation/IMPLEMENTATION_WAVES.md` | IWP-001 | 5-wave execution plan, exit criteria per wave, 26-file change summary |
| `TESTING_STRATEGY.md` | `docs/remediation/TESTING_STRATEGY.md` | TST-001 | 149 new unit tests + 57 E2E acceptance tests, fixture factories, CTR calibration design |
| `TRIGGER_AND_REENTRY_DECISION_MATRIX.md` | `docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md` | TDM-001 | **35 binding business rule decisions across 15 topic areas — sign-off required** |

### 1.2 Stage Certification Reports (6 documents — REQUIRED)

These are the production certification records for the v1.0 release. They serve as the baseline regression contract — any Wave implementation must not break results certified here.

| Local Path | GitHub Destination | Purpose |
|-----------|-------------------|---------|
| `ARCH_RISK_003_REMEDIATION_REPORT.md` | `docs/certifications/ARCH_RISK_003_REMEDIATION_REPORT.md` | Root-cause analysis and fix for historical_engaged stamping bug |
| `STAGE_12_END_TO_END_CERTIFICATION.md` | `docs/certifications/STAGE_12_END_TO_END_CERTIFICATION.md` | Full E2E pipeline certification |
| `STAGE_13_MULTITRIGGER_CERTIFICATION.md` | `docs/certifications/STAGE_13_MULTITRIGGER_CERTIFICATION.md` | Multi-trigger campaign certification |
| `STAGE_14_HISTORICAL_WINDOW_CERTIFICATION.md` | `docs/certifications/STAGE_14_HISTORICAL_WINDOW_CERTIFICATION.md` | Historical window modes certification |
| `STAGE_15_MULTIRUN_PERSISTENCE_CERTIFICATION.md` | `docs/certifications/STAGE_15_MULTIRUN_PERSISTENCE_CERTIFICATION.md` | Multi-run chain state persistence certification |
| `STAGE_16_PERFORMANCE_CERTIFICATION.md` | `docs/certifications/STAGE_16_PERFORMANCE_CERTIFICATION.md` | Scale and performance SLA certification |

### 1.3 Project Governance Documents (10 documents — REQUIRED)

These are the authoritative decision and tracking records. Future Claude Code sessions need these to understand prior decisions without re-reading execution logs.

| Local Path | GitHub Destination | Authority Level | Purpose |
|-----------|-------------------|----------------|---------|
| `PROJECT_DECISIONS.md` | `docs/governance/PROJECT_DECISIONS.md` | **HIGHEST** | All approved architecture and business decisions (ARCH-*, CFG-*, SIM-*, BIZ-*) |
| `PROJECT_MASTER_REGISTER.md` | `docs/governance/PROJECT_MASTER_REGISTER.md` | HIGH | Open items, defect register, remediation register, risk register |
| `PROJECT_RELEASE_PACKAGE.md` | `docs/governance/PROJECT_RELEASE_PACKAGE.md` | HIGH | v1.0 release certification, deployment instructions |
| `PROJECT_CHANGE_LOG.md` | `docs/governance/PROJECT_CHANGE_LOG.md` | MEDIUM | Chronological change history |
| `PROJECT_RISK_REGISTER.md` | `docs/governance/PROJECT_RISK_REGISTER.md` | MEDIUM | Active risks and mitigations |
| `PROJECT_BACKLOG.md` | `docs/governance/PROJECT_BACKLOG.md` | MEDIUM | Prioritized backlog and deferred items |
| `TRACEABILITY_MATRIX.md` | `docs/governance/TRACEABILITY_MATRIX.md` | HIGH | Requirement-to-implementation traceability |
| `USER_STATE_DICTIONARY.md` | `docs/governance/USER_STATE_DICTIONARY.md` | HIGH | Authoritative definition of all 35+ UserState fields |
| `RELEASE_GATES.md` | `docs/governance/RELEASE_GATES.md` | MEDIUM | Release quality gates and criteria |
| `REPOSITORY_CLEANUP_REPORT.md` | `docs/governance/REPOSITORY_CLEANUP_REPORT.md` | LOW | Historical cleanup audit record |

### 1.4 CLAUDE.md — AI Session Context File (CRITICAL)

**This is the most important file for continuity of AI-assisted implementation.** Every future Claude Code session working on this codebase must read `CLAUDE.md` first. See Section 6 for the complete file content.

| Local Path | GitHub Destination | Purpose |
|-----------|-------------------|---------|
| `CLAUDE.md` *(content in Section 6)* | `CLAUDE.md` (repo root) | Context file for Claude Code — project state, defect map, decision refs, implementation entry points |

---

## SECTION 2 — EXISTING FILES TO UPDATE

### 2.1 Source Code Files — NO CHANGES

**No source code files are modified in this sync commit.** The v1.0 certified source code on GitHub is unchanged. All 10 `core/` modules, all 11 `models/` modules, all `utils/`, `ui/`, and `tests/` files remain exactly as certified in Stage 16.

Source code modifications begin in **Wave 1** (after this commit is merged and signed off on `TRIGGER_AND_REENTRY_DECISION_MATRIX.md`).

### 2.2 README.md — UPDATE REQUIRED

`engagement_data_generator/README.md` must be updated to add a section pointing to the new `docs/` folder. Append the following block to the existing README:

```markdown
## Documentation

| Folder | Contents |
|--------|---------|
| `docs/remediation/` | v2.0 remediation architecture (8 documents). Start with `ARCHITECTURE_REMEDIATION_PACKAGE.md`. |
| `docs/certifications/` | Stage 12–16 certification reports and defect remediation records. |
| `docs/governance/` | Project decisions, defect register, risk register, traceability matrix. |

The `TRIGGER_AND_REENTRY_DECISION_MATRIX.md` in `docs/remediation/` is the binding business-rules authority for all Wave 1–5 implementation. Engineering must not make assumption-based decisions — all ambiguities are resolved there.

See `CLAUDE.md` at the repo root for AI-assisted implementation context.
```

### 2.3 .gitignore — CONFIRM CURRENT CONTENT IS PRESENT

Verify the `.gitignore` in the repo root contains all entries from the local `.gitignore`. The local file already covers all necessary exclusions (`__pycache__/`, `.coverage`, `.pytest_cache/`, `.streamlit/secrets.toml`). No change needed if the repo version matches.

---

## SECTION 3 — RECOMMENDED FOLDER STRUCTURE

The final repository structure after this sync commit:

```
engagement_data_generator/               ← GitHub repository root
│
├── CLAUDE.md                            ← NEW: AI session context (repo root)
├── README.md                            ← UPDATED: add docs/ section
├── app.py
├── requirements.txt
├── .gitignore
│
├── core/                                ← UNCHANGED (v1.0 certified)
│   ├── __init__.py
│   ├── audience_manager.py
│   ├── behavior_engine.py
│   ├── config_loader.py
│   ├── engagement_generator.py
│   ├── excel_exporter.py
│   ├── input_loader.py
│   ├── journey_engine.py
│   ├── simulation_orchestrator.py
│   ├── user_state_manager.py
│   └── validation_engine.py
│
├── models/                              ← UNCHANGED (v1.0 certified)
│   ├── __init__.py
│   ├── ad_config.py
│   ├── capacity_row.py
│   ├── channel_config.py
│   ├── config_registry.py
│   ├── enums.py
│   ├── rule_config.py
│   ├── segment_config.py
│   ├── simulation_result.py
│   ├── trigger_config.py
│   └── user_state.py
│
├── utils/                               ← UNCHANGED (v1.0 certified)
│   ├── __init__.py
│   ├── constants.py
│   ├── date_utils.py
│   ├── excel_utils.py
│   ├── exceptions.py
│   ├── logger.py
│   ├── schema_validator.py
│   └── version.py
│
├── ui/                                  ← UNCHANGED (v1.0 certified)
│   ├── __init__.py
│   ├── business_rules_page.py
│   ├── campaign_page.py
│   ├── results_page.py
│   ├── run_page.py
│   ├── state.py
│   └── upload_page.py
│
├── tests/                               ← UNCHANGED (1,111 passing tests)
│   ├── __init__.py
│   ├── test_core/
│   │   ├── conftest.py
│   │   ├── test_audience_manager.py
│   │   ├── test_behavior_engine.py
│   │   ├── test_config_loader.py
│   │   ├── test_engagement_generator.py
│   │   ├── test_excel_exporter.py
│   │   ├── test_input_loader.py
│   │   ├── test_journey_engine.py
│   │   ├── test_simulation_orchestrator.py
│   │   ├── test_user_state_manager.py
│   │   └── test_validation_engine.py
│   ├── test_e2e/
│   │   ├── test_business_rule_certification.py
│   │   ├── test_historical_window_certification.py
│   │   ├── test_multirun_persistence_certification.py
│   │   ├── test_multitrigger_certification.py
│   │   └── test_scale_certification.py
│   ├── test_models/
│   │   ├── test_ad_config.py
│   │   ├── test_capacity_row.py
│   │   ├── test_config_registry.py
│   │   ├── test_config_registry_weights.py
│   │   ├── test_enums.py
│   │   ├── test_segment_config.py
│   │   ├── test_trigger_config.py
│   │   └── test_user_state.py
│   ├── test_ui/
│   │   └── test_smoke.py
│   ├── test_utils/
│   │   └── test_schema_validator.py
│   └── unit/
│       └── test_date_utils.py
│
└── docs/                                ← NEW FOLDER (entire tree is new)
    ├── remediation/                     ← v2.0 remediation architecture
    │   ├── ARCHITECTURE_REMEDIATION_PACKAGE.md    (ARP-001 — read first)
    │   ├── DATA_MODEL_REMEDIATION.md              (DMR-001)
    │   ├── USER_STATE_REMEDIATION.md              (USR-001)
    │   ├── HISTORICAL_PROCESSING_REMEDIATION.md   (HPR-001)
    │   ├── TRIGGER_JOURNEY_REMEDIATION.md         (TJR-001)
    │   ├── IMPLEMENTATION_WAVES.md                (IWP-001)
    │   ├── TESTING_STRATEGY.md                    (TST-001)
    │   └── TRIGGER_AND_REENTRY_DECISION_MATRIX.md (TDM-001 — sign-off required)
    │
    ├── certifications/                  ← v1.0 production certification records
    │   ├── ARCH_RISK_003_REMEDIATION_REPORT.md
    │   ├── STAGE_12_END_TO_END_CERTIFICATION.md
    │   ├── STAGE_13_MULTITRIGGER_CERTIFICATION.md
    │   ├── STAGE_14_HISTORICAL_WINDOW_CERTIFICATION.md
    │   ├── STAGE_15_MULTIRUN_PERSISTENCE_CERTIFICATION.md
    │   └── STAGE_16_PERFORMANCE_CERTIFICATION.md
    │
    └── governance/                      ← project decisions and tracking
        ├── PROJECT_DECISIONS.md         ← highest authority document
        ├── PROJECT_MASTER_REGISTER.md
        ├── PROJECT_RELEASE_PACKAGE.md
        ├── PROJECT_CHANGE_LOG.md
        ├── PROJECT_RISK_REGISTER.md
        ├── PROJECT_BACKLOG.md
        ├── TRACEABILITY_MATRIX.md
        ├── USER_STATE_DICTIONARY.md
        ├── RELEASE_GATES.md
        └── REPOSITORY_CLEANUP_REPORT.md
```

### 3.1 Files Explicitly Excluded from This Commit

The following files exist in the local workspace but must NOT be committed:

| File(s) | Reason |
|---------|--------|
| `__pycache__/` (all) | Already in .gitignore |
| `.coverage`, `.coverage.*` | Already in .gitignore |
| `.pytest_cache/` (all) | Already in .gitignore |
| `PHASE_2_*.md`, `PHASE_3_*.md` | Session execution logs — not authoritative references; superseded by the 8 remediation docs |
| `WAVE_1_*.md` through `WAVE_6_*.md` | Session execution logs — superseded by IMPLEMENTATION_WAVES.md |
| `AUDIENCE_MANAGER_IMPLEMENTATION_REPORT.md` et al. | Per-component implementation logs — superseded by certification reports |
| `GOVERNANCE_SYNC_REPORT.md` | Point-in-time audit snapshot; not a living reference document |
| `REPOSITORY_VERIFICATION_REPORT.md` | One-time verification snapshot |
| `PROJECT_MEMORY.md` | Internal session notes; not a formal governance document |
| `WAVE_1_GOVERNANCE_AUTOMATION.md`, `WAVE_1_PRE_IMPLEMENTATION_BACKLOG_UPDATE.md` | Session-level execution notes |

---

## SECTION 4 — GIT COMMIT MESSAGE

Use this exact message for the sync commit. Paste verbatim into `git commit`:

```
docs: add v2.0 remediation architecture package and project documentation

Add complete v2.0 remediation architecture for 13 production defects
(CRIT-001..008, HIGH-001..005) identified in v1.0 post-deployment testing.
Also add v1.0 stage certification reports, project governance documents,
and CLAUDE.md AI context file.

No source code changes. This commit establishes the documentation baseline
required before Wave 1 implementation begins.

New documents:
  docs/remediation/ARCHITECTURE_REMEDIATION_PACKAGE.md  (ARP-001)
  docs/remediation/DATA_MODEL_REMEDIATION.md            (DMR-001)
  docs/remediation/USER_STATE_REMEDIATION.md            (USR-001)
  docs/remediation/HISTORICAL_PROCESSING_REMEDIATION.md (HPR-001)
  docs/remediation/TRIGGER_JOURNEY_REMEDIATION.md       (TJR-001)
  docs/remediation/IMPLEMENTATION_WAVES.md              (IWP-001)
  docs/remediation/TESTING_STRATEGY.md                  (TST-001)
  docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md (TDM-001)
  docs/certifications/  (6 v1.0 stage certification reports)
  docs/governance/      (10 project governance and decision documents)
  CLAUDE.md             (AI session context — read first in new sessions)

Updated:
  README.md             (add docs/ navigation section)

Remediation scope:
  CRIT-001  Historical journey continuation (HistoricalStateReconstructor)
  CRIT-002  Trigger-specific journeys (TriggerJourneyResolver)
  CRIT-003  Historical audience continuity (audience augmentation)
  CRIT-004  Historical state reconstruction (new service)
  CRIT-005  Cooling period from history (completion date derivation)
  CRIT-006  Cooling period override (CoolingOverrideService)
  CRIT-007  CTR/TER accuracy at low targets (TCC floor + boost cohort)
  CRIT-008  Journey progression gating (VR-J001..J005)
  HIGH-001  Canonical schema (CanonicalSchema module)
  HIGH-002  Upload validation alignment (upload_page vs schema_validator)
  HIGH-003  User_ID type safety (dtype=str in all reads)
  HIGH-004  Journey status gate in events (BehaviorEngine)
  HIGH-005  Historical schema extension (8-column schema)

Implementation: 5 waves, est. 13-18 engineering days
Test additions: 149 unit + 57 E2E acceptance tests (currently 1,111 passing)
```

---

## SECTION 5 — RELEASE TAG

### 5.1 Tag for This Commit

After pushing this documentation commit, apply the following annotated tag:

```bash
git tag -a v2.0.0-planning -m "v2.0.0 remediation planning baseline

All 8 remediation architecture documents and binding business rules
(TDM-001) committed. Source code unchanged from v1.0.0.

Wave 1 implementation may begin after TRIGGER_AND_REENTRY_DECISION_MATRIX.md
receives product owner sign-off.

Certified state: 1,111 tests passing, APP_VERSION=1.0.0
Next milestone: v2.0.0-wave1 (CanonicalSchema + type safety)"

git push origin v2.0.0-planning
```

### 5.2 Tag History Context

| Tag | Represents | Source Code State |
|-----|-----------|-------------------|
| `v1.0.0` | Certified production release | Stage 16 certified, 1,111 tests passing |
| `v2.0.0-planning` | This commit — docs baseline | Same as v1.0.0 (no code changes) |
| `v2.0.0-wave1` | After Wave 1 complete | CanonicalSchema + type safety committed |
| `v2.0.0-wave2` | After Wave 2 complete | Trigger journeys + UserState fields |
| `v2.0.0-wave3` | After Wave 3 complete | Historical processing |
| `v2.0.0-wave4` | After Wave 4 complete | Business logic (CTR, cooling, gating) |
| `v2.0.0` | Full remediation complete | All 13 defects fixed, full regression PASS |

### 5.3 Branch Strategy

```
main              ← v1.0.0 certified release (protected)
  └── remediation/v2.0.0   ← create this branch for all Wave work
        ├── wave1/schema-type-safety   ← Wave 1 feature branch
        ├── wave2/trigger-journeys     ← Wave 2 feature branch
        └── ...
```

Create the remediation branch before any Wave work begins:

```bash
git checkout main
git pull origin main
git checkout -b remediation/v2.0.0
git push -u origin remediation/v2.0.0
```

Wave branches merge into `remediation/v2.0.0` via pull request. `remediation/v2.0.0` merges into `main` only after all 5 waves pass full regression.

---

## SECTION 6 — CLAUDE.md (COMPLETE FILE CONTENT)

The following is the complete content of `CLAUDE.md` to be placed at the repository root. This file is automatically read by Claude Code at session start and provides the minimum context needed to work on this codebase without re-reading all documentation.

---

```markdown
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

---

## CURRENT STATE

**v1.0.0 is production-certified.** Stages 12–16 certified. 1,111 tests pass.
The app runs correctly for basic use cases.

**13 production defects were identified post-deployment.** No source code has
been changed yet. All remediation is in the planning phase.

**You are likely here to implement one of the 5 remediation waves.**

---

## CRITICAL FILES — READ THESE FIRST

| File | When to Read |
|------|-------------|
| `docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md` | **ALWAYS first** — 35 binding business rule decisions. Never make an assumption without checking here. |
| `docs/remediation/ARCHITECTURE_REMEDIATION_PACKAGE.md` | Before any implementation — full defect register, pipeline changes, new components |
| `docs/remediation/IMPLEMENTATION_WAVES.md` | To understand which wave you're in and what exit criteria apply |
| `docs/governance/PROJECT_DECISIONS.md` | For any architectural decision — this is the highest-authority document |
| `docs/governance/USER_STATE_DICTIONARY.md` | Before touching any UserState field |

---

## THE 13 DEFECTS — QUICK REFERENCE

| ID | Title | Wave | Key File |
|----|-------|------|----------|
| CRIT-001 | Historical journey continuation | 3 | `docs/remediation/HISTORICAL_PROCESSING_REMEDIATION.md` |
| CRIT-002 | Trigger-specific journeys | 2 | `docs/remediation/TRIGGER_JOURNEY_REMEDIATION.md` |
| CRIT-003 | Historical audience continuity | 3 | `docs/remediation/USER_STATE_REMEDIATION.md` |
| CRIT-004 | Historical state reconstruction | 3 | `docs/remediation/HISTORICAL_PROCESSING_REMEDIATION.md` |
| CRIT-005 | Cooling period from history | 3 | `docs/remediation/USER_STATE_REMEDIATION.md` |
| CRIT-006 | Cooling period override | 4 | `docs/remediation/USER_STATE_REMEDIATION.md` |
| CRIT-007 | CTR/TER accuracy at low targets | 4 | `docs/remediation/TRIGGER_JOURNEY_REMEDIATION.md` |
| CRIT-008 | Journey progression gating | 4 | `docs/remediation/TRIGGER_JOURNEY_REMEDIATION.md` |
| HIGH-001 | Canonical schema | 1 | `docs/remediation/DATA_MODEL_REMEDIATION.md` |
| HIGH-002 | Upload validation alignment | 1 | `docs/remediation/DATA_MODEL_REMEDIATION.md` |
| HIGH-003 | User_ID type safety (dtype=str) | 1 | `docs/remediation/DATA_MODEL_REMEDIATION.md` |
| HIGH-004 | Journey status gate in events | 2 | `docs/remediation/TRIGGER_JOURNEY_REMEDIATION.md` |
| HIGH-005 | Historical schema extension | 1 | `docs/remediation/DATA_MODEL_REMEDIATION.md` |

---

## SIMULATION PIPELINE (6 STAGES)

```
Pre-Stage 1 [NEW]:  HistoricalStateReconstructor.reconstruct()   → reconstructed_state_df
Stage 1:            UserStateManager.initialize_user_states()     → state_df  (3-way merge)
  [NEW injection]:  Augment audience with historically-active users absent from trigger_df
Post-Stage 2 [NEW]: CoolingOverrideService.apply()               → audience_df
Stage 2:            AudienceManager.resolve()                     → audience_df
Stage 3:            EngagementGenerator.generate()               → (events_df, metrics_df, diag_df, df)
Stage 4:            ValidationEngine.validate()                   → validation_result
Stage 5:            ExcelExporter.export()                        [optional]
Stage 6:            UserStateManager.finalize_state()             → final_state_df
```

---

## NEW COMPONENTS TO CREATE (not yet implemented)

| File | Wave | Purpose |
|------|------|---------|
| `utils/canonical_schema.py` | 1 | Authoritative column name registry — import here, not inline |
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

- `ConfigRegistry` is a **frozen dataclass**. `ads: tuple[AdConfig, ...]` is the campaign-level ad journey (global default).
- `TriggerConfig` gets a new `ads: tuple[AdConfig, ...] | None = None` field (CRIT-002).
- `UserState` gets 3 new fields: `journey_step: int | None`, `trigger_ads_key: str | None`, `cooling_override_applied: bool`.
- `TRIGGER_HISTORY_DELIMITER = "|"` (in `utils/constants.py`).
- All `User_ID` values must be `str` throughout the pipeline (HIGH-003).
- `EligibilityStatus` values: NEW, ACTIVE, COOLING, RE_ENTRY, SKIPPED, EXCLUDED (+ deprecated ELIGIBLE, INELIGIBLE, COMPLETED).
- `JourneyStatus` values: NOT_STARTED, ACTIVE, COMPLETED, DROPPED.

---

## CRITICAL BUSINESS RULES (BINDING — do not deviate)

All 35 decisions are in `docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md`.

Top 10 most likely to cause implementation errors if not checked:

1. **Priority tie-break** → alphabetic by trigger_name (case-insensitive, ascending). Decision 1.1.
2. **Multi-trigger conflict** → one journey per user; highest priority wins; lower-priority trigger entry discarded. Decision 2.1.
3. **Active user re-triggered (same trigger)** → new entry discarded; active journey continues. Decision 4.1.
4. **Active user re-triggered (higher-priority trigger)** → current journey DROPPED; new journey starts Ad_1. Decision 4.2.
5. **DROPPED journey** → NO cooling period; eligible for immediate re-triggering; allow_reentry not applicable. Decision 5.3.
6. **Cooling boundary** → `as_of_date >= cooling_period_end` → RE_ENTRY (inclusive). Decision 7.1.
7. **allow_reentry=False evaluation order** → evaluated BEFORE cooling; EXCLUDED immediately; never COOLING. Decision 7.2.
8. **cooling_override + allow_reentry=False** → no-op; CoolingOverrideService returns unchanged state. Decision 8.1.
9. **previous_state_df priority** → absolute; historical reconstruction NEVER overrides it. Decision 14.1.
10. **trigger_ads_key drift** → ad sequence changed between runs → reset journey to Ad_1 with WARNING. Decision 14.3.

---

## TEST SUITE STRUCTURE

```
tests/
  test_core/       # unit tests for core/ modules
  test_e2e/        # E2E certification tests (BRC, HWC, MTC, MPC, SCC)
  test_models/     # unit tests for models/
  test_ui/         # Streamlit smoke tests
  test_utils/      # unit tests for utils/
  unit/            # miscellaneous unit tests
```

Run all tests: `cd engagement_data_generator && pytest tests/ -x`
Run E2E only:  `pytest tests/test_e2e/ -x`
Run fast only: `pytest tests/ -x -m "not slow"`

---

## WAVE IMPLEMENTATION ORDER

**Do NOT skip waves. Each has exit criteria that must pass before the next begins.**

| Wave | Defects | Entry Gate |
|------|---------|------------|
| Wave 1 | HIGH-001, 002, 003, 005 | Decisions 1.1, 1.2, 3.1, 3.2 confirmed |
| Wave 2 | CRIT-002, HIGH-004 | Wave 1 exit criteria met; full regression pass |
| Wave 3 | CRIT-001, 003, 004, 005 | Wave 2 exit criteria met; full regression pass |
| Wave 4 | CRIT-006, 007, 008 | Wave 3 exit criteria met; full regression pass |
| Wave 5 | All (validation + UI + tests) | Wave 4 exit criteria met; full regression pass |

Details: `docs/remediation/IMPLEMENTATION_WAVES.md`

---

## BACKWARD COMPATIBILITY CONSTRAINTS

Only one **breaking** change across all 5 waves:
- `dtype=str` coercion in `upload_page.py` (HIGH-003) — integer User_IDs become strings.
  Action: update all test fixtures using int User_IDs to use string User_IDs.

All other changes are additive (new optional fields, new modules, new parameters with defaults).

---

## PERFORMANCE BASELINE (DO NOT REGRESS)

From Stage 16 certification:
- 1,000 users × 30-day simulation: < 3.0 seconds
- 10,000 users × 30-day simulation: < 25 seconds  
- Full regression suite: 1,111 tests in < 120 seconds

Guard: `tests/test_e2e/test_scale_certification.py` — must pass after every wave.
```

---

## SECTION 7 — EXECUTION CHECKLIST

Complete all steps in order. Each step has a verification gate.

### Step 1 — Create docs/ folder structure

```bash
cd engagement_data_generator   # repo root
mkdir -p docs/remediation
mkdir -p docs/certifications
mkdir -p docs/governance
```

### Step 2 — Copy remediation documents

```bash
# From local workspace (adjust path to where your outputs folder is):
cp ARCHITECTURE_REMEDIATION_PACKAGE.md   docs/remediation/
cp DATA_MODEL_REMEDIATION.md             docs/remediation/
cp USER_STATE_REMEDIATION.md             docs/remediation/
cp HISTORICAL_PROCESSING_REMEDIATION.md  docs/remediation/
cp TRIGGER_JOURNEY_REMEDIATION.md        docs/remediation/
cp IMPLEMENTATION_WAVES.md               docs/remediation/
cp TESTING_STRATEGY.md                   docs/remediation/
cp TRIGGER_AND_REENTRY_DECISION_MATRIX.md docs/remediation/
```

### Step 3 — Copy certification reports

```bash
cp ARCH_RISK_003_REMEDIATION_REPORT.md              docs/certifications/
cp STAGE_12_END_TO_END_CERTIFICATION.md             docs/certifications/
cp STAGE_13_MULTITRIGGER_CERTIFICATION.md           docs/certifications/
cp STAGE_14_HISTORICAL_WINDOW_CERTIFICATION.md      docs/certifications/
cp STAGE_15_MULTIRUN_PERSISTENCE_CERTIFICATION.md   docs/certifications/
cp STAGE_16_PERFORMANCE_CERTIFICATION.md            docs/certifications/
```

### Step 4 — Copy governance documents

```bash
cp PROJECT_DECISIONS.md         docs/governance/
cp PROJECT_MASTER_REGISTER.md   docs/governance/
cp PROJECT_RELEASE_PACKAGE.md   docs/governance/
cp PROJECT_CHANGE_LOG.md        docs/governance/
cp PROJECT_RISK_REGISTER.md     docs/governance/
cp PROJECT_BACKLOG.md           docs/governance/
cp TRACEABILITY_MATRIX.md       docs/governance/
cp USER_STATE_DICTIONARY.md     docs/governance/
cp RELEASE_GATES.md             docs/governance/
cp REPOSITORY_CLEANUP_REPORT.md docs/governance/
```

### Step 5 — Create CLAUDE.md

Create `CLAUDE.md` at the repository root using the content in Section 6 of this document.

### Step 6 — Update README.md

Append the docs navigation block from Section 2.2 to `README.md`.

### Step 7 — Verify file count

```bash
find docs/ -name "*.md" | wc -l
# Expected: 24 (8 remediation + 6 certifications + 10 governance)

ls docs/remediation/ | wc -l   # Expected: 8
ls docs/certifications/ | wc -l # Expected: 6
ls docs/governance/ | wc -l     # Expected: 10

ls CLAUDE.md                    # Must exist at repo root
```

### Step 8 — Verify no prohibited files staged

```bash
git status | grep -E "__pycache__|\.coverage|\.pytest_cache"
# Expected: empty output (no prohibited files staged)
```

### Step 9 — Stage and commit

```bash
git add docs/ CLAUDE.md README.md
git status  # review staged files — should be 24 docs + CLAUDE.md + README.md only
git commit  # paste commit message from Section 4
```

### Step 10 — Apply release tag

```bash
git tag -a v2.0.0-planning -m "v2.0.0 remediation planning baseline..."
git push origin main
git push origin v2.0.0-planning
```

### Step 11 — Verify on GitHub

Open the GitHub repository and confirm:
- `docs/remediation/` contains 8 markdown files
- `docs/certifications/` contains 6 markdown files
- `docs/governance/` contains 10 markdown files
- `CLAUDE.md` exists at root
- Tag `v2.0.0-planning` appears in the Releases/Tags list

### Step 12 — Obtain sign-off on TRIGGER_AND_REENTRY_DECISION_MATRIX.md

Before Wave 1 begins, the Product Owner must sign the sign-off table on the last page of `docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md`. Without this sign-off, engineering must not begin Wave 1.

---

## SECTION 8 — FILES REQUIRED FOR FUTURE CLAUDE CODE WORK

When a new Claude Code session begins work on the v2.0 remediation, the following files must be in the context or explicitly read at session start. Listed in read-order priority:

### Mandatory First Reads (every session)

| File | Why |
|------|-----|
| `CLAUDE.md` | Project state, defect map, critical business rules summary |
| `docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md` | 35 binding decisions — consult before any logic change |

### Wave-Specific Reads

| Wave | Read Before Starting |
|------|---------------------|
| Wave 1 | `docs/remediation/DATA_MODEL_REMEDIATION.md` + `utils/schema_validator.py` + `ui/upload_page.py` |
| Wave 2 | `docs/remediation/TRIGGER_JOURNEY_REMEDIATION.md` + `core/journey_engine.py` + `core/engagement_generator.py` |
| Wave 3 | `docs/remediation/HISTORICAL_PROCESSING_REMEDIATION.md` + `docs/remediation/USER_STATE_REMEDIATION.md` + `core/simulation_orchestrator.py` |
| Wave 4 | `docs/remediation/TRIGGER_JOURNEY_REMEDIATION.md` (CTR sections) + `core/behavior_engine.py` + `core/audience_manager.py` |
| Wave 5 | `docs/remediation/TESTING_STRATEGY.md` + `core/validation_engine.py` + `ui/` all pages |

### Context Files to Keep in Working Memory

| File | Why Always Relevant |
|------|---------------------|
| `docs/governance/PROJECT_DECISIONS.md` | Highest-authority document — all ARCH/BIZ/SIM decisions |
| `docs/governance/USER_STATE_DICTIONARY.md` | Authoritative field definitions — consult before touching UserState |
| `docs/remediation/IMPLEMENTATION_WAVES.md` | Wave exit criteria — defines when a wave is done |
| `docs/remediation/TESTING_STRATEGY.md` | Test coverage requirements — defines what tests must exist |

### Source Files Most Likely to Be Modified

| File | Modified In Wave | Reason |
|------|-----------------|--------|
| `utils/canonical_schema.py` | Wave 1 (CREATE) | New module — column name authority |
| `utils/schema_validator.py` | Wave 1 | Import from CanonicalSchema |
| `ui/upload_page.py` | Wave 1 | dtype=str + validation alignment |
| `models/trigger_config.py` | Wave 2 | Add `ads` field |
| `models/user_state.py` | Wave 2 | Add 3 new fields |
| `core/journey_engine.py` | Wave 2 | Add `ads_override` parameter |
| `core/trigger_journey_resolver.py` | Wave 2 (CREATE) | New service |
| `core/engagement_generator.py` | Wave 2 + Wave 4 | Per-trigger cohort loop, TCC floor, boost cohort |
| `core/behavior_engine.py` | Wave 2 + Wave 4 | Journey_status gate, boost_multiplier |
| `core/simulation_orchestrator.py` | Wave 3 | Pre-Stage 1 injection, audience augmentation |
| `core/user_state_manager.py` | Wave 3 | Three-way merge |
| `core/historical_state_reconstructor.py` | Wave 3 (CREATE) | New service |
| `core/cooling_override_service.py` | Wave 4 (CREATE) | New service |
| `core/audience_manager.py` | Wave 4 | Eligibility resolution order |
| `core/validation_engine.py` | Wave 5 | VR-J001 through VR-J005 |
| `ui/business_rules_page.py` | Wave 5 | Cooling override toggle |
| `ui/campaign_page.py` | Wave 5 | Per-trigger ad sequence UI |

---

## APPENDIX A — DOCUMENT AUTHORITY HIERARCHY

For any conflict between documents, this hierarchy governs:

```
docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md  ← HIGHEST (35 binding decisions)
docs/governance/PROJECT_DECISIONS.md                     ← High (all arch/biz decisions)
docs/remediation/ARCHITECTURE_REMEDIATION_PACKAGE.md     ← High (defect register + contracts)
docs/remediation/[specific remediation doc]              ← Medium (per-area spec)
docs/certifications/[stage reports]                      ← Reference (v1.0 baseline)
docs/governance/[governance docs]                        ← Reference (project tracking)
```

---

## APPENDIX B — COMPLETE FILE COUNT SUMMARY

| Category | Count | Destination |
|----------|-------|-------------|
| Remediation architecture docs | 8 | `docs/remediation/` |
| Stage certification reports | 6 | `docs/certifications/` |
| Governance documents | 10 | `docs/governance/` |
| CLAUDE.md | 1 | repo root |
| README.md update | 1 | repo root (existing file modified) |
| **Total new/modified** | **26** | |
| Source code files changed | **0** | |
| Test files changed | **0** | |

---

*Document: GSP-001 | GITHUB_SYNC_PACKAGE.md | v1.0 | 2026-06-24*
