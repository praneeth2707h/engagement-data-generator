# TRACEABILITY MATRIX
# Engagement Data Generator — Version 1.0
# Project Governance Document

**Document Version:** 1.0
**Prepared:** 2026-06-21
**Role:** Chief Architect and Product Governance Lead
**Baseline:** Requirements_v1.md (2025-12-01)
**Authority:** PROJECT_DECISIONS.md governs all conflicts between documents.

**Source Documents Reviewed:**
- Requirements_v1.md
- Architecture_v2.md
- Technical_Design.md
- Technical_Design_Addendum.md
- Trigger_Engagement_Clarification.md
- PROJECT_DECISIONS.md
- PROJECT_BACKLOG.md
- PROJECT_CHANGE_LOG.md
- PHASE_2_REMEDIATION_PLAN.md
- PROJECT_HANDOFF.md

---

## Table of Contents

1. Document Information
2. Traceability Methodology
3. Requirement Traceability Matrix
4. Architecture Traceability Matrix
5. Business Rule Traceability Matrix
6. Validation Coverage Matrix
7. Backlog Traceability Matrix
8. Phase Traceability Matrix
9. Gap Analysis
10. Recommendations

---

## 1. Document Information

| Field | Value |
|-------|-------|
| Project | Engagement Data Generator |
| Version | 1.0 |
| Document ID | TRACEABILITY_MATRIX |
| Document Version | 1.0 |
| Baseline | Requirements_v1.md (2025-12-01) |
| Last Updated | 2026-06-22 (Phase 3 foundation sprint — ARCH-015 through ARCH-020 added; BIZ-023 date_utils status corrected) |
| Current Phase | Phase 2 Complete (Remediation Pending) — Phase 3 Not Started |

**Purpose:** This document provides end-to-end traceability from original requirements through architecture decisions, business rules, validation rules, implementation phases, and backlog items. It enables impact analysis (what breaks if requirement X changes?), coverage assessment (which requirements lack validation?), and gap identification (which requirements have no implementation owner?).

**Scope:** All requirements derived from Requirements_v1.md and clarified through the design document hierarchy. All architecture decisions ARCH-001 through ARCH-014 (ARCH-013 and ARCH-014 added 2026-06-21 governance sync). CFG-NEW-001 (reserved config field, added 2026-06-21). All approved business rules (BIZ-*, C-*, SIM-*, I-*, R-CA-*). All 35 validation rules (HR-001–HR-015, SR-001–SR-020). All 10 implementation phases. All backlog items BL-001 through BL-061.

**How to read this document:**
- Each matrix cross-references items by their canonical IDs.
- "—" means no direct relationship exists (and is expected).
- "⚠ GAP" marks a cell where a relationship is expected but absent.
- Status: Implemented | Pending | Deferred | Remediation Required

---

## 2. Traceability Methodology

### Requirement Derivation

Requirements are derived from Requirements_v1.md sections and subsequently refined by the document hierarchy:

```
Requirements_v1.md (baseline)
    ↓  clarified/superseded by
Architecture_v2.md
    ↓  further specified by
Technical_Design.md
    ↓  amended by
Technical_Design_Addendum.md
    ↓  highest-authority resolution by
Trigger_Engagement_Clarification.md
    ↓  all decisions finalized in
PROJECT_DECISIONS.md (single source of truth)
```

Requirements that were ambiguous in Requirements_v1.md are traced to the document where they were formally resolved.

### Requirement ID Convention

Requirements are assigned IDs REQ-001 through REQ-030 based on the logical groupings in Requirements_v1.md and the handoff. Where a requirement was formally split or renamed by a later document, both the original requirement ID and the superseding decision ID are recorded.

### Traceability Link Types

| Symbol | Meaning |
|--------|---------|
| ✓ | Fully covered/implemented |
| ~ | Partially covered (some aspects implemented, some deferred) |
| ⚠ | Coverage gap — relationship expected but not present |
| D | Deferred — intentionally absent from current scope |
| R | Remediation required — defect found |

### Implementation Status Definitions

| Status | Meaning |
|--------|---------|
| Implemented | Fully implemented and tested in a completed phase |
| Pending | Implementation specified; not yet coded |
| Remediation Required | Implemented but defective; fix required before Phase 3 |
| Deferred | Not in current release scope |
| Not Started | Phase not yet begun |

---

## 3. Requirement Traceability Matrix

### Requirement Inventory

The following 30 requirements were derived from Requirements_v1.md, with refinements documented in the design document hierarchy.

| REQ-ID | Requirement Summary | Source Document | Classification |
|--------|---------------------|-----------------|----------------|
| REQ-001 | Local desktop application — no server, no cloud | Requirements_v1 | Deployment |
| REQ-002 | Synthetic pharma marketing engagement data generation | Requirements_v1 | Core Purpose |
| REQ-003 | Non-technical users configure via Streamlit UI | Requirements_v1 | UI |
| REQ-004 | Support Display channel (Endemic, Programmatic, Banner) — Impression + Click | Requirements_v1 | Channel |
| REQ-005 | Support Email channel — Sent + Open + Click with causal dependencies | Requirements_v1 | Channel |
| REQ-006 | Support WhatsApp channel — Sent + Open + Click with causal dependencies | Requirements_v1 | Channel |
| REQ-007 | Trigger file defines eligible users per campaign | Requirements_v1 | Engine |
| REQ-008 | Trigger priority resolution (1 = highest) when user appears in multiple triggers | Requirements_v1 | Engine |
| REQ-009 | Segment assignment and priority resolution from trigger file | Requirements_v1 | Engine |
| REQ-010 | Multi-ad linear journey: Ad1 → Ad2 → AdN | Requirements_v1 | Journey |
| REQ-011 | Duration-based ad advance after configurable duration_days | Requirements_v1 | Journey |
| REQ-012 | Click-based ad advance when move_on_click=True | Requirements_v1 | Journey |
| REQ-013 | Journey completion triggers cooling period (default 90 days) | Requirements_v1 | Journey |
| REQ-014 | User re-entry after cooling period expires on new trigger appearance | Requirements_v1 | Journey |
| REQ-015 | Trigger Engagement Rate (TER) as reporting KPI only | Technical_Design_Addendum / Trigger_Engagement_Clarification | Metric |
| REQ-016 | Trigger Capacity Consumption (TCC) as engine capacity driver | Technical_Design_Addendum / Trigger_Engagement_Clarification | Engine |
| REQ-017 | User state schema persisted across runs; prior state loaded as input | Requirements_v1 | State |
| REQ-018 | Four behavior profiles (Highly_Engaged, Moderate, Passive, Dormant) | Requirements_v1 | Simulation |
| REQ-019 | Channel affinity model (Display, Email, WhatsApp) — float32 [0.0–1.0] | Technical_Design_Addendum | Simulation |
| REQ-020 | Creative affinity model — dynamic per-ad columns — float32 [0.0–1.0] | Technical_Design_Addendum | Simulation |
| REQ-021 | 15 hard validation rules — FAIL blocks all export except ValidationReport | Technical_Design | Validation |
| REQ-022 | 20 soft validation rules — WARNING never blocks export | Technical_Design | Validation |
| REQ-023 | Three-tier configuration (Category A/B/C); Category C not UI-exposed | Technical_Design_Addendum | Configuration |
| REQ-024 | Configuration snapshot save/load in JSON; schema version enforcement | Technical_Design_Addendum | Configuration |
| REQ-025 | Composite engagement scoring: 5 weighted components + jitter | Technical_Design | Simulation |
| REQ-026 | Reproducible output — same input + same seed → identical output | Technical_Design | Simulation |
| REQ-027 | 7 Excel output workbooks; each includes Run_Metadata sheet | Technical_Design | Output |
| REQ-028 | Performance: 1K users ≤ 1 min; 10K ≤ 5 min; 50K ≤ 15 min | Architecture_v2 | Performance |
| REQ-029 | Weekly fatigue enforcement — ISO Monday reset BEFORE processing | Technical_Design_Addendum | Engine |
| REQ-030 | Historical engagement deduplication on file load (before any filtering) | Technical_Design | Engine |

---

### Requirement Traceability — Full Matrix

| REQ-ID | Requirement Summary | Architecture Decision | Technical Design Section | Business Rule | Validation Rule | Backlog Item | Implementation Phase | Target Module(s) | Status |
|--------|---------------------|-----------------------|--------------------------|---------------|-----------------|--------------|---------------------|-----------------|--------|
| REQ-001 | Local desktop deployment | ARCH-001 (single campaign/run) | Tech Design §Deployment | — | — | BL-004 (sample files) | Phase 9 (UI) | app/ | Pending |
| REQ-002 | Synthetic pharma data generation | ARCH-003 (11-stage pipeline) | Tech Design §Pipeline | — | SR-020 (Realism Score) | BL-002, BL-003 | Phase 3–8 | core/ | Not Started |
| REQ-003 | Non-technical Streamlit UI | ARCH-005 (UI isolation) | Tech Design §UI | — | — | BL-002 | Phase 9 | app/ | Not Started |
| REQ-004 | Display channel | ARCH-004 (BaseChannel) | Tech Design §Channels | — | HR-003, HR-004 | — | Phase 5 | channels/display.py | Not Started |
| REQ-005 | Email channel | ARCH-004 (BaseChannel) | Tech Design §Channels | — | HR-005, HR-006 | — | Phase 5 | channels/email.py | Not Started |
| REQ-006 | WhatsApp channel | ARCH-004 (BaseChannel) | Tech Design §Channels | — | HR-007, HR-008 | — | Phase 5 | channels/whatsapp.py | Not Started |
| REQ-007 | Trigger file eligibility | ARCH-001, ARCH-002 | Tech Design §Input | BIZ-019 (Campaign_ID default) | HR-015 (Campaign_ID match) | BL-001 (defect fix) | Phase 2 (input_loader), Phase 3 (Audience Manager) | core/input_loader.py, core/audience_manager.py | Remediation Required |
| REQ-008 | Trigger priority resolution | — | Tech Design §Audience | — | SR-008 (trigger distribution) | BL-010 | Phase 3 | core/audience_manager.py | Not Started |
| REQ-009 | Segment assignment/priority | — | Tech Design §Audience | — | SR-007 (segment distribution) | BL-010 | Phase 3 | core/audience_manager.py | Not Started |
| REQ-010 | Multi-ad linear journey | ARCH-003 (Stage 5) | Tech Design §Journey | — | HR-001 (journey sequence) | BL-027 (V2 branching) | Phase 4 | core/journey_engine.py | Not Started |
| REQ-011 | Duration-based ad advance | — | Tech Design §Journey | — | HR-001 | — | Phase 4 | core/journey_engine.py | Not Started |
| REQ-012 | Click-based ad advance | — | Tech Design §Journey | BIZ-018 / C-001 (Move On Click exclusive) | HR-001 | — | Phase 4 | core/journey_engine.py | Not Started |
| REQ-013 | Cooling period (default 90 days) | — | Tech Design Addendum §Cooling | — | HR-002, HR-013 | BL-026 (V2 per-trigger cooldown) | Phase 3 (classify) | core/audience_manager.py, core/fatigue_engine.py | Not Started |
| REQ-014 | Re-entry after cooling | — | Tech Design Addendum §Re-entry | — | — | — | Phase 3 | core/audience_manager.py | Not Started |
| REQ-015 | TER as reporting KPI | — | Trigger_Engagement_Clarification §TER | BIZ-003 (TER/TCC separation), BIZ-004 (90-day window) | SR-005 (TER vs target) | FE-018 (Rolling TER Windows, V2) | Phase 7 (Validation) | core/validation_engine.py, utils/schema_validator.py | Not Started |
| REQ-016 | TCC as engine driver | — | Trigger_Engagement_Clarification §TCC | BIZ-003, BIZ-004, BIZ-011 | SR-006 (capacity ≤ 0) | BL-008 (ceil fix) | Phase 2 (capacity_row), Phase 3 (Audience Manager) | models/capacity_row.py, core/audience_manager.py | Remediation Required |
| REQ-017 | User state persistence | ARCH-002 (composite PK) | Tech Design §UserState | BIZ-019 (Campaign_ID), R-CA-004 (schema reconciliation) | — | BL-004 | Phase 2 (models), Phase 3 (state init), Phase 8 (export) | models/user_state.py, core/user_state_manager.py | Remediation Required |
| REQ-018 | Four behavior profiles | — | Tech Design Addendum §Profiles | SIM-001 (composite score) | SR-020 (Realism Score) | BL-024 (V2 Category B), BL-047 (calibration) | Phase 5 | core/behavior_engine.py | Not Started |
| REQ-019 | Channel affinity model | ARCH-012 (dynamic columns) | Tech Design Addendum §ChannelAffinity | — | — | BL-020 (V2 thresholds), BL-048 (calibration) | Phase 5 | core/behavior_engine.py, models/user_state.py | Not Started |
| REQ-020 | Creative affinity model | ARCH-012 (Option A) | Tech Design Addendum §CreativeAffinity | R-CA-004 (schema reconciliation) | — | — | Phase 2 (excel_utils), Phase 5 (behavior) | utils/excel_utils.py, core/behavior_engine.py | Implemented (Phase 2) |
| REQ-021 | 15 hard validation rules | ARCH-006 (self-registering rules) | Tech Design §ValidationFramework | VAL-001 | HR-001–HR-015 | BL-011 (rules catalog, V1.1) | Phase 7 | rules/hard/, core/validation_engine.py | Not Started |
| REQ-022 | 20 soft validation rules | ARCH-006 | Tech Design §ValidationFramework | VAL-002 | SR-001–SR-020 | BL-011 | Phase 7 | rules/soft/, core/validation_engine.py | Not Started |
| REQ-023 | Three-tier config (A/B/C) | — | Tech Design Addendum §ConfigStrategy | — | — | — | Phase 2 (config_registry), Phase 9 (UI) | models/config_registry.py, app/pages/ | Remediation Required |
| REQ-024 | Config snapshot save/load | — | Tech Design Addendum §ConfigIO | CFG-005 (schema version) | — | BL-016 (V1.1 UX) | Phase 2 | utils/config_io.py | Implemented (Phase 2) |
| REQ-025 | Composite engagement scoring | — | Tech Design §ScoringFormula | SIM-001, SIM-002 | SR-020 | BL-010 (missing fields), BL-023 (V2 sliders) | Phase 5, Phase 6 | core/behavior_engine.py, core/allocation_engine.py | Not Started |
| REQ-026 | Reproducible output | — | Tech Design §Reproducibility | SIM-019 (MD5 seed) | — | BL-022 (V2 RNG snapshot), BL-045 (MD5 research) | Phase 2 (seed), Phase 5 (RNG usage) | core/input_loader.py (_per_user_seed) | Implemented (Phase 2) |
| REQ-027 | 7 Excel output workbooks | ARCH-009 (openpyxl direct) | Tech Design §ExportEngine | — | — | BL-012 (V1.1 CSV option) | Phase 8 | core/export_engine.py, utils/excel_utils.py | Not Started |
| REQ-028 | Performance targets | ARCH-011 (DataFrame-first) | Tech Design §Performance | — | — | BL-005, BL-044 | Phase 10 | core/ (all stages) | Not Started |
| REQ-029 | Weekly fatigue enforcement | — | Tech Design §FatigueEngine | BIZ-023 / C-003 (ISO Monday reset before processing) | HR-009, HR-012 | — | Phase 6 | core/fatigue_engine.py | Not Started |
| REQ-030 | Historical deduplication on load | — | Tech Design §InputLoader | BIZ-021 / C-005 | — | BL-035 (iterrows cleanup) | Phase 2 | core/input_loader.py | Remediation Required |

---

## 4. Architecture Traceability Matrix

| Architecture Decision | Decision ID | Related Requirements | Technical Design References | Modules Impacted | Validation Coverage | Test Coverage |
|-----------------------|-------------|---------------------|---------------------------|------------------|--------------------|-|
| Single campaign per run in V1 | ARCH-001 | REQ-001, REQ-007 | Tech Design §CampaignScope | All core/ modules; all DataFrames carry single campaign_id | HR-015 (Campaign_ID match) | Phase 2 tests (config_registry), Phase 3 tests (audience_manager) — Not Started |
| Composite primary key (Campaign_ID, User_ID) | ARCH-002 | REQ-017, REQ-007 | Tech Design §DataFrameSchema | models/user_state.py, all DataFrames, all 7 output workbooks | HR-015 | Phase 2 tests — Remediation Required (MM-006: user_state import error) |
| 11-stage pipeline with strict execution order | ARCH-003 | REQ-002, REQ-028 | Tech Design §Pipeline | core/run_controller.py (orchestrates all 11 stages) | SR-020 (Realism Score evaluates output of all stages) | Phase 10 integration tests — Not Started |
| BaseChannel abstract class for Display, Email, WhatsApp | ARCH-004 | REQ-004, REQ-005, REQ-006 | Tech Design §Channels | channels/base.py, channels/display.py, channels/email.py, channels/whatsapp.py | HR-003–HR-008 | Phase 5 unit tests — Not Started |
| Strict import tier hierarchy (core/ never imports app/) | ARCH-005 | REQ-001, REQ-003 | Tech Design §ImportRules | All modules (enforced by CI linting) | ⚠ GAP: No automated validation rule enforces this at runtime | BL-006 (CI import linting) — Not Started |
| Self-registering rule classes (hard/ and soft/) | ARCH-006 | REQ-021, REQ-022 | Tech Design §RuleFramework | rules/hard/ (15 rules), rules/soft/ (20 rules), core/validation_engine.py | All HR-* and SR-* rules | Phase 7 unit tests — Not Started |
| pytest as test framework; conftest.py for fixtures | ARCH-007 | All REQs (test coverage) | Tech Design §TestStrategy | tests/ (all test files) | Indirect (test coverage gate via BL-007) | All phases — Phase 2 Remediation Required |
| pyproject.toml as build/metadata file | ARCH-008 | REQ-001 | Tech Design §BuildSystem | pyproject.toml | — | — |
| openpyxl direct write; no pd.to_excel() | ARCH-009 | REQ-027 | Tech Design §ExportEngine | core/export_engine.py, utils/excel_utils.py | ⚠ GAP: No validation rule verifies that pd.to_excel() was not used at runtime | CI grep check (BL-007 related) — Not Started |
| run_controller.py as sole pipeline orchestrator | ARCH-010 | REQ-002, REQ-003 | Tech Design §Pipeline | core/run_controller.py | SR-020 (Realism Score — post-run summary) | Phase 8 + Phase 10 tests — Not Started |
| DataFrame-first; no iterrows() in production code | ARCH-011 | REQ-028 | Tech Design §Performance, docs/performance_guidelines.md | All core/ modules | **RESOLVED — 2026-06-22 (REM-009). PV-001 fixed. Zero grep hits. MT-012 regression test added to test_input_loader.py.** | CI grep check (BL-064-CI) pending CI infrastructure |
| Dynamic creative affinity columns — Option A | ARCH-012 | REQ-020 | Creative_Affinity_Design_Review §OptionA | models/user_state.py, utils/excel_utils.py (reconcile_creative_affinity_columns), core/behavior_engine.py | ⚠ GAP: No explicit validation rule checks that creative affinity columns are float32 in export | Phase 2 tests (excel_utils) — Implemented; Phase 5 tests — Not Started |
| Alphabetical Trigger_Name tiebreak when priority tied; unified sort chain: df.sort_values(['priority','Trigger_Name','Segment']).drop_duplicates(subset=['Campaign_ID','User_ID'],keep='first'); WARNING log when tiebreak fires | ARCH-013 | REQ-008 | PHASE_3_ARCHITECTURE_DECISIONS.md §DD-013 | core/audience_manager.py (resolve_triggers) | SR-008 (trigger distribution) | Phase 3 — resolve_triggers() — TC-AUD-001 through TC-AUD-007 — APPROVED awaiting implementation |
| Segment follows winning trigger's row (Option A); alphabetical Segment sub-sort handles pathological duplicates (same trigger name, same user, two segments); implemented by same unified sort chain as ARCH-013 | ARCH-014 | REQ-009 | PHASE_3_ARCHITECTURE_DECISIONS.md §DD-014 | core/audience_manager.py (resolve_segments) | SR-007 (segment distribution) | Phase 3 — resolve_segments() — TC-AUD-008 through TC-AUD-012 — APPROVED awaiting implementation |
| strict_priority_validation: bool = False reserved field on ConfigRegistry — no-op in V1; reserved for future strict-audit mode (ValidationError instead of alphabetical tiebreak) | CFG-NEW-001 | REQ-023 | PHASE_3_ARCHITECTURE_DECISIONS.md §CFG-NEW-001 | models/config_registry.py (strict_priority_validation field) | — | Phase 3 — field present, behavior deferred — APPROVED no-op |
| EligibilityStatus canonical values: NEW, ACTIVE, COOLING, RE_ENTRY (="Re_Entry"), SKIPPED, EXCLUDED; deprecated ELIGIBLE/INELIGIBLE/COMPLETED retained for backward compat only | ARCH-015 | REQ-012 | PHASE_3_BLOCKER_RESOLUTION.md RESOLUTION 02 | models/enums.py (EligibilityStatus); core/audience_manager.py (classify_eligibility) | AUDIT-002 | Phase 3 — IMPLEMENTED 2026-06-22; test_enums.py — 3 tests PASSING |
| UserState weekly counters are per-action (impressions/clicks/opens/engagements), NOT per-channel; ConfigRegistry cap fields align | ARCH-016 | REQ-029 | PHASE_3_BLOCKER_RESOLUTION.md RESOLUTION 04 | models/user_state.py; models/config_registry.py; core/fatigue_engine.py | AUDIT-004 | Phase 3 — design confirmed; fatigue_engine.py — Phase 6 Not Started |
| Trigger_History delimiter is pipe (|); TRIGGER_HISTORY_DELIMITER = "|" in utils/constants.py; no inline literals | ARCH-017 | REQ-031 | PHASE_3_BLOCKER_RESOLUTION.md Decision A | utils/constants.py; models/user_state.py; core/user_state_manager.py; core/export_engine.py | AUDIT-013; R-NEW-001 | Phase 3 — IMPLEMENTED 2026-06-22; constant present in constants.py |
| JourneyStatus.DROPPED → EligibilityStatus.EXCLUDED (first/highest-priority condition in classify_eligibility np.select call) | ARCH-018 | REQ-012 | PHASE_3_BLOCKER_RESOLUTION.md Decision B | core/audience_manager.py (classify_eligibility) | AUDIT-011 | Phase 3 — Wave 1 audience_manager.py — Not Started |
| ConfigRegistry.__post_init__ rejects trigger with priority < 1 (ConfigError) as defense-in-depth; TriggerConfig.__post_init__ is primary guard | ARCH-019 | REQ-008 | PHASE_3_BLOCKER_RESOLUTION.md Decision C | models/config_registry.py (__post_init__) | MISS-004 | Phase 3 — IMPLEMENTED 2026-06-22; test_config_registry.py test PASSING |
| allow_reentry=False classifies cooling-expired users as EXCLUDED (not RE_ENTRY); np.select priority order documented in ARCH-020 | ARCH-020 | REQ-012 | PHASE_3_BLOCKER_RESOLUTION.md Decision D | core/audience_manager.py (classify_eligibility); models/config_registry.py (allow_reentry field) | AUDIT-014; MISS-003 | Phase 3 — Wave 1 audience_manager.py — Not Started |

---

## 5. Business Rule Traceability Matrix

### System-Level Rules

| Rule ID | Rule Name | Source Document | Decision ID | Implementation Location | Validation Rule | Test Coverage |
|---------|-----------|-----------------|-------------|------------------------|-----------------|---------------|
| BIZ-003 | TER and TCC are separate concepts with separate code paths | Trigger_Engagement_Clarification | BIZ-003 | core/audience_manager.py (TCC), core/validation_engine.py (TER) | SR-005 (TER), SR-006 (TCC) | Phase 3 + Phase 7 tests — Not Started |
| BIZ-004 | Historical window default Last 90 Days (TCC only, not TER) | Technical_Design_Addendum | BIZ-004 | core/input_loader.py (load_historical_file), core/audience_manager.py | SR-005, SR-006 | Phase 2 tests (input_loader) — Remediation Required |
| BIZ-011 | QUALIFYING_ACTIONS is Category C — system constant in schema_validator.py | Trigger_Engagement_Clarification | BIZ-011 | utils/schema_validator.py (QUALIFYING_ACTIONS constant) | All rules that evaluate engagement events | Phase 2 tests (schema_validator) — TCC-002 documentation gap |
| BIZ-018 / C-001 | Move On Click is exclusive — skip duration check if click-advance fires | Technical_Design_Addendum | BIZ-018 | core/journey_engine.py | HR-001 (journey sequence) | Phase 4 tests — Not Started |
| BIZ-019 | Campaign_ID absent → insert "Default" and log INFO | Technical_Design_Addendum | BIZ-019 | core/input_loader.py (load_trigger_file, load_historical_file) | — | Phase 2 tests (input_loader) — Remediation Required |
| BIZ-021 / C-005 | Historical deduplication on load — before any filtering | Technical_Design | BIZ-021 | core/input_loader.py (load_historical_file) — first transform after date parse | — | Phase 2 tests (input_loader) — LM-002 ordering comment gap |
| BIZ-023 / C-003 | Weekly counter reset at ISO Monday boundary, BEFORE processing | Technical_Design_Addendum | BIZ-023 | core/fatigue_engine.py; utils/date_utils.py (iso_week_start) | HR-009, HR-012 | utils/date_utils.py CREATED Phase 3 pre-wave 2026-06-22; tests/unit/test_date_utils.py — 3 tests passing; Phase 6 fatigue_engine.py — Not Started |
| C-002 | Campaign ID filter in Audience Manager | Technical_Design_Addendum | — | core/audience_manager.py | HR-015 | Phase 3 tests — Not Started |
| I-001 | Vendor precedence: per-ad vendor overrides campaign default_vendor | Technical_Design | I-001 | models/config_registry.py (get_effective_vendor) | — | Phase 2 tests (config_registry) — Remediation Required (MM-004) |
| R-CA-004 | Creative affinity schema reconciliation on prior state load | Technical_Design_Addendum | ARCH-012 | utils/excel_utils.py (reconcile_creative_affinity_columns) | ⚠ GAP: No validation rule verifies reconciliation was applied | Phase 2 tests (excel_utils) — Implemented |
| SIM-001 | Composite scoring formula: 5 weighted components + jitter | Technical_Design | SIM-001 | core/behavior_engine.py | SR-020 (Realism Score) | Phase 5 tests — Not Started; BL-010 (missing ConfigRegistry fields) — Remediation Required |
| SIM-002 | Scoring weights are Category B (Advanced Configurable) | Technical_Design | SIM-002 | models/config_registry.py (5 weight fields), app/pages/advanced_settings.py | — | Phase 2 tests — Remediation Required (MM-007: fields missing) |
| SIM-019 | Per-user RNG seed via hashlib.md5 — never Python hash() | Technical_Design | SIM-019 | core/input_loader.py (_per_user_seed) | — | Phase 2 tests (input_loader) — Implemented |
| CFG-005 | CONFIG_SCHEMA_VERSION = "2.0" — mismatch raises SchemaVersionError | Technical_Design_Addendum | CFG-005 | utils/version.py, utils/config_io.py | — | Phase 2 tests (config_io) — Implemented |
| VAL-001 | Hard rule FAIL blocks all export except ValidationReport | Technical_Design | VAL-001 | core/validation_engine.py, core/export_engine.py | All HR-* rules | Phase 7 + Phase 8 tests — Not Started |
| VAL-002 | Soft rules never block export | Technical_Design | VAL-002 | core/validation_engine.py | All SR-* rules | Phase 7 tests — Not Started |

### Journey-Level Rules

| Rule ID | Rule Name | Source Document | Implementation Location | Validation Rule | Test Coverage |
|---------|-----------|-----------------|------------------------|-----------------|---------------|
| C-001 | Move On Click exclusive (click-advance fires → skip duration check) | Technical_Design_Addendum | core/journey_engine.py | HR-001 | Phase 4 tests — Not Started |
| C-002 | Campaign ID filter before audience resolution | Technical_Design_Addendum | core/audience_manager.py | HR-015 | Phase 3 tests — Not Started |
| C-003 | Weekly counter reset: ISO Monday, before any processing | Technical_Design_Addendum | core/fatigue_engine.py + utils/date_utils.py | HR-009, HR-012 | Phase 2 (date_utils) — Implemented; Phase 6 — Not Started |
| C-005 | Historical deduplication immediately on load, before filtering | Technical_Design | core/input_loader.py | — | Phase 2 (partial) — LM-002 comment gap |

---

## 6. Validation Coverage Matrix

### Hard Rules (15 total — FAIL or PASS; any FAIL blocks export)

| Rule ID | Rule Name | Requirement Protected | Business Rule Protected | Phase Implemented | Implementation Status |
|---------|-----------|-----------------------|------------------------|-------------------|-----------------------|
| HR-001 | Journey stages progress strictly sequentially | REQ-010, REQ-011, REQ-012 | C-001 (Move On Click exclusive) | Phase 7 | Not Started |
| HR-002 | No events during cooling period | REQ-013 | — | Phase 7 | Not Started |
| HR-003 | Display Click requires same-day Impression | REQ-004 | — | Phase 7 | Not Started |
| HR-004 | Display Click must occur on same date as Impression | REQ-004 | — | Phase 7 | Not Started |
| HR-005 | Email Open requires prior Sent | REQ-005 | — | Phase 7 | Not Started |
| HR-006 | Email Click requires prior Open | REQ-005 | — | Phase 7 | Not Started |
| HR-007 | WhatsApp Open requires prior Sent | REQ-006 | — | Phase 7 | Not Started |
| HR-008 | WhatsApp Click requires prior Open | REQ-006 | — | Phase 7 | Not Started |
| HR-009 | Max daily impressions per user (default 3) | REQ-029 | C-003 (fatigue reset) | Phase 7 | Not Started |
| HR-010 | ⚠ GAP — Not explicitly listed in handoff; assumed within range HR-001–HR-015 | — | — | Phase 7 | Not Started |
| HR-011 | ⚠ GAP — Not explicitly listed in handoff; assumed within range HR-001–HR-015 | — | — | Phase 7 | Not Started |
| HR-012 | Max weekly engagements per user (default 3) | REQ-029 | BIZ-023 / C-003 | Phase 7 | Not Started |
| HR-013 | No engagement events during engagement cooldown period | REQ-013 | — | Phase 7 | Not Started |
| HR-014 | ⚠ GAP — Not explicitly listed in handoff; assumed within range HR-001–HR-015 | — | — | Phase 7 | Not Started |
| HR-015 | All event Campaign_IDs must match config.campaign_id | REQ-007, REQ-017 | ARCH-001, BIZ-019, C-002 | Phase 7 | Not Started |

### Soft Rules (20 total — WARNING or PASS; never block export)

| Rule ID | Rule Name | Requirement Protected | Business Rule Protected | Phase Implemented | Implementation Status |
|---------|-----------|-----------------------|------------------------|-------------------|-----------------------|
| SR-001 | ⚠ GAP — Not explicitly listed in handoff for SR-001 through SR-004 | — | — | Phase 7 | Not Started |
| SR-002 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-003 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-004 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-005 | TER vs target engagement rate | REQ-015 | BIZ-003, BIZ-004 | Phase 7 | Not Started |
| SR-006 | Remaining capacity ≤ 0 (no new events will be generated) | REQ-016 | BIZ-003 | Phase 7 | Not Started |
| SR-007 | Segment distribution within ±10% of population proportions | REQ-009 | — | Phase 7 | Not Started |
| SR-008 | Trigger distribution within ±10% of population proportions | REQ-008 | — | Phase 7 | Not Started |
| SR-009 | ⚠ GAP — Not explicitly listed in handoff for SR-009 through SR-019 | — | — | Phase 7 | Not Started |
| SR-010 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-011 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-012 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-013 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-014 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-015 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-016 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-017 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-018 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-019 | ⚠ GAP — Not explicitly listed in handoff | — | — | Phase 7 | Not Started |
| SR-020 | Composite Simulation Realism Score (0–100; Advisory — always INFO) | REQ-002 | SIM-001 | Phase 7 | Not Started |

**Note on SR-001–SR-004 and SR-009–SR-019 gaps:** The handoff identifies SR-005 through SR-008 and SR-020 by name. The remaining 13 soft rules (SR-001–SR-004, SR-009–SR-019) are specified in `uploads/Validation_Rules_Catalog.md`, which was not available for direct review. These rules are confirmed to exist (the framework supports 20 soft rules) but their individual names, requirements protected, and business rules cannot be traced without reading Validation_Rules_Catalog.md. See Gap Analysis Section 9.

### Validation Rule Summary

| Category | Total | Named in Design Docs | ⚠ Gap (unnamed) | Implementation Status |
|----------|-------|---------------------|-----------------|----------------------|
| Hard Rules | 15 | 9 (HR-001–HR-009, HR-012, HR-013, HR-015) | 3 (HR-010, HR-011, HR-014) | Not Started (Phase 7) |
| Soft Rules | 20 | 6 (SR-005–SR-008, SR-020) | 14 (SR-001–SR-004, SR-009–SR-019) | Not Started (Phase 7) |
| **Total** | **35** | **15 fully traced** | **17 partially traced** | **0 implemented** |

---

## 7. Backlog Traceability Matrix

### V1 Critical (Must Ship)

| Backlog Item | Title | Originating Requirement | Originating Decision | Target Release | Key Dependencies |
|-------------|-------|------------------------|---------------------|----------------|-----------------|
| BL-001 | Resolve Phase 2 Critical Defects | REQ-007, REQ-016, REQ-017, REQ-023 | ARCH-001, ARCH-002, MM-001–006 | V1 (pre-Phase-3) | None (blocks all) |
| BL-002 | Complete Phase 3–10 Implementation | All REQs | All ARCH decisions | V1 | BL-001 |
| BL-003 | Integration Tests (Phase 10) | REQ-002 (realism), REQ-027 (7 workbooks) | ARCH-003 | V1 | BL-002 |
| BL-004 | Sample Input Files | REQ-003 (non-technical users) | — | V1 | BL-002 |
| BL-005 | Performance Validation | REQ-028 | ARCH-011 | V1 | BL-002 |
| BL-006 | CI Import Linting | — | ARCH-005 | V1 | BL-002 |
| BL-007 | CI Coverage Gate (≥90%) | — | ARCH-007 | V1 | BL-003 |
| BL-008 | Fix ceil() in RemainingCapacityRow | REQ-016 (TCC accuracy) | — | V1 (pre-Phase-3) | None |
| BL-009 | Fix Phase 2 Test Gaps (MT-001–MT-012) | REQ-016, REQ-023 | ARCH-007 | V1 (pre-Phase-3) | BL-001 |
| BL-010 | Add Missing ConfigRegistry Fields | REQ-025 (composite scoring), REQ-018 | SIM-001, SIM-002 | V1 (pre-Phase-5) | BL-001 |

### V1.1 Post-Release

| Backlog Item | Title | Originating Requirement | Originating Decision | Target Release | Key Dependencies |
|-------------|-------|------------------------|---------------------|----------------|-----------------|
| BL-011 | Standalone Validation_Rules_Catalog.md | REQ-021, REQ-022 | DEF-008 | V1.1 | Phase 7 complete |
| BL-012 | CSV Export for EngagementEvents | REQ-027 (output formats) | ARCH-009 | V1.1 | Phase 8 complete |
| BL-013 | Run History Tracking | REQ-003 (user experience) | — | V1.1 | Phase 8, 9 |
| BL-014 | Additional Sample Files | REQ-003 | — | V1.1 | BL-003 |
| BL-015 | Engagement Score Trend in SimulationReport | REQ-027 | — | V1.1 | Phase 8 |
| BL-016 | Config Save/Load UX Improvement | REQ-024 | CFG-005 | V1.1 | Phase 9 |
| BL-017 | Dry Run / Validate-Only Mode | REQ-021, REQ-022 | VAL-001, VAL-002 | V1.1 | Phase 8, 9 |

### V2 Major Enhancements

| Backlog Item | Title | Originating Requirement | Originating Decision | Target Release | Key Dependencies |
|-------------|-------|------------------------|---------------------|----------------|-----------------|
| BL-018 | Multi-Campaign Per Run | REQ-007, REQ-017 | DEF-001 / ARCH-001 | V2 | ARCH-002 composite PK |
| BL-019 | Configurable Qualifying Actions | REQ-015, REQ-016 | DEF-003 / BIZ-011 | V2 | DEF-008 (rules catalog) |
| BL-020 | Historical Affinity Thresholds as Category B | REQ-019 | DEF-005 | V2 | RE-007 (research) |
| BL-021 | Timezone Configuration | REQ-029 (weekly reset) | DEF-006 | V2 | — |
| BL-022 | RNG State Snapshot Per Stage | REQ-026 (reproducibility) | DEF-007 | V2 | Phase 8 Run Controller |
| BL-023 | Scoring Weights UI Sliders | REQ-025, REQ-023 | SIM-002 / DEF-009 | V2 | BL-010 |
| BL-024 | Profile Evolution Probabilities as Category B | REQ-018 | — | V2 | RE-006 (research) |
| BL-025 | Behavior Profile Density Thresholds as Category B | REQ-018 | — | V2 | RE-006 |
| BL-026 | Engagement Cooldown as Per-Trigger Setting | REQ-013 | — | V2 | BL-018 |
| BL-027 | Journey Branching (Conditional Ad Sequences) | REQ-010 | — | V2 | BL-018 |
| BL-028 | Audience Forecast Accuracy (Monte Carlo) | REQ-015, REQ-016 | — | V2 | BL-023, Phase 6 |

### V3 Platform Features

| Backlog Item | Title | Originating Requirement | Originating Decision | Target Release | Key Dependencies |
|-------------|-------|------------------------|---------------------|----------------|-----------------|
| BL-029 | Channel Plugin Framework | REQ-004, REQ-005, REQ-006 | DEF-002 | V3 | V1+V2 stable |
| BL-030 | Background Thread Execution | REQ-028 (performance) | DEF-004 | V3 | BL-022 (RNG snapshots) |
| BL-031 | REST API / Headless Mode | REQ-001 (deployment) | — | V3 | ARCH-005 isolation |
| BL-032 | Cloud Storage Output Target | REQ-027 | — | V3 | BL-031 |
| BL-033 | Scheduled Batch Run Support | REQ-002 | — | V3 | BL-030, BL-031 |
| BL-034 | Database Output Target (SQL) | REQ-027 | — | V3 | BL-031, stable schema |

### New Backlog Items (Added 2026-06-21)

| Backlog Item | Title | Originating Requirement | Originating Decision | Target Release | Key Dependencies |
|-------------|-------|------------------------|---------------------|----------------|-----------------|
| FE-018 / BL-056 | Rolling TER Windows with validation context-awareness | REQ-015 | BIZ-003, BIZ-004 | V2 | SR-005 (Phase 7 stable) |
| FE-019 / BL-057 | Trigger Saturation Protection | REQ-016 | SR-006 | V2 | Phase 3, 7, 9 |
| FE-020 / BL-058 | Segment Saturation Protection | REQ-009, REQ-016 | — | V2 | FE-019, Phase 3, 7 |
| FE-021 / BL-059 | Engagement Decay Model (Exponential) | REQ-018, REQ-025 | SIM-001 | V2 | BL-042 (calibration) |
| FE-022 / BL-060 | Historical Engagement Weighting | REQ-016 | BIZ-004 | V2 | BL-048 (calibration) |
| FE-023 / BL-061 | Campaign Seasonality Modeling | REQ-002, REQ-025 | SIM-001 | V3 | Phase 5 stable, V2 config |

---

## 8. Phase Traceability Matrix

Each implementation phase is mapped to the requirements it satisfies, architecture decisions it implements, business rules it enforces, validation rules it enables, and modules it delivers.

---

### Phase 1 — Project Skeleton (COMPLETE)

| Dimension | Items |
|-----------|-------|
| Requirements | REQ-001 (deployment structure), REQ-026 (version.py / seed infrastructure) |
| Architecture Decisions | ARCH-005 (import hierarchy via directory structure), ARCH-007 (pytest conftest.py), ARCH-008 (pyproject.toml) |
| Business Rules | BIZ-011 (QUALIFYING_ACTIONS stub in schema_validator.py), CFG-005 (CONFIG_SCHEMA_VERSION in version.py) |
| Validation Rules | None (validation engine not yet built) |
| Modules Delivered | utils/logger.py, utils/constants.py, utils/exceptions.py, utils/version.py, models/enums.py, docs/performance_guidelines.md, all stub modules |
| Status | COMPLETE |

---

### Phase 2 — Core Data Models, Input Loader, Config Loader, Utilities (COMPLETE — Remediation Required)

| Dimension | Items |
|-----------|-------|
| Requirements | REQ-007 (input loading), REQ-015 (TER infrastructure), REQ-016 (TCC capacity_row), REQ-017 (user_state schema), REQ-020 (creative affinity reconciliation), REQ-023 (config_registry), REQ-024 (config_io), REQ-026 (per_user_seed), REQ-030 (historical dedup) |
| Architecture Decisions | ARCH-002 (composite PK in models), ARCH-009 (excel_utils openpyxl), ARCH-011 (no iterrows — VIOLATED by PV-001), ARCH-012 (dynamic creative affinity columns in excel_utils) |
| Business Rules Implemented | BIZ-004 (90-day window cutoff in input_loader), BIZ-019 (Campaign_ID default), BIZ-021/C-005 (historical dedup), BIZ-023/C-003 (iso_week_start in date_utils), SIM-019 (_per_user_seed via MD5), CFG-005 (schema version in config_io), R-CA-004 (reconcile_creative_affinity_columns in excel_utils) |
| Validation Rules Enabled | None directly (models + loaders only — validation in Phase 7) |
| Modules Delivered | models/ (10 files), utils/ (date_utils, schema_validator, excel_utils, config_io), core/ (input_loader, config_loader) |
| Critical Defects | MM-001–MM-006 (import errors, wrong fields), LM-001 (wrong required keys), TCC-001 (int() vs ceil()), PV-001 (dead iterrows() executes), MT-001–MT-003 (broken test helpers) |
| Remediation Items | BL-001, BL-008, BL-009, BL-010, BL-035, BL-036 |
| Status | COMPLETE — Remediation Required before Phase 3 |

---

### Phase 3 — User State Manager + Audience Manager (NOT STARTED)

| Dimension | Items |
|-----------|-------|
| Requirements | REQ-007 (trigger eligibility), REQ-008 (trigger priority), REQ-009 (segment priority), REQ-013 (cooling classification), REQ-014 (re-entry), REQ-016 (TCC remaining capacity), REQ-017 (state init and merge) |
| Architecture Decisions | ARCH-001 (single campaign_id filter), ARCH-002 (composite PK merge), ARCH-011 (vectorized eligibility classification — no iterrows), ARCH-013 (alphabetical Trigger_Name tiebreak — RESOLVED 2026-06-21), ARCH-014 (segment follows winning trigger row — RESOLVED 2026-06-21) |
| Business Rules to Implement | BIZ-003 (TCC only — separate from TER), C-002 (campaign ID filter), ARCH-013 (trigger tiebreak resolved — alphabetical Trigger_Name ASC), ARCH-014 (segment assignment resolved — follows winning trigger row) |
| Validation Rules Enabled | HR-002, HR-013 (cooling enforcement), HR-015 (Campaign_ID match), SR-007 (segment distribution), SR-008 (trigger distribution) |
| Modules to Deliver | core/user_state_manager.py, core/audience_manager.py |
| Blockers | ~~DD-013~~ RESOLVED 2026-06-21 → ARCH-013. ~~DD-014~~ RESOLVED 2026-06-21 → ARCH-014. Remaining blocker: Phase 2 remediation DoD (DEP-007). Architecture decisions unblocked. |
| Status | NOT STARTED — Architecture decisions UNBLOCKED (DD-013/DD-014 resolved). Pending Phase 2 remediation completion. |

---

### Phase 4 — Journey Engine (NOT STARTED)

| Dimension | Items |
|-----------|-------|
| Requirements | REQ-010 (multi-ad journey), REQ-011 (duration advance), REQ-012 (click advance), REQ-013 (cooling start on completion), REQ-014 (re-entry from Ad1) |
| Architecture Decisions | ARCH-003 (Stage 5 — Journey Building), ARCH-011 (vectorized schedule building) |
| Business Rules to Implement | BIZ-018 / C-001 (Move On Click exclusive — click-advance evaluated before duration), DD-012 (terminal journey event — Open Question) |
| Validation Rules Enabled | HR-001 (sequential journey stages) |
| Modules to Deliver | core/journey_engine.py |
| Status | NOT STARTED |

---

### Phase 5 — Behavior Engine + Timing Engine (NOT STARTED)

| Dimension | Items |
|-----------|-------|
| Requirements | REQ-018 (four behavior profiles), REQ-019 (channel affinity), REQ-020 (creative affinity updates), REQ-025 (composite scoring formula), REQ-026 (reproducibility via RNG seeding) |
| Architecture Decisions | ARCH-003 (Stage 6 — Engagement Scoring, Stage 7 — Behavior Processing, Stage 8 — Timing Assignment), ARCH-011 (vectorized scoring), ARCH-012 (dynamic creative affinity columns) |
| Business Rules to Implement | SIM-001 (composite score formula), SIM-002 (weights from ConfigRegistry — requires BL-010), SIM-019 (per-user RNG seed — already in input_loader), engagement score clamp I-006 (np.clip at every update), channel affinity boost/decay, creative affinity boost/decay |
| Validation Rules Enabled | SR-020 (Realism Score — informed by scoring output) |
| Modules to Deliver | core/behavior_engine.py, core/timing_engine.py |
| Blockers | BL-010 (missing scoring weight and frequency_max fields in ConfigRegistry) must be resolved first |
| Status | NOT STARTED |

---

### Phase 6 — Engagement Allocation Engine + Frequency/Fatigue Engine (NOT STARTED)

| Dimension | Items |
|-----------|-------|
| Requirements | REQ-016 (TCC capacity enforcement), REQ-025 (composite score drives allocation), REQ-028 (performance), REQ-029 (weekly fatigue enforcement) |
| Architecture Decisions | ARCH-003 (Stage 9 — Fatigue Enforcement), ARCH-011 (vectorized allocation and fatigue) |
| Business Rules to Implement | BIZ-023 / C-003 (weekly reset before processing), C-001 (Move On Click — interacts with allocation), RemainingCapacityRow enforcement (clamped ≥ 0) |
| Validation Rules Enabled | HR-009 (max daily impressions), HR-012 (max weekly engagements) |
| Modules to Deliver | core/allocation_engine.py, core/fatigue_engine.py |
| Status | NOT STARTED |

---

### Phase 7 — Validation Engine (NOT STARTED)

| Dimension | Items |
|-----------|-------|
| Requirements | REQ-015 (TER reporting — SR-005), REQ-016 (TCC reporting — SR-006), REQ-021 (15 hard rules), REQ-022 (20 soft rules) |
| Architecture Decisions | ARCH-003 (Stage 10 — Validation), ARCH-006 (self-registering rules), ARCH-010 (validation before export) |
| Business Rules to Implement | VAL-001 (hard FAIL blocks export), VAL-002 (soft WARNING never blocks), BIZ-003 (TER computed here for SR-005), all RuleConfig enable/disable flags |
| Validation Rules Implemented | All 35: HR-001–HR-015, SR-001–SR-020 |
| Modules to Deliver | core/validation_engine.py, rules/hard/ (15 files), rules/soft/ (20 files) |
| Open Question | OQ-014 (should validation rules be versioned independently of CONFIG_SCHEMA_VERSION?) |
| Status | NOT STARTED |

---

### Phase 8 — Excel Export Engine + Run Controller (NOT STARTED)

| Dimension | Items |
|-----------|-------|
| Requirements | REQ-027 (7 Excel workbooks), REQ-021 (ValidationReport always exported), REQ-026 (Run_Metadata in every workbook) |
| Architecture Decisions | ARCH-003 (Stage 11 — Export), ARCH-009 (openpyxl direct write — no pd.to_excel()), ARCH-010 (run_controller.py sole orchestrator), DD-008 (in-memory batch vs. streaming write — leaning toward batch) |
| Business Rules to Implement | VAL-001 (check ValidationResult.is_blocking() before each workbook), run_controller timing, all 11 stage invocations in sequence |
| Validation Rules Enabled | None new (validation completed in Phase 7; export checks results) |
| Modules to Deliver | core/export_engine.py, core/run_controller.py |
| Status | NOT STARTED |

---

### Phase 9 — Streamlit UI (NOT STARTED)

| Dimension | Items |
|-----------|-------|
| Requirements | REQ-003 (non-technical users), REQ-023 (Category A/B screens), REQ-024 (config save/load on Screen 3) |
| Architecture Decisions | ARCH-005 (app/ imports core/ and models/ only — zero business logic in app/), ARCH-010 (UI calls run_controller.run()) |
| Business Rules to Implement | Display of TER vs TCC distinction on Screen 7 (CHG-026), Category A/B/C parameter placement, scoring weight sliders deferred to V2 |
| Validation Rules Enabled | Screen 7 displays SR-005/SR-006 projections pre-run |
| Modules to Deliver | app/pages/ (9 pages), app/components/ (shared UI components) |
| Status | NOT STARTED |

---

### Phase 10 — Integration Testing + Sample Files (NOT STARTED)

| Dimension | Items |
|-----------|-------|
| Requirements | All REQs (end-to-end verification) |
| Architecture Decisions | ARCH-003 (all 11 stages exercised in sequence), ARCH-007 (pytest integration test suite) |
| Business Rules Verified | All BIZ-*, C-*, SIM-*, VAL-* rules verified via integration scenarios |
| Validation Rules Verified | All 35 rules exercised end-to-end with known input |
| Key Test Scenarios | Single-run campaign; two-run incremental (carry-forward state); all-cooling scenario; segment saturation; max-scale (50K users) benchmark |
| Modules Tested | All (full integration) |
| Status | NOT STARTED |

---

## 9. Gap Analysis

This section identifies traceability weaknesses: requirements without validation, requirements without implementation owners, architecture decisions without test coverage, and business rules without enforcement mechanisms.

---

### Gap Category 1: Requirements With No Validation Rule

These requirements have no validation rule guarding their correctness at runtime. If the implementation violates them, the engine will produce wrong output silently.

| REQ-ID | Requirement Summary | Gap Description | Risk Level | Recommended Action |
|--------|---------------------|-----------------|------------|-------------------|
| REQ-014 | User re-entry after cooling | No hard or soft rule verifies that users correctly transition from Re-Entry status to Active after appearing in a new trigger file following cooling | Medium | Add soft rule SR-NEW: "Users in Re-Entry status must progress to Active within one simulation day of being eligible." Consider as V2 addition. |
| REQ-019 | Channel affinity initialization for historical users | No validation rule checks that channel affinities were correctly initialized from historical data (vs. defaulted to 0.5 for all users regardless of history) | Medium | Add advisory note in SimulationReport (or SR-NEW) flagging when historical users show 0.5 affinity across all channels — may indicate initialization bypassed. |
| REQ-020 | Creative affinity schema reconciliation | R-CA-004 governs reconciliation but no validation rule checks that reconcile_creative_affinity_columns() was actually applied when prior state is loaded | Low | Add assertion in validation engine or Phase 3 state init that verifies all expected Creative_Affinity_{ad_name} columns are present and are float32. |
| REQ-024 | Config snapshot schema version enforcement | CFG-005 raises SchemaVersionError on mismatch — but this is exception-based, not a validation rule that appears in ValidationReport | Low | Add as an INFO entry in ValidationReport recording the schema version used for this run. Assists debugging if a version mismatch error is reported post-run. |
| REQ-026 | Reproducible output | No validation rule verifies reproducibility within a run. If hash() sneaks in despite the no-hash() constraint, output would differ silently | Medium | Add integration test in Phase 10 that runs the same config twice and compares EngagementEvents output byte-for-byte. |
| REQ-028 | Performance targets (1K/10K/50K user SLAs) | No validation rule or hard rule enforces performance. If a regression causes runtime to exceed SLA, the engine completes — just slowly | Low | CI benchmark test (BL-044/BL-005) is the enforcement mechanism. Mark explicit SLA thresholds in conftest.py performance fixtures. |
| REQ-029 | Weekly fatigue enforcement — ISO Monday reset | C-003 states reset before processing. If reset happens after processing, HR-009/HR-012 will catch violations in the same run, but not violations that occurred because the reset was skipped | Medium | Add a soft rule SR-NEW: "Weekly counter totals should not exceed configured caps at any measurement point in the run." Alternatively, add an assertion in fatigue_engine.py. |

---

### Gap Category 2: Requirements With No Implementation Owner (Phase Not Assigned)

| REQ-ID | Requirement Summary | Gap Description | Blocking? |
|--------|---------------------|-----------------|-----------|
| REQ-004 | Display channel (Impression + Click causal chain) | HR-003 and HR-004 enforce the rules, but the channel module itself (channels/display.py) has no detailed specification beyond "implements BaseChannel." No timing distribution spec for Display channel | No (Phase 5) |
| REQ-019 | Channel affinity initialization thresholds (0.2 / 0.5 / 0.8) | The thresholds are Category C (hardcoded) but no module is formally assigned as the owner of "when historical affinity is initialized" — this is a Phase 5 task implied by behavior_engine.py but not specified in the Phase 5 acceptance criteria in the handoff | No (Phase 5) |
| REQ-022 (SR-001–SR-004, SR-009–SR-019) | 14 of 20 soft rules | The specific names, evaluation logic, and implementation locations of SR-001–SR-004 and SR-009–SR-019 are not documented in any reviewed artifact. They appear in Validation_Rules_Catalog.md which was not in scope. No traceability to requirements can be established without this document | Yes (Phase 7 cannot begin without rule specifications) |

---

### Gap Category 3: Architecture Decisions With No Test Coverage

| Decision ID | Decision | Gap Description | Remediation |
|-------------|---------|-----------------|-------------|
| ARCH-005 | core/ never imports from app/ | The import hierarchy is enforced by future CI linting (BL-006), but no test currently catches a forbidden import. A developer can introduce a violation that goes undetected until CI is set up | BL-006 — Add to V1 pre-release scope |
| ARCH-009 | openpyxl direct write — no pd.to_excel() | No test currently asserts that export modules use openpyxl exclusively. A developer implementing Phase 8 could accidentally use pd.to_excel() without detection until the CI grep check | Add a unit test in Phase 8 that monkeypatches pd.to_excel() and asserts it is never called during export |
| ARCH-011 | No iterrows() in production code | PV-001 confirms a violation slipped through Phase 2 review. CI grep (BL-035) is the fix, but it is not yet in place. Between now and BL-035 resolution, no automated check catches future violations | Highest priority in BL-035 — before Phase 3 |
| ARCH-012 | Dynamic creative affinity columns (Option A) | reconcile_creative_affinity_columns() is implemented in excel_utils.py and tested in Phase 2. However, the case where a column exists in prior state but not in current config (keep, log WARNING) is listed as a test concern but no specific test case for this branch is confirmed in the Phase 2 test suite | Add explicit test for "extra column preserved with WARNING" branch |
| ARCH-013 | Alphabetical Trigger_Name tiebreak | Decision approved 2026-06-21. core/audience_manager.py not yet implemented. TC-AUD-001 through TC-AUD-007 specified but not yet written. No test currently validates tiebreak behavior. | Implement tests TC-AUD-001–TC-AUD-007 in Phase 3 before audience_manager.py is merged. |
| ARCH-014 | Segment follows winning trigger row | Decision approved 2026-06-21. core/audience_manager.py not yet implemented. TC-AUD-008 through TC-AUD-012 specified but not yet written. | Implement tests TC-AUD-008–TC-AUD-012 in Phase 3 before audience_manager.py is merged. |

---

### Gap Category 4: Business Rules With No Enforcement Mechanism

| Rule ID | Rule Name | Gap Description | Risk Level | Recommended Action |
|---------|-----------|-----------------|------------|-------------------|
| SIM-019 (no hash()) | Per-user seed via MD5 only | No runtime check prevents Python hash() from being used in a future module. The constraint is documented but not enforced by tests or linting | High | Add CI grep: `grep -r "hash(" engagement_data_generator/` excluding `hashlib` — already in BL-008 definition of done item 6 |
| SIM-002 (scoring weights sum to 1.0) | Five scoring weights must sum to 1.0 | ConfigRegistry fields for weights (pending BL-010) have no __post_init__ validator enforcing that the five weights sum to 1.0. If a user passes malformed JSON with weights summing to 0.7, the scoring formula produces systematically low composite scores | Medium | Add __post_init__ assertion: `assert abs(sum([w_eng, w_prof, w_cre, w_cha, w_rec]) - 1.0) < 0.001, "Scoring weights must sum to 1.0"` |
| R-CA-004 (affinity schema reconciliation) | Creative affinity columns must be float32 after reconciliation | reconcile_creative_affinity_columns() performs the reconciliation, but no enforcement prevents other code paths from loading prior state and skipping the reconciliation call | Medium | Validate in Phase 3 user_state_manager.py: assert all Creative_Affinity_* columns are float32 after state init |
| C-003 (weekly reset before processing) | ISO Monday reset must precede any allocation for the day | If fatigue_engine.py calls reset after allocation, HR-009/HR-012 would catch over-allocation within the same day only — they would not catch that the reset occurred in the wrong order | Medium | Add explicit ordering assertion in core/run_controller.py: within each simulation day, fatigue reset is the first call |
| BIZ-019 (Campaign_ID "Default") | Null Campaign_IDs filled with "Default" | The fill is applied in input_loader.py, but if a downstream module creates a new DataFrame row without going through input_loader, the composite PK could have a null Campaign_ID | Low | Add validation in Phase 7 HR-015 to explicitly check for null Campaign_IDs (not just mismatches) |
| CFG-005 (schema version) | SchemaVersionError on mismatch | The check is in config_io.py but not in all load paths. If config_loader.py is called directly without going through config_io, the version check is bypassed | Low | Confirm that load_config_from_dict() in config_loader.py also validates schema_version (it does per TCC-003 but the docstring error must be fixed) |

---

### Gap Category 5: Validation Rules With Incomplete Specifications

| Rule Range | Count | Gap | Impact on Phase 7 |
|-----------|-------|-----|-------------------|
| HR-010, HR-011, HR-014 | 3 | Hard rules in the 1–15 range with no names or logic specified in reviewed documents | Phase 7 cannot implement these rules without reading Validation_Rules_Catalog.md |
| SR-001–SR-004 | 4 | Soft rules with no names or logic in reviewed documents | Phase 7 blocked without Validation_Rules_Catalog.md |
| SR-009–SR-019 | 11 | Soft rules with no names or logic in reviewed documents | Phase 7 blocked without Validation_Rules_Catalog.md |
| **Total Unspecified** | **18 of 35** | Significant gap — nearly half the validation framework is untraced | Phase 7 implementation will require reading Validation_Rules_Catalog.md before writing a single rule |

---

### Gap Category 6: Open Decisions That Block Implementation Phases

| Open Item | Type | Blocks | Risk If Unresolved |
|-----------|------|--------|-------------------|
| ~~DD-013~~ (trigger tiebreak: identical priority) — **RESOLVED 2026-06-21** | Deferred Decision | ~~Phase 3 — Audience Manager~~ **UNBLOCKED** | RESOLVED — ARCH-013: alphabetical Trigger_Name ASC tiebreak. Unified sort chain: df.sort_values(['priority','Trigger_Name','Segment']).drop_duplicates(subset=['Campaign_ID','User_ID'],keep='first'). Test coverage: TC-AUD-001 through TC-AUD-007. See PROJECT_DECISIONS.md. |
| ~~DD-014~~ (segment tiebreak: same priority, different segments) — **RESOLVED 2026-06-21** | Deferred Decision | ~~Phase 3 — Audience Manager~~ **UNBLOCKED** | RESOLVED — ARCH-014: segment follows winning trigger's row (Option A). Alphabetical Segment sub-sort for pathological same-trigger duplicates. Test coverage: TC-AUD-008 through TC-AUD-012. See PROJECT_DECISIONS.md. |
| OQ-002 (terminal journey event in EngagementEvents?) | Open Question | Phase 4 — Journey Engine | Journey completion is recorded in UserState but output schema for EngagementEvents may be incomplete |
| OQ-003 (90-day cooling period compliance?) | Open Question | Phase 3 — Audience Manager | Legal risk if the default is non-compliant; affects cooling period field validation |
| ~~OQ-005~~ (identical trigger priority tiebreak) — **RESOLVED 2026-06-21** | Open Question | ~~Phase 3~~ **CLOSED** | RESOLVED — see ARCH-013 in PROJECT_DECISIONS.md. Duplicate of DD-013. |
| ~~OQ-011~~ (same-priority segment tiebreak) — **RESOLVED 2026-06-21** | Open Question | ~~Phase 3~~ **CLOSED** | RESOLVED — see ARCH-014 in PROJECT_DECISIONS.md. Duplicate of DD-014. |
| OQ-007 (legal constraints on synthetic HCP data) | Open Question | Pre-release | Potential compliance risk; affects UI disclaimers and data classification warnings |
| OQ-014 (should validation rules have independent versioning?) | Open Question | Phase 7 | Affects whether CONFIG_SCHEMA_VERSION must be bumped on rule changes |

---

### Gap Summary Table

| Gap Category | Gap Count | Blocking Phase 3? | Severity |
|-------------|-----------|-------------------|----------|
| Requirements with no validation rule | 7 | No | Medium |
| Requirements with no implementation owner | 3 | Yes (REQ-022 / 14 soft rules) | High |
| Architecture decisions with no test coverage | 4 | No | Medium |
| Business rules with no enforcement mechanism | 6 | No (discovered during review) | Medium |
| Validation rules with incomplete specifications | 18 | Yes (Phase 7) | High |
| Open decisions blocking implementation | 4 (was 8; DD-013, DD-014, OQ-005, OQ-011 RESOLVED 2026-06-21) | No — Phase 3 architecture decisions fully resolved | High (remaining 4 block Phase 4+) |
| **Total Gaps** | **42** (was 46; 4 resolved 2026-06-21) | — | — |

---

## 10. Recommendations

The following recommendations are ordered by urgency and impact. Items marked [CRITICAL] block Phase 3. Items marked [HIGH] should be resolved before Phase 4.

---

### ~~REC-001~~ [RESOLVED 2026-06-21] — ~~Resolve DD-013 and DD-014 Before Phase 3 Begins~~ DD-013 and DD-014 RESOLVED

**Resolution:** DD-013 resolved as ARCH-013 (alphabetical Trigger_Name ASC tiebreak). DD-014 resolved as ARCH-014 (segment follows winning trigger's row). Both recorded in PROJECT_DECISIONS.md version 1.1. This matrix's Section 8 Phase 3 row updated accordingly. Phase 3 is architecturally unblocked.

**Remaining action:** Phase 2 remediation DoD must be achieved before Phase 3 kick-off. See DEP-007 in PROJECT_MASTER_REGISTER.md.

**Timeline:** COMPLETE.

---

### REC-002 [CRITICAL] — Complete All Phase 2 Remediation Before Phase 3

**Gap:** Six critical defects (MM-001 through MM-006) cause ImportError or TypeError before any Phase 3 module can be tested. TCC-001 causes silent data undercount. PV-001 violates ARCH-011 at runtime.

**Recommendation:** Execute the PHASE_2_REMEDIATION_PLAN.md remediation in dependency order (Groups A through F). Do not proceed to Phase 3 until all 10 Definition of Done criteria in PHASE_2_REMEDIATION_PLAN.md Section 8 are satisfied.

**Timeline:** Immediately — no other work should begin until this is complete.

---

### REC-003 [CRITICAL] — Read Validation_Rules_Catalog.md Before Phase 7 Planning

**Gap:** 18 of 35 validation rules (HR-010, HR-011, HR-014, SR-001–SR-004, SR-009–SR-019) have no specification in reviewed documents. Phase 7 cannot begin without their definitions.

**Recommendation:** Read `uploads/Validation_Rules_Catalog.md` before Phase 7 planning. Update this traceability matrix Sections 6 and 9 with the complete rule specifications. Determine which requirements each unspecified rule protects and which business rules it enforces.

**Timeline:** Before Phase 7 kick-off (can be done in parallel with Phases 3–6).

---

### REC-004 [HIGH] — Add __post_init__ Validator for Scoring Weights Sum

**Gap:** ConfigRegistry (after BL-010 adds scoring weight fields) has no enforcement that the five weights sum to 1.0. A misconfigured JSON snapshot with non-unit-sum weights silently corrupts all composite scoring output.

**Recommendation:** When implementing BL-010, add to ConfigRegistry.__post_init__:
```python
weight_sum = sum([w_engagement, w_profile, w_creative, w_channel, w_recency])
if abs(weight_sum - 1.0) > 0.001:
    raise ConfigError(f"Scoring weights must sum to 1.0; got {weight_sum:.4f}")
```
This should be added alongside BL-010 (pre-Phase-5).

**Timeline:** During BL-010 resolution.

---

### REC-005 [HIGH] — Add CI grep Checks Before Phase 3

**Gap:** ARCH-011 (no iterrows()), ARCH-009 (no pd.to_excel()), and SIM-019 (no hash()) are enforced by policy and code review only. PV-001 shows that iterrows() slipped through in Phase 2. CI enforcement must exist before Phase 3 introduces more production code.

**Recommendation:** Add three grep-based CI checks to pyproject.toml or a pre-commit hook:
1. `grep -r "iterrows()" engagement_data_generator/ --include="*.py"` → fail if found in non-test code
2. `grep -r "pd\.to_excel" engagement_data_generator/ --include="*.py"` → fail if found in any production export path
3. `grep -rP "\bhash\(" engagement_data_generator/ --include="*.py" | grep -v hashlib` → fail if found

**Timeline:** Before Phase 3 begins (BL-006 prerequisite).

---

### REC-006 [HIGH] — Resolve OQ-003 (Cooling Period Compliance) Before Phase 3

**Gap:** The 90-day cooling period default is unvalidated against pharma marketing regulations. If legal review determines a different minimum is required, Phase 3 Audience Manager eligibility classification must be redesigned.

**Recommendation:** Initiate legal/medical affairs review of the cooling period before Phase 3 audience_manager.py is implemented. Record the outcome in PROJECT_DECISIONS.md. If compliance requires a longer minimum, update ConfigRegistry defaults and the Phase 3 acceptance criteria.

**Timeline:** Parallel with Phase 2 remediation.

---

### REC-007 [HIGH] — Formally Specify HR-010, HR-011, HR-014 Before Phase 7

**Gap:** Three hard rules in the HR-001 through HR-015 range have no names or logic in reviewed documents. If these are placeholders, they should be removed from the count. If they are real rules, they must be specified before implementation.

**Recommendation:** Review Validation_Rules_Catalog.md to confirm whether HR-010, HR-011, and HR-014 are named rules or placeholders. If they are real rules, add their full specifications to this matrix. If they are placeholders, update the hard rule count from 15 to 12, update the validation framework documentation, and update all statements that reference "15 hard rules." Record the outcome in PROJECT_DECISIONS.md.

**Timeline:** Before Phase 7 planning.

---

### REC-008 [MEDIUM] — Add Validation Rule for Creative Affinity Reconciliation

**Gap:** R-CA-004 (schema reconciliation) is enforced procedurally in excel_utils.py but no validation rule confirms reconciliation occurred correctly. A prior state file with columns of wrong dtype could silently pass through.

**Recommendation:** In Phase 7 or Phase 3, add a schema integrity assertion that after user_state_manager.initialize() all Creative_Affinity_* columns are dtype float32. Raise InputValidationError if any column is float64 or object. This can be an advisory rule (SR-NEW / INFO severity) or an internal assertion rather than a full hard rule.

**Timeline:** Phase 3 (state initialization) or Phase 7 (validation engine).

---

### REC-009 [MEDIUM] — Expand BL-011 Scope to Include Machine-Readable Rule Catalog

**Gap:** DEF-008 defers a standalone Validation_Rules_Catalog.md to V1.1. However, 18 of 35 rules are already untraced in this matrix. If the catalog remains human-readable Markdown only (DD-010 Option A), it cannot be used to auto-generate rule documentation or validate completeness.

**Recommendation:** Resolve DD-010 (machine-readable vs. Markdown) before Phase 7. If JSON schema (Option B) is chosen, the catalog can be used to auto-generate rule IDs, verify that exactly 35 rules are registered, and ensure every rule has a requirement ID and business rule reference. This directly closes the 18 unspecified rules gap.

**Timeline:** Before Phase 7.

---

### REC-010 [MEDIUM] — Update This Document After Every Phase Completion

**Gap:** This traceability matrix currently shows many cells as "Not Started." As phases are completed, implementation statuses must be updated to maintain traceability accuracy. Without updates, the matrix becomes stale and loses governance value.

**Recommendation:** Add "Update TRACEABILITY_MATRIX.md" as a mandatory item in the Definition of Done for every phase (Phases 3–10). Specifically:
- Update Section 3 (Requirement Traceability): change relevant Status cells from "Not Started" to "Implemented"
- Update Section 8 (Phase Traceability): mark the phase as COMPLETE
- Update Section 9 (Gap Analysis): close resolved gaps
- Increment the Document Version in Section 1

**Timeline:** After each phase completion.

---

### REC-011 [LOW] — Create REQ-IDs in Requirements_v1.md

**Gap:** The 30 requirement IDs (REQ-001 through REQ-030) used in this matrix were derived by this document and do not exist in Requirements_v1.md itself. Future developers may not recognize these IDs without the mapping.

**Recommendation:** In the next version of Requirements_v1.md (or in an addendum), add the REQ-ID column to each requirement section so that the IDs are normative. Alternatively, publish the mapping table in Section 3 of this document as the official authoritative mapping.

**Timeline:** V1.1 governance cleanup.

---

### REC-012 [LOW] — Confirm OQ-007 (Legal) Before V1 Release

**Gap:** OQ-007 asks whether there are legal or regulatory constraints on synthetic HCP engagement data generation. This is P0 per the backlog but remains Open.

**Recommendation:** Initiate legal review no later than Phase 6 completion so that findings can be incorporated into the UI (Assumption A-011 already notes a data classification warning should be added). If the legal review identifies constraints, they must be recorded in PROJECT_DECISIONS.md and may require changes to Validation rules (e.g., a mandatory disclaimer rule) or the configuration strategy (e.g., a HIPAA mode).

**Timeline:** Before Phase 9 (UI) design begins.

---

*TRACEABILITY_MATRIX.md — Version 1.0*
*Engagement Data Generator v1.0*
*Chief Architect and Product Governance Lead — 2026-06-21*
*Baseline: Requirements_v1.md (2025-12-01)*
*This document must be updated after each phase completion. Witho