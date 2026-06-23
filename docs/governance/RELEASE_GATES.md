# RELEASE GATES
# Engagement Data Generator — Version 1.0
# Mandatory Exit Criteria for Every Phase and the V1 Release

**Document Version:** 1.0
**Prepared:** 2026-06-21
**Role:** Chief Architect / Program Manager / Governance Owner
**Status:** ACTIVE — Governs all phase transitions from Phase 2 through V1 Release
**Authority:** This document is subordinate only to PROJECT_DECISIONS.md. Where a gate criterion conflicts with a decision in PROJECT_DECISIONS.md, the decision takes precedence. All other project documents are subordinate to this gate document.

**Enforcement Rule:**
> A phase may not begin until every criterion of the preceding phase's exit gate is satisfied and signed off. No exceptions. Partial gate passage does not permit partial phase start. The gate is binary: PASS or FAIL.

**Gate Sign-Off Authority:**
- Phase 2–6 exits: Lead Engineer + Chief Architect
- Phase 7–9 exits: Lead Engineer + Chief Architect + Program Manager
- Phase 10 exit / V1 Release: Lead Engineer + Chief Architect + Program Manager + Product Owner

---

## Table of Contents

1. Gate Structure and Conventions
2. Phase 2 Exit Gate — Core Data Models, Loaders, Utilities
3. Phase 3 Exit Gate — User State Manager + Audience Manager
4. Phase 4 Exit Gate — Journey Engine
5. Phase 5 Exit Gate — Behavior Engine
6. Phase 6 Exit Gate — Timing Engine
7. Phase 7 Exit Gate — Validation Engine
8. Phase 8 Exit Gate — Export Engine
9. Phase 9 Exit Gate — Streamlit UI + Run Controller
10. Phase 10 Exit Gate — Integration + End-to-End Testing
11. V1 Release Gate
12. Gate Status Dashboard

---

## 1. Gate Structure and Conventions

### Eight Categories Per Gate

Every gate contains exactly these eight categories, evaluated in the order listed:

| # | Category | Description |
|---|----------|-------------|
| 1 | Required Documents | Governance and design documents that must exist and be current before the gate is evaluated |
| 2 | Required Tests | Specific test files, test functions, and test types that must be present and passing |
| 3 | Required Coverage | Minimum pytest-cov coverage percentage for all modules introduced in this phase |
| 4 | Required Governance Updates | Updates to PROJECT_MASTER_REGISTER.md, PROJECT_CHANGE_LOG.md, and other governance registers |
| 5 | Required Traceability Updates | Updates to TRACEABILITY_MATRIX.md linking phase outputs to requirements and architecture decisions |
| 6 | Required Decision Updates | Architecture or business decisions that must be recorded in PROJECT_DECISIONS.md before the gate passes |
| 7 | Required Backlog Review | Items in PROJECT_BACKLOG.md that must be triaged, closed, or deferred before the gate passes |
| 8 | Required Risk Review | Risk register items that must be reviewed and either mitigated or formally accepted before the gate passes |

### Verification Commands

Each gate specifies the exact shell commands used to verify automated criteria. All commands are run from the project root. A gate does not pass until all commands exit 0.

### Gate Terminology

- **MUST** — hard requirement; gate fails if not met
- **MUST NOT** — hard prohibition; gate fails if violated
- **SHOULD** — strong recommendation; can be waived with documented Chief Architect approval and a corresponding backlog item
- **RESOLVED** — a decision or question has a recorded answer in PROJECT_DECISIONS.md
- **REVIEWED** — a risk or question has been assessed and a formal position recorded, even if unresolved

### Permanent Performance Constraints (Apply to Every Gate)

These constraints are checked at every gate via grep. A gate fails automatically if any constraint is violated in production code.

```bash
# No iterrows() in production code
grep -rn "iterrows" engagement_data_generator/ --include="*.py"
# Expected: zero hits

# No pd.to_excel() in production code
grep -rn "pd\.to_excel" engagement_data_generator/ --include="*.py"
# Expected: zero hits

# No hash() without hashlib in production code
grep -rPn "\bhash\(" engagement_data_generator/ --include="*.py" | grep -v hashlib
# Expected: zero hits

# No TODO, FIXME, or HACK in any production file
grep -rn "TODO\|FIXME\|HACK" engagement_data_generator/ --include="*.py"
# Expected: zero hits
```

These four checks are referred to collectively as the **Performance Constraint Verification** block and are required at every gate without re-stating them in full.

---

## 2. Phase 2 Exit Gate
### Core Data Models, Input Loader, Config Loader, Utilities

**Gate ID:** GATE-P2
**Predecessor:** Phase 1 (project skeleton — already passed)
**Unlocks:** Phase 3 — User State Manager + Audience Manager
**Estimated Evaluation Time:** Half day

---

### 2.1 Required Documents

All documents must exist at the path shown, be non-stub, and reflect the current state of Phase 2 code.

| Document | Path | Requirement |
|----------|------|-------------|
| Phase_2_Implementation.md | uploads/ | Base canonical document used for implementation (NOT Part1/Part2 variants) — must be the source of truth for all Phase 2 module specifications |
| PHASE_2_REMEDIATION_PLAN.md | outputs/ | Must exist; all 33 defects listed; status of each item must be current |
| PHASE_2_EXECUTION_PLAN.md | outputs/ | Must exist; all 18 REM actions listed |
| PROJECT_DECISIONS.md | outputs/ | Must contain ARCH-013 and ARCH-014 (trigger and segment tiebreak rules — required before Phase 3 can be unlocked by this gate) |
| PHASE_3_ARCHITECTURE_DECISIONS.md | outputs/ | Must exist; DD-013 and DD-014 analysis complete |

**Document Content Checks:**
- PHASE_2_REMEDIATION_PLAN.md: every defect from MM-001 through DOC-005 marked RESOLVED with a commit reference
- PROJECT_DECISIONS.md: `reconcile_creative_affinity_columns` referenced only in `utils/excel_utils.py`, never in `utils/schema_validator.py` (DOC-001 resolution verified)

---

### 2.2 Required Tests

| Test File | Must Exist | Must Pass | Key Functions Covered |
|-----------|------------|-----------|----------------------|
| tests/test_models/test_user_state.py | YES | YES | is_in_journey_cooling(), get_creative_affinity(), engagement_score boundaries |
| tests/test_models/test_config_registry.py | YES | YES | __post_init__ validators, scoring weight sum, end_before_start, empty ads, empty triggers |
| tests/test_models/test_capacity_row.py | YES | YES | compute() ceil, is_at_capacity(), utilization_pct() zero-division guard |
| tests/test_models/test_trigger_config.py | YES | YES | valid construction, all __post_init__ validation paths (rate < 0, rate > 1, pct > 100, priority < 1) |
| tests/test_models/test_segment_config.py | YES | YES | valid construction, all __post_init__ validation paths |
| tests/test_models/test_ad_config.py | YES | YES | is_email_channel(), is_whatsapp_channel() |
| tests/test_utils/test_schema_validator.py | YES | YES | is_qualifying_action() for all channel/action combinations |
| tests/test_core/test_input_loader.py | YES | YES | load_trigger_file(), load_historical_file() dedup, qualifying filter, Campaign_ID default |
| tests/test_core/test_config_loader.py | YES | YES | load_config_from_dict() with valid config, error paths for _REQUIRED_TOP_KEYS |

**Specific Named Test Functions That Must Exist:**

```
tests/test_models/test_capacity_row.py::test_compute_ceil_not_floor
  — asserts ceil(101 * 0.10) = 11, not 10. This is the TCC-001 regression gate.

tests/test_models/test_config_registry.py::test_scoring_weights_do_not_sum_to_one
  — asserts ConfigError raised when weights sum != 1.0.

tests/test_core/test_input_loader.py::test_dedup_applied_before_filters
  — asserts historical file deduplication runs before campaign and qualifying filters.
```

**Verification Command:**
```bash
pytest tests/test_models/ tests/test_utils/ tests/test_core/ -x --tb=short -v
# Expected: 0 failed, 0 errors
# Both test_trigger_config.py and test_segment_config.py must appear in collected tests
```

---

### 2.3 Required Coverage

```bash
pytest tests/test_models/ tests/test_utils/ tests/test_core/ \
    --cov=models \
    --cov=utils \
    --cov=core/input_loader \
    --cov=core/config_loader \
    --cov-fail-under=90 \
    --cov-report=term-missing
# Expected: exit 0; no module below 90%
```

| Module | Minimum Coverage |
|--------|-----------------|
| models/ (all files) | 90% |
| utils/ (all files) | 90% |
| core/input_loader.py | 90% |
| core/config_loader.py | 90% |

---

### 2.4 Required Governance Updates

| Register | Item | Required Update |
|----------|------|-----------------|
| PROJECT_MASTER_REGISTER.md — Defects Register | All 33 defects (MM-001 through DOC-005) | Status = RESOLVED; commit reference populated |
| PROJECT_MASTER_REGISTER.md — Remediation Register | All 18 REM items (REM-001 through REM-018) | Status = RESOLVED |
| PROJECT_MASTER_REGISTER.md — Critical Blockers | CB-001, CB-002 (DD-013, DD-014) | Status = RESOLVED — see ARCH-013, ARCH-014 |
| PROJECT_MASTER_REGISTER.md — Open Decisions | DD-013, DD-014 | Status = RESOLVED |
| PROJECT_MASTER_REGISTER.md — Open Questions | OQ-005, OQ-011 | Status = RESOLVED — see ARCH-013, ARCH-014 |
| PROJECT_MASTER_REGISTER.md — Phase Readiness | Phase 3 row | Readiness updated to reflect decision blockers cleared |
| PROJECT_CHANGE_LOG.md | Phase 2 remediation changes CHG-028 through CHG-035 | All marked APPROVED with implementation date |

---

### 2.5 Required Traceability Updates

| Document | Section | Required Update |
|----------|---------|-----------------|
| TRACEABILITY_MATRIX.md | Section 3 — Phase Matrix, Phase 2 row | Status = COMPLETE; all defects resolved |
| TRACEABILITY_MATRIX.md | Section 3 — Phase Matrix, Phase 3 row | Status = UNBLOCKED (architecture decisions resolved) |
| TRACEABILITY_MATRIX.md | Section 4 — Architecture Matrix | ARCH-013 and ARCH-014 rows added |
| TRACEABILITY_MATRIX.md | Section 9 — Gap Analysis | DD-013 and DD-014 gaps marked RESOLVED |

---

### 2.6 Required Decision Updates

| Decision | Status Required | Notes |
|----------|----------------|-------|
| ARCH-013 (alphabetical trigger tiebreak) | APPROVED and recorded in PROJECT_DECISIONS.md | Must be present before Phase 3 may begin |
| ARCH-014 (segment follows winning trigger) | APPROVED and recorded in PROJECT_DECISIONS.md | Must be present before Phase 3 may begin |
| CFG-NEW-001 (strict_priority_validation reserved field) | APPROVED and recorded | Adds bool field to ConfigRegistry |

---

### 2.7 Required Backlog Review

| Backlog Item | Required Action |
|-------------|-----------------|
| BL-006 (CI import linting for ARCH-005) | Triage: assign to phase, estimate, or formally defer with reason |
| BL-007 (CI coverage gate in pyproject.toml) | Triage: assign to phase, estimate, or formally defer with reason |
| BL-040 (scoring weight constants in utils/constants.py) | RESOLVED — constants added as part of REM-004 |
| All BL items tagged Phase 2 | Verify each is either CLOSED or has a correct target phase assignment |

---

### 2.8 Required Risk Review

| Risk | Required Action |
|------|-----------------|
| R-001 (iterrows() ban enforcement) | Verify grep check passes. Mark MITIGATED if CI grep gate added; ACCEPTED if deferred to Phase CI work. |
| R-007 (TCC-001 silent under-counting) | Mark RESOLVED — math.ceil() fix verified by test_compute_ceil_not_floor. |
| R-013 (file-order non-determinism in audience resolution) | Mark RESOLVED — ARCH-013 alphabetical rule eliminates file-order dependency. |

---

## 3. Phase 3 Exit Gate
### User State Manager + Audience Manager

**Gate ID:** GATE-P3
**Predecessor:** Phase 2 Exit Gate (GATE-P2) — MUST PASS first
**Unlocks:** Phase 4 — Journey Engine
**Files Gated:** core/user_state_manager.py, core/audience_manager.py, tests/unit/test_user_state_manager.py, tests/unit/test_audience_manager.py

---

### 3.1 Required Documents

| Document | Requirement |
|----------|-------------|
| outputs/Implementation_Plan.md, Section 5 (Phase 3) | Must be current; acceptance criteria consulted during implementation |
| PROJECT_DECISIONS.md | Must contain ARCH-013, ARCH-014; DD-012 must be RESOLVED or formally deferred (see 3.6) |
| USER_STATE_DICTIONARY.md | Must have been read and all 29 UserState fields confirmed implemented |

---

### 3.2 Required Tests

| Test File | Key Functions Required |
|-----------|----------------------|
| tests/unit/test_user_state_manager.py | initialize() new user, initialize() existing user carry-forward, update_user() immutability, finalize_state() as_of_date, Campaign_ID always = config.campaign_id |
| tests/unit/test_audience_manager.py | TC-AUD-001 through TC-AUD-014 as specified in PHASE_3_ARCHITECTURE_DECISIONS.md Section 10 |

**Specific Named Test Functions That Must Exist:**

```
test_audience_manager.py::test_tiebreak_is_file_order_independent  (TC-AUD-003)
  — runs resolve() twice with same data in different row orders; asserts identical output.
  This is the definitive ARCH-013 determinism gate.

test_audience_manager.py::test_segment_follows_trigger_not_alphabet  (TC-AUD-009)
  — asserts segment from winning trigger row, not alphabetically first segment across all rows.
  This is the definitive ARCH-014 semantic coherence gate.

test_user_state_manager.py::test_campaign_id_always_from_config
  — asserts UserState.Campaign_ID = config.campaign_id regardless of prior state values.
```

**Eligibility Classification Tests (all four states must be covered):**
```
classify_eligibility() must have explicit tests for each of:
  New: Journey_Status = Not_Started AND no prior state
  Active: Journey_Status = Active
  Cooling: Cooling_Period_End is not null AND as_of_date < Cooling_Period_End
  Re-Entry: Journey_Status = Completed AND as_of_date >= Cooling_Period_End
  Skipped: User has no valid trigger assignment after resolution
```

**Verification Command:**
```bash
pytest tests/unit/test_user_state_manager.py tests/unit/test_audience_manager.py -x --tb=short -v
# Expected: 0 failed, 0 errors; both TC-AUD-003 and TC-AUD-009 present and passing
```

---

### 3.3 Required Coverage

```bash
pytest tests/unit/test_user_state_manager.py tests/unit/test_audience_manager.py \
    --cov=core/user_state_manager \
    --cov=core/audience_manager \
    --cov-fail-under=90
# Expected: exit 0
```

| Module | Minimum Coverage |
|--------|-----------------|
| core/user_state_manager.py | 90% |
| core/audience_manager.py | 90% |

**Additionally:** Performance Constraint Verification block must pass (no iterrows, no pd.to_excel, no hash, no TODO/FIXME/HACK) for the two new modules.

---

### 3.4 Required Governance Updates

| Register | Required Update |
|----------|-----------------|
| PROJECT_MASTER_REGISTER.md — Phase Readiness | Phase 3 = COMPLETE; Phase 4 = UNBLOCKED (or BLOCKED with named remaining blocker) |
| PROJECT_MASTER_REGISTER.md — Open Questions | OQ-003 (90-day cooling period compliance) must be marked REVIEWED with a formal risk position — not necessarily resolved, but assessed by Legal/Medical Affairs |
| PROJECT_CHANGE_LOG.md | Phase 3 completion entry added |

---

### 3.5 Required Traceability Updates

| Document | Section | Required Update |
|----------|---------|-----------------|
| TRACEABILITY_MATRIX.md | Phase Matrix, Phase 3 row | Status = COMPLETE |
| TRACEABILITY_MATRIX.md | Phase Matrix, Phase 4 row | Status updated |
| TRACEABILITY_MATRIX.md | Architecture Matrix | ARCH-013 and ARCH-014 rows: Implementation Phase = Phase 3, Status = IMPLEMENTED |
| TRACEABILITY_MATRIX.md | Validation Coverage Matrix | Audience resolution rules linked to test coverage |

---

### 3.6 Required Decision Updates

| Decision | Status Required |
|----------|----------------|
| DD-012 (terminal journey event on completion) | Must be RESOLVED before Phase 3 gate passes, because the Journey Engine (Phase 4) cannot be designed without this decision. Options: (A) No terminal event; (B) "Journey_Completed" action in EngagementEvents; (C) Flag in UserState only. Record as ARCH-NEW in PROJECT_DECISIONS.md. |
| OQ-003 (90-day cooling period compliance) | Must be REVIEWED — a formal written position from Legal/Medical Affairs, even if the position is "no concern identified." |

---

### 3.7 Required Backlog Review

| Item | Required Action |
|------|-----------------|
| All BL items tagged Phase 3 | Verify each is CLOSED or correctly re-assigned |
| BL-006 (CI import linting) | Must have a target phase or formal deferral decision |
| Any new BL items discovered during Phase 3 | Added to PROJECT_BACKLOG.md with priority and target phase |

---

### 3.8 Required Risk Review

| Risk | Required Action |
|------|-----------------|
| R-003 (OQ-003 cooling period legal compliance) | Update with Legal review outcome. If still open, escalate to P0 and document acceptance. |
| R-006 (audience resolution non-determinism) | Mark RESOLVED — ARCH-013 tiebreak verified by TC-AUD-003. |
| Any new risks discovered during Phase 3 | Added to Risk Register with probability, impact, and mitigation plan |

---

## 4. Phase 4 Exit Gate
### Journey Engine

**Gate ID:** GATE-P4
**Predecessor:** Phase 3 Exit Gate (GATE-P3) — MUST PASS first
**Unlocks:** Phase 5 — Behavior Engine
**Files Gated:** core/journey_engine.py, tests/unit/test_journey_engine.py

---

### 4.1 Required Documents

| Document | Requirement |
|----------|-------------|
| PROJECT_DECISIONS.md | DD-012 recorded as ARCH-NEW (terminal journey event decision) |
| Implementation_Plan.md, Phase 4 section | Consulted; acceptance criteria satisfied |

---

### 4.2 Required Tests

| Test Area | Test Requirements |
|-----------|------------------|
| C-001 (Move On Click exclusive) | Test that when click-advance fires, duration check is skipped entirely on the same day. Explicit test: user on a 1-day ad receives both a click and reaches duration — only one advance occurs, not two. |
| C-003 (Weekly reset on Monday ISO boundary) | Test that counters reset on Monday (weekday() == 0), NOT on Sunday (isoweekday() == 7). Test that reset fires BEFORE any processing on the first day of a new week. |
| Journey completion | Test that Journey_Status = Completed after final ad; Cooling_Period_End is set; user does not re-enter journey during cooling. |
| Journey continuation | Test that an Active user from prior state continues their journey uninterrupted; Current_Ad and Days_In_Ad are preserved; trigger/segment may update but journey fields are not reset. |
| Ad advancement by duration | Test that user advances to next ad after Days_In_Current_Ad >= ad.duration. |
| Ad advancement by click | Test that a Click event advances user to next ad regardless of remaining duration (C-001). |
| Journey_Status transitions | All four transitions must have tests: Not_Started→Active, Active→Active, Active→Completed, Completed→Cooling (Re-Entry wait). |

**Specific Named Test Functions That Must Exist:**
```
test_journey_engine.py::test_move_on_click_skips_duration_check
  — verifies C-001: a 1-day ad with a click does not double-advance.

test_journey_engine.py::test_weekly_reset_fires_on_monday_not_sunday
  — verifies C-003: weekday() == 0 is the boundary, not isoweekday() == 7.

test_journey_engine.py::test_active_journey_continues_across_runs
  — verifies journey continuation: Current_Ad, Days_In_Ad, Journey_Start_Date unchanged.
```

**Verification Command:**
```bash
pytest tests/unit/test_journey_engine.py -x --tb=short -v
# Expected: 0 failed, 0 errors
```

---

### 4.3 Required Coverage

| Module | Minimum Coverage |
|--------|-----------------|
| core/journey_engine.py | 90% |

All journey status transitions must appear in the coverage report as covered.

---

### 4.4 Required Governance Updates

| Register | Required Update |
|----------|-----------------|
| PROJECT_MASTER_REGISTER.md — Phase Readiness | Phase 4 = COMPLETE; Phase 5 blocker analysis updated |
| PROJECT_CHANGE_LOG.md | Phase 4 completion entry added |
| PROJECT_MASTER_REGISTER.md — Open Decisions | DD-012 marked RESOLVED with reference to ARCH-NEW decision ID |

---

### 4.5 Required Traceability Updates

| Document | Section | Required Update |
|----------|---------|-----------------|
| TRACEABILITY_MATRIX.md | Phase Matrix, Phase 4 row | Status = COMPLETE |
| TRACEABILITY_MATRIX.md | Business Rule Matrix | C-001, C-003 rows: Implementation Phase = Phase 4, Test Coverage = named test functions |
| TRACEABILITY_MATRIX.md | Phase Matrix, Phase 5 row | Prerequisites updated |

---

### 4.6 Required Decision Updates

| Decision | Status Required |
|----------|----------------|
| DD-012 | RESOLVED and in PROJECT_DECISIONS.md before this gate is evaluated — it was a Phase 3 gate prerequisite (Section 3.6) and must now be confirmed implemented |
| Any Phase 4 design decisions discovered during implementation | Recorded in PROJECT_DECISIONS.md before gate evaluation |

---

### 4.7 Required Backlog Review

| Item | Required Action |
|------|-----------------|
| All BL items tagged Phase 4 | CLOSED or re-assigned |
| BL items related to journey engine edge cases discovered during implementation | Added with priority |

---

### 4.8 Required Risk Review

| Risk | Required Action |
|------|-----------------|
| R-002 (C-001 double-advance) | Mark RESOLVED — test_move_on_click_skips_duration_check covers this path |
| R-004 (C-003 wrong weekday boundary) | Mark RESOLVED — test_weekly_reset_fires_on_monday_not_sunday covers this |
| Any new risks discovered during Phase 4 | Added to Risk Register |

---

## 5. Phase 5 Exit Gate
### Behavior Engine

**Gate ID:** GATE-P5
**Predecessor:** Phase 4 Exit Gate (GATE-P4) — MUST PASS first
**Unlocks:** Phase 6 — Timing Engine
**Files Gated:** core/behavior_engine.py, tests/unit/test_behavior_engine.py

---

### 5.1 Required Documents

| Document | Requirement |
|----------|-------------|
| Implementation_Plan.md, Phase 5 section | Consulted; composite scoring formula SIM-001 fully implemented |
| PROJECT_DECISIONS.md | SIM-001 (composite scoring formula), SIM-002 (weights Category B), SIM-019 (per-user seed via hashlib.md5) all confirmed implemented |

---

### 5.2 Required Tests

| Test Area | Test Requirements |
|-----------|------------------|
| SIM-019 (per-user seed) | Test that `hashlib.md5(user_id.encode()).hexdigest()` is the seed source. Test that two calls with the same user_id produce identical random sequences. Test that different user_ids produce different sequences. |
| Composite scoring formula | Test that all five components (engagement_score, profile_component, creative_affinity, channel_affinity, reach_recency_normalized) contribute to the composite score. Test boundary: if all weights are 0 except one, only that component influences the score. |
| Scoring weight sum constraint | Test that ConfigRegistry.__post_init__ raises ConfigError when weights do not sum to 1.0 (regression from REM-004 — must still pass here). |
| Behavior profiles | All four profiles must have explicit tests: Highly_Engaged (2.0x multiplier, 10% population target), Moderate (1.0x, 40%), Passive (0.4x, 35%), Dormant (0.1x, 15%). |
| Creative affinity update | Test that a Click event increases Creative_Affinity by affinity_boost_on_click. Test that a non-engaging impression decreases it by affinity_decay_no_engage. Test floor (0.0) and ceiling (1.0) are enforced. |
| Jitter | Test that jitter is in [0.0, 0.05] range. Test that jitter is different across two runs for the same user on the same day (probabilistic — use large sample). |
| float32 storage | Test that engagement_score, all Creative_Affinity_* columns, and channel affinity columns are dtype float32 in the output DataFrame. |

**Specific Named Test Functions That Must Exist:**
```
test_behavior_engine.py::test_seed_is_hashlib_md5_not_python_hash
  — explicitly asserts that Python hash() is NOT used; hashlib.md5 IS used.
  Must verify the seed formula: int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 2**32

test_behavior_engine.py::test_composite_score_uses_all_five_components
  — verifies SIM-001: each component has a non-zero weight by default.

test_behavior_engine.py::test_affinity_respects_floor_and_ceiling
  — verifies floor 0.0 and ceiling 1.0 are enforced via np.clip() or equivalent.

test_behavior_engine.py::test_engagement_score_columns_are_float32
  — verifies ARCH-011 dtype requirement.
```

**Verification Command:**
```bash
pytest tests/unit/test_behavior_engine.py -x --tb=short -v
# Expected: 0 failed, 0 errors; seed test and dtype test must appear
```

---

### 5.3 Required Coverage

| Module | Minimum Coverage |
|--------|-----------------|
| core/behavior_engine.py | 90% |

All four behavior profiles must appear as covered branches in the coverage report.

---

### 5.4 Required Governance Updates

| Register | Required Update |
|----------|-----------------|
| PROJECT_MASTER_REGISTER.md — Phase Readiness | Phase 5 = COMPLETE |
| PROJECT_MASTER_REGISTER.md — Open Questions | OQ-001 (max trigger file size / run-time SLA) must be REVIEWED: an informal benchmark run performed and results recorded. A formal SLA decision is not required at this gate, but "untested" is not acceptable. |
| PROJECT_CHANGE_LOG.md | Phase 5 completion entry |

---

### 5.5 Required Traceability Updates

| Document | Section | Required Update |
|----------|---------|-----------------|
| TRACEABILITY_MATRIX.md | Phase Matrix, Phase 5 row | Status = COMPLETE |
| TRACEABILITY_MATRIX.md | Architecture Matrix | SIM-001 and SIM-019 rows: Implementation Phase = Phase 5, Status = IMPLEMENTED |
| TRACEABILITY_MATRIX.md | Business Rule Matrix | SIM-002 (weights Category B) confirmed implemented |

---

### 5.6 Required Decision Updates

| Decision | Status Required |
|----------|----------------|
| OQ-001 (SLA benchmark) | REVIEWED — informal benchmark results recorded. If benchmark reveals SLA violation, DD-NEW must be opened for architecture remediation before Phase 6. |
| OQ-013 (behavior profile defaults validated against real pharma HCP populations) | REVIEWED — position documented. If the defaults are not validated, record as a known limitation in the Risk Register. |
| Any Phase 5 design decisions discovered during implementation | Recorded in PROJECT_DECISIONS.md |

---

### 5.7 Required Backlog Review

| Item | Required Action |
|------|-----------------|
| BL-010 (scoring weight fields on ConfigRegistry) | CLOSED — implemented in Phase 2 remediation and confirmed in Phase 5 |
| BL-040 (scoring weight named constants) | CLOSED — implemented in Phase 2 remediation |
| All BL items tagged Phase 5 | CLOSED or re-assigned |

---

### 5.8 Required Risk Review

| Risk | Required Action |
|------|-----------------|
| R-005 (non-deterministic behavior engine due to hash() misuse) | Mark RESOLVED — test_seed_is_hashlib_md5_not_python_hash confirms correct seed. |
| R-008 (behavior profile population drift) | Updated with Phase 5 test results. If SR-007 (segment distribution ±10% tolerance) cannot be met, open a new risk item. |
| OQ-001 SLA risk | If benchmark reveals violation, add as R-NEW with priority P1 before gate passes. |

---

## 6. Phase 6 Exit Gate
### Timing Engine

**Gate ID:** GATE-P6
**Predecessor:** Phase 5 Exit Gate (GATE-P5) — MUST PASS first
**Unlocks:** Phase 7 — Validation Engine
**Files Gated:** core/timing_engine.py, tests/unit/test_timing_engine.py

---

### 6.1 Required Documents

| Document | Requirement |
|----------|-------------|
| Implementation_Plan.md, Phase 6 section | Consulted; email timing model (day1/day2/day3 min/max) fully implemented |
| PROJECT_DECISIONS.md | All timing-related decisions implemented (email open window, fatigue counters, weekly reset timing) |

---

### 6.2 Required Tests

| Test Area | Test Requirements |
|-----------|------------------|
| Email open timing window | Test that email opens occur within the day1/day2/day3 min/max probability ranges from ChannelConfig. Test that no email open occurs after day 3 (the window closes). Test that probability draws use the per-user seed (deterministic for same user_id and same send date). |
| WhatsApp open timing | Test equivalent day-window behavior to email. |
| Display timing | Test that Display channel has no open event (only Click or Impression). |
| Fatigue counter enforcement | Test that a user who hits the weekly impression cap receives no further impressions that week. Test that fatigue counters reset on the ISO Monday boundary (aligns with C-003, already tested in Phase 4 — verify timing engine also resets). |
| Fatigue recovery | Test that after recovery_days have elapsed since fatigue threshold reached, user becomes eligible again. |
| Channel-specific timing rules | Test that email/WhatsApp multi-day open window does not apply to Display; Display events are same-day only. |

**Specific Named Test Functions That Must Exist:**
```
test_timing_engine.py::test_email_open_bounded_by_day_window
  — verifies open cannot occur after day3.

test_timing_engine.py::test_fatigue_counter_resets_on_iso_monday
  — verifies weekly fatigue reset aligns with C-003 boundary.

test_timing_engine.py::test_display_has_no_open_event
  — verifies Display channel cannot produce an Open action.
```

**Verification Command:**
```bash
pytest tests/unit/test_timing_engine.py -x --tb=short -v
```

---

### 6.3 Required Coverage

| Module | Minimum Coverage |
|--------|-----------------|
| core/timing_engine.py | 90% |

All channel types (Email, WhatsApp, Display — at minimum) must appear as covered branches.

---

### 6.4 Required Governance Updates

| Register | Required Update |
|----------|-----------------|
| PROJECT_MASTER_REGISTER.md — Phase Readiness | Phase 6 = COMPLETE |
| PROJECT_CHANGE_LOG.md | Phase 6 completion entry |

---

### 6.5 Required Traceability Updates

| Document | Section | Required Update |
|----------|---------|-----------------|
| TRACEABILITY_MATRIX.md | Phase Matrix, Phase 6 row | Status = COMPLETE |
| TRACEABILITY_MATRIX.md | Business Rule Matrix | Fatigue enforcement (C-003 weekly reset in timing context), email window rules — both marked IMPLEMENTED with test references |

---

### 6.6 Required Decision Updates

| Decision | Status Required |
|----------|----------------|
| DD-005 (performance benchmark — Phase 5 data now available) | REVIEWED: if Phase 5 benchmark revealed SLA concerns, DD-005 must be resolved before or during Phase 6. |
| Any Phase 6 timing design decisions | Recorded in PROJECT_DECISIONS.md |

---

### 6.7 Required Backlog Review

| Item | Required Action |
|------|-----------------|
| All BL items tagged Phase 6 | CLOSED or re-assigned |

---

### 6.8 Required Risk Review

| Risk | Required Action |
|------|-----------------|
| SLA risk (from Phase 5 OQ-001 benchmark) | If risk was opened, update with Phase 6 performance data. If timing engine adds significant overhead, escalate. |
| Any new risks from Phase 6 implementation | Added to Risk Register |

---

## 7. Phase 7 Exit Gate
### Validation Engine

**Gate ID:** GATE-P7
**Predecessor:** Phase 6 Exit Gate (GATE-P6) — MUST PASS first
**Unlocks:** Phase 8 — Export Engine
**Files Gated:** core/validation_engine.py, tests/unit/test_validation_engine.py
**Special Note:** Phase 7 is the highest-complexity gate. The Validation Engine implements 35 rules (15 hard, 20 soft) and CB-008 (Validation_Rules_Catalog.md review) must be complete before implementation begins.

---

### 7.1 Required Documents

| Document | Requirement |
|----------|-------------|
| uploads/Validation_Rules_Catalog.md | MUST have been read and all 35 rule specifications extracted BEFORE Phase 7 coding begins. If this document does not exist, Phase 7 cannot start. This is CB-008. |
| Implementation_Plan.md, Phase 7 section | Consulted; all 35 rules have acceptance criteria |
| PROJECT_DECISIONS.md | VAL-001 (hard rule FAIL blocks export) confirmed implemented |

---

### 7.2 Required Tests

| Test Requirement | Detail |
|------------------|--------|
| All 15 hard rules (HR-001 through HR-015) | Each hard rule must have at least one explicit FAIL test (input that triggers the rule) and one explicit PASS test (clean input). 15 × 2 = 30 minimum hard rule tests. |
| All 20 soft rules (SR-001 through SR-020) | Each soft rule must have at least one WARN test. 20 minimum soft rule tests. |
| VAL-001 gate | Test that any hard rule FAIL returns a ValidationResult with is_blocking=True. Test that soft rule WARN returns is_blocking=False. |
| No false positives | Test that a fully valid synthetic run produces zero hard rule FAILs and zero spurious soft rule WARNs. |
| Rule severity isolation | Test that a FAIL in HR-001 does not suppress reporting of a FAIL in HR-002 — all hard rule violations must be reported, not just the first. |

**Specific Named Test Functions That Must Exist:**
```
test_validation_engine.py::test_hard_rule_fail_is_blocking
  — verifies VAL-001: ValidationResult.is_blocking = True when any HR fires.

test_validation_engine.py::test_soft_rule_warn_is_not_blocking
  — verifies soft rules produce warnings, not blocks.

test_validation_engine.py::test_all_hard_rule_violations_reported
  — verifies all HR FAILs are collected, not just first.

test_validation_engine.py::test_clean_run_produces_no_violations
  — verifies no false positives on well-formed data.
```

**Verification Command:**
```bash
pytest tests/unit/test_validation_engine.py -x --tb=short -v
# Expected: 0 failed; at minimum 50 tests collected (30 HR + 20 SR)
```

---

### 7.3 Required Coverage

| Module | Minimum Coverage |
|--------|-----------------|
| core/validation_engine.py | 90% |

All 35 rule code paths (FAIL branch and PASS branch for HR; WARN branch and PASS branch for SR) must be covered.

---

### 7.4 Required Governance Updates

| Register | Required Update |
|----------|-----------------|
| PROJECT_MASTER_REGISTER.md — Critical Blockers | CB-008 (Validation_Rules_Catalog.md unread) | Status = RESOLVED |
| PROJECT_MASTER_REGISTER.md — Validation Gap Register | All 13 VG items (VG-001 through VG-013) reviewed; each either RESOLVED (rule now specified and implemented) or updated with current status |
| PROJECT_MASTER_REGISTER.md — Phase Readiness | Phase 7 = COMPLETE |
| PROJECT_CHANGE_LOG.md | Phase 7 completion entry |
| PROJECT_MASTER_REGISTER.md — Open Decisions | OQ-006 (publish SR-020 formula to users) must be REVIEWED — a written position recorded |

---

### 7.5 Required Traceability Updates

| Document | Section | Required Update |
|----------|---------|-----------------|
| TRACEABILITY_MATRIX.md | Phase Matrix, Phase 7 row | Status = COMPLETE |
| TRACEABILITY_MATRIX.md | Validation Coverage Matrix (Section 5) | All 35 rules: Status = IMPLEMENTED, Test Coverage = named test functions |
| TRACEABILITY_MATRIX.md | Requirement Matrix | All requirements mapped to validation rules must have IMPLEMENTED status |

---

### 7.6 Required Decision Updates

| Decision | Status Required |
|----------|----------------|
| DD-010 (Validation_Rules_Catalog.md machine-readable format) | REVIEWED — position recorded. If decision is to keep Markdown, document as deferred to V2. |
| DD-014 (OQ-014 — validation rules versioned independently) | REVIEWED — written position in PROJECT_DECISIONS.md |
| OQ-006 (SR-020 Composite Realism Score formula published to users) | RESOLVED — yes or no decision by Product Owner |

---

### 7.7 Required Backlog Review

| Item | Required Action |
|------|-----------------|
| All BL items tagged Phase 7 | CLOSED or re-assigned |
| Any validation rules that could not be fully specified from Validation_Rules_Catalog.md | New BL items created with rule IDs and open specification questions |

---

### 7.8 Required Risk Review

| Risk | Required Action |
|------|-----------------|
| CB-008 risk (18 unspecified validation rules) | RESOLVED if all 35 rules now specified and implemented; otherwise any remaining unspecified rules become R-NEW items |
| R-009 (validation engine false positive risk) | Updated with test_clean_run_produces_no_violations result |
| Legal review (OQ-007) | Status updated — if still open, escalate urgency as V1 release is now 3 phases away |

---

## 8. Phase 8 Exit Gate
### Export Engine

**Gate ID:** GATE-P8
**Predecessor:** Phase 7 Exit Gate (GATE-P7) — MUST PASS first
**Unlocks:** Phase 9 — Streamlit UI + Run Controller
**Files Gated:** core/export_engine.py, utils/excel_utils.py (finalized), tests/unit/test_export_engine.py

---

### 8.1 Required Documents

| Document | Requirement |
|----------|-------------|
| PROJECT_DECISIONS.md | ARCH-009 (openpyxl direct write) confirmed implemented; DD-008 (in-memory batch vs streaming write) RESOLVED |
| Implementation_Plan.md, Phase 8 section | All 7 output workbooks specified and implemented |

---

### 8.2 Required Tests

| Test Area | Test Requirements |
|-----------|------------------|
| openpyxl direct write | Test that all 7 output workbooks are written with openpyxl.Workbook() directly. Verify pd.to_excel() does not appear in export_engine.py (also caught by Performance Constraint Verification). |
| 7 output workbooks | Each workbook must have at least one test verifying: correct sheet names present, correct column headers, at least one data row written, file is a valid .xlsx. |
| ValidationResult gate | Test that when ValidationResult.is_blocking = True, export is halted and no output files are written. Test that when all rules pass, all 7 workbooks are created. |
| reconcile_creative_affinity_columns | Test that this function is called from excel_utils.py ONLY (not schema_validator.py). Test that columns present in prior state but absent from current config are preserved with a WARNING. Test that columns in current config but absent from prior state are inserted at 0.5. |
| Workbook data integrity | For at least one workbook, test round-trip: write data, read back with openpyxl, assert values match source DataFrame. |
| DD-008 implementation | Test matches the chosen option (in-memory batch or streaming append) per PROJECT_DECISIONS.md. |

**Specific Named Test Functions That Must Exist:**
```
test_export_engine.py::test_blocking_validation_halts_export
  — verifies no output files written when is_blocking = True.

test_export_engine.py::test_all_seven_workbooks_created_on_clean_run
  — verifies all 7 files exist after a successful run.

test_export_engine.py::test_creative_affinity_reconciliation_source_is_excel_utils
  — verifies reconcile_creative_affinity_columns is called from excel_utils.py.
```

**Verification Command:**
```bash
pytest tests/unit/test_export_engine.py -x --tb=short -v
# Expected: 0 failed, 0 errors

# Additionally: confirm pd.to_excel is absent from export_engine.py
grep -n "pd\.to_excel" engagement_data_generator/core/export_engine.py
# Expected: zero hits
```

---

### 8.3 Required Coverage

| Module | Minimum Coverage |
|--------|-----------------|
| core/export_engine.py | 90% |
| utils/excel_utils.py | 90% |

Both the blocking-halt path and the clean-export path must appear as covered branches.

---

### 8.4 Required Governance Updates

| Register | Required Update |
|----------|-----------------|
| PROJECT_MASTER_REGISTER.md — Open Decisions | DD-008 marked RESOLVED with chosen option and rationale |
| PROJECT_MASTER_REGISTER.md — Phase Readiness | Phase 8 = COMPLETE |
| PROJECT_CHANGE_LOG.md | Phase 8 completion entry |
| PROJECT_MASTER_REGISTER.md — Open Questions | OQ-004 (UserState.xlsx V1→V2 migration) must be REVIEWED — written position recorded, even if deferred to V2 |

---

### 8.5 Required Traceability Updates

| Document | Section | Required Update |
|----------|---------|-----------------|
| TRACEABILITY_MATRIX.md | Phase Matrix, Phase 8 row | Status = COMPLETE |
| TRACEABILITY_MATRIX.md | Architecture Matrix | ARCH-009 row: Status = IMPLEMENTED |

---

### 8.6 Required Decision Updates

| Decision | Status Required |
|----------|----------------|
| DD-008 (in-memory vs streaming write) | RESOLVED and recorded in PROJECT_DECISIONS.md before gate evaluation |
| OQ-004 (UserState.xlsx migration V1→V2) | REVIEWED — written position in PROJECT_DECISIONS.md or a new backlog item with clear deferral rationale |

---

### 8.7 Required Backlog Review

| Item | Required Action |
|------|-----------------|
| All BL items tagged Phase 8 | CLOSED or re-assigned |
| Any workbook formatting or schema issues discovered during export testing | New BL items created |

---

### 8.8 Required Risk Review

| Risk | Required Action |
|------|-----------------|
| R-010 (export engine performance with large datasets) | Updated with Phase 8 benchmark data. If batch write causes memory issues, revisit DD-008. |
| Legal review (OQ-007) | Status updated — if still open, this is now a hard pre-release gate item (2 phases remain) |

---

## 9. Phase 9 Exit Gate
### Streamlit UI + Run Controller

**Gate ID:** GATE-P9
**Predecessor:** Phase 8 Exit Gate (GATE-P8) — MUST PASS first
**Unlocks:** Phase 10 — Integration + End-to-End Testing
**Files Gated:** app/run_controller.py, app/ui.py (or equivalent), tests/unit/test_run_controller.py

---

### 9.1 Required Documents

| Document | Requirement |
|----------|-------------|
| Implementation_Plan.md, Phase 9 section | All UI screens and run_controller.run() function specified |
| PROJECT_DECISIONS.md | Any UI-level decisions recorded |

---

### 9.2 Required Tests

| Test Area | Test Requirements |
|-----------|------------------|
| run_controller.run() | Test that run() invokes all 11 pipeline stages in the correct order (ARCH-003). Test that a stage failure propagates correctly and subsequent stages are not invoked. |
| Config schema version check | Test that CFG-005 is enforced: a config dict with CONFIG_SCHEMA_VERSION != "2.0" raises SchemaVersionError before any pipeline stage runs. |
| Dry-run flag (if OQ-008 resolved as Yes) | If dry-run is implemented, test that no output files are written in dry-run mode; test that validation still runs. If OQ-008 resolved as No, test that no dry-run parameter exists on run(). |
| Progress indicators | Test (unit-level, mocked) that progress updates are emitted at each stage boundary. |
| Import tier compliance | Test that app/ never imports from core/ directly, except through run_controller. Enforced by: `grep -rn "from core" engagement_data_generator/app/ --include="*.py"` returning only run_controller imports. |

**Specific Named Test Functions That Must Exist:**
```
test_run_controller.py::test_pipeline_stages_invoked_in_order
  — verifies ARCH-003: all 11 stages called; order enforced.

test_run_controller.py::test_schema_version_mismatch_raises_before_pipeline
  — verifies CFG-005: SchemaVersionError raised on CONFIG_SCHEMA_VERSION != "2.0".

test_run_controller.py::test_stage_failure_halts_pipeline
  — verifies that an error in any stage does not silently continue to next stage.
```

**Verification Command:**
```bash
pytest tests/unit/test_run_controller.py -x --tb=short -v

# Import tier compliance check
grep -rn "^from core\|^import core" engagement_data_generator/app/ --include="*.py"
# Expected: only run_controller.py imports from core; no other app/ files import core/
```

---

### 9.3 Required Coverage

| Module | Minimum Coverage |
|--------|-----------------|
| app/run_controller.py | 90% |

Both the success path and the failure/abort path must be covered.

---

### 9.4 Required Governance Updates

| Register | Required Update |
|----------|-----------------|
| PROJECT_MASTER_REGISTER.md — Phase Readiness | Phase 9 = COMPLETE |
| PROJECT_MASTER_REGISTER.md — Open Questions | OQ-008 (dry-run flag) marked RESOLVED |
| PROJECT_MASTER_REGISTER.md — Open Questions | OQ-009 (data retention policy) must be REVIEWED |
| PROJECT_CHANGE_LOG.md | Phase 9 completion entry |
| PROJECT_MASTER_REGISTER.md — Open Questions | OQ-010 (compressed trigger file support) must be REVIEWED — final position for V1 |

---

### 9.5 Required Traceability Updates

| Document | Section | Required Update |
|----------|---------|-----------------|
| TRACEABILITY_MATRIX.md | Phase Matrix, Phase 9 row | Status = COMPLETE |
| TRACEABILITY_MATRIX.md | Requirement Matrix | All UI-level requirements (REQ entries related to app/) marked IMPLEMENTED |

---

### 9.6 Required Decision Updates

| Decision | Status Required |
|----------|----------------|
| OQ-008 (dry-run flag) | RESOLVED — yes or no; if yes, implemented and tested |
| OQ-009 (data retention policy) | REVIEWED — operational policy documented |
| OQ-010 (compressed trigger file support for V1) | RESOLVED — yes (implement) or no (backlog item for V2) |
| CFG-005 enforcement | CONFIRMED implemented in run_controller.py |

---

### 9.7 Required Backlog Review

| Item | Required Action |
|------|-----------------|
| All BL items tagged Phase 9 | CLOSED or re-assigned |
| All UI-related BL items | Final triage before integration |
| BL items tagged V2 | Reviewed and confirmed correctly deferred — no V2 scope accidentally included in V1 |

---

### 9.8 Required Risk Review

| Risk | Required Action |
|------|-----------------|
| R-011 (Streamlit performance with large datasets in UI) | Updated with Phase 9 manual testing data |
| OQ-007 (legal compliance) | MUST be RESOLVED before Phase 10 gate. If not resolved by end of Phase 9, escalate to P0 blocker. |
| All open P0 and P1 risks | Reviewed and given clear resolution paths before Phase 10 begins |

---

## 10. Phase 10 Exit Gate
### Integration + End-to-End Testing

**Gate ID:** GATE-P10
**Predecessor:** Phase 9 Exit Gate (GATE-P9) — MUST PASS first
**Unlocks:** V1 Release Gate
**Files Gated:** tests/integration/, tests/e2e/ (all integration and end-to-end test suites)
**Special Note:** Phase 10 is the final quality gate before V1. Every P0 and P1 item in every register must be resolved or formally accepted before this gate passes.

---

### 10.1 Required Documents

| Document | Requirement |
|----------|-------------|
| All project governance documents | Must be current — no section marked "TODO" or "PLACEHOLDER" in any of: PROJECT_MASTER_REGISTER.md, TRACEABILITY_MATRIX.md, PROJECT_CHANGE_LOG.md, PROJECT_DECISIONS.md |
| Legal / Compliance clearance (OQ-007) | Written clearance or formal risk acceptance from authorized legal representative. This is a hard gate item — no waiver permitted. |

---

### 10.2 Required Tests

| Test Area | Test Requirements |
|-----------|------------------|
| Full pipeline integration | At minimum 3 end-to-end runs: (1) single trigger, single segment, clean data; (2) multiple triggers with priority ties (exercises ARCH-013); (3) historical data present from prior run (exercises TCC calculation). All must produce all 7 output workbooks with no ValidationResult.is_blocking = True. |
| Reproducibility test | Run the full pipeline twice with identical inputs and CONFIG_SCHEMA_VERSION = "2.0". Assert byte-identical output across both runs for all numeric columns. This is the definitive SIM-019 validation. |
| Schema version rejection | End-to-end test that a config with wrong schema version is rejected before any output is produced. |
| Performance benchmark | Run with the largest trigger file that will be supported in V1. Record run time. Assert it is within the SLA agreed in OQ-001 resolution. |
| Regression suite | All unit tests from Phases 2–9 must continue to pass with no regressions introduced during Phase 10. |

**Specific Named Test Functions That Must Exist:**
```
tests/integration/test_full_pipeline.py::test_clean_run_produces_all_seven_workbooks

tests/integration/test_full_pipeline.py::test_reproducibility_identical_inputs_identical_outputs
  — THE definitive SIM-019 integration gate.

tests/integration/test_full_pipeline.py::test_historical_run_exercises_tcc_path
  — verifies TCC path with real historical data file.

tests/e2e/test_performance.py::test_run_time_within_sla
  — verifies run time <= agreed SLA threshold (from OQ-001 resolution).
```

**Full Regression Command:**
```bash
pytest tests/ -x --tb=short -v
# Expected: 0 failed, 0 errors across ALL test suites

# Performance Constraint Verification block (all four grep checks)
grep -rn "iterrows" engagement_data_generator/ --include="*.py"
grep -rn "pd\.to_excel" engagement_data_generator/ --include="*.py"
grep -rPn "\bhash\(" engagement_data_generator/ --include="*.py" | grep -v hashlib
grep -rn "TODO\|FIXME\|HACK" engagement_data_generator/ --include="*.py"
# All four: zero hits
```

---

### 10.3 Required Coverage

```bash
pytest tests/ \
    --cov=engagement_data_generator \
    --cov-fail-under=85 \
    --cov-report=term-missing
# Expected: exit 0; overall project coverage >= 85%
```

| Scope | Minimum Coverage |
|-------|-----------------|
| Overall project (engagement_data_generator/) | 85% |
| models/ | 90% (maintained from Phase 2) |
| core/ (all modules) | 90% |
| utils/ | 90% |
| app/ | 80% (UI modules have lower target due to Streamlit rendering paths) |

---

### 10.4 Required Governance Updates

**Every register must be fully current:**

| Register | Requirement |
|----------|-------------|
| PROJECT_MASTER_REGISTER.md — Defects Register | All defects: RESOLVED (with commit references) or formally ACCEPTED as known limitations with a documented rationale and V2 backlog entry |
| PROJECT_MASTER_REGISTER.md — Open Decisions | All decisions DD-001 through DD-014 and any DD-NEW items: RESOLVED or formally deferred to V2 with written rationale |
| PROJECT_MASTER_REGISTER.md — Open Questions | All OQ-001 through OQ-014: RESOLVED or REVIEWED |
| PROJECT_MASTER_REGISTER.md — Risk Register | All P0 risks: RESOLVED or ACCEPTED with authorized sign-off. All P1 risks: REVIEWED with mitigation plans documented. |
| PROJECT_MASTER_REGISTER.md — Compliance Register | COMP-001 through COMP-005: all items either COMPLIANT or ACCEPTED with legal sign-off |
| PROJECT_MASTER_REGISTER.md — Technical Debt Register | All TD items: either resolved or re-filed as V2 backlog entries with correct priority |
| PROJECT_MASTER_REGISTER.md — Phase Readiness | Phase 10 = COMPLETE; V1 Release = PENDING GATE |
| PROJECT_CHANGE_LOG.md | Complete — all approved changes CHG-001 through latest reflected |
| PROJECT_MASTER_REGISTER.md | Health Score updated for Phase 10 completion — expected >= 80/100 |

---

### 10.5 Required Traceability Updates

| Document | Section | Requirement |
|----------|---------|-------------|
| TRACEABILITY_MATRIX.md | ALL sections | Fully current — no row with Status = "Unknown" or "Pending" |
| TRACEABILITY_MATRIX.md | Phase Matrix | All 10 phases: COMPLETE |
| TRACEABILITY_MATRIX.md | Requirement Matrix | All REQ-001 through REQ-030: Status = IMPLEMENTED with test reference |
| TRACEABILITY_MATRIX.md | Architecture Matrix | All ARCH decisions: Status = IMPLEMENTED |
| TRACEABILITY_MATRIX.md | Validation Coverage Matrix | All 35 rules: IMPLEMENTED with named test function |
| TRACEABILITY_MATRIX.md | Gap Analysis | All gaps: RESOLVED or formally documented as V2 scope with backlog reference |

---

### 10.6 Required Decision Updates

All deferred decisions must have a written final status. The following must be RESOLVED:
- All P0 decisions blocking any implemented feature
- CONFIG_SCHEMA_VERSION = "2.0" confirmed as the final V1 version string
- All ARCH decisions ARCH-001 through ARCH-014: confirmed as implemented

The following may remain as V2 deferred (with written rationale):
- DD-001 (configurable QUALIFYING_ACTIONS)
- DD-002 (multi-campaign per run)
- DD-009 (data-driven affinity thresholds)
- DD-010 (machine-readable validation catalog)
- DD-011 (CONFIG_SCHEMA_VERSION migration V1→V2)

---

### 10.7 Required Backlog Review

| Category | Requirement |
|----------|-------------|
| P0 backlog items | All CLOSED or escalated to defects register |
| P1 backlog items | All CLOSED or re-filed as V2 items with explicit V2 target |
| V1-tagged items | Every item tagged V1 must be CLOSED. No V1-tagged item may survive the Phase 10 gate as open. |
| V2 backlog | Reviewed and groomed — each item has a priority, description, and dependency noted |

---

### 10.8 Required Risk Review

| Category | Requirement |
|----------|-------------|
| P0 risks | ALL must be RESOLVED or have written ACCEPTED status signed by authorized party |
| P1 risks | ALL must have documented mitigation plans — not necessarily mitigated, but planned |
| OQ-007 (legal compliance) | HARD REQUIREMENT: Written legal clearance OR written formal risk acceptance with authorized signature. This item alone can block Phase 10 gate. |
| Residual risks summary | A summary of all ACCEPTED (non-mitigated) risks must be prepared for V1 Release documentation |

---

## 11. V1 Release Gate

**Gate ID:** GATE-V1
**Predecessor:** Phase 10 Exit Gate (GATE-P10) — MUST PASS first
**Unlocks:** V1 public release / distribution
**Sign-Off Authority:** Lead Engineer + Chief Architect + Program Manager + Product Owner (all four required)

The V1 Release Gate is a final confirmation that the product is production-ready. It does not introduce new criteria beyond Phase 10 — it confirms that Phase 10 criteria remain satisfied in the release candidate and adds release-specific checks.

---

### 11.1 Required Documents

| Document | Requirement |
|----------|-------------|
| All governance documents | Final read-through confirming no section is stale, outdated, or inconsistent with the release candidate |
| Legal clearance document (OQ-007) | On file — written, signed, dated. Not a verbal confirmation. |
| User-facing documentation | User guide, configuration reference, and quick-start guide exist in /docs/ and have been reviewed for accuracy against the release candidate |
| RELEASE_GATES.md (this document) | All gates from GATE-P2 through GATE-P10 documented as PASSED with dates |
| Release notes | Drafted — lists all implemented features, known limitations, and V2 roadmap items |

---

### 11.2 Required Tests

All tests from Phase 10 gate must still pass against the release candidate binary without modification.

```bash
pytest tests/ --tb=short -q
# Expected: 0 failed, 0 errors

pytest tests/ \
    --cov=engagement_data_generator \
    --cov-fail-under=85 \
    --cov-report=term-missing
# Expected: exit 0
```

**Release-Specific Test:**
```bash
# Smoke test: install the package and run the minimal end-to-end pipeline
# from a clean Python environment (no dev dependencies)
python -c "from app.run_controller import run_controller; print('Import OK')"
# Expected: prints 'Import OK', exits 0
```

---

### 11.3 Required Coverage

Same as Phase 10: overall >= 85%, core/ >= 90%, models/ >= 90%, utils/ >= 90%.

---

### 11.4 Required Governance Updates

| Document | Required Final Update |
|----------|-----------------------|
| PROJECT_MASTER_REGISTER.md | Health Score entry for V1 Release state (target >= 88/100). Project Phase = V1 RELEASED. |
| PROJECT_MASTER_REGISTER.md — Go/No-Go | Both Phase 3 entry and V1 Release rows updated to PASS |
| PROJECT_CHANGE_LOG.md | V1.0 release entry added with date and version tag |
| TRACEABILITY_MATRIX.md | Document version updated; all gaps in Section 9 have final disposition |

---

### 11.5 Required Traceability Updates

No new traceability updates beyond Phase 10. Confirm all TRACEABILITY_MATRIX.md sections are final and consistent with the release candidate.

---

### 11.6 Required Decision Updates

| Item | Requirement |
|------|-------------|
| All DD-NEW decisions created during Phases 3–10 | Either RESOLVED (if V1 scope) or moved to V2 backlog with written rationale |
| CONFIG_SCHEMA_VERSION | Confirmed as "2.0" in utils/version.py — version string in code matches documentation |
| V2 decisions list | All deferred decisions summarized in a single V2 decision register entry in PROJECT_DECISIONS.md |

---

### 11.7 Required Backlog Review

| Category | Requirement |
|----------|-------------|
| V1-tagged items | Zero open V1-tagged items. Every V1 item is CLOSED. |
| V2 backlog | Complete and groomed — minimum viable V2 scope is documented |
| FE-018 through FE-023 (new backlog candidates from PROJECT_CHANGE_LOG.md) | Each has a V2 priority and dependency noted |

---

### 11.8 Required Risk Review

| Category | Requirement |
|----------|-------------|
| All P0 risks | RESOLVED or ACCEPTED with legal/authorized sign-off on file |
| All P1 risks | Written mitigation plans on file |
| Residual risk summary | Included in release documentation visible to users or operators |
| OQ-007 (legal compliance) | Written clearance on file — absolute hard gate, no exceptions |

---

## 12. Gate Status Dashboard

This section is updated at each gate evaluation. Each row is updated to PASS or FAIL by the gate sign-off authority.

| Gate | Phase | Status | Date Passed | Sign-Off |
|------|-------|--------|-------------|----------|
| GATE-P1 | Phase 1 — Project Skeleton | PASSED | Pre-existing | — |
| GATE-P2 | Phase 2 — Core Data Models | PENDING | — | Lead Engineer + Chief Architect |
| GATE-P3 | Phase 3 — User State + Audience | NOT STARTED | — | Lead Engineer + Chief Architect |
| GATE-P4 | Phase 4 — Journey Engine | NOT STARTED | — | Lead Engineer + Chief Architect |
| GATE-P5 | Phase 5 — Behavior Engine | NOT STARTED | — | Lead Engineer + Chief Architect |
| GATE-P6 | Phase 6 — Timing Engine | NOT STARTED | — | Lead Engineer + Chief Architect |
| GATE-P7 | Phase 7 — Validation Engine | NOT STARTED | — | Lead Eng + Architect + PM |
| GATE-P8 | Phase 8 — Export Engine | NOT STARTED | — | Lead Eng + Architect + PM |
| GATE-P9 | Phase 9 — UI + Run Controller | NOT STARTED | — | Lead Eng + Architect + PM |
| GATE-P10 | Phase 10 — Integration + E2E | NOT STARTED | — | Lead Eng + Architect + PM + PO |
| GATE-V1 | V1 Release | NOT STARTED | — | Lead Eng + Architect + PM + PO |

**Current Blocker Summary (as of 2026-06-22, updated Wave 3 complete):**

| Gate | Hard Blockers Remaining |
|------|------------------------|
| GATE-P2 | **Wave 3 complete 2026-06-22.** REM-001/002 CLOSED 2026-06-21. REM-003/004 CLOSED 2026-06-22. REM-005/006/007/008 CLOSED 2026-06-22 (config_loader TypeError eliminated). CB-004 RESOLVED. 127/127 tests pass. 10 REM items remain (REM-009 iterrows, REM-010–013 test helpers, REM-014–018 minor). |
| GATE-P3 | Awaiting GATE-P2; OQ-003 legal review not initiated |
| GATE-P4 | Awaiting GATE-P3; DD-012 unresolved |
| GATE-P7 | CB-008: Validation_Rules_Catalog.md must be read before Phase 7 begins |
| GATE-V1 | OQ-007 legal review not initiated — this is the single highest-risk long-lead item for V1 delivery |

**Critical Path to V1 (gates on the longest dependency chain):**
```
GATE-P2 → GATE-P3 → GATE-P4 → GATE-P5 → GATE-P6 → GATE-P7 → GATE-P8 → GATE-P9 → GATE-P10 → GATE-V1
```
All gates are strictly sequential. No gate may be evaluated until its predecessor passes.

**Longest-Lead Parallel Track:**
```
OQ-007 Legal Review ──────────────────────────────────────────────► GATE-V1 (hard requirement)
```
This review should be initiated immediately and is independent of the technical gate sequence. It is the item most likely to delay V1 beyond the technical completion date.

---

*RELEASE_GATES.md — Version 1.0*
*Engagement Data Generator v1.0*
*Chief Architect / Program Manager / Governance Owner*
*2026-06-21*

*This document governs all phase transitions from Phase 2 through V1 release.*
*A phase may not begin until the preceding gate is signed off.*
*The gate is binary — PASS or FAIL. No partial passage.*
*When this document conflicts with PROJECT_DECISIONS.md, PROJECT_DECISIONS.md takes precedence.*
*Update Section 12 (Gate Status Dashboard) at every gate evaluation.*
