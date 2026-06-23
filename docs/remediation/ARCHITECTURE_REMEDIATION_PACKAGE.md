# ARCHITECTURE REMEDIATION PACKAGE
## Engagement Data Generator — Production Defect & Gap Resolution

**Document ID:** ARP-001  
**Version:** 1.0  
**Date:** 2026-06-23  
**Classification:** Production-Critical — Engineering Execution Required  
**Status:** APPROVED FOR IMPLEMENTATION  

---

## EXECUTIVE SUMMARY

Post-deployment production testing of the Engagement Data Generator revealed thirteen defects and gaps spanning critical business logic, data modelling, user state management, and UI validation. Eight are classified CRITICAL (system produces incorrect results silently); five are classified HIGH (data integrity and operational risk). This package is the authoritative remediation architecture. It defines the complete desired state, precise gap analysis, implementation contracts, backward compatibility constraints, and regression requirements for each defect.

The remediation is organized into five implementation waves. Waves 1–2 address data model and schema foundation work. Waves 3–4 implement the core business logic changes. Wave 5 closes validation, UI, and test coverage gaps. No wave may begin until its predecessor's exit criteria are fully satisfied.

---

## SECTION 1 — CURRENT STATE ASSESSMENT

### 1.1 Simulation Pipeline

The system executes a six-stage orchestrated pipeline:

```
Stage 1: UserStateManager.initialize_user_states(trigger_df, previous_state_df)
Stage 2: AudienceManager.resolve(trigger_df, historical_df, state_df, as_of_date)
Stage 3: EngagementGenerator.generate(audience_df, sim_start, sim_end) → 4-tuple
Stage 4: ValidationEngine.validate(events_df, audience_df)
Stage 5: ExcelExporter.export(...) [optional]
Stage 6: UserStateManager.finalize_state(_final_sim_state, as_of_date)
```

Stage 1 initializes user state rows from the trigger file, merging with `previous_state_df` for returning users. Stage 2 resolves the eligible audience, computing TCC (Trigger Capacity Ceiling) from `historical_df`. Stage 3 runs the daily simulation loop: journey advancement → TCC enforcement → event generation. Stage 4 validates output. Stage 6 persists final state for multi-run chains.

### 1.2 ConfigRegistry Architecture

`ConfigRegistry` is a frozen dataclass holding the global campaign configuration. Critically, it owns a single `ads: tuple[AdConfig, ...]` field — a global journey shared across ALL triggers. There is no mechanism for trigger-specific ad sequences. `TriggerConfig` contains only `trigger_name`, `priority`, `engagement_rate_target`, and `distribution_pct`. Ad-sequence ownership is not scoped to any trigger.

### 1.3 Historical Data Processing

`historical_df` is used exclusively for capacity computation. `AudienceManager.compute_remaining_capacity()` counts distinct engaged users in the historical window to reduce TCC. The ARCH-RISK-003 fix stamped `historical_engaged=True` on matching audience rows so `EngagementGenerator` reduces capacity for historically engaged users. Historical data is **never** used to: reconstruct journey position, determine current ad, calculate days in ad, set cooling period end dates, or admit users not present in the current trigger file.

### 1.4 User State Initialization

`UserState.new()` creates all users at `EligibilityStatus.NEW` / `JourneyStatus.NOT_STARTED`. Journey position fields (`current_ad`, `days_in_ad`, `journey_start_date`, `ad_click_received`) are all initialized to None/False. When `previous_state_df` is provided, returning users have their state carried forward — but only if they appear in the current trigger file. Users who completed a journey in a prior run and are absent from the current trigger file are not processed at all.

### 1.5 CTR and TER Generation

`BehaviorEngine` computes per-user click probability from `ad.target_ctr` scaled by the composite engagement score. However, at low TER targets (2%), the TCC cap limits total qualifying events, and the composite score often produces scores below the CTR threshold for most users — resulting in observed CTR=0% even when target=2%. The engagement score initialization (0.5 neutral) combined with the default behavior profile (MODERATE) and the five-component weighted scoring formula produces insufficient click generation probability for low-volume targets.

### 1.6 UI Validation Discrepancies

`upload_page.py` enforces `_TRIGGER_REQUIRED_COLS = {"Campaign_ID", "User_ID", "Trigger_Name", "Segment"}`. `schema_validator.py` enforces `TRIGGER_FILE_REQUIRED_COLUMNS = ["User_ID", "Trigger_Name", "Trigger_Date", "Segment"]`. These are different: UI requires `Campaign_ID` (which schema_validator treats as optional via BIZ-019), UI does not require `Trigger_Date` (which schema_validator requires). For historical files: UI checks `{"user_id", "campaign_id"}` (lowercase) while `HISTORICAL_FILE_REQUIRED_COLUMNS = ["User_ID", "Date", "Action", "Channel"]`. UI guidance is incorrect for both file types.

---

## SECTION 2 — DESIRED STATE

### 2.1 Historical Journey Continuation (CRIT-001)

When a historical engagement file is supplied, the system must reconstruct each user's current journey position. For each user in the historical file: find their most recent qualifying engagement, identify which ad it corresponds to (by `Ad_Name` column in the historical schema), determine how many days have elapsed since that engagement, and set `current_ad`, `days_in_ad`, `journey_status=Active`, and `journey_start_date` accordingly. Users with a historical journey completion must enter the cooling period calculation path (CRIT-005).

### 2.2 Trigger-Specific Journeys (CRIT-002)

Each `TriggerConfig` must own an independent ordered ad sequence. The campaign-level `ads` tuple in `ConfigRegistry` becomes a default fallback only. When a `TriggerConfig` carries its own `ads: tuple[AdConfig, ...] | None`, those ads govern that trigger's users exclusively. `JourneyEngine` must accept the trigger-specific ad sequence when advancing users belonging to that trigger.

### 2.3 Historical Audience Continuity (CRIT-003)

Users who are currently progressing through a journey (identifiable from historical data) must remain eligible even if they do not appear in the current simulation's trigger file. The orchestrator must merge historically-active users into the audience alongside trigger-file users before Stage 3 begins.

### 2.4 Historical State Reconstruction (CRIT-004)

A new `HistoricalStateReconstructor` service must be able to rebuild a `UserState`-compatible DataFrame from historical engagement data alone. This is the foundation for CRIT-001 and CRIT-003.

### 2.5 Cooling Period from History (CRIT-005)

`journey_completion_date` must be derivable from historical data (the date of the last qualifying engagement on the terminal ad). Cooling period end must be calculated as `journey_completion_date + timedelta(days=cooling_period_days)`.

### 2.6 Cooling Period Override (CRIT-006)

A UI toggle "Override Cooling Period" must set all cooling-period-constrained users directly to `RE_ENTRY` regardless of `cooling_period_end`. This is distinct from `allow_reentry` (which controls whether re-entry is permitted at all after cooling expires). The override bypasses the cooling period entirely for the current run.

### 2.7 CTR/TER Accuracy (CRIT-007)

Observed CTR must reach target CTR within ±20% tolerance. The BehaviorEngine click-generation path must be redesigned so that at low TER targets (2–5%), the system selects a targeted cohort of users and assigns them a sufficiently high engagement score to generate qualifying clicks. The current approach of applying target_ctr uniformly against a mid-range composite score fails at low volumes.

### 2.8 Journey Progression Gating (CRIT-008)

The system must enforce and report: Ad1→Click→Ad2→Click→Ad3 gating (when `move_on_click=True`), open progression for email/WhatsApp (Impression→Open→Click), journey completion detection, drop-off detection (user never clicked on terminal ad before simulation end), and re-entry path validation.

### 2.9 Canonical Schema (HIGH-001)

A single canonical column-name registry must exist. Internal (lowercase snake_case) and external (Title_Case) representations must be explicitly defined and consistently applied. `Campaign_ID` is the canonical external name; `campaign_id` is the canonical internal name. No code may use ambiguous casing.

### 2.10 Upload Validation Alignment (HIGH-002)

`upload_page.py` validation must exactly match `schema_validator.py` requirements. Both must enforce the same required columns for both file types.

### 2.11 User_ID Type Safety (HIGH-003)

`upload_page.py` reads files without `dtype=str`, meaning numeric User_IDs remain as `int64`. All downstream code — MD5 seeding, join keys, state_df merge — expects string User_IDs. Type coercion to `str` must occur at the earliest ingestion point (the upload page read).

### 2.12 Journey Status Consistency (HIGH-004)

Events may not be generated for users whose `journey_status=Not_Started`. The BehaviorEngine event-generation path must gate on `journey_status == Active` before producing any event record.

### 2.13 Historical Schema Extension (HIGH-005)

The historical engagement file schema must be extended to include: `Ad_Name`, `Journey_Step` (1-based integer), `Trigger_Name`, and `Completion_Date` (nullable, set on terminal-ad engagement). These fields are required by CRIT-001, CRIT-004, and CRIT-005 to reconstruct journey position from history.

---

## SECTION 3 — GAP ANALYSIS

| Defect ID | Category | Root Cause | Blast Radius |
|-----------|----------|-----------|--------------|
| CRIT-001 | Historical journey continuation | Historical data pipeline terminates after capacity counting; no journey reconstruction service exists | All users with prior engagement history start at Ad1 regardless of progress |
| CRIT-002 | Trigger-specific journeys | `TriggerConfig` has no `ads` field; `ConfigRegistry.ads` is global | All triggers use identical ad sequence; multi-trigger campaigns cannot differentiate journeys |
| CRIT-003 | Historical audience continuity | Audience resolution restricted to `trigger_df` users; no historical-active user injection | Mid-journey users disappear from simulation if not re-triggered |
| CRIT-004 | State reconstruction | No `HistoricalStateReconstructor` class exists anywhere in the codebase | First-run scenarios with historical data cannot bootstrap accurate user state |
| CRIT-005 | Cooling from history | `journey_completion_date` only set by `JourneyEngine._complete_journeys()` during live simulation | Historical completions not recognised; historically-completed users always re-enter immediately |
| CRIT-006 | Cooling override | `allow_reentry` controls post-cooling eligibility, not cooling bypass | No mechanism to force users into RE_ENTRY during a run regardless of cooling_period_end |
| CRIT-007 | CTR/TER accuracy | Composite score uniformly initialized at 0.5; TCC cap too aggressive at low TER; no targeted-cohort selection | Observed CTR=0% at 2% target; TER never achieved |
| CRIT-008 | Journey gating validation | ValidationEngine does not enforce Ad→Click→Ad progression sequence; no causal chain rule exists | Invalid journeys (Ad2 without Ad1 Click) pass validation silently |
| HIGH-001 | Column name inconsistency | No canonical schema registry; modules independently defined column names | Cross-module DataFrame operations fail on casing mismatch; merge/join bugs |
| HIGH-002 | Upload validation mismatch | `upload_page.py` and `schema_validator.py` defined requirements independently | User sees confusing error: file accepted by UI validation but rejected by pipeline |
| HIGH-003 | User_ID type safety | `upload_page.py` reads CSV/Excel without `dtype=str` | MD5 seed computation fails on int User_IDs; state merge produces NaN rows |
| HIGH-004 | Journey status in events | `EngagementGenerator` does not gate event generation on `journey_status=Active` | Events appear in output with `journey_status=Not_Started`; downstream analytics corrupted |
| HIGH-005 | Historical schema deficiency | Historical file spec never updated to include journey fields | CRIT-001/004/005 cannot be implemented; journey reconstruction has no data source |

---

## SECTION 4 — ARCHITECTURE CHANGES

### 4.1 New Components

**`HistoricalStateReconstructor`** (`core/historical_state_reconstructor.py`)  
Accepts `historical_df` (with extended schema) and `ConfigRegistry`. Returns a `pd.DataFrame` in `USER_STATE_REQUIRED_COLUMNS` format with reconstructed journey position for each user found in history. This is a pure function with no side effects. See `HISTORICAL_PROCESSING_REMEDIATION.md` for full specification.

**`TriggerJourneyResolver`** (`core/trigger_journey_resolver.py`)  
Accepts `TriggerConfig` and `ConfigRegistry`. Returns the effective `tuple[AdConfig, ...]` for a given trigger — the trigger's own ads if defined, falling back to `ConfigRegistry.ads`. Used by `JourneyEngine` and `EngagementGenerator` to resolve the correct ad sequence per trigger cohort.

**`CoolingOverrideService`** (`core/cooling_override_service.py`)  
Accepts a `state_df` and a boolean `override_cooling` flag. When `True`, sets `eligibility_status=RE_ENTRY` for all users whose `eligibility_status=COOLING` and `journey_status=Completed`, regardless of `cooling_period_end`. Returns modified `state_df`.

**`CanonicalSchema`** (`utils/canonical_schema.py`)  
Authoritative mapping of all column names between internal (snake_case) and external (Title_Case) representations. Replaces ad-hoc column definitions scattered across `upload_page.py`, `schema_validator.py`, and `simulation_orchestrator.py`.

### 4.2 Modified Components

**`TriggerConfig`** — add `ads: tuple[AdConfig, ...] | None = None` field.

**`JourneyEngine`** — accept optional `trigger_ads: tuple[AdConfig, ...] | None` at construction; use these instead of `config.ads` when provided.

**`EngagementGenerator`** — per-trigger cohort processing; construct `JourneyEngine` with trigger-specific ads per cohort.

**`SimulationOrchestrator`** — inject `HistoricalStateReconstructor` before Stage 1; inject `CoolingOverrideService` after Stage 2 when cooling_override=True.

**`BehaviorEngine`** — redesign click-generation to use targeted-cohort selection for low-volume TER targets.

**`upload_page.py`** — add `dtype=str` to all file reads; align validation against `CanonicalSchema`.

**`schema_validator.py`** — update `TRIGGER_FILE_REQUIRED_COLUMNS` and `HISTORICAL_FILE_REQUIRED_COLUMNS` to match UI guidance and extended historical schema.

### 4.3 Pipeline Changes

```
[NEW] Pre-Stage 1: HistoricalStateReconstructor.reconstruct(historical_df, config)
                   → reconstructed_state_df

Stage 1 (modified): UserStateManager.initialize_user_states(
                      trigger_df,
                      previous_state_df=previous_state_df,
                      reconstructed_state_df=reconstructed_state_df,   ← NEW
                    )

[NEW] Post-Stage 2: CoolingOverrideService.apply(audience_df, cooling_override)
                   → audience_df

[NEW] Post-Stage 2: AudienceManager inject historically-active users
                   not present in trigger_df (CRIT-003)

Stage 3 (modified): EngagementGenerator processes per-trigger cohorts
                   with trigger-scoped JourneyEngine instances
```

---

## SECTION 5 — DATA MODEL CHANGES

See `DATA_MODEL_REMEDIATION.md` for complete specification. Summary:

**`TriggerConfig`** — add `ads: tuple[AdConfig, ...] | None = None`.

**`UserState`** — add `journey_step: int | None` (1-based current ad position), `trigger_ads_key: str | None` (hash of trigger's ad sequence for change detection).

**Historical file schema** — add `Ad_Name: str`, `Journey_Step: int`, `Trigger_Name: str`, `Completion_Date: date | None`.

**`CanonicalSchema`** — new module defining all 35+ column names with both internal and external representations.

---

## SECTION 6 — USER STATE CHANGES

See `USER_STATE_REMEDIATION.md` for complete specification. Summary:

Three new `UserState` fields: `journey_step` (current 1-based position in ad sequence), `trigger_ads_key` (fingerprint of the trigger's ad sequence to detect mid-run changes), `cooling_override_applied` (boolean flag set by `CoolingOverrideService` for audit trail).

`UserState.new()` must initialize all three new fields to their None/False defaults.

`UserStateManager.initialize_user_states()` must accept and merge `reconstructed_state_df`.

---

## SECTION 7 — UI CHANGES

**Upload Page (`upload_page.py`)**

1. Change `pd.read_csv(uploaded_file)` to `pd.read_csv(uploaded_file, dtype=str)`.
2. Change `pd.read_excel(uploaded_file)` to `pd.read_excel(uploaded_file, dtype=str)`.
3. Replace `_TRIGGER_REQUIRED_COLS` with `CanonicalSchema.TRIGGER_FILE_REQUIRED_COLUMNS`.
4. Replace `_HISTORICAL_REQUIRED_COLS` with `CanonicalSchema.HISTORICAL_FILE_REQUIRED_COLUMNS`.
5. Add column presence feedback: show which required columns were found vs missing.

**Business Rules Page (`business_rules_page.py`)**

1. Add "Override Cooling Period" checkbox (default: False). Writes `cfg["cooling_override"] = True/False`.
2. Add tooltip: "When enabled, users currently in their cooling period will be eligible to re-enter the journey immediately in this simulation run."

**Campaign Page (`campaign_page.py`)**

1. Add per-trigger "Ad Journey" section. When a trigger expands, show an optional "Use custom ad sequence for this trigger" toggle. When toggled, show the same ad-definition UI that currently exists at campaign level, scoped to that trigger.
2. The campaign-level ad sequence becomes the default; trigger-level overrides it when defined.

---

## SECTION 8 — VALIDATION CHANGES

**`ValidationEngine`** must add the following new rules:

| Rule ID | Description | Severity |
|---------|-------------|----------|
| VR-J001 | Journey causal chain: if current_ad=Ad_N (N>1) then at least one Click event for Ad_(N-1) must exist for this user | Hard |
| VR-J002 | Journey status consistency: no event record may have journey_status=Not_Started | Hard |
| VR-J003 | CTR achieved within ±20% of target per ad | Soft |
| VR-J004 | TER achieved within ±20% of target per trigger | Soft |
| VR-J005 | No duplicate (user_id, simulation_date, ad_name, action_type) rows in events_df | Hard |
| VR-H001 | Historical user journey position matches reconstructed position (when historical_df provided) | Advisory |

---

## SECTION 9 — MIGRATION STRATEGY

### 9.1 Historical File Schema Migration

Existing historical files with the 4-column schema (`User_ID`, `Date`, `Action`, `Channel`) must remain loadable. The extended schema adds 4 optional columns (`Ad_Name`, `Journey_Step`, `Trigger_Name`, `Completion_Date`). `input_loader.load_historical_file()` must treat these as optional and skip journey reconstruction when they are absent.

### 9.2 ConfigRegistry Migration

`TriggerConfig.ads = None` (default) preserves backward compatibility — existing configurations without trigger-specific ads continue to use `ConfigRegistry.ads` as the single journey.

### 9.3 UserState Migration

New `UserState` fields (`journey_step`, `trigger_ads_key`, `cooling_override_applied`) have default values (`None`, `None`, `False`). Existing `previous_state_df` DataFrames without these columns will have them filled with defaults during `UserStateManager.initialize_user_states()` via `_reconcile_columns()`.

### 9.4 Multi-Run Chain Migration

The `ARCH-RISK-005` fix already ensures `_final_sim_state` is persisted correctly. The new fields added in this remediation are appended to the state columns that `finalize_state()` outputs. Existing `run1.state_df` passed as `previous_state_df` into `run2` will receive default fills for the new columns — no breaking change.

---

## SECTION 10 — BACKWARD COMPATIBILITY ASSESSMENT

| Change | Backward Compatible | Notes |
|--------|--------------------|-|
| `TriggerConfig.ads = None` | YES | Default None; existing TriggerConfig instances unchanged |
| Extended historical schema | YES | New columns optional; 4-column files still load |
| `UserState` new fields | YES | Defaults provided; existing state_df reconciled on load |
| `JourneyEngine` trigger_ads param | YES | Optional param; defaults to `config.ads` |
| `CanonicalSchema` module | YES | Pure addition; replaces local defs via import change |
| Upload page dtype=str | BREAKING | Int User_IDs become str; any downstream int comparison breaks |
| `CoolingOverrideService` | YES | New service; not invoked unless `cooling_override=True` |
| `HistoricalStateReconstructor` | YES | New service; only invoked when historical file has extended schema |
| New ValidationEngine rules VR-J001–VR-J005 | POTENTIALLY | New Hard rules may fail existing test fixtures |

**The only breaking change** is the dtype=str coercion for User_ID (HIGH-003). All test fixtures that use integer User_IDs must be updated to use string User_IDs. This is the sole migration-breaking item.

---

## SECTION 11 — PERFORMANCE IMPACT

| Change | Expected Impact | Mitigation |
|--------|----------------|-----------|
| `HistoricalStateReconstructor` | +O(H) where H = historical rows | Runs once pre-Stage 1; cached result |
| Trigger-specific JourneyEngine instances | +O(T) construction overhead, T = trigger count | T is bounded by UI (max 10); negligible |
| Per-trigger cohort processing in EngagementGenerator | No change — already iterates all users daily | Cohort split is a vectorized groupby |
| New ValidationEngine rules (VR-J001–VR-J005) | +O(U * A) for causal chain check | Vectorized groupby on (user_id, current_ad) |
| Historical file extended schema | +O(H) for parsing 4 additional columns | Negligible; pandas reads additional columns at same IO cost |
| CoolingOverrideService | O(U) for boolean mask operation | Sub-millisecond at 100k users |

No change to the primary performance bottleneck (EngagementGenerator daily loop, ~80% of wall time). Stage 16 SLAs are unaffected.

---

## SECTION 12 — RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Historical reconstruction produces incorrect journey position | Medium | High | Extensive unit tests against known historical fixtures; advisory validation rule VR-H001 |
| Trigger-specific ad sequences cause JourneyEngine state corruption | Low | High | JourneyEngine is immutable per instance; per-trigger instances prevent state sharing |
| CTR redesign breaks deterministic reproducibility (SIM-019) | Medium | High | All probability draws must continue to use MD5+ordinal seeds; no PRNG state shared between users |
| Cooling override misapplied to users not yet in cooling | Low | Medium | `CoolingOverrideService` gates on `eligibility_status=COOLING` AND `journey_status=Completed` |
| dtype=str breaks existing tests with int User_IDs | High | Low | Systematic fixture update in Wave 1; automated detection script |
| New Hard validation rules fail valid simulations | Low | Medium | New rules included in Wave 5 only after core logic validated |
| Historical schema extension creates confusion with optional columns | Low | Low | Clear documentation in `CanonicalSchema`; explicit `hasattr` checks in loader |

---

## SECTION 13 — ACCEPTANCE CRITERIA

### Per-Defect Acceptance Criteria

**CRIT-001:** Given a historical file containing User_ID=U1 with last engagement on Ad_B (journey step 2), after simulation, U1's `current_ad=Ad_C` (step 3) and `days_in_ad` correctly reflects elapsed days since Ad_B engagement.

**CRIT-002:** Given a campaign with Trigger_A owning ads [Ad_A1, Ad_A2] and Trigger_B owning ads [Ad_B1], users from Trigger_A journey through Ad_A1→Ad_A2 and users from Trigger_B journey through Ad_B1 only.

**CRIT-003:** Given a user active in historical data but absent from the current trigger file, that user appears in the simulation output and continues their journey.

**CRIT-004:** `HistoricalStateReconstructor.reconstruct()` returns a valid `USER_STATE_REQUIRED_COLUMNS` DataFrame when given a valid extended historical file.

**CRIT-005:** Given a user whose last historical engagement was on the terminal ad 20 days ago with `cooling_period_days=14`, their reconstructed state is `eligibility_status=RE_ENTRY` (cooling expired).

**CRIT-006:** When `cooling_override=True`, all users with `eligibility_status=COOLING` enter the simulation as `RE_ENTRY`.

**CRIT-007:** Observed CTR is within ±20% of target CTR for each ad. Observed TER is within ±20% of target TER for each trigger. Both assertions hold for target rates between 2% and 50%.

**CRIT-008:** ValidationEngine rule VR-J001 fires for any user on Ad_N (N>1) with no Click event on Ad_(N-1).

**HIGH-001:** All modules import column names from `CanonicalSchema` exclusively. No string literal column definitions remain outside `CanonicalSchema`.

**HIGH-002:** `upload_page.py` and `schema_validator.py` enforce identical required columns for both file types.

**HIGH-003:** A trigger file with numeric User_ID column processes without error; all downstream User_IDs are string type.

**HIGH-004:** No event record in `events_df` has `journey_status=Not_Started`.

**HIGH-005:** A historical file with `Ad_Name`, `Journey_Step`, `Trigger_Name`, `Completion_Date` columns loads without error and enables journey reconstruction.

---

## SECTION 14 — DEFINITION OF DONE

The remediation is complete when ALL of the following are true:

1. All 13 defects have passing acceptance-criteria tests (automated, committed to `tests/test_e2e/test_remediation_certification.py`).
2. Full regression suite (1,111 + new tests) passes with 0 failures.
3. `CanonicalSchema` is the sole source of column name definitions; no other module defines column names as literals (enforced by `grep` in CI).
4. Performance regression: no Stage 16 SLA exceeded by the new code path (verified by re-running `test_scale_certification.py`).
5. `IMPLEMENTATION_WAVES.md` Wave 5 exit criteria all checked.
6. `TESTING_STRATEGY.md` test coverage requirements met for all 13 defects.
7. All documents in this package reviewed and signed off as: ARP-001, DATA_MODEL_REMEDIATION.md, USER_STATE_REMEDIATION.md, HISTORICAL_PROCESSING_REMEDIATION.md, TRIGGER_JOURNEY_REMEDIATION.md, IMPLEMENTATION_WAVES.md, TESTING_STRATEGY.md.

---

## SECTION 15 — REGRESSION TEST REQUIREMENTS

### Existing Tests — Required Updates

| Test File | Change Required |
|-----------|----------------|
| `tests/test_models/test_trigger_config.py` | Add tests for `ads` field (None default, tuple override) |
| `tests/test_models/test_config_registry.py` | Add tests for trigger-scoped ad resolution |
| `tests/test_models/test_user_state.py` | Add tests for `journey_step`, `trigger_ads_key`, `cooling_override_applied` fields |
| `tests/test_core/test_journey_engine.py` | Add tests for trigger-specific ad sequence construction |
| `tests/test_core/test_engagement_generator.py` | Add per-trigger cohort tests; CTR accuracy tests |
| `tests/test_core/test_user_state_manager.py` | Add `reconstructed_state_df` merge tests |
| `tests/test_core/test_validation_engine.py` | Add VR-J001 through VR-J005 rule tests |
| `tests/test_e2e/test_multirun_persistence_certification.py` | Verify new state fields round-trip across runs |
| `tests/test_ui/test_smoke.py` | Add dtype=str upload tests; add cooling_override toggle test |

### New Test Files Required

| Test File | Purpose |
|-----------|---------|
| `tests/test_core/test_historical_state_reconstructor.py` | Full unit coverage of HistoricalStateReconstructor |
| `tests/test_core/test_cooling_override_service.py` | CoolingOverrideService unit tests |
| `tests/test_utils/test_canonical_schema.py` | CanonicalSchema consistency tests |
| `tests/test_e2e/test_remediation_certification.py` | Acceptance-criteria tests for all 13 defects |

### Non-Regression Guard

`tests/test_e2e/test_scale_certification.py` must pass without SLA degradation after all waves are complete. The 50 existing scale tests serve as the performance regression guard.

---

## APPENDIX A — DEFECT REGISTER

| ID | Title | Wave | Priority |
|----|-------|------|----------|
| CRIT-001 | Historical Journey Continuation | Wave 3 | P0 |
| CRIT-002 | Trigger-Specific Journeys | Wave 2 | P0 |
| CRIT-003 | Historical Audience Continuity | Wave 3 | P0 |
| CRIT-004 | Historical State Reconstruction | Wave 3 | P0 |
| CRIT-005 | Cooling Period from History | Wave 3 | P0 |
| CRIT-006 | Cooling Period Override | Wave 4 | P0 |
| CRIT-007 | CTR/TER Accuracy | Wave 4 | P0 |
| CRIT-008 | Journey Progression Validation | Wave 4 | P0 |
| HIGH-001 | Canonical Schema | Wave 1 | P1 |
| HIGH-002 | Upload Validation Alignment | Wave 1 | P1 |
| HIGH-003 | User_ID Type Safety | Wave 1 | P1 |
| HIGH-004 | Journey Status in Events | Wave 2 | P1 |
| HIGH-005 | Historical Schema Extension | Wave 1 | P1 |

---

## APPENDIX B — CROSS-REFERENCE TO COMPANION DOCUMENTS

| Document | Scope |
|----------|-------|
| `DATA_MODEL_REMEDIATION.md` | TriggerConfig.ads, UserState new fields, CanonicalSchema, historical schema |
| `USER_STATE_REMEDIATION.md` | UserState field changes, initialization contracts, finalize_state changes |
| `HISTORICAL_PROCESSING_REMEDIATION.md` | HistoricalStateReconstructor spec, pipeline injection, audience continuity |
| `TRIGGER_JOURNEY_REMEDIATION.md` | TriggerJourneyResolver, JourneyEngine per-trigger, CTR redesign, gating validation |
| `IMPLEMENTATION_WAVES.md` | Wave-by-wave execution plan with exit criteria |
| `TESTING_STRATEGY.md` | Test design for all 13 defects |

---

*Document: ARP-001 | ARCHITECTURE_REMEDIATION_PACKAGE.md | v1.0 | 2026-06-23*
