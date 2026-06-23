# PROJECT BACKLOG
# Engagement Data Generator — Version 1.0
# Formal Backlog Register — All Items, All Phases, All Horizons

**Document Version:** 1.0
**Prepared:** 2026-06-21
**Role:** Chief Architect / Program Manager / Governance Owner
**Status:** ACTIVE — Updated at every phase gate per RELEASE_GATES.md
**Authority:** PROJECT_DECISIONS.md governs all conflicts. RELEASE_GATES.md governs phase entry and exit criteria.

**Sources Reviewed for This Register:**
- PROJECT_MASTER_REGISTER.md — backlog register, risk register, governance gaps, architecture gaps, validation gaps, compliance register, technical debt register, open decisions, open questions
- PHASE_2_EXECUTION_PLAN.md — remediation-derived backlog, CI recommendations, coverage recommendations
- PHASE_3_ARCHITECTURE_DECISIONS.md — DD-013/DD-014 resolution, V2 extensibility items, reserved fields
- RELEASE_GATES.md — gate-derived backlog items, phase-specific test requirements, compliance gates

**ID Assignment:**
- BL-001 through BL-061: Items carried forward from PROJECT_MASTER_REGISTER.md Section 14
- BL-062 through BL-090: New items identified from review of the four source documents above
- BL-091 through BL-093: Added 2026-06-22 — Wave 1 pre-implementation governance review (WAVE_1_PRE_IMPLEMENTATION_BACKLOG_UPDATE.md)
- All items assigned exactly once; IDs never reused

**Backlog Rules:**
- Every item that does not have a Phase 2 target must not block Phase 2 remediation
- Every V1-tagged item must be CLOSED before GATE-V1 passes
- No item may be silently dropped; deferred items must have a documented reason and target release
- Backlog is reviewed at every phase gate (start and end)

---

## Table of Contents

1. Open Backlog Items
2. Deferred Items
3. Technical Debt Register
4. Future Enhancements
5. Governance Enhancements
6. CI/CD Enhancements
7. Backlog Review Process

---

## 1. Open Backlog Items

Open items are active work that must complete within V1. Sorted by priority then target phase.

| BL-ID | Title | Description | Priority | Category | Source Document | Owner | Target Phase | Status | Dependencies |
|-------|-------|-------------|----------|----------|-----------------|-------|-------------|--------|-------------|
| BL-001 | Resolve Phase 2 Critical Import and Type Errors | Fix all 6 critical defects (MM-001 through MM-006) causing ImportError and TypeError at module load. All Phase 2 tests are blocked until these are resolved. Covered by REM-001 through REM-008. | P0 | Defect Remediation | PROJECT_MASTER_REGISTER.md §7, PHASE_2_EXECUTION_PLAN.md | Lead Engineer | Phase 2 | **FULLY RESOLVED — 2026-06-22. All 13 critical/high defects resolved (REM-001–013). 204/204 tests pass. 90.13% coverage. Phase 2 DoD 10/10 met.** | None — must be first |
| BL-008 | Fix ceil() in RemainingCapacityRow.compute() (TCC-001) | TCC formula requires math.ceil(). Current int() causes systematic under-generation of engagement events. 101 users × 10% must yield 11, not 10. Covered by REM-003. | P0 | Defect Remediation | PROJECT_MASTER_REGISTER.md §7.3, PHASE_2_EXECUTION_PLAN.md §REM-003 | Lead Engineer | Phase 2 | **RESOLVED — 2026-06-22 (REM-003)** | BL-001 (imports must work first) |
| BL-009 | Fix Phase 2 Test Suite (MT-001 through MT-012) | Fix three critical test helpers (make_state, make_registry TriggerConfig, make_registry ConfigRegistry field names). Add 8 missing test functions. Create test_trigger_config.py and test_segment_config.py from scratch. Covered by REM-010 through REM-013. | P0 | Test Coverage | PROJECT_MASTER_REGISTER.md §7.5, PHASE_2_EXECUTION_PLAN.md §Wave 5 | Lead Engineer | Phase 2 | **RESOLVED — 2026-06-22 (REM-010–013). All 12 MT defects resolved. 6 new test files. 204/204 tests pass.** | BL-001, BL-008, BL-010 |
| BL-035 | Delete Dead iterrows() Code (PV-001) | The 5-line mask=[...iterrows()...] block in load_historical_file() executes at runtime, violating ARCH-011. Delete entirely. Retain only the apply() path. Add PV-002 comment above apply(). Covered by REM-009. | P0 | Performance | PROJECT_MASTER_REGISTER.md §7.4, PHASE_2_EXECUTION_PLAN.md §REM-009 | Lead Engineer | Phase 2 | **RESOLVED — 2026-06-22 (REM-009). core/input_loader.py created without iterrows block. Zero grep hits in production code.** | BL-001 |
| BL-003 | Integration Tests and End-to-End Verification | Full pipeline integration test suite (Phase 10). Three required runs: clean single-trigger, multi-trigger with tiebreaks, historical data present. Reproducibility test (two runs, identical inputs, identical numeric output). Performance benchmark at scale. | P0 | Testing | PROJECT_MASTER_REGISTER.md §14, RELEASE_GATES.md §10 | Lead Engineer | Phase 10 | Not Started | All Phases 2–9 complete |
| BL-010 | Add Missing ConfigRegistry Fields (Scoring Weights + frequency_max) | Add scoring_weight_engagement (0.30), scoring_weight_profile (0.25), scoring_weight_creative (0.15), scoring_weight_channel (0.15), scoring_weight_recency (0.15), frequency_max (30). Add __post_init__ weight-sum validator. Add named constants to utils/constants.py. Covered by REM-004. | P1 | Model Correctness | PROJECT_MASTER_REGISTER.md §7.1 MM-007/MM-008, PHASE_2_EXECUTION_PLAN.md §REM-004 | Lead Engineer | Phase 2 | **FULLY RESOLVED — 2026-06-22. Fields + validator + constants (REM-004). config_loader.py parsing complete (REM-005–REM-008). 84/84 Wave 3 tests pass.** | BL-001 |
| BL-002 | Complete Phases 3 Through 10 Implementation | Implement all remaining pipeline stages per Implementation_Plan.md. Each phase has explicit acceptance criteria. No phase may begin until its predecessor's RELEASE_GATE passes. | P0 | Implementation | PROJECT_MASTER_REGISTER.md §14, RELEASE_GATES.md | Lead Engineer + Architect | Phases 3–10 | Not Started | GATE-P2 |
| BL-004 | Sample Input Files for Home Screen Downloads | Produce minimal valid trigger file, historical file, and config JSON that a first-time user can download from Screen 1 and run immediately. Required for onboarding UX. | P1 | UX | PROJECT_MASTER_REGISTER.md §14 | Lead Engineer | Phase 9 | Not Started | Phase 8 complete |
| BL-005 | Performance Validation at 1K / 10K / 50K User Scale | Benchmark the full pipeline at three scale points. Results feed DD-005 (background thread decision) and DD-008 (streaming write decision). Must complete before Phase 9 UI design. | P1 | Performance | PROJECT_MASTER_REGISTER.md §14, RELEASE_GATES.md §5.4 | Lead Engineer | Phase 10 | Not Started | Phase 5 complete |
| BL-006 | CI Import Linting for ARCH-005 Enforcement | Add automated import linting (pylint or custom script) that fails if core/ imports from app/, or utils/ imports from core/ or app/. Must run in pre-commit and CI. Closes GG-002 and AG-001. Mitigated by MT-012 regression test pending CI implementation. | P1 | CI/CD — **Phase 3 Infrastructure** | PROJECT_MASTER_REGISTER.md §9 GG-002, PHASE_2_EXECUTION_PLAN.md §9 | Lead Engineer | **Phase 3 — Infrastructure work stream** | **Formally assigned 2026-06-22 (Wave 6). Target: Phase 3 kick-off sprint.** | Phase 2 gate (EX-P2-007) |
| BL-007 | CI Coverage Gate (≥90% for Core Modules) | Add pytest-cov --fail-under=90 to pyproject.toml and CI pipeline for models/, core/, utils/. Closes GG-003. Currently verified manually at each gate review. | P1 | CI/CD — **Phase 3 Infrastructure** | PROJECT_MASTER_REGISTER.md §9 GG-003, RELEASE_GATES.md §2.3 | Lead Engineer | **Phase 3 — Infrastructure work stream** | **Formally assigned 2026-06-22 (Wave 6). Target: Phase 3 kick-off sprint.** | Phase 2 gate (EX-P2-007) |
| BL-NEW-001 | Create tests/test_utils/test_schema_validator.py | Standalone test file for utils/schema_validator.py. Required by GATE-P2 §2.2 (accepted as EX-P2-001). Must cover all QUALIFYING_ACTIONS channel/action combinations, is_qualifying_action() unknown channel/action/Sent/Impression, compute_error_threshold() all three tiers, validate_required_columns(), validate_no_null_primary_keys(). | P1 | Test Coverage | PHASE_2_GATE_REVIEW.md EX-P2-001 | Lead Engineer | Phase 2 Wave 6 | **RESOLVED — 2026-06-22 (Wave 6). 73 tests created and passing.** | EX-P2-001 |
| BL-NEW-002 | Audit PROJECT_CHANGE_LOG.md CHG-028–CHG-035 | Update status of CHG-028 through CHG-035 from Pending to APPROVED with implementation dates and wave references. Add CHG-036 for Wave 6 documentation pass. | P2 | Governance | PHASE_2_GATE_REVIEW.md EX-P2-006 | Lead Engineer | Phase 2 Wave 6 | **RESOLVED — 2026-06-22 (Wave 6). All 8 entries updated to APPROVED. CHG-036 added.** | EX-P2-006 |
| BL-040 | Consolidate Scoring Weight Constants in utils/constants.py | Replace inline float literals (0.30, 0.25, 0.15 etc.) in ConfigRegistry field defaults with named constants (DEFAULT_WEIGHT_ENGAGEMENT etc.) in utils/constants.py. Prevents magic numbers from drifting across phases. | P2 | Code Quality | PROJECT_MASTER_REGISTER.md §13 TD-018, PHASE_2_EXECUTION_PLAN.md §REM-004 | Lead Engineer | Phase 2 | **RESOLVED — 2026-06-22 (REM-004)** | BL-010 |
| BL-041 | Remove Unused os Import from config_io.py | Unused import triggers F401 in any linting run. Remove on the next touch of the file. | P3 | Code Quality | PROJECT_MASTER_REGISTER.md §13 TD-017 | Lead Engineer | Phase 2 (next touch) | Open | None |
| BL-062 | Add strict_priority_validation Reserved Field to ConfigRegistry | Add bool field strict_priority_validation (default False) to ConfigRegistry per CFG-NEW-001. In V1 it is a no-op. When True in a future release it raises ValidationError instead of applying alphabetical tiebreak (ARCH-013). Prevents field name from being claimed by other features. | P2 | Model / V2 Readiness | PHASE_3_ARCHITECTURE_DECISIONS.md §6, §8 CFG-NEW-001 | Lead Engineer | Phase 3 | Open | BL-001 (ConfigRegistry fixed) |
| BL-071 | Initiate OQ-007 Legal Review (Synthetic HCP Data) | Commission and complete a legal review of whether generating synthetic data resembling HCP engagement records creates HIPAA, GDPR, EU MDR, FDA 21 CFR Part 11, or state privacy law obligations. Required before Phase 9 UI design. Hard gate for GATE-V1. | P0 | Compliance | PROJECT_MASTER_REGISTER.md §12 COMP-001, RELEASE_GATES.md §11.1 | Program Manager + Legal | Before Phase 9 | Not Started | None — start immediately |
| BL-072 | Complete OQ-003 Cooling Period Compliance Review | Obtain written position from Legal/Medical Affairs on whether the 90-day default cooling period aligns with pharma marketing compliance norms (FDA/PhRMA/EFPIA). Hard gate for GATE-P3. If minimum required period differs, update ConfigRegistry default and Phase 3 acceptance criteria. | P0 | Compliance | PROJECT_MASTER_REGISTER.md §12 COMP-002, RELEASE_GATES.md §3.4 | Program Manager + Legal | Before Phase 3 | Not Started | None — start immediately |
| BL-073 | Add UI Data Classification Warning for Screen 1 / Screen 2 | Add a prominently displayed disclaimer that the tool is designed for synthetic data generation only and must not be run against real patient or HCP identifiers. Text reviewed by Legal before Phase 9 UI implementation. Required per COMP-003. | P1 | Compliance / UX | PROJECT_MASTER_REGISTER.md §12 COMP-003 | Lead Engineer + Legal | Phase 9 | Not Started | BL-071 (legal text review) |
| BL-074 | Confirm Week Start Convention with Stakeholders (COMP-004) | The weekly reset boundary uses Monday-start (ISO). US pharma marketing uses Sunday-start. Confirm target market convention before Phase 6 timing engine is implemented. If Sunday-start required, add week_start_day field to ConfigRegistry Category B. | P1 | Compliance / Architecture | PROJECT_MASTER_REGISTER.md §12 COMP-004 | Architect + Product Owner | Before Phase 6 | Not Started | None |
| BL-075 | Pin Python Version Requirement in pyproject.toml | Add python_requires = ">=3.11" to pyproject.toml. Update README with clear installation prerequisite. Prevents silent failures on Python 3.9/3.10. | P2 | Packaging | PROJECT_MASTER_REGISTER.md §12 COMP-005 | Lead Engineer | Phase 2 (next pyproject.toml touch) | Open | None |
| BL-076 | Assert float32 Dtype for Creative Affinity Columns After State Init | Add assertion in user_state_manager.py (Phase 3) or as a Phase 7 advisory validation rule: all Creative_Affinity_* columns must be dtype float32 after reconcile_creative_affinity_columns() runs. Closes AG-004 and VG-011. | P2 | Architecture Enforcement | PROJECT_MASTER_REGISTER.md §10 AG-004, §11 VG-011 | Lead Engineer | Phase 3 | Not Started | Phase 3 |
| BL-077 | Add Engagement Score Clamp Assertion in Integration Test | Phase 10 integration test must assert no engagement_score values outside [0.0, 1.0] in UserState output across any run. Closes AG-005 and VG-008. Documents that callers (Behavior Engine) are responsible for clamping via np.clip(). | P2 | Architecture Enforcement | PROJECT_MASTER_REGISTER.md §10 AG-005, PHASE_2_EXECUTION_PLAN.md §REM-013 MT-011 | Lead Engineer | Phase 10 | Not Started | Phase 5 complete |
| BL-078 | Add Re-Entry Transition Validation Rule (VG-006) | No hard or soft rule currently verifies that users correctly transition from Re-Entry to Active status. Add a soft rule: users in Re-Entry on simulation day D who appear in a new trigger file must be reclassified Active within one day. | P2 | Validation | PROJECT_MASTER_REGISTER.md §11 VG-006 | Architect | Phase 7 | Not Started | Phase 3 complete |
| BL-079 | Add Channel Affinity Initialization Validation Rule (VG-007) | No rule detects when all historical users show 0.5 affinity across all channels, which may indicate initialization bypass. Add advisory SimulationReport note or SR-NEW soft rule. | P2 | Validation | PROJECT_MASTER_REGISTER.md §11 VG-007 | Architect | Phase 7 | Not Started | Phase 5 complete |
| BL-080 | Read Validation_Rules_Catalog.md Before Phase 7 Begins | All 35 rule specifications must be extracted from Validation_Rules_Catalog.md before Phase 7 coding begins. This is CB-008. Closes VG-001 through VG-005 (18 unspecified validation rules). Hard gate per RELEASE_GATES.md §7.1. | P0 | Governance / Validation | PROJECT_MASTER_REGISTER.md §4 CB-008, RELEASE_GATES.md §7.1 | Architect | Before Phase 7 | Not Started | None — read before Phase 7 kick-off |
| BL-081 | Add Performance SLA Validation in Test Suite (VG-009) | Add CI benchmark tests with explicit SLA thresholds. 1K users: < X seconds. 10K users: < Y seconds. 50K users: < Z seconds. Thresholds set from OQ-001 resolution. Fails CI if engine regresses below SLA. | P2 | Performance / Validation | PROJECT_MASTER_REGISTER.md §11 VG-009, RELEASE_GATES.md §10.2 | Lead Engineer | Phase 10 | Not Started | BL-005 (benchmarks done first) |
| BL-082 | Add Weekly Reset Ordering Assertion (VG-010) | Add assertion in run_controller.py or Phase 6 timing engine: fatigue reset is the first call within each simulation day's loop. Prevents reset-after-processing ordering bug. Alternatively: soft rule in Phase 7. | P2 | Architecture Enforcement / Validation | PROJECT_MASTER_REGISTER.md §11 VG-010 | Lead Engineer | Phase 6 | Not Started | Phase 6 |
| BL-083 | Resolve OQ-001 (Max Trigger File Size / Run-Time SLA) | Conduct informal benchmark run and record results. Define V1 max supported trigger file size (rows) and associated run-time SLA. Record resolution in PROJECT_DECISIONS.md. Required reviewed by GATE-P5. | P1 | Performance / Governance | PROJECT_MASTER_REGISTER.md §6 OQ-001, RELEASE_GATES.md §5.4 | Lead Engineer + Architect | Phase 5 | Not Started | Phase 5 complete |
| BL-084 | Resolve DD-012 (Terminal Journey Event) Before Phase 4 | Decide whether journey completion generates a terminal EngagementEvent record. Options: (A) No terminal event; (B) "Journey_Completed" action; (C) Flag in UserState only. Must be recorded in PROJECT_DECISIONS.md before Phase 4 begins. Hard gate per GATE-P3. | P0 | Architecture Decision | PROJECT_MASTER_REGISTER.md §5 DD-012, RELEASE_GATES.md §3.6 | Architect + Product Owner | Before Phase 4 | Open | Phase 3 implementation |
| BL-085 | Resolve DD-008 (In-Memory Batch vs. Streaming openpyxl Write) | Decide export write strategy before Phase 8 implementation. Inform decision with Phase 5/6 performance benchmark (BL-005). Hard gate per GATE-P8. | P1 | Architecture Decision | PROJECT_MASTER_REGISTER.md §5 DD-008, RELEASE_GATES.md §8.6 | Architect + Lead Engineer | Before Phase 8 | Open | BL-005 |
| BL-086 | Resolve OQ-008 (Dry-Run / Validate-Only Mode) | Decide whether to implement a dry-run flag that runs validation without generating output files. Hard gate per GATE-P9. If yes, implement and test in Phase 9. If no, document rationale and confirm no dry-run parameter exists on run(). | P2 | Product Decision | RELEASE_GATES.md §9.6 OQ-008 | Product Owner | Before Phase 9 | Open | Phase 8 |
| BL-087 | Resolve OQ-010 (Compressed Trigger File Support for V1) | Decide whether V1 input_loader.py supports gzip CSV trigger and historical files. If yes, implement in Phase 2 remediation or Phase 3. If no, create BL item for V2. Hard gate per GATE-P9. | P2 | Feature Decision | RELEASE_GATES.md §9.6 OQ-010 | Architect + Lead Engineer | Before Phase 9 | Open | None |
| BL-088 | Add TRACEABILITY_MATRIX.md Update Gate to Every Phase DoD | Add "Update TRACEABILITY_MATRIX.md" as an explicit criterion to the Definition of Done for every phase (Phases 3–10). Prevents matrix from becoming stale. Closes GG-004. | P1 | Governance | PROJECT_MASTER_REGISTER.md §9 GG-004, RELEASE_GATES.md §all | Program Manager | Phase 3 | Open | None |
| BL-089 | Add PROJECT_MASTER_REGISTER.md Update Gate to Every Phase DoD | Add "Update PROJECT_MASTER_REGISTER.md" as an explicit criterion to the Definition of Done for every phase (Phases 3–10). Prevents register from becoming stale. Closes GG-005. | P1 | Governance | PROJECT_MASTER_REGISTER.md §9 GG-005 | Program Manager | Phase 3 | Open | None |
| BL-090 | Assign Resolution Deadlines to All Open Questions (OQ-001 to OQ-014) | Each OQ must be assigned a resolution-by date corresponding to its first-blocking phase. OQ-003 and OQ-007 deadlines are before Phase 3 and Phase 9 respectively. Closes GG-012. | P1 | Governance | PROJECT_MASTER_REGISTER.md §9 GG-012 | Program Manager | Immediately | Open | None |
| BL-091 | Historical Window Validation Testing | Verify AudienceManager.compute_remaining_capacity() correctly filters historical_df by each supported window (30-day, 60-day, 90-day, All Time) before counting historical_engaged_users. Expected test: test_compute_remaining_capacity_respects_historical_window. A passing Wave 1 null-history unit test does NOT cover this scenario. See BRC-009. | P1 | Test Coverage | WAVE_1_PRE_IMPLEMENTATION_BACKLOG_UPDATE.md | Lead Engineer | Phase 5 or 6 | Open | Phase 3 Wave 1 (compute_remaining_capacity implemented) |
| BL-092 | Trigger Engagement Formula Validation | Verify Trigger Engagement Rate = (Distinct Engaged Users / Distinct Triggered Users) × 100 per trigger matches business definition end-to-end. Numerator = distinct users with qualifying engagement events. Denominator = distinct users in trigger_df for this trigger (all triggered, not just winners). Division by zero → TER = 0.0. Expected test: test_trigger_engagement_rate_calculation_matches_business_definition. See BRC-010. | P1 | Test Coverage / Business Rule | WAVE_1_PRE_IMPLEMENTATION_BACKLOG_UPDATE.md | Lead Engineer + Architect | Phase 6 | Open | Phase 3 Wave 1, Phase 5 (BehaviorEngine), Phase 6 (SimulationReport) |
| BL-093 | Multi-Run Simulation Stability Validation | Run 12 consecutive weekly simulation passes and verify: run_count correctness, trigger_history pipe-delimited correctness, cooling period correctness, fatigue/weekly counter reset correctness, no duplicate user states per run, state persistence (no cross-stage field overwrite), historical_engaged carry-forward correctness. Expected test suite: test_multi_run_simulation_stability (7 test functions). See BRC-011. | P1 | Test Coverage / End-to-End | WAVE_1_PRE_IMPLEMENTATION_BACKLOG_UPDATE.md | Lead Engineer | Phase 10 | Open | All Phases 3–9 complete |

**Open Backlog Total: 39 items. P0: 8. P1: 16. P2: 13. P3: 2.**
*(Added 2026-06-22: BL-091, BL-092, BL-093 — Wave 1 pre-implementation review)*

---

## 2. Deferred Items

Deferred items are out of V1 scope. Each has a documented target release and deferral rationale. No deferred item may re-enter the V1 backlog without a documented change request approved by the Chief Architect.

### V1.1 — Post-Release Enhancements

| BL-ID | Title | Deferral Rationale | Target Release | Priority | Dependencies |
|-------|-------|--------------------|----------------|----------|-------------|
| BL-011 | Standalone Validation_Rules_Catalog.md (machine-readable) | DD-010 not yet resolved. Markdown format sufficient for V1. JSON schema adds value for V2 automation. | V1.1 | P2 | DD-010 resolved |
| BL-012 | CSV Export Option for EngagementEvents | V1 scope is Excel only (ARCH-009). CSV adds negligible risk but is not required for initial users. | V1.1 | P2 | Phase 8 complete |
| BL-013 | Run History Tracking (local run log) | No user story in V1 requirements. Useful for power users. Low implementation cost post-V1. | V1.1 | P2 | Phase 9 complete |
| BL-014 | Additional Sample Files by Scenario | One set of sample files sufficient for V1. Scenario library is a nice-to-have. | V1.1 | P3 | BL-004 complete |
| BL-015 | Engagement Score Trend Chart in SimulationReport | No chart in V1 SimulationReport. Useful visualization post-release. | V1.1 | P3 | Phase 8 complete |
| BL-016 | Config Save/Load UX Improvement (Screen 3) | V1 allows manual JSON editing. Improved UX deferred to gather user feedback first. | V1.1 | P2 | Phase 9 complete |
| BL-017 | Dry Run / Validate-Only Mode | Pending OQ-008 decision. If resolved as V1.1, implement here. | V1.1 | P2 | BL-086 resolved as V1.1 |
| BL-036 | Document All Unavoidable apply() Calls | Minor documentation quality item. Comment added in Phase 2 remediation (PV-002). Full audit deferred. | V1.1 | P2 | Phase 2 remediation |
| BL-037 | Add mypy Type-Check Configuration | Adds type safety but not critical for V1 correctness. Low impact on users. | V1.1 | P3 | Phase 10 complete |
| BL-038 | Enforce __all__ Completeness in CI | Automation for a low-risk quality check. Manual review sufficient for V1. | V1.1 | P3 | Phase 10 complete |

### V2 — Major Enhancements

| BL-ID | Title | Deferral Rationale | Target Release | Priority | Key Dependencies |
|-------|-------|--------------------|----------------|----------|-----------------|
| BL-018 | Multi-Campaign Per Run (DEF-001) | DD-002 deferred. ARCH-001 (single campaign) is a V1 design constraint. Composite PK (ARCH-002) enables V2 upgrade without schema changes. | V2 | P1 | DD-002 resolved; ARCH-002 in place |
| BL-019 | Configurable Qualifying Actions (DEF-003) | DD-001 deferred. QUALIFYING_ACTIONS is Category C (system constant) in V1 per BIZ-011. V2 may promote to Category B. | V2 | P2 | DD-001 resolved |
| BL-020 | Historical Affinity Thresholds as Category B (DEF-005) | Fixed thresholds (0.2/0.5/0.8) sufficient for V1. DD-009 deferred. | V2 | P3 | DD-009 resolved |
| BL-021 | Timezone Configuration (DEF-006) | ISO Monday-start assumption confirmed for V1 per BL-074. Timezone and week-start configurability deferred to V2. | V2 | P2 | BL-074 resolved; COMP-004 cleared |
| BL-022 | RNG State Snapshot Per Stage (DEF-007) | V1 reproducibility guaranteed via SIM-019 per-user seed. Cross-run RNG state snapshot (for crash recovery and multi-run campaigns) is V2. | V2 | P2 | R-008 accepted for V1 |
| BL-023 | Scoring Weights UI Sliders (DEF-009) | ConfigRegistry fields added in Phase 2 (BL-010). JSON-editable in V1. UI sliders in V2. | V2 | P1 | BL-010 complete |
| BL-024 | Profile Evolution Probabilities as Category B | Fixed probabilities for V1. Configurability deferred pending BL-047 calibration research. | V2 | P2 | BL-047 research complete |
| BL-025 | Behavior Profile Density Thresholds as Category B | Fixed thresholds for V1. Configurability deferred pending user feedback and research. | V2 | P2 | BL-047 research complete |
| BL-026 | Engagement Cooldown as Per-Trigger Setting | Global cooldown setting sufficient for V1. Per-trigger granularity is V2. | V2 | P2 | V1 complete |
| BL-027 | Journey Branching (Conditional Ad Sequences) | Linear journeys only in V1. Branching requires new journey model design. | V2 | P2 | V1 journey engine complete |
| BL-028 | Audience Forecast Monte Carlo (Screen 7) | No Monte Carlo in V1. Deterministic capacity calculation sufficient. | V2 | P2 | Phase 9 complete |
| BL-039 | Replace UserState Float Fields with float32 Annotations | float32 enforced at DataFrame level via explicit casting. Model-level annotation is a V2 polish item. | V2 | P2 | V1 complete |
| BL-056 | Rolling TER Windows with SR-005 Context-Awareness (FE-018) | TER is cumulative denominator in V1 per Trigger_Engagement_Clarification.md. Rolling window is a reporting enhancement. | V2 | P2 | V1 complete |
| BL-057 | Trigger Saturation Protection (FE-019) | Not in V1 requirements. Saturation detection is an advanced capacity management feature. | V2 | P1 | BL-044 benchmark data |
| BL-058 | Segment Saturation Protection (FE-020) | Same rationale as BL-057. | V2 | P2 | BL-044 benchmark data |
| BL-059 | Engagement Decay Model — Exponential (FE-021) | V1 uses linear affinity decay. Exponential decay model adds realism but not required for V1. | V2 | P2 | BL-048 calibration data |
| BL-060 | Historical Engagement Weighting (FE-022) | Historical data informs affinity in V1 but not engagement probability directly. Weighting model is V2. | V2 | P2 | BL-042 research |
| BL-063 | Formal SegmentConfig.priority as V2 Tiebreak Key | In V1, segment follows trigger winner (ARCH-014). V2 may introduce a formal SegmentConfig.priority sort key as a secondary tiebreak before alphabetical segment name. Reserved field name: preferred_segment on TriggerConfig. Do not implement in V1; field name is reserved. | V2 | P2 | ARCH-014 implemented in V1 |

### V3 — Platform Features

| BL-ID | Title | Deferral Rationale | Target Release | Priority |
|-------|-------|--------------------|----------------|----------|
| BL-029 | Channel Plugin Framework (DEF-002) | Current fixed channels (Email, WhatsApp, Display, Endemic_Display) sufficient for V1. Plugin architecture for custom channels is a major platform investment. | V3 | P1 |
| BL-030 | Background Thread Execution (DEF-004) | Streamlit single-thread model acceptable for V1 scale. Background threads required for large-scale async execution. | V3 | P2 |
| BL-031 | REST API / Headless Mode | UI-only product for V1. Headless mode for CI/automation integration is a V3 platform feature. | V3 | P2 |
| BL-032 | Cloud Storage Output Target | Local file system output only in V1. Cloud storage (S3, GCS, Azure Blob) is a V3 platform feature. | V3 | P2 |
| BL-033 | Scheduled Batch Run Support | UI-triggered runs only in V1. Scheduled batch execution requires background daemon and is V3. | V3 | P3 |
| BL-034 | Database Output Target (SQL) | Excel output only in V1. SQL output target for analytics integration is V3. | V3 | P3 |
| BL-061 | Campaign Seasonality Modeling (FE-023) | No seasonality in V1 engagement model. Seasonality requires time-series calibration data. | V3 | P3 |

### Nice to Have (No Release Commitment)

| BL-ID | Title | Notes |
|-------|-------|-------|
| BL-050 | Interactive Engagement Curve Chart in Screen 9 | Requires charting library integration; low user demand signal so far. |
| BL-051 | Campaign Comparison / Diff View | Useful for power users running multiple config variants. |
| BL-052 | Configurable Output File Naming Format | Minor UX polish. |
| BL-053 | Auto-Suggest Engagement Rate Based on Segment Size | Would require inverse TCC calculation; design complexity not justified. |
| BL-054 | PDF Export of ValidationReport | Low priority; Excel export satisfies most stakeholders. |
| BL-055 | Simulation "What-If" Sandbox Mode | High design complexity; insufficient user stories to justify V1/V2. |

---

## 3. Technical Debt Register

Technical debt items are existing code or configuration deficiencies that increase future maintenance cost. V1-targeted debt must be resolved before GATE-P10. V1.1 debt must be resolved before V2 coding begins.

| TD-ID | BL-ID | Title | Description | Severity | Target Release | Phase Introduced | Status |
|-------|-------|-------|-------------|----------|----------------|-----------------|--------|
| TD-001 | BL-035 | Dead iterrows() executes at runtime | ARCH-011 violation. iterrows() block in load_historical_file() runs on every call despite producing a variable (mask) that is never used. | High | V1 — Phase 2 remediation | Phase 2 | **RESOLVED — 2026-06-22 (REM-009)** |
| TD-002 | BL-036 | Undocumented apply() call in load_historical_file() | No comment explains why a vectorized alternative is not used. Future developer may replace with iterrows() thinking it is equivalent. | Medium | V1 — Phase 2 remediation | Phase 2 | **RESOLVED — 2026-06-22 (REM-009). PV-002 comment added.** |
| TD-003 | BL-009 | test_trigger_config.py and test_segment_config.py absent | Two model classes have no test files at all. Equivalent to zero coverage for critical __post_init__ validation paths. | High | V1 — Phase 2 remediation | Phase 2 | **RESOLVED — 2026-06-22 (REM-013). Both files created.** |
| TD-004 | BL-010 | ConfigRegistry missing 5 scoring weight fields | SIM-001 composite formula requires five configurable weights. None exist in ConfigRegistry. Phase 5 cannot implement scoring without hardcoded literals. | High | V1 — Phase 2 remediation | Phase 2 | **RESOLVED — 2026-06-22 (REM-004)** |
| TD-005 | BL-010 | ConfigRegistry missing frequency_max field | Reach recency formula requires frequency_max. Absent from model forces Phase 5 to hardcode. | High | V1 — Phase 2 remediation | Phase 2 | **RESOLVED — 2026-06-22 (REM-004)** |
| TD-006 | BL-001 | config_loader.py builds all three sub-models with wrong fields | TriggerConfig, SegmentConfig, ChannelConfig constructors all receive wrong field names and counts. TypeError on every config load. | Critical | V1 — Phase 2 remediation | Phase 2 | **RESOLVED — 2026-06-22 (REM-005/REM-006/REM-007)** |
| TD-007 | BL-001 | config_loader.py passes 11+ wrong field names to ConfigRegistry | load_config_from_dict() references field names that do not exist in ConfigRegistry (vendor, historical_campaign_match_mode, custom_historical_days, etc.). TypeError on every call. | Critical | V1 — Phase 2 remediation | Phase 2 | **RESOLVED — 2026-06-22 (REM-008)** |
| TD-008 | BL-006 | No CI import linting for ARCH-005 | Import tier hierarchy is policy-only. PV-001 proves human review is insufficient. Any future developer can introduce a forbidden import without detection. | High | V1 | Phase 2 | Open — BL-006 |
| TD-009 | BL-007 | No CI coverage gate | ≥90% coverage requirement in Definition of Done is manually verified. Can drift silently without automation. | Medium | V1 | Phase 2 | Open — BL-007 |
| TD-010 | BL-039 | UserState affinity fields typed as float (not float32) at model level | ARCH-012 specifies float32 for all affinity and score columns. Model definitions use float (64-bit). DataFrame casting handles this at runtime but model type annotations are misleading. | Medium | V2 | Phase 2 | Open — deferred |
| TD-011 | BL-001 | is_qualifying_action() docstring mentions only TER, not TCC | BIZ-011 states QUALIFYING_ACTIONS is the single source of truth for both TER and TCC. Docstring implies TER-only usage, which could lead Phase 5 developers to bypass the function for TCC calculations. | Low | V1 — Phase 2 remediation | Phase 2 | Open — REM-015 |
| TD-012 | BL-001 | count_historical_engaged_users() docstring uses wrong TCC name | "Target Capacity Check" is not the project term. Correct term is "Trigger Capacity Consumption." Misleads developers looking for TCC functions. | Low | V1 — Phase 2 remediation | Phase 2 | Open — REM-016 |
| TD-013 | BL-001 | config_registry.py imports HistoricalMatchMode (non-existent enum) | HistoricalCampaignMatchMode is the approved enum. HistoricalMatchMode import causes ImportError at module load. | Critical | V1 — Phase 2 (immediate) | Phase 2 | **RESOLVED — 2026-06-21 (REM-001). See WAVE_1_EXECUTION_REPORT.md.** |
| TD-014 | BL-001 | user_state.py imports Channel enum (should be ChannelType) | ChannelType is the approved enum. Channel import causes ImportError at module load. | Critical | V1 — Phase 2 (immediate) | Phase 2 | **RESOLVED — 2026-06-21 (REM-002). See WAVE_1_EXECUTION_REPORT.md.** |
| TD-015 | BL-037 | No mypy type-check configuration in pyproject.toml | Type checking is entirely manual. mypy would catch type annotation mismatches before runtime. | Low | V1.1 | Phase 2 | Open — deferred |
| TD-016 | BL-038 | __all__ completeness not enforced by CI | __all__ lists can become stale as new public symbols are added. No automated check detects missing symbols. | Low | V1.1 | Phase 2 | Open — deferred |
| TD-017 | BL-041 | Unused os import in config_io.py | Triggers F401 in linting. Small code quality issue. | Low | V1 (next touch) | Phase 2 | Open |
| TD-018 | BL-040 | Scoring weight defaults as inline literals | DEFAULT_WEIGHT_ENGAGEMENT = 0.30 etc. should be named constants in utils/constants.py. Current literals will drift if one location is updated and another is not. | Medium | V1 — Phase 2 remediation | Phase 2 | **RESOLVED — 2026-06-22 (REM-004)** |
| TD-019 | BL-008 | RemainingCapacityRow.compute() uses int() not math.ceil() | TCC under-counts by floor instead of ceiling. Silent correctness defect affecting every capacity row. | High | V1 — Phase 2 (immediate) | Phase 2 | **RESOLVED — 2026-06-22 (REM-003)** |
| TD-020 | BL-001 | reconcile_creative_affinity_columns in Part1/2 schema_validator variants | Base document correctly places function in excel_utils.py only. Part1/Part2 variants duplicate it in schema_validator.py. Wrong variant written to disk means the function appears in the wrong module. | Medium | V1 — Phase 2 remediation | Phase 2 | Open — REM-014 |
| TD-021 | BL-001 | Dedup step ordering not documented in load_historical_file() | C-005 requires dedup before any filter. The ordering is correct but undocumented. A future refactoring could silently re-order steps. | Low | V1 — Phase 2 remediation | Phase 2 | Open — REM-017 |
| TD-022 | BL-009 | make_state() uses EligibilityStatus.ELIGIBLE (non-existent) | EligibilityStatus has no ELIGIBLE member. AttributeError raised before any test in the file reaches its assertion lines. | Critical | V1 — Phase 2 (immediate) | Phase 2 | **RESOLVED — 2026-06-22 (REM-010)** |
| TD-023 | BL-009 | make_registry() TriggerConfig called with 6 wrong positional args | Canonical TriggerConfig takes 4 keyword args. Six positional args raises TypeError before any test in the file runs. | Critical | V1 — Phase 2 (immediate) | Phase 2 | **RESOLVED — 2026-06-22 (REM-011/012)** |

**Technical Debt Total: 23. Critical: 6. High: 5. Medium: 5. Low: 7. All Phase 2 origin.**

---

## 4. Future Enhancements

Future enhancements are features with user or business value that are explicitly out of V1 scope. Organized by release horizon.

### FE-001 through FE-017 (Carried from PROJECT_CHANGE_LOG.md)

These features were proposed and evaluated during the V1 design phase. Each was formally rejected for V1 scope and assigned a target release.

| FE-ID | BL-ID | Title | Target Release | Rejection Reason |
|-------|-------|-------|----------------|-----------------|
| FE-001 | BL-019 | Per-Channel Qualifying Action Override | V2 | BIZ-011: system constant in V1; V2 Category B candidate |
| FE-002 | — | Per-User Journey Branching | V2 | Requires new journey state model; not in V1 requirements |
| FE-003 | BL-022 | RNG State Snapshot for Multi-Run Campaigns | V2 | Single-run reproducibility via SIM-019 sufficient for V1 |
| FE-004 | BL-018 | Multi-Campaign Batch Runner | V2 | DD-002 deferred; ARCH-001 single-campaign for V1 |
| FE-005 | BL-029 | Channel Plugin Framework | V3 | Major platform investment; fixed channels sufficient for V1 |
| FE-006 | BL-020 | Data-Driven Affinity Thresholds | V2 | Fixed thresholds sufficient; calibration research (BL-046) needed first |
| FE-007 | BL-021 | Timezone and Week-Start Configuration | V2 | ISO Monday assumed in V1; BL-074 confirms via stakeholder review |
| FE-008 | BL-023 | Scoring Weights UI Sliders | V2 | Fields added (BL-010); JSON-editable in V1; UI sliders V2 |
| FE-009 | BL-031 | REST API / Headless Mode | V3 | V1 is desktop UI only |
| FE-010 | — | Conditional (Branching) Ad Sequences | V2 | Linear sequences only in V1; journey state complexity |
| FE-011 | — | Cross-Campaign HCP De-Duplication | V2 | Single campaign in V1; multi-campaign required |
| FE-012 | — | Predictive Engagement Score Calibration | V3 | Requires training data not available for V1 |
| FE-013 | — | Real-Time Simulation Progress Streaming | V2 | Single-thread Streamlit sufficient for V1 |
| FE-014 | — | Configurable Journey Length (Min/Max Days) | V2 | Fixed journey structure per AdConfig in V1 |
| FE-015 | — | Audience Overlap Report (Cross-Trigger) | V2 | Single trigger perspective in V1 reporting |
| FE-016 | BL-028 | Audience Forecast Monte Carlo | V2 | Deterministic TCC calculation sufficient for V1 |
| FE-017 | — | Automated HCP Segmentation from Trigger Data | V3 | Requires ML/clustering; far out of V1 scope |

### FE-018 through FE-023 (New — Added 2026-06-21)

| FE-ID | BL-ID | Title | Description | Target Release | Priority |
|-------|-------|-------|-------------|----------------|----------|
| FE-018 | BL-056 | Rolling TER Windows with SR-005 Context-Awareness | Report TER over rolling 30/60/90-day windows in addition to the current all-time cumulative denominator. SR-005 would operate on the rolling window rather than lifetime totals. Allows campaigns to measure recent momentum rather than historical weight. | V2 | P2 |
| FE-019 | BL-057 | Trigger Saturation Protection | Detect when a trigger's engaged user count approaches its TCC ceiling and automatically throttle further engagement generation to prevent unrealistic saturation patterns. Requires a saturation threshold field on TriggerConfig. | V2 | P1 |
| FE-020 | BL-058 | Segment Saturation Protection | Same concept as FE-019 applied at the segment level. Prevents one segment from consuming all available engagement capacity when multiple segments share a trigger. | V2 | P2 |
| FE-021 | BL-059 | Engagement Decay Model — Exponential Decay | Replace linear affinity decay (affinity_decay_no_engage) with an exponential decay curve parameterized by half-life. More realistic for long-dormancy users. Requires new ConfigRegistry field and calibration data (BL-048). | V2 | P2 |
| FE-022 | BL-060 | Historical Engagement Weighting | Weight current-cycle engagement probability by historical engagement rate for the same user-channel pair. Users with high historical engagement probability receive a boost; cold users receive a penalty. Requires historical data join in Behavior Engine. | V2 | P2 |
| FE-023 | BL-061 | Campaign Seasonality Modeling | Multiply engagement probabilities by a configurable time-series seasonality index (e.g., reduced engagement in August and December for US pharma). Requires new ConfigRegistry fields and a seasonality profile input file. | V3 | P3 |

---

## 5. Governance Enhancements

Governance enhancements are process and documentation improvements that reduce project risk and improve long-term maintainability. These are not features but are equally important for project health.

| BL-ID | GG-ID | Title | Description | Priority | Owner | Target Phase | Status |
|-------|-------|-------|-------------|----------|-------|-------------|--------|
| BL-088 | GG-004 | Add Traceability Update to Every Phase DoD | Update TRACEABILITY_MATRIX.md is an explicit required criterion in every phase's Definition of Done (Phases 3–10). Without enforcement, the matrix becomes stale after Phase 2. | P1 | Program Manager | Phase 3 (immediate) | Open |
| BL-089 | GG-005 | Add Master Register Update to Every Phase DoD | Update PROJECT_MASTER_REGISTER.md is an explicit required criterion in every phase's Definition of Done (Phases 3–10). | P1 | Program Manager | Phase 3 (immediate) | Open |
| BL-090 | GG-012 | Assign Resolution Deadlines to All Open Questions | Each of OQ-001 through OQ-014 must be assigned a resolution-by date corresponding to its blocking phase. OQ-003 and OQ-007 are highest urgency. | P1 | Program Manager | Immediately | Open |
| BL-066 | GG-001 | Annotate Requirements_v1.md with REQ-IDs | The 30 REQ-IDs in TRACEABILITY_MATRIX.md were assigned by that document. They do not appear in Requirements_v1.md. Add a mapping addendum to Requirements_v1.md so REQ-IDs are traceable to their source. | P2 | Governance Lead | Phase 3 | Open |
| BL-067 | GG-009 | Document Amendment Process Workflow | PROJECT_HANDOFF.md §24 Rule 3 describes an amendment process but no workflow exists for approver roles, review SLA, or definition of breaking vs. non-breaking amendment. | P2 | Governance Lead | Phase 3 | Open |
| BL-068 | GG-010 | Assign Verification Phase to Each of 15 Assumptions | Each assumption in the assumptions register (A-001 through A-015) needs a verification phase. Unverifiable assumptions must be escalated to Open Questions before V1 release. | P2 | Program Manager | Phase 3 | Open |
| BL-069 | GG-011 | Define Risk Escalation Triggers and Notification Owners | 13 risks are identified but no process exists for when a risk escalates from Low to High exposure or who is notified. Define exposure thresholds and escalation owners for each risk. | P2 | Program Manager | Phase 3 | Open |
| BL-064 | GG-004 | RELEASE_GATES.md Dashboard Updates After Each Gate | Gate Status Dashboard in RELEASE_GATES.md §12 must be updated (date, sign-off) after each gate evaluation. Assign responsibility to Program Manager role. | P2 | Program Manager | Ongoing | Open |
| BL-065 | GG-005 | PROJECT_MASTER_REGISTER.md Health Score Updated Each Phase | Project Health Score (Section 2) must be recalculated at each phase completion. Target scores per phase are defined in §2. | P2 | Program Manager | Ongoing | Open |

**Governance Enhancement Total: 9 items. P1: 3. P2: 6.**

---

## 6. CI/CD Enhancements

CI/CD enhancements automate quality gates that are currently manual. Each item closes a governance gap or architecture gap.

| BL-ID | AG-ID / GG-ID | Title | Description | Priority | Owner | Target Phase | Status |
|-------|---------------|-------|-------------|----------|-------|-------------|--------|
| BL-006 | AG-001 / GG-002 | Import Linting Gate for ARCH-005 Enforcement | Automated check that fails if core/ imports app/, or utils/ imports core/ or app/. Implement as pylint plugin or a custom script run in pre-commit and CI. Closes AG-001 and GG-002. Verification: `grep -rn "^from app\|^import app" engagement_data_generator/core/` returns zero hits. | P1 | Lead Engineer | Phase 3 | Open |
| BL-007 | GG-003 | Coverage Gate (--cov-fail-under=90) in CI | Add to pyproject.toml: `addopts = --cov=models --cov=utils --cov=core --cov-fail-under=90` for all non-app modules. CI fails if coverage regresses below 90%. Closes GG-003. | P1 | Lead Engineer | Phase 3 | Open |
| BL-064-CI | AG-003 | CI Grep Gate: No iterrows() in Production Code | Add to pre-commit and CI: `grep -rn "iterrows" engagement_data_generator/ --include="*.py"` exits non-zero if any hits. Closes AG-003 permanently after PV-001 is fixed. | P1 | Lead Engineer | Phase 2 (alongside REM-009) | Open |
| BL-065-CI | AG-007 | CI Grep Gate: No hash() Without hashlib | Add to pre-commit and CI: `grep -rPn "\bhash\(" engagement_data_generator/ --include="*.py" | grep -v hashlib` exits non-zero if any hits. Closes AG-007. | P1 | Lead Engineer | Phase 2 | Open |
| BL-066-CI | — | CI Grep Gate: No pd.to_excel() in Production Code | Add to pre-commit and CI: `grep -rn "pd\.to_excel" engagement_data_generator/ --include="*.py"` exits non-zero if any hits. Consistent with ARCH-009. | P1 | Lead Engineer | Phase 2 | Open |
| BL-067-CI | — | CI Grep Gate: No TODO/FIXME/HACK in Production Code | Add to pre-commit and CI: `grep -rn "TODO\|FIXME\|HACK" engagement_data_generator/ --include="*.py"` exits non-zero if any hits. Keeps codebase clean between phases. | P2 | Lead Engineer | Phase 3 | Open |
| BL-068-CI | AG-002 | Phase 8 Unit Test Monkeypatching pd.to_excel() | Phase 8 test suite must monkeypatch pd.to_excel() and assert it is never called during any export function invocation. Closes AG-002. | P1 | Lead Engineer | Phase 8 | Not Started |
| BL-044 | — | Engine Performance Benchmarking Framework | Automated benchmark tests at 1K, 10K, 50K user scale with explicit SLA thresholds in conftest.py. Fails CI if run time exceeds SLA. Results feed DD-005 and DD-008 decisions. | P1 | Lead Engineer | Phase 10 | Not Started |
| BL-081-CI | VG-009 | SLA Assertion in CI Performance Suite | Once BL-044 benchmarks are run and OQ-001 SLA is resolved, add explicit SLA threshold assertions to CI performance test suite. | P2 | Lead Engineer | Phase 10 | Not Started |
| BL-015-CI | — | mypy Type-Check in CI (Post V1) | Add mypy --strict run to CI pipeline. Flags type annotation mismatches not caught at runtime. Deferred to V1.1 but CI plumbing should be prepared. | P3 | Lead Engineer | V1.1 | Deferred |

**CI/CD Enhancement Total: 10 items. P1: 7. P2: 2. P3: 1.**

---

## 7. Backlog Review Process

### Review Cadence

The backlog is reviewed at five mandatory points:

| Review Point | Trigger | Required Actions |
|-------------|---------|-----------------|
| Phase Start | Beginning of each phase | (1) Confirm all open P0 items for this phase are assigned and in progress. (2) Review deferred items for any that should be pulled forward. (3) Update each open item's status. |
| Mid-Phase (Optional) | When a blocking issue is discovered | Add new items discovered during implementation. Escalate priority if needed. |
| Phase End / Gate Evaluation | When phase gate criteria are being checked | (1) Close all items completed this phase. (2) Re-assign any items not completed to the next appropriate phase. (3) Add newly discovered items. (4) Update RELEASE_GATES.md §12 dashboard. |
| V1 Release Freeze | When all phases are complete | Confirm all V1-tagged items are CLOSED. Prepare V2 backlog as a clean prioritized list. |
| Post-Release Retro | After V1 ships | Review actual vs. estimated effort. Identify estimation patterns. Incorporate learnings into V2 backlog sizing. |

### Item Lifecycle

```
Identified → Triaged → Prioritized → In Progress → Closed (or Deferred)
```

- **Identified:** Item discovered during implementation, testing, governance review, or user feedback.
- **Triaged:** Item reviewed by Lead Engineer + Architect; assigned ID, priority, category, and target phase.
- **Prioritized:** Item placed in the correct section of this document (Open, Deferred, TD, FE, GE, CI/CD).
- **In Progress:** Phase gate criteria require this item to be completed; engineer assigned.
- **Closed:** Acceptance criteria met; gate verification command passes; registered as resolved in PROJECT_MASTER_REGISTER.md.
- **Deferred:** Item's target release is V1.1 or later; documented in Section 2 with rationale.

### Priority Definitions

| Priority | Definition | Examples |
|----------|------------|---------|
| P0 | Hard gate blocker — phase or release cannot proceed without this item | Critical defects, architecture decisions blocking implementation, compliance reviews required before coding |
| P1 | Strong requirement — should ship in target phase; deferral requires Chief Architect approval | CI gates, coverage requirements, important test coverage gaps, primary UX features |
| P2 | Useful but non-blocking — can shift one phase or to V1.1 without impacting V1 quality | Documentation quality, secondary test coverage, non-critical compliance items |
| P3 | Nice to have — ships if capacity allows; otherwise V1.1 | Code hygiene, import cleanup, non-critical analytics features |

### Adding New Items

When a new item is discovered:
1. Assign the next available BL-ID (current highest: BL-090; next available: BL-091).
2. Determine priority (P0–P3) using the Priority Definitions above.
3. Choose the appropriate section: Open (V1 work), Deferred (V1.1+), TD, FE, GE, or CI/CD.
4. Add a dependency entry if the item blocks or is blocked by another item.
5. Add the item to PROJECT_MASTER_REGISTER.md Section 14 simultaneously.
6. If the item affects a phase gate, update RELEASE_GATES.md accordingly.

### Closing Items

When an item is complete:
1. Change Status to CLOSED in this document.
2. Change Status to RESOLVED in PROJECT_MASTER_REGISTER.md with a commit reference.
3. If the item resolved a governance gap (GG-ID), architecture gap (AG-ID), or validation gap (VG-ID), update those registers in PROJECT_MASTER_REGISTER.md.
4. If the item satisfied a gate criterion, update RELEASE_GATES.md §12 dashboard.
5. Do not delete rows. Closed items remain as historical record.

### Escalation Rules

| Condition | Action |
|-----------|--------|
| P2 item becomes a blocking dependency | Re-prioritize to P1 or P0 and notify Lead Engineer + Architect |
| P1 item cannot be completed before its phase gate | Either defer phase gate, descope item to V1.1, or escalate to P0 with additional resource allocation |
| P0 item is not started within 2 business days of phase start | Escalate to Program Manager; identify blocker and resolution path |
| New item has P0 priority | Immediately notify Lead Engineer + Architect; item is added to this register within 24 hours |
| Legal or compliance item (COMP-*) is not initiated 4 phases before V1 release | Program Manager escalates to executive sponsor |

### Next Available BL-ID: BL-094

---

## Backlog Summary Dashboard

| Section | Total Items | P0 | P1 | P2 | P3 | Open | Deferred | Closed |
|---------|-------------|----|----|----|----|------|----------|--------|
| Open Backlog Items | 39 | 8 | 16 | 13 | 2 | 39 | 0 | 0 |
| Deferred Items | 28 | 0 | 3 | 17 | 8 | 0 | 28 | 0 |
| Technical Debt | 23 | 6 | 5 | 5 | 7 | 23 | 0 | 0 |
| Future Enhancements (FE) | 23 | 0 | 1 | 11 | 11 | 0 | 23 | 0 |
| Governance Enhancements | 9 | 0 | 3 | 6 | 0 | 9 | 0 | 0 |
| CI/CD Enhancements | 10 | 0 | 7 | 2 | 1 | 9 | 1 | 0 |
| **TOTAL** | **132** | **14** | **35** | **54** | **29** | **80** | **52** | **0** |

**V1 Critical Path Items (P0, Open):** BL-001, BL-009, BL-035, BL-003, BL-071, BL-072, BL-080, BL-084, TD-022, TD-023 *(TD-013 and TD-014 RESOLVED 2026-06-21; BL-008 and TD-019 RESOLVED 2026-06-22)*

**Longest-Lead Items (start immediately, not blocked by any code work):**
- BL-071: Legal review OQ-007 — start now; 8+ week lead time typical
- BL-072: Cooling period compliance review OQ-003 — start now; blocks Phase 3
- BL-090: OQ deadline assignment — 1-hour task, blocks nothing, unblocks everyone

---

*PROJECT_BACKLOG.md — Version 1.0*
*Engagement Data Generator v1.0*
*Chief Architect / Program Manager / Governance Owner*
*2026-06-21*

*This document is the single authoritative backlog register.*
*All additions must be made here and in PROJECT_MASTER_REGISTER.md simultaneously.*
*Next available BL-ID: BL-091*
*Review cadence: start and end of every phase gate per RELEASE_GATES.md §7.*
