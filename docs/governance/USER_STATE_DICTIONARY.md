# UserState Field Dictionary

## Engagement Data Generator — v1.0

| Metadata | Value |
|----------|-------|
| Document | USER_STATE_DICTIONARY.md |
| Version | 1.0 |
| Created | 2026-06-22 |
| Last Updated | 2026-06-22 (Phase 3 pre-wave) |
| Authority | PROJECT_DECISIONS.md (ARCH-015 through ARCH-020) |
| Status | AUTHORITATIVE — supersedes any prior column count reference |

---

## Overview

UserState is the central mutable per-user record for a single campaign run. It is implemented as a Python dataclass in `models/user_state.py`. The DataFrame representation is produced by Stage 3 (User State Init) and carried through all subsequent pipeline stages.

**Column naming convention:** All field names in the Python dataclass use snake_case. The export layer (Phase 8, Stage 11) maps snake_case field names to Pascal_Case column headers for Excel output. Within the pipeline, all code uses snake_case field names directly.

**Field count:** 35 static fields + N dynamic creative affinity columns.

> Note: Previous specifications (PHASE_3_PREP_IMPLEMENTATION.md, early PHASE_3_IMPLEMENTATION_PLAN.md drafts) referred to 29 columns. The correct count is 35 static fields. The discrepancy arose from: (a) the implementation plan listing only named columns and omitting `weekly_engagements`, `ad_click_received`, `total_lifetime_engagements`, `run_count`, `engagement_cooldown_end`; and (b) two new fields (`historical_engaged`, `is_valid`) added in Phase 3 pre-wave (2026-06-22).

---

## Field Count Summary

| Category | Count |
|----------|-------|
| Identity fields | 2 |
| Trigger & segment assignment | 3 |
| Eligibility & journey status | 5 |
| Creative state | 2 |
| Engagement scoring | 4 |
| Weekly action counters (ARCH-016) | 4 |
| Lifetime counters | 2 |
| Reach & recency | 2 |
| Simulation run tracking | 2 |
| Trigger history | 4 |
| Channel & vendor | 2 |
| Phase 3 pre-wave additions | 2 |
| **Total static fields** | **35** |
| Dynamic creative affinity columns | N (one per ad in config.ads) |

---

## Architecture Decision Cross-References

| Decision | Summary | Impact on This Dictionary |
|----------|---------|--------------------------|
| ARCH-012 | Dynamic creative affinity columns | creative_affinities stored as dict in dataclass; expanded to Creative_Affinity_{ad_name} columns in DataFrame |
| ARCH-015 | EligibilityStatus canonical values | eligibility_status field uses: NEW, ACTIVE, COOLING, RE_ENTRY (="Re_Entry"), SKIPPED, EXCLUDED |
| ARCH-016 | Weekly counters are per-action, not per-channel | weekly_impressions/clicks/opens/engagements are action-type counters, not channel-type counters |
| ARCH-017 | Trigger_History delimiter is pipe | trigger_history uses TRIGGER_HISTORY_DELIMITER = "\|" from utils/constants.py |
| ARCH-018 | DROPPED → EXCLUDED in classify_eligibility | eligibility_status = EXCLUDED when journey_status = DROPPED |
| ARCH-020 | allow_reentry=False → EXCLUDED | eligibility_status = EXCLUDED when cooling expired and allow_reentry=False |

---

## Section 1: Identity Fields

### Field 1: campaign_id
| Attribute | Value |
|-----------|-------|
| Python type | str |
| Nullable | No |
| Default | (required — no default) |
| Written by | Stage 3 (User State Init) — set at construction |
| Read by | All stages — primary key component |
| Description | Campaign identifier. Part of composite primary key (campaign_id, user_id) per ARCH-002. Sourced from ConfigRegistry.campaign_id. |

### Field 2: user_id
| Attribute | Value |
|-----------|-------|
| Python type | str |
| Nullable | No |
| Default | (required — no default) |
| Written by | Stage 3 (User State Init) — set at construction |
| Read by | All stages — primary key component |
| Description | User identifier. Part of composite primary key (campaign_id, user_id) per ARCH-002. Sourced from the trigger file User_ID column. |

---

## Section 2: Trigger & Segment Assignment

### Field 3: trigger_name
| Attribute | Value |
|-----------|-------|
| Python type | str \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 3 (resolve_triggers) |
| Read by | Stage 4 (Audience Resolution), Stage 11 (Export) |
| Description | The winning trigger name assigned to this user for this run. None until Stage 3 resolves trigger assignment. Updated on every simulation run. |

### Field 4: segment
| Attribute | Value |
|-----------|-------|
| Python type | str \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 3 (resolve_segments per ARCH-014) |
| Read by | Stage 4, Stage 11 |
| Description | The segment assigned from the winning trigger's row per ARCH-014. Follows the winning trigger — no independent segment resolution. |

### Field 5: first_trigger_name
| Attribute | Value |
|-----------|-------|
| Python type | str \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 3 (resolve_triggers) — set only if currently None |
| Read by | Stage 11 (Export) |
| Description | The trigger name from the user's very first trigger appearance. Set once and never overwritten (immutable after first set). |

---

## Section 3: Eligibility & Journey Status

### Field 6: eligibility_status
| Attribute | Value |
|-----------|-------|
| Python type | str |
| Nullable | No |
| Default | EligibilityStatus.NEW.value = "New" |
| Written by | Stage 3 (classify_eligibility — ARCH-015) |
| Read by | Stage 4, Stage 11 |
| Description | Canonical eligibility state per ARCH-015. Valid values: "New", "Active", "Cooling", "Re_Entry", "Skipped", "Excluded". NEVER "Re-Entry" (hyphen). Deprecated values ELIGIBLE/INELIGIBLE/COMPLETED must not be written by any Phase 3+ code. |

### Field 7: journey_status
| Attribute | Value |
|-----------|-------|
| Python type | str |
| Nullable | No |
| Default | JourneyStatus.NOT_STARTED.value = "Not_Started" |
| Written by | Stage 4 (Journey Engine) |
| Read by | Stage 3 (classify_eligibility), Stage 4, Stage 11 |
| Description | Journey progression state. Valid values: "Not_Started", "Active", "Completed", "Dropped". JourneyStatus.DROPPED maps to EligibilityStatus.EXCLUDED per ARCH-018. |

### Field 8: journey_start_date
| Attribute | Value |
|-----------|-------|
| Python type | date \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 4 — set when user enters a journey |
| Read by | Stage 4, Stage 11 |
| Description | The date the user first entered the journey. Set once on first Active transition. |

### Field 9: journey_completion_date
| Attribute | Value |
|-----------|-------|
| Python type | date \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 4 — set when journey_status transitions to Completed |
| Read by | Stage 4, Stage 11 |
| Description | The date the user completed the journey. Null until journey completes. |

### Field 10: cooling_period_end
| Attribute | Value |
|-----------|-------|
| Python type | date \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 4 — computed as journey_completion_date + config.cooling_period_days |
| Read by | Stage 3 (classify_eligibility), Stage 11 |
| Description | The date the cooling period ends. Used by classify_eligibility to assign COOLING vs RE_ENTRY vs EXCLUDED. |

---

## Section 4: Creative State (Current Ad)

### Field 11: current_ad
| Attribute | Value |
|-----------|-------|
| Python type | str \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 4 (Journey Engine) |
| Read by | Stage 4, Stage 5 (Behavior Engine), Stage 11 |
| Description | The ad name currently being shown to this user. Updated as the user progresses through the journey. |

### Field 12: days_in_ad
| Attribute | Value |
|-----------|-------|
| Python type | int \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 4 |
| Read by | Stage 4, Stage 5 |
| Description | Number of days the user has been on the current_ad. Used for Move-On-Click and duration-based progression. |

---

## Section 5: Engagement Scoring

### Field 13: behavior_profile
| Attribute | Value |
|-----------|-------|
| Python type | str |
| Nullable | No |
| Default | BehaviorProfile.MODERATE.value = "Moderate" |
| Written by | Stage 5 (Behavior Engine) |
| Read by | Stage 5, Stage 6 (Scoring), Stage 11 |
| Description | Behavioral classification. Valid values: "Highly_Engaged", "Moderate", "Passive", "Dormant". |

### Field 14: engagement_score
| Attribute | Value |
|-----------|-------|
| Python type | float |
| Nullable | No |
| Default | DEFAULT_ENGAGEMENT_SCORE = 0.5 (from utils/constants.py) |
| Written by | Stage 5 (Behavior Engine) |
| Read by | Stage 6 (Composite Score), Stage 11 |
| Description | Per-user engagement score in [0.0, 1.0]. Updated by behavior engine based on user interactions. Initial value 0.5 avoids cold-start bias. |

### Field 15: channel_affinity_display
| Attribute | Value |
|-----------|-------|
| Python type | float |
| Nullable | No |
| Default | DEFAULT_CHANNEL_AFFINITY = 0.5 (from utils/constants.py) |
| Written by | Stage 5 (Behavior Engine) |
| Read by | Stage 6 (Composite Score), Stage 11 |
| Description | Affinity score for Display-family channels in [0.0, 1.0]. Applies to Display, Endemic_Display, Programmatic_Display, Banner. |

### Field 16: channel_affinity_email
| Attribute | Value |
|-----------|-------|
| Python type | float |
| Nullable | No |
| Default | DEFAULT_CHANNEL_AFFINITY = 0.5 |
| Written by | Stage 5 |
| Read by | Stage 6, Stage 11 |
| Description | Affinity score for Email channel in [0.0, 1.0]. |

### Field 17: channel_affinity_whatsapp
| Attribute | Value |
|-----------|-------|
| Python type | float |
| Nullable | No |
| Default | DEFAULT_CHANNEL_AFFINITY = 0.5 |
| Written by | Stage 5 |
| Read by | Stage 6, Stage 11 |
| Description | Affinity score for WhatsApp channel in [0.0, 1.0]. |

---

## Section 6: Weekly Action Counters (ARCH-016)

> ARCH-016: These are per-ACTION counters, not per-channel counters. Each counter tracks a different action type across all channels. Counters reset on ISO Monday (BIZ-023/C-003) via reset_weekly_counters().

### Field 18: weekly_impressions
| Attribute | Value |
|-----------|-------|
| Python type | int |
| Nullable | No |
| Default | 0 |
| Written by | Stage 6 (Fatigue Engine) |
| Read by | Stage 6, Stage 11 |
| Description | Count of Impression-type events in the current ISO week. Capped by ConfigRegistry.weekly_impression_cap. |

### Field 19: weekly_clicks
| Attribute | Value |
|-----------|-------|
| Python type | int |
| Nullable | No |
| Default | 0 |
| Written by | Stage 6 (Fatigue Engine) |
| Read by | Stage 6, Stage 11 |
| Description | Count of Click-type events in the current ISO week. Capped by ConfigRegistry.weekly_click_cap. |

### Field 20: weekly_opens
| Attribute | Value |
|-----------|-------|
| Python type | int |
| Nullable | No |
| Default | 0 |
| Written by | Stage 6 (Fatigue Engine) |
| Read by | Stage 6, Stage 11 |
| Description | Count of Open-type events in the current ISO week. Capped by ConfigRegistry.weekly_open_cap. |

### Field 21: weekly_engagements
| Attribute | Value |
|-----------|-------|
| Python type | int |
| Nullable | No |
| Default | 0 |
| Written by | Stage 6 (Fatigue Engine) |
| Read by | Stage 6, Stage 11 |
| Description | Count of qualifying engagement events in the current ISO week. Capped by ConfigRegistry.weekly_engagement_cap. Qualifying actions per C-004: Click for Display-family; Open+Click for Email and WhatsApp. |

---

## Section 7: Lifetime Counters

### Field 22: total_lifetime_engagements
| Attribute | Value |
|-----------|-------|
| Python type | int |
| Nullable | No |
| Default | 0 |
| Written by | Stage 5 (Behavior Engine) |
| Read by | Stage 5, Stage 11 |
| Description | Cumulative count of all qualifying engagement events since the user was first initialized. Never resets. |

### Field 23: ad_click_received
| Attribute | Value |
|-----------|-------|
| Python type | bool |
| Nullable | No |
| Default | False |
| Written by | Stage 4 (Journey Engine) — set True on first Click event |
| Read by | Stage 4 (Move-On-Click logic), Stage 11 |
| Description | True if the user has received at least one Click on the current ad. Used to trigger Move-On-Click journey progression (C-001). Reset when ad advances. |

---

## Section 8: Reach & Recency

### Field 24: last_reached_date
| Attribute | Value |
|-----------|-------|
| Python type | date \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 5 (Behavior Engine) |
| Read by | Stage 6 (Recency scoring), Stage 11 |
| Description | The most recent date on which this user received any delivery (impression, open, or click). Used in the reach-recency scoring component (SIM-001, MM-008). |

### Field 25: last_engagement_date
| Attribute | Value |
|-----------|-------|
| Python type | date \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 5 (Behavior Engine) |
| Read by | Stage 5, Stage 6, Stage 11 |
| Description | The most recent date on which this user had a qualifying engagement. Used for engagement cooldown and behavior scoring. |

---

## Section 9: Simulation Run Tracking

### Field 26: run_count
| Attribute | Value |
|-----------|-------|
| Python type | int |
| Nullable | No |
| Default | 0 |
| Written by | Stage 3 — incremented by initialize() on each run |
| Read by | Stage 3, Stage 11 |
| Description | Number of times this user has been initialized (i.e., number of simulation runs in which this user appeared). |

### Field 27: state_as_of_date
| Attribute | Value |
|-----------|-------|
| Python type | date |
| Nullable | No |
| Default | (required — passed to new() classmethod) |
| Written by | Stage 3 — set at construction; updated by finalize_state() |
| Read by | All stages |
| Description | The simulation date this state record reflects. Updated to the current simulation date by finalize_state() at end of each day. |

---

## Section 10: Engagement Cooldown

### Field 28: engagement_cooldown_end
| Attribute | Value |
|-----------|-------|
| Python type | date \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 5 (Behavior Engine) — set after a qualifying engagement |
| Read by | Stage 5 (is_in_cooldown()), Stage 6 |
| Description | Date through which the user is in engagement cooldown. User will not receive additional engagement events until this date has passed. Set to last_engagement_date + config.engagement_cooldown_days. |

---

## Section 11: Trigger History

### Field 29: trigger_history
| Attribute | Value |
|-----------|-------|
| Python type | str \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 3 (resolve_triggers) |
| Read by | Stage 11 (Export) |
| Description | Pipe-delimited (ARCH-017) string of all trigger names assigned to this user, in chronological order (oldest first, newest last). Example: "Trigger_A\|Trigger_B\|Trigger_A". No deduplication. TRIGGER_HISTORY_DELIMITER = "\|" in utils/constants.py is the sole delimiter reference — never use inline "\|" literals. |

### Field 30: first_trigger_date
| Attribute | Value |
|-----------|-------|
| Python type | date \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 3 (resolve_triggers) — set only if currently None |
| Read by | Stage 11 (Export) |
| Description | The simulation date of the user's first trigger appearance. Set once and never overwritten. |

### Field 31: total_trigger_appearances
| Attribute | Value |
|-----------|-------|
| Python type | int |
| Nullable | No |
| Default | 0 |
| Written by | Stage 3 (resolve_triggers) — incremented by 1 on each run |
| Read by | Stage 11 (Export) |
| Description | Total number of simulation runs in which this user was assigned a trigger. Incremented on each resolve_triggers() call. |

---

## Section 12: Channel & Vendor

### Field 32: channel
| Attribute | Value |
|-----------|-------|
| Python type | str \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 4 (Journey Engine) — set to the channel of the current ad |
| Read by | Stage 11 (Export) |
| Description | The delivery channel for the current ad. Derived from the current_ad's ChannelConfig. |

### Field 33: vendor
| Attribute | Value |
|-----------|-------|
| Python type | str \| None |
| Nullable | Yes |
| Default | None |
| Written by | Stage 4 (Journey Engine) |
| Read by | Stage 11 (Export) |
| Description | The vendor for the current ad delivery. Resolved via ConfigRegistry.get_effective_vendor() — per-ad vendor overrides campaign default per I-001. |

---

## Section 13: Phase 3 Pre-Wave Additions (2026-06-22)

### Field 34: historical_engaged
| Attribute | Value |
|-----------|-------|
| Python type | bool |
| Nullable | No |
| Default | False |
| Written by | Stage 3 (User State Init) — set True when historical engagement data is processed |
| Read by | Stage 4 (Audience Resolution) — compute_remaining_capacity() |
| Description | True if this user had at least one qualifying engagement in the historical window (BIZ-004 / BIZ-011). Determines whether the user is counted against the trigger's historical_engaged_users count in TCC calculations. Default False — assume no prior history until proven. |

### Field 35: is_valid
| Attribute | Value |
|-----------|-------|
| Python type | bool |
| Nullable | No |
| Default | True |
| Written by | Stage 10 (ValidationEngine) — set False when any hard or soft rule FAIL is recorded |
| Read by | Stage 11 (Excel Export) — ValidationReport generation |
| Description | True while all evaluated validation rules pass for this user. Set to False by ValidationEngine when a hard rule (HR-*) or soft rule (SR-*) FAIL is recorded. Default True — a user is valid until marked invalid. |

---

## Section 14: Dynamic Creative Affinity Columns (ARCH-012)

These are NOT static dataclass fields. They are stored as `creative_affinities: dict[str, float]` in the Python dataclass and expanded to individual DataFrame columns by `reconcile_creative_affinity_columns()` in `utils/excel_utils.py`.

| Attribute | Value |
|-----------|-------|
| Column naming | Creative_Affinity_{ad_name} (one column per ad in config.ads) |
| Python type (dataclass) | dict[str, float] |
| Python type (DataFrame) | float32 |
| Nullable | No |
| Default | DEFAULT_CREATIVE_AFFINITY = 0.5 (from utils/constants.py) |
| Written by | Stage 3 (new() classmethod initializes to 0.5 for each ad); Stage 5 (Behavior Engine updates based on user interactions) |
| Read by | Stage 6 (Composite Score); Stage 11 (Export) |
| Description | Per-ad creative affinity score in [0.0, 1.0]. The dict key is ad_name from AdConfig. The DataFrame column name is Creative_Affinity_{ad_name}. The exact set of columns depends on config.ads at runtime. |

---

## Section 15: EligibilityStatus Canonical Values (ARCH-015)

| Value | String | Semantics | Phase 3+ usage |
|-------|--------|-----------|----------------|
| EligibilityStatus.NEW | "New" | User has never entered this campaign | Canonical — use |
| EligibilityStatus.ACTIVE | "Active" | User is currently in an active journey | Canonical — use |
| EligibilityStatus.COOLING | "Cooling" | Journey complete; cooling period still running | Canonical — use |
| EligibilityStatus.RE_ENTRY | "Re_Entry" | Cooling expired; allow_reentry=True (ARCH-020) | Canonical — use; underscore NOT hyphen |
| EligibilityStatus.SKIPPED | "Skipped" | In-scope but excluded due to capacity constraints | Canonical — use |
| EligibilityStatus.EXCLUDED | "Excluded" | Permanently ineligible (DROPPED, allow_reentry=False, or hard exclusion — ARCH-018, ARCH-020) | Canonical — use |
| EligibilityStatus.ELIGIBLE | "Eligible" | Deprecated alias for ACTIVE | DEPRECATED — do not use in Phase 3+ |
| EligibilityStatus.INELIGIBLE | "Ineligible" | Deprecated alias for SKIPPED | DEPRECATED — do not use in Phase 3+ |
| EligibilityStatus.COMPLETED | "Completed" | Deprecated alias for COOLING or RE_ENTRY | DEPRECATED — do not use in Phase 3+ |

---

## Section 16: USER_STATE_REQUIRED_COLUMNS (utils/schema_validator.py)

The minimum required columns for a valid UserState DataFrame, as enforced by `validate_required_columns()`:

```python
USER_STATE_REQUIRED_COLUMNS = [
    "Campaign_ID", "User_ID", "Eligibility_Status", "Journey_Status",
    "Behavior_Profile", "Engagement_Score", "State_As_Of_Date",
    "historical_engaged", "is_valid",
]
```

Note: `historical_engaged` and `is_valid` use snake_case (pipeline representation). These columns were added in Phase 3 pre-wave (2026-06-22) per PHASE_3_BLOCKER_RESOLUTION.md RESOLUTION 06.

---

*USER_STATE_DICTIONARY.md — Version 1.0*
*Engagement Data Generator v1.0*
*Created: 2026-06-22 (Phase 3 pre-wave) | Last Updated: 2026-06-22*
*This document is the authoritative reference for all UserState fields.*
*Changes to UserState fields require simultaneous updates to this document, TRACEABILITY_MATRIX.md, and PROJECT_DECISIONS.md.*
