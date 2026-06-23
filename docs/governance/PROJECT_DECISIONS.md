# PROJECT DECISIONS
# Engagement Data Generator — Version 1.0
# Authoritative Register of All Approved Architecture and Design Decisions

**Document Version:** 1.1
**Created:** 2026-06-21 (retroactively synthesized from prior governance documentation)
**Last Updated:** 2026-06-21 (governance sync — ARCH-013, ARCH-014, CFG-NEW-001 added)
**Role:** Chief Architect / Program Manager / Governance Lead
**Authority:** This document is the highest-authority technical reference in the project. Where any other document conflicts with an entry here, this document takes precedence.

**Creation Note:** This document was created retroactively on 2026-06-21 as part of a mandatory governance synchronization pass. All decisions recorded herein were previously enacted in practice and referenced in TRACEABILITY_MATRIX.md, PROJECT_MASTER_REGISTER.md, PHASE_3_ARCHITECTURE_DECISIONS.md, and the design document hierarchy (Requirements_v1.md → Architecture_v2.md → Technical_Design.md → Technical_Design_Addendum.md → Trigger_Engagement_Clarification.md). They are now formalized in this register.

**Document Authority Hierarchy:**
```
PROJECT_DECISIONS.md          ← THIS DOCUMENT (highest authority)
    ↑ superseded by
Trigger_Engagement_Clarification.md
    ↑ superseded by
Technical_Design_Addendum.md
    ↑ superseded by
Technical_Design.md
    ↑ superseded by
Architecture_v2.md
    ↑ superseded by
Requirements_v1.md            ← (baseline — lowest authority)
```

**Amendment Process:**
Any addition or modification to this document requires approval from the Chief Architect and must be reflected in PROJECT_MASTER_REGISTER.md (Section 5 if it resolves a Deferred Decision) and TRACEABILITY_MATRIX.md (Section 4 or 5 as applicable).

---

## Table of Contents

1. Architecture Decisions (ARCH-*)
2. Configuration Decisions (CFG-*)
3. Simulation Decisions (SIM-*)
4. Business Logic Decisions (BIZ-*, C-*, I-*, R-CA-*)
5. Validation Decisions (VAL-*)
6. Deferred Decisions Index (DD-* — Open and Resolved)

---

## 1. Architecture Decisions (ARCH-*)

---

### ARCH-001
| Field | Value |
|-------|-------|
| ID | ARCH-001 |
| Category | Architecture — Campaign Scope |
| Decision | Single campaign per run in V1 |
| Statement | The engine operates on exactly one campaign per invocation in V1. All DataFrames carry a single campaign_id throughout the pipeline. Multi-campaign support is deferred to V2 (DD-002). |
| Rationale | Simplifies state management, output workbook design, and validation logic. The composite primary key (ARCH-002) still reserves space for multi-campaign in V2 without breaking the V1 schema. |
| Applies to | All core/ modules; all DataFrames; all 7 output workbooks |
| Source | Architecture_v2.md §CampaignScope |
| Resolves | — |
| Status | APPROVED — 2026-01-10 |

---

### ARCH-002
| Field | Value |
|-------|-------|
| ID | ARCH-002 |
| Category | Architecture — Data Model |
| Decision | Composite primary key (Campaign_ID, User_ID) on all DataFrames |
| Statement | All DataFrames that represent per-user state, engagement events, or audience resolution use the composite key (Campaign_ID, User_ID) as the logical primary key. All merge and deduplication operations use this pair as the key subset. |
| Rationale | Enables V2 multi-campaign support without breaking V1 schema. Prevents user ID collisions if campaigns are ever mixed in a single DataFrame. Ensures all output workbooks can be unambiguously joined. |
| Applies to | models/user_state.py; all DataFrames; all 7 output workbooks |
| Source | Technical_Design.md §DataFrameSchema |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### ARCH-003
| Field | Value |
|-------|-------|
| ID | ARCH-003 |
| Category | Architecture — Pipeline |
| Decision | 11-stage pipeline with strict execution order |
| Statement | The engine executes exactly 11 stages in this fixed sequence: (1) Input Load, (2) Config Load, (3) User State Init, (4) Audience Resolution, (5) Journey Building, (6) Engagement Scoring, (7) Behavior Processing, (8) Timing Assignment, (9) Fatigue Enforcement, (10) Validation, (11) Excel Export. No stage may be skipped or reordered. core/run_controller.py is the sole orchestrator. |
| Rationale | Deterministic pipeline order is required for reproducibility (SIM-019). Each stage has well-defined inputs and outputs. The strict order eliminates circular dependencies between engines. |
| Applies to | core/run_controller.py (orchestrates all 11 stages) |
| Source | Technical_Design.md §Pipeline |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### ARCH-004
| Field | Value |
|-------|-------|
| ID | ARCH-004 |
| Category | Architecture — Channel Abstraction |
| Decision | BaseChannel abstract class for Display, Email, WhatsApp |
| Statement | All channel implementations (Display, Email, WhatsApp) extend a shared BaseChannel abstract class. BaseChannel defines the common interface: generate_events(), validate_events(), get_channel_type(). No channel module may bypass BaseChannel. |
| Rationale | Channel-agnostic validation (HR-003 through HR-008) can operate on the common interface. Future channels (V3 plugin architecture, DD-003) can be added without modifying existing code. |
| Applies to | channels/base.py, channels/display.py, channels/email.py, channels/whatsapp.py |
| Source | Technical_Design.md §Channels |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### ARCH-005
| Field | Value |
|-------|-------|
| ID | ARCH-005 |
| Category | Architecture — Import Hierarchy |
| Decision | Strict import tier hierarchy: models/ → utils/ → channels/ + rules/ → core/ → app/ |
| Statement | Import direction is strictly bottom-up. models/ may not import from any other tier. utils/ may import from models/ only. channels/ and rules/ may import from models/ and utils/ only. core/ may import from models/, utils/, channels/, and rules/ — but never from app/. app/ may import from all tiers. No reverse imports. No circular imports. |
| Rationale | Prevents circular dependencies. Enforces separation of concerns: UI code (app/) cannot introduce logic into the engine (core/). Enables independent testing of all tiers below core/. |
| Applies to | All modules — enforced by CI linting (BL-006, pending) |
| Source | Technical_Design.md §ImportRules |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### ARCH-006
| Field | Value |
|-------|-------|
| ID | ARCH-006 |
| Category | Architecture — Validation Framework |
| Decision | Self-registering rule classes in rules/hard/ and rules/soft/ |
| Statement | Each validation rule is a standalone class in its own file under rules/hard/ (15 files, HR-001 through HR-015) or rules/soft/ (20 files, SR-001 through SR-020). Rules self-register with core/validation_engine.py via a class registry mechanism. The validation engine discovers and executes all registered rules without explicit enumeration. |
| Rationale | New rules can be added by creating a single file — no changes to validation_engine.py. Enables independent testing of each rule. Supports machine-readable rule catalog (DD-010). |
| Applies to | rules/hard/ (15 rule files), rules/soft/ (20 rule files), core/validation_engine.py |
| Source | Technical_Design.md §RuleFramework |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### ARCH-007
| Field | Value |
|-------|-------|
| ID | ARCH-007 |
| Category | Architecture — Testing |
| Decision | pytest as test framework; conftest.py for shared fixtures |
| Statement | All tests use pytest. A single conftest.py at the tests/ root provides shared fixtures (sample DataFrames, ConfigRegistry instances, mock trigger files). Test coverage is measured with pytest-cov and enforced at ≥90% for all non-app/ modules. |
| Rationale | pytest is the Python testing standard. Shared conftest.py fixtures prevent duplication and ensure test consistency across all phases. |
| Applies to | tests/ (all test files) |
| Source | Technical_Design.md §TestStrategy |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### ARCH-008
| Field | Value |
|-------|-------|
| ID | ARCH-008 |
| Category | Architecture — Build System |
| Decision | pyproject.toml as build and metadata file |
| Statement | Project metadata, dependencies, and tool configuration (pytest, coverage, linting) are managed in pyproject.toml following PEP 518 and PEP 621. No setup.py or setup.cfg. Python version requirement: ≥3.11 (to be confirmed — see COMP-005). |
| Rationale | Modern Python packaging standard. Single file for all build configuration. Enables pip install -e . for local development. |
| Applies to | pyproject.toml |
| Source | Technical_Design.md §BuildSystem |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### ARCH-009
| Field | Value |
|-------|-------|
| ID | ARCH-009 |
| Category | Architecture — Export |
| Decision | openpyxl direct write; no pd.to_excel() permitted anywhere in production code |
| Statement | All Excel file creation uses openpyxl.Workbook() directly. pd.to_excel() is banned from all production code (including utils/ and app/). Violation is caught by CI grep check (BL-007, pending). All 7 output workbooks are written via openpyxl worksheet operations. |
| Rationale | pd.to_excel() has unpredictable memory usage and limited formatting control. openpyxl direct write enables cell-level control, streaming write patterns (for DD-008), and is more performant for large datasets. |
| Applies to | core/export_engine.py, utils/excel_utils.py |
| Source | Technical_Design.md §ExportEngine |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### ARCH-010
| Field | Value |
|-------|-------|
| ID | ARCH-010 |
| Category | Architecture — Pipeline Control |
| Decision | core/run_controller.py as sole pipeline orchestrator |
| Statement | All 11 pipeline stages are invoked exclusively through core/run_controller.run(). No other module may invoke pipeline stages directly. The UI (app/) calls run_controller.run() only. Stage results are passed as return values between stages; no global state is mutated outside run_controller. |
| Rationale | Single orchestrator enables testable pipeline (mock any stage), consistent error handling, and accurate progress reporting to the UI. |
| Applies to | core/run_controller.py; app/pages/ (UI screens call run() only) |
| Source | Technical_Design.md §Pipeline |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### ARCH-011
| Field | Value |
|-------|-------|
| ID | ARCH-011 |
| Category | Architecture — Performance |
| Decision | DataFrame-first processing; no iterrows() permitted in any production code |
| Statement | All operations over DataFrames use vectorized pandas/numpy operations (apply(), map(), merge(), groupby(), etc.). iterrows() is banned from all production code. Violation is an active defect (PV-001 in Phase 2) and is caught by CI grep check (BL-035, pending). The sole exception: apply(axis=1) for multi-column per-row lookups where vectorized alternatives do not exist — these must have an inline comment explaining why vectorization is not possible. |
| Rationale | iterrows() performance is O(n) Python-loop overhead. At 50K users, iterrows() is 10–100× slower than vectorized alternatives. The performance SLAs (REQ-028: 50K users ≤ 15 min) require vectorized processing throughout. |
| Applies to | All core/ modules; all utils/ modules |
| Source | Technical_Design.md §Performance; docs/performance_guidelines.md |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### ARCH-012
| Field | Value |
|-------|-------|
| ID | ARCH-012 |
| Category | Architecture — Data Model |
| Decision | Dynamic creative affinity columns — Option A (append to UserState DataFrame) |
| Statement | Creative affinities are stored as dynamic columns Creative_Affinity_{ad_name} appended to the UserState DataFrame, one column per ad in the campaign's journey. The UserState dataclass stores creative_affinities as a dict[str, float]. utils/excel_utils.reconcile_creative_affinity_columns() reconciles column sets when loading prior-run state with a different ad lineup. Option B (separate CreativeAffinity table) was rejected as overly complex for V1. |
| Rationale | Dynamic columns allow direct pandas operations on per-ad affinities without joining a separate table. Reconciliation handles V1's single-campaign constraint cleanly. |
| Applies to | models/user_state.py, utils/excel_utils.py (reconcile_creative_affinity_columns), core/behavior_engine.py |
| Source | Technical_Design_Addendum.md §CreativeAffinity; Creative_Affinity_Design_Review §OptionA |
| Resolves | — |
| Status | APPROVED — 2026-03-15 |

---

### ARCH-013
| Field | Value |
|-------|-------|
| ID | ARCH-013 |
| Category | Architecture — Audience Resolution |
| Decision | Trigger priority tiebreak rule: Alphabetical Trigger_Name |
| Statement | When two or more TriggerConfigs have identical priority values and a user appears in trigger file rows for both, the winning trigger is determined by alphabetical sort of Trigger_Name ascending. The trigger whose name sorts first alphabetically is the winner. This rule is applied after primary priority filtering (minimum priority value wins). A WARNING log entry is emitted for every user affected by this tiebreak, listing: number of affected users, tied trigger names, and winner. Implementation: df.sort_values(['priority', 'Trigger_Name', 'Segment']).drop_duplicates(subset=['Campaign_ID', 'User_ID'], keep='first'). |
| Rationale | Alphabetical ordering is a total order over strings, producing full determinism from governed inputs (ConfigRegistry + trigger file column values) without requiring preservation of trigger file row order. This is consistent with the project's reproducibility-first architecture (SIM-019) and ARCH-002 composite primary key design. Option B (first-in-file) was rejected for non-determinism across file regenerations. Option C (ValidationError) was rejected for UX disruption on valid configurations where tied priority is intentional. |
| Applies to | core/audience_manager.py resolve_triggers() |
| Source | PHASE_3_ARCHITECTURE_DECISIONS.md §DD-013 Section 3.5 |
| Resolves | DD-013, OQ-005 |
| Status | APPROVED — 2026-06-21 |

---

### ARCH-014
| Field | Value |
|-------|-------|
| ID | ARCH-014 |
| Category | Architecture — Audience Resolution |
| Decision | Segment tiebreak rule: Segment follows the winning trigger's row |
| Statement | The segment assigned to each user is the Segment value from the winning trigger's row, as determined by ARCH-013. Segment assignment requires no independent resolution step in the normal case — when ARCH-013 produces one winning row per user, that row's Segment column is the user's segment. For the pathological edge case where the same (Campaign_ID, User_ID, Trigger_Name) triple appears with two different Segment values in the trigger file (a data quality defect), alphabetical Segment name ascending is used as a secondary tiebreak. A WARNING log entry is emitted for every user affected by this pathological tiebreak. The unified sort chain for both ARCH-013 and ARCH-014: df.sort_values(['priority', 'Trigger_Name', 'Segment']).drop_duplicates(subset=['Campaign_ID', 'User_ID'], keep='first'). |
| Rationale | Segment follows trigger preserves semantic coherence — the trigger that enrolled a user and the segment that user belongs to refer to the same business context. Option B (alphabetical segment across all rows regardless of trigger) was rejected because it can assign a user to a segment from a different trigger than the one that won, producing internally inconsistent synthetic data. Option C (first-in-file segment) was rejected for file-order non-determinism (same reasons as ARCH-013 Option B). |
| Applies to | core/audience_manager.py resolve_segments() |
| Source | PHASE_3_ARCHITECTURE_DECISIONS.md §DD-014 Section 4.6 |
| Resolves | DD-014, OQ-011 |
| Status | APPROVED — 2026-06-21 |

---

## 2. Configuration Decisions (CFG-*)

---

### CFG-005
| Field | Value |
|-------|-------|
| ID | CFG-005 |
| Category | Configuration — Schema Version |
| Decision | CONFIG_SCHEMA_VERSION = "2.0" — mismatch raises SchemaVersionError |
| Statement | The configuration schema version string is "2.0". utils/version.py defines CONFIG_SCHEMA_VERSION = "2.0". utils/config_io.py validates this field on every config load. If the loaded JSON contains a config_schema_version field that does not match "2.0", SchemaVersionError is raised before any parsing proceeds. |
| Rationale | Prevents silent corruption when a V1 config file is loaded into a V2 engine (or vice versa). The version check is a hard gate: it is better to fail fast with a clear error than to parse a mismatched schema and produce wrong output. |
| Applies to | utils/version.py, utils/config_io.py |
| Source | Technical_Design_Addendum.md §ConfigIO |
| Resolves | — |
| Status | APPROVED — 2026-03-15 |

---

### CFG-NEW-001
| Field | Value |
|-------|-------|
| ID | CFG-NEW-001 |
| Category | Configuration — Reserved Field |
| Decision | Reserve strict_priority_validation field on ConfigRegistry |
| Statement | ConfigRegistry includes a boolean field strict_priority_validation (default: False). In V1, this field is a no-op — it does not change engine behavior. When True in a future release, it causes core/audience_manager.resolve_triggers() to raise ValidationError instead of applying the ARCH-013 alphabetical tiebreak when tied priorities are detected. This reserves Option C (DD-013) as a future strict-audit mode. The field must be accepted by config_loader.py and silently ignored when False. |
| Rationale | Preserves Option C (DD-013 ValidationError) as a future capability without committing to it in V1. Cost is one bool field on a frozen dataclass — negligible. Future users who need strict audit trails can set this flag without requiring an engine version upgrade. |
| Applies to | models/config_registry.py (field definition), core/audience_manager.py (future enforcement) |
| Source | PHASE_3_ARCHITECTURE_DECISIONS.md §Section 6, Risk 4 |
| Resolves | — (reservation for DD-013 Option C) |
| Status | APPROVED — 2026-06-21 |

---

## 3. Simulation Decisions (SIM-*)

---

### SIM-001
| Field | Value |
|-------|-------|
| ID | SIM-001 |
| Category | Simulation — Engagement Scoring |
| Decision | Composite engagement scoring formula with 5 weighted components plus jitter |
| Statement | Each user's daily engagement score is computed as: score = clip(w_eng×engagement_score + w_prof×profile_component + w_cre×creative_affinity + w_cha×channel_affinity + w_rec×reach_recency_normalized + jitter(0.0, 0.05), 0.0, 1.0). The five component weights (w_eng, w_prof, w_cre, w_cha, w_rec) must sum to 1.0 ± 0.001 and are stored in ConfigRegistry as Category B (advanced configurable). Default weights: 0.30 / 0.25 / 0.15 / 0.15 / 0.15. |
| Rationale | Multi-component scoring produces more realistic engagement patterns than single-factor models. Weighted combination allows future tuning of component importance. Jitter prevents identical scores for users with identical profiles. |
| Applies to | core/behavior_engine.py |
| Source | Technical_Design.md §ScoringFormula |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### SIM-002
| Field | Value |
|-------|-------|
| ID | SIM-002 |
| Category | Simulation — Configuration |
| Decision | Scoring weights are Category B (Advanced Configurable) |
| Statement | The five SIM-001 scoring weights are Category B parameters: visible to advanced users in the UI (app/pages/advanced_settings.py) but hidden from basic configuration screens. They appear in ConfigRegistry as named fields (not a dict). Their sum is validated at ConfigRegistry.__post_init__ time. Score weight UI sliders are deferred to V2 (DEF-009). |
| Rationale | Category B parameters enable expert users to tune simulation realism without exposing complexity to non-technical users. The __post_init__ sum validator prevents misconfigured weights from silently corrupting simulation output. |
| Applies to | models/config_registry.py (5 weight fields), app/pages/advanced_settings.py |
| Source | Technical_Design.md §ScoringFormula; Technical_Design_Addendum.md §ConfigStrategy |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### SIM-019
| Field | Value |
|-------|-------|
| ID | SIM-019 |
| Category | Simulation — Reproducibility |
| Decision | Per-user RNG seed via hashlib.md5 — Python built-in hash() is banned |
| Statement | The per-user random seed is computed as: int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 2**32. Python's built-in hash() is prohibited for seed generation because hash() is non-deterministic across Python processes (PYTHONHASHSEED). The hashlib.md5 approach produces a deterministic, reproducible seed for any user_id string across all Python versions, operating systems, and processes. |
| Rationale | Reproducibility is a core requirement (REQ-026). Per-user seeds ensure that two runs with the same input produce identical output for every user independently. Using hash() would silently break reproducibility across separate Python invocations. The MD5 approach is battle-tested, collision-resistant within the 32-bit seed space (4B distinct values), and fast. |
| Applies to | core/input_loader.py (_per_user_seed) |
| Source | Technical_Design.md §Reproducibility |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

## 4. Business Logic Decisions (BIZ-*, C-*, I-*, R-CA-*)

---

### BIZ-003
| Field | Value |
|-------|-------|
| ID | BIZ-003 |
| Category | Business Logic — Metric Separation |
| Decision | TER (Trigger Engagement Rate) and TCC (Trigger Capacity Consumption) are separate concepts with separate code paths |
| Statement | TER is a reporting-only KPI: Distinct Engaged Users / Distinct All-Time Trigger Users × 100. It uses a cumulative (all-time) denominator and is computed by the Validation Engine (Phase 7) for display in the ValidationReport. TCC is an engine driver: max(0, math.ceil(Current_Trigger_File_Users × Target_Engagement_Rate) − Historical_Engaged_Users). It uses a windowed historical denominator and drives remaining capacity calculation in core/audience_manager.py. TER and TCC must never share code paths, formula logic, or configuration fields. |
| Rationale | Conflating TER and TCC caused the TCC-001 defect (int() vs ceil()) and the docstring errors TCC-002/003. Explicit separation makes each metric independently testable and prevents future metric confusion. |
| Applies to | core/audience_manager.py (TCC), core/validation_engine.py (TER) |
| Source | Trigger_Engagement_Clarification.md §TER; §TCC |
| Resolves | — |
| Status | APPROVED — 2026-04-01 |

---

### BIZ-004
| Field | Value |
|-------|-------|
| ID | BIZ-004 |
| Category | Business Logic — Historical Window |
| Decision | Historical engagement window default: Last 90 Days (applies to TCC only, not TER) |
| Statement | The default historical engagement window for TCC capacity calculation is Last 90 Days. ConfigRegistry.historical_engagement_window defaults to HistoricalWindow.LAST_90. This window determines which historical engagement records count as "already engaged" for the purposes of computing remaining capacity. TER always uses a cumulative (all-time) denominator regardless of this setting. |
| Rationale | 90 days is a practical default aligned with standard pharma marketing campaign cycles. The distinction from TER's all-time denominator prevents TCC under-counting (if TER's all-time denominator were used, historical users from years ago would reduce capacity for current campaigns). |
| Applies to | core/input_loader.py (load_historical_file), core/audience_manager.py |
| Source | Technical_Design_Addendum.md §HistoricalEngagement; Trigger_Engagement_Clarification.md §TCC |
| Resolves | — |
| Status | APPROVED — 2026-03-15 |

---

### BIZ-011
| Field | Value |
|-------|-------|
| ID | BIZ-011 |
| Category | Business Logic — Qualifying Actions |
| Decision | QUALIFYING_ACTIONS is a Category C system constant in utils/schema_validator.py |
| Statement | The set of engagement event types that count as "qualifying actions" for TCC and TER calculations is a Category C constant (system-defined, not user-configurable in V1). It is defined in utils/schema_validator.py as QUALIFYING_ACTIONS. In V1, qualifying actions are: Display Click, Email Open, Email Click, WhatsApp Open, WhatsApp Click. Display Impression is not qualifying. Category B configurability of qualifying actions is deferred to V2 (DEF-001 / BL-019). |
| Rationale | Category C prevents users from accidentally disabling qualifying action detection. The constant definition in schema_validator.py ensures it is applied consistently in all validation and TCC/TER calculation paths. |
| Applies to | utils/schema_validator.py (QUALIFYING_ACTIONS constant) |
| Source | Trigger_Engagement_Clarification.md §QUALIFYING_ACTIONS |
| Resolves | — |
| Status | APPROVED — 2026-04-01 |

---

### BIZ-018 / C-001
| Field | Value |
|-------|-------|
| ID | BIZ-018 / C-001 |
| Category | Business Logic — Journey Advance |
| Decision | Move On Click is exclusive — skip duration check if click-advance fires |
| Statement | When an AdConfig has move_on_click=True and the user receives a click on the current ad, the journey advances to the next ad immediately. The duration check (days_in_ad ≥ ad.duration_days) is NOT evaluated on the same day a click-advance fires. A user cannot double-advance (click AND duration) on the same simulation day. |
| Rationale | Without the exclusive check, a user who clicks on day 1 of a 1-day ad would advance twice: once for click and once for duration expiry. Double-advance would corrupt journey sequencing and violate HR-001. |
| Applies to | core/journey_engine.py |
| Source | Technical_Design_Addendum.md §Journey |
| Resolves | — |
| Status | APPROVED — 2026-03-15 |

---

### BIZ-019
| Field | Value |
|-------|-------|
| ID | BIZ-019 |
| Category | Business Logic — Campaign ID |
| Decision | Campaign_ID absent in input file → insert "Default" and log INFO |
| Statement | If a trigger file or historical engagement file row is missing a Campaign_ID column or has a null/empty Campaign_ID, the engine inserts "Default" for that row and logs an INFO-level message: "Campaign_ID absent or null for N rows — substituting 'Default'." This substitution occurs in core/input_loader.py on file load, before any downstream filtering or processing. |
| Rationale | Fail-open behavior: rather than rejecting the entire file when Campaign_ID is absent (common in early-stage pharma CRM exports), the engine substitutes a sentinel value that survives the HR-015 Campaign_ID match check when ConfigRegistry.campaign_id is also "Default". |
| Applies to | core/input_loader.py (load_trigger_file, load_historical_file) |
| Source | Technical_Design_Addendum.md §InputLoader |
| Resolves | — |
| Status | APPROVED — 2026-03-15 |

---

### BIZ-021 / C-005
| Field | Value |
|-------|-------|
| ID | BIZ-021 / C-005 |
| Category | Business Logic — Historical Data |
| Decision | Historical engagement file deduplication on load — before any filtering |
| Statement | When loading a historical engagement file, deduplication is applied immediately after date parsing — before campaign ID filtering, before qualifying action filtering, and before any date window filtering. The deduplication key is (Campaign_ID, User_ID, Engagement_Date, Channel, Action). A comment is required above the dedup call: "# C-005: Dedup applied after date parse (Date is part of key) but before all filters." |
| Rationale | Deduplicating before filtering ensures that if the same event was recorded twice in the source system (common in marketing automation platforms), the dedup fires regardless of which filter would later keep or exclude the row. Deduplicating after filtering could miss duplicates that straddle filter boundaries. |
| Applies to | core/input_loader.py (load_historical_file) |
| Source | Technical_Design.md §InputLoader |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### BIZ-023 / C-003
| Field | Value |
|-------|-------|
| ID | BIZ-023 / C-003 |
| Category | Business Logic — Fatigue Reset |
| Decision | Weekly counter reset at ISO Monday boundary (d.weekday() == 0), BEFORE any processing for that day |
| Statement | All weekly engagement counters (weekly_impressions, weekly_clicks, weekly_opens, weekly_engagements) are reset to 0 at the start of any simulation day where d.weekday() == 0 (Monday per ISO standard). The reset must occur BEFORE any engagement allocation or fatigue enforcement for that day. The correct Python check is d.weekday() == 0, NOT d.isoweekday() == 7 (Sunday). |
| Rationale | ISO Monday-start weeks are the standard in EU pharma markets. The ordering requirement (reset before processing) ensures that Monday is treated as a fresh week from the first allocation call. If reset occurred after processing, Monday would incorrectly consume from the previous week's counter. |
| Applies to | core/fatigue_engine.py; utils/date_utils.py (iso_week_start) |
| Source | Technical_Design_Addendum.md §FatigueEngine |
| Resolves | — |
| Status | APPROVED — 2026-03-15 |

---

### C-002
| Field | Value |
|-------|-------|
| ID | C-002 |
| Category | Business Logic — Audience Resolution |
| Decision | Campaign ID filter applied before audience resolution |
| Statement | In core/audience_manager.py, the trigger DataFrame is filtered to rows matching config.campaign_id BEFORE any priority resolution or tiebreak logic. Rows with a Campaign_ID that does not match the active campaign are excluded from the audience resolution entirely. |
| Rationale | Prevents users from one campaign being evaluated for audience resolution under a different campaign's triggers. Required for correct HR-015 validation (all events must match the active campaign_id). |
| Applies to | core/audience_manager.py |
| Source | Technical_Design_Addendum.md §AudienceResolution |
| Resolves | — |
| Status | APPROVED — 2026-03-15 |

---

### C-004
| Field | Value |
|-------|-------|
| ID | C-004 |
| Category | Business Logic — Journey Re-Entry |
| Decision | Re-entry begins from Ad1 (first journey ad) after cooling period expires |
| Statement | When a user completes a journey and their cooling period expires, re-entry (if triggered by a new trigger file appearance) restarts the journey from the first ad (ad_order = 1). The user's prior journey completion is preserved in UserState (journey_completion_date is retained). Journey_Status transitions from Cooling → Re-Entry → Active (at Ad1). |
| Rationale | Re-starting from Ad1 ensures consistent journey exposure for re-engaged users. Preserving the prior completion date supports TER/TCC historical calculations. |
| Applies to | core/audience_manager.py (classify_eligibility), core/journey_engine.py |
| Source | Technical_Design_Addendum.md §Re-Entry |
| Resolves | — |
| Status | APPROVED — 2026-03-15 |

---

### I-001
| Field | Value |
|-------|-------|
| ID | I-001 |
| Category | Business Logic — Vendor Assignment |
| Decision | Per-ad vendor overrides campaign-level default_vendor |
| Statement | Each AdConfig has an optional vendor field. If AdConfig.vendor is not None, it takes precedence over ConfigRegistry.default_vendor for that ad. ConfigRegistry.get_effective_vendor(ad) implements this logic. |
| Rationale | Different ads in the same campaign may be served by different vendors (e.g., endemic display by one vendor, programmatic by another). The per-ad override avoids requiring a separate ConfigRegistry per vendor. |
| Applies to | models/config_registry.py (get_effective_vendor) |
| Source | Technical_Design.md §VendorAssignment |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### R-CA-004
| Field | Value |
|-------|-------|
| ID | R-CA-004 |
| Category | Business Logic — State Reconciliation |
| Decision | Creative affinity schema reconciliation on prior state load |
| Statement | When loading a prior-run UserState Excel file, utils/excel_utils.reconcile_creative_affinity_columns() is called to reconcile the Creative_Affinity_{ad_name} columns between the prior state and the current campaign's ad lineup. Reconciliation rules: (1) Columns in prior state but not in current config → retained with a WARNING log; (2) Columns in current config but not in prior state → inserted with value 0.5 (neutral default); (3) Columns in both → retained as-is. All Creative_Affinity_* columns must be dtype float32 after reconciliation. |
| Rationale | Campaign ad lineups can change between runs. Hard-failing on column mismatch would prevent legitimate incremental runs where ads were added or removed. The retain-with-warning approach preserves historical data while ensuring new ads get a neutral starting affinity. |
| Applies to | utils/excel_utils.py (reconcile_creative_affinity_columns) |
| Source | Technical_Design_Addendum.md §CreativeAffinity |
| Resolves | — |
| Status | APPROVED — 2026-03-15 |

---

## 5. Validation Decisions (VAL-*)

---

### VAL-001
| Field | Value |
|-------|-------|
| ID | VAL-001 |
| Category | Validation — Hard Rule Enforcement |
| Decision | Any hard rule FAIL blocks all export except ValidationReport |
| Statement | When core/validation_engine.py produces a ValidationResult with is_blocking() = True (i.e., at least one HR-* rule returned FAIL), the export engine halts all workbook generation EXCEPT the ValidationReport workbook. The ValidationReport is always written, even when other exports are blocked. The blocking result must list all failing hard rules (not just the first). |
| Rationale | Blocking export on hard rule failure prevents engineers or users from receiving and acting on invalid data. The ValidationReport is always exported to provide actionable information about what failed and why. Reporting all failures (not just the first) enables single-pass correction. |
| Applies to | core/validation_engine.py, core/export_engine.py |
| Source | Technical_Design.md §ValidationFramework |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

### VAL-002
| Field | Value |
|-------|-------|
| ID | VAL-002 |
| Category | Validation — Soft Rule Non-Blocking |
| Decision | Soft rules (SR-*) produce WARNING entries; they never block export |
| Statement | All SR-* soft rules produce WARNING-level entries in the ValidationReport. No soft rule, regardless of severity, may block or delay export of any workbook. The ValidationReport records all soft rule results alongside hard rule results. Users must be able to review soft rule warnings and decide whether to proceed with the generated data. |
| Rationale | Soft rules represent statistical advisories and quality indicators, not correctness constraints. Blocking export on a soft rule WARN would be overly restrictive for a data generation tool where "imperfect but usable" data is the norm for exploratory runs. |
| Applies to | core/validation_engine.py |
| Source | Technical_Design.md §ValidationFramework |
| Resolves | — |
| Status | APPROVED — 2026-02-15 |

---

## 6. Deferred Decisions Index (DD-*)

This section records the status of all Deferred Decisions from PROJECT_MASTER_REGISTER.md Section 5. Decisions resolved by entries in this document are cross-referenced here.

| DD-ID | Decision Summary | Status | Resolution |
|-------|-----------------|--------|------------|
| DD-001 | Qualifying actions Category B configurable in V2 | DEFERRED — V2 | See BL-019 |
| DD-002 | Multi-campaign per run in V2 | DEFERRED — V2 | See BL-018 |
| DD-003 | Channel plugin architecture for V3 | DEFERRED — V3 | See BL-029 |
| DD-004 | TER rolling window vs. cumulative in V2 | DEFERRED — V2 | See BL-056 / FE-018 |
| DD-005 | Background threads vs. multiprocessing for V3 | DEFERRED — V3 | See BL-030 |
| DD-006 | UserState storage migration to SQLite in V2 | DEFERRED — V2 | — |
| DD-007 | API authentication for V3 headless mode | DEFERRED — V3 | — |
| DD-008 | In-memory batch vs. streaming openpyxl write | OPEN — Phase 8 decision | Leaning Option A (in-memory batch) |
| DD-009 | Historical affinity thresholds data-driven in V2 | DEFERRED — V2 | See BL-020 |
| DD-010 | Validation_Rules_Catalog.md machine-readable format | OPEN — pre-Phase-7 | — |
| DD-011 | CONFIG_SCHEMA_VERSION migration V1 → V2 | DEFERRED — pre-V2 | — |
| DD-012 | Terminal journey event on completion | OPEN — pre-Phase-4 | Must resolve before GATE-P3 |
| DD-013 | Trigger priority tiebreak rule | **RESOLVED — 2026-06-21** | **ARCH-013: Alphabetical Trigger_Name** |
| DD-014 | Segment tiebreak when same priority + different segments | **RESOLVED — 2026-06-21** | **ARCH-014: Segment follows winning trigger row** |
| DD-015 | Trigger_History delimiter (pipe vs semicolon) | **RESOLVED — 2026-06-22** | **ARCH-017: Pipe character (\|)** |
| DD-016 | DROPPED eligibility classification | **RESOLVED — 2026-06-22** | **ARCH-018: → EXCLUDED** |

---

### ARCH-015
| Field | Value |
|-------|-------|
| ID | ARCH-015 |
| Category | Architecture — Data Model |
| Decision | EligibilityStatus canonical values: NEW, ACTIVE, COOLING, RE_ENTRY, SKIPPED, EXCLUDED |
| Statement | EligibilityStatus has six canonical values for Phase 3+: NEW (never entered this campaign), ACTIVE (currently in an active journey), COOLING (journey complete, cooling period still running), RE_ENTRY (cooling expired and allow_reentry=True; string value "Re_Entry" with underscore), SKIPPED (in-scope but excluded due to capacity constraints), EXCLUDED (permanently ineligible — hard exclusion, DROPPED journey, or allow_reentry=False). Three deprecated values retained for backward import compatibility only — must not be used in Phase 3+ code: ELIGIBLE (deprecated alias for ACTIVE), INELIGIBLE (deprecated alias for SKIPPED), COMPLETED (deprecated alias for COOLING or RE_ENTRY). RE_ENTRY string value is "Re_Entry" (underscore) — never "Re-Entry" (hyphen). |
| Rationale | Existing values ELIGIBLE/INELIGIBLE/COMPLETED had no defined semantics in any planning document. C-004 explicitly names Re-Entry as a journey state. NCR-003 described the intended enum incorrectly; this decision establishes the canonical set. REM-010 had already changed the default from ELIGIBLE to NEW, confirming ELIGIBLE was a placeholder. Zero regression risk: no test asserts classify_eligibility logic against ELIGIBLE/INELIGIBLE/COMPLETED. |
| Applies to | models/enums.py (EligibilityStatus); core/audience_manager.py (classify_eligibility) |
| Source | PHASE_3_BLOCKER_RESOLUTION.md RESOLUTION 02 |
| Resolves | AUDIT-002; NCR-003 correction |
| Status | APPROVED — 2026-06-22 |

---

### ARCH-016
| Field | Value |
|-------|-------|
| ID | ARCH-016 |
| Category | Architecture — Data Model |
| Decision | UserState weekly counters track per-action events, not per-channel events |
| Statement | The four weekly counter fields in UserState are: weekly_impressions (impression events), weekly_clicks (click events), weekly_opens (open events), weekly_engagements (qualifying engagement events). These are per-action counters, NOT per-channel counters. ConfigRegistry cap fields align: weekly_impression_cap, weekly_click_cap, weekly_open_cap, weekly_engagement_cap. No per-channel weekly caps exist in V1. reset_weekly_counters() resets all four counters on ISO Monday (BIZ-023/C-003). Per-channel weekly frequency caps are deferred to V2. |
| Rationale | Per-action counters are implemented in Phase 2 UserState and ConfigRegistry. Changing to per-channel would require a schema migration. BIZ-023/C-003 names weekly_impressions/clicks/opens/engagements explicitly — the approved decision governs over plan spec. |
| Applies to | models/user_state.py (4 weekly counter fields); models/config_registry.py (4 cap fields); core/fatigue_engine.py |
| Source | PHASE_3_BLOCKER_RESOLUTION.md RESOLUTION 04 |
| Resolves | AUDIT-004 |
| Status | APPROVED — 2026-06-22 |

---

### ARCH-017
| Field | Value |
|-------|-------|
| ID | ARCH-017 |
| Category | Architecture — Data Serialization |
| Decision | Trigger_History field uses pipe character (|) as delimiter |
| Statement | UserState.trigger_history is a pipe-delimited string of trigger names in chronological order (oldest first, newest last). TRIGGER_HISTORY_DELIMITER = "|" in utils/constants.py is the sole reference — no inline "|" literals permitted. Format example: "Trigger_A|Trigger_B|Trigger_A". Deduplication NOT applied. Append pattern: if trigger_history is None, set to trigger_name; otherwise append TRIGGER_HISTORY_DELIMITER + trigger_name. |
| Rationale | Pipe is safe in pharma CRM trigger names (alphanumeric + hyphen + underscore). Pipe avoids CSV/semicolon ambiguity. PHASE_3_ARCHITECTURE_DECISIONS.md §6 specifies pipe; PROJECT_HANDOFF.md §22 specifies semicolon — this decision resolves R-NEW-001 in favor of pipe. |
| Applies to | utils/constants.py (TRIGGER_HISTORY_DELIMITER); models/user_state.py (trigger_history field); core/user_state_manager.py (writes); core/export_engine.py (reads) |
| Source | PHASE_3_BLOCKER_RESOLUTION.md Decision A |
| Resolves | AUDIT-013; R-NEW-001 |
| Status | APPROVED — 2026-06-22 |

---

### ARCH-018
| Field | Value |
|-------|-------|
| ID | ARCH-018 |
| Category | Architecture — State Machine |
| Decision | JourneyStatus.DROPPED maps to EligibilityStatus.EXCLUDED in classify_eligibility() |
| Statement | DROPPED is a terminal journey state indicating abnormal journey termination. In classify_eligibility(), the condition (journey_status == JourneyStatus.DROPPED.value) must appear as the first (highest-priority) condition in the np.select call, mapping to EligibilityStatus.EXCLUDED.value. DROPPED users bypass all other condition checks. |
| Rationale | DROPPED users require explicit business re-qualification before re-entry. Classifying as SKIPPED (capacity-based) is incorrect. Classifying as RE_ENTRY is incorrect — no cooling period was set. EXCLUDED is the correct permanent-ineligibility signal. |
| Applies to | core/audience_manager.py (classify_eligibility) |
| Source | PHASE_3_BLOCKER_RESOLUTION.md Decision B |
| Resolves | AUDIT-011 |
| Status | APPROVED — 2026-06-22 |

---

### ARCH-019
| Field | Value |
|-------|-------|
| ID | ARCH-019 |
| Category | Architecture — Validation |
| Decision | Invalid trigger priority rejected at ConfigRegistry.__post_init__ (defense-in-depth) |
| Statement | ConfigRegistry.__post_init__ validates that every TriggerConfig in self.triggers has priority >= 1, raising ConfigError if any has an invalid priority. This is secondary defense — TriggerConfig.__post_init__ already validates priority >= 1 (raises ValueError); a None priority raises TypeError at TriggerConfig construction time. The ConfigRegistry guard provides defense-in-depth for any future code path that bypasses TriggerConfig validation. |
| Rationale | ARCH-013 tiebreak sort uses priority as a sort key. Null/invalid values in pandas sort_values produce NaN ordering issues. Fail-fast at ConfigRegistry construction ensures audience_manager.py never encounters invalid priority. |
| Applies to | models/config_registry.py (__post_init__) |
| Source | PHASE_3_BLOCKER_RESOLUTION.md Decision C |
| Resolves | MISS-004 |
| Status | APPROVED — 2026-06-22 |

---

### ARCH-020
| Field | Value |
|-------|-------|
| ID | ARCH-020 |
| Category | Architecture — State Machine |
| Decision | allow_reentry=False classifies cooling-expired users as EXCLUDED (not RE_ENTRY) |
| Statement | classify_eligibility() receives config.allow_reentry as a boolean scalar. The RE_ENTRY classification is guarded by (allow_reentry == True). When allow_reentry=False, cooling-expired users are classified EligibilityStatus.EXCLUDED. np.select condition order (highest to lowest priority): (1) DROPPED→EXCLUDED, (2) cooling_period_end in future→COOLING, (3) cooling expired AND allow_reentry=True→RE_ENTRY, (4) cooling expired AND allow_reentry=False→EXCLUDED, (5) journey_status==ACTIVE→ACTIVE, (6) journey_status==NOT_STARTED→NEW, (7) default→SKIPPED. |
| Rationale | allow_reentry=False is an operator administrative decision to disable re-entry. Users who completed a journey and finished cooling are not "skipped due to capacity" — they are administratively excluded. EXCLUDED is semantically precise. |
| Applies to | core/audience_manager.py (classify_eligibility); models/config_registry.py (allow_reentry field) |
| Source | PHASE_3_BLOCKER_RESOLUTION.md Decision D |
| Resolves | AUDIT-014, MISS-003 |
| Status | APPROVED — 2026-06-22 |

---

*PROJECT_DECISIONS.md — Version 1.1*
*Engagement Data Generator v1.0*
*Chief Architect / Program Manager / Governance Lead*
*Created: 2026-06-21 | Last Updated: 2026-06-22 (Phase 3 foundation sprint — ARCH-015 through ARCH-020 added)*

*This document is the authoritative reference for all approved decisions.*
*No decision may be implemented without an entry here.*
*No item in any other document may be marked RESOLVED without a corresponding entry in this document.*
*Amendment requires Chief Architect approval and simultaneous updates to PROJECT_MASTER_REGISTER.md and TRACEABILITY_MATRIX.md.*
