# USER STATE REMEDIATION
## Engagement Data Generator — User State Changes

**Document ID:** USR-001  
**Version:** 1.0  
**Date:** 2026-06-23  
**Parent:** ARCHITECTURE_REMEDIATION_PACKAGE.md (ARP-001)  
**Defects Addressed:** CRIT-001 (partial), CRIT-003, CRIT-004, CRIT-005, CRIT-006, HIGH-004

---

## SECTION 1 — CURRENT STATE ASSESSMENT

### 1.1 UserState Initialization Contract

`UserState.new()` creates every user in a clean-slate initial state:
- `eligibility_status = EligibilityStatus.NEW`
- `journey_status = JourneyStatus.NOT_STARTED`
- `current_ad = None`
- `days_in_ad = None`
- `journey_step = None` (field does not yet exist)
- `cooling_period_end = None`
- `historical_engaged = False`

When `previous_state_df` is supplied, `UserStateManager.initialize_user_states()` merges returning users. Their `journey_status`, `current_ad`, `eligibility_status`, `cooling_period_end`, and engagement counters are carried forward. New users (absent from `previous_state_df`) are initialized with `UserState.new()`.

### 1.2 Audience Resolution and EligibilityStatus Transitions

`AudienceManager.resolve()` transitions eligibility after `initialize_user_states()`:

- Users with `journey_status=Completed` and `cooling_period_end <= sim_start` → `RE_ENTRY`
- Users with `journey_status=Completed` and `cooling_period_end > sim_start` → `COOLING`
- Users with `journey_status=Active` → `ACTIVE`
- Users with `journey_status=NOT_STARTED` → `NEW`
- TCC-capped users → `SKIPPED`

There is no mechanism to override `COOLING → RE_ENTRY` for a running simulation (CRIT-006).

### 1.3 Journey Status in Events (HIGH-004)

`EngagementGenerator` calls `BehaviorEngine.generate_events()` for all users in the state DataFrame. The guard `journey_status == Active` is applied by `JourneyEngine` before advancing, but `BehaviorEngine` receives the full `state_df` slice including users whose `journey_status=Not_Started`. When the engagement score is above threshold for a NOT_STARTED user (edge case, especially at the boundary between initialization and journey start), an event record with `journey_status=Not_Started` can be emitted.

### 1.4 Multi-Run Chain — Current Behavior

The ARCH-RISK-005 fix ensures `_final_sim_state` (post-simulation) is passed to `finalize_state()`. The returned `state_df` in `SimulationResult` carries: final `eligibility_status`, `journey_status`, `cooling_period_end`, and all engagement counters. This is passed as `previous_state_df` in a subsequent run and merged correctly via `UserStateManager.initialize_user_states()`.

### 1.5 Historical Reconstruction — Complete Absence

There is no `HistoricalStateReconstructor`. Historical data enters the pipeline as `historical_df` and is used only for capacity counting (ARCH-RISK-003 fix stamped `historical_engaged=True`). Historical data never drives:
- Journey position reconstruction (`current_ad`, `days_in_ad`, `journey_step`)
- Cooling period end date calculation from historical journey completion
- Eligibility status transitions (NEW vs ACTIVE vs COOLING) for historically-engaged users

The consequence: a user who received Ad_A in month 1 and Ad_B in month 2 (per historical records) will be placed at Ad_A again in month 3, starting the journey from scratch.

---

## SECTION 2 — DESIRED STATE

### 2.1 Historical State Reconstruction Pipeline

Before Stage 1 (UserStateManager), a new pre-stage runs `HistoricalStateReconstructor.reconstruct()` when:
1. `historical_df` is not None, AND
2. `historical_df` has the extended schema (contains `Ad_Name`, `Journey_Step`, `Trigger_Name`, `Completion_Date` columns)

The reconstructor produces `reconstructed_state_df`: a DataFrame in `UserState` layout with one row per user found in the historical file, with journey position and cooling period correctly populated.

### 2.2 Three-Way Merge in UserStateManager

`UserStateManager.initialize_user_states()` currently performs a two-way merge:
1. Users in `trigger_df` that also appear in `previous_state_df` → carry forward previous state
2. Users in `trigger_df` not in `previous_state_df` → initialize with `UserState.new()`

With this remediation, a three-way merge is performed:

```
Priority (highest to lowest):
  1. previous_state_df  — explicit prior-run state (multi-run chains)
  2. reconstructed_state_df — state derived from historical_df
  3. UserState.new()    — clean slate for brand-new users

Resolution: for each user_id in audience:
  if user_id in previous_state_df:
      use previous_state_df row (run-chain continuity takes priority)
  elif user_id in reconstructed_state_df:
      use reconstructed_state_df row (history-derived)
  else:
      use UserState.new()
```

### 2.3 Cooling Override Service

`CoolingOverrideService.apply(state_df, cooling_override=False)` must be called after Stage 2 (AudienceManager). When `cooling_override=True`:

```python
mask_cooling = (
    (df["eligibility_status"] == EligibilityStatus.COOLING.value)
    & (df["journey_status"] == JourneyStatus.COMPLETED.value)
)
if mask_cooling.any():
    df.loc[mask_cooling, "eligibility_status"] = EligibilityStatus.RE_ENTRY.value
    df.loc[mask_cooling, "cooling_override_applied"] = True
```

The `allow_reentry` flag remains unchanged — it still controls whether users are eligible to re-enter after cooling expires naturally. `cooling_override` separately allows bypassing the waiting period entirely. Both flags can coexist:
- `allow_reentry=False, cooling_override=False` → user permanently EXCLUDED after journey completion
- `allow_reentry=True, cooling_override=False` → user waits for cooling; re-enters naturally
- `allow_reentry=True, cooling_override=True` → user re-enters immediately regardless of cooling

### 2.4 Journey Status Gate in BehaviorEngine (HIGH-004)

`BehaviorEngine.generate_events()` and `BehaviorEngine.generate_clicks()` must filter the input DataFrame to `journey_status == Active` before processing. Any user with `journey_status != Active` must receive no events (not even Impressions). This is a hard pre-processing gate, not an output filter.

### 2.5 Historical Audience Continuity (CRIT-003)

After the three-way merge, the orchestrator must augment the trigger-file-derived audience with users from `reconstructed_state_df` who are NOT in the trigger file but whose reconstructed `journey_status=Active`. These users are mid-journey and must continue their journey even though they did not appear in the current trigger file.

---

## SECTION 3 — GAP ANALYSIS

### Gap G-USR-001: No HistoricalStateReconstructor

**Current:** Historical data enters pipeline; capacity counting runs; data discarded.  
**Required:** `HistoricalStateReconstructor` class reconstructs UserState from extended historical schema.  
**Impact:** All CRIT-001, CRIT-003, CRIT-004, CRIT-005 are blocked until this gap is closed.

### Gap G-USR-002: Two-way merge ignores historical reconstruction

**Current:** `initialize_user_states(trigger_df, previous_state_df)` — two inputs.  
**Required:** `initialize_user_states(trigger_df, previous_state_df, reconstructed_state_df)` — three inputs with explicit priority.  

### Gap G-USR-003: No CoolingOverrideService

**Current:** `allow_reentry` controls post-cooling eligibility. No bypass mechanism exists.  
**Required:** `CoolingOverrideService.apply()` + `cfg["cooling_override"]` UI toggle.

### Gap G-USR-004: BehaviorEngine generates events for NOT_STARTED users

**Current:** BehaviorEngine receives full state_df including NOT_STARTED users.  
**Required:** Hard gate: `state_df = state_df[state_df["journey_status"] == JourneyStatus.ACTIVE.value]` before any event generation.

### Gap G-USR-005: Historically-active users excluded from audience

**Current:** Audience is exactly `set(trigger_df["User_ID"])`.  
**Required:** Audience = `set(trigger_df["User_ID"]) ∪ set(historically_active_user_ids)`.

---

## SECTION 4 — ARCHITECTURE CHANGES

### 4.1 HistoricalStateReconstructor

**New file:** `core/historical_state_reconstructor.py`

**Contract:**

```python
class HistoricalStateReconstructor:
    def __init__(self, config: ConfigRegistry) -> None:
        ...

    def reconstruct(
        self,
        historical_df: pd.DataFrame,
        as_of_date: date,
    ) -> pd.DataFrame:
        """Reconstruct UserState rows from extended historical schema.

        For each distinct User_ID in historical_df:
          1. Sort engagements by Date descending.
          2. Find most recent qualifying engagement.
          3. If Completion_Date is set:
             - journey_status = Completed
             - journey_completion_date = Completion_Date
             - cooling_period_end = Completion_Date + timedelta(cooling_period_days)
             - eligibility_status = RE_ENTRY if as_of_date > cooling_period_end, else COOLING
          4. If no Completion_Date (journey still in progress):
             - journey_status = Active
             - current_ad = most recent Ad_Name
             - journey_step = most recent Journey_Step
             - days_in_ad = (as_of_date - most_recent_Date).days
             - eligibility_status = ACTIVE
          5. Set historical_engaged = True for all reconstructed users.

        Returns:
            pd.DataFrame with USER_STATE_REQUIRED_COLUMNS + journey fields.
            One row per unique User_ID.
        """
```

**Reconstruction algorithm (step-by-step):**

```
For each user_id U in historical_df:
  rows = historical_df[historical_df["User_ID"] == U].sort_values("Date", ascending=False)

  # Check if journey was completed
  completed_rows = rows[rows["Completion_Date"].notna()]
  if completed_rows.empty:
      # Journey still in progress
      most_recent = rows.iloc[0]
      ad_name = most_recent["Ad_Name"]
      journey_step = int(most_recent["Journey_Step"])
      days_since = (as_of_date - most_recent["Date"]).days
      # Find effective ads for this user's trigger
      trigger = config.get_trigger_by_name(most_recent["Trigger_Name"])
      effective_ads = trigger.get_effective_ads(config.ads) if trigger else config.ads
      # Determine actual days_in_ad (capped at ad duration)
      ad_config = next((a for a in effective_ads if a.ad_name == ad_name), None)
      max_days = ad_config.duration_days if ad_config else days_since
      days_in_ad = min(days_since, max_days)
      state = UserState(
          journey_status=JourneyStatus.ACTIVE,
          eligibility_status=EligibilityStatus.ACTIVE,
          current_ad=ad_name,
          journey_step=journey_step,
          days_in_ad=days_in_ad,
          journey_start_date=rows["Date"].min(),
          historical_engaged=True,
          ...
      )
  else:
      # Journey completed
      completion = completed_rows.sort_values("Completion_Date", ascending=False).iloc[0]
      completion_date = completion["Completion_Date"]
      cooling_end = completion_date + timedelta(days=config.cooling_period_days)
      state = UserState(
          journey_status=JourneyStatus.COMPLETED,
          eligibility_status=(
              EligibilityStatus.RE_ENTRY if as_of_date > cooling_end
              else EligibilityStatus.COOLING
          ),
          journey_completion_date=completion_date,
          cooling_period_end=cooling_end,
          current_ad=None,
          journey_step=None,
          historical_engaged=True,
          ...
      )
  return state
```

### 4.2 UserStateManager Changes

**Modified file:** `core/user_state_manager.py`

Signature change:

```python
def initialize_user_states(
    self,
    trigger_df: pd.DataFrame,
    previous_state_df: pd.DataFrame | None = None,
    reconstructed_state_df: pd.DataFrame | None = None,   # NEW
) -> pd.DataFrame:
```

Three-way merge logic:

```python
def _merge_state_sources(
    self,
    trigger_user_ids: set[str],
    previous_state_df: pd.DataFrame | None,
    reconstructed_state_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Merge state from three sources with explicit priority."""
    rows = []
    for uid in trigger_user_ids:
        if previous_state_df is not None and uid in _uid_set(previous_state_df):
            rows.append(_get_row(previous_state_df, uid))
        elif reconstructed_state_df is not None and uid in _uid_set(reconstructed_state_df):
            rows.append(_get_row(reconstructed_state_df, uid))
        else:
            rows.append(UserState.new(campaign_id, uid, as_of_date, ad_names))
    return pd.DataFrame([dataclasses.asdict(r) for r in rows])
```

### 4.3 Orchestrator Changes

**Modified file:** `core/simulation_orchestrator.py`

Pre-Stage 1 injection:

```python
# ── Pre-Stage 1: Historical State Reconstruction ─────────────────────
reconstructed_state_df = None
if historical_df is not None and len(historical_df) > 0:
    if CanonicalSchema.historical_file_has_extended_schema(historical_df):
        reconstructed_state_df = self._run_stage(
            "HistoricalStateReconstructor",
            stage_timings,
            lambda: HistoricalStateReconstructor(cfg).reconstruct(
                historical_df, as_of_date=sim_start
            ),
        )
        logger.info(
            "HistoricalStateReconstructor: reconstructed state for %d users",
            len(reconstructed_state_df),
        )

# ── Stage 1 (modified) ────────────────────────────────────────────────
state_df = self._run_stage(
    "UserStateManager",
    stage_timings,
    lambda: UserStateManager(cfg).initialize_user_states(
        trigger_df,
        previous_state_df=previous_state_df,
        reconstructed_state_df=reconstructed_state_df,
    ),
)

# ── CRIT-003: Augment trigger audience with historically-active users ─
if reconstructed_state_df is not None:
    hist_active = reconstructed_state_df[
        reconstructed_state_df["journey_status"] == JourneyStatus.ACTIVE.value
    ]
    hist_active_not_in_trigger = hist_active[
        ~hist_active["user_id"].isin(set(trigger_df["User_ID"].astype(str)))
    ]
    if len(hist_active_not_in_trigger) > 0:
        trigger_df = _augment_trigger_df(trigger_df, hist_active_not_in_trigger)
        logger.info(
            "CRIT-003: augmented trigger_df with %d historically-active users",
            len(hist_active_not_in_trigger),
        )

# ── Post-Stage 2: Cooling Override ───────────────────────────────────
cooling_override = getattr(cfg, "cooling_override", False)
if cooling_override:
    audience_df = self._run_stage(
        "CoolingOverrideService",
        stage_timings,
        lambda: CoolingOverrideService().apply(audience_df, cooling_override=True),
    )
```

---

## SECTION 5 — DATA MODEL CHANGES

New fields on `UserState` (defined in full in `DATA_MODEL_REMEDIATION.md`):
- `journey_step: int | None` — written by JourneyEngine
- `trigger_ads_key: str | None` — written at journey start
- `cooling_override_applied: bool` — written by CoolingOverrideService

`HistoricalStateReconstructor` output schema must exactly match `USER_STATE_REQUIRED_COLUMNS` plus all journey-position fields. The orchestrator passes this DataFrame as `reconstructed_state_df` to Stage 1. Its columns are a strict subset of the full `UserState` column set; missing columns (e.g., creative affinities) receive defaults.

---

## SECTION 6 — USER STATE CHANGES (DETAILED)

### 6.1 EligibilityStatus Transition Matrix

```
Source                         Condition                              → eligibility_status
─────────────────────────────────────────────────────────────────────────────────────────
HistoricalStateReconstructor   Journey in progress                    ACTIVE
HistoricalStateReconstructor   Journey completed, cooling active      COOLING
HistoricalStateReconstructor   Journey completed, cooling expired     RE_ENTRY
HistoricalStateReconstructor   No qualifying history                  NEW
UserState.new()                No prior state                         NEW
previous_state_df carry-fwd    journey_status=Active                  ACTIVE (preserved)
previous_state_df carry-fwd    journey_status=Completed,cooling>now  COOLING (re-evaluated)
previous_state_df carry-fwd    journey_status=Completed,cooling≤now  RE_ENTRY (re-evaluated)
CoolingOverrideService         eligibility_status=COOLING, override   RE_ENTRY (forced)
AudienceManager TCC            capacity=0                             SKIPPED
AudienceManager                allow_reentry=False, Completed        EXCLUDED
```

### 6.2 Journey Status Gate in BehaviorEngine

```python
# BEFORE (HIGH-004 bug):
def generate_events(self, state_df: pd.DataFrame, ...) -> pd.DataFrame:
    # no journey_status gate
    # processes ALL users including NOT_STARTED

# AFTER (HIGH-004 fix):
def generate_events(self, state_df: pd.DataFrame, ...) -> pd.DataFrame:
    active_mask = state_df["journey_status"] == JourneyStatus.ACTIVE.value
    if not active_mask.any():
        return pd.DataFrame(columns=_EVENT_COLS)  # empty
    active_df = state_df[active_mask].copy()
    # ... rest of event generation on active_df only
```

### 6.3 finalize_state Changes

`UserStateManager.finalize_state()` currently accepts `_final_sim_state` (ARCH-RISK-005 fix). No changes required here — it already correctly snapshots the post-simulation state including all journey fields. The new `journey_step`, `trigger_ads_key`, and `cooling_override_applied` fields are preserved automatically because they are columns on the state DataFrame.

---

## SECTION 7 — UI CHANGES

### Business Rules Page — Cooling Override Toggle

```python
# Add to business_rules_page.py after "Allow Re-entry" checkbox:
cfg["cooling_override"] = st.checkbox(
    "Override Cooling Period (this run only)",
    value=bool(cfg.get("cooling_override", False)),
    help=(
        "When enabled, users currently in their post-journey cooling period "
        "will be eligible to re-enter the journey immediately in this simulation run. "
        "This does not permanently change the cooling period setting. "
        "Requires 'Allow Re-entry' to also be enabled."
    )
)
if cfg.get("cooling_override") and not cfg.get("allow_reentry"):
    st.warning(
        "⚠️ Cooling Override has no effect when Allow Re-entry is disabled. "
        "Enable Allow Re-entry to use this feature."
    )
```

### Results Page — Historical Reconstruction Summary

When `reconstructed_state_df` is available in `SimulationResult`, the results page must display a summary:

```
Historical Reconstruction Summary:
  • Users reconstructed from history: N
  • Currently Active (mid-journey): N
  • In Cooling: N
  • Eligible for Re-Entry: N
  • Cooling Override Applied: N
```

---

## SECTION 8 — VALIDATION CHANGES

### VR-USR-001: No NOT_STARTED Events

Hard validation rule: if `events_df` contains any row where `journey_status = "Not_Started"`, the rule FAILS. Implementation: `events_df["journey_status"].ne("Not_Started").all()` — if False, emit VR-J002 FAIL.

### VR-USR-002: Historical Reconstruction Consistency

Advisory rule (only when `historical_df` has extended schema): for each user in `reconstructed_state_df` whose `journey_status=Active`, the final `events_df` must contain at least one event for that user on their reconstructed `current_ad`. If the user's reconstructed position is not honored, this advisory rule fires.

---

## SECTION 9 — MIGRATION STRATEGY

### 9.1 reconstructed_state_df as New Optional Parameter

`initialize_user_states()` receives a new optional `reconstructed_state_df=None`. When None (the default), behavior is identical to the current implementation — the three-way merge degenerates to the existing two-way merge. No existing call sites need updating.

### 9.2 Previous State Compatibility with New Fields

`UserStateManager._reconcile_user_state_columns()` must add the following handling for state DataFrames that pre-date this remediation:

```python
# Fill new fields with defaults for pre-V2 state DataFrames
if "journey_step" not in df.columns:
    df["journey_step"] = None
if "trigger_ads_key" not in df.columns:
    df["trigger_ads_key"] = None
if "cooling_override_applied" not in df.columns:
    df["cooling_override_applied"] = False
```

### 9.3 ConfigRegistry cooling_override Field

`ConfigRegistry` must add:

```python
cooling_override: bool = False
"""When True, CoolingOverrideService forces all COOLING users to RE_ENTRY.
Requires allow_reentry=True to have any effect.
"""
```

`config_loader.py` must parse this from the config dict when present. Default False preserves backward compatibility.

---

## SECTION 10 — BACKWARD COMPATIBILITY ASSESSMENT

| Change | Backward Compatible | Notes |
|--------|--------------------|-|
| `initialize_user_states` new optional param | YES | `reconstructed_state_df=None` default |
| `CoolingOverrideService` | YES | Only runs when `cooling_override=True` |
| `ConfigRegistry.cooling_override = False` | YES | Default False; existing configs unaffected |
| `BehaviorEngine` journey_status gate | POTENTIALLY | Removes events for NOT_STARTED users; existing tests asserting those events must be updated |
| New UserState fields | YES | Defaults provided; reconciliation fills missing columns |
| `HistoricalStateReconstructor` | YES | Only invoked when extended schema present; no-op otherwise |

---

## SECTION 11 — PERFORMANCE IMPACT

| Change | Impact | Notes |
|--------|--------|-------|
| `HistoricalStateReconstructor.reconstruct()` | O(H) where H = historical rows | Vectorized groupby on User_ID; fast at typical H < 1M |
| Three-way merge in `initialize_user_states` | O(N+H) | Two set lookups per user; negligible |
| `CoolingOverrideService` | O(U) boolean mask | Sub-1ms at 100k |
| BehaviorEngine journey_status gate | O(U) boolean filter | Removes NOT_STARTED users early; net performance improvement |
| Historically-active user augmentation | O(A) where A = active hist users | Small; typically A << N |

---

## SECTION 12 — RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| `HistoricalStateReconstructor` reconstructs wrong journey position | Medium | High | Deterministic reconstruction; unit tests with known historical fixtures |
| Three-way merge priority inversion | Low | High | Explicit unit test: same user in both previous and reconstructed → previous wins |
| `cooling_override` enabled globally by accident | Low | Medium | UI: checkbox defaults to False; tooltip warns "this run only" |
| BehaviorEngine gate removes users who should receive events | Low | Medium | Test: user with journey_status=Active still receives events after gate |
| Historically-active users injected with wrong trigger data | Medium | Medium | `_augment_trigger_df` must synthesize trigger row from reconstructed state |

---

## SECTION 13 — ACCEPTANCE CRITERIA

1. `HistoricalStateReconstructor.reconstruct()` given a user with last engagement on Ad_B (step 2) on date D, with no Completion_Date, with `as_of_date=D+5`, produces a row with `current_ad="Ad_B"`, `journey_step=2`, `days_in_ad=5`.

2. Given a user with `Completion_Date=D` and `cooling_period_days=14`, `as_of_date=D+10`: reconstructed state has `eligibility_status=COOLING`, `cooling_period_end=D+14`.

3. Given `as_of_date=D+20` (cooling expired): reconstructed state has `eligibility_status=RE_ENTRY`.

4. `initialize_user_states` with the same user in both `previous_state_df` and `reconstructed_state_df`: `previous_state_df` row is used (priority 1 wins).

5. `initialize_user_states` with a user in `reconstructed_state_df` only (not in trigger, not in previous): user appears in output with reconstructed state.

6. `CoolingOverrideService.apply(df, cooling_override=True)` changes all `COOLING`+`Completed` rows to `RE_ENTRY`; `cooling_override_applied=True` on each.

7. `BehaviorEngine.generate_events()` produces zero event rows for users with `journey_status=Not_Started`.

8. `events_df` contains zero rows with `journey_status="Not_Started"` in any end-to-end simulation run.

---

## SECTION 14 — DEFINITION OF DONE

- [ ] `core/historical_state_reconstructor.py` created with `HistoricalStateReconstructor` class.
- [ ] `core/cooling_override_service.py` created with `CoolingOverrideService` class.
- [ ] `UserStateManager.initialize_user_states()` accepts `reconstructed_state_df` param with three-way merge.
- [ ] `SimulationOrchestrator.run()` invokes `HistoricalStateReconstructor` pre-Stage 1.
- [ ] `SimulationOrchestrator.run()` augments trigger audience with historically-active users.
- [ ] `SimulationOrchestrator.run()` invokes `CoolingOverrideService` post-Stage 2.
- [ ] `BehaviorEngine.generate_events()` gates on `journey_status=Active`.
- [ ] `ConfigRegistry` has `cooling_override: bool = False` field.
- [ ] `UserState` has `journey_step`, `trigger_ads_key`, `cooling_override_applied` fields.
- [ ] `UserState.new()` initializes all three new fields.
- [ ] `UserStateManager._reconcile_user_state_columns()` fills new fields from legacy state_df.
- [ ] `business_rules_page.py` has "Override Cooling Period" checkbox.
- [ ] All acceptance criteria tests pass.
- [ ] Full regression suite passes with 0 failures.

---

## SECTION 15 — REGRESSION TEST REQUIREMENTS

### New Test Files

**`tests/test_core/test_historical_state_reconstructor.py`**
- `test_reconstruct_active_user_correct_journey_step`
- `test_reconstruct_active_user_correct_days_in_ad`
- `test_reconstruct_completed_user_cooling_active`
- `test_reconstruct_completed_user_cooling_expired_re_entry`
- `test_reconstruct_empty_historical_returns_empty_df`
- `test_reconstruct_multiple_users_independent`
- `test_reconstruct_uses_trigger_specific_ads`
- `test_reconstruct_no_extended_schema_not_called`

**`tests/test_core/test_cooling_override_service.py`**
- `test_apply_no_override_no_change`
- `test_apply_override_true_cooling_users_become_re_entry`
- `test_apply_override_sets_cooling_override_applied_true`
- `test_apply_override_does_not_affect_active_users`
- `test_apply_override_does_not_affect_excluded_users`

**`tests/test_core/test_user_state_manager.py` — additions**
- `test_three_way_merge_previous_wins_over_reconstructed`
- `test_three_way_merge_reconstructed_wins_over_new`
- `test_three_way_merge_new_user_gets_defaults`
- `test_initialize_user_states_reconstructed_none_behaves_as_before`

**`tests/test_core/test_behavior_engine.py` — additions**
- `test_generate_events_not_started_users_receive_no_events`
- `test_generate_events_active_users_still_receive_events`

### Existing Tests to Update

- `tests/test_e2e/test_multirun_persistence_certification.py`: add `MR-011` class verifying historical reconstruction state passes through multi-run chain.

---

*Document: USR-001 | USER_STATE_REMEDIATION.md | v1.0 | 2026-06-23*
