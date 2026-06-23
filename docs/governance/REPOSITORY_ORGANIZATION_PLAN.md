# REPOSITORY ORGANIZATION PLAN
## Engagement Data Generator — Complete Markdown File Registry

**Document ID:** ROP-001  
**Version:** 1.0  
**Date:** 2026-06-24  
**Role:** Release Manager / Repository Architect  
**Authority:** This document supersedes GITHUB_SYNC_PACKAGE.md (GSP-001) for file classification decisions. GSP-001 remains valid for the commit message, tag name, and execution checklist.  
**Scope:** Every `.md` file in the local workspace — 62 total.

---

## SECTION 1 — COMPLETE FILE INVENTORY WITH CLASSIFICATION

Total files catalogued: **62**  
Files to commit: **31** (8 remediation + 8 certifications + 12 governance + 2 root + 1 app-root)  
Files excluded from commit: **31** (29 do_not_commit + 2 auto-generated)

Classification key:
- **remediation** — v2.0 remediation architecture; commit to `docs/remediation/`
- **certifications** — stage build and certification reports; commit to `docs/certifications/`
- **governance** — project decisions, tracking, and release records; commit to `docs/governance/`
- **root** — repo root level; commit to `/`
- **obsolete** — superseded by a current document; do not commit
- **do_not_commit** — session execution logs, scratch artifacts, or auto-generated files

---

### 1.1 File-by-File Classification Table

| # | Current Filename | Current Location | Classification | GitHub Destination Path |
|---|-----------------|-----------------|----------------|------------------------|
| 1 | `ARCHITECTURE_REMEDIATION_PACKAGE.md` | outputs/ | **remediation** | `docs/remediation/ARCHITECTURE_REMEDIATION_PACKAGE.md` |
| 2 | `ARCH_RISK_003_REMEDIATION_REPORT.md` | outputs/ | **certifications** | `docs/certifications/ARCH_RISK_003_REMEDIATION_REPORT.md` |
| 3 | `AUDIENCE_MANAGER_IMPLEMENTATION_REPORT.md` | outputs/ | **do_not_commit** | — superseded by STAGE_12 certification |
| 4 | `BEHAVIOR_ENGINE_IMPLEMENTATION_REPORT.md` | outputs/ | **do_not_commit** | — superseded by STAGE_12 certification |
| 5 | `CLAUDE.md` | outputs/ | **root** | `CLAUDE.md` |
| 6 | `DATA_MODEL_REMEDIATION.md` | outputs/ | **remediation** | `docs/remediation/DATA_MODEL_REMEDIATION.md` |
| 7 | `ENGAGEMENT_GENERATOR_IMPLEMENTATION_REPORT.md` | outputs/ | **do_not_commit** | — superseded by STAGE_12 certification |
| 8 | `EXCEL_EXPORTER_IMPLEMENTATION_REPORT.md` | outputs/ | **do_not_commit** | — superseded by STAGE_12 certification |
| 9 | `GITHUB_SYNC_PACKAGE.md` | outputs/ | **governance** | `docs/governance/GITHUB_SYNC_PACKAGE.md` |
| 10 | `GOVERNANCE_SYNC_REPORT.md` | outputs/ | **obsolete** | — superseded by GITHUB_SYNC_PACKAGE.md |
| 11 | `HISTORICAL_PROCESSING_REMEDIATION.md` | outputs/ | **remediation** | `docs/remediation/HISTORICAL_PROCESSING_REMEDIATION.md` |
| 12 | `IMPLEMENTATION_WAVES.md` | outputs/ | **remediation** | `docs/remediation/IMPLEMENTATION_WAVES.md` |
| 13 | `JOURNEY_ENGINE_IMPLEMENTATION_REPORT.md` | outputs/ | **do_not_commit** | — superseded by STAGE_12 certification |
| 14 | `PHASE_2_EXECUTION_PLAN.md` | outputs/ | **do_not_commit** | — session execution log; no living reference value |
| 15 | `PHASE_2_FINAL_CLOSEOUT.md` | outputs/ | **do_not_commit** | — session execution log |
| 16 | `PHASE_2_GATE_REVIEW.md` | outputs/ | **do_not_commit** | — session execution log |
| 17 | `PHASE_2_PROGRESS_REPORT.md` | outputs/ | **do_not_commit** | — session execution log |
| 18 | `PHASE_2_REMEDIATION_PLAN.md` | outputs/ | **do_not_commit** | — superseded by ARCHITECTURE_REMEDIATION_PACKAGE.md |
| 19 | `PHASE_3_ARCHITECTURE_DECISIONS.md` | outputs/ | **do_not_commit** | — decisions ratified into PROJECT_DECISIONS.md; this is the pre-ratification analysis |
| 20 | `PHASE_3_BLOCKER_RESOLUTION.md` | outputs/ | **do_not_commit** | — session execution log |
| 21 | `PHASE_3_EXECUTION_PLAN.md` | outputs/ | **do_not_commit** | — session execution log |
| 22 | `PHASE_3_FOUNDATION_SPRINT_REPORT.md` | outputs/ | **do_not_commit** | — superseded by STAGE_12 certification |
| 23 | `PHASE_3_IMPLEMENTATION_PLAN.md` | outputs/ | **do_not_commit** | — superseded by IMPLEMENTATION_WAVES.md |
| 24 | `PHASE_3_PREP_IMPLEMENTATION.md` | outputs/ | **do_not_commit** | — session preparation notes |
| 25 | `PHASE_3_PRE_IMPLEMENTATION_AUDIT.md` | outputs/ | **do_not_commit** | — session audit snapshot; no living value |
| 26 | `PHASE_3_PRODUCT_RULES_CHECKLIST.md` | outputs/ | **do_not_commit** | — superseded by TRIGGER_AND_REENTRY_DECISION_MATRIX.md |
| 27 | `PHASE_3_WAVE_1_BUILD_CONTRACT.md` | outputs/ | **do_not_commit** | — Phase 3 Wave 1 (v1.0 build); superseded by IMPLEMENTATION_WAVES.md (v2.0 waves) |
| 28 | `PHASE_3_WAVE_1_EXECUTION_PACKAGE.md` | outputs/ | **do_not_commit** | — Phase 3 Wave 1 execution log; superseded |
| 29 | `PROJECT_BACKLOG.md` | outputs/ | **governance** | `docs/governance/PROJECT_BACKLOG.md` |
| 30 | `PROJECT_CHANGE_LOG.md` | outputs/ | **governance** | `docs/governance/PROJECT_CHANGE_LOG.md` |
| 31 | `PROJECT_DECISIONS.md` | outputs/ | **governance** | `docs/governance/PROJECT_DECISIONS.md` |
| 32 | `PROJECT_MASTER_REGISTER.md` | outputs/ | **governance** | `docs/governance/PROJECT_MASTER_REGISTER.md` |
| 33 | `PROJECT_MEMORY.md` | outputs/ | **do_not_commit** | — internal session memory notes; not a formal document |
| 34 | `PROJECT_RELEASE_PACKAGE.md` | outputs/ | **governance** | `docs/governance/PROJECT_RELEASE_PACKAGE.md` |
| 35 | `PROJECT_RISK_REGISTER.md` | outputs/ | **governance** | `docs/governance/PROJECT_RISK_REGISTER.md` |
| 36 | `RELEASE_GATES.md` | outputs/ | **governance** | `docs/governance/RELEASE_GATES.md` |
| 37 | `REPOSITORY_CLEANUP_REPORT.md` | outputs/ | **governance** | `docs/governance/REPOSITORY_CLEANUP_REPORT.md` |
| 38 | `REPOSITORY_ORGANIZATION_PLAN.md` | outputs/ | **governance** | `docs/governance/REPOSITORY_ORGANIZATION_PLAN.md` |
| 39 | `REPOSITORY_VERIFICATION_REPORT.md` | outputs/ | **obsolete** | — point-in-time v1.0 upload check; superseded by REPOSITORY_ORGANIZATION_PLAN.md |
| 40 | `STAGE_10_ORCHESTRATOR_IMPLEMENTATION.md` | outputs/ | **certifications** | `docs/certifications/STAGE_10_ORCHESTRATOR_IMPLEMENTATION.md` |
| 41 | `STAGE_12_END_TO_END_CERTIFICATION.md` | outputs/ | **certifications** | `docs/certifications/STAGE_12_END_TO_END_CERTIFICATION.md` |
| 42 | `STAGE_13_MULTITRIGGER_CERTIFICATION.md` | outputs/ | **certifications** | `docs/certifications/STAGE_13_MULTITRIGGER_CERTIFICATION.md` |
| 43 | `STAGE_14_HISTORICAL_WINDOW_CERTIFICATION.md` | outputs/ | **certifications** | `docs/certifications/STAGE_14_HISTORICAL_WINDOW_CERTIFICATION.md` |
| 44 | `STAGE_15_MULTIRUN_PERSISTENCE_CERTIFICATION.md` | outputs/ | **certifications** | `docs/certifications/STAGE_15_MULTIRUN_PERSISTENCE_CERTIFICATION.md` |
| 45 | `STAGE_16_PERFORMANCE_CERTIFICATION.md` | outputs/ | **certifications** | `docs/certifications/STAGE_16_PERFORMANCE_CERTIFICATION.md` |
| 46 | `TESTING_STRATEGY.md` | outputs/ | **remediation** | `docs/remediation/TESTING_STRATEGY.md` |
| 47 | `TRACEABILITY_MATRIX.md` | outputs/ | **governance** | `docs/governance/TRACEABILITY_MATRIX.md` |
| 48 | `TRIGGER_AND_REENTRY_DECISION_MATRIX.md` | outputs/ | **remediation** | `docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md` |
| 49 | `TRIGGER_JOURNEY_REMEDIATION.md` | outputs/ | **remediation** | `docs/remediation/TRIGGER_JOURNEY_REMEDIATION.md` |
| 50 | `USER_STATE_DICTIONARY.md` | outputs/ | **governance** | `docs/governance/USER_STATE_DICTIONARY.md` |
| 51 | `USER_STATE_REMEDIATION.md` | outputs/ | **remediation** | `docs/remediation/USER_STATE_REMEDIATION.md` |
| 52 | `VALIDATION_ENGINE_IMPLEMENTATION_REPORT.md` | outputs/ | **do_not_commit** | — superseded by STAGE_12 certification |
| 53 | `WAVE_1_EXECUTION_REPORT.md` | outputs/ | **do_not_commit** | — session execution log |
| 54 | `WAVE_1_GOVERNANCE_AUTOMATION.md` | outputs/ | **do_not_commit** | — session execution log |
| 55 | `WAVE_1_PRE_IMPLEMENTATION_BACKLOG_UPDATE.md` | outputs/ | **do_not_commit** | — session execution log |
| 56 | `WAVE_2_EXECUTION_REPORT.md` | outputs/ | **do_not_commit** | — session execution log |
| 57 | `WAVE_3_EXECUTION_REPORT.md` | outputs/ | **do_not_commit** | — session execution log |
| 58 | `WAVE_4_5_EXECUTION_REPORT.md` | outputs/ | **do_not_commit** | — session execution log |
| 59 | `WAVE_6_EXECUTION_REPORT.md` | outputs/ | **do_not_commit** | — session execution log |
| 60 | `engagement_data_generator/README.md` | app root | **root** | `README.md` (update — add docs/ navigation block) |
| 61 | `engagement_data_generator/STAGE_11_STREAMLIT_MVP_IMPLEMENTATION.md` | app root | **certifications** | `docs/certifications/STAGE_11_STREAMLIT_MVP_IMPLEMENTATION.md` ⚠ MOVE from app root |
| 62 | `engagement_data_generator/.pytest_cache/README.md` | auto-generated | **do_not_commit** | — auto-generated by pytest; already excluded by .gitignore |
| 63 | `engagement_data_generator/tests/.pytest_cache/README.md` | auto-generated | **do_not_commit** | — auto-generated by pytest; already excluded by .gitignore |

---

## SECTION 2 — CLASSIFICATION SUMMARY

### 2.1 Files to Commit (31 files)

#### remediation — 8 files → `docs/remediation/`

| File | Doc ID | Authority Level |
|------|--------|----------------|
| `ARCHITECTURE_REMEDIATION_PACKAGE.md` | ARP-001 | Master document — read first |
| `DATA_MODEL_REMEDIATION.md` | DMR-001 | CanonicalSchema, TriggerConfig.ads, UserState fields |
| `USER_STATE_REMEDIATION.md` | USR-001 | HistoricalStateReconstructor, three-way merge, CoolingOverrideService |
| `HISTORICAL_PROCESSING_REMEDIATION.md` | HPR-001 | 8-column historical schema, audience augmentation |
| `TRIGGER_JOURNEY_REMEDIATION.md` | TJR-001 | TriggerJourneyResolver, TCC floor, boost cohort, VR-J rules |
| `IMPLEMENTATION_WAVES.md` | IWP-001 | 5-wave plan, exit criteria per wave |
| `TESTING_STRATEGY.md` | TST-001 | 149 unit + 57 E2E test design |
| `TRIGGER_AND_REENTRY_DECISION_MATRIX.md` | TDM-001 | **35 binding decisions — sign-off required before Wave 1** |

#### certifications — 8 files → `docs/certifications/`

| File | Stage | Content |
|------|-------|---------|
| `STAGE_10_ORCHESTRATOR_IMPLEMENTATION.md` | 10 | SimulationOrchestrator 6-stage pipeline build record |
| `STAGE_11_STREAMLIT_MVP_IMPLEMENTATION.md` | 11 | Streamlit UI MVP build record ⚠ **MOVE from app root** |
| `STAGE_12_END_TO_END_CERTIFICATION.md` | 12 | Full E2E pipeline certification baseline |
| `STAGE_13_MULTITRIGGER_CERTIFICATION.md` | 13 | Multi-trigger campaign certification |
| `STAGE_14_HISTORICAL_WINDOW_CERTIFICATION.md` | 14 | Historical window modes certification |
| `STAGE_15_MULTIRUN_PERSISTENCE_CERTIFICATION.md` | 15 | Multi-run state persistence certification |
| `STAGE_16_PERFORMANCE_CERTIFICATION.md` | 16 | Scale and performance SLA certification (1,111 tests) |
| `ARCH_RISK_003_REMEDIATION_REPORT.md` | — | Root-cause analysis: historical_engaged stamping bug |

#### governance — 12 files → `docs/governance/`

| File | Authority | Content |
|------|-----------|---------|
| `PROJECT_DECISIONS.md` | **HIGHEST** | All ARCH/CFG/SIM/BIZ decisions — supersedes all other documents |
| `PROJECT_MASTER_REGISTER.md` | HIGH | Open items, defect register, risk register |
| `PROJECT_RELEASE_PACKAGE.md` | HIGH | v1.0 release certification and deployment instructions |
| `TRACEABILITY_MATRIX.md` | HIGH | Requirement-to-implementation cross-reference |
| `USER_STATE_DICTIONARY.md` | HIGH | Authoritative definition of all 35+ UserState fields |
| `GITHUB_SYNC_PACKAGE.md` | MEDIUM | Repository synchronization plan (commit message, tags, checklist) |
| `REPOSITORY_ORGANIZATION_PLAN.md` | MEDIUM | **This document** — file classification registry |
| `PROJECT_CHANGE_LOG.md` | MEDIUM | Chronological change history |
| `PROJECT_RISK_REGISTER.md` | MEDIUM | Active risks and mitigations |
| `PROJECT_BACKLOG.md` | MEDIUM | Prioritized backlog and deferred items |
| `RELEASE_GATES.md` | MEDIUM | Quality gates and release criteria |
| `REPOSITORY_CLEANUP_REPORT.md` | LOW | v1.0 cleanup audit record |

#### root — 2 files

| File | Action | Destination |
|------|--------|-------------|
| `CLAUDE.md` | NEW | `/CLAUDE.md` (repo root) |
| `README.md` | UPDATE — add docs/ nav block | `/README.md` (already exists) |

---

### 2.2 Files NOT to Commit (31 files)

#### obsolete — 2 files (superseded by current documents)

| File | Superseded By | Reason |
|------|--------------|--------|
| `GOVERNANCE_SYNC_REPORT.md` | `GITHUB_SYNC_PACKAGE.md` | GOV-SYNC-001 was a point-in-time sync for ARCH-013/014 ratification. GITHUB_SYNC_PACKAGE.md covers the current full sync comprehensively. |
| `REPOSITORY_VERIFICATION_REPORT.md` | `REPOSITORY_ORGANIZATION_PLAN.md` | Was a 26-check verification for the v1.0 upload. Current plan supersedes it with complete classification. |

#### do_not_commit — 29 files (execution logs and scratch artifacts)

**Phase 2 session logs (5 files) — no living reference value:**

| File | Reason |
|------|--------|
| `PHASE_2_EXECUTION_PLAN.md` | Session execution roadmap; outcome captured in STAGE_12 certification |
| `PHASE_2_FINAL_CLOSEOUT.md` | Session closeout report; outcome captured in PROJECT_CHANGE_LOG.md |
| `PHASE_2_GATE_REVIEW.md` | Session gate review notes; decisions ratified into PROJECT_DECISIONS.md |
| `PHASE_2_PROGRESS_REPORT.md` | Session status log; no permanent reference value |
| `PHASE_2_REMEDIATION_PLAN.md` | Early defect plan; fully superseded by ARCHITECTURE_REMEDIATION_PACKAGE.md |

**Phase 3 session logs (10 files) — decisions ratified elsewhere:**

| File | Reason |
|------|--------|
| `PHASE_3_ARCHITECTURE_DECISIONS.md` | Pre-ratification analysis for DD-013 and DD-014; decisions moved into PROJECT_DECISIONS.md (ARCH-013, ARCH-014); this document's own header says "becomes read-only historical record" once ratified |
| `PHASE_3_BLOCKER_RESOLUTION.md` | Session blocker log; resolved items in PROJECT_MASTER_REGISTER.md |
| `PHASE_3_EXECUTION_PLAN.md` | Session execution plan; superseded by IMPLEMENTATION_WAVES.md |
| `PHASE_3_FOUNDATION_SPRINT_REPORT.md` | Foundation sprint status report; baseline captured in STAGE_12 certification |
| `PHASE_3_IMPLEMENTATION_PLAN.md` | Session implementation plan; superseded by IMPLEMENTATION_WAVES.md |
| `PHASE_3_PREP_IMPLEMENTATION.md` | Session preparation notes; transient |
| `PHASE_3_PRE_IMPLEMENTATION_AUDIT.md` | Point-in-time audit before Phase 3; no longer current |
| `PHASE_3_PRODUCT_RULES_CHECKLIST.md` | v1.0 build-phase rules checklist; fully superseded by TRIGGER_AND_REENTRY_DECISION_MATRIX.md which covers all 35 decisions |
| `PHASE_3_WAVE_1_BUILD_CONTRACT.md` | Phase 3 Wave 1 (v1.0 core build) contract; not to be confused with IMPLEMENTATION_WAVES.md (v2.0 remediation waves); commits this would create naming confusion |
| `PHASE_3_WAVE_1_EXECUTION_PACKAGE.md` | Phase 3 Wave 1 execution instructions; superseded |

**Wave execution reports (7 files) — build-time logs:**

| File | Reason |
|------|--------|
| `WAVE_1_EXECUTION_REPORT.md` | v1.0 Wave 1 build log (user_state_manager + audience_manager); outcome in STAGE_12 |
| `WAVE_1_GOVERNANCE_AUTOMATION.md` | Governance process notes for v1.0 Wave 1; no reference value post-build |
| `WAVE_1_PRE_IMPLEMENTATION_BACKLOG_UPDATE.md` | Pre-wave backlog snapshot; backlog current state in PROJECT_BACKLOG.md |
| `WAVE_2_EXECUTION_REPORT.md` | v1.0 Wave 2 build log (behavior_engine + engagement_generator); outcome in STAGE_12 |
| `WAVE_3_EXECUTION_REPORT.md` | v1.0 Wave 3 build log (journey_engine + validation_engine); outcome in STAGE_12 |
| `WAVE_4_5_EXECUTION_REPORT.md` | v1.0 Waves 4+5 build log (excel_exporter + UI + orchestrator); outcome in STAGE_10/12 |
| `WAVE_6_EXECUTION_REPORT.md` | v1.0 Wave 6 build log (additional features); outcome in STAGE_12 |

**Per-component implementation reports (6 files) — build-time component logs:**

| File | Reason |
|------|--------|
| `AUDIENCE_MANAGER_IMPLEMENTATION_REPORT.md` | Component build log; certified baseline in STAGE_12 |
| `BEHAVIOR_ENGINE_IMPLEMENTATION_REPORT.md` | Component build log; certified baseline in STAGE_12 |
| `ENGAGEMENT_GENERATOR_IMPLEMENTATION_REPORT.md` | Component build log; certified baseline in STAGE_12 |
| `EXCEL_EXPORTER_IMPLEMENTATION_REPORT.md` | Component build log; certified baseline in STAGE_12 |
| `JOURNEY_ENGINE_IMPLEMENTATION_REPORT.md` | Component build log; certified baseline in STAGE_12 |
| `VALIDATION_ENGINE_IMPLEMENTATION_REPORT.md` | Component build log; certified baseline in STAGE_12 |

**Internal session artifacts (1 file):**

| File | Reason |
|------|--------|
| `PROJECT_MEMORY.md` | Internal session "remember this" notes used between AI sessions; not a formal document; content that survives should be merged into PROJECT_DECISIONS.md or CLAUDE.md |

**Auto-generated (2 files — already in .gitignore):**

| File | Reason |
|------|--------|
| `engagement_data_generator/.pytest_cache/README.md` | Auto-generated by pytest; excluded by .gitignore |
| `engagement_data_generator/tests/.pytest_cache/README.md` | Auto-generated by pytest; excluded by .gitignore |

---

## SECTION 3 — ANOMALIES: MISSING, DUPLICATE, MISPLACED FILES

### 3.1 Misplaced Files (require action before commit)

| File | Current Location | Problem | Correct Action |
|------|-----------------|---------|----------------|
| `STAGE_11_STREAMLIT_MVP_IMPLEMENTATION.md` | `engagement_data_generator/` (app root) | Stage certification documents belong in `docs/certifications/`, not in the application root. Presence in the app root clutters the project's entry-level directory and breaks the doc taxonomy. | **MOVE** to `docs/certifications/STAGE_11_STREAMLIT_MVP_IMPLEMENTATION.md`. Remove from app root. |

**Note on STAGE_10:** `STAGE_10_ORCHESTRATOR_IMPLEMENTATION.md` is currently at the workspace top-level outputs/ folder rather than inside `engagement_data_generator/`. It was never in the app folder. No action needed — simply copy to `docs/certifications/` like the other stage docs.

### 3.2 Missing Files (should exist, do not)

| Missing File | Where It Should Be | Reason It Is Needed |
|-------------|-------------------|---------------------|
| `docs/remediation/README.md` | `docs/remediation/README.md` | Navigation index for the remediation folder. Engineers opening docs/remediation/ on GitHub see a raw file list with no guidance on read order. A one-page README with document-ID→file mapping and recommended read sequence would prevent confusion. |
| `docs/certifications/README.md` | `docs/certifications/README.md` | Navigation index for the certifications folder. Engineers need to know which stage reports constitute the regression baseline and which are merely historical records. |
| `docs/governance/README.md` | `docs/governance/README.md` | Navigation index for the governance folder. The authority hierarchy (PROJECT_DECISIONS.md at top, then PROJECT_MASTER_REGISTER.md, etc.) is not self-evident from filenames alone. |
| `CHANGELOG.md` | `/CHANGELOG.md` (repo root) | A machine-readable changelog at the repo root following Keep a Changelog format (https://keepachangelog.com). PROJECT_CHANGE_LOG.md serves a similar purpose but is a prose governance document. A root CHANGELOG.md in conventional format is expected by GitHub and tooling. |

**Priority of missing files:** CHANGELOG.md and the three README.md navigation indexes are low-urgency. The repo is fully functional without them. They are recommended for Wave 5 (documentation polish). They are not blockers for Wave 1.

### 3.3 Duplicate Content (same information in multiple documents)

| Content Area | Primary Authority | Superseded Duplicate | Action |
|-------------|------------------|---------------------|--------|
| Architecture decisions (ARCH-*, CFG-*, SIM-*, BIZ-*) | `PROJECT_DECISIONS.md` | `PHASE_3_ARCHITECTURE_DECISIONS.md` | Do not commit the duplicate. PROJECT_DECISIONS.md is the sole authority. |
| Business rules for triggers and re-entry | `TRIGGER_AND_REENTRY_DECISION_MATRIX.md` (TDM-001) | `PHASE_3_PRODUCT_RULES_CHECKLIST.md` | Do not commit the checklist. TDM-001 covers all 35 decisions in binding form. |
| Wave implementation plan | `IMPLEMENTATION_WAVES.md` (IWP-001) | `PHASE_3_IMPLEMENTATION_PLAN.md`, `PHASE_3_WAVE_1_BUILD_CONTRACT.md`, `PHASE_3_WAVE_1_EXECUTION_PACKAGE.md` | Do not commit the three phase-3 docs. IWP-001 is the current plan. |
| Repository sync instructions | `GITHUB_SYNC_PACKAGE.md` (GSP-001) | `GOVERNANCE_SYNC_REPORT.md` | Do not commit GOVERNANCE_SYNC_REPORT.md. GSP-001 is the current sync reference. |
| Repository file inventory | `REPOSITORY_ORGANIZATION_PLAN.md` (ROP-001, this document) | `REPOSITORY_VERIFICATION_REPORT.md` | Do not commit REPOSITORY_VERIFICATION_REPORT.md. ROP-001 is the current complete inventory. |

### 3.4 Naming Convention Inconsistency

| File | Issue | Recommendation |
|------|-------|----------------|
| `ARCH_RISK_003_REMEDIATION_REPORT.md` | Uses underscores; all other docs use hyphens between words or none. Not a blocker. | Accept as-is. Renaming risks breaking references in PROJECT_DECISIONS.md and TRACEABILITY_MATRIX.md. |
| `WAVE_4_5_EXECUTION_REPORT.md` | Covers two waves in one file (unusual). | Accept as-is. This is a do_not_commit file; no action needed. |

---

## SECTION 4 — FINAL REPOSITORY TREE

This is the exact tree GitHub must contain after the sync commit. Every file listed below must be present. Files from the current repo not listed here (source code, test files) are unchanged and retained.

```
engagement_data_generator/               ← repository root
│
│  ── ROOT LEVEL ──────────────────────────────────────────────────
│
├── CLAUDE.md                            ← NEW (AI session context)
├── README.md                            ← UPDATE (add docs/ nav block)
├── app.py
├── requirements.txt
├── .gitignore
│
│  ── APPLICATION SOURCE (unchanged from v1.0.0) ────────────────
│
├── core/
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
├── models/
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
├── utils/
│   ├── __init__.py
│   ├── constants.py
│   ├── date_utils.py
│   ├── excel_utils.py
│   ├── exceptions.py
│   ├── logger.py
│   ├── schema_validator.py
│   └── version.py
│
├── ui/
│   ├── __init__.py
│   ├── business_rules_page.py
│   ├── campaign_page.py
│   ├── results_page.py
│   ├── run_page.py
│   ├── state.py
│   └── upload_page.py
│
│  ── TEST SUITE (unchanged from v1.0.0, 1,111 tests) ────────────
│
├── tests/
│   ├── __init__.py
│   ├── test_core/
│   │   ├── __init__.py
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
│   │   ├── __init__.py
│   │   ├── test_business_rule_certification.py
│   │   ├── test_historical_window_certification.py
│   │   ├── test_multirun_persistence_certification.py
│   │   ├── test_multitrigger_certification.py
│   │   └── test_scale_certification.py
│   ├── test_models/
│   │   ├── __init__.py
│   │   ├── test_ad_config.py
│   │   ├── test_capacity_row.py
│   │   ├── test_config_registry.py
│   │   ├── test_config_registry_weights.py
│   │   ├── test_enums.py
│   │   ├── test_segment_config.py
│   │   ├── test_trigger_config.py
│   │   └── test_user_state.py
│   ├── test_ui/
│   │   ├── __init__.py
│   │   └── test_smoke.py
│   ├── test_utils/
│   │   ├── __init__.py
│   │   └── test_schema_validator.py
│   └── unit/
│       ├── __init__.py
│       └── test_date_utils.py
│
│  ── DOCUMENTATION (all new — this commit) ─────────────────────
│
└── docs/
    │
    │  ── REMEDIATION (v2.0 architecture) ───────────────────────
    │
    ├── remediation/
    │   ├── ARCHITECTURE_REMEDIATION_PACKAGE.md    ← ARP-001 — read first
    │   ├── DATA_MODEL_REMEDIATION.md              ← DMR-001
    │   ├── USER_STATE_REMEDIATION.md              ← USR-001
    │   ├── HISTORICAL_PROCESSING_REMEDIATION.md   ← HPR-001
    │   ├── TRIGGER_JOURNEY_REMEDIATION.md         ← TJR-001
    │   ├── IMPLEMENTATION_WAVES.md                ← IWP-001
    │   ├── TESTING_STRATEGY.md                    ← TST-001
    │   └── TRIGGER_AND_REENTRY_DECISION_MATRIX.md ← TDM-001 ⚠ SIGN-OFF REQUIRED
    │
    │  ── CERTIFICATIONS (v1.0 build and QA records) ────────────
    │
    ├── certifications/
    │   ├── STAGE_10_ORCHESTRATOR_IMPLEMENTATION.md
    │   ├── STAGE_11_STREAMLIT_MVP_IMPLEMENTATION.md  ← MOVED from app root
    │   ├── STAGE_12_END_TO_END_CERTIFICATION.md
    │   ├── STAGE_13_MULTITRIGGER_CERTIFICATION.md
    │   ├── STAGE_14_HISTORICAL_WINDOW_CERTIFICATION.md
    │   ├── STAGE_15_MULTIRUN_PERSISTENCE_CERTIFICATION.md
    │   ├── STAGE_16_PERFORMANCE_CERTIFICATION.md
    │   └── ARCH_RISK_003_REMEDIATION_REPORT.md
    │
    │  ── GOVERNANCE (decisions, tracking, release records) ──────
    │
    └── governance/
        ├── PROJECT_DECISIONS.md            ← HIGHEST authority
        ├── PROJECT_MASTER_REGISTER.md
        ├── PROJECT_RELEASE_PACKAGE.md
        ├── TRACEABILITY_MATRIX.md
        ├── USER_STATE_DICTIONARY.md
        ├── GITHUB_SYNC_PACKAGE.md
        ├── REPOSITORY_ORGANIZATION_PLAN.md ← this document
        ├── PROJECT_CHANGE_LOG.md
        ├── PROJECT_RISK_REGISTER.md
        ├── PROJECT_BACKLOG.md
        ├── RELEASE_GATES.md
        └── REPOSITORY_CLEANUP_REPORT.md
```

---

## SECTION 5 — FILES EXCLUDED FROM COMMIT: COMPLETE LIST

The following 31 files must NOT be committed. They exist in the local workspace and must be either deleted locally or moved to an off-repo archive if historical record is desired.

```
do_not_commit/
│
├── PHASE_2_EXECUTION_PLAN.md
├── PHASE_2_FINAL_CLOSEOUT.md
├── PHASE_2_GATE_REVIEW.md
├── PHASE_2_PROGRESS_REPORT.md
├── PHASE_2_REMEDIATION_PLAN.md
│
├── PHASE_3_ARCHITECTURE_DECISIONS.md         ← decisions already in PROJECT_DECISIONS.md
├── PHASE_3_BLOCKER_RESOLUTION.md
├── PHASE_3_EXECUTION_PLAN.md
├── PHASE_3_FOUNDATION_SPRINT_REPORT.md
├── PHASE_3_IMPLEMENTATION_PLAN.md
├── PHASE_3_PREP_IMPLEMENTATION.md
├── PHASE_3_PRE_IMPLEMENTATION_AUDIT.md
├── PHASE_3_PRODUCT_RULES_CHECKLIST.md        ← superseded by TDM-001
├── PHASE_3_WAVE_1_BUILD_CONTRACT.md          ← v1.0 Wave 1; do not confuse with IWP-001
├── PHASE_3_WAVE_1_EXECUTION_PACKAGE.md
│
├── WAVE_1_EXECUTION_REPORT.md
├── WAVE_1_GOVERNANCE_AUTOMATION.md
├── WAVE_1_PRE_IMPLEMENTATION_BACKLOG_UPDATE.md
├── WAVE_2_EXECUTION_REPORT.md
├── WAVE_3_EXECUTION_REPORT.md
├── WAVE_4_5_EXECUTION_REPORT.md
├── WAVE_6_EXECUTION_REPORT.md
│
├── AUDIENCE_MANAGER_IMPLEMENTATION_REPORT.md
├── BEHAVIOR_ENGINE_IMPLEMENTATION_REPORT.md
├── ENGAGEMENT_GENERATOR_IMPLEMENTATION_REPORT.md
├── EXCEL_EXPORTER_IMPLEMENTATION_REPORT.md
├── JOURNEY_ENGINE_IMPLEMENTATION_REPORT.md
├── VALIDATION_ENGINE_IMPLEMENTATION_REPORT.md
│
├── GOVERNANCE_SYNC_REPORT.md                 ← obsolete; superseded by GSP-001
├── REPOSITORY_VERIFICATION_REPORT.md         ← obsolete; superseded by ROP-001
├── PROJECT_MEMORY.md                         ← internal session notes; not a formal doc
│
├── .pytest_cache/README.md                   ← auto-generated; already in .gitignore
└── tests/.pytest_cache/README.md             ← auto-generated; already in .gitignore
```

---

## SECTION 6 — GIT COMMANDS: EXACT FILE OPERATIONS

The following commands execute the organization plan precisely. Run in order from the `engagement_data_generator/` repo root.

### Step 1 — Create directory structure

```bash
mkdir -p docs/remediation
mkdir -p docs/certifications
mkdir -p docs/governance
```

### Step 2 — Copy remediation documents (from local outputs/)

```bash
# Adjust SOURCE_DIR to your local outputs folder path
SOURCE_DIR="/path/to/your/outputs"

cp "$SOURCE_DIR/ARCHITECTURE_REMEDIATION_PACKAGE.md"   docs/remediation/
cp "$SOURCE_DIR/DATA_MODEL_REMEDIATION.md"             docs/remediation/
cp "$SOURCE_DIR/USER_STATE_REMEDIATION.md"             docs/remediation/
cp "$SOURCE_DIR/HISTORICAL_PROCESSING_REMEDIATION.md"  docs/remediation/
cp "$SOURCE_DIR/TRIGGER_JOURNEY_REMEDIATION.md"        docs/remediation/
cp "$SOURCE_DIR/IMPLEMENTATION_WAVES.md"               docs/remediation/
cp "$SOURCE_DIR/TESTING_STRATEGY.md"                   docs/remediation/
cp "$SOURCE_DIR/TRIGGER_AND_REENTRY_DECISION_MATRIX.md" docs/remediation/
```

### Step 3 — Copy and MOVE certification documents

```bash
# Copy from outputs/
cp "$SOURCE_DIR/ARCH_RISK_003_REMEDIATION_REPORT.md"              docs/certifications/
cp "$SOURCE_DIR/STAGE_10_ORCHESTRATOR_IMPLEMENTATION.md"          docs/certifications/
cp "$SOURCE_DIR/STAGE_12_END_TO_END_CERTIFICATION.md"             docs/certifications/
cp "$SOURCE_DIR/STAGE_13_MULTITRIGGER_CERTIFICATION.md"           docs/certifications/
cp "$SOURCE_DIR/STAGE_14_HISTORICAL_WINDOW_CERTIFICATION.md"      docs/certifications/
cp "$SOURCE_DIR/STAGE_15_MULTIRUN_PERSISTENCE_CERTIFICATION.md"   docs/certifications/
cp "$SOURCE_DIR/STAGE_16_PERFORMANCE_CERTIFICATION.md"            docs/certifications/

# MOVE STAGE_11 out of app root → certifications
git mv STAGE_11_STREAMLIT_MVP_IMPLEMENTATION.md docs/certifications/
```

### Step 4 — Copy governance documents

```bash
cp "$SOURCE_DIR/PROJECT_DECISIONS.md"         docs/governance/
cp "$SOURCE_DIR/PROJECT_MASTER_REGISTER.md"   docs/governance/
cp "$SOURCE_DIR/PROJECT_RELEASE_PACKAGE.md"   docs/governance/
cp "$SOURCE_DIR/PROJECT_CHANGE_LOG.md"        docs/governance/
cp "$SOURCE_DIR/PROJECT_RISK_REGISTER.md"     docs/governance/
cp "$SOURCE_DIR/PROJECT_BACKLOG.md"           docs/governance/
cp "$SOURCE_DIR/TRACEABILITY_MATRIX.md"       docs/governance/
cp "$SOURCE_DIR/USER_STATE_DICTIONARY.md"     docs/governance/
cp "$SOURCE_DIR/RELEASE_GATES.md"             docs/governance/
cp "$SOURCE_DIR/REPOSITORY_CLEANUP_REPORT.md" docs/governance/
cp "$SOURCE_DIR/GITHUB_SYNC_PACKAGE.md"       docs/governance/
cp "$SOURCE_DIR/REPOSITORY_ORGANIZATION_PLAN.md" docs/governance/
```

### Step 5 — Place root-level files

```bash
cp "$SOURCE_DIR/CLAUDE.md" ./
# README.md already exists — add docs/ navigation block manually
```

### Step 6 — Verify file counts

```bash
find docs/remediation/   -name "*.md" | wc -l    # Expected: 8
find docs/certifications/ -name "*.md" | wc -l   # Expected: 8
find docs/governance/     -name "*.md" | wc -l   # Expected: 12
ls CLAUDE.md                                      # Must exist
ls README.md                                      # Must exist
```

### Step 7 — Verify no prohibited files are staged

```bash
git status | grep -E "PHASE_|WAVE_[1-6]|_IMPLEMENTATION_REPORT|PROJECT_MEMORY|GOVERNANCE_SYNC|REPOSITORY_VERIFICATION|\.pytest_cache"
# Expected: empty output
```

### Step 8 — Stage exactly the right files

```bash
git add docs/ CLAUDE.md README.md
git status
# Expected staged: 29 files in docs/ + CLAUDE.md + README.md changes = ~31 items
```

---

## SECTION 7 — COUNT RECONCILIATION

Total `.md` files in workspace: **62**  
Auto-generated (pytest cache): **2** → do_not_commit (already in .gitignore)  
Net document files: **60**

| Classification | Count | Action |
|---------------|-------|--------|
| remediation | 8 | commit to `docs/remediation/` |
| certifications | 8 | commit to `docs/certifications/` (incl. STAGE_11 move) |
| governance | 12 | commit to `docs/governance/` |
| root | 2 | `CLAUDE.md` (new) + `README.md` (update) |
| obsolete | 2 | do not commit: GOVERNANCE_SYNC_REPORT, REPOSITORY_VERIFICATION_REPORT |
| do_not_commit | 28 | session logs, superseded documents, internal notes |
| auto-generated | 2 | already excluded by .gitignore |
| **Total** | **62** | |

Files committed: **8 + 8 + 12 + 2 = 30** (plus README.md update = 31 operations)  
Files not committed: **2 + 28 + 2 = 32**

---

## SECTION 8 — DOCUMENT AUTHORITY HIERARCHY (FINAL)

For any conflict between committed documents, this hierarchy governs resolution:

```
Tier 1 — Binding Decisions
  docs/remediation/TRIGGER_AND_REENTRY_DECISION_MATRIX.md  (TDM-001)
  docs/governance/PROJECT_DECISIONS.md

Tier 2 — Architecture Reference
  docs/remediation/ARCHITECTURE_REMEDIATION_PACKAGE.md     (ARP-001)
  docs/remediation/[specific remediation documents]

Tier 3 — Implementation Contracts
  docs/remediation/IMPLEMENTATION_WAVES.md                 (IWP-001)
  docs/remediation/TESTING_STRATEGY.md                     (TST-001)

Tier 4 — Project Tracking
  docs/governance/PROJECT_MASTER_REGISTER.md
  docs/governance/TRACEABILITY_MATRIX.md
  docs/governance/USER_STATE_DICTIONARY.md

Tier 5 — Historical Record
  docs/certifications/[all stage certification reports]
  docs/governance/PROJECT_RELEASE_PACKAGE.md
  docs/governance/PROJECT_CHANGE_LOG.md

Tier 6 — Process and Meta
  docs/governance/GITHUB_SYNC_PACKAGE.md
  docs/governance/REPOSITORY_ORGANIZATION_PLAN.md          (this document)
  CLAUDE.md
```

---

*Document: ROP-001 | REPOSITORY_ORGANIZATION_PLAN.md | v1.0 | 2026-06-24*
