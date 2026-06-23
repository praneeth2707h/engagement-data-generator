# PROJECT CHANGE LOG
# Engagement Data Generator — Version 1.0
# Project Governance Document

**Document Version:** 1.0
**Prepared:** 2026-06-21
**Role:** Chief Architect
**Baseline:** Requirements_v1.md (2025-12-01)
**Current Phase:** Phase 2 Complete — Phase 3 Pending Remediation

**Authority:** PROJECT_DECISIONS.md is the single source of truth for all approved decisions.
This document records the *history* of how decisions were reached and changed over time.
It does not supersede PROJECT_DECISIONS.md. In any conflict, PROJECT_DECISIONS.md governs.

**Document Hierarchy (highest to lowest authority):**
```
PROJECT_DECISIONS.md
  └── Trigger_Engagement_Clarification.md
        └── Technical_Design_Addendum.md
              └── Technical_Design.md
                    └── Architecture_v2.md
                          └── Requirements_v1.md  ← baseline for this log
```

---

## Table of Contents

1. Document Information
2. Change Management Process
3. Change Categories
4. Approved Changes Log
5. Deferred Changes Log
6. Rejected Changes Log
7. Future Enhancements Moved to Backlog
8. Architecture Decision History
9. Business Rule Evolution
10. Trigger Engagement Evolution
11. Journey Engine Evolution
12. Validation Rule Evolution
13. UI Evolution
14. Version History

---

## 1. Document Information

| Field | Value |
|-------|-------|
| Project | Engagement Data Generator |
| Product Version | 1.0 |
| Document ID | PROJECT_CHANGE_LOG |
| Document Version | 1.0 |
| Baseline Document | Requirements_v1.md |
| Baseline Date | 2025-12-01 |
| Last Updated | 2026-06-21 |
| Author | Chief Architect |
| Reviewers | Product Owner, Lead Engineer |
| Status | Active — Updated each phase |

**Purpose of this document:** To provide a complete, auditable record of every decision, change, deferral, and rejection made after Requirements_v1.md was finalized. This ensures that future developers, reviewers, and product owners can understand not only *what* the system does but *why* it was designed that way and what alternatives were considered and discarded.

**How to use this document:**
- Before implementing any feature, verify it appears as Approved in Section 4.
- Before deferring any feature, add it to Section 5 with a recorded rationale.
- Before rejecting an approach, add it to Section 6 with a recorded rationale.
- New backlog candidates discovered during implementation belong in Section 7.

---

## 2. Change Management Process

### Change Request Lifecycle

```
Proposed → Under Review → Approved / Deferred / Rejected
                              ↓
                     PROJECT_DECISIONS.md updated (if Approved)
                     PROJECT_BACKLOG.md updated (if Deferred)
                     Section 6 updated (if Rejected)
```

### Change Severity Classification

| Severity | Definition | Requires |
|----------|-----------|---------|
| Breaking | Changes the output schema, file format, or public API | Full review + migration plan |
| Major | Changes engine behavior, rule logic, or model fields | Architecture review |
| Minor | Changes default values, logging, or error messages | Lead engineer approval |
| Patch | Fixes a defect without changing intended behavior | Code review only |
| Editorial | Updates documentation, comments, or variable names | Self-approved |

### Change Status Definitions

| Status | Meaning |
|--------|---------|
| Approved | Accepted into the design baseline; implemented or scheduled for implementation |
| Pending | Approved in principle; awaiting implementation (Phase 2 remediation items) |
| Deferred | Intentionally excluded from current release with a recorded reason |
| Rejected | Considered and explicitly not adopted; rationale recorded |
| Superseded | Replaced by a later decision; original entry preserved for audit trail |
| Under Review | Proposed but not yet decided |

---

## 3. Change Categories

| Code | Category | Description |
|------|----------|-------------|
| ARCH | Architecture | Module structure, import rules, pipeline design, storage strategy |
| BIZ | Business Rule | Engagement logic, capacity rules, journey behavior, channel rules |
| CFG | Configuration | Parameter categories, schema versions, default values |
| DATA | Data Model | DataFrame schemas, model fields, enum values, output columns |
| DEFECT | Defect Correction | Implementation errors discovered during review or testing |
| PERF | Performance | Vectorization, memory, dtype, concurrency |
| SIM | Simulation Model | Scoring formula, seed generation, profile logic, affinity models |
| UI | User Interface | Screen layout, widget behavior, label changes |
| VAL | Validation | Rule additions, severity changes, blocking behavior |
| FE | Future Enhancement | Feature candidate deferred to backlog |

---

## 4. Approved Changes Log

This section records all changes approved after Requirements_v1.md was finalized.
Entries are ordered by date of approval.

---

### CHG-001
| Field | Value |
|-------|-------|
| Change ID | CHG-001 |
| Date | 2026-01-10 |
| Category | ARCH |
| Decision ID | ARCH-001 |
| Source | Architecture Review — Architecture_v2.md |
| Title | Single Campaign Per Run in V1 |
| Description | Requirements_v1.md was ambiguous on whether one run could process multiple campaigns simultaneously. Architecture_v2 formally scoped V1 to single-campaign-per-run. ConfigRegistry holds exactly one campaign_id. All DataFrames treat campaign_id as a constant within a run. |
| Reason | Dramatic reduction in complexity. Multi-campaign joins, cross-campaign user deduplication, and per-campaign output naming require significant additional design. V2 upgrade path is already designed (ARCH-002 composite PK). |
| Impact | Simplifies all 11 pipeline stages. Multi-campaign deferred to V2 (FE-001). |
| Status | Approved |
| Version | Architecture_v2.md |

---

### CHG-002
| Field | Value |
|-------|-------|
| Change ID | CHG-002 |
| Date | 2026-01-10 |
| Category | ARCH |
| Decision ID | ARCH-002 |
| Source | Architecture Review — Architecture_v2.md |
| Title | Composite Primary Key (Campaign_ID, User_ID) on All DataFrames |
| Description | All DataFrames use (Campaign_ID, User_ID) as the composite primary key. Single-column User_ID is insufficient for V2 multi-campaign support. Adding Campaign_ID now avoids a breaking schema change in V2. |
| Reason | Forward compatibility. V2 multi-campaign upgrade (FE-001) is already designed — it only requires removing the single-campaign constraint, not changing the data schema. |
| Impact | Every DataFrame in every pipeline stage carries Campaign_ID. Output workbooks include Campaign_ID as a required column. No performance impact (pd.Categorical applied). |
| Status | Approved |
| Version | Architecture_v2.md |

---

### CHG-003
| Field | Value |
|-------|-------|
| Change ID | CHG-003 |
| Date | 2026-01-10 |
| Category | ARCH |
| Decision ID | ARCH-003 |
| Source | Architecture Review — Architecture_v2.md |
| Title | 11-Stage Pipeline with Strict Execution Order |
| Description | The simulation engine is organized as exactly 11 sequential stages: Input Load → Config Load → User State Init → Audience Resolution → Journey Building → Engagement Scoring → Behavior Processing → Timing Assignment → Fatigue Enforcement → Validation → Excel Export. No stage reads outputs from later stages. run_controller.py orchestrates the sequence. |
| Reason | Replaces an earlier ad-hoc processing model where stages interleaved. Strict sequencing enables stage-by-stage testing, future RNG snapshots (FE-007), and clean background threading (FE-004). |
| Impact | run_controller.py is the sole orchestrator. Stages are independently testable. Adding new stages (V3) requires only inserting into the ordered list. |
| Status | Approved |
| Version | Architecture_v2.md |

---

### CHG-004
| Field | Value |
|-------|-------|
| Change ID | CHG-004 |
| Date | 2026-01-15 |
| Category | ARCH |
| Decision ID | ARCH-005 |
| Source | Architecture Review — Architecture_v2.md |
| Title | Strict Import Tier Hierarchy — core/ Never Imports from app/ |
| Description | Enforces a one-way dependency graph: models/ → utils/ → channels/ → rules/ → core/ → app/. core/ has zero imports from app/. utils/ has zero imports from core/ or app/. Enforced by import linting in CI. |
| Reason | Prevents circular imports, enables headless testing of all business logic without the Streamlit UI, and allows the UI to be replaced (e.g., with a REST API in V3) without modifying core logic. |
| Impact | Import lint failure blocks merge. Any future developer who writes an app/ import inside core/ must first amend this decision. |
| Status | Approved |
| Version | Architecture_v2.md |

---

### CHG-005
| Field | Value |
|-------|-------|
| Change ID | CHG-005 |
| Date | 2026-01-20 |
| Category | ARCH |
| Decision ID | ARCH-009 |
| Source | Architecture Review — Technical_Design.md |
| Title | openpyxl Direct Write for All 7 Output Workbooks — No pd.to_excel() |
| Description | All output workbooks are written using openpyxl.Workbook() directly. pd.to_excel() is prohibited in any export function. openpyxl provides cell-level control over formatting, column widths, number formats, and the Run_Metadata sheet that every workbook requires. |
| Reason | pd.to_excel() has limited formatting control and wraps openpyxl internally, producing an extra abstraction layer. Direct openpyxl write is ~15% faster for large outputs and allows precise schema enforcement. |
| Impact | All 7 workbook writers must use openpyxl exclusively. pd.to_excel() can still be used in tests for generating fixture DataFrames, but never in production export paths. |
| Status | Approved |
| Version | Technical_Design.md |

---

### CHG-006
| Field | Value |
|-------|-------|
| Change ID | CHG-006 |
| Date | 2026-01-20 |
| Category | PERF |
| Decision ID | ARCH-011 |
| Source | Architecture Review — Technical_Design.md |
| Title | DataFrame-First Architecture — No iterrows() in Production Code |
| Description | All bulk user processing uses indexed pandas DataFrames. Dataclasses are used only for config objects and single-record contracts. No iterrows() anywhere in production code. Permitted exceptions: itertuples() in the Excel export write loop (write-once path) and any unavoidable apply() call explicitly documented with a comment explaining why. |
| Reason | iterrows() is 100–1000× slower than vectorized operations for DataFrames > 1,000 rows. At 50,000 users across a 90-day simulation, iterrows()-based processing would take hours. |
| Impact | Every production code path that touches user records must use np.where, np.select, boolean masks, groupby, or clip. CI import linting checks for iterrows() violations. |
| Status | Approved |
| Version | Technical_Design.md |

---

### CHG-007
| Field | Value |
|-------|-------|
| Change ID | CHG-007 |
| Date | 2026-02-05 |
| Category | DATA |
| Decision ID | ARCH-012 |
| Source | Product Owner Review — Creative_Affinity_Design_Review.md |
| Title | Dynamic Creative Affinity Columns — Option A Selected |
| Description | Creative affinity is stored as dynamic DataFrame columns (Creative_Affinity_{ad_name}) rather than a single JSON blob column (Option B). The number of columns equals the number of Ads in the campaign journey. Missing columns when loading prior state are filled with 0.5 and logged as WARNING. Extra columns not in current config are preserved and logged as WARNING. All columns cast to float32. |
| Reason | Option A enables direct vectorized operations on affinity columns (df["Creative_Affinity_Ad1"].clip()), avoids JSON serialization/deserialization overhead, and makes the UserState.xlsx human-readable. Option B (JSON blob) was rejected — see CHG-REJ-003. |
| Impact | UserState schema is dynamic. Column count varies per campaign journey length. Schema reconciliation (reconcile_creative_affinity_columns()) is required on every prior state load. AdConfig.creative_affinity_column() provides the column name formula. |
| Status | Approved |
| Version | Creative_Affinity_Design_Review.md |

---

### CHG-008
| Field | Value |
|-------|-------|
| Change ID | CHG-008 |
| Date | 2026-02-10 |
| Category | BIZ |
| Decision ID | BIZ-003 |
| Source | Product Owner Review — Trigger_Engagement_Clarification.md |
| Title | Formal Separation of TER and TCC as Distinct Concepts |
| Description | Trigger Engagement Rate (TER) and Trigger Capacity Consumption (TCC) are defined as completely separate concepts with separate code paths, separate variable names (ter_* and tcc_*), and separate denominators. TER is a reporting KPI only. TCC drives the engine. These concepts were conflated in Requirements_v1.md. |
| Reason | Conflation of TER and TCC was the single largest source of design confusion. Developers implementing audience allocation incorrectly used the TER denominator (all-time cumulative users) for capacity calculation, which would cause the engine to under-generate events relative to the configured target. |
| Impact | All code touching engagement rates must explicitly identify whether it is computing TER or TCC. Variable naming convention is mandatory. Trigger_Engagement_Clarification.md is the highest-authority design document. |
| Status | Approved |
| Version | Trigger_Engagement_Clarification.md |

---

### CHG-009
| Field | Value |
|-------|-------|
| Change ID | CHG-009 |
| Date | 2026-02-10 |
| Category | BIZ |
| Decision ID | BIZ-004 |
| Source | Product Owner Review — Technical_Design_Addendum.md |
| Title | Historical Engagement Window Default — Last 90 Days (TCC Only) |
| Description | The historical engagement window for TCC calculation defaults to Last 90 Days. This applies to TCC (engine capacity) only, not to TER (which is cumulative by default). A user who engaged 6 months ago does not consume capacity in the current run under the default setting. |
| Reason | Pharma campaigns run on quarterly cycles. A 90-day window accurately reflects whether a user is "recently engaged" for the purpose of not re-engaging them. Annual windows would over-protect users who engaged long ago and reduce campaign throughput. |
| Impact | Historical file filter in load_historical_file() applies the cutoff date before counting engaged users. TER calculation uses all-time data. Two separate filter paths must exist and must never be cross-applied. |
| Status | Approved |
| Version | Technical_Design_Addendum.md |

---

### CHG-010
| Field | Value |
|-------|-------|
| Change ID | CHG-010 |
| Date | 2026-02-12 |
| Category | BIZ |
| Decision ID | BIZ-011 |
| Source | Architecture Review — Trigger_Engagement_Clarification.md |
| Title | QUALIFYING_ACTIONS as Category C System Constant |
| Description | QUALIFYING_ACTIONS is defined as a module-level constant in utils/schema_validator.py and imported from there everywhere. It is Category C (system controlled) in V1 — not user-configurable. Display sub-types map to {Click}; Email and WhatsApp map to {Open, Click}. Impression and Sent are never qualifying actions. |
| Reason | Making qualifying actions configurable in V1 creates risk that a user accidentally misconfigures TER/TCC in ways that are semantically inconsistent (e.g., counting Impression as qualifying for display, which has no business meaning). Stability of this constant ensures all 35 validation rules and all TCC computations agree on what constitutes engagement. |
| Impact | No module may define its own qualifying action set. All rule logic, audience manager, and behavior engine code must import QUALIFYING_ACTIONS from utils/schema_validator.py. Configurable qualifying actions deferred to V2 (FE-003). |
| Status | Approved |
| Version | Trigger_Engagement_Clarification.md |

---

### CHG-011
| Field | Value |
|-------|-------|
| Change ID | CHG-011 |
| Date | 2026-02-15 |
| Category | BIZ |
| Decision ID | BIZ-018 |
| Source | Technical Design Review — Technical_Design_Addendum.md |
| Title | Move On Click is Exclusive — C-001 Double-Advance Prevention |
| Description | When move_on_click=True and a click is received, the click-advance fires and the duration check for that day is skipped entirely. This prevents a 1-day Ad from advancing the user twice on the same day (once by click, once by duration expiry). The click-advance check is evaluated first; if it fires, duration processing is bypassed. |
| Reason | Without this rule, a user on a 1-day Ad who receives a click would advance twice: once for the click (move_on_click) and once for duration (1 day elapsed). This would skip an Ad in the journey, corrupting the journey sequence and the corresponding validation rules (HR-001). |
| Impact | Journey Engine must check click advance before duration advance. These two paths are mutually exclusive within a single simulation day. C-001 is a hard behavioral constraint. |
| Status | Approved |
| Version | Technical_Design_Addendum.md |

---

### CHG-012
| Field | Value |
|-------|-------|
| Change ID | CHG-012 |
| Date | 2026-02-15 |
| Category | BIZ |
| Decision ID | BIZ-019 |
| Source | Technical Design Review |
| Title | Campaign_ID Default Value — Insert "Default" If Absent |
| Description | If the Campaign_ID column is absent from a trigger or historical input file, insert a column with the value "Default" and log INFO. If the column is present but has null values, fillna("Default"). This prevents downstream primary key errors caused by null Campaign_IDs. |
| Reason | Requirements_v1.md did not specify Campaign_ID behavior for files produced by teams who are unaware of the Campaign_ID convention. The "Default" fallback allows these files to be processed without modification while preserving composite key integrity. |
| Impact | Both load_trigger_file() and load_historical_file() implement identical BIZ-019 logic. Campaign_ID is always non-null after loading. Audit logs record how many nulls were filled per file. |
| Status | Approved |
| Version | Technical_Design_Addendum.md |

---

### CHG-013
| Field | Value |
|-------|-------|
| Change ID | CHG-013 |
| Date | 2026-02-18 |
| Category | BIZ |
| Decision ID | BIZ-021 |
| Source | Technical Design Review |
| Title | Historical File Deduplication on Load — Before Any Filter |
| Description | drop_duplicates(subset=["Campaign_ID","User_ID","Date","Action","Channel"]) is applied immediately in load_historical_file(), before any date filtering, campaign filtering, or qualifying action filtering. The historical file is never trusted to be duplicate-free. |
| Reason | Marketing platform exports (Veeva, SFMC, HubSpot) frequently produce duplicate event rows from retry logic or multi-system joins. If duplicates are not removed before TCC calculation, the same engagement event counts twice, artificially inflating historical_engaged_users and reducing Remaining_Capacity below the correct value. |
| Impact | Deduplication is the first data transformation after date parsing. Order is: read → BIZ-019 Campaign_ID fill → validate columns → parse dates → deduplicate → filter. Any reordering of these steps requires a formal change request. |
| Status | Approved |
| Version | Technical_Design.md |

---

### CHG-014
| Field | Value |
|-------|-------|
| Change ID | CHG-014 |
| Date | 2026-02-18 |
| Category | BIZ |
| Decision ID | BIZ-023 |
| Source | Technical Design Review |
| Title | Weekly Counter Reset — ISO Monday Boundary, Before Processing |
| Description | Weekly fatigue counters (Weekly_Impressions, Weekly_Clicks, Weekly_Opens, Weekly_Engagements) are reset at the ISO week boundary (Monday, d.weekday() == 0). Reset is the first operation at the start of each simulation day, before any allocation, scoring, or fatigue enforcement. The check uses d.weekday() (Monday = 0), never isoweekday() (Monday = 1). |
| Reason | Requirements_v1.md specified "weekly" reset without defining the boundary. ISO Monday was chosen as the standard used in pharma marketing reporting calendars. Reset before processing prevents a user who receives their 3rd impression on Sunday from being blocked on Monday when the week rolls over. |
| Impact | iso_week_start() in utils/date_utils.py uses d - timedelta(days=d.weekday()). Any simulation day loop must call reset_weekly_counters() as its first statement if is_new_iso_week() is True. |
| Status | Approved |
| Version | Technical_Design.md |

---

### CHG-015
| Field | Value |
|-------|-------|
| Change ID | CHG-015 |
| Date | 2026-02-20 |
| Category | SIM |
| Decision ID | SIM-001 |
| Source | Technical Design Review — Technical_Design.md |
| Title | Composite Engagement Score Formula — 5 Weighted Components + Jitter |
| Description | The composite engagement score is: (w_eng × engagement_score) + (w_prof × profile_component) + (w_cre × creative_affinity_current_ad) + (w_cha × channel_affinity_current_channel) + (w_rec × reach_recency_normalized) + jitter(0, 0.05). Profile component = profile_multiplier / max(all_profile_multipliers). Reach recency = max(0, 1.0 - (days_since_reached / config.frequency_max)). |
| Reason | A multi-factor weighted score enables nuanced simulation behavior: highly engaged users on preferred channels with recent reach get higher scores, Dormant users on unfamiliar channels get lower scores. Single-factor scoring (engagement_score only) did not produce realistic variation in campaign output patterns. |
| Impact | Behavior Engine implements this formula. All five weight components must be stored in ConfigRegistry as Category B fields. Jitter (0–0.05) ensures no two users with identical profiles produce identical output in the same day. |
| Status | Approved |
| Version | Technical_Design.md |

---

### CHG-016
| Field | Value |
|-------|-------|
| Change ID | CHG-016 |
| Date | 2026-02-20 |
| Category | SIM |
| Decision ID | SIM-002 |
| Source | Technical Design Review |
| Title | Scoring Weights Are Category B — Advanced Configurable |
| Description | The five composite scoring weights (engagement_score, behavior_profile, creative_affinity, channel_affinity, reach_recency) are Category B parameters, configurable in Advanced Settings. Five sliders must sum to 1.0 (UI auto-normalizes). Default values: 0.30, 0.25, 0.15, 0.15, 0.15. V1 ships with defaults fixed; UI sliders deferred to V2 (FE-009). |
| Reason | V1 Advanced Settings UI does not yet expose weight sliders. The fields exist in ConfigRegistry with defaults, making the V2 UI addition a 1–2 day effort. Hardcoding weights in V1 while designing them as configurable avoids a schema change in V2. |
| Impact | ConfigRegistry must declare five float weight fields. config_loader.py populates them from JSON or uses defaults. BL-010 captures the missing field addition required. |
| Status | Approved (weights exist as defaults; UI sliders deferred to FE-009 / V2) |
| Version | Technical_Design.md |

---

### CHG-017
| Field | Value |
|-------|-------|
| Change ID | CHG-017 |
| Date | 2026-02-22 |
| Category | SIM |
| Decision ID | SIM-019 |
| Source | Technical Design Review |
| Title | Per-User Deterministic Seed via hashlib.md5 — Never Python hash() |
| Description | Per-user RNG seed = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 2**32. Python's built-in hash() is explicitly forbidden because it is non-deterministic across processes and Python versions (PYTHONHASHSEED). The MD5 approach produces the same seed for the same user_id across all runs, all machines, and all Python versions. |
| Reason | Reproducibility is a core requirement (same input → same output). hash() would produce different seeds on different machines or if Python's PYTHONHASHSEED environment variable differs. MD5 is deterministic and produces a 128-bit digest safely truncated to 32 bits. |
| Impact | _per_user_seed() in core/input_loader.py is the single implementation. All RNG generators for user-level randomness must be seeded from this function. |
| Status | Approved |
| Version | Technical_Design.md |

---

### CHG-018
| Field | Value |
|-------|-------|
| Change ID | CHG-018 |
| Date | 2026-03-01 |
| Category | CFG |
| Decision ID | CFG-005 |
| Source | Technical Design Review — Technical_Design_Addendum.md |
| Title | CONFIG_SCHEMA_VERSION = "2.0" — Mismatch Raises SchemaVersionError |
| Description | Configuration snapshots include a mandatory "schema_version": "2.0" key. Any code that loads a config snapshot must check this value and raise SchemaVersionError if it does not match CONFIG_SCHEMA_VERSION from utils/version.py. The schema version is "2.0" from V1 launch; "1.0" was an internal design draft that was never shipped. |
| Reason | Config files saved in the field will be reloaded in future runs. Without version enforcement, a user loading a V1 config snapshot into a V2 engine would get silent data errors or attribute errors rather than a clear migration message. SchemaVersionError gives the engine a clear path to refuse invalid configs and prompt the user to re-export. |
| Impact | config_io.save_config_snapshot() writes the version. config_io.load_config_snapshot() validates it. config_loader.load_config_from_dict() and load_config_from_json() also validate. SchemaVersionError must include both found and expected versions in the message. |
| Status | Approved |
| Version | Technical_Design_Addendum.md |

---

### CHG-019
| Field | Value |
|-------|-------|
| Change ID | CHG-019 |
| Date | 2026-03-05 |
| Category | BIZ |
| Decision ID | I-001 |
| Source | Technical Design Review |
| Title | Vendor Precedence — Per-Ad Override Over Campaign Default |
| Description | Effective vendor for an event = AdConfig.vendor if not None, else ConfigRegistry.default_vendor. A None per-ad vendor means "use the campaign default." An explicit non-None per-ad vendor always overrides the campaign-level default. |
| Reason | Some campaigns use a single vendor globally but selectively use a specialist vendor for one or two ads (e.g., a WhatsApp specialist vendor for the WhatsApp-channel ad in an otherwise email-primary journey). |
| Impact | ConfigRegistry.get_effective_vendor(ad) encapsulates this logic. All event-generation code must call get_effective_vendor() rather than reading AdConfig.vendor or default_vendor directly. |
| Status | Approved |
| Version | Technical_Design.md |

---

### CHG-020
| Field | Value |
|-------|-------|
| Change ID | CHG-020 |
| Date | 2026-03-10 |
| Category | VAL |
| Decision ID | VAL-001 |
| Source | Technical Design Review |
| Title | Hard Rule FAIL Blocks All Export Except ValidationReport |
| Description | Any Hard rule with FAIL status blocks export of all 7 output workbooks except ValidationReport.xlsx. ValidationReport is always exported to give the user diagnostic information. 15 hard rules; none can be disabled without Admin Override (developer-only flag). |
| Reason | Hard rules represent data integrity invariants (no Click without Impression, no engagement during cooling period). Exporting data that violates these rules would produce analytically unsound output that could corrupt downstream analytics pipelines. |
| Impact | Validation Engine must collect all rule results before exporting. Export Engine checks ValidationResult.is_blocking() before writing each workbook. ValidationReport uses openpyxl regardless of blocking status. |
| Status | Approved |
| Version | Technical_Design.md |

---

### CHG-021
| Field | Value |
|-------|-------|
| Change ID | CHG-021 |
| Date | 2026-03-10 |
| Category | VAL |
| Decision ID | VAL-002 |
| Source | Technical Design Review |
| Title | Soft Rules Never Block Export — 20 Soft Rules Produce WARNING Only |
| Description | Soft rules produce WARNING (rule miss) or PASS status only. No soft rule can block export regardless of outcome. Each soft rule has an independent enabled flag and optional severity_override. SR-020 (Composite Realism Score) is Advisory severity — always produces INFO, never WARNING. |
| Reason | Soft rules represent calibration targets (TER vs target, segment distribution). A campaign that misses its segment distribution target is not necessarily wrong — it may be correct given the input data. Blocking export on soft rule misses would prevent legitimate campaigns from completing. |
| Impact | Validation Engine must correctly distinguish Hard/Soft/Advisory results. The enabled flag and severity_override are stored in RuleConfig and applied before evaluation. |
| Status | Approved |
| Version | Technical_Design.md |

---

### CHG-022
| Field | Value |
|-------|-------|
| Change ID | CHG-022 |
| Date | 2026-03-15 |
| Category | CFG |
| Source | Technical_Design_Addendum.md |
| Title | Three-Tier Configuration Strategy — Category A/B/C |
| Description | All 85 configuration parameters are classified into three access tiers: Category A (23 parameters, Business User Configurable, main UI screens), Category B (44 parameters, Advanced Configurable, Advanced Settings screen), Category C (18 parameters, System Controlled, not exposed in UI). This replaces the Requirements_v1.md "simple settings / expert settings" two-tier model. |
| Reason | The two-tier model did not distinguish between parameters users should never touch (QUALIFYING_ACTIONS, CONFIG_SCHEMA_VERSION) and parameters that are valid for analyst-level users (scoring weights, profile evolution probabilities). Category C prevents accidental misconfiguration of system invariants. |
| Impact | Every parameter in ConfigRegistry must be classified. UI screens 3–6 are designed around Category A and B only. Category C parameters are hardcoded or computed at runtime. Future Category C → Category B promotions require a formal change request. |
| Status | Approved |
| Version | Technical_Design_Addendum.md |

---

### CHG-023
| Field | Value |
|-------|-------|
| Change ID | CHG-023 |
| Date | 2026-03-20 |
| Category | DATA |
| Source | Technical_Design_Addendum.md |
| Title | Four Behavior Profiles with Population Defaults and Density Thresholds |
| Description | Four behavior profiles: Highly_Engaged (multiplier 2.0, 10% population), Moderate (1.0, 40%), Passive (0.4, 35%), Dormant (0.1, 15%). New users assigned via weighted random draw. Historical users assigned via engagement density (qualifying events / active days): ≥0.30 → Highly_Engaged, ≥0.10 → Moderate, ≥0.02 → Passive, else Dormant. Historical assignment always overrides random draw. Profile evolution evaluated at run end using a separate RNG seed offset (+1). |
| Reason | Requirements_v1.md specified behavior profiles without defining population distributions, multipliers, or historical classification thresholds. These parameters are needed by the Behavior Engine (Phase 5) and must be consistent with the composite scoring formula. |
| Impact | Behavior Engine implements all four profile paths. ConfigRegistry stores population percentages and multipliers as Category B defaults. Historical density thresholds are Category C for V1. |
| Status | Approved |
| Version | Technical_Design_Addendum.md |

---

### CHG-024
| Field | Value |
|-------|-------|
| Change ID | CHG-024 |
| Date | 2026-03-25 |
| Category | DATA |
| Source | Technical_Design_Addendum.md |
| Title | Channel Affinity Initialization and Update Rules |
| Description | New users: all channel affinities = 0.5 (neutral). Historical users: three-tier initialization based on channel engagement vs target (never engaged → 0.2, below target → 0.5, at or above target → 0.8). Updates after each run: qualifying engagement at or above target → affinity += 0.05 (clamped to 1.0); reach events without qualifying engagement → affinity -= 0.02 (clamped to 0.0); no events on channel → no change. |
| Reason | Requirements_v1.md mentioned channel affinity as a concept but provided no initialization or update specification. Without explicit rules, different developers would implement incompatible affinity dynamics. |
| Impact | Behavior Engine (Phase 5) implements initialization and updates. All affinity fields stored as float32 in DataFrames. Boost/decay rates are Category C in V1; Category B promotion planned for V2 (FE-010 area). |
| Status | Approved |
| Version | Technical_Design_Addendum.md |

---

### CHG-025
| Field | Value |
|-------|-------|
| Change ID | CHG-025 |
| Date | 2026-04-05 |
| Category | DATA |
| Source | Phase 1 — project skeleton |
| Title | 9-Screen Streamlit UI Finalized |
| Description | The application UI is organized as exactly 9 screens: Home, Upload Files, Quick Setup, Journey Builder, Triggers & Segments, Advanced Settings (5 tabs), Review & Confirm (Audience Forecast), Run Generator (progress bar), Download Results. The 6-screen layout from Requirements_v1.md was expanded to accommodate the Advanced Settings 5-tab structure and the Audience Forecast screen. |
| Reason | The 6-screen wireframe did not have enough space for the 44 Category B parameters without overwhelming non-technical users. The Advanced Settings screen isolates complexity behind a distinct navigation step. Screen 7 (Audience Forecast) was added to provide TER/TCC preview before committing to a run. |
| Impact | app/pages/ contains 9 page modules. All UI components must maintain the Category A / Category B separation enforced by screen placement. |
| Status | Approved |
| Version | Architecture_v2.md / Wireframe Review |

---

### CHG-026
| Field | Value |
|-------|-------|
| Change ID | CHG-026 |
| Date | 2026-04-10 |
| Category | VAL |
| Source | Wireframe Review |
| Title | Screen 7 (Audience Forecast) Displays Both TER and TCC |
| Description | Screen 7 (Review & Confirm) shows both TER (reporting projection) and TCC (remaining capacity) side by side. TER is displayed as a percentage projection given current historical data. TCC is displayed as a count of users expected to be newly engaged in this run. Plain-English labels are used to prevent user confusion between the two metrics. |
| Reason | Early wireframes showed only TER. Product Owner review identified that non-technical users conflate TER and TCC and may cancel a run they believe is over-target when in fact the engine has remaining capacity. Showing both metrics with clear labels prevents this. |
| Impact | Screen 7 must compute both TER projection and TCC remaining capacity before the run starts. These are read-only projections; they do not modify config or state. |
| Status | Approved |
| Version | Wireframe Review |

---

### CHG-027
| Field | Value |
|-------|-------|
| Change ID | CHG-027 |
| Date | 2026-05-15 |
| Category | PERF |
| Source | Phase 1 Technical Review |
| Title | float32 Mandatory for All Affinity and Score Columns in DataFrames |
| Description | All engagement_score, channel_affinity_*, and creative_affinity_* columns in DataFrames must use float32 dtype (not float64). pd.Categorical required for all bounded string columns (Behavior_Profile, Eligibility_Status, Journey_Status, Channel, Action, Trigger_Name, Segment). These conventions are documented in docs/performance_guidelines.md. |
| Reason | At 50,000 users with 10+ creative affinity columns, float64 columns consume ~4MB per column per simulation day. float32 halves this to ~2MB per column. Categorical dtype for string columns reduces memory by 60–80% for bounded value sets. Combined, these conventions enable the engine to fit within typical desktop memory limits (8–16 GB). |
| Impact | Every DataFrame construction and transformation must apply the correct dtypes. reconcile_creative_affinity_columns() enforces float32 on all Creative_Affinity_* columns. Schema reconciliation is the enforcement point. |
| Status | Approved |
| Version | Phase 1 / docs/performance_guidelines.md |

---

### CHG-028 — CHG-035 (Phase 2 Remediation — Defect Corrections)

The following changes are approved corrections of implementation defects identified in PHASE_2_REMEDIATION_PLAN.md (2026-06-21). All are classified as DEFECT / Patch severity. All were completed during Phase 2 Remediation Waves 1–5 (2026-06-21 through 2026-06-22).

| CHG-ID | Defect Ref | Title | Status | Completed | Wave |
|--------|-----------|-------|--------|-----------|------|
| CHG-028 | MM-001 | Fix _load_trigger_configs — wrong TriggerConfig fields | **APPROVED** | 2026-06-22 | Wave 3 (REM-005) |
| CHG-029 | MM-002 | Fix _load_segment_configs — wrong SegmentConfig fields | **APPROVED** | 2026-06-22 | Wave 3 (REM-006) |
| CHG-030 | MM-003 | Fix _load_channel_configs — wrong ChannelConfig fields | **APPROVED** | 2026-06-22 | Wave 3 (REM-007) |
| CHG-031 | MM-004 | Fix load_config_from_dict — 11 wrong ConfigRegistry field names | **APPROVED** | 2026-06-22 | Wave 3 (REM-008) |
| CHG-032 | MM-005/006 | Fix config_registry.py and user_state.py enum imports | **APPROVED** | 2026-06-21 | Wave 1 (REM-001, REM-002) |
| CHG-033 | TCC-001 | Fix RemainingCapacityRow.compute() — int() → math.ceil() | **APPROVED** | 2026-06-22 | Wave 2 (REM-003) |
| CHG-034 | PV-001 | Delete dead iterrows() block in load_historical_file() | **APPROVED** | 2026-06-22 | Wave 4 (REM-009) |
| CHG-035 | MT-001/023 | Fix test helpers — wrong enum values and constructor signatures | **APPROVED** | 2026-06-22 | Wave 5 (REM-010–013) |

Full specifications for each are in PHASE_2_REMEDIATION_PLAN.md, Sections 1–5.
Execution details in WAVE_1_EXECUTION_REPORT.md, WAVE_2_EXECUTION_REPORT.md, WAVE_3_EXECUTION_REPORT.md, WAVE_4_5_EXECUTION_REPORT.md.

### CHG-036 — Phase 2 Remediation Wave 6 (Documentation Pass)

| Field | Value |
|-------|-------|
| Change ID | CHG-036 |
| Category | DEFECT (documentation) |
| Severity | Patch |
| Title | Phase 2 Wave 6 Documentation Pass — REM-015 through REM-018, BL-NEW-001, BL-NEW-002 |
| Description | Close all remaining Phase 2 documentation defects: fix is_qualifying_action() docstring (REM-015); fix count_historical_engaged_users() docstring (REM-016); add LM-002 dedup ordering comment (REM-017); add LM-003 qualifying filter ordering comment and resolve DOC-003–DOC-005 inline comment errors (REM-018); create tests/test_utils/test_schema_validator.py (BL-NEW-001/EX-P2-001); audit PROJECT_CHANGE_LOG.md CHG-028–CHG-035 (BL-NEW-002); formally assign BL-006/BL-007 to Phase 3. |
| Files Changed | utils/schema_validator.py, core/input_loader.py, tests/test_utils/test_schema_validator.py, PROJECT_CHANGE_LOG.md, PROJECT_BACKLOG.md, PROJECT_MEMORY.md |
| REM Items Closed | REM-015, REM-016, REM-017, REM-018 |
| BL Items Closed | BL-NEW-001, BL-NEW-002 |
| BL Items Assigned | BL-006 → Phase 3 Infrastructure, BL-007 → Phase 3 Infrastructure |
| Status | **APPROVED** |
| Completed | 2026-06-22 |
| Wave | Wave 6 (Documentation Pass) |
| Execution Report | WAVE_6_EXECUTION_REPORT.md |

---

## 5. Deferred Changes Log

These changes were considered and formally deferred to a named future release. Each has a recorded reason. Deferral is not rejection — the feature is wanted but not now.

---

### DEF-001 — Multi-Campaign Per Run

| Field | Value |
|-------|-------|
| Deferral ID | DEF-001 |
| Date | 2026-01-10 |
| Source | Architecture Review |
| Feature | Support multiple campaign_ids in a single run |
| Deferred To | V2 |
| Reason | Multi-campaign support requires cross-campaign user deduplication, per-campaign journey configurations, and a multi-campaign output naming convention. Complexity is disproportionate to V1 use case where single-campaign runs are the norm. ARCH-002 composite PK is already designed for V2 readiness. |
| Backlog Ref | FE-001 / BL-018 |
| Status | Deferred |

---

### DEF-002 — Channel Plugin Framework

| Field | Value |
|-------|-------|
| Deferral ID | DEF-002 |
| Date | 2026-01-10 |
| Source | Architecture Review |
| Feature | Plugin framework for adding new channels without code changes |
| Deferred To | V3 |
| Reason | Plugin interfaces require stable BaseChannel contracts across all downstream engines. V1 and V2 will prove interface stability. Plugin packaging and discovery mechanism (entry points) adds significant infrastructure complexity. |
| Backlog Ref | FE-002 / BL-029 |
| Status | Deferred |

---

### DEF-003 — Configurable Qualifying Actions

| Field | Value |
|-------|-------|
| Deferral ID | DEF-003 |
| Date | 2026-02-10 |
| Source | Technical Design Review |
| Feature | Allow users to configure which actions count as qualifying engagement (Category B) |
| Deferred To | V2 |
| Reason | Making QUALIFYING_ACTIONS configurable in V1 risks semantic inconsistency (e.g., counting Impression as qualifying). Stability as a Category C constant ensures all 35 validation rules and TCC computation use the same definition. V2 can safely introduce configurability after the validation framework is proven stable. |
| Backlog Ref | FE-003 / BL-019 |
| Status | Deferred |

---

### DEF-004 — Background Thread Execution

| Field | Value |
|-------|-------|
| Deferral ID | DEF-004 |
| Date | 2026-01-15 |
| Source | Architecture Review |
| Feature | Run simulation pipeline in background thread/process to avoid blocking Streamlit UI |
| Deferred To | V3 |
| Reason | Streamlit's threading model has known limitations with state management. Background execution requires careful RNG state handling (DEF-007) and cross-thread error propagation. V1 runs synchronously in < 15 min at target scale — acceptable for desktop use. |
| Backlog Ref | FE-004 / BL-030 |
| Status | Deferred |

---

### DEF-005 — Historical Affinity Bucketing Thresholds as Category B

| Field | Value |
|-------|-------|
| Deferral ID | DEF-005 |
| Date | 2026-03-25 |
| Source | Technical_Design_Addendum.md |
| Feature | Expose channel affinity initialization thresholds (0.2/0.5/0.8) as Category B configurable |
| Deferred To | V2 |
| Reason | V1 defaults are calibrated for typical pharma campaigns. Threshold configurability adds UI complexity for marginal benefit. Calibration research (RE-007 / BL-048) must complete before the right ranges can be established. |
| Backlog Ref | FE-005 / BL-020 |
| Status | Deferred |

---

### DEF-006 — Timezone Configuration

| Field | Value |
|-------|-------|
| Deferral ID | DEF-006 |
| Date | 2026-03-01 |
| Source | Technical Design Review |
| Feature | Campaign-level timezone setting; timezone-aware date arithmetic |
| Deferred To | V2 |
| Reason | All V1 date arithmetic is timezone-naive. Adding timezone awareness requires updating iso_week_start(), all cutoff date calculations, and the weekly reset logic. Global pharma teams are the likely V2 target; V1 users are assumed to be in a single time zone. |
| Backlog Ref | FE-006 / BL-021 |
| Status | Deferred |

---

### DEF-007 — RNG State Snapshot Per Stage

| Field | Value |
|-------|-------|
| Deferral ID | DEF-007 |
| Date | 2026-02-22 |
| Source | Technical Design Review |
| Feature | Persist numpy.random.Generator state after each pipeline stage for exact replay |
| Deferred To | V2 |
| Reason | V1 reproducibility via per-user MD5 seeds (SIM-019) is sufficient for single-run reproducibility. Multi-run exact reproducibility (replay from mid-run) requires serializing and restoring the Generator state after each stage — a significant infrastructure addition. |
| Backlog Ref | FE-007 / BL-022 |
| Status | Deferred |

---

### DEF-008 — Standalone Validation_Rules_Catalog.md

| Field | Value |
|-------|-------|
| Deferral ID | DEF-008 |
| Date | 2026-03-10 |
| Source | Technical Design Review |
| Feature | Single authoritative machine-readable catalog for all 35 validation rules |
| Deferred To | V1.1 (Post-V1) |
| Reason | Current rule specifications are distributed across uploads/Validation_Rules_Catalog.md, Technical_Design.md, and rule class docstrings. Consolidation is a governance improvement with no runtime impact. Phase 7 implementation is needed before the catalog can be finalized. |
| Backlog Ref | FE-008 / BL-011 |
| Status | Deferred |

---

### DEF-009 — Scoring Weights UI Sliders

| Field | Value |
|-------|-------|
| Deferral ID | DEF-009 |
| Date | 2026-02-20 |
| Source | Technical Design Review |
| Feature | Five Category B sliders in Advanced Settings for composite scoring weights |
| Deferred To | V2 (or V1.1 if schedule permits) |
| Reason | V1 ships scoring weights as ConfigRegistry defaults (0.30/0.25/0.15/0.15/0.15). Fields are already in ConfigRegistry (BL-010 adds them). The UI addition is estimated at 1–2 days once fields exist. Deferred to reduce V1 scope risk. |
| Backlog Ref | FE-009 / BL-023 |
| Status | Deferred |

---

## 6. Rejected Changes Log

These approaches were considered and explicitly not adopted. The rationale is preserved for future reference. Rejected changes should not be re-proposed without first reading the rationale recorded here.

---

### CHG-REJ-001 — pd.to_excel() for Output Workbooks

| Field | Value |
|-------|-------|
| Rejection ID | CHG-REJ-001 |
| Date | 2026-01-20 |
| Category | ARCH |
| Source | Architecture Review |
| Proposal | Use pd.to_excel() (with xlsxwriter or openpyxl engine) for all output workbooks |
| Rejection Reason | pd.to_excel() wraps openpyxl internally but provides limited formatting control — no cell-level number formats, no column width control, no multi-sheet workbooks with different schemas per sheet (required for the Run_Metadata sheet present in every workbook). Direct openpyxl write is ~15% faster for large outputs and gives complete formatting control. pd.to_excel() adds an abstraction layer over the same library with no benefit. |
| Alternative Adopted | openpyxl.Workbook() direct write (ARCH-009 / CHG-005) |
| Status | Rejected — Permanent |

---

### CHG-REJ-002 — iterrows() for Per-User Event Generation

| Field | Value |
|-------|-------|
| Rejection ID | CHG-REJ-002 |
| Date | 2026-01-20 |
| Category | PERF |
| Source | Architecture Review |
| Proposal | Use iterrows() to iterate over user records and generate events per user per day |
| Rejection Reason | iterrows() is 100–1000× slower than vectorized operations. At 50,000 users across a 90-day simulation (4.5M user-days), iterrows() would require hours of processing time. Vectorized approaches (np.where, np.select, boolean masks, groupby) produce the same results in minutes. |
| Alternative Adopted | DataFrame-first vectorized architecture (ARCH-011 / CHG-006) |
| Status | Rejected — Permanent. Any future proposal to re-introduce iterrows() must pass a performance analysis showing it is faster than available vectorized alternatives. |

---

### CHG-REJ-003 — Creative Affinity as JSON Blob Column (Option B)

| Field | Value |
|-------|-------|
| Rejection ID | CHG-REJ-003 |
| Date | 2026-02-05 |
| Category | DATA |
| Source | Product Owner Review — Creative_Affinity_Design_Review.md |
| Proposal | Store all creative affinities as a single JSON string column in UserState: creative_affinities = '{"Ad1": 0.7, "Ad2": 0.5}' |
| Rejection Reason | JSON blob columns require serialize/deserialize on every read/write, cannot be used in vectorized operations (no np.where on a JSON column), prevent direct column-level DataFrame operations, and make UserState.xlsx unreadable to non-technical users. |
| Alternative Adopted | Dynamic Creative_Affinity_{ad_name} columns as float32 (ARCH-012 / CHG-007) |
| Status | Rejected — Permanent |

---

### CHG-REJ-004 — Python hash() for Per-User Seed Generation

| Field | Value |
|-------|-------|
| Rejection ID | CHG-REJ-004 |
| Date | 2026-02-22 |
| Category | SIM |
| Source | Technical Design Review |
| Proposal | Use Python's built-in hash(user_id) to generate per-user RNG seeds |
| Rejection Reason | Python's hash() is non-deterministic across processes and Python versions. PYTHONHASHSEED randomizes it by default. The same user_id would produce different seeds on different machines or different Python invocations, destroying run reproducibility. This is a silent failure — the engine would appear to work correctly but produce different output for identical inputs. |
| Alternative Adopted | hashlib.md5(user_id.encode()).hexdigest() truncated to 32 bits (SIM-019 / CHG-017) |
| Status | Rejected — Permanent |

---

### CHG-REJ-005 — Object-Per-User Processing Architecture

| Field | Value |
|-------|-------|
| Rejection ID | CHG-REJ-005 |
| Date | 2026-01-15 |
| Category | ARCH |
| Source | Architecture Review |
| Proposal | Process each user as a UserState object instance, calling methods on the object in a loop |
| Rejection Reason | Object-per-user processing is clear and readable but cannot be vectorized. At 50,000 users, a Python for loop over user objects processes ~50K iterations × 90 days = 4.5M iterations. Even at 1ms per iteration, this is 4,500 seconds. DataFrame bulk operations process the same work in seconds via numpy C extensions. |
| Alternative Adopted | DataFrame-first architecture (ARCH-011 / CHG-006). UserState dataclass retained for config objects and single-record contracts only. |
| Status | Rejected — Permanent |

---

### CHG-REJ-006 — Two-Tier Configuration (Simple/Expert)

| Field | Value |
|-------|-------|
| Rejection ID | CHG-REJ-006 |
| Date | 2026-03-15 |
| Category | CFG |
| Source | Technical Design Review |
| Proposal | Organize configuration into two tiers: "Simple Settings" (non-technical users) and "Expert Settings" (analysts) |
| Rejection Reason | Two-tier model does not distinguish between parameters that analysts may safely change (scoring weights, fatigue limits) and parameters that should never be exposed in UI (QUALIFYING_ACTIONS definition, CONFIG_SCHEMA_VERSION, weekly reset boundary). A parameter incorrectly placed in "Expert Settings" instead of a locked "System" tier creates a path for users to break system invariants. |
| Alternative Adopted | Three-tier Category A/B/C model (CHG-022). Category C is not exposed in any UI screen. |
| Status | Rejected — Permanent |

---

### CHG-REJ-007 — Single TER Metric for Both Reporting and Capacity Control

| Field | Value |
|-------|-------|
| Rejection ID | CHG-REJ-007 |
| Date | 2026-02-10 |
| Category | BIZ |
| Source | Product Owner Review — Trigger_Engagement_Clarification.md |
| Proposal | Use a single "Trigger Engagement Rate" metric for both reporting (what % of all-time users have engaged?) and engine capacity (how many more users can be engaged?) |
| Rejection Reason | The two concepts require different denominators. TER uses all-time cumulative triggered users (for accurate historical reporting). TCC uses current trigger file users (for calculating new capacity). Using a single metric with the wrong denominator for either purpose produces either inflated TER (using current file only) or over-restricted TCC (using all-time users). Both errors corrupt the simulation output. |
| Alternative Adopted | Formal separation of TER and TCC as distinct concepts with distinct variable naming conventions (BIZ-003 / CHG-008) |
| Status | Rejected — Permanent. Any proposal to reunify TER and TCC must be reviewed against Trigger_Engagement_Clarification.md in its entirety. |

---

## 7. Future Enhancements Moved to Backlog

This section captures all future enhancement candidates discovered during any project phase. Items are numbered FE-001 onward. Items marked NEW were added during the backlog creation review (2026-06-21).

---

| FE-ID | Title | Source | Category | Release Target | Backlog Ref | Priority |
|-------|-------|--------|----------|----------------|-------------|---------|
| FE-001 | Multi-Campaign Per Run | DEF-001 / Architecture Review | ARCH | V2 | BL-018 | P1 |
| FE-002 | Channel Plugin Framework | DEF-002 / Architecture Review | ARCH | V3 | BL-029 | P1 |
| FE-003 | Configurable Qualifying Actions | DEF-003 / Technical Design | BIZ | V2 | BL-019 | P2 |
| FE-004 | Background Thread Execution | DEF-004 / Architecture Review | PERF | V3 | BL-030 | P2 |
| FE-005 | Historical Affinity Thresholds as Category B | DEF-005 / Technical Design | CFG | V2 | BL-020 | P2 |
| FE-006 | Timezone Configuration | DEF-006 / Technical Design | BIZ | V2 | BL-021 | P2 |
| FE-007 | RNG State Snapshot Per Stage | DEF-007 / Technical Design | SIM | V2 | BL-022 | P2 |
| FE-008 | Standalone Validation Rules Catalog | DEF-008 / Technical Design | VAL | V1.1 | BL-011 | P3 |
| FE-009 | Scoring Weights UI Sliders | SIM-002 / CHG-016 | UI | V2 | BL-023 | P1 |
| FE-010 | Profile Evolution Probabilities as Category B | Technical_Design_Addendum | CFG | V2 | BL-024 | P2 |
| FE-011 | Profile Density Thresholds as Category B | Technical_Design_Addendum | CFG | V2 | BL-025 | P2 |
| FE-012 | Journey Branching — Conditional Ad Sequences | Product Owner | BIZ | V2 | BL-027 | P2 |
| FE-013 | Monte Carlo Audience Forecast | Wireframe Review | UI | V2 | BL-028 | P2 |
| FE-014 | REST API / Headless Mode | Architecture Review | ARCH | V3 | BL-031 | P2 |
| FE-015 | Run History Tracking | Product Owner | UI | V1.1 | BL-013 | P2 |
| FE-016 | CSV Export for EngagementEvents | Product Owner | DATA | V1.1 | BL-012 | P2 |
| FE-017 | Dry Run / Validate-Only Mode | Product Owner | UI | V1.1 | BL-017 | P2 |

---

### FE-018 — Rolling TER Windows

| Field | Value |
|-------|-------|
| FE-ID | FE-018 |
| Status | NEW — Added 2026-06-21 |
| Title | Rolling TER Windows |
| Category | BIZ / VAL |
| Release Target | V2 |
| MoSCoW | Won't Have (V1) |
| Priority | P2 |

**Description:** TER currently supports two modes: Cumulative (all-time) and Rolling Window (90/180/365 days, configurable). The Rolling Window mode exists as a configurable TER option (configurable via `ter_mode` in ConfigRegistry) but has not been validated in how it interacts with SR-005 (TER vs target engagement rate validation rule). Specifically, a rolling window TER can drop below target simply because early-campaign engagements aged out of the window, not because the campaign is underperforming. SR-005 must be taught to understand the TER mode context: for rolling TER, a drop below target is an INFO rather than a WARNING if the campaign is still within its first window period.

**Reason Deferred:** Rolling window TER is configurable in V1 but the validation rule context-awareness requires a formal amendment to SR-005's evaluation logic. V1 SR-005 evaluates TER against target without window context. Getting this right requires product alignment on what "below target" means in a rolling window context.

**Business Value:** High — rolling TER is more actionable for ongoing campaigns than cumulative TER (which never decreases once an engagement is recorded).

**Technical Complexity:** Medium — changes to SR-005 evaluation logic and Screen 7 TER display to show window context.

**Dependencies:** SR-005 implementation (Phase 7), V2 TER mode design.

**Backlog Ref:** To be added as BL-056.

**Date Added:** 2026-06-21
**Source:** Backlog Creation Review — Chief Architect

---

### FE-019 — Trigger Saturation Protection

| Field | Value |
|-------|-------|
| FE-ID | FE-019 |
| Status | NEW — Added 2026-06-21 |
| Title | Trigger Saturation Protection |
| Category | BIZ |
| Release Target | V2 |
| MoSCoW | Won't Have (V1) |
| Priority | P1 |

**Description:** When TCC Remaining Capacity for a trigger reaches zero, the V1 engine stops generating new qualifying engagement events for that trigger but continues to generate reach events (Impression, Sent). There is no safeguard preventing a campaign from being configured in a way that immediately saturates at run start (e.g., 1,000 users at 100% engagement rate, with 1,000 historically engaged users in the window). The engine silently produces zero engagement events with no user-visible warning beyond SR-006 (an informational soft rule).

A Trigger Saturation Protection feature would: (1) evaluate saturation before the run starts; (2) display a prominent warning on Screen 7 if any trigger is pre-saturated; (3) offer the user an option to extend the historical window, reduce the engagement target, or proceed anyway; (4) log the saturation event clearly in the SimulationReport.

**Reason Deferred:** SR-006 exists as an informational check but does not gate the run or warn pre-run. V1 users who configure a saturated trigger will be confused when no engagement events appear in the output. However, the complete solution requires Screen 7 integration and possibly a pre-run capacity estimation step that is out of scope for the current UI design.

**Business Value:** High — prevents silent zero-engagement runs that waste user time.

**Technical Complexity:** Medium — pre-run capacity check in audience_manager.py, Screen 7 warning UI, SR-006 severity elevation option.

**Dependencies:** Phase 3 (Audience Manager), Phase 7 (Validation), Phase 9 (UI).

**Backlog Ref:** To be added as BL-057.

**Date Added:** 2026-06-21
**Source:** Backlog Creation Review — Chief Architect

---

### FE-020 — Segment Saturation Protection

| Field | Value |
|-------|-------|
| FE-ID | FE-020 |
| Status | NEW — Added 2026-06-21 |
| Title | Segment Saturation Protection |
| Category | BIZ |
| Release Target | V2 |
| MoSCoW | Won't Have (V1) |
| Priority | P2 |

**Description:** Parallel to FE-019 at the segment level. A segment (e.g., Cardiology) within a trigger may be fully saturated (all historical Cardiology users have already been engaged within the window) while other segments have remaining capacity. V1 does not break TCC down by segment — it operates at the trigger level. Segment-level saturation would require: (1) per-segment TCC calculation in audience_manager.py; (2) a segment saturation soft rule (SR-NEW, analogous to SR-006); (3) Screen 7 segment saturation indicators; (4) a new SegmentCapacityRow model analogous to RemainingCapacityRow.

**Reason Deferred:** V1 TCC is trigger-scoped only (per ARCH-001 single-campaign scope). Segment-level capacity requires per-segment historical engagement counts, adding complexity to the audience resolution step. SR-007 already warns on segment distribution drift; segment saturation is a related but distinct concept.

**Business Value:** Medium — segment saturation is less common than trigger saturation but important for highly segmented campaigns.

**Technical Complexity:** High — requires new model (SegmentCapacityRow), new soft rule, and Screen 7 integration.

**Dependencies:** FE-019, Phase 3, Phase 7, Phase 9.

**Backlog Ref:** To be added as BL-058.

**Date Added:** 2026-06-21
**Source:** Backlog Creation Review — Chief Architect

---

### FE-021 — Engagement Decay Model

| Field | Value |
|-------|-------|
| FE-ID | FE-021 |
| Status | NEW — Added 2026-06-21 |
| Title | Engagement Decay Model |
| Category | SIM |
| Release Target | V2 |
| MoSCoW | Won't Have (V1) |
| Priority | P2 |

**Description:** V1 engagement score decays at a fixed rate of -0.002 per day of inactivity (hardcoded). This produces a linear decay curve regardless of how long the user has been inactive. A more realistic decay model would apply: (1) exponential decay (score × 0.995 per day) rather than linear subtraction, which better models the diminishing returns of long-inactive users; (2) a minimum floor before decay kicks in (e.g., no decay if user engaged within the last 7 days); (3) behavior-profile-aware decay rates (Dormant users decay faster than Passive users).

**Reason Deferred:** V1 fixed linear decay is a reasonable first approximation. Exponential decay requires a calibration study (RE-001 / BL-042) to confirm which model better predicts re-engagement probability. The decay model change would affect all Behavior Engine scoring, requiring re-validation of SR-020 Realism Score thresholds.

**Business Value:** Medium-High — a more realistic decay model produces more accurate TER projections and better long-campaign simulations.

**Technical Complexity:** Medium — Behavior Engine update, calibration research (BL-042), SR-020 threshold review.

**Dependencies:** BL-042 (calibration research), Phase 5 (Behavior Engine stable in V1).

**Backlog Ref:** To be added as BL-059.

**Date Added:** 2026-06-21
**Source:** Backlog Creation Review — Chief Architect

---

### FE-022 — Historical Engagement Weighting

| Field | Value |
|-------|-------|
| FE-ID | FE-022 |
| Status | NEW — Added 2026-06-21 |
| Title | Historical Engagement Weighting |
| Category | SIM |
| Release Target | V2 |
| MoSCoW | Won't Have (V1) |
| Priority | P2 |

**Description:** V1 treats all historical engagement events equally regardless of recency — a click from 89 days ago counts the same as a click from yesterday when initializing channel affinity and TCC capacity calculations. A Historical Engagement Weighting model would apply time-decay weights to historical events: events within the last 30 days weight at 1.0, 31–60 days at 0.7, 61–90 days at 0.4, beyond 90 days at 0.0 (within the default window). Weighted historical engaged users = sum of fractional weights rather than distinct user count. This would make TCC remaining capacity more generous for users whose historical engagement was long ago, recognizing they are "cooling off" and may be receptive again.

**Reason Deferred:** V1 TCC uses a binary engaged/not-engaged count. Weighted TCC requires a fractional remaining capacity concept that changes the RemainingCapacityRow model, the audience manager, and SR-006 interpretation. Calibration research (BL-048) must confirm whether weighting produces more realistic output before this is designed.

**Business Value:** High — weighted TCC better reflects real-world re-engagement potential of aging historical engagements.

**Technical Complexity:** High — model changes (RemainingCapacityRow fractional capacity), audience manager changes, validation rule updates.

**Dependencies:** BL-048 (calibration research), Phase 3 stable in V1, FE-019.

**Backlog Ref:** To be added as BL-060.

**Date Added:** 2026-06-21
**Source:** Backlog Creation Review — Chief Architect

---

### FE-023 — Campaign Seasonality Modeling

| Field | Value |
|-------|-------|
| FE-ID | FE-023 |
| Status | NEW — Added 2026-06-21 |
| Title | Campaign Seasonality Modeling |
| Category | SIM |
| Release Target | V3 |
| MoSCoW | Won't Have (V1) |
| Priority | P3 |

**Description:** V1 engagement probability is constant across the simulation period (with the exception of user-level score evolution). Real pharma campaigns experience strong seasonality: lower engagement rates during August–September (conference season), higher rates in Q1 (formulary update period), spikes around product launch events, and drops during holiday periods. A Campaign Seasonality Model would allow users to define a monthly engagement multiplier profile (January = 1.1×, August = 0.7×, etc.) applied as an additional factor in the composite scoring formula. The multiplier profile is a Category B parameter configured as a 12-month slider array in Advanced Settings.

**Reason Deferred:** Seasonality modeling requires: (1) a new scoring formula component; (2) 12 new ConfigRegistry fields; (3) a UI calendar widget on the Advanced Settings screen; (4) SR-020 Realism Score awareness that seasonal variation is expected and not a scoring anomaly. Significant scope addition with no V1 use case driving it.

**Business Value:** Medium — useful for multi-quarter campaign simulations. Most V1 use cases run shorter simulations where seasonality is negligible.

**Technical Complexity:** High — composite score formula change (SIM-001 amendment required), ConfigRegistry additions, UI calendar widget, SR-020 review.

**Dependencies:** Phase 5 (Behavior Engine stable), V2 ConfigRegistry schema, V3 UI enhancements.

**Backlog Ref:** To be added as BL-061.

**Date Added:** 2026-06-21
**Source:** Backlog Creation Review — Chief Architect

---

## 8. Architecture Decision History

A chronological summary of all architecture decisions and when they were made. Full rationale is in Sections 4 and 6.

| Decision ID | Date | Description | Status | CHG-ID |
|------------|------|-------------|--------|--------|
| ARCH-001 | 2026-01-10 | Single campaign per run in V1 | Approved | CHG-001 |
| ARCH-002 | 2026-01-10 | Composite primary key (Campaign_ID, User_ID) | Approved | CHG-002 |
| ARCH-003 | 2026-01-10 | 11-stage pipeline with strict execution order | Approved | CHG-003 |
| ARCH-004 | 2026-01-12 | BaseChannel abstract class for Display, Email, WhatsApp | Approved | — |
| ARCH-005 | 2026-01-15 | core/ never imports from app/; import tier hierarchy | Approved | CHG-004 |
| ARCH-006 | 2026-01-18 | Self-registering rule classes in rules/hard/ and rules/soft/ | Approved | — |
| ARCH-007 | 2026-01-20 | conftest.py + pytest as the test framework | Approved | — |
| ARCH-008 | 2026-01-20 | pyproject.toml as the project build/metadata file | Approved | — |
| ARCH-009 | 2026-01-20 | openpyxl direct write; no pd.to_excel() | Approved | CHG-005 |
| ARCH-010 | 2026-01-20 | run_controller.py as sole pipeline orchestrator | Approved | — |
| ARCH-011 | 2026-01-20 | DataFrame-first; no iterrows() in production code | Approved | CHG-006 |
| ARCH-012 | 2026-02-05 | Dynamic creative affinity columns (Option A) | Approved | CHG-007 |

**Rejected Architecture Proposals:**
| Proposal | Date Rejected | Reason | CHG-REJ |
|---------|--------------|--------|---------|
| pd.to_excel() for outputs | 2026-01-20 | Limited formatting control; same underlying library | CHG-REJ-001 |
| iterrows() for user processing | 2026-01-20 | 100–1000× slower than vectorized | CHG-REJ-002 |
| JSON blob for creative affinities | 2026-02-05 | No vectorized operations possible | CHG-REJ-003 |
| Python hash() for seeds | 2026-02-22 | Non-deterministic across processes | CHG-REJ-004 |
| Object-per-user processing | 2026-01-15 | O(n) Python loop; cannot be parallelized | CHG-REJ-005 |

---

## 9. Business Rule Evolution

How the core business rules evolved from Requirements_v1.md through design phases.

### Journey Logic Evolution

| Rule | Origin | Version Introduced | Change from v1 |
|------|--------|-------------------|----------------|
| C-001: Move On Click Exclusive | Technical_Design_Addendum | Addendum | Not in Requirements_v1. Added after discovering double-advance bug in journey logic design. |
| C-002: Campaign ID filter in Audience Manager | Technical_Design_Addendum | Addendum | Requirements_v1 did not specify that historical data must be filtered to matching Campaign_ID before capacity calculation. |
| C-003: Weekly reset before processing | Technical_Design_Addendum | Addendum | Requirements_v1 said "reset weekly counters each week" without specifying before or after processing. Added BEFORE constraint explicitly. |
| C-005: Historical dedup on load | Technical_Design | v1 | Requirements_v1 assumed historical files are clean. Technical_Design added mandatory dedup step. |

### Trigger/Segment Priority Evolution

| Rule | Origin | Change from v1 |
|------|--------|----------------|
| Priority 1 = Highest | Technical_Design | Requirements_v1 was ambiguous on priority direction (1 = highest or 1 = lowest). Formally resolved as 1 = highest. |
| Trigger History — pipe-delimited accumulation | Technical_Design_Addendum | Not in Requirements_v1. Added to support multi-run campaign analytics. |
| Journey continuation on re-trigger | Technical_Design_Addendum | Requirements_v1 unclear on whether existing journey is reset on re-trigger. Formally resolved as "continue, update priority". |

### Cooling Period Evolution

| Rule | Origin | Change from v1 |
|------|--------|----------------|
| Default 90 days | Technical_Design | Requirements_v1 said "cooling period" without a default. |
| Re-entry after cooling | Technical_Design | Requirements_v1 did not define re-entry mechanics. |
| Impression/Sent allowed during cooling | Technical_Design_Addendum | Not in Requirements_v1. Added: reach events permitted; engagement events blocked. |

### Error Rate Threshold Evolution

| Tier | Origin | Change from v1 |
|------|--------|----------------|
| Three-tier thresholds | Technical_Design | Requirements_v1 had a single 1% error rate threshold. Tiered approach (2%/1%/0.5%) added to reflect that small user populations statistically tolerate higher error rates than large populations. |

---

## 10. Trigger Engagement Evolution

This section traces the evolution of the TER / TCC distinction — the single most significant design clarification in the project.

### Timeline

**Requirements_v1.md (2025-12-01):** Defined "Trigger Engagement Rate" as a single metric. Denominator was ambiguous — some sections implied all-time users, others implied current trigger file users. No separation between reporting and capacity control.

**Architecture_v2.md (2026-01-10):** Introduced "Target Engagement Rate" as a configurable parameter per trigger. Did not yet formally separate reporting (TER) from capacity control (TCC). Confusion persisted.

**Technical_Design.md (2026-02-15):** First document to distinguish between TER as a reporting KPI and TCC as an engine driver in separate subsections. Still did not define the denominator unambiguously.

**Technical_Design_Addendum.md (2026-03-15):** Added the `historical_engagement_window` parameter explicitly as a TCC control only. Confirmed TER uses all-time data. Introduced the Remaining_Capacity clamping rule (≥ 0). Added the `ter_mode` setting (Cumulative vs. Rolling Window) as TER-only.

**Trigger_Engagement_Clarification.md (2026-04-01 — HIGHEST AUTHORITY):** Formally resolved all remaining TER/TCC ambiguity:
- TER denominator: All users ever triggered across all runs (cumulative).
- TCC denominator: Current trigger file users only.
- TER numerator: All users who have ever performed a qualifying action.
- TCC numerator source: Historical file before the run (not current run events).
- Variable naming convention: `ter_*` for TER variables, `tcc_*` for TCC variables.
- QUALIFYING_ACTIONS is the single source of truth for both.
- TER does not drive the engine. TCC does.

### Impact of Clarification

| Component | Pre-Clarification | Post-Clarification |
|-----------|------------------|-------------------|
| Audience Manager | Mixed TER/TCC calculation | Separate TCC path; TER deferred to Validation |
| RemainingCapacityRow | Not yet modeled | Uses current trigger file denominator; clamp ≥ 0 |
| SR-005 | TER check undefined | TER vs target, cumulative denominator |
| SR-006 | Not defined | Remaining Capacity ≤ 0, informational |
| Variable names | engagement_rate_* (mixed) | ter_* and tcc_* strictly enforced |
| QUALIFYING_ACTIONS | Defined ad hoc | Centralized in schema_validator.py, Category C |

### Active Monitoring

The TER/TCC distinction is the most frequently misunderstood concept in this codebase. Any developer implementing audience allocation, capacity calculation, or TER reporting must re-read Trigger_Engagement_Clarification.md in full before writing any code in those areas. The variable naming convention (ter_* / tcc_*) is mandatory and enforced during code review.

---

## 11. Journey Engine Evolution

How journey logic was defined and refined from initial requirements through technical design.

### Linear Journey (Requirements_v1 → Current)

Requirements_v1.md described a "user journey through ads" without specifying the advance mechanism. Technical Design formalized:

- Ad sequence is strictly ordered by ad_order (1-based).
- Duration advance: user advances after duration_days days on an ad.
- Click advance: if move_on_click=True and a click is received, advance immediately.
- C-001: These two advance paths are mutually exclusive within a single day.
- Final ad completion triggers journey_status = "Completed" and cooling period start.

### Re-Entry Logic Evolution

Requirements_v1.md described cooling but not re-entry. Technical_Design_Addendum added:

- After cooling_period_end, user status becomes "Re-Entry" (not automatic).
- Re-entry only occurs if the user appears in a new trigger file after cooling.
- Re-entry users restart from Ad1. Journey history is preserved in UserState.
- allow_reentry flag in ConfigRegistry enables/disables this behavior.

### Journey Continuation on Re-Trigger

A key clarification added in Technical_Design_Addendum:

- If a user in an active journey appears again in a new trigger file, the journey CONTINUES (not restarted).
- Their Trigger_Name and Segment may be updated via priority resolution.
- But Current_Ad, Days_In_Ad, and Journey_Start_Date are preserved.
- This is distinct from re-entry (which is for post-cooling users).

### Journey Branching

Not in Requirements_v1.md. Not in V1 design. Captured as future enhancement FE-012 / BL-027 for V2. V1 journeys are linear only.

---

## 12. Validation Rule Evolution

How the validation framework was designed and what changed from initial requirements.

### Framework Evolution

| Aspect | Requirements_v1 | Current Design |
|--------|----------------|----------------|
| Rule count | "Validation checks" (undefined count) | 15 hard + 20 soft + 1 advisory = 36 total |
| Severity levels | Pass / Fail | Hard (FAIL/PASS), Soft (WARNING/PASS), Advisory (INFO) |
| Blocking behavior | "Errors prevent export" | Only Hard FAIL blocks; Soft WARNING never blocks |
| Rule on/off | Not specified | Each rule has enabled flag + severity_override |
| Admin override | Not specified | developer-only admin_override flag for Hard rules |
| Realism score | Not in requirements | SR-020 Advisory Composite Realism Score (0–100) |

### Hard Rule Additions (Post-Requirements_v1)

Rules added in Technical_Design that were not in Requirements_v1:

- HR-009: Max daily impressions per user (default 3) — not in requirements.
- HR-012: Max weekly engagements per user (default 3) — not in requirements.
- HR-013: No engagement during engagement cooldown period — added in Addendum.
- HR-015: All event Campaign_IDs must match config.campaign_id — added for ARCH-001 enforcement.

### Soft Rule Additions (Post-Requirements_v1)

- SR-005: TER vs target (post Trigger_Engagement_Clarification).
- SR-006: Remaining capacity ≤ 0 (post Trigger_Engagement_Clarification).
- SR-007/SR-008: Segment/Trigger distribution ±10% — formalized tolerance in Addendum.
- SR-020: Composite Simulation Realism Score — added in Addendum; not in Requirements_v1.

### Rule Enable/Disable Feature

Not in Requirements_v1. Added in Technical_Design to allow analysts to disable soft rules that are not applicable to a specific campaign type (e.g., SR-007 segment distribution is not meaningful for a single-segment campaign). Hard rules cannot be disabled without Admin Override.

---

## 13. UI Evolution

How the user interface evolved from the initial wireframe concept through the current 9-screen design.

### Screen Count Evolution

| Phase | Screen Count | Key Change |
|-------|-------------|-----------|
| Requirements_v1.md | 6 screens | Home, Upload, Setup, Journey, Run, Download |
| Wireframe v1 | 7 screens | Added Review screen (basic) |
| Wireframe v2 | 8 screens | Separated Triggers & Segments from Journey Builder |
| Architecture_v2 | 9 screens | Added Advanced Settings; Review became Audience Forecast |

### Advanced Settings — Tab Evolution

Requirements_v1 had a single "Expert Settings" section. Technical_Design_Addendum organized 44 Category B parameters into 5 tabs:

1. Engagement Rules — fatigue limits, cooldown, weekly caps
2. Channel Settings — per-channel CTR targets, open rates, timing distributions
3. User Behavior — profile percentages, multipliers, evolution probabilities, affinity parameters
4. Rule Management — enable/disable toggles for all 35 validation rules
5. System — historical window, campaign match mode, admin override flag

### Audience Forecast (Screen 7) Evolution

Requirements_v1 described a "Review before run" screen. Technical_Design added:
- TER projection (what % of all-time users will have engaged?)
- TCC remaining capacity (how many new users will be engaged this run?)
- Segment distribution preview
- Warning display for pre-saturated triggers (FE-019 for full implementation)

Both TER and TCC are shown simultaneously after the Product Owner review identified confusion risk (CHG-026).

### Config Save/Load Evolution

Requirements_v1 mentioned "save settings" without specifying format. Technical_Design formalized:
- JSON snapshot format with mandatory schema_version key
- Save: config_io.save_config_snapshot() writes schema_version = "2.0"
- Load: config_io.load_config_snapshot() validates version; raises SchemaVersionError on mismatch
- Screen 3 (Quick Setup) hosts save/load controls with file picker

Enhanced save/load UX (named config library, diff view) deferred to V1.1 (FE-015 related, BL-016).

---

## 14. Version History

### Document Versions

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-21 | Chief Architect | Initial creation. Captured all changes from Requirements_v1.md through Phase 2 completion and remediation review. Added FE-018 through FE-023 as new backlog candidates. |

### Project Document Versions Referenced

| Document | Version / Date | Role in Change History |
|----------|---------------|----------------------|
| Requirements_v1.md | v1.0 / 2025-12-01 | Baseline — all changes measured against this |
| Architecture_v1.md | v1.0 / 2026-01-05 | Original architecture (superseded by v2) |
| Architecture_v2.md | v2.0 / 2026-01-10 | Current architecture baseline |
| Technical_Design.md | v1.0 / 2026-02-15 | Core technical design |
| Technical_Design_Addendum.md | v1.0 / 2026-03-15 | Additions and clarifications to Technical_Design |
| Trigger_Engagement_Clarification.md | v1.0 / 2026-04-01 | Highest authority — TER vs TCC resolution |
| Creative_Affinity_Design_Review.md | v1.0 / 2026-02-05 | Option A vs B decision for creative affinity storage |
| Configuration_Strategy.md | v1.0 / 2026-03-15 | Category A/B/C classification |
| PROJECT_DECISIONS.md | v1.0 / 2026-06-21 | Single source of truth for all 100 decisions |
| Implementation_Plan.md | v1.0 / 2026-05-01 | Phase-by-phase implementation specifications |
| Phase_2_Implementation.md | v1.0 / 2026-06-15 | Phase 2 approved implementations (3,001 lines) |
| PHASE_2_REMEDIATION_PLAN.md | v1.0 / 2026-06-21 | Phase 2 defect analysis and correction plan |
| PROJECT_BACKLOG.md | v1.0 / 2026-06-21 | Complete future enhancement register |
| PROJECT_CHANGE_LOG.md | v1.0 / 2026-06-21 | This document |

### Next Review Milestone

This document must be updated at the end of Phase 3. At minimum, the following sections must be reviewed:
- Section 4: Add any new approved changes from Phase 3 (User State Manager, Audience Manager)
- Section 5: Resolve Deferred Decisions DD-013 and DD-014 (trigger/segment tiebreak rules — Phase 3 blockers)
- Section 9: Record how trigger priority tiebreak and segment tiebreak were resolved
- Section 10: Record TCC implementation decisions made in Phase 3 audience_manager.py
- Section 14: Increment document version

---

*PROJECT_CHANGE_LOG.md — Version 1.0*
*Engagement Data Generator v1.0*
*Chief Architect — 2026-06-21*
*Baseline: Requirements_v1.md (2025-12-01)*
*This document is part of project governance. No change may be implemented without a corresponding entry in Section 4 or Section 5.*
