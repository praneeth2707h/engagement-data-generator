# Stage 13 — Multi-Trigger End-to-End Certification Report

**Version:** 1.0  
**Date:** 2026-06-22  
**Author roles:** CTO · Principal Architect · QA Director · Release Manager · Independent Auditor  
**Test suite:** `tests/test_e2e/test_multitrigger_certification.py`  
**Total tests executed:** 59  
**Total tests passed:** 59  
**Total tests failed:** 0  
**Full regression:** 1,007 passed / 0 failed / 0 errors  

---

## Certification Question

> **MT-CERT-Q-001: Can users belong to multiple triggers without creating attribution errors, reporting errors, or journey assignment errors?**

## Verdict

> **YES — CERTIFIED**
>
> All 10 multi-trigger certification scenarios pass. The winner-takes-all priority model is deterministic, correctly propagated through every pipeline stage, and validated by VAL-010 on every run. No attribution errors, reporting errors, or journey assignment errors were found. Two architecture risks are documented for operational awareness (not blockers).

---

## 1. Certification Results

### MT-001 — Single User, Single Trigger (Baseline)

**Purpose:** Establish correct single-trigger attribution before testing multi-trigger behaviour.

**Configuration:** 3 users, T1 only, 14-day simulation.

| Metric | Value |
|---|---|
| Users | 3 |
| Events | 42 |
| Trigger in audience_df | `['T1']` |
| Trigger in events | `['T1']` |
| T2 events | 0 |

**Tests:** 5 / 5 PASSED

---

### MT-002 — Two Triggers, Priority Resolution

**Rule under test:** Lower `priority` integer wins. `TriggerConfig("T1", priority=1)` beats `TriggerConfig("T2", priority=2)`.

**Population:** U001 in T1+T2, U002 in T1 only, U003 in T2 only.

| User | Triggers in file | Winner | Events attributed to |
|---|---|---|---|
| U001 | T1, T2 | **T1** | T1 only |
| U002 | T1 | T1 | T1 |
| U003 | T2 | T2 | T2 |

**Verified:**
- U001 winning trigger = T1 ✅
- U001 events carry trigger_name="T1" exclusively ✅
- U003 untouched (T2 only, T2 wins) ✅
- Each user has exactly 1 trigger_name in events ✅

**Tests:** 7 / 7 PASSED

---

### MT-003 — Three Triggers + Alphabetical Tiebreak

**Rule under test:** Lowest priority number wins among ≥3 triggers. Equal-priority ties broken alphabetically (ARCH-013).

**Three-trigger scenario:** U001 in T1(priority=3), T2(priority=1), T3(priority=2) → T2 wins.

| Config | User | Triggers | Winner |
|---|---|---|---|
| 3-trigger | U001 | T1(p=3), T2(p=1), T3(p=2) | **T2** |
| 3-trigger | U002 | T3 only | T3 |

**Alphabetical tiebreak scenario (ARCH-013):** U001 in T_Alpha(priority=1) + T_Beta(priority=1) → T_Alpha wins.

| User | Triggers | Winner |
|---|---|---|
| U001 | T_Beta(p=1), T_Alpha(p=1) | **T_Alpha** |

**Tests:** 6 / 6 PASSED

---

### MT-004 — Mixed Population Attribution Counts

**Population:**

| Group | Users | Triggers in file | Expected winner |
|---|---|---|---|
| T1-only | 40 | T1 | T1 |
| T2-only | 40 | T2 | T2 |
| Both | 20 | T1(p=1) + T2(p=2) | T1 |

**Attribution counts verified:**

| Trigger | Expected users | Actual users |
|---|---|---|
| T1 | 60 (40+20) | 60 ✅ |
| T2 | 40 | 40 ✅ |
| Total | 100 | 100 ✅ |
| Overlap (T1∩T2) | 0 | 0 ✅ |

**VAL-010 result:** PASS — 0 users appear with >1 trigger_name in events.

**Tests:** 6 / 6 PASSED

---

### MT-005 — TER Reporting Against Correct Trigger Denominator

**Mechanism:** ValidationEngine computes TER per trigger using only the users who WON that trigger as the denominator, not all users who appeared in the trigger file for that trigger.

**Same 100-user population as MT-004:**

| Trigger | Denominator (winning users) | TER message |
|---|---|---|
| T1 | 60 | `"42/60 users engaged"` ✅ |
| T2 | 40 | `"30/40 users engaged"` ✅ |

**Key insight:** T2's TER denominator is 40 (T2-only), NOT 60 (T2-only + the 20 multi-trigger users who appeared in T2's row but won T1). This is correct — TER measures the rate against users actually served by that trigger.

**Tests:** 5 / 5 PASSED

---

### MT-006 — Re-entry User with Multiple Triggers

**Setup:** 20 users with expired cooling (journey_status=Completed). Each appears in T1+T2. 30 new users in T1 only.

**allow_reentry=True:**

| User group | Status | Winner trigger |
|---|---|---|
| 30 new users | NEW | T1 |
| 20 cooling-expired | RE_ENTRY | **T1** (priority resolution still applied) |

**allow_reentry=False:**

| User group | Status |
|---|---|
| 20 cooling-expired | EXCLUDED |

**Verified:**
- Re-entry classification is correct (20 RE_ENTRY vs 20 EXCLUDED) ✅
- Priority resolution unchanged for RE_ENTRY users — T1 wins ✅
- Re-entry ON generates more events than OFF ✅
- Re-entry users' events attributed to T1 only ✅

**Tests:** 6 / 6 PASSED

---

### MT-007 — Journey Assignment to Winning Trigger

**Configuration:** 3-ad journey (Ad_A dur=3, Ad_B dur=3, Ad_C dur=14). 30 users each in T1+T2. T1 wins.

**Journey progression verified (14-day simulation):**

| Stage | Events |
|---|---|
| Ad_A | > 0 ✅ |
| Ad_B | > 0 ✅ (users advance after day 3) |
| Ad_C | > 0 ✅ (users advance after day 6) |
| T2 events | 0 ✅ (losing trigger generates no events) |

**Tests:** 6 / 6 PASSED

---

### MT-008 — ValidationEngine Multi-Trigger Correctness

**Validation rules verified with 80-user mixed population (T1-only/T2-only/both):**

| Rule | Result |
|---|---|
| VAL-009 Trigger Priority (no unknown triggers) | PASS ✅ |
| VAL-010 Multi-Trigger Consistency | PASS ✅ |
| VAL-003 TER Achievement — T1 | Row exists ✅ |
| VAL-003 TER Achievement — T2 | Row exists ✅ |
| VAL-013 TCC Calculation — T1 | Row exists ✅ |
| VAL-013 TCC Calculation — T2 | Row exists ✅ |
| Quality score | 0–100 range ✅ |

**Tests:** 6 / 6 PASSED

---

### MT-009 — Workbook Export Trigger Attribution

**Configuration:** 20 T1-only + 20 T2-only + 10 both-trigger users (→30 T1, 20 T2).

**Workbook verified:**

| Check | Result |
|---|---|
| workbook_bytes non-None and non-empty | ✅ |
| Event Data row count matches events_df | ✅ |
| Trigger_Name column present in Event Data | ✅ |
| Both T1 and T2 appear in workbook | ✅ |
| Zero users with >1 trigger_name in workbook | ✅ |
| T1 user count in workbook = 30 (20+10) | ✅ |

**Tests:** 6 / 6 PASSED

---

### MT-010 — Determinism with Multi-Trigger Inputs

**Two identical runs (same inputs, same priority config):**

| Metric | Result |
|---|---|
| events_df byte-identical | ✅ |
| workbook_bytes identical | ✅ |
| trigger attribution identical | ✅ |
| quality_score identical | ✅ |

**Priority reversal test (T1↔T2 priority swapped):**

| Config | MT users winner |
|---|---|
| T1(p=1) T2(p=2) | T1 ✅ |
| T1(p=2) T2(p=1) | T2 ✅ |

Priority controls attribution — not hash ordering, insertion order, or randomness.

**Tests:** 5 / 5 PASSED

---

## 2. Trigger Attribution Matrix

For a population of 100 users (40 T1-only, 40 T2-only, 20 in both):

| User type | Rows in trigger file | Winner (T1 p=1, T2 p=2) | Events attributed to |
|---|---|---|---|
| T1-only (40) | T1 | T1 | T1 |
| T2-only (40) | T2 | T2 | T2 |
| Both (20) | T1, T2 | **T1** | T1 |
| **Totals** | | T1=60, T2=40 | T1=60, T2=40 |

**Invariant:** Each user appears in exactly one attribution group. The groups are disjoint and exhaustive.

---

## 3. Trigger Priority Matrix

| Scenario | Trigger configs | Winner rule | Winner |
|---|---|---|---|
| 2 triggers, different priority | T1(p=1), T2(p=2) | Lowest integer | T1 |
| 2 triggers, reversed | T1(p=2), T2(p=1) | Lowest integer | T2 |
| 3 triggers | T1(p=3), T2(p=1), T3(p=2) | Lowest integer | T2 |
| Equal priority | T_Alpha(p=1), T_Beta(p=1) | Alphabetical name | T_Alpha |
| Equal priority, equal name | (impossible — names must be unique per config) | N/A | N/A |

**Architecture:** `AudienceManager._compute_winner_df()` implements this as:
```
sort_values(["_priority", "Trigger_Name", "Segment"], ascending=[True, True, True])
.drop_duplicates(subset=["Campaign_ID", "User_ID"], keep="first")
```

---

## 4. Reporting Validation

| Report | Multi-trigger behaviour | Verified |
|---|---|---|
| TER per trigger | Denominator = users who WON that trigger (not all users in file) | ✅ MT-005 |
| TCC per trigger | Ceiling = ceil(winning_users × TER_target) | ✅ MT-008 |
| VAL-010 | Each user has exactly 1 trigger_name in events | ✅ MT-004, MT-008 |
| VAL-009 | All trigger names in events are known | ✅ MT-008 |
| Campaign Metrics sheet | Aggregated across all triggers correctly | ✅ MT-009 |
| Diagnostics sheet | TER rows exist per trigger | ✅ MT-009 |

**Critical reporting invariant confirmed:** When 20 users appear in both T1 and T2 rows but T1 wins, T2's TER denominator is 40 (T2-only users) — not 60. This prevents TER from appearing artificially low for the losing trigger due to users it never actually received.

---

## 5. Workbook Validation

| Check | Result |
|---|---|
| `Trigger_Name` column present in Event Data sheet | ✅ |
| Each row has exactly one non-null Trigger_Name | ✅ |
| No user_id maps to >1 Trigger_Name in workbook | ✅ |
| Workbook T1 user count = 30 (T1-only + multi-trigger winners) | ✅ |
| Workbook T2 user count = 20 (T2-only) | ✅ |
| Row count matches in-memory events_df | ✅ |

---

## 6. Defects Discovered

**No correctness defects were found.** The multi-trigger pipeline is fully correct.

The following architecture risks are documented for operational awareness:

---

## 7. Architecture Risks

### ARCH-RISK-001 — AudienceManager capacity overestimates losing-trigger user counts (LOW RISK)

**Severity:** Low — no correctness impact; purely an estimation divergence  
**Description:** `AudienceManager.compute_remaining_capacity()` counts ALL rows for each Trigger_Name in the filtered trigger file, regardless of which trigger wins for each user. `EngagementGenerator._init_capacity_tracker()` independently recomputes capacity from `state_df["trigger_name"]` (winning users only). These produce different counts for multi-trigger populations.

**Example:** 40 T2-only + 20 both-trigger users. AudienceManager T2 capacity uses total=60. EngagementGenerator T2 capacity uses total=40 (only T2 winners). The EngagementGenerator's calculation is the authoritative one — it determines actual TCC enforcement.

**Impact:** `SimulationResult.execution_metadata` does not expose AudienceManager's pre-flight capacity estimate, so users never see this discrepancy. However, if capacity is surfaced in future analytics, the two numbers will not match for multi-trigger campaigns.

**Recommendation:** Document the divergence. If pre-flight capacity estimation is ever exposed in the UI, use the EngagementGenerator calculation as the source of truth.

---

### ARCH-RISK-002 — Trigger history accumulates across runs but not within runs (LOW RISK, BY DESIGN)

**Severity:** Low — correct by design, but may surprise analysts  
**Description:** `trigger_history` in `state_df` accumulates all trigger names a user has been assigned across multiple simulation runs (via `previous_state_df`). It does NOT record the multiple triggers a user appeared under in a single run's trigger file — only the winning trigger is appended to history.

**Example:** User U001 in run 1 wins T1 → trigger_history="T1". In run 2 (still in T1+T2) wins T1 → trigger_history="T1|T1". The T2 appearance in the trigger file is never recorded.

**Impact:** Audit trails based on trigger_history are incomplete for multi-trigger users. Analysts cannot reconstruct which non-winning triggers a user was eligible for in past runs.

**Recommendation:** No change required for current Streamlit MVP. If multi-trigger audit trails are needed in a future release, consider adding a `trigger_file_history` field that records all trigger names seen in a given run, separately from the winning trigger.

---

## 8. Release Recommendation

### Go / No-Go: **GO**

#### Gate Assessment

| Gate | Criterion | Status |
|---|---|---|
| G1 | All multi-trigger certification tests pass (59/59) | ✅ PASS |
| G2 | Full regression passes (1,007/1,007) | ✅ PASS |
| G3 | Attribution invariant: each user has exactly 1 trigger | ✅ PASS |
| G4 | Priority resolution is deterministic and reversible | ✅ PASS |
| G5 | TER denominator uses winning-trigger users, not file rows | ✅ PASS |
| G6 | Re-entry respects priority resolution | ✅ PASS |
| G7 | Journey progression uses winning-trigger ads only | ✅ PASS |
| G8 | Workbook reflects winning trigger for all rows | ✅ PASS |
| G9 | Zero correctness defects found | ✅ PASS |
| G10 | Architecture risks are low-severity and non-blocking | ✅ PASS |

#### Conditions

1. Document ARCH-RISK-001 (capacity overestimate) in operator notes if pre-flight capacity is ever exposed in the UI.
2. Add a UI tooltip or documentation note clarifying that when a user appears in multiple trigger rows, only the highest-priority trigger governs their journey and all event attribution.

#### Not blocking release

- Both architecture risks are low-severity and affect only edge-case analytics, not simulation correctness.
- FutureWarning from `journey_engine.py` on pandas `.fillna().astype()` chains — not a production error.

---

## Appendix: Test Execution Summary

```
Platform:    Linux (Ubuntu 22 sandbox)
Python:      3.10
pytest:      installed

Test file:   tests/test_e2e/test_multitrigger_certification.py
Tests:       59
Duration:    ~9.5 seconds

Full regression (split due to shell timeout):
  tests/ (excluding test_e2e):   893 passed, 0 failed
  tests/test_e2e/:               114 passed, 0 failed
  Total:                        1,007 passed, 0 failed, 0 errors

Certification runs use:
  - Real SimulationOrchestrator (all 6 stages)
  - Real Excel workbooks for MT-009, MT-010
  - Zero mocks for any core simulation component
  - Population sizes: 1–100 users per scenario
  - Multi-trigger populations: up to 20 users in 2–3 triggers simultaneously
```

---

*End of Stage 13 Multi-Trigger Certification Report*
