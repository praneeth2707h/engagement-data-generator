# TESTING STRATEGY
## Engagement Data Generator — Remediation Test Design

**Document ID:** TST-001  
**Version:** 1.0  
**Date:** 2026-06-23  
**Parent:** ARCHITECTURE_REMEDIATION_PACKAGE.md (ARP-001)

---

## SECTION 1 — CURRENT STATE ASSESSMENT

### 1.1 Existing Test Coverage

The certified test suite comprises 1,111 tests across the following categories:

| Category | File | Tests | Status |
|----------|------|-------|--------|
| Model tests | `tests/test_models/` | ~180 | PASS |
| Core unit tests | `tests/test_core/` | ~420 | PASS |
| Utility tests | `tests/test_utils/` | ~60 | PASS |
| UI smoke tests | `tests/test_ui/` | ~30 | PASS |
| Business rule E2E | `test_business_rule_certification.py` | ~200 | PASS |
| Historical window E2E | `test_historical_window_certification.py` | ~100 | PASS |
| Multi-trigger E2E | `test_multitrigger_certification.py` | ~50 | PASS |
| Multi-run persistence E2E | `test_multirun_persistence_certification.py` | ~50 | PASS |
| Scale certification E2E | `test_scale_certification.py` | ~50 | PASS |

### 1.2 Coverage Gaps Identified

The 1,111 existing tests do not cover:

1. Journey position reconstruction from historical data (CRIT-001/004/005) — `HistoricalStateReconstructor` does not exist.
2. Trigger-specific ad sequences (CRIT-002) — `TriggerConfig.ads` field does not exist.
3. Historical audience continuity (CRIT-003) — audience augmentation not implemented.
4. Cooling period override (CRIT-006) — `CoolingOverrideService` does not exist.
5. CTR accuracy at low TER targets (CRIT-007) — no CTR calibration tests.
6. Journey causal chain validation (CRIT-008) — VR-J001 does not exist.
7. Canonical schema consistency (HIGH-001) — no cross-module column name tests.
8. Upload validation alignment (HIGH-002) — no test verifying UI matches schema_validator.
9. User_ID type safety in upload path (HIGH-003) — no dtype=str test.
10. Journey status gate in events (HIGH-004) — no test for NOT_STARTED event generation.
11. Extended historical schema (HIGH-005) — no 8-column historical file test.

### 1.3 Test Infrastructure Capabilities

- `pytest` with class-level caching pattern (established in Stage 16 — see `test_scale_certification.py`).
- `conftest.py` fixtures: `_make_config()`, `_make_trigger_df()`, standard campaign helpers.
- Bash 45-second timeout constraint: large simulations use class-level caching.
- All deterministic by design (MD5+ordinal RNG seeds — SIM-019).

---

## SECTION 2 — DESIRED STATE

### 2.1 Test Coverage Targets

| Defect | Unit Tests | Integration Tests | E2E Tests |
|--------|-----------|-------------------|-----------|
| CRIT-001 | 8 (reconstructor) | 3 (orchestrator wiring) | 5 (E2E acceptance) |
| CRIT-002 | 5 (TriggerConfig) + 5 (JourneyEngine) + 5 (TJR) | 3 | 5 |
| CRIT-003 | 3 (augmentation) | 2 | 4 |
| CRIT-004 | 5 (reconstructor) | 2 | 5 |
| CRIT-005 | 4 (cooling from history) | 2 | 4 |
| CRIT-006 | 5 (CoolingOverrideService) | 2 | 4 |
| CRIT-007 | 3 (TCC floor) + 3 (boost) | 2 (CTR calibration) | 5 |
| CRIT-008 | 6 (ValidationEngine rules) | 2 | 4 |
| HIGH-001 | 7 (CanonicalSchema) | 2 | 3 |
| HIGH-002 | 3 (upload page) | 1 | 3 |
| HIGH-003 | 3 (dtype=str) | 1 | 3 |
| HIGH-004 | 3 (BehaviorEngine gate) | 1 | 3 |
| HIGH-005 | 4 (extended schema) | 2 | 4 |
| **Total** | **~80 new unit** | **~27 integration** | **57 E2E** |

### 2.2 Test Naming Convention

All remediation tests use the prefix `test_rc_` (Remediation Certification) in E2E files. Unit tests follow the existing convention `test_{function_name}_{scenario}`.

---

## SECTION 3 — GAP ANALYSIS (TEST COVERAGE)

| Gap | Files Missing Tests | Test Priority |
|-----|---------------------|--------------|
| HistoricalStateReconstructor | `test_historical_state_reconstructor.py` (new) | P0 |
| TriggerJourneyResolver | `test_trigger_journey_resolver.py` (new) | P0 |
| CoolingOverrideService | `test_cooling_override_service.py` (new) | P0 |
| CanonicalSchema | `test_canonical_schema.py` (new) | P1 |
| JourneyEngine ads_override | `test_journey_engine.py` additions | P0 |
| BehaviorEngine journey_status gate | `test_behavior_engine.py` additions | P0 |
| EngagementGenerator CTR accuracy | `test_engagement_generator.py` additions | P0 |
| ValidationEngine VR-J001..J005 | `test_validation_engine.py` additions | P0 |
| UserStateManager three-way merge | `test_user_state_manager.py` additions | P0 |
| Upload page dtype=str | `test_smoke.py` additions | P1 |
| Upload validation alignment | `test_smoke.py` additions | P1 |
| E2E acceptance criteria | `test_remediation_certification.py` (new) | P0 |

---

## SECTION 4 — ARCHITECTURE CHANGES (TEST INFRASTRUCTURE)

### 4.1 New Test Files

```
tests/
  test_utils/
    test_canonical_schema.py        (Wave 1)
  test_core/
    test_trigger_journey_resolver.py (Wave 2)
    test_historical_state_reconstructor.py (Wave 3)
    test_cooling_override_service.py (Wave 4)
  test_e2e/
    test_remediation_certification.py (Wave 5)
```

### 4.2 Historical File Test Fixtures

All historical file tests require both 4-column and 8-column fixture DataFrames. Standard factory:

```python
def _make_4col_historical_df(
    user_ids: list[str],
    days_ago: int = 10,
    action: str = "Click",
    channel: str = "Display",
) -> pd.DataFrame:
    from datetime import date, timedelta
    today = date.today()
    return pd.DataFrame({
        "User_ID": user_ids,
        "Date": [(today - timedelta(days=days_ago)).isoformat()] * len(user_ids),
        "Action": [action] * len(user_ids),
        "Channel": [channel] * len(user_ids),
    })


def _make_8col_historical_df(
    user_ids: list[str],
    ad_name: str = "Ad_A",
    journey_step: int = 1,
    trigger_name: str = "T1",
    completion_date: str | None = None,
    days_ago: int = 10,
    action: str = "Click",
    channel: str = "Display",
) -> pd.DataFrame:
    df = _make_4col_historical_df(user_ids, days_ago, action, channel)
    df["Ad_Name"] = ad_name
    df["Journey_Step"] = journey_step
    df["Trigger_Name"] = trigger_name
    df["Completion_Date"] = completion_date
    return df
```

### 4.3 Trigger-Specific Ad Config Fixtures

```python
def _make_trigger_with_ads(
    trigger_name: str = "T_CUSTOM",
    ad_names: list[str] | None = None,
    engagement_rate_target: float = 0.20,
) -> TriggerConfig:
    from models.ad_config import AdConfig
    if ad_names is None:
        ad_names = ["Custom_Ad_1", "Custom_Ad_2"]
    ads = tuple(
        AdConfig(
            ad_name=name,
            ad_order=i+1,
            duration_days=3,
            move_on_click=True,
            channel="Display",
            vendor=None,
            target_ctr=0.10,
        )
        for i, name in enumerate(ad_names)
    )
    return TriggerConfig(
        trigger_name=trigger_name,
        priority=1,
        engagement_rate_target=engagement_rate_target,
        ads=ads,
    )
```

---

## SECTION 5 — DATA MODEL CHANGES (TEST IMPACT)

### 5.1 Existing Tests Requiring Update

| Test File | Change Required | Root Cause |
|-----------|----------------|-----------|
| All tests using int User_IDs in fixture data | Change to str | HIGH-003 dtype=str fix |
| Tests asserting `remaining_capacity=0` when historical fills TCC | Update to `remaining_capacity≥1` | CRIT-007 TCC floor |
| Tests asserting events for NOT_STARTED users | Update to assert no such events | HIGH-004 gate |
| Tests constructing `TriggerConfig` | No change needed (ads=None default) | CRIT-002 backward compatible |
| Tests constructing `UserState.new()` | Add assertions for 3 new fields | CRIT-002 |
| Tests constructing `JourneyEngine` | No change needed (ads_override=None) | CRIT-002 backward compatible |

### 5.2 Test Data Migration Script

To identify all test files with integer User_IDs:

```bash
grep -rn '"User_ID": [0-9]\|"user_id": [0-9]\|User_ID.*[0-9][0-9][0-9][0-9]' \
    tests/ --include="*.py"
```

All matches must be converted to string format: `"User_ID": "1001"` not `"User_ID": 1001`.

---

## SECTION 6 — USER STATE CHANGES (TEST IMPACT)

### UserState New Fields — Test Coverage

Every test that calls `UserState.new()` should add assertions for the three new fields:

```python
state = UserState.new(campaign_id="C", user_id="U1", state_as_of_date=date.today(), ad_names=[])
assert state.journey_step is None
assert state.trigger_ads_key is None
assert state.cooling_override_applied is False
```

### UserStateManager Three-Way Merge — Test Matrix

| Scenario | previous_state_df | reconstructed_state_df | Expected source |
|----------|-------------------|----------------------|-----------------|
| User in previous only | ✓ | ✗ | previous |
| User in reconstructed only | ✗ | ✓ | reconstructed |
| User in neither | ✗ | ✗ | UserState.new() |
| User in both | ✓ | ✓ | previous (wins) |
| All three sources present | ✓ | ✓ | n/a | previous |

Each scenario is a distinct test case in `test_user_state_manager.py`.

---

## SECTION 7 — UI CHANGES (TEST IMPACT)

### Upload Page Tests

**`tests/test_ui/test_smoke.py` — new tests:**

```python
def test_read_upload_csv_numeric_user_id_becomes_str():
    """HIGH-003: CSV with integer User_IDs must produce str-typed User_ID column."""
    import io
    from ui.upload_page import _read_upload
    csv_content = "User_ID,Trigger_Name,Trigger_Date,Segment\n1001,T1,2025-01-01,Seg_A"
    mock_file = io.BytesIO(csv_content.encode())
    mock_file.name = "test.csv"
    df = _read_upload(mock_file)
    assert df["User_ID"].dtype == object  # str in pandas
    assert df["User_ID"].iloc[0] == "1001"


def test_trigger_required_cols_match_schema_validator():
    """HIGH-002: Upload page required cols == schema_validator required cols."""
    from ui.upload_page import _TRIGGER_REQUIRED_COLS  # after fix: sourced from CanonicalSchema
    from utils.schema_validator import TRIGGER_FILE_REQUIRED_COLUMNS
    assert set(_TRIGGER_REQUIRED_COLS) == set(TRIGGER_FILE_REQUIRED_COLUMNS)


def test_historical_required_cols_match_schema_validator():
    """HIGH-002: Upload page historical cols == schema_validator historical cols."""
    from ui.upload_page import _HISTORICAL_REQUIRED_COLS
    from utils.schema_validator import HISTORICAL_FILE_REQUIRED_COLUMNS
    assert set(_HISTORICAL_REQUIRED_COLS) == set(HISTORICAL_FILE_REQUIRED_COLUMNS)
```

---

## SECTION 8 — VALIDATION CHANGES (TEST IMPACT)

### ValidationEngine — New Rule Tests

**`tests/test_core/test_validation_engine.py` additions:**

**VR-J001 (click-gated causal chain):**

```python
def test_vr_j001_fires_when_ad2_without_ad1_click():
    """User on Ad_2 (move_on_click=True) with no Ad_1 Click event → VR-J001 FAIL."""
    events_df = pd.DataFrame({
        "user_id": ["U1"],
        "simulation_date": [date(2025, 1, 5)],
        "current_ad": ["Ad_2"],  # on Ad_2
        "action_type": ["Impression"],
        "journey_step": [2],
        # No Click event for Ad_1 in the DataFrame
        ...
    })
    results = ValidationEngine(config_with_click_gated_ads).validate(events_df, ...)
    assert any(r["rule_id"] == "VR-J001" and r["status"] == "Fail" for r in results)


def test_vr_j001_no_fire_for_duration_advance():
    """User on Ad_2 (move_on_click=False) with no Ad_1 Click → no VR-J001 violation."""
    # move_on_click=False on Ad_1; user advances by duration only
    # No click event needed
    ...
    results = ValidationEngine(config_with_duration_ads).validate(events_df, ...)
    assert not any(r["rule_id"] == "VR-J001" and r["status"] == "Fail" for r in results)
```

**VR-J002 (NOT_STARTED events):**

```python
def test_vr_j002_fires_when_not_started_event_present():
    events_df["journey_status"] = "Not_Started"
    results = ValidationEngine(cfg).validate(events_df, ...)
    assert any(r["rule_id"] == "VR-J002" and r["status"] == "Fail" for r in results)


def test_vr_j002_no_fire_when_all_active():
    events_df["journey_status"] = "Active"
    results = ValidationEngine(cfg).validate(events_df, ...)
    assert not any(r["rule_id"] == "VR-J002" for r in results)
```

---

## SECTION 9 — MIGRATION STRATEGY (TEST MIGRATION)

### Migration Playbook

1. Run `grep -rn 'user_id.*[0-9][0-9][0-9][0-9]\|User_ID.*[0-9][0-9][0-9][0-9]' tests/ --include="*.py"` to identify all integer User_ID usages in tests.
2. Convert all integer User_IDs in test fixtures to string equivalents.
3. Run `pytest tests/ -x` after each batch of fixture conversions.
4. For any test that explicitly asserts `remaining_capacity == 0` due to historical engagement filling TCC: update assertion to `remaining_capacity >= 1` or `remaining_capacity > 0`.
5. For any test asserting events for `journey_status=Not_Started`: update to assert no such events.

This migration should be completed in Wave 1 (integer User_ID fixtures) and Wave 2 (NOT_STARTED assertions), not deferred to Wave 5.

---

## SECTION 10 — BACKWARD COMPATIBILITY ASSESSMENT (TEST PERSPECTIVE)

| Category | Impact |
|----------|--------|
| Existing model tests | LOW — new optional fields with defaults; only `test_user_state.py` needs additions |
| Existing JourneyEngine tests | NONE — `ads_override=None` default; behavior unchanged |
| Existing EngagementGenerator tests | MEDIUM — per-trigger cohort loop changes behavior; TCC floor changes assertions |
| Existing BehaviorEngine tests | LOW — journey_status gate removes NOT_STARTED events; fixtures may need update |
| Existing ValidationEngine tests | LOW — new rules added; existing rules unchanged |
| Existing E2E tests | LOW — backward-compatible changes; new features don't affect existing test scenarios |

---

## SECTION 11 — PERFORMANCE IMPACT (TEST SUITE)

### New Test Count

| Category | New Tests |
|----------|-----------|
| `test_canonical_schema.py` | 9 |
| `test_trigger_journey_resolver.py` | 5 |
| `test_historical_state_reconstructor.py` | 8 |
| `test_cooling_override_service.py` | 5 |
| Additions to existing core tests | ~30 |
| Additions to existing model tests | ~10 |
| Additions to existing UI tests | ~5 |
| `test_remediation_certification.py` | 57 |
| Additions to existing E2E tests | ~20 |
| **Total new tests** | **~149** |

**Projected total:** 1,111 + 149 = ~1,260 tests.

### Bash Timeout Management

The 57 E2E certification tests in `test_remediation_certification.py` must use class-level caching where the simulation is expensive:

```python
class TestRC007CTRTERAccuracy:
    _N = 1000
    _DAYS = 14
    _m: dict | None = None

    @classmethod
    def _get_result(cls) -> dict:
        if cls._m is None:
            cfg = _make_config(n_days=cls._DAYS, ...)
            tdf = _make_trigger_df(cls._N)
            cls._m = _run_and_measure(cfg, tdf, generate_excel=False)
        return cls._m

    def test_s01_observed_ctr_nonzero(self):
        m = self._get_result()
        assert m["ctr"] > 0.0

    def test_s02_observed_ctr_within_tolerance(self):
        m = self._get_result()
        assert abs(m["ctr"] - m["target_ctr"]) / m["target_ctr"] <= 0.20
```

---

## SECTION 12 — RISK ASSESSMENT (TEST RISK)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| test_remediation_certification.py exceeds bash timeout | Medium | Low | Class-level caching for all large-N tests |
| Integer User_ID fixture migration breaks unexpected tests | Medium | Medium | Systematic grep; update all occurrences before running suite |
| Determinism broken by boost cohort selection | Low | High | Boost selection uses deterministic `nlargest(key=engagement_score, user_id)` tie-break |
| Historical reconstruction tests too slow at large N | Low | Low | Use small fixture datasets (N=20 users, H=50 historical rows) for unit tests |
| VR-J001 test fixtures difficult to construct correctly | Medium | Medium | Build minimal fixtures: 2 users, 2 ads, explicit event records |

---

## SECTION 13 — ACCEPTANCE CRITERIA (TEST SUITE)

1. `pytest tests/test_e2e/test_remediation_certification.py -v` produces 57 passed, 0 failed, 0 errors.
2. `pytest tests/ -v` produces 0 failures across all test files.
3. `pytest tests/test_e2e/test_scale_certification.py -v` produces 50 passed with no SLA degradation.
4. `grep -r '"User_ID": [0-9]' tests/ --include="*.py"` returns no results (all integer User_IDs converted).
5. `pytest tests/test_utils/test_canonical_schema.py -v` produces all tests passed.
6. Total test count ≥ 1,260.

---

## SECTION 14 — DEFINITION OF DONE (TESTING)

- [ ] `test_canonical_schema.py` exists and passes (Wave 1).
- [ ] `test_trigger_journey_resolver.py` exists and passes (Wave 2).
- [ ] `test_historical_state_reconstructor.py` exists and passes (Wave 3).
- [ ] `test_cooling_override_service.py` exists and passes (Wave 4).
- [ ] `test_remediation_certification.py` exists with 57 tests; all pass (Wave 5).
- [ ] All integer User_ID fixtures converted to str (Wave 1).
- [ ] All TCC floor assertions updated (Wave 4).
- [ ] All NOT_STARTED event assertions removed (Wave 2).
- [ ] All existing 1,111 tests still pass.
- [ ] Scale tests 50/50 pass with no SLA degradation.
- [ ] Total test count ≥ 1,260.

---

## SECTION 15 — REGRESSION TEST REQUIREMENTS (COMPLETE)

### Regression Matrix — Per Defect

**CRIT-001:**
- Unit: `test_reconstructor_active_user_correct_position`, `test_reconstructor_capped_days_in_ad`
- E2E: `TestRC001` — historical user resumes mid-journey

**CRIT-002:**
- Unit: `test_trigger_config_ads_field`, `test_journey_engine_ads_override`, `test_resolver_trigger_routing`
- E2E: `TestRC002` — Trigger_A and Trigger_B use different journeys; events isolated

**CRIT-003:**
- Unit: `test_augment_trigger_df_adds_historical_users`
- E2E: `TestRC003` — 5 historically-active users absent from trigger_df appear in events_df

**CRIT-004:**
- Unit: Full `test_historical_state_reconstructor.py`
- E2E: `TestRC004` — reconstruct() output matches known historical fixture

**CRIT-005:**
- Unit: `test_reconstructor_cooling_active`, `test_reconstructor_re_entry`
- E2E: `TestRC005` — historically completed user in correct cooling state

**CRIT-006:**
- Unit: Full `test_cooling_override_service.py`
- E2E: `TestRC006` — cooling_override=True forces COOLING → RE_ENTRY

**CRIT-007:**
- Unit: `test_tcc_floor_min_one`, `test_boost_cohort_selection_deterministic`
- Integration: CTR calibration at TER=2%, 5%, 10%, 20% within ±20%
- E2E: `TestRC007` — end-to-end CTR accuracy at 2% TER

**CRIT-008:**
- Unit: `test_vr_j001_causal_chain`, `test_vr_j002_not_started`, `test_vr_j003_ctr`, `test_vr_j004_ter`, `test_vr_j005_duplicates`
- E2E: `TestRC008` — validation correctly classifies valid vs invalid journeys

**HIGH-001:**
- Unit: `test_canonical_schema_all_modules_import_from_single_source` (grep-based assertion)
- E2E: `TestRC009` — simulation runs; no column name errors

**HIGH-002:**
- Unit: `test_upload_page_trigger_cols_match_schema_validator`
- E2E: `TestRC010` — upload validation correctly accepts/rejects files

**HIGH-003:**
- Unit: `test_read_upload_csv_numeric_user_id_becomes_str`
- E2E: `TestRC011` — simulation with numeric User_ID CSV succeeds end-to-end

**HIGH-004:**
- Unit: `test_behavior_engine_no_events_for_not_started`
- E2E: `TestRC012` — events_df contains zero Not_Started journey_status rows

**HIGH-005:**
- Unit: `test_load_historical_file_extended_schema_parses_all_columns`
- E2E: `TestRC013` — 8-column historical file processed without error; reconstruction enabled

### Non-Regression Guard

The following existing test suites are the non-regression guard. They must pass at 100% after every wave:

1. `tests/test_e2e/test_business_rule_certification.py` (business rules unchanged)
2. `tests/test_e2e/test_historical_window_certification.py` (historical capacity counting unchanged)
3. `tests/test_e2e/test_multirun_persistence_certification.py` (multi-run chain unchanged)
4. `tests/test_e2e/test_scale_certification.py` (no SLA degradation)

---

*Document: TST-001 | TESTING_STRATEGY.md | v1.0 | 2026-06-23*
