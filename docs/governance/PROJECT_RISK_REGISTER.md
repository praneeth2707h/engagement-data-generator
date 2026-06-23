# PROJECT RISK REGISTER
# Engagement Data Generator — Version 1.0
# Formal Risk Register — All Categories, All Phases

**Document Version:** 1.0
**Prepared:** 2026-06-21
**Role:** Chief Architect / Program Manager / Risk Owner
**Status:** ACTIVE — Reviewed at every phase gate per RELEASE_GATES.md

**Sources Reviewed:**
- PROJECT_MASTER_REGISTER.md (R-001 through R-013, CB-001 through CB-009, GG-001 through GG-012, AG-001 through AG-007, VG-001 through VG-013, COMP-001 through COMP-005)
- PHASE_2_EXECUTION_PLAN.md (REM-001 through REM-018, 33 defects)
- PHASE_3_ARCHITECTURE_DECISIONS.md (DD-013/DD-014 analysis, ARCH-013, ARCH-014, CFG-NEW-001)
- RELEASE_GATES.md (GATE-P2 through GATE-V1 requirements)
- PROJECT_BACKLOG.md (BL-001 through BL-090)

**ID Assignment:** R-001 through R-013 carry forward from PROJECT_MASTER_REGISTER.md §15. R-014 onward are new risks identified from cross-document review.

---

## Risk Scoring Framework

### Probability Scale

| Code | Label | Definition |
|------|-------|------------|
| L | Low | Unlikely to occur given current controls; < 25% chance |
| M | Medium | Possible; reasonable probability given project context; 25–60% chance |
| H | High | Likely to occur if no mitigation action is taken; > 60% chance |

### Impact Scale

| Code | Label | Numeric | Definition |
|------|-------|---------|------------|
| L | Low | 1 | Minor inconvenience; < 1 day rework; no phase timeline impact |
| M | Medium | 2 | Meaningful rework; 1–3 day delay; single phase affected |
| H | High | 3 | Significant rework or delay; multiple phases affected; user-facing defect possible |
| C | Critical | 4 | Major scope, compliance, or release impact; V1 date at risk or legal exposure |

### Risk Score Formula

**Score = Probability_Numeric × Impact_Numeric**

| Probability | Low Impact (×1) | Medium Impact (×2) | High Impact (×3) | Critical Impact (×4) |
|-------------|----------------|-------------------|-----------------|---------------------|
| Low (×1) | 1 — Low | 2 — Low | 3 — Medium | 4 — Medium |
| Medium (×2) | 2 — Low | 4 — Medium | 6 — High | 8 — High |
| High (×3) | 3 — Medium | 6 — High | 9 — Critical | 12 — Critical |

### Severity Thresholds

| Score | Severity |
|-------|---------|
| 1–2 | Low |
| 3–5 | Medium |
| 6–8 | High |
| 9–12 | Critical |

### Status Values

| Status | Meaning |
|--------|---------|
| Open | Risk is active and mitigations are not yet fully in place |
| Active | Risk is being actively managed; mitigations in progress |
| Escalated | Risk has increased in probability or impact; requires leadership decision |
| Monitoring | Mitigations are in place; risk is tracked but not expected to fire |
| Closed | Risk condition eliminated or phase has passed the exposure window |

---

## Table of Contents

1. Technical Risks (R-001 through R-017)
2. Performance Risks (R-018 through R-022)
3. Governance Risks (R-023 through R-027)
4. Architecture Risks (R-028 through R-033)
5. Testing Risks (R-034 through R-039)
6. Documentation Risks (R-040 through R-044)
7. Compliance Risks (R-045 through R-049)
8. Risk Summary Dashboard
9. Critical and High Risk Action Plan
10. Risk Review Process

---

## 1. Technical Risks

Technical risks are defects, type errors, data-model mismatches, or implementation failures that will cause incorrect behavior, import failures, or silent data corruption if not resolved.

---

### R-001

| Field | Value |
|-------|-------|
| **Risk ID** | R-001 |
| **Category** | Technical |
| **Description** | Phase 2 critical defects (MM-005, MM-006: ImportError in config_registry.py and user_state.py; MM-001–MM-004, LM-001: TypeError on every config load call; MT-001–MT-003: all test helpers raise before any assertion runs) block the entire test suite. No Phase 2 verification, no Phase 3 entry. These 10 critical defects form a single compound risk: if any one is missed during remediation, all downstream testing remains broken. |
| **Probability** | High |
| **P Numeric** | 3 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 9 |
| **Severity** | Critical |
| **Owner** | Lead Engineer |
| **Mitigation** | Execute REM-001 through REM-013 in dependency order (Group A first, Group B–E in sequence). Verify after each group: `python -c "from models.config_registry import ConfigRegistry"` and `pytest tests/test_models/ -x --tb=short`. Do not proceed to Group B until Group A passes. |
| **Contingency** | If remediation reveals additional defects not in the 33-item register, add to PHASE_2_EXECUTION_PLAN.md as REM-019+ and extend the Phase 2 timeline accordingly. Do not begin Phase 3 until all new defects are also resolved. |
| **Status** | **SUBSTANTIALLY MITIGATED — 2026-06-22. Wave 1: MM-005/MM-006 resolved (REM-001/002). Wave 2: TCC-001 and scoring weights resolved (REM-003/004). Wave 3: MM-001–MM-004, LM-001 resolved (REM-005–008). 127/127 tests pass. 3 of 10 critical defects remain (MT-001–MT-003 — test helpers, Wave 5). config_loader TypeError fully eliminated.** |
| **Review Date** | 2026-07-02 (Phase 2 remediation target completion) |

---

### R-002

| Field | Value |
|-------|-------|
| **Risk ID** | R-002 |
| **Category** | Technical |
| **Description** | TCC-001: RemainingCapacityRow.compute() uses int() (floor truncation) instead of math.ceil(). For 101 users at 10% engagement rate, int() returns 10 while math.ceil() returns 11. The error is silent — no exception is raised — and compounds across every trigger in every simulation run. Phase 5 Behavior Engine will build on an under-counting capacity model, and all engagement generation will be systematically below target. |
| **Probability** | High |
| **P Numeric** | 3 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 9 |
| **Severity** | Critical |
| **Owner** | Lead Engineer |
| **Mitigation** | REM-003: Replace int() with math.ceil() in capacity_row.py. Add `import math`. Update both docstrings. Add test: 101 users × 0.10 → assert result == 11. Gate check: `grep -n "int(total_users" models/capacity_row.py` returns zero hits after fix. |
| **Contingency** | If the fix is delayed past Phase 3, any audience capacity calculation performed before the fix is applied must be marked invalid and re-run. Phase 5 entry gate must verify math.ceil() is present before the Behavior Engine uses RemainingCapacityRow.compute(). |
| **Status** | **RESOLVED — 2026-06-22 (REM-003). math.ceil() applied; 16 tests passing; test_compute_ceil_not_floor regression gate passes.** |
| **Review Date** | 2026-07-02 |

---

### R-003

| Field | Value |
|-------|-------|
| **Risk ID** | R-003 |
| **Category** | Technical |
| **Description** | CONFIG_SCHEMA_VERSION = "2.0" is hardcoded. When V2 introduces new required fields, any user who opens a V1-generated UserState.xlsx or config JSON will get a SchemaVersionError. No migration path is documented. There is no mechanism to detect which version a file was generated with and auto-migrate. Users who have V1 output files cannot carry them forward into V2 without a migration tool. |
| **Probability** | High |
| **P Numeric** | 3 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer + Architect |
| **Mitigation** | Document V1 schema version and all required fields before V1 ships. Record the migration decision (DD-011) in PROJECT_DECISIONS.md before V2 design begins. Add a config version comment to every generated config file so the version is inspectable without loading the file. |
| **Contingency** | Build a migration script (BL-011 equivalent for config) as the first V2 pre-work item. If migration complexity is high, add `config_schema_version` to the User-Facing Breaking Changes section of the V1 release notes so users are warned before upgrade. |
| **Status** | Open |
| **Review Date** | 2026-10-12 (V1 release gate) |

---

### R-004

| Field | Value |
|-------|-------|
| **Risk ID** | R-004 |
| **Category** | Technical |
| **Description** | Per-user RNG seeds use hashlib.md5(user_id.encode()).hexdigest() mod 2^32, producing a 32-bit seed space of ~4.3 billion values. At trigger files with several hundred thousand users from a small ID namespace (e.g., sequential integer IDs), the probability of two users receiving the same seed becomes non-trivial (birthday problem). Seed collisions produce identical behavior profiles, journey outcomes, and engagement patterns for two distinct users, which reduces synthetic data diversity and is detectable by analysts. |
| **Probability** | Low |
| **P Numeric** | 1 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 3 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | BL-045 (RE-004): Verify collision probability using the birthday problem formula for the actual maximum trigger file size. If collision probability exceeds 0.01% at the V1 supported scale, switch to SHA-256 with 64-bit seed space. Document the chosen hash function in PROJECT_DECISIONS.md before Phase 5. |
| **Contingency** | If collision is detected in Phase 10 integration testing (two users with identical behavior profiles), switch to 64-bit seed immediately. This requires only a one-line change in utils/schema_validator.py or the relevant seeding function, so contingency cost is low. |
| **Status** | Open |
| **Review Date** | 2026-08-01 (Phase 5 start) |

---

### R-005

| Field | Value |
|-------|-------|
| **Risk ID** | R-005 |
| **Category** | Technical |
| **Description** | Streamlit releases minor versions frequently and has a history of deprecating widget APIs (e.g., st.beta_*, st.experimental_*). Between V1 release and V2 development, a Streamlit minor version upgrade could silently change component behavior or deprecate widgets used in the 9 app screens, causing UI regressions that were not present at V1 release. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | Pin Streamlit version exactly in requirements.txt (e.g., streamlit==1.X.Y). Document the pinned version in COMP-005 alongside the Python version pin. Test all 9 screens against each Streamlit minor release before upgrading. |
| **Contingency** | If a breaking change is introduced in a Streamlit patch before V2, stay on the pinned version for V1 maintenance. For V2, dedicate one sprint to upgrading the pinned version and verifying all screens. |
| **Status** | Open |
| **Review Date** | 2026-09-26 (Phase 9 start) |

---

### R-006

| Field | Value |
|-------|-------|
| **Risk ID** | R-006 |
| **Category** | Technical |
| **Description** | pandas and numpy minor version changes have historically broken vectorized operations, dtype inference, and groupby behavior. If the exact library versions are not pinned and a developer upgrades their environment, production tests could produce different results. Specifically at risk: pd.Categorical merges (R-013), dtype promotion behavior, and numpy array broadcasting in SIM-001 scoring. |
| **Probability** | Low |
| **P Numeric** | 1 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 2 |
| **Severity** | Low |
| **Owner** | Lead Engineer |
| **Mitigation** | Pin exact pandas and numpy versions in requirements.txt before Phase 3 begins. Add a CI compatibility matrix test (Python 3.11, Python 3.12) against the pinned versions. Document exact versions in COMP-005 addendum alongside Streamlit and Python. |
| **Contingency** | If a version upgrade is forced (e.g., security patch), run the full pytest suite before merging. If tests fail, identify the breaking API change and fix it as a P1 defect before the next phase begins. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (Phase 2 remediation completion — pin versions now) |

---

### R-007

| Field | Value |
|-------|-------|
| **Risk ID** | R-007 |
| **Category** | Technical |
| **Description** | pd.Categorical dtype columns (EligibilityStatus, ChannelType, etc.) exhibit unexpected behavior in pandas groupby, merge, and reindex operations when category levels are not aligned between DataFrames. A Categorical column in one DataFrame merged with an object-dtype column in another may produce NaN rows silently instead of raising an error. This type of silent data loss could occur during audience resolution, journey building, or fatigue aggregation. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | Add explicit dtype assertions in each phase's integration tests for all Categorical columns. Where merging is required, convert Categorical to object before the merge, then re-apply Categorical after. Document this pattern in docs/performance_guidelines.md. |
| **Contingency** | If a Categorical merge bug produces NaN rows in production output, add a post-merge assertion that row count equals pre-merge row count for inner joins. Add an advisory validation soft rule to detect unexpected NaN values in EligibilityStatus or ChannelType columns. |
| **Status** | Open |
| **Review Date** | 2026-07-11 (Phase 3 completion) |

---

### R-008

| Field | Value |
|-------|-------|
| **Risk ID** | R-008 |
| **Category** | Technical |
| **Description** | ConfigRegistry currently has no __post_init__ validator enforcing that the five scoring weights (scoring_weight_engagement + scoring_weight_profile + scoring_weight_creative + scoring_weight_channel + scoring_weight_recency) sum to 1.0 ± tolerance. A user who manually edits the config JSON with non-unit-sum weights will produce a silently corrupted composite score across all users — scores will not be in the expected [0, 1] range, and the SR-020 Realism Score will produce meaningless results. No exception is raised. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer |
| **Mitigation** | REM-004: Add __post_init__ assertion to ConfigRegistry: `if abs(sum([scoring_weight_engagement, scoring_weight_profile, scoring_weight_creative, scoring_weight_channel, scoring_weight_recency]) - 1.0) > 0.001: raise ConfigError("Scoring weights must sum to 1.0")`. Add test: non-unit weights raise ConfigError. |
| **Contingency** | If the validator is not added before Phase 5 implements SIM-001, add a weight-sum normalization step at the start of behavior_engine.py as a failsafe. Record as a technical debt item and add the validator in the next remediation pass. |
| **Status** | **RESOLVED — 2026-06-22 (REM-004). __post_init__ validator added; 27 tests passing including weight-sum and boundary tests.** |
| **Review Date** | 2026-07-02 (REM-004 target) |

---

### R-009

| Field | Value |
|-------|-------|
| **Risk ID** | R-009 |
| **Category** | Technical |
| **Description** | Phase 2 remediation involves rewriting 18 actions across 6 dependency groups. There is a risk that the remediation itself introduces new defects (e.g., a corrected field name does not exactly match what Phase 3 expects, or a new test file uses a fixture from a Phase 3 file that does not yet exist). Remediation work is always at risk of creating lateral defects when multiple files are changed simultaneously under time pressure. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | Execute remediation groups sequentially with a micro-verification step after each group (run pytest, run import check). Use `git diff --stat` after each group to review change scope. Do not combine Group A and Group B in a single commit. |
| **Contingency** | If new defects are introduced, add them to the remediation plan as REM-019+ with the same Group structure. Do not proceed to Phase 3 until the net defect count returns to zero (pytest passes cleanly). |
| **Status** | Open |
| **Review Date** | 2026-07-02 |

---

### R-010

| Field | Value |
|-------|-------|
| **Risk ID** | R-010 |
| **Category** | Technical |
| **Description** | TERMode is imported in config_registry.py but does not exist in the approved enum list in models/enums.py. REM-001 must either add TERMode to enums.py or replace it with an alternative (string annotation or removal). If TERMode is added as a new enum, it must be reviewed by the Architect to confirm it does not conflict with any approved enum design. If TERMode is removed, all references to it in the codebase must be found and replaced. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer + Architect |
| **Mitigation** | During REM-001, the Lead Engineer decides: (A) add `TERMode` to enums.py with values (Cumulative, Rolling) and document as a reserved V2 enum, or (B) replace the type annotation with `str` and add a docstring noting V2 will introduce a formal TERMode enum. Record the chosen resolution in PROJECT_DECISIONS.md. |
| **Contingency** | If neither option is clean, remove TERMode from config_registry.py entirely and add a TODO comment pointing to DD-004 (rolling window decision). File BL-091 to re-introduce TERMode in V2. |
| **Status** | **RESOLVED — 2026-06-21. REM-001 removed TERMode from the import entirely. The inline comment on the ter_mode field in ConfigRegistry was updated to note TERMode is reserved for V2 (no enum in V1). No references to TERMode remain in production code. No new enum was added. See config_registry.py line 11.** |
| **Review Date** | 2026-07-02 |

---

### R-011

| Field | Value |
|-------|-------|
| **Risk ID** | R-011 |
| **Category** | Technical |
| **Description** | reconcile_creative_affinity_columns() appears in the wrong file in the Part1/Part2 variant of schema_validator.py. If the wrong variant is written to disk, the function resides in schema_validator.py instead of the mandated location excel_utils.py. Any Phase 8 code that calls the function from schema_validator.py will import from the wrong module. When Phase 8 is tested in isolation (without importing schema_validator.py), the function will not be found and a NameError will be raised. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | REM-014: Verify that the file written to disk is the base document variant where reconcile_creative_affinity_columns() lives only in excel_utils.py. Add a CI grep check: `grep -n "reconcile_creative_affinity_columns" engagement_data_generator/utils/schema_validator.py` returns zero hits. |
| **Contingency** | If the wrong variant was written, remove the function from schema_validator.py and add a re-export stub that imports from excel_utils.py with a DeprecationWarning. Update all callers before Phase 8 begins. |
| **Status** | Open |
| **Review Date** | 2026-07-02 |

---

### R-012

| Field | Value |
|-------|-------|
| **Risk ID** | R-012 |
| **Category** | Technical |
| **Description** | Streamlit operates in a single-threaded event loop. For trigger files with large user populations (approaching 50K), the full 11-stage pipeline will block the main thread for the entire run duration. Users who expect responsiveness during a long run will have no feedback mechanism and may interpret a slow run as a frozen app. A user closing the browser window mid-run may kill the process, leaving a partial UserState.xlsx on disk. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer + Product Owner |
| **Mitigation** | Phase 9 Screen 8 (Run Generator) displays a progress spinner for the duration of the run. Add a run status flag to UserState during writes so a partial state file can be detected and rejected on next load. Document the single-thread limitation in the V1 release notes. |
| **Contingency** | If user complaints about frozen UI are significant post-V1, promote DD-005 (background thread) from V3 to V2. For V1, add an explicit estimated run-time display on Screen 8 based on trigger file row count. |
| **Status** | Open |
| **Review Date** | 2026-09-26 (Phase 9 start) |

---

### R-013

| Field | Value |
|-------|-------|
| **Risk ID** | R-013 |
| **Category** | Technical |
| **Description** | Streamlit API deprecations between V1 and later releases may break the 9-screen UI. Specifically, `st.experimental_*` and `st.beta_*` patterns were deprecated in Streamlit 1.x, and similar deprecations occur in each minor release. If the Phase 9 developer uses any experimental or beta API that is subsequently removed, V2 UI development will begin with broken baseline screens. |
| **Probability** | Low |
| **P Numeric** | 1 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 2 |
| **Severity** | Low |
| **Owner** | Lead Engineer |
| **Mitigation** | During Phase 9, do not use any `st.experimental_*` or `st.beta_*` APIs. Review Streamlit deprecation changelog for the pinned version before beginning implementation. Add a Streamlit version check to app/__init__.py that raises a clear error if the wrong version is loaded. |
| **Contingency** | If a deprecated API was used and a version upgrade breaks it, the fix is straightforward (replace the deprecated call with the stable API). Allocate 1–2 days for this as V1.1 maintenance if needed. |
| **Status** | Open |
| **Review Date** | 2026-09-26 (Phase 9 start) |

---

### R-014

| Field | Value |
|-------|-------|
| **Risk ID** | R-014 |
| **Category** | Technical |
| **Description** | The Move-On-Click rule (C-001) requires that a click-advance evaluation fires first; if it fires, the duration check is skipped entirely to prevent double-advance. If the Journey Engine (Phase 4) evaluates duration check before click-advance, or evaluates both and takes the first result, users will advance twice in one simulation step. This doubles journey progress and produces unrealistically short journeys. This ordering constraint is documented but has no test assertion yet (test enforcement deferred to Phase 4). |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer |
| **Mitigation** | Phase 4 must include a test: `test_c001_click_advance_skips_duration_check()` — when a Click qualifying action fires, assert that the duration check function is not called (using monkeypatch or spy). Add this test to Phase 4 acceptance criteria before Phase 4 coding begins. |
| **Contingency** | If double-advance is detected in Phase 10 integration testing, add an advance guard flag to JourneyState that prevents a second advance within the same simulation step. Rerun all Phase 4 tests with the guard in place before closing. |
| **Status** | Open |
| **Review Date** | 2026-07-20 (Phase 4 start) |

---

### R-015

| Field | Value |
|-------|-------|
| **Risk ID** | R-015 |
| **Category** | Technical |
| **Description** | The Weekly Reset rule (C-003) uses `d.weekday() == 0` (Monday = 0, ISO standard) to trigger the reset. The `isoweekday()` method returns Monday = 1, not 0. If a future developer replaces `weekday()` with `isoweekday()` while "fixing" what appears to be an off-by-one error, resets will fire on Tuesdays instead of Mondays. This produces an eight-day first week and silently incorrect fatigue counts for all users. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer |
| **Mitigation** | Add a comment above the `d.weekday() == 0` check: `# IMPORTANT: weekday() (0=Monday) NOT isoweekday() (1=Monday) — see C-003 in PROJECT_DECISIONS.md.` Add a test: `test_c003_reset_fires_on_monday()` that asserts no reset on Sunday, reset on Monday, no reset on Tuesday. |
| **Contingency** | If the wrong method is introduced in a later phase, detection occurs immediately via the test. Fix is a one-line change. No contingency planning required beyond the test gate. |
| **Status** | Open |
| **Review Date** | 2026-08-10 (Phase 6 start — fatigue engine) |

---

### R-016

| Field | Value |
|-------|-------|
| **Risk ID** | R-016 |
| **Category** | Technical |
| **Description** | Beyond the known TCC-001 defect, the Behavior Engine (Phase 5) and Allocation Engine (Phase 6) will introduce new numeric formulas involving ceiling, flooring, and percentage calculations. Silent arithmetic errors similar to TCC-001 (using int() instead of math.ceil(), integer division instead of float division) are a recurring risk in any phase that implements capacity or quota calculations. These errors produce no exceptions and are only detectable via test assertions that explicitly check boundary values. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer |
| **Mitigation** | Add to the Definition of Done for Phases 5 and 6: "All capacity and quota calculations include a boundary-value test asserting the correct rounding behavior (e.g., N users × rate = expected ceiling, not floor)." Add `math.ceil` usage to the performance guidelines document as the standard for all capacity calculations. |
| **Contingency** | If a silent arithmetic error is found in Phase 10 integration testing, identify every formula in Phases 5 and 6 that uses integer arithmetic and audit for correct rounding. Add regression tests for each formula before the Phase 10 gate closes. |
| **Status** | Open |
| **Review Date** | 2026-08-01 (Phase 5 start) |

---

### R-017

| Field | Value |
|-------|-------|
| **Risk ID** | R-017 |
| **Category** | Technical |
| **Description** | The EligibilityStatus enum approved values are: New, Active, Cooling, Re-Entry, Skipped. The test helper make_state() currently uses the non-existent EligibilityStatus.ELIGIBLE value (defect MT-001). If REM-010 replaces this with EligibilityStatus.NEW but other test files across later phases are written using ELIGIBLE by a developer who copies the broken fixture, the error will propagate silently until pytest is run. The risk is a class of copy-paste fixture errors from a broken template. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | After REM-010, add a comment above make_state(): `# APPROVED EligibilityStatus values: New, Active, Cooling, Re-Entry, Skipped. ELIGIBLE does not exist.` Add a conftest.py note referencing approved enum values. Phase 3+ test authors must reference the approved enum list in models/enums.py before writing fixtures. |
| **Contingency** | If a future phase introduces EligibilityStatus.ELIGIBLE in a test, it will raise AttributeError immediately. No silent failure. Fix is trivial. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (REM-010 target) |

---

## 2. Performance Risks

Performance risks are risks that cause the engine to exceed acceptable run times, consume excessive memory, or produce output files too large to open on a desktop machine.

---

### R-018

| Field | Value |
|-------|-------|
| **Risk ID** | R-018 |
| **Category** | Performance |
| **Description** | Trigger files with more than 50,000 users loaded as a single pandas DataFrame may exceed Streamlit's default memory limits (typically 1–2 GB for a desktop process). For a 50K-user trigger file with 50 columns, the loaded DataFrame requires approximately 200 MB before any processing. During Audience Resolution and User State initialization, multiple intermediate DataFrames coexist in memory, potentially reaching 1–3 GB total. Desktop machines with 8 GB RAM running other applications may OOM-kill the Streamlit process. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer |
| **Mitigation** | BL-044 (RE-003): Run performance benchmarks at 1K, 10K, 50K user scale during Phase 5. If memory consumption exceeds 1 GB at 50K, implement chunked DataFrame processing in Audience Resolution. Add a UI warning on Screen 2 when the uploaded trigger file contains more than 25,000 rows: "Large file detected. Run time and memory usage will be elevated." |
| **Contingency** | If 50K users causes OOM on reference hardware, cap V1 maximum trigger file size at 25,000 rows with a hard UI error. Document this constraint in the V1 release notes. Promote BL-030 (background thread / chunked processing) from V3 to V2. |
| **Status** | Open |
| **Review Date** | 2026-08-01 (Phase 5 benchmarks) |

---

### R-019

| Field | Value |
|-------|-------|
| **Risk ID** | R-019 |
| **Category** | Performance |
| **Description** | openpyxl writing to the EngagementEvents workbook may degrade significantly when the output exceeds 500,000 rows. openpyxl writes row-by-row in pure Python; a 500K-row write at the typical openpyxl throughput of 50K–100K rows/second takes 5–10 seconds. For 50K users × high engagement rates, the EngagementEvents output could exceed 1M rows, making write time 10–20+ seconds. Decision DD-008 (streaming vs. batch write) must be made before Phase 8. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer + Architect |
| **Mitigation** | BL-044 (RE-003): Measure openpyxl write time as part of Phase 5/6 benchmarks. Resolve DD-008 before Phase 8 coding begins. If batch write is too slow, implement streaming openpyxl writes (write-and-append row by row using WorksheetWriter). Add Phase 8 SLA: EngagementEvents write must complete in < 30 seconds for a 50K-user run. |
| **Contingency** | If openpyxl performance is insufficient even with streaming, add a CSV export option as a V1 alternative (BL-012 promoted from V1.1 to V1). Users with large datasets use CSV; users with standard datasets use Excel. |
| **Status** | Open |
| **Review Date** | 2026-08-01 (Phase 5 benchmarks complete; informs DD-008) |

---

### R-020

| Field | Value |
|-------|-------|
| **Risk ID** | R-020 |
| **Category** | Performance |
| **Description** | The SIM-001 composite score formula requires computing five weighted components per user per trigger assignment. With 50K users, 10 triggers, and 5 components per score, the scoring loop requires 2.5 million component computations per simulation run. If implemented naively as a Python loop (even with apply()), this could take 30–60 seconds. If vectorized incorrectly, the computation may still be slow due to intermediate DataFrame materializations for each component. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer |
| **Mitigation** | Phase 5 must implement SIM-001 as a fully vectorized numpy operation: compute all five weight components as DataFrame column operations, then take the weighted sum in a single expression. Add a Phase 5 benchmark test: SIM-001 scoring for 50K users must complete in < 10 seconds. Reject any apply()-based implementation of the scoring loop. |
| **Contingency** | If vectorization is not feasible due to per-user conditional logic in one of the components, implement the offending component in Cython or use numba JIT as a last resort. Document the non-vectorized component and its justification in performance_guidelines.md. |
| **Status** | Open |
| **Review Date** | 2026-08-01 (Phase 5 completion) |

---

### R-021

| Field | Value |
|-------|-------|
| **Risk ID** | R-021 |
| **Category** | Performance |
| **Description** | All 7 output workbooks (EngagementEvents, UserState, TriggerCapacitySummary, SegmentSummary, ValidationReport, CampaignSummary, SimulationReport) are held open simultaneously by openpyxl during Phase 8 export. For large runs, each workbook may consume 50–200 MB of memory while open. Seven concurrent workbooks at maximum size could require 700 MB–1.4 GB of memory for the export stage alone, on top of the already-loaded simulation data. |
| **Probability** | Low |
| **P Numeric** | 1 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 2 |
| **Severity** | Low |
| **Owner** | Lead Engineer |
| **Mitigation** | DD-008 decision must address whether workbooks should be opened, written, and closed sequentially rather than simultaneously. Measure peak memory during Phase 8 test runs. If sequential write is needed, design Phase 8 accordingly before coding. |
| **Contingency** | If peak memory during export causes an OOM, switch to sequential workbook write (open, populate, close, repeat). The change is architectural within Phase 8 and does not affect the public API of export_engine.py. |
| **Status** | Open |
| **Review Date** | 2026-09-10 (Phase 8 start) |

---

### R-022

| Field | Value |
|-------|-------|
| **Risk ID** | R-022 |
| **Category** | Performance |
| **Description** | The historical file deduplication step in load_historical_file() must process all historical engagement records before filtering. For a pharma campaign that has been running for 2+ years, the historical file could contain millions of rows. Loading a million-row CSV into memory for deduplication before any filtering will consume 500 MB+ and may exceed available memory on low-spec machines before any data processing begins. |
| **Probability** | Low |
| **P Numeric** | 1 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 3 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | Add a row count check in load_historical_file() before loading: if file row count > 100,000 (configurable threshold), display a warning on Screen 2. Document V1 historical file size limitation. BL-009 (RE-008): Analyze actual historical file sizes from target users before Phase 5. |
| **Contingency** | If historical files routinely exceed 100K rows, implement chunked deduplication using pandas read_csv(chunksize=) with a hash-based dedup accumulator. Deferred to V2 (BL-030) if V1 users are not blocked by this. |
| **Status** | Open |
| **Review Date** | 2026-07-11 (Phase 3 — historical data loading) |

---

## 3. Governance Risks

Governance risks are risks arising from missing process controls, unenforced policies, unresolved decisions, or documentation that becomes stale or inconsistent.

---

### R-023

| Field | Value |
|-------|-------|
| **Risk ID** | R-023 |
| **Category** | Governance |
| **Description** | DD-013 and DD-014 (trigger tiebreak and segment tiebreak) were analyzed and decided in PHASE_3_ARCHITECTURE_DECISIONS.md, but neither decision has yet been formally recorded in PROJECT_DECISIONS.md as ARCH-013 and ARCH-014. Phase 3 cannot begin until these decisions are in PROJECT_DECISIONS.md — this is an explicit GATE-P2 requirement. If Phase 3 begins before the formal recording, audience_manager.py will be implemented against an undocumented decision that could be interpreted differently by a different developer later. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Architect |
| **Mitigation** | Before Phase 3 kick-off, add ARCH-013 and ARCH-014 entries to PROJECT_DECISIONS.md with the full decision text from PHASE_3_ARCHITECTURE_DECISIONS.md §6. Also add CFG-NEW-001 (strict_priority_validation reserved field). Confirm GATE-P2 checklist item "ARCH-013 and ARCH-014 must be in PROJECT_DECISIONS.md" is marked complete by the Program Manager. |
| **Contingency** | If Phase 3 has already begun without formal recording, stop Phase 3 work, complete the PROJECT_DECISIONS.md recording immediately, then resume. Any audience_manager.py code written before the recording must be reviewed for consistency with the formal decision. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (GATE-P2 checklist) |

---

### R-024

| Field | Value |
|-------|-------|
| **Risk ID** | R-024 |
| **Category** | Governance |
| **Description** | 14 open questions (OQ-001 through OQ-014) have no assigned resolution deadlines. Three are blockers for specific phases: OQ-003 (cooling period compliance) blocks Phase 3 if not reviewed; OQ-007 (legal review) blocks Phase 9 if not completed; OQ-005 and OQ-011 (duplicate of DD-013/DD-014) block Phase 3. If no deadlines are assigned and no reminders are sent, these questions will remain open until they become emergency blockers — discovering at Phase 3 kick-off that the cooling period compliance review was never initiated adds 2–4 weeks to the timeline. |
| **Probability** | High |
| **P Numeric** | 3 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 9 |
| **Severity** | Critical |
| **Owner** | Program Manager |
| **Mitigation** | BL-090: Assign a resolution deadline to each OQ within 2 business days of this document being published. OQ-003 deadline: before Phase 3 kick-off. OQ-007 deadline: before Phase 9 kick-off (requires 8+ week lead time for legal review). OQ-005/OQ-011: resolved via ARCH-013/ARCH-014 recording. Add OQ deadlines to the RELEASE_GATES.md gate checklists. |
| **Contingency** | If an OQ deadline is missed and it blocks a phase gate, immediately escalate to the Program Manager and identify the resolution path. If the OQ cannot be resolved before the phase gate, either descope the dependent functionality or accept the blocker risk explicitly in PROJECT_DECISIONS.md. |
| **Status** | Open |
| **Review Date** | 2026-06-23 (48-hour action — OQ deadline assignment) |

---

### R-025

| Field | Value |
|-------|-------|
| **Risk ID** | R-025 |
| **Category** | Governance |
| **Description** | TRACEABILITY_MATRIX.md and PROJECT_MASTER_REGISTER.md have no mandatory update gate in the Definition of Done for Phases 3–10. Based on past behavior (Phase 2 produced 33 defects without any of them appearing in the traceability matrix), developers under schedule pressure will skip governance document updates. By Phase 7, the traceability matrix will reference Phase 2 state and be useless as an audit tool. This directly violates GG-004 and GG-005. |
| **Probability** | High |
| **P Numeric** | 3 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Program Manager + Governance Lead |
| **Mitigation** | BL-088 and BL-089: Add "Update TRACEABILITY_MATRIX.md" and "Update PROJECT_MASTER_REGISTER.md" as explicit criteria 11 and 12 in the Definition of Done for every phase (Phases 3–10). Program Manager verifies these are updated as part of gate evaluation. |
| **Contingency** | If either document becomes stale (e.g., last updated 2+ phases ago), conduct an emergency governance update before the next phase gate. Assign a Governance Lead hour-block at the start of each phase to pre-populate the expected updates. |
| **Status** | Open |
| **Review Date** | 2026-07-11 (Phase 3 DoD update) |

---

### R-026

| Field | Value |
|-------|-------|
| **Risk ID** | R-026 |
| **Category** | Governance |
| **Description** | Phase 2 currently has 7 of 10 Definition of Done criteria unmet. There is a risk that schedule pressure causes the team to declare Phase 2 "complete" before all 10 criteria are satisfied, and begin Phase 3 work. This would mean Phase 3 is implemented on top of a broken Phase 2 foundation — broken tests, wrong field names, and an incorrect TCC formula. When the Phase 2 defects are eventually fixed, Phase 3 code may need to be reworked to match the corrected model interfaces. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Program Manager |
| **Mitigation** | GATE-P2 is a hard gate: all 10 Phase 2 DoD criteria must be verified with specific commands before Phase 3 begins. The gate checklist is documented in RELEASE_GATES.md §2. Program Manager and Architect must both sign off. No exceptions. |
| **Contingency** | If Phase 3 has already begun on a defective Phase 2 foundation, immediately pause Phase 3, complete Phase 2 remediation, and audit Phase 3 work to date for compatibility with the corrected models. Treat any Phase 3 rework as a new REM item. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (GATE-P2) |

---

### R-027

| Field | Value |
|-------|-------|
| **Risk ID** | R-027 |
| **Category** | Governance |
| **Description** | There is no formal risk escalation process (GG-011). 13 risks in this register and the existing PROJECT_MASTER_REGISTER.md have no defined triggers for escalation from Open to Escalated. A risk that moves from Low probability to High probability during Phase 5 (e.g., R-022 historical file memory exhaustion is discovered to affect more users than expected) will not be noticed until it causes a failure. No one is assigned to monitor risk probability changes between phase gates. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Program Manager |
| **Mitigation** | Define escalation triggers for each Critical and High risk in the Risk Review Process section (Section 10 of this document). Add a 15-minute risk review to every phase gate meeting. If a risk's probability changes from Low to Medium, or Medium to High, the Owner must notify the Program Manager within 24 hours. |
| **Contingency** | If an unmonitored risk fires and causes a phase failure, add it to the post-mortem action items. Document what signal would have predicted the escalation and add that signal as an escalation trigger in this document. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (first gate review) |

---

## 4. Architecture Risks

Architecture risks are risks that an approved architecture decision is violated, misimplemented, or undone by a later developer — producing correctness, maintainability, or reproducibility failures.

---

### R-028

| Field | Value |
|-------|-------|
| **Risk ID** | R-028 |
| **Category** | Architecture |
| **Description** | ARCH-005 mandates core/ never imports from app/, and utils/ never imports from core/ or app/. There is no CI linting check enforcing this (GG-002, AG-001). A developer in Phase 5 or Phase 6 who needs a utility function from app/ will be tempted to add an import rather than refactor. A single circular import can cause Python to silently load an incomplete module, producing AttributeError at runtime rather than at import time. The defect may be invisible during unit testing if only isolated modules are tested. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | BL-006: Implement CI import linting before Phase 3 begins. Acceptable: pylint-import-hierarchy plugin or a custom script that greps for `^from app` and `^import app` in core/ and utils/ directories and fails CI. Add pre-commit hook for the same check. |
| **Contingency** | If a circular import is introduced and detected (AttributeError at runtime or circular import warning), immediately identify and refactor the offending module. Do not merge the fix until the CI import check is also added in the same PR. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (before Phase 3 begins) |

---

### R-029

| Field | Value |
|-------|-------|
| **Risk ID** | R-029 |
| **Category** | Architecture |
| **Description** | ARCH-013 specifies alphabetical trigger name as tiebreak when two TriggerConfigs have identical priority for the same user. This decision is architecturally sound but non-obvious: a user who configures two triggers with the same priority expecting them to apply equally will get a deterministic but alphabetically-biased result that may not reflect intent. A future developer who reviews audience_manager.py and considers the tiebreak "wrong" may change the sort order, breaking TC-AUD-003 (determinism test) and re-opening CB-001. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Architect |
| **Mitigation** | Add a prominent comment above the tiebreak sort in audience_manager.py: `# ARCH-013: Alphabetical trigger name tiebreak when priorities are equal. See PROJECT_DECISIONS.md. Do not change without a formal architecture amendment.` TC-AUD-003 must be present in the test suite as a regression guard. |
| **Contingency** | If the tiebreak is changed and TC-AUD-003 fails, the CI gate catches it before merge. The Developer must file a formal amendment to ARCH-013 via the PROJECT_DECISIONS.md amendment process before the change can be accepted. |
| **Status** | Open |
| **Review Date** | 2026-07-11 (Phase 3 audience_manager.py implementation) |

---

### R-030

| Field | Value |
|-------|-------|
| **Risk ID** | R-030 |
| **Category** | Architecture |
| **Description** | ARCH-009 prohibits pd.to_excel() in all export functions. No automated test currently asserts this (AG-002). A Phase 8 developer who is unfamiliar with the prohibition may use pd.to_excel() for convenience — it produces valid Excel files and passes functional tests. The violation would be undetected until the CI grep check is added. If pd.to_excel() is used for any of the 7 workbooks, it introduces a hidden performance dependency that was explicitly rejected during architecture. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | Add CI grep check before Phase 8 begins: `grep -rn "pd\.to_excel" engagement_data_generator/ --include="*.py"` fails if any hits. Add Phase 8 unit test that monkeypatches pd.to_excel() and asserts it is never called during any export invocation (AG-002 closure). |
| **Contingency** | If pd.to_excel() is found in Phase 8 code after merge, replace with openpyxl.Workbook() pattern immediately. The change is mechanical (same data, different write mechanism) and requires < 1 day. |
| **Status** | Open |
| **Review Date** | 2026-09-10 (Phase 8 start) |

---

### R-031

| Field | Value |
|-------|-------|
| **Risk ID** | R-031 |
| **Category** | Architecture |
| **Description** | Python's built-in hash() is non-deterministic across processes (its seed is randomized at Python startup since Python 3.3). SIM-019 explicitly prohibits hash() for user seed generation, mandating hashlib.md5 instead. There is no CI grep check enforcing this prohibition (AG-007). A developer in Phase 5 or later who writes a utility function using hash() for any purpose (not necessarily seed generation) may accidentally use it in a context where reproducibility is required. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer |
| **Mitigation** | Add CI grep check before Phase 3: `grep -rPn "\bhash\(" engagement_data_generator/ --include="*.py" | grep -v hashlib` fails if any hits. Add pre-commit hook for the same. Add a comment in utils/schema_validator.py above the hashlib.md5 call: `# SIM-019: Never use Python's built-in hash() — it is non-deterministic across processes.` |
| **Contingency** | If hash() is introduced and detected by the grep check, replace with hashlib.md5 or hashlib.sha256 depending on the use case. Add a test asserting the seed value is consistent across two process invocations with the same input. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (before Phase 3 begins) |

---

### R-032

| Field | Value |
|-------|-------|
| **Risk ID** | R-032 |
| **Category** | Architecture |
| **Description** | Profile evolution without an RNG state snapshot makes multi-run campaigns non-reproducible. If a user runs the simulation twice with the same historical state file, the RNG for profile evolution (Highly_Engaged, Moderate, Passive, Dormant transitions) will produce different results because the per-user seed only controls the initial placement, not the sequence of future transitions. Users expecting identical outputs from identical inputs will be surprised, and may incorrectly attribute the difference to a bug. |
| **Probability** | High |
| **P Numeric** | 3 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Architect + Product Owner |
| **Mitigation** | Document V1 reproducibility limitation clearly: "Two runs with the same trigger file and historical state file will produce identical engagement totals and identical user assignments, but individual user behavior profiles may differ due to RNG sequence variance." Add this language to the V1 release notes and Screen 8 tooltip. BL-022 (RNG snapshot) is the V2 resolution. |
| **Contingency** | If users report reproducibility failures as a bug post-V1, publish a knowledge base article explaining the design. Accelerate BL-022 into V2. For users who require exact reproducibility, document that saving the simulation date as a fixed constant in the config is sufficient for single-run reproducibility. |
| **Status** | Open |
| **Review Date** | 2026-10-12 (V1 release notes review) |

---

### R-033

| Field | Value |
|-------|-------|
| **Risk ID** | R-033 |
| **Category** | Architecture |
| **Description** | The weekly reset boundary uses d.weekday() == 0 (Monday, ISO 8601). US pharma marketing calendars use Sunday-start weeks. If the target user base operates on Sunday-start, the weekly fatigue counter resets one day later than expected. An HCP who received their weekly cap on Sunday will appear to have available capacity on Monday when the counter resets, but the user's intended week has not ended. This is a compliance risk (COMP-004) as well as an architecture risk. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Architect + Product Owner |
| **Mitigation** | BL-074: Obtain stakeholder confirmation of the target market's week-start convention before Phase 6 begins. If Sunday-start is required, add `week_start_day: str = "monday"` as a Category B field to ConfigRegistry before Phase 6. The Phase 6 fatigue engine reads the field and adjusts the reset condition accordingly. |
| **Contingency** | If Phase 6 is implemented with Monday reset before the stakeholder confirmation is obtained, a post-Phase-6 change to support Sunday reset requires a new ConfigRegistry field plus a Phase 6 re-test. Add 2–3 days to the timeline if this path is taken. |
| **Status** | Open |
| **Review Date** | 2026-08-10 (Phase 6 start) |

---

## 5. Testing Risks

Testing risks are risks that the test suite fails to detect defects, provides false confidence in correctness, or lacks coverage of critical behaviors.

---

### R-034

| Field | Value |
|-------|-------|
| **Risk ID** | R-034 |
| **Category** | Testing |
| **Description** | TC-AUD-003 is the definitive ARCH-013 gate: run audience_manager.resolve() twice with the same data in different row orders and assert identical output. If this test is not written before Phase 3 is completed, there is no automated guard against a row-order-dependent implementation. If TC-AUD-003 is written after implementation, it may reveal that the implementation has order dependencies (e.g., relying on the order of rows in the input DataFrame rather than the canonical sort chain). Fixing a row-order dependency in audience_manager.py after Phase 4 has been built on top of it is a significant rework. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer |
| **Mitigation** | TC-AUD-003 must be written as an acceptance criterion before Phase 3 coding begins on audience_manager.py. The test is specified in PHASE_3_ARCHITECTURE_DECISIONS.md §5 as: "Call resolve() twice with same data in different row orders; assert output DataFrames are identical." This test must pass before Phase 3 gate. |
| **Contingency** | If TC-AUD-003 fails after implementation, identify where order-dependency exists in the sort chain. The fix is to add `.reset_index(drop=True).sort_values(...)` as the first operation in resolve() rather than trusting input order. Rerun all 14 TC-AUD tests after the fix. |
| **Status** | Open |
| **Review Date** | 2026-07-11 (Phase 3 completion) |

---

### R-035

| Field | Value |
|-------|-------|
| **Risk ID** | R-035 |
| **Category** | Testing |
| **Description** | Phase 7 (Validation Engine) requires a minimum of 50 test cases across 35 rules. 18 of the 35 rules (HR-010, HR-011, HR-014, SR-001–SR-004, SR-009–SR-019) have no specification in any reviewed document — their requirement coverage, evaluation logic, and enabling conditions are unknown until Validation_Rules_Catalog.md is read. If the catalog reveals that these 18 rules require complex multi-condition evaluation logic, the 50-test minimum may be insufficient to cover all required cases, and defective validation rules will pass the gate. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Architect + Lead Engineer |
| **Mitigation** | BL-080: Read Validation_Rules_Catalog.md before Phase 7 begins (hard gate per RELEASE_GATES.md §7.1). After reading, reassess the minimum test count per rule based on actual rule complexity. If the 18 unspecified rules each require 3–5 test cases, the minimum test count for Phase 7 should be 100–140, not 50. Update RELEASE_GATES.md §7.3 accordingly. |
| **Contingency** | If Validation_Rules_Catalog.md reveals rules with more complexity than expected, extend the Phase 7 timeline by the number of additional test days required (estimate 1 day per 10 additional tests). Do not ship Phase 7 with a test suite that covers fewer than 90% of rule evaluation paths. |
| **Status** | Open |
| **Review Date** | 2026-08-28 (before Phase 7 start) |

---

### R-036

| Field | Value |
|-------|-------|
| **Risk ID** | R-036 |
| **Category** | Testing |
| **Description** | Phase 10 integration tests may pass functional correctness but miss performance regressions because no explicit SLA thresholds are defined yet (OQ-001 unresolved). Without a performance SLA, integration tests pass even if a 50K-user run takes 45 minutes. V1 releases with an undocumented and unacceptable run time. Users discover the performance issue post-release. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer + Product Owner |
| **Mitigation** | BL-083: Resolve OQ-001 (max trigger file size and SLA) before Phase 5 benchmarks (BL-044). Record the SLA in PROJECT_DECISIONS.md. Add explicit `@pytest.mark.benchmark` SLA tests to Phase 10: assert 1K-user run < T1 seconds, 10K < T2 seconds, 50K < T3 seconds. Fail the Phase 10 gate if SLA thresholds are breached. |
| **Contingency** | If Phase 10 reveals SLA violations, identify the slowest pipeline stage via profiling, apply targeted optimization (vectorize or chunk the bottleneck), and rerun benchmarks. Do not cap V1 at a smaller scale as a first response — optimize first. |
| **Status** | Open |
| **Review Date** | 2026-10-05 (Phase 10 completion) |

---

### R-037

| Field | Value |
|-------|-------|
| **Risk ID** | R-037 |
| **Category** | Testing |
| **Description** | There is no integration test for a two-run campaign scenario (carry-forward state). A user who runs the engine in Week 1, saves the UserState.xlsx, then runs again in Week 2 with the same UserState.xlsx file is the primary production use case. Without a Phase 10 test covering this exact scenario, backward-incompatible changes to the UserState schema between phases will not be detected until a user reports data loss. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | Phase 10 must include a test: `test_two_run_campaign_carry_forward()` — run the engine with a minimal trigger file, save UserState.xlsx, run again with the same UserState.xlsx and a new trigger file, assert that historical engagement counts from Run 1 are correctly read in Run 2. This test must use the actual openpyxl file read/write path, not mocked DataFrames. |
| **Contingency** | If the two-run test reveals a schema incompatibility between the Phase 8 write and the Phase 3 read, fix the schema immediately before V1 ships. This is a critical data integrity issue that cannot be deferred. |
| **Status** | Open |
| **Review Date** | 2026-10-05 (Phase 10 completion) |

---

### R-038

| Field | Value |
|-------|-------|
| **Risk ID** | R-038 |
| **Category** | Testing |
| **Description** | Phase 2 test helper remediation (REM-010 through REM-012) corrects known errors in make_state() and make_registry(). However, the corrected helpers may contain additional undetected issues: for example, make_registry() may not populate all required fields added by REM-004 (scoring weights, frequency_max). Tests that use make_registry() as a fixture will pass even if the registry has default values for these fields, which means behavior-engine tests in Phase 5 may not be exercising the full ConfigRegistry interface. |
| **Probability** | Low |
| **P Numeric** | 1 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 2 |
| **Severity** | Low |
| **Owner** | Lead Engineer |
| **Mitigation** | After completing REM-010 through REM-013, audit make_state() and make_registry() to confirm they use all canonical field names and provide non-default values for at least the critical fields. Add a docstring to each helper listing the fields it sets explicitly and the fields it relies on defaults for. |
| **Contingency** | If Phase 5 tests fail because make_registry() does not provide scoring weight fields, update the helper and rerun Phase 5 tests. The fix is straightforward and takes less than 1 hour. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (REM-013 completion) |

---

### R-039

| Field | Value |
|-------|-------|
| **Risk ID** | R-039 |
| **Category** | Testing |
| **Description** | The Coverage ≥ 90% gate (Phase 2 DoD criterion, GATE-P2, and all subsequent gates) is currently verified manually. Without a CI coverage gate (`--fail-under=90`), a developer can merge a phase deliverable with 75% coverage if no one runs the coverage report manually. As phases accumulate and the codebase grows, uncovered branches in core modules (capacity_row.py, audience_manager.py, behavior_engine.py) could hide defects that are only triggered in edge-case scenarios. |
| **Probability** | High |
| **P Numeric** | 3 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Lead Engineer |
| **Mitigation** | BL-007: Add `addopts = --cov=models --cov=utils --cov=core --cov-fail-under=90` to pyproject.toml before Phase 3 begins. The CI pipeline runs pytest with this flag on every PR merge. Any phase deliverable that drops coverage below 90% in any target module fails CI automatically. |
| **Contingency** | If coverage drops below 90% in a specific module after a merge, create a dedicated test-coverage issue and resolve it before the next phase gate. Treat it as a P1 defect — it does not block the current phase but blocks the next phase gate. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (Phase 2 remediation target — add to pyproject.toml) |

---

## 6. Documentation Risks

Documentation risks are risks that critical specifications are missing, ambiguous, or inconsistent with implementation — causing developers to build the wrong thing, validators to test the wrong behavior, or users to misunderstand the tool.

---

### R-040

| Field | Value |
|-------|-------|
| **Risk ID** | R-040 |
| **Category** | Documentation |
| **Description** | 18 of the 35 validation rules required for Phase 7 (HR-010, HR-011, HR-014, SR-001–SR-004, SR-009–SR-019) have no specification in any reviewed document. Their requirement IDs, evaluation logic, enabling conditions, and test cases are unknown. Validation_Rules_Catalog.md contains the specifications but was not included in the Phase 2 review. If Phase 7 planning begins without reading the catalog, rules will be invented by the developer rather than specified by the requirements, and the resulting validation engine will not enforce the intended business rules. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Architect |
| **Mitigation** | BL-080: Hard gate in RELEASE_GATES.md §7.1 — Validation_Rules_Catalog.md must be read and all 35 rules must be added to TRACEABILITY_MATRIX.md Section 6 before Phase 7 coding begins. This is an absolute prerequisite. The Architect must certify this is done before Phase 7 kick-off. |
| **Contingency** | If Phase 7 has begun without reading the catalog, immediately pause implementation, read the catalog, and audit the rules already implemented for consistency with the actual specifications. Any rules that were invented rather than specified must be redesigned before Phase 7 testing begins. |
| **Status** | Open |
| **Review Date** | 2026-08-28 (before Phase 7 kick-off) |

---

### R-041

| Field | Value |
|-------|-------|
| **Risk ID** | R-041 |
| **Category** | Documentation |
| **Description** | The SR-020 Composite Realism Score thresholds (≥ 85 = Excellent, ≥ 70 = Acceptable, < 70 = Below Threshold) are specified but not derived from any empirical pharma engagement data. The thresholds are engineering estimates. A simulation that produces highly unrealistic engagement patterns (e.g., 99% of users engaging on Day 1) may receive a score of 88 (Excellent) because the formula weights are tuned to the default behavior profiles. Conversely, a simulation with realistic but unusual parameters may receive a score of 65 (Below Threshold) despite being correct. |
| **Probability** | High |
| **P Numeric** | 3 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Analytics + Architect |
| **Mitigation** | BL-042 (RE-001) and BL-043 (RE-002): Complete statistical validation research before Phase 7 ships. Validate SR-020 formula and thresholds against real pharma engagement benchmarks. If benchmarks are not available before Phase 7, add a disclaimer to the SR-020 output in SimulationReport: "Realism score thresholds are preliminary and subject to calibration." |
| **Contingency** | If the thresholds prove misleading post-V1, publish revised thresholds as a V1.1 patch to the SR-020 formula. Add a calibration override to ConfigRegistry (SR-020 threshold fields) so power users can set their own thresholds based on historical data. |
| **Status** | Open |
| **Review Date** | 2026-08-28 (before Phase 7 ships) |

---

### R-042

| Field | Value |
|-------|-------|
| **Risk ID** | R-042 |
| **Category** | Documentation |
| **Description** | Users interacting with Screen 7 (TER/TCC Display) are highly likely to confuse TER (Trigger Engagement Rate — a reporting KPI) with TCC (Trigger Capacity Consumption — the engine driver). TER uses a cumulative denominator; TCC uses a windowed denominator. A user who sees TER = 12% and TCC = 15% and interprets them as measuring the same thing will adjust the target engagement rate in the wrong direction. This is a product UX and documentation risk that directly affects the usefulness of the generated data. |
| **Probability** | High |
| **P Numeric** | 3 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Product Owner + Lead Engineer |
| **Mitigation** | Phase 9 Screen 7 must display TER and TCC in separate, clearly labeled columns with plain-English sub-labels. Add tooltips: "TER (Trigger Engagement Rate): Cumulative reporting metric. Does not drive the engine." and "TCC (Trigger Capacity Consumption): Engine driver. Controls how many users can engage per simulation period." Reference CHG-026 (separate TER/TCC display columns) in Phase 9 acceptance criteria. |
| **Contingency** | If user feedback post-V1 reveals persistent confusion, add a "How to read this screen" help modal to Screen 7 with a worked numerical example showing TER and TCC with the same input data. |
| **Status** | Open |
| **Review Date** | 2026-09-26 (Phase 9 Screen 7 implementation) |

---

### R-043

| Field | Value |
|-------|-------|
| **Risk ID** | R-043 |
| **Category** | Documentation |
| **Description** | The config file format documentation (user-facing JSON schema documentation) must match the actual ConfigRegistry field names after Phase 2 remediation. The remediation renames 7 fields and adds 6 new fields. If the user-facing documentation is not updated simultaneously, users who follow the documented config format will receive a TypeError or SchemaVersionError when loading the config, with no actionable error message explaining which field names changed. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | After REM-005 through REM-008, update the config file documentation (if it exists) and the sample config JSON (BL-004) to match the canonical ConfigRegistry field names. Before Phase 9, Screen 3 (Config Editor) must validate config field names against ConfigRegistry and surface a clear error with the correct field name when a wrong name is used. |
| **Contingency** | If a user is stuck with a wrong config field name, the SchemaVersionError message should include a link to the canonical field list or a migration hint. Add a "Did you mean: default_vendor?" suggestion to the ConfigError message for commonly mistyped legacy field names. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (post-remediation config doc update) |

---

### R-044

| Field | Value |
|-------|-------|
| **Risk ID** | R-044 |
| **Category** | Documentation |
| **Description** | PROJECT_DECISIONS.md is the highest-authority document in the project. There is no formal amendment workflow (GG-009) — no approver roles, no SLA, and no definition of breaking vs. non-breaking change. A developer could add an amendment that contradicts a prior decision (e.g., amending ARCH-009 to allow pd.to_excel() for "performance reasons") without any architectural review. Conflicting decisions both in force simultaneously undermine the authority hierarchy. |
| **Probability** | Low |
| **P Numeric** | 1 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 2 |
| **Severity** | Low |
| **Owner** | Governance Lead |
| **Mitigation** | BL-067 (GG-009): Document the amendment process before Phase 3 begins. Required: (1) Proposer writes a formal amendment with rationale, (2) Chief Architect reviews within 48 hours, (3) If breaking change: Product Owner also approves, (4) Superseded decision is marked AMENDED with a reference to the new decision. |
| **Contingency** | If a conflicting amendment is added without review, identify the conflict, resolve it in a joint Architect + Product Owner session, and mark one decision as SUPERSEDED. Add the conflict to the post-mortem and tighten the amendment process. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (process documentation target) |

---

## 7. Compliance Risks

Compliance risks are risks of legal, regulatory, or organizational policy violations that could expose the organization to liability, require product redesign, or prevent V1 release.

---

### R-045

| Field | Value |
|-------|-------|
| **Risk ID** | R-045 |
| **Category** | Compliance |
| **Description** | OQ-007 (legal review of synthetic HCP engagement data) has not been initiated. The tool generates data designed to resemble HCP engagement records. In some jurisdictions (EU GDPR, US state privacy laws, FDA 21 CFR Part 11), generating synthetic records that could be mistaken for real HCP records may trigger obligations even when no real data is used. If the legal review is not completed before Phase 9 UI implementation, the UI will be built without the legally required disclaimer, data classification warning, or consent flow — requiring retrospective redesign of Screens 1, 2, and potentially 8. Legal review typically requires 4–8 weeks; initiating it after Phase 7 is too late. |
| **Probability** | High |
| **P Numeric** | 3 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 9 |
| **Severity** | Critical |
| **Owner** | Program Manager + Legal |
| **Mitigation** | BL-071: Initiate the legal review immediately. Do not wait for Phase 7. The review should be initiated within 5 business days of this document being published. Assign a legal contact, provide the product description, the data model, and a sample of the generated output files. Hard gate in RELEASE_GATES.md §9: legal review must be complete before Phase 9 begins. Hard gate in RELEASE_GATES.md §11: written, signed, dated legal clearance document required before GATE-V1 passes. |
| **Contingency** | If the legal review identifies obligations (e.g., a mandatory "No Real HCP Data" agreement, an audit log requirement, or geographic restrictions), implement the required changes as P0 Phase 9 backlog items. If constraints are severe enough to require re-architecture, this is a V1 scope decision that must involve the Product Owner. |
| **Status** | Open — START IMMEDIATELY |
| **Review Date** | 2026-06-28 (5-business-day action: initiation confirmed) |

---

### R-046

| Field | Value |
|-------|-------|
| **Risk ID** | R-046 |
| **Category** | Compliance |
| **Description** | The default cooling period of 90 days has not been reviewed against pharma marketing compliance norms in the target market (FDA voluntary guidelines, PhRMA Code on Interactions, EFPIA Guidelines for EU). Some markets require a minimum gap between HCP outreach cycles. If the required minimum exceeds 90 days and Phase 3 is implemented before the review, the default must be changed post-implementation — requiring a ConfigRegistry default update, audience_manager.py logic review, and Phase 3 re-test. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | High |
| **I Numeric** | 3 |
| **Risk Score** | 6 |
| **Severity** | High |
| **Owner** | Program Manager + Legal / Medical Affairs |
| **Mitigation** | BL-072: Initiate the cooling period compliance review before Phase 3 begins. It is a shorter review than OQ-007 and can be completed within 1–2 weeks. If the required minimum is > 90 days, update the ConfigRegistry default before Phase 3 implements the Audience Manager. Hard gate per GATE-P3: cooling period review must be complete before Phase 3 gate passes. |
| **Contingency** | If Phase 3 is implemented before the review and the default must change, update ConfigRegistry.cooling_period_days default, rerun the Audience Manager acceptance tests with the new default, and add a CHANGELOG note documenting the compliance-driven default change. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (before Phase 3 kick-off) |

---

### R-047

| Field | Value |
|-------|-------|
| **Risk ID** | R-047 |
| **Category** | Compliance |
| **Description** | The UI currently has no prominently displayed warning that the tool must not be run against real HCP identifiers. Assumption A-011 requires this warning, but it has not been designed or implemented. If a user uploads a real HCP list (even accidentally), the tool processes it as synthetic data, producing output files that reference real HCP identifiers as engagement records. If those output files are shared, the organization has effectively generated a synthetic engagement profile for identifiable individuals, which may constitute a HIPAA or GDPR violation. |
| **Probability** | Low |
| **P Numeric** | 1 |
| **Impact** | Critical |
| **I Numeric** | 4 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer + Legal |
| **Mitigation** | BL-073: Phase 9 Screen 1 (Home) and Screen 2 (Upload Files) must display a prominent, non-dismissable data classification banner: "This tool is designed for use with SYNTHETIC (non-identifiable) data only. Do not upload files containing real patient, HCP, or personally identifiable information." Banner text reviewed by Legal before Phase 9 implementation. |
| **Contingency** | If a compliance incident occurs before the banner is implemented, immediately halt use of the tool with any data until the banner is in place. If a real HCP file was processed, consult Legal immediately for breach assessment. This risk, while low probability, is irreversible once it fires. |
| **Status** | Open |
| **Review Date** | 2026-09-26 (Phase 9 start — Screen 1 and Screen 2 implementation) |

---

### R-048

| Field | Value |
|-------|-------|
| **Risk ID** | R-048 |
| **Category** | Compliance |
| **Description** | The Python version requirement (3.11+) is not pinned in pyproject.toml (COMP-005). Users who install the tool on Python 3.9 or 3.10 may encounter silent failures with walrus operators, match/case statements, `zoneinfo` imports, or `tomllib` usage. The failures may produce incorrect output without raising a clear error, depending on whether the affected code path is executed. A user who generates engagement data on Python 3.9 and receives a result may trust the output even if it is corrupted. |
| **Probability** | Medium |
| **P Numeric** | 2 |
| **Impact** | Medium |
| **I Numeric** | 2 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Lead Engineer |
| **Mitigation** | BL-075: Add `python_requires = ">=3.11"` to pyproject.toml and `[project]` section of pyproject.toml before Phase 3. Add a startup check in app/__init__.py: `if sys.version_info < (3, 11): sys.exit("Error: Python 3.11 or higher is required.")` Update README with clear installation prerequisite. |
| **Contingency** | If a user reports incorrect output on Python < 3.11, advise them to upgrade Python and rerun. If a syntax error is raised on < 3.11, the startup check will surface it with a clear error message before any data is processed. |
| **Status** | Open |
| **Review Date** | 2026-07-02 (alongside Phase 2 remediation — pyproject.toml update) |

---

### R-049

| Field | Value |
|-------|-------|
| **Risk ID** | R-049 |
| **Category** | Compliance |
| **Description** | The legal review (OQ-007) may identify constraints that require changes to V1 features that have already been implemented by the time the review completes. If the legal review is initiated at Phase 7 (the minimum initiation time in RELEASE_GATES.md §7) and takes 6–8 weeks, results arrive at Phase 9. At that point, Phases 3–8 are complete. If the review requires changes to qualifying actions, data retention, or output file content, rework will affect the core pipeline (Phases 5–8), not just the UI. The cost of late legal review is far higher than early legal review. |
| **Probability** | Low |
| **P Numeric** | 1 |
| **Impact** | Critical |
| **I Numeric** | 4 |
| **Risk Score** | 4 |
| **Severity** | Medium |
| **Owner** | Program Manager + Legal |
| **Mitigation** | Legal review must be initiated immediately (R-045 mitigation). The goal is to receive findings before Phase 5 begins, allowing any required design changes to be incorporated into the Behavior Engine rather than retrofitted. If legal findings require pipeline changes, treat them as P0 backlog items for the relevant phase. |
| **Contingency** | If late legal findings require core pipeline changes after Phase 5 is complete, conduct an impact assessment: identify every module affected, estimate rework, update the timeline, and communicate to stakeholders. Do not ship V1 with unresolved legal findings of any severity. |
| **Status** | Open |
| **Review Date** | 2026-06-28 (legal review initiation) |

---

## 8. Risk Summary Dashboard

### Risk Inventory by Category

| Category | Total | Critical | High | Medium | Low |
|----------|-------|---------|------|--------|-----|
| Technical | 17 | 2 | 7 | 7 | 1 |
| Performance | 5 | 0 | 3 | 1 | 1 |
| Governance | 5 | 1 | 3 | 1 | 0 |
| Architecture | 6 | 0 | 3 | 3 | 0 |
| Testing | 6 | 0 | 3 | 2 | 1 |
| Documentation | 5 | 0 | 3 | 1 | 1 |
| Compliance | 5 | 2 | 1 | 2 | 0 |
| **TOTAL** | **49** | **5** | **23** | **17** | **4** |

### Risk Severity Matrix

| Risk ID | Category | Probability | Impact | Score | Severity |
|---------|----------|------------|--------|-------|---------|
| R-001 | Technical | High | High | 9 | **Critical** |
| R-002 | Technical | High | High | 9 | **Critical** |
| R-008 | Technical | Medium | High | 6 | **High** |
| R-014 | Technical | Medium | High | 6 | **High** |
| R-015 | Technical | Medium | High | 6 | **High** |
| R-016 | Technical | Medium | High | 6 | **High** |
| R-003 | Technical | High | Medium | 6 | **High** |
| R-005 | Technical | Medium | Medium | 4 | Medium |
| R-007 | Technical | Medium | Medium | 4 | Medium |
| R-009 | Technical | Medium | Medium | 4 | Medium |
| R-010 | Technical | Medium | Medium | 4 | Medium |
| R-011 | Technical | Medium | Medium | 4 | Medium |
| R-012 | Technical | Medium | Medium | 4 | Medium |
| R-017 | Technical | Medium | Medium | 4 | Medium |
| R-004 | Technical | Low | High | 3 | Medium |
| R-006 | Technical | Low | Medium | 2 | Low |
| R-013 | Technical | Low | Medium | 2 | Low |
| R-018 | Performance | Medium | High | 6 | **High** |
| R-019 | Performance | Medium | High | 6 | **High** |
| R-020 | Performance | Medium | High | 6 | **High** |
| R-022 | Performance | Low | High | 3 | Medium |
| R-021 | Performance | Low | Medium | 2 | Low |
| R-024 | Governance | High | High | 9 | **Critical** |
| R-023 | Governance | Medium | High | 6 | **High** |
| R-025 | Governance | High | Medium | 6 | **High** |
| R-026 | Governance | Medium | High | 6 | **High** |
| R-027 | Governance | Medium | Medium | 4 | Medium |
| R-031 | Architecture | Medium | High | 6 | **High** |
| R-032 | Architecture | High | Medium | 6 | **High** |
| R-033 | Architecture | Medium | Medium | 4 | Medium |
| R-028 | Architecture | Medium | Medium | 4 | Medium |
| R-029 | Architecture | Medium | Medium | 4 | Medium |
| R-030 | Architecture | Medium | Medium | 4 | Medium |
| R-034 | Testing | Medium | High | 6 | **High** |
| R-036 | Testing | Medium | High | 6 | **High** |
| R-039 | Testing | High | Medium | 6 | **High** |
| R-035 | Testing | Medium | Medium | 4 | Medium |
| R-037 | Testing | Medium | Medium | 4 | Medium |
| R-038 | Testing | Low | Medium | 2 | Low |
| R-040 | Documentation | Medium | High | 6 | **High** |
| R-041 | Documentation | High | Medium | 6 | **High** |
| R-042 | Documentation | High | Medium | 6 | **High** |
| R-043 | Documentation | Medium | Medium | 4 | Medium |
| R-044 | Documentation | Low | Medium | 2 | Low |
| R-045 | Compliance | High | High | 9 | **Critical** |
| R-046 | Compliance | Medium | High | 6 | **High** |
| R-047 | Compliance | Low | Critical | 4 | Medium† |
| R-048 | Compliance | Medium | Medium | 4 | Medium |
| R-049 | Compliance | Low | Critical | 4 | Medium† |

†R-047 and R-049 are scored Medium by formula but carry Critical-impact scenarios at low probability. They must be managed as High-severity risks from a risk management perspective despite the numeric score.

### Critical Risks — Immediate Action Required

| Risk ID | Description | Owner | Action Deadline |
|---------|-------------|-------|----------------|
| R-001 | Phase 2 critical defects (ImportError/TypeError/broken tests) block all work | Lead Engineer | 2026-07-02 |
| R-002 | TCC-001 silent floor-rounding causes systematic engagement under-generation | Lead Engineer | 2026-07-02 |
| R-024 | OQ deadlines unassigned — compliance reviews will miss blocking phase deadlines | Program Manager | 2026-06-23 |
| R-045 | OQ-007 legal review not initiated — must precede Phase 9 by 8+ weeks | Program Manager | 2026-06-28 |

---

## 9. Critical and High Risk Action Plan

Actionable steps for all Critical and High severity risks, ordered by deadline.

| Action | Risk(s) | Owner | Deadline | Blocks |
|--------|---------|-------|----------|--------|
| Assign resolution deadlines to OQ-001 through OQ-014 | R-024 | Program Manager | 2026-06-23 | All phase gates |
| Initiate OQ-007 legal review (contact legal team) | R-045, R-049 | Program Manager | 2026-06-28 | Phase 9, GATE-V1 |
| ~~Execute REM-001/REM-002 (fix ImportErrors)~~ **DONE — 2026-06-21** | R-001 | Lead Engineer | ~~2026-07-01~~ COMPLETE | All Phase 2 tests — ImportErrors eliminated |
| ~~Execute REM-003 (fix int() → math.ceil())~~ **DONE — 2026-06-22** | R-002 | Lead Engineer | ~~2026-07-01~~ COMPLETE | TCC correctness — math.ceil() applied; 16 tests passing |
| Execute REM-005 through REM-013 (remaining Phase 2 remediation) | R-001, R-008, R-017 | Lead Engineer | 2026-07-02 | GATE-P2 *(REM-004 fields+validator DONE 2026-06-22; config_loader.py parsing in REM-005–008)* |
| Add CI grep checks (iterrows, pd.to_excel, hash()) | R-031, R-030, R-039 | Lead Engineer | 2026-07-02 | GATE-P2 |
| Add CI coverage gate (--fail-under=90) to pyproject.toml | R-039 | Lead Engineer | 2026-07-02 | GATE-P2 |
| Record ARCH-013/ARCH-014/CFG-NEW-001 in PROJECT_DECISIONS.md | R-023 | Architect | 2026-07-02 | GATE-P2 |
| Add governance update requirements to Phase 3+ DoD | R-025 | Program Manager | 2026-07-02 | All phase gates |
| Verify Phase 2 DoD (all 10 criteria) before Phase 3 kick-off | R-026 | Program Manager + Architect | 2026-07-02 | GATE-P2 |
| Initiate OQ-003 cooling period compliance review | R-046 | Program Manager | 2026-07-02 | GATE-P3 |
| Add CI import linting for ARCH-005 | R-028 | Lead Engineer | 2026-07-07 | Phase 3 onwards |
| Add ConfigRegistry scoring weights sum validator | R-008 | Lead Engineer | 2026-07-07 | Phase 5 |
| Write TC-AUD-003 determinism test as Phase 3 acceptance criterion | R-034 | Lead Engineer | 2026-07-07 | Phase 3 DoD |
| Add Move-On-Click (C-001) ordering test as Phase 4 acceptance criterion | R-014 | Lead Engineer | 2026-07-14 | Phase 4 DoD |
| Add Weekly Reset (C-003) test and comment for Phase 6 | R-015 | Lead Engineer | 2026-08-01 | Phase 6 DoD |
| Run Phase 5 benchmarks (BL-044) and resolve OQ-001 | R-018, R-019, R-020, R-036 | Lead Engineer | 2026-08-07 | GATE-P5 |
| Resolve DD-008 (streaming vs. batch write) before Phase 8 | R-019 | Architect | 2026-09-01 | Phase 8 design |
| Read Validation_Rules_Catalog.md before Phase 7 planning | R-040 | Architect | 2026-08-28 | GATE-P7 |
| Validate SR-020 thresholds against empirical data | R-041 | Analytics | 2026-08-28 | Phase 7 DoD |
| Implement TER/TCC labels and tooltips on Screen 7 | R-042 | Lead Engineer | 2026-09-26 | Phase 9 DoD |
| Implement legal data classification banner on Screens 1 and 2 | R-047 | Lead Engineer + Legal | 2026-09-26 | Phase 9 DoD |
| Add Phase 10 SLA benchmark tests | R-036 | Lead Engineer | 2026-10-01 | GATE-P10 |
| Add Phase 10 two-run campaign carry-forward test | R-037 | Lead Engineer | 2026-10-01 | GATE-P10 |
| Obtain written legal clearance for V1 release | R-045, R-049 | Legal + Program Manager | 2026-10-05 | GATE-V1 |

---

## 10. Risk Review Process

### Review Cadence

| Review Point | Trigger | Required Actions |
|-------------|---------|-----------------|
| Immediate (within 24 hours) | Any new risk with Score ≥ 9 is identified | Owner notified; action plan assigned within 24 hours; Program Manager briefed |
| Phase Start | Beginning of each phase | Review all Open risks; confirm owners; update Review Dates; confirm Critical risk mitigations are in progress |
| Phase Gate | End-of-phase gate evaluation | Update status of all risks; close risks whose exposure window has passed; re-score any risks that changed during the phase; add new risks discovered |
| V1 Pre-Release | When all Phase 10 tests pass | Final review: confirm all Critical risks are Closed or Monitoring; confirm all Compliance risks are resolved; sign off by Lead Engineer + Architect + Program Manager |
| Post-Release Retrospective | After V1 ships | Identify which risks fired; analyze missed mitigations; incorporate learnings into V2 risk register |

### Risk Escalation Triggers

A risk must be escalated (Status changed to Escalated) and the Owner must notify the Program Manager within 24 hours if:

- Probability increases: Low → Medium (e.g., legal review initiation is now overdue, making R-045 probability rise from High to Certain)
- Impact increases: any risk where a new piece of information increases impact (e.g., BL-044 benchmark reveals SLA will be breached, raising R-036 impact from High to Critical)
- A mitigation is no longer available (e.g., the CI import linting tool chosen for R-028 is unavailable — alternative must be identified)
- Two or more Medium risks combine into a compound risk with High or Critical exposure
- A risk fires in production (V1 is live and a risk condition is observed)

### Escalation Owners

| Phase Range | Escalation Approver |
|-------------|---------------------|
| Phases 2–6 | Lead Engineer + Chief Architect |
| Phases 7–9 | Lead Engineer + Chief Architect + Program Manager |
| Phase 10 + V1 Release | Lead Engineer + Chief Architect + Program Manager + Product Owner |
| Compliance risks (any phase) | Program Manager + Legal (immediately) |

### Adding New Risks

When a new risk is identified:
1. Assign the next available R-ID (current highest: R-049; next available: R-050).
2. Score the risk using the framework in Section 0 (Probability × Impact).
3. Determine the appropriate category and add to the correct section.
4. Add the risk to PROJECT_MASTER_REGISTER.md §15 simultaneously.
5. If the risk is Critical, trigger the immediate escalation process above.
6. If the risk affects a phase gate, update RELEASE_GATES.md accordingly.

### Closing Risks

A risk may be closed when:
- Its exposure window has permanently passed (e.g., R-006 is Closed after pandas/numpy versions are pinned and a CI compatibility test is passing)
- Its mitigation has eliminated the risk condition (e.g., R-031 is Closed after the CI hash() grep check is added and passing)
- The phase it was associated with is complete and the risk did not fire

Closed risks are not deleted. They remain in this register as a historical record.

**Next Available R-ID: R-050**

---

### Risk Register Statistics

| Metric | Value |
|--------|-------|
| Total Risks | 49 |
| Critical (Score 9–12) | 5 (R-001, R-002, R-024, R-045 + indirect R-047, R-049) |
| High (Score 6–8) | 23 |
| Medium (Score 3–5) | 17 |
| Low (Score 1–2) | 4 |
| Open | 49 |
| Active (Mitigations In Progress) | 0 |
| Monitoring | 0 |
| Closed | 2 (R-002 RESOLVED 2026-06-22; R-008 RESOLVED 2026-06-22) |
| Immediate Actions Required (≤ 5 business days) | 2 (R-001, R-024, R-045 — R-002 RESOLVED) |

---

*PROJECT_RISK_REGISTER.md — Version 1.0*
*Engagement Data Generator v1.0*
*Chief Architect / Program Manager / Risk Owner*
*2026-06-21*

*This document is the single authoritative risk register.*
*All additions must be made here and in PROJECT_MASTER_REGISTER.md §15 simultaneously.*
*Next available R-ID: R-050*
*Review cadence: start and end of every phase gate per RELEASE_GATES.md.*
