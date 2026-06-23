# TRIGGER AND RE-ENTRY DECISION MATRIX
## Engagement Data Generator — Final Business Rules Audit

**Document ID:** TDM-001  
**Version:** 1.0  
**Date:** 2026-06-23  
**Classification:** Business Decision Authority Document — Engineering Must Not Deviate  
**Status:** REQUIRES SIGN-OFF BEFORE WAVE 1 IMPLEMENTATION BEGINS  
**Authored by:** Product Owner / CTO / Principal Architect / QA Director / Release Manager  
**Input Documents:** ARP-001, DMR-001, USR-001, HPR-001, TJR-001, IWP-001, TST-001

---

## PURPOSE

This document resolves every business-rule ambiguity identified across the seven approved remediation architecture documents. Each decision area was found to have one or more open questions that — left unanswered — would require an engineering team to make a product assumption during implementation.

Every scenario below follows the same structure:

- **Business Situation** — The specific ambiguity encountered in the architecture.
- **Recommended Behavior** — The decision this document makes.
- **Alternative Behaviors Considered** — Other viable options evaluated.
- **Pros** — Why the recommended decision is correct.
- **Cons** — What it sacrifices or risks.
- **Recommended Decision** — Definitive statement an engineer can implement directly.
- **Impacted Components** — Specific files and classes that must implement this decision.
- **Acceptance Criteria** — Measurable test conditions that confirm correct implementation.

---

## TABLE OF CONTENTS

1. Trigger Priority Logic
2. Trigger Conflict Resolution
3. Multi-Trigger Membership
4. Journey Interruptions
5. Journey Continuation Rules
6. Historical Audience Continuation
7. Cooling Period Re-Entry
8. Cooling Period Override
9. Journey Completion Handling
10. Weekly Simulation Carry-Forward Rules
11. Historical Completion Lifecycle
12. Re-Triggering Scenarios
13. Existing User vs New User Processing
14. Multi-Run Simulation Behavior
15. Trigger Hierarchy Rules

---

## SECTION 1 — TRIGGER PRIORITY LOGIC

### Decision 1.1 — Same-Priority Tie-Breaking

**Business Situation:** `TriggerConfig.priority: int` is used to rank triggers when a user qualifies under more than one. The TRIGGER_JOURNEY_REMEDIATION document notes that same-priority triggers currently resolve alphabetically by trigger_name (ARCH-013). It is not specified whether this alphabetic fallback is a permanent business rule or an implementation artifact that should be replaced.

**Recommended Behavior:** Alphabetic tie-breaking by `trigger_name` is the permanent, documented tie-breaking rule. It is deterministic, reproducible, and requires no additional configuration.

**Alternative Behaviors Considered:**
- A: Tie-break by `distribution_pct` descending (higher distribution wins). Logical but adds coupling between distribution and priority that has no business justification.
- B: Tie-break by insertion order in the config. Non-deterministic across config serialization formats.
- C: Raise a configuration error if two triggers have identical priority. Forces the operator to resolve ties explicitly, but adds friction for single-trigger and two-trigger campaigns where priority has never mattered.

**Pros:** Alphabetic tie-breaking is fully reproducible given the same config, requires no additional UI surface, and is self-documenting (priority=1 always means "highest"; among equals, A before B). Engineers can implement it with `sorted(triggers, key=lambda t: (t.priority, t.trigger_name))` — a one-liner.

**Cons:** The business may someday want a different tie-breaking rule (e.g., recency of trigger event date). Alphabetic ordering has no inherent campaign-business meaning.

**Recommended Decision:** Alphabetic by `trigger_name` (ascending, case-insensitive) is the permanent tie-breaking rule when two triggers have identical `priority` values. This must be documented in `TriggerConfig` docstring and in the `TriggerJourneyResolver` sort contract. No UI change is needed. This rule applies to: trigger selection order in multi-trigger membership, cohort processing order in `EngagementGenerator`, and TCC evaluation order.

**Impacted Components:**
- `core/trigger_journey_resolver.py` — trigger iteration order
- `core/engagement_generator.py` — per-trigger cohort processing order
- `core/audience_manager.py` — TCC evaluation order
- `models/trigger_config.py` — docstring for `priority` field

**Acceptance Criteria:**
1. Given Trigger_A (priority=1, name="Zebra") and Trigger_B (priority=1, name="Apple"), Trigger_B is processed first in all pipeline stages.
2. Given Trigger_A (priority=1) and Trigger_B (priority=2), Trigger_A is processed first regardless of name.
3. `sorted(config.triggers, key=lambda t: (t.priority, t.trigger_name.lower()))` produces a stable, deterministic sequence for any config.

---

### Decision 1.2 — Priority Numeric Range and Validation

**Business Situation:** `TriggerConfig.priority` is typed as `int` but its valid range is not specified. The remediation documents do not state whether priority=0 is valid, whether lower numbers mean higher or lower priority, or whether two triggers at the same priority in a multi-trigger conflict is an error or a normal state.

**Recommended Behavior:** Priority is a positive integer (≥ 1). Lower number = higher priority. Priority=1 is the highest. Same-priority across multiple triggers is permitted (resolved by Decision 1.1). Priority=0 is rejected at config load time.

**Alternative Behaviors Considered:**
- A: Priority 0–100 range, higher number = higher priority (inverted convention). Familiar to some frameworks but inconsistent with the existing codebase which uses priority=1 as the top tier.
- B: Priority as an enum (HIGH/MEDIUM/LOW). Limits flexibility to three bands.

**Recommended Decision:** `priority: int` must satisfy `priority >= 1`. `TriggerConfig.__post_init__` must raise `ValueError` if `priority < 1`. Lower value = higher priority. This matches current implicit behavior and requires only a guard clause addition.

**Impacted Components:**
- `models/trigger_config.py` — add `__post_init__` guard: `if self.priority < 1: raise ValueError`
- `utils/schema_validator.py` — config validation step (if config is validated from JSON)

**Acceptance Criteria:**
1. `TriggerConfig(trigger_name="T", priority=0, ...)` raises `ValueError`.
2. `TriggerConfig(trigger_name="T", priority=1, ...)` succeeds.
3. Two triggers with priority=1 coexist without error; tie-breaking per Decision 1.1 applies.

---

## SECTION 2 — TRIGGER CONFLICT RESOLUTION

### Decision 2.1 — User Eligible Under Two Triggers With Different Journeys

**Business Situation:** When a user appears in the trigger file under both Trigger_A (which has a custom 3-ad journey) and Trigger_B (which uses the campaign-level 2-ad journey), and Trigger_A has higher priority (lower number), the current architecture does not specify whether the user receives one journey (Trigger_A's) or two independent journeys (one per trigger).

**Recommended Behavior:** A user participates in exactly ONE journey at a time. When a user appears under multiple triggers, the highest-priority trigger (per Decision 1.1) governs. The lower-priority trigger entries for that user are discarded for this simulation run.

**Alternative Behaviors Considered:**
- A: User runs both journeys simultaneously (parallel journeys). Doubles event volume for that user, complicates TCC accounting (which trigger's capacity does each event consume?), and has no precedent in the current data model.
- B: User runs the higher-priority journey first; lower-priority journey queues and begins after the first journey completes. Requires a journey queue on UserState — significant data model expansion not included in the current remediation scope.
- C: User runs the trigger whose `Trigger_Date` is most recent (recency wins over priority). Ignores the intentional priority configuration.

**Pros:** Single-journey enforcement is the simplest model consistent with the existing `UserState` design (one `current_ad`, one `journey_status`, one `cooling_period_end`). It avoids TCC ambiguity entirely. It respects operator intent (priority exists specifically to express this preference).

**Cons:** A user who legitimately qualifies for two distinct promotional tracks only receives one. The operator must be aware that priority configuration is binding when overlapping audiences are possible.

**Recommended Decision:** When a user appears in the trigger file under multiple triggers, the trigger with the lowest `priority` number (and alphabetic tie-break per Decision 1.1) governs. All other trigger entries for that user are removed from the trigger DataFrame before Stage 1 processing. This deduplication step must occur in `UserStateManager.initialize_user_states()` or as a pre-processing step in the orchestrator. The user's `trigger_name` field is set to the winning trigger.

**Impacted Components:**
- `core/simulation_orchestrator.py` — add pre-Stage 1 multi-trigger deduplication step
- `core/user_state_manager.py` — document single-journey contract in docstring
- `utils/canonical_schema.py` — no change; existing trigger_name field handles this
- `tests/test_e2e/test_multitrigger_certification.py` — add conflict-resolution test class

**Acceptance Criteria:**
1. A trigger file with User_ID=U1 under Trigger_A (priority=1) and Trigger_B (priority=2) produces `trigger_name="Trigger_A"` for U1 in all output DataFrames.
2. Events_df for U1 contains only ads from Trigger_A's journey.
3. Trigger_B's TCC capacity is NOT reduced by U1 (U1 never counted against Trigger_B's `historically_engaged` or `remaining_capacity`).
4. The deduplication step logs a WARNING with the count of users resolved away from lower-priority triggers.

---

### Decision 2.2 — Trigger Conflict When Priorities Are Equal

**Business Situation:** When a user appears under two triggers with identical priority values, Decision 1.1 resolves tie-breaking alphabetically. But should the operator be warned that this situation exists?

**Recommended Behavior:** Yes — emit a WARN-level log when any user is found under multiple triggers at the same priority level. The alphabetic rule still resolves it deterministically, but the operator should know the configuration is ambiguous.

**Recommended Decision:** After trigger deduplication, if any user had their winning trigger determined by alphabetic tie-break (i.e., there were two or more equal-priority triggers for that user), emit a `logger.warning()` with: the count of users affected, the trigger names involved, and a recommendation to assign different priority values.

**Impacted Components:**
- `core/simulation_orchestrator.py` — deduplication step logs warning

**Acceptance Criteria:**
1. Given User_ID=U1 under Trigger_Apple (priority=1) and Trigger_Zebra (priority=1), the simulation emits a WARNING referencing Trigger_Apple and Trigger_Zebra.
2. Simulation still completes successfully; U1 assigned to Trigger_Apple.

---

## SECTION 3 — MULTI-TRIGGER MEMBERSHIP

### Decision 3.1 — User in Trigger File Multiple Times Under Same Trigger

**Business Situation:** The trigger file deduplication rule in `input_loader.load_historical_file()` (C-005) applies to the historical file. The trigger file deduplication behavior is not fully specified. A user could appear in the trigger file twice under the same trigger (e.g., two rows with User_ID=U1, Trigger_Name="T_A") due to upstream CRM export errors.

**Recommended Behavior:** Within the same trigger, deduplicate by `(User_ID, Trigger_Name)` keeping the row with the most recent `Trigger_Date`. If `Trigger_Date` values are identical, keep the first occurrence (row-order stable).

**Alternative Behaviors Considered:**
- A: Raise a validation error — no duplicates permitted. Too strict; CRM exports commonly contain duplicates.
- B: Keep all rows and process the user twice. Would double-count the user in TCC capacity and produce duplicate state rows.
- C: Deduplicate by keeping the first occurrence regardless of Trigger_Date. Ignores more recent trigger data.

**Recommended Decision:** `load_trigger_file()` (or the pre-Stage 1 deduplication step in the orchestrator) must deduplicate trigger rows on `(User_ID, Trigger_Name)` keeping the most-recent `Trigger_Date` row. Emit an INFO log with the count of duplicate rows dropped. This deduplication is separate from the multi-trigger conflict resolution in Decision 2.1 — that resolves across triggers; this resolves within the same trigger.

**Impacted Components:**
- `core/input_loader.py` — `load_trigger_file()` deduplication
- `core/simulation_orchestrator.py` — or delegated to input_loader

**Acceptance Criteria:**
1. A trigger file with User_ID=U1 under Trigger_A twice (Trigger_Date=D1 and Trigger_Date=D2, D2 > D1) produces one row in the pipeline with Trigger_Date=D2.
2. INFO log emitted: "N duplicate trigger rows dropped (same User_ID + Trigger_Name)."
3. TCC capacity for Trigger_A is not inflated by the duplicate row.

---

### Decision 3.2 — Distribution_Pct Sum Validation

**Business Situation:** `TriggerConfig.distribution_pct` is documented as the fraction of campaign-level users allocated to this trigger. The remediation documents do not specify whether the sum across all triggers must equal 1.0, or whether it is purely informational.

**Recommended Behavior:** `distribution_pct` values are informational only and do not gate audience resolution. The actual audience for each trigger is determined by which users appear in the trigger file under that trigger's name — not by the distribution percentage. A soft WARNING is emitted if the sum of `distribution_pct` values across all triggers deviates from 1.0 by more than 0.01, but this does not halt the simulation.

**Recommended Decision:** `distribution_pct` is advisory. No hard validation against sum=1.0. Emit a WARNING if sum deviates from 1.0 by more than 1%. Document this in `TriggerConfig.distribution_pct` docstring.

**Impacted Components:**
- `models/config_registry.py` — `__post_init__` soft validation
- `models/trigger_config.py` — docstring

**Acceptance Criteria:**
1. Config with three triggers at distribution_pct=[0.4, 0.4, 0.4] (sum=1.2) logs a WARNING but simulation proceeds.
2. Config with distribution_pct=[0.3, 0.3, 0.4] (sum=1.0) logs no warning.

---

## SECTION 4 — JOURNEY INTERRUPTIONS

### Decision 4.1 — Active User Receives a New Trigger Entry in the Same Run

**Business Situation:** A user is ACTIVE (mid-journey, currently on Ad_2 of a 3-ad journey for Trigger_A). The same simulation run's trigger file contains an entry for this user under Trigger_A again (either a duplicate or a new trigger event for the same trigger). Should the journey restart from Ad_1, continue from Ad_2, or should the new trigger entry be ignored?

**Recommended Behavior:** If the user is ACTIVE under the same trigger, the new trigger entry is ignored. The in-progress journey continues from its current position. Restarting mid-journey would destroy accumulated journey data and generate incorrect historical records.

**Alternative Behaviors Considered:**
- A: Restart journey from Ad_1 — simulates the operator sending a "fresh" engagement cycle. This loses journey state and creates causality gaps (user on Ad_1 with no preceding completion of prior journey).
- B: Advance to the next journey by queuing — requires journey queuing infrastructure not in scope.

**Recommended Decision:** For a user with `journey_status=ACTIVE` and the same `trigger_name` as the new trigger entry, the new trigger entry is silently discarded during the multi-trigger deduplication step (Decision 3.1). The user's existing ACTIVE journey is preserved. This applies within a single simulation run.

**Impacted Components:**
- `core/simulation_orchestrator.py` — pre-Stage 1 deduplication logic
- `core/user_state_manager.py` — `initialize_user_states()` merge contract: ACTIVE prior state wins over NEW trigger entry

**Acceptance Criteria:**
1. User U1 is ACTIVE on Ad_2 (from `previous_state_df`). Trigger file also contains U1 under the same trigger. After initialization, U1 remains ACTIVE on Ad_2 with unchanged `days_in_ad`.
2. No duplicate state row is created for U1.
3. U1 is not reset to `journey_status=NOT_STARTED`.

---

### Decision 4.2 — Active User Receives a New Trigger Entry for a Different Trigger

**Business Situation:** A user is ACTIVE on Trigger_A's journey (on Ad_A2). The current simulation's trigger file contains an entry for this user under Trigger_B (which has different ads). Should Trigger_B interrupt the Trigger_A journey?

**Recommended Behavior:** Trigger_B does NOT interrupt the active Trigger_A journey. The user is currently mid-journey for Trigger_A. Multi-trigger conflict resolution (Decision 2.1) applies: the higher-priority trigger wins. If Trigger_A has higher priority than Trigger_B, the Trigger_B entry is discarded. If Trigger_B has higher priority than Trigger_A, the following sub-rule applies.

**Sub-Rule — Higher-Priority Trigger Arrival for Active User:**

If the NEW trigger (from the current trigger file) has a HIGHER priority than the trigger governing the user's ACTIVE journey (from `previous_state_df` or `reconstructed_state_df`), the new higher-priority trigger takes over. The existing journey is DROPPED (`journey_status=DROPPED`). The user begins the new trigger's journey from Ad_1.

If the existing journey's trigger has EQUAL or HIGHER priority than the new trigger, the new trigger entry is discarded.

**Recommended Decision:**
- Higher-priority new trigger arriving for an ACTIVE user → DROPS current journey; starts new trigger journey from Ad_1.
- Equal or lower-priority new trigger arriving for an ACTIVE user → new trigger discarded; current journey continues.
- When a journey is DROPPED, `journey_status=DROPPED` is written, `journey_completion_date=None`, `cooling_period_end=None`. DROPPED users do NOT enter a cooling period. They are eligible for future re-triggering under the same or any trigger.

**Impacted Components:**
- `core/simulation_orchestrator.py` — pre-Stage 1 deduplication with priority comparison
- `core/user_state_manager.py` — DROPPED status handling in `initialize_user_states()`
- `models/enums.py` — `JourneyStatus.DROPPED` already exists; add to docstring

**Acceptance Criteria:**
1. User ACTIVE on Trigger_A (priority=2, Ad_2). Trigger file contains entry for Trigger_B (priority=1). User is assigned Trigger_B; `journey_status=DROPPED` is written for the Trigger_A state; user begins new journey on Trigger_B's Ad_1.
2. User ACTIVE on Trigger_A (priority=1, Ad_2). Trigger file contains entry for Trigger_B (priority=2). Trigger_B entry discarded; user continues on Trigger_A's Ad_2.
3. DROPPED users have `cooling_period_end=None` and `journey_completion_date=None`.

---

## SECTION 5 — JOURNEY CONTINUATION RULES

### Decision 5.1 — Move-on-Click vs Duration — Which Ad-Level Setting Governs?

**Business Situation:** `AdConfig.move_on_click: bool` is set per ad, not per journey. A journey could have Ad_1 with `move_on_click=True` and Ad_2 with `move_on_click=False`. The JourneyEngine advance logic handles each ad independently. The remediation documents confirm this behavior but do not explicitly state it as a business rule.

**Recommended Behavior:** `move_on_click` is evaluated independently per ad. A user on Ad_1 (click-gated) must click to advance to Ad_2. A user on Ad_2 (duration-based) advances automatically after `duration_days` regardless of click behavior. Mixed journeys are intentional and supported.

**Recommended Decision:** This is an existing behavior confirmed as correct. The `JourneyEngine._advance_active()` per-ad lookup is correct. No change needed. Document explicitly in `AdConfig.move_on_click` docstring: "Evaluated per-ad. When True, this ad requires a click event to advance. When False, advancement occurs after duration_days. A journey may mix click-gated and duration-based ads."

**Impacted Components:**
- `models/ad_config.py` — docstring clarification only
- `core/journey_engine.py` — existing behavior confirmed correct; no code change needed

**Acceptance Criteria:**
1. Journey: Ad_1 (`move_on_click=True`, duration=7), Ad_2 (`move_on_click=False`, duration=5). User clicks Ad_1 on Day 3 → advances to Ad_2. User does NOT click Ad_2 → automatically advances to completion after 5 days on Ad_2.
2. User on Ad_1 (`move_on_click=True`) who does NOT click is still on Ad_1 after 7 days.

---

### Decision 5.2 — Journey Advance When User Has Both Click and Duration Eligibility

**Business Situation:** A user is on Ad_1 with `move_on_click=True` and `duration_days=7`. They click on Day 3 (click advance condition met) but have also been on the ad for exactly 7 days (duration condition also met on the same day). The remediation document BIZ-018 states: "when `move_on_click=True`, advancement is exclusive to click events." But what is the behavior on the day the user both clicks AND has duration expired?

**Recommended Behavior:** Click-advance and duration-advance are mutually exclusive per the BIZ-018 rule. When `move_on_click=True`, duration elapsed NEVER triggers advance — only a click does. If both conditions are simultaneously true (click received on day = duration threshold), the click triggers the advance (the duration condition is irrelevant). Outcome is identical: user advances. The rule is about mechanism, not timing conflict.

**Recommended Decision:** When `move_on_click=True`, the ONLY valid advance mechanism is `ad_click_received=True`. Duration elapsed is ignored for click-gated ads. There is no conflict to resolve — duration is simply not evaluated. Implementation must not check `days_in_ad >= duration_days` for click-gated ads.

**Impacted Components:**
- `core/journey_engine.py` — `_advance_active()` guard: when `move_on_click=True`, skip duration check entirely

**Acceptance Criteria:**
1. User on Ad_1 (`move_on_click=True`, duration=7), `days_in_ad=7`, `ad_click_received=False` → user does NOT advance.
2. User on Ad_1 (`move_on_click=True`, duration=7), `days_in_ad=3`, `ad_click_received=True` → user advances.
3. User on Ad_1 (`move_on_click=True`, duration=7), `days_in_ad=7`, `ad_click_received=True` → user advances (same outcome as case 2).

---

### Decision 5.3 — DROPPED Journey Re-Entry Rules

**Business Situation:** `JourneyStatus.DROPPED` exists in the enum but the remediation documents do not specify: (a) whether DROPPED users enter a cooling period, (b) whether DROPPED users are eligible for re-entry under `allow_reentry`, or (c) whether DROPPED users can be re-triggered by a future trigger file entry.

**Recommended Behavior:** DROPPED is not a completion. DROPPED users did not finish a journey; they were interrupted. They do NOT enter a cooling period. They are immediately eligible for re-triggering by any future trigger file entry — including entries in the same simulation run if they are re-triggered via a higher-priority trigger (Decision 4.2). `allow_reentry` does not apply to DROPPED users; `allow_reentry` governs only users with `journey_status=COMPLETED`. DROPPED users are treated as NEW arrivals for their next journey.

**Alternative Behaviors Considered:**
- A: DROPPED users enter a cooling period of half the normal duration. Penalizes users for an interruption they did not choose.
- B: DROPPED users can never re-enter (EXCLUDED forever). Too punitive; no business justification.

**Recommended Decision:** DROPPED journey → no cooling period → eligible for re-triggering immediately. On re-entry: `eligibility_status=NEW`, `journey_status=NOT_STARTED`, `current_ad=None`, `days_in_ad=None`. `allow_reentry` flag is irrelevant to DROPPED users; they are treated as fresh entries. This must be explicit in `AudienceManager.resolve()`.

**Impacted Components:**
- `core/audience_manager.py` — `resolve()` must treat `journey_status=DROPPED` as re-eligible (same as NEW)
- `core/user_state_manager.py` — `initialize_user_states()` must reset DROPPED users who re-appear in trigger file
- `models/enums.py` — docstring for `JourneyStatus.DROPPED`

**Acceptance Criteria:**
1. User with `journey_status=DROPPED` who appears in the next trigger file is assigned `eligibility_status=NEW` and `journey_status=NOT_STARTED`.
2. DROPPED user is NOT blocked by `allow_reentry=False` setting.
3. DROPPED user has no `cooling_period_end`.

---

## SECTION 6 — HISTORICAL AUDIENCE CONTINUATION

### Decision 6.1 — Historically-Active User Also in Current Trigger File Under Different Trigger

**Business Situation:** `HistoricalStateReconstructor` reconstructs User_ID=U1 as ACTIVE on Trigger_A's journey (Ad_2, step 2). The current trigger file also contains U1 under Trigger_B (a different trigger). Which governs: the reconstructed historical position (Trigger_A, Ad_2) or the new trigger entry (Trigger_B, Ad_1)?

**Recommended Behavior:** The three-way merge priority from USR-001 applies: `previous_state_df > reconstructed_state_df > UserState.new()`. However, `reconstructed_state_df` is equivalent to a prior run's state for priority purposes when no `previous_state_df` exists. The new trigger file entry is the "New" tier. Therefore: reconstructed ACTIVE state (Trigger_A, Ad_2) wins over the new trigger file entry (Trigger_B, Ad_1).

But: if the new trigger (Trigger_B) has HIGHER priority than the trigger governing the reconstructed journey (Trigger_A), Decision 4.2 applies — the higher-priority new trigger interrupts and DROPS the reconstructed journey.

**Recommended Decision:** Apply the same interrupt logic as Decision 4.2 to historically-reconstructed ACTIVE users. Reconstructed state is treated as equivalent to a prior-run active journey. Higher-priority new trigger → DROPS reconstructed journey, starts fresh on new trigger. Equal or lower-priority new trigger → new trigger entry discarded, reconstructed journey continues. The priority comparison is: `new_trigger.priority` vs `config.get_trigger_by_name(reconstructed_trigger_name).priority`.

**Impacted Components:**
- `core/simulation_orchestrator.py` — pre-Stage 1: apply interrupt logic to reconstructed active users
- `core/user_state_manager.py` — three-way merge must pass trigger priority context

**Acceptance Criteria:**
1. Reconstructed user on Trigger_A (priority=2), new trigger file entry for Trigger_B (priority=1) → user assigned Trigger_B, reconstructed journey DROPPED.
2. Reconstructed user on Trigger_A (priority=1), new trigger file entry for Trigger_B (priority=2) → Trigger_B discarded, user continues on Trigger_A's Ad_2.

---

### Decision 6.2 — Historically-Active User NOT in Current Trigger File

**Business Situation:** `HistoricalStateReconstructor` finds U1 ACTIVE on Ad_2. U1 is NOT in the current trigger file at all. CRIT-003 specifies that historically-active users not in the trigger file must be injected into the audience via `_augment_trigger_df()`. But: what `Trigger_Date` is assigned to the synthetic trigger row? And what `Segment` is used?

**Recommended Behavior:** Synthetic trigger rows use `Trigger_Date = simulation_start_date` (the first date of the current simulation run). `Segment` is populated from the reconstructed state's `segment` field if present; otherwise `"Historical"`. `_synthetic_historical = True` flag is set on the row (already specified in HPR-001).

**Recommended Decision:** Synthetic trigger rows have: `Trigger_Date = simulation_start_date`, `Segment = reconstructed_state.segment or "Historical"`, `Trigger_Name = reconstructed_state.trigger_name or "Historical"`, `Campaign_ID = config.campaign_id`. The `_synthetic_historical` column is internal only and must be stripped before the trigger_df reaches the schema validator.

**Impacted Components:**
- `core/simulation_orchestrator.py` — `_augment_trigger_df()` helper
- `core/input_loader.py` — strip `_synthetic_historical` column before validation

**Acceptance Criteria:**
1. Synthetic rows have `Trigger_Date` equal to `simulation_start_date` (not today's date, not the historical engagement date).
2. `_synthetic_historical` column is absent from the trigger_df when it reaches `schema_validator.validate_trigger_file()`.
3. Historically-injected users produce events on their reconstructed `current_ad` (not on Ad_1).

---

## SECTION 7 — COOLING PERIOD RE-ENTRY

### Decision 7.1 — Cooling Period Expiry Boundary Condition (Same Day)

**Business Situation:** A user's `cooling_period_end = D`. The simulation starts on day D. Is D the last day of cooling (user still COOLING) or the first day of re-entry (user is RE_ENTRY on day D)?

**Recommended Behavior:** `cooling_period_end` is the exclusive boundary. A user with `cooling_period_end = D` and `simulation_start = D` is eligible for RE_ENTRY. The cooling period is "expired" at the start of day D. The condition is `as_of_date >= cooling_period_end` (not strictly greater than).

**Alternative Behaviors Considered:**
- A: `as_of_date > cooling_period_end` (strictly greater). Means user must wait one additional day. This creates off-by-one errors in campaigns where cooling is scheduled to end on a specific date.

**Recommended Decision:** `eligibility_status = RE_ENTRY` when `as_of_date >= cooling_period_end`. The condition in `AudienceManager.resolve()` and `HistoricalStateReconstructor.reconstruct()` must use `>=` (greater than or equal). This is the "cooling ends at the START of the day" model.

**Impacted Components:**
- `core/audience_manager.py` — cooling comparison operator
- `core/historical_state_reconstructor.py` — same comparison operator

**Acceptance Criteria:**
1. User with `cooling_period_end = date(2026, 7, 1)`, simulation starts `date(2026, 7, 1)` → `eligibility_status=RE_ENTRY`.
2. User with `cooling_period_end = date(2026, 7, 1)`, simulation starts `date(2026, 6, 30)` → `eligibility_status=COOLING`.

---

### Decision 7.2 — Allow_Reentry=False When Cooling Has Expired

**Business Situation:** `allow_reentry=False` is the global campaign setting that prevents re-entry after journey completion. If `allow_reentry=False` and a user's cooling period has expired (`cooling_period_end <= simulation_start`), should the user be `EXCLUDED` or `COOLING`?

**Recommended Behavior:** When `allow_reentry=False`, users who have COMPLETED a journey are EXCLUDED — permanently. The cooling period is irrelevant because re-entry is never permitted. The system should not show them as COOLING (which implies eventual eligibility) when they will never re-enter.

**Recommended Decision:** `allow_reentry=False` → completed users are assigned `eligibility_status=EXCLUDED` immediately, regardless of `cooling_period_end`. The `cooling_period_end` field is still computed and stored (for audit/reporting) but does not affect eligibility. `AudienceManager.resolve()` must evaluate `allow_reentry` BEFORE evaluating cooling period expiry.

Logic order:
1. If `journey_status=COMPLETED` AND `allow_reentry=False` → `EXCLUDED`.
2. If `journey_status=COMPLETED` AND `allow_reentry=True` AND `cooling_period_end > sim_start` → `COOLING`.
3. If `journey_status=COMPLETED` AND `allow_reentry=True` AND `cooling_period_end <= sim_start` → `RE_ENTRY`.

**Impacted Components:**
- `core/audience_manager.py` — eligibility resolution order
- `core/historical_state_reconstructor.py` — same logic when reconstructing completed users

**Acceptance Criteria:**
1. User with `journey_status=COMPLETED`, `cooling_period_end=yesterday`, `allow_reentry=False` → `eligibility_status=EXCLUDED`.
2. User with `journey_status=COMPLETED`, `cooling_period_end=yesterday`, `allow_reentry=True` → `eligibility_status=RE_ENTRY`.
3. User with `journey_status=COMPLETED`, `cooling_period_end=tomorrow`, `allow_reentry=True` → `eligibility_status=COOLING`.

---

## SECTION 8 — COOLING PERIOD OVERRIDE

### Decision 8.1 — Cooling Override When Allow_Reentry=False

**Business Situation:** The USR-001 document specifies that `cooling_override=True` bypasses the cooling period and forces COOLING users to RE_ENTRY. But it also states: "Requires 'Allow Re-entry' to also be enabled." When `cooling_override=True` AND `allow_reentry=False`, what is the behavior? USR-001 shows a warning in the UI but does not specify the exact system behavior — does the override silently fail, raise an error, or override the `allow_reentry` setting too?

**Recommended Behavior:** `cooling_override=True` with `allow_reentry=False` is a no-op at the system level. The UI shows a warning (already specified in USR-001). The `CoolingOverrideService` is not invoked when `allow_reentry=False`. The combination does NOT override `allow_reentry`.

**Rationale:** `cooling_override` means "skip the waiting period." `allow_reentry` means "re-entry is never permitted." A skip of zero duration produces zero re-entries. These two settings have different semantic scope — `allow_reentry` is a policy setting, `cooling_override` is an operational convenience. Policy takes precedence over operational convenience.

**Recommended Decision:** `CoolingOverrideService.apply()` must be preceded by a guard: `if not config.allow_reentry: return state_df (unchanged)`. The service is effectively a no-op when `allow_reentry=False`. The UI warning already informs the operator. No users are forced to RE_ENTRY. No error is raised.

**Impacted Components:**
- `core/cooling_override_service.py` — add `allow_reentry` guard as first line
- `core/simulation_orchestrator.py` — pass `config.allow_reentry` to `CoolingOverrideService`

**Acceptance Criteria:**
1. `CoolingOverrideService.apply(df, cooling_override=True)` with `allow_reentry=False` returns `df` unchanged (no rows modified).
2. `CoolingOverrideService.apply(df, cooling_override=True)` with `allow_reentry=True` forces COOLING users to RE_ENTRY.
3. No exception is raised for the `cooling_override=True, allow_reentry=False` combination.

---

### Decision 8.2 — Cooling Override Scope: All Triggers or Selected Triggers?

**Business Situation:** `cooling_override` is a single boolean in `ConfigRegistry`. When multiple triggers are in use, does the override apply to ALL triggers' cooling users, or only to a specific trigger's cooling users?

**Recommended Behavior:** `cooling_override` applies globally to all COOLING users in the run, across all triggers. There is no per-trigger cooling override setting.

**Rationale:** The UI toggle "Override Cooling Period (this run only)" is presented at the campaign run level, not at the trigger level. Adding per-trigger cooling override would require a new UI surface and data model change outside the current scope.

**Recommended Decision:** `CoolingOverrideService.apply()` operates on the entire `state_df` without trigger filtering. All COOLING + COMPLETED users across all triggers become RE_ENTRY when `cooling_override=True`. If per-trigger cooling override is required in the future, it must be scoped as a separate feature request.

**Impacted Components:**
- `core/cooling_override_service.py` — no trigger filter in the boolean mask

**Acceptance Criteria:**
1. With two triggers (T_A and T_B) and COOLING users in both, `cooling_override=True` forces RE_ENTRY for COOLING users under BOTH triggers.
2. `cooling_override_applied=True` is set for all forced users regardless of their `trigger_name`.

---

## SECTION 9 — JOURNEY COMPLETION HANDLING

### Decision 9.1 — What Constitutes a Journey Completion?

**Business Situation:** The architecture confirms that `JourneyEngine._complete_journeys()` sets `journey_status=COMPLETED`. But the precise business definition of completion is not stated: is it (a) the user advances PAST the final ad (i.e., clicks the last ad when `move_on_click=True`), (b) the user is ON the final ad and its duration expires (when `move_on_click=False`), or (c) the final ad produces any qualifying event?

**Recommended Behavior:** A journey is COMPLETE when one of the following is true for the user's current ad, and that ad is the FINAL ad in the sequence (no `_next_ad` successor):
- `move_on_click=True`: the user has received a click event on the final ad (ad_click_received=True on terminal ad).
- `move_on_click=False`: the user has been on the final ad for `duration_days` days.

Completion occurs at the END of the day that satisfies the condition, not the beginning of the next day.

**Recommended Decision:** Journey completion = terminal ad condition satisfied (click-received OR duration-elapsed, per that ad's `move_on_click` setting). `_complete_journeys()` fires at end-of-day during `JourneyEngine.advance()`. The `journey_completion_date` is set to the simulation date on which the condition is first satisfied. `cooling_period_end = journey_completion_date + timedelta(days=config.cooling_period_days)`.

**Impacted Components:**
- `core/journey_engine.py` — `_complete_journeys()` confirmation
- Documentation: `journey_completion_date` docstring

**Acceptance Criteria:**
1. User on terminal Ad_3 (`move_on_click=True`), receives click on Day 15 → `journey_status=COMPLETED`, `journey_completion_date=Day 15`.
2. User on terminal Ad_3 (`move_on_click=False`, duration=7), reaches Day 7 on Ad_3 → `journey_status=COMPLETED`, `journey_completion_date=Day 7 on Ad_3`.
3. `cooling_period_end = journey_completion_date + timedelta(days=cooling_period_days)`.

---

### Decision 9.2 — User Who Never Advances Past Ad_1 By Run End

**Business Situation:** A user starts a journey on Ad_1 (`move_on_click=True`) but never clicks during the entire simulation run. The simulation ends. What is the user's final `journey_status`?

**Recommended Behavior:** The user remains `journey_status=ACTIVE`. They are not DROPPED (no competing trigger forced a drop) and not COMPLETED (terminal ad condition not met). ACTIVE mid-journey users carry forward their state into the next run via `previous_state_df` (multi-run chain).

**Recommended Decision:** Simulation end does NOT automatically set `journey_status=DROPPED` for non-completing users. They remain ACTIVE with their last-known `current_ad`, `days_in_ad`, and `journey_step`. `finalize_state()` preserves the ACTIVE status. This is already the implicit behavior but must be explicit: no "end of simulation" drop logic should ever be added.

**Impacted Components:**
- `core/user_state_manager.py` — `finalize_state()` must not transition ACTIVE users to DROPPED
- `core/simulation_orchestrator.py` — documentation in the `finalize_state` step

**Acceptance Criteria:**
1. User with `journey_status=ACTIVE` at the start of Day 1 who never clicks and reaches end of simulation has `journey_status=ACTIVE` in `final_state_df`.
2. The same user's `current_ad`, `days_in_ad`, and `journey_step` are preserved in `final_state_df`.
3. The user is not penalized with EXCLUDED or DROPPED status.

---

## SECTION 10 — WEEKLY SIMULATION CARRY-FORWARD RULES

### Decision 10.1 — Weekly Counter Reset in Multi-Run Chains

**Business Situation:** `UserState` has `weekly_impressions`, `weekly_clicks`, `weekly_opens`, `weekly_engagements`. `BehaviorEngine` resets these on ISO Monday. When Run_1 ends on Wednesday and Run_2 starts the following Monday, the carry-forward `previous_state_df` contains the mid-week counter values from Run_1. Should Run_2 honor these mid-week values (and reset them on the first Monday of Run_2) or reset them immediately at Run_2 startup?

**Recommended Behavior:** The ISO Monday reset logic already handles this correctly. `BehaviorEngine` resets weekly counters when `simulation_date.weekday() == 0` (Monday). If Run_2 starts on Monday, the counters are reset on Day 1 of Run_2. If Run_2 starts on Tuesday (mid-week), the carried-over counters from Run_1 are valid for the remainder of that week and reset on the next Monday. This is the correct behavior — weekly limits are calendar-week limits, not per-run limits.

**Recommended Decision:** No change to the weekly counter reset logic. `previous_state_df` carries weekly counters as-is. `BehaviorEngine` resets them on the first Monday encountered in Run_2's date range, regardless of when Run_1 ended. Document this explicitly: "weekly counters are calendar-week scoped, not simulation-run scoped."

**Impacted Components:**
- `core/behavior_engine.py` — docstring for weekly counter reset
- `core/user_state_manager.py` — `finalize_state()` docstring: "weekly counters carry forward; reset occurs at next calendar Monday"

**Acceptance Criteria:**
1. Run_1 ends Wednesday (weekly_clicks=3 for user U1). Run_2 starts Thursday. On Thursday, U1's weekly_clicks starts at 3 (carried over). On the following Monday, U1's weekly_clicks resets to 0.
2. Run_1 ends Wednesday (weekly_clicks=3). Run_2 starts the following Monday. On Monday (Day 1 of Run_2), U1's weekly_clicks is 0 (reset).

---

### Decision 10.2 — Daily Frequency Cap Carry-Forward

**Business Situation:** `DEFAULT_FREQUENCY_MAX=30` is a monthly/period cap (not daily). Is there a daily impression cap? If so, does it carry forward between runs?

**Recommended Behavior:** The frequency cap (`DEFAULT_FREQUENCY_MAX`) is a WEEKLY cap — the maximum number of impressions a user can receive in a single calendar week. It applies to `weekly_impressions`. There is no daily cap. Weekly counters carry forward as per Decision 10.1.

**Recommended Decision:** Confirm `DEFAULT_FREQUENCY_MAX` governs `weekly_impressions` only. No daily cap exists. Document in `utils/constants.py` docstring: "DEFAULT_FREQUENCY_MAX: int — maximum impressions per user per calendar week."

**Impacted Components:**
- `utils/constants.py` — docstring clarification
- `core/behavior_engine.py` — comment confirming weekly (not daily or monthly) scope

**Acceptance Criteria:**
1. A user with `weekly_impressions = DEFAULT_FREQUENCY_MAX - 1` does not receive an impression on Day N.
2. A user with `weekly_impressions = DEFAULT_FREQUENCY_MAX` does not receive an impression.
3. On the following Monday, `weekly_impressions` resets to 0 and the user is eligible for impressions again.

---

## SECTION 11 — HISTORICAL COMPLETION LIFECYCLE

### Decision 11.1 — User Completed Journey Historically and Appears in Current Trigger File for Same Trigger

**Business Situation:** Historical data shows User_ID=U1 completed a journey for Trigger_A on date D (with Completion_Date in the extended schema). Cooling has expired. The current trigger file also contains U1 under Trigger_A. Should U1 enter as `RE_ENTRY` (honoring historical completion) or as `NEW` (ignoring history because they appear fresh in the trigger file)?

**Recommended Behavior:** U1 enters as `RE_ENTRY`. The historical completion is real data. Ignoring it would cause the user to be treated as if they had never engaged, which misrepresents their actual journey history and corrupts TCC accounting (they would not count against the `historically_engaged` floor).

**Recommended Decision:** `HistoricalStateReconstructor.reconstruct()` produces a row for U1 with `eligibility_status=RE_ENTRY` (cooling expired). The three-way merge priority (Decision 2.1 of USR-001): `previous_state_df > reconstructed_state_df > UserState.new()`. If U1 is absent from `previous_state_df`, the reconstructed RE_ENTRY state is used. U1 starts the simulation as RE_ENTRY and journeys from Ad_1 again under Trigger_A.

**Impacted Components:**
- `core/historical_state_reconstructor.py` — produces RE_ENTRY status for cooling-expired completions
- `core/audience_manager.py` — RE_ENTRY users follow the re-entry path in `resolve()`

**Acceptance Criteria:**
1. Historical file contains U1 with `Completion_Date=D`, `cooling_period_days=14`, `as_of_date=D+20`. U1 is reconstructed as `eligibility_status=RE_ENTRY`.
2. U1 starts the simulation at Ad_1 (first ad of the trigger's journey), `days_in_ad=0`.
3. U1's `historical_engaged=True` is preserved (reduces TCC capacity for this trigger).

---

### Decision 11.2 — User Completed Journey Historically and Appears Under a DIFFERENT Trigger

**Business Situation:** U1 completed a journey for Trigger_A historically. Cooling has expired. The current trigger file contains U1 under Trigger_B (different trigger, different ad journey). Should U1's historical completion under Trigger_A affect their eligibility or TCC under Trigger_B?

**Recommended Behavior:** Historical completion under Trigger_A does NOT affect eligibility under Trigger_B. Trigger_B's journey is independent. U1 enters Trigger_B's journey as `NEW` (no prior history with Trigger_B). U1's `historical_engaged=True` flag should ONLY reduce TCC for Trigger_A (the trigger they historically engaged with), not for Trigger_B.

**Recommended Decision:** TCC capacity accounting in `_init_capacity_tracker()` must count historically engaged users per-trigger. User U1 with historical engagement on Trigger_A reduces Trigger_A's `remaining_capacity` but not Trigger_B's. The `historical_df` filter for TCC counting must be scoped by `Trigger_Name` when the extended schema is present. When the extended schema is absent (4-column), historical engagement is attributed globally (current behavior preserved).

**Impacted Components:**
- `core/engagement_generator.py` — `_init_capacity_tracker()` per-trigger historical count
- `core/audience_manager.py` — same scoping for `compute_remaining_capacity()`

**Acceptance Criteria:**
1. U1 historically engaged with Trigger_A. U1 enters Trigger_B. Trigger_B's `remaining_capacity` is NOT reduced by U1's history.
2. Trigger_A's `remaining_capacity` IS reduced by U1's history (if Trigger_A is also in the current run).
3. When historical file is 4-column (no Trigger_Name), historical engagement reduces all-trigger capacity as before.

---

### Decision 11.3 — Multiple Historical Journeys for the Same User

**Business Situation:** Historical data shows User_ID=U1 completed Trigger_A's journey twice (two distinct `Completion_Date` values in the extended schema). `HistoricalStateReconstructor` sees multiple completions. Which one is used?

**Recommended Behavior:** The MOST RECENT completion is used. Only the last journey matters for current state reconstruction. The user's `cooling_period_end` is calculated from the most recent `Completion_Date`.

**Recommended Decision:** `HistoricalStateReconstructor.reconstruct()` uses `completed_rows[EXTERNAL_COMPLETION_DATE].max()` to find the most recent completion. All earlier completions are ignored for state reconstruction purposes. This is already implied by the `max()` call in the HPR-001 algorithm.

**Impacted Components:**
- `core/historical_state_reconstructor.py` — `completed.sort_values("Completion_Date", ascending=False).iloc[0]` already handles this

**Acceptance Criteria:**
1. U1 has Completion_Date rows for D_1 and D_2 (D_2 > D_1). Reconstructed state uses `cooling_period_end = D_2 + timedelta(cooling_period_days)`.
2. D_1 completion is ignored for state reconstruction.

---

## SECTION 12 — RE-TRIGGERING SCENARIOS

### Decision 12.1 — Same Trigger Re-Entry After Natural Cooling Expiry

**Business Situation:** When a user's cooling period expires naturally (no override), and `allow_reentry=True`, and they appear in the trigger file again under the same trigger — do they start at Ad_1 or do they resume from where they left off (i.e., the first ad of the journey but with enriched engagement score)?

**Recommended Behavior:** RE_ENTRY users ALWAYS start from Ad_1 of the relevant trigger's journey. There is no resumption of a prior journey position. The prior journey was COMPLETED. Re-entry is a fresh journey under the same trigger.

**Rationale:** The user completed their prior journey. Their prior engagement history is preserved in their behavioral profile (engagement_score, creative_affinities) which carries forward via `previous_state_df`. But journey position resets. Starting from a mid-journey position on re-entry would imply the user was never gone — which is factually incorrect.

**Recommended Decision:** On RE_ENTRY: `current_ad = first_ad_of_trigger_journey`, `days_in_ad = 0`, `journey_step = 1`, `ad_click_received = False`, `journey_status = ACTIVE`. All behavioral scores (engagement_score, affinities) are PRESERVED from prior state. `journey_start_date = simulation_start_date`. `journey_completion_date = None`. This is handled by `JourneyEngine._start_journeys()` processing `RE_ENTRY` status users.

**Impacted Components:**
- `core/journey_engine.py` — `_JOURNEY_START_STATUSES = {NEW, RE_ENTRY}` already handles this; confirm Ad_1 placement
- `models/user_state.py` — docstring for RE_ENTRY processing

**Acceptance Criteria:**
1. User in RE_ENTRY at simulation start: after Day 1 JourneyEngine advance, `current_ad = first_ad`, `days_in_ad = 0 or 1`, `journey_step = 1`, `journey_status = ACTIVE`.
2. User's `engagement_score` from previous run is preserved (not reset to 0.5).
3. User's `creative_affinities` from previous run are preserved.

---

### Decision 12.2 — Re-Entry Journey Uses Which Ad Sequence?

**Business Situation:** A user completed Trigger_A's journey in Run_1. In Run_2, Trigger_A's ad sequence has been changed (different ads). The user re-enters. Do they follow the OLD journey (from their prior run state) or the NEW journey (from the current config)?

**Recommended Behavior:** The user follows the CURRENT config's journey for their trigger. Journey configurations are not locked per user. The `trigger_ads_key` field detects this change — if the key differs between prior state and current config, the user starts the new journey from Ad_1 on re-entry.

**Recommended Decision:** On RE_ENTRY, always use the CURRENT `TriggerJourneyResolver.get_engine(trigger_name)` ads. Prior journey position is irrelevant because the journey was completed. `trigger_ads_key` is updated to reflect the new sequence fingerprint when the RE_ENTRY journey starts.

**Impacted Components:**
- `core/journey_engine.py` — `_start_journeys()` uses `self._first_ad` from current engine's ads
- `models/user_state.py` — `trigger_ads_key` updated at journey start

**Acceptance Criteria:**
1. Run_1 Trigger_A uses [Ad_A1, Ad_A2]. User completes. Run_2 Trigger_A uses [Ad_A1, Ad_A2, Ad_A3] (new ad added). Re-entering user starts on [Ad_A1] and follows the 3-ad sequence.
2. `trigger_ads_key` in `final_state_df` reflects the fingerprint of the 3-ad sequence, not the 2-ad sequence.

---

### Decision 12.3 — SKIPPED User Re-Triggering

**Business Situation:** A user is `eligibility_status=SKIPPED` in Run_1 because TCC capacity was exhausted (they were capacity-blocked). They appear in the trigger file again in Run_2. Are they treated as NEW or do they retain SKIPPED status?

**Recommended Behavior:** SKIPPED users are treated as NEW in subsequent runs. SKIPPED is a within-run capacity allocation result, not a persistent eligibility state. It has no cross-run meaning.

**Recommended Decision:** `AudienceManager.resolve()` evaluates `previous_state_df` users with `eligibility_status=SKIPPED` as if they were NEW arrivals (no prior journey state to preserve). Their behavioral profile (engagement_score, affinities) is preserved, but their journey fields are reset to NOT_STARTED. The `UserStateManager.initialize_user_states()` three-way merge must treat SKIPPED users from `previous_state_df` as equivalent to absent users (fall through to UserState.new() tier OR use reconstructed state if available).

**Impacted Components:**
- `core/user_state_manager.py` — SKIPPED users from `previous_state_df` are not treated as "prior run state wins"
- `core/audience_manager.py` — SKIPPED users re-evaluated fresh

**Acceptance Criteria:**
1. User with `eligibility_status=SKIPPED` in Run_1 `previous_state_df`, appearing in Run_2 trigger file → assigned `eligibility_status=NEW` and `journey_status=NOT_STARTED` in Run_2.
2. User's engagement_score from Run_1 is preserved in Run_2 (profile carries forward even when journey resets).

---

## SECTION 13 — EXISTING USER vs NEW USER PROCESSING

### Decision 13.1 — Existing User With No Prior Journey State (Prior EXCLUDED)

**Business Situation:** A user was EXCLUDED in Run_1 (completed journey, `allow_reentry=False`). In Run_2, `allow_reentry=True` is now set. The `previous_state_df` from Run_1 contains this user as EXCLUDED. Should the system honor the EXCLUDED status from prior state (never let them re-enter) or re-evaluate based on the current `allow_reentry` setting?

**Recommended Behavior:** `allow_reentry` is a CURRENT RUN configuration setting. Prior EXCLUDED status is not inherited. On each run, eligibility is re-evaluated from the current config. A user who was EXCLUDED under `allow_reentry=False` may become RE_ENTRY in a subsequent run where `allow_reentry=True` and their cooling period has expired.

**Rationale:** EXCLUDED is an eligibility decision made within a run based on that run's configuration. Persisting EXCLUDED status across runs would lock users out permanently even when the operator explicitly enables re-entry — which contradicts the intent of the `allow_reentry` toggle.

**Recommended Decision:** `AudienceManager.resolve()` must re-evaluate EXCLUDED users from `previous_state_df` by applying the CURRENT run's `allow_reentry` and cooling period logic. If `allow_reentry=True` and `cooling_period_end <= sim_start`, the previously-EXCLUDED user becomes RE_ENTRY. If `allow_reentry=False`, they remain EXCLUDED.

**Impacted Components:**
- `core/audience_manager.py` — `resolve()` must re-evaluate prior EXCLUDED users, not pass them through as EXCLUDED automatically

**Acceptance Criteria:**
1. User with `eligibility_status=EXCLUDED` in `previous_state_df`, current run `allow_reentry=True`, `cooling_period_end=yesterday` → becomes RE_ENTRY.
2. User with `eligibility_status=EXCLUDED` in `previous_state_df`, current run `allow_reentry=False` → remains EXCLUDED.

---

### Decision 13.2 — User in Previous State With journey_status=NOT_STARTED (Never Ran)

**Business Situation:** Run_1 initialized User U1 (from trigger file) but U1 was SKIPPED by TCC before their journey started. Final state: `journey_status=NOT_STARTED`, `eligibility_status=SKIPPED`. In Run_2, U1 appears in the trigger file again. The `previous_state_df` shows NOT_STARTED. Should Run_2 advance from NOT_STARTED (was queued) or reset to NEW?

**Recommended Behavior:** NOT_STARTED in `previous_state_df` with SKIPPED eligibility is treated as NEW. The user was never meaningfully in a journey. There is no journey position to preserve. Their behavioral profile is preserved.

Per Decision 12.3, SKIPPED users are treated as fresh arrivals. NOT_STARTED users are SKIPPED users by definition in this context (they were initialized but capacity-blocked).

**Recommended Decision:** Same as Decision 12.3. Users with `journey_status=NOT_STARTED` AND `eligibility_status=SKIPPED` in `previous_state_df` are treated as NEW in the subsequent run. Users with `journey_status=NOT_STARTED` AND `eligibility_status=NEW` (edge case: initialized but never processed) are also treated as NEW.

**Impacted Components:**
- `core/user_state_manager.py` — prior state merge: NOT_STARTED + SKIPPED → treated as new entry, not prior state carry-forward

**Acceptance Criteria:**
1. User with `journey_status=NOT_STARTED`, `eligibility_status=SKIPPED` in `previous_state_df` → Run_2 treats them as NEW, `days_in_ad=None`, journey resets.

---

## SECTION 14 — MULTI-RUN SIMULATION BEHAVIOR

### Decision 14.1 — Historical_df vs Previous_state_df When Both Are Present

**Business Situation:** In a multi-run chain, Run_2 has BOTH a `previous_state_df` (from Run_1's final state) AND a `historical_df` (the operator uploaded an 8-column historical file). The three-way merge rule says `previous_state_df` takes priority. But should `historical_df` inform users who are in `previous_state_df` at all? For example: a user in `previous_state_df` as ACTIVE on Ad_2, but the historical file shows a completion event after Run_1 ended — should the reconstructed COMPLETED state override the `previous_state_df` ACTIVE state?

**Recommended Behavior:** `previous_state_df` is the authoritative state for the multi-run chain. It is always preferred over reconstructed historical state. The historical file is a supplementary source for users NOT present in `previous_state_df`. If the historical file contains more recent information than `previous_state_df`, the operator should update `previous_state_df` manually or the historical file should not contradict a known state. The system does not attempt to reconcile conflicts between these two sources.

**Recommended Decision:** Three-way merge priority is absolute: `previous_state_df > reconstructed_state_df > UserState.new()`. If a user is in `previous_state_df`, their `previous_state_df` row is used verbatim — the historical file is NOT consulted for that user. Historical reconstruction is only used for users absent from `previous_state_df`.

**Impacted Components:**
- `core/user_state_manager.py` — three-way merge must exit early when user found in `previous_state_df`
- Documentation: this priority must be explicit in `initialize_user_states()` docstring

**Acceptance Criteria:**
1. User U1 in `previous_state_df` as ACTIVE on Ad_2 (Run_1 ended mid-journey). Historical file shows U1 with a Completion_Date 3 days ago. Run_2 treats U1 as ACTIVE on Ad_2 (previous_state_df wins). Historical completion is ignored.
2. User U2 NOT in `previous_state_df`. Historical file shows U2 as completed with cooling expired. Run_2 treats U2 as RE_ENTRY (reconstructed state used).

---

### Decision 14.2 — Same Campaign_ID vs Different Campaign_ID in Multi-Run Chain

**Business Situation:** `previous_state_df` always contains a `campaign_id` column. If Run_2 uses a different `campaign_id` than Run_1, should Run_2 accept Run_1's state as a valid chain link?

**Recommended Behavior:** `previous_state_df` rows with a `campaign_id` that does not match the current `ConfigRegistry.campaign_id` are silently excluded from the merge. They are treated as if they do not exist. The user begins fresh from `UserState.new()` (or reconstructed state if available).

**Rationale:** A different `campaign_id` means a different campaign. State from Campaign A should not bleed into Campaign B.

**Recommended Decision:** `UserStateManager.initialize_user_states()` must filter `previous_state_df` to rows where `campaign_id == config.campaign_id` before performing the three-way merge. Rows with mismatched `campaign_id` are discarded silently (no error; users simply become NEW).

**Impacted Components:**
- `core/user_state_manager.py` — filter `previous_state_df` by `campaign_id`

**Acceptance Criteria:**
1. `previous_state_df` contains rows for Campaign_A and Campaign_B. Run_2 uses Campaign_B config. Only Campaign_B rows participate in the merge. Campaign_A users are treated as NEW.

---

### Decision 14.3 — Ad Sequence Changed Between Runs in Multi-Run Chain

**Business Situation:** Run_1 uses Trigger_A with ads [Ad_1, Ad_2, Ad_3]. A user is ACTIVE on Ad_2 (`journey_step=2`). Between runs, the operator changes Trigger_A to use [Ad_1, Ad_X, Ad_2, Ad_3] (a new ad inserted). Run_2 starts. The user's `previous_state_df` shows `current_ad="Ad_2"`, `journey_step=2`. In the new sequence, Ad_2 is now step 3. What happens?

**Recommended Behavior:** The `trigger_ads_key` fingerprint is used to detect this. If the key in `previous_state_df` differs from the current config's key for that trigger, the user's journey position is reset to Ad_1 (`journey_step=1`, `days_in_ad=0`). The journey effectively restarts under the new ad sequence.

**Alternative Behaviors Considered:**
- A: Attempt to map old position to new sequence by ad_name lookup. "Ad_2" is still in the sequence; place user at Ad_2 in the new sequence (step 3). Complex logic; what if an ad was renamed?
- B: Raise an error when ad sequence changes between runs. Blocks all mid-journey users from continuing — too disruptive.

**Recommended Decision:** When `trigger_ads_key` in `previous_state_df` differs from the current trigger's `ads_fingerprint()`, reset the user's journey to Ad_1 with a WARNING log: "User {uid} journey reset: trigger {trigger_name} ad sequence changed between runs." Journey reset means: `current_ad = first_ad`, `days_in_ad = 0`, `journey_step = 1`, `ad_click_received = False`. Journey status is preserved as ACTIVE (user was mid-journey and remains ACTIVE, just from the beginning). This must be applied in `UserStateManager.initialize_user_states()` after the three-way merge, as a post-merge reconciliation step.

**Impacted Components:**
- `core/user_state_manager.py` — post-merge reconciliation: `trigger_ads_key` drift detection
- `models/trigger_config.py` — `ads_fingerprint()` method

**Acceptance Criteria:**
1. User ACTIVE on Ad_2, `trigger_ads_key="abc12345"`. Current config fingerprint for trigger = "xyz99999" (different). User's journey resets to Ad_1 in `final_state_df` after initialization.
2. A WARNING log is emitted for each user whose journey was reset due to key mismatch.
3. User ACTIVE on Ad_2, `trigger_ads_key="abc12345"`. Current config fingerprint = "abc12345" (same). User's journey is preserved at Ad_2.

---

## SECTION 15 — TRIGGER HIERARCHY RULES

### Decision 15.1 — Which Trigger Governs TCC When User Switches Triggers

**Business Situation:** User U1 was in Trigger_A in Run_1 (`historical_engaged=True` for Trigger_A). In Run_2, U1 appears in the trigger file under Trigger_B (priority higher; journey dropped per Decision 4.2). Which trigger's TCC capacity does U1's historical engagement reduce?

**Recommended Behavior:** U1's `historical_engaged=True` flag in Run_1 was attributed to Trigger_A. In Run_2, U1 is now in Trigger_B. U1's historical engagement (from Run_1) reduces Trigger_A's TCC, NOT Trigger_B's TCC. U1 is brand-new to Trigger_B (no prior engagement with Trigger_B's ads).

**Recommended Decision:** `_init_capacity_tracker()` must count `historically_engaged` per-trigger using the user's `trigger_name` from state — not their presence in any historical engagement broadly. When extended schema is available in historical_df, `Trigger_Name` column is used to scope the count per trigger. When using `previous_state_df` for the `historical_engaged` count, use the `trigger_name` stored in that row.

**Impacted Components:**
- `core/engagement_generator.py` — `_init_capacity_tracker()` per-trigger scoping
- `core/audience_manager.py` — `compute_remaining_capacity()` per-trigger scoping

**Acceptance Criteria:**
1. U1 has `historical_engaged=True` for Trigger_A (from prior state). U1 enters Run_2 under Trigger_B. Trigger_A's `remaining_capacity` reduced by 1 (if Trigger_A is present in Run_2). Trigger_B's capacity NOT reduced by U1.
2. When extended historical schema is present, Trigger_Name column is used to attribute engagement to the correct trigger's TCC.

---

### Decision 15.2 — Trigger with Zero engagement_rate_target

**Business Situation:** A `TriggerConfig` with `engagement_rate_target=0.0` is a valid configuration — it means the trigger generates no qualifying engagements (impressions only, or purely informational). The TCC floor fix (`max(1, ...)`) in CRIT-007 must not apply to zero-rate triggers. The current document states: `max(1, ...) if engagement_rate_target > 0 else 0`.

**Recommended Behavior:** When `engagement_rate_target=0.0`, `remaining_capacity=0` is intentional and correct. The TCC floor (`max(1, ...)`) does NOT apply. Zero-rate triggers receive only impressions; no click or open events are generated.

**Recommended Decision:** The guard `if trigger.engagement_rate_target > 0` already in the TJR-001 spec is the correct gate. `remaining_capacity = 0` for zero-rate triggers. `CoolingOverrideService` has no effect on zero-rate triggers' eligibility (they can still be processed; they just generate no qualifying events).

**Impacted Components:**
- `core/engagement_generator.py` — `_init_capacity_tracker()` zero-rate guard (already specified)
- `utils/schema_validator.py` — validate `engagement_rate_target >= 0.0` (allow zero)

**Acceptance Criteria:**
1. Trigger with `engagement_rate_target=0.0` has `remaining_capacity=0`. No click or open events generated for any user under this trigger.
2. Impression events ARE generated for zero-rate trigger users (journey still advances for duration-based ads).
3. TCC floor `max(1, ...)` does NOT apply when `engagement_rate_target=0.0`. Zero remains zero.

---

### Decision 15.3 — Trigger Priority vs Ad Sequence Length Interaction

**Business Situation:** The ARCHITECTURE_REMEDIATION_PACKAGE notes that per-trigger ad sequence validation must confirm consecutive `ad_order` values starting at 1. What if Trigger_A has a 3-ad sequence and Trigger_B has a 1-ad sequence? Users in Trigger_B complete in 1 ad cycle. Can completed Trigger_B users then be re-triggered into Trigger_A (a different trigger) in the same campaign run?

**Recommended Behavior:** No. A user cannot switch triggers within a single simulation run except via the interruption mechanic in Decision 4.2 (higher-priority trigger at run start). A user who completes Trigger_B's 1-ad journey becomes COMPLETED + COOLING under Trigger_B. They cannot be moved to Trigger_A within the same run. Re-triggering into a different trigger requires them to appear in a future run's trigger file under that different trigger.

**Recommended Decision:** Journey completion ends the user's active processing for the current run. COMPLETED users are not re-queued to any other trigger within the same run. This is enforced by `JourneyEngine._ELIGIBLE_FOR_JOURNEY = {NEW, ACTIVE, RE_ENTRY}` — COMPLETED is not in this set. No cross-trigger re-triggering occurs within a single simulation run.

**Impacted Components:**
- `core/journey_engine.py` — `_ELIGIBLE_FOR_JOURNEY` set: COMPLETED is absent (already correct)
- Documentation: docstring confirming within-run cross-trigger re-triggering is not supported

**Acceptance Criteria:**
1. User completes Trigger_B's journey on Day 3 of a 7-day simulation. The user has no events on Trigger_A's ads in the same simulation run.
2. User's `trigger_name` remains "Trigger_B" in `final_state_df`.

---

### Decision 15.4 — Global vs Per-Trigger Cooling Period

**Business Situation:** `ConfigRegistry.cooling_period_days` is a single global setting. It applies to all triggers. The remediation documents do not specify whether per-trigger cooling period overrides are supported.

**Recommended Behavior:** Cooling period is a GLOBAL campaign setting only. Per-trigger cooling period is NOT supported in this remediation scope. All triggers use `ConfigRegistry.cooling_period_days`. This is a deliberate scope limit — per-trigger cooling would require a new UI surface and `TriggerConfig` field not included in the current architecture.

**Recommended Decision:** `cooling_period_days` is global. `TriggerConfig` does NOT receive a `cooling_period_days` field in this remediation. Any future request for per-trigger cooling periods must be treated as a new feature request. Document this constraint in `TriggerConfig` docstring: "cooling_period_days is governed globally by ConfigRegistry; per-trigger cooling is not currently supported."

**Impacted Components:**
- `models/trigger_config.py` — docstring only
- `models/config_registry.py` — confirm `cooling_period_days` is used by all cooling calculations

**Acceptance Criteria:**
1. Campaign with Trigger_A and Trigger_B, `cooling_period_days=14`. Completed users under BOTH triggers have `cooling_period_end = completion_date + 14 days`.
2. No `cooling_period_days` field exists on `TriggerConfig`.

---

## SUMMARY OF ALL DECISIONS

| # | Decision | Verdict |
|---|----------|---------|
| 1.1 | Same-priority tie-breaking | Alphabetic by trigger_name (case-insensitive, ascending) |
| 1.2 | Priority numeric range | priority ≥ 1; lower = higher priority; zero raises ValueError |
| 2.1 | Multi-trigger conflict | One journey per user; highest-priority trigger wins; lower-priority discarded |
| 2.2 | Equal-priority conflict warning | Emit WARNING when alphabetic tie-break used |
| 3.1 | Same-trigger duplicate rows | Deduplicate on (User_ID, Trigger_Name); keep most recent Trigger_Date |
| 3.2 | distribution_pct sum | Advisory only; WARNING if sum deviates from 1.0 by >1%; not a hard gate |
| 4.1 | Active user re-triggered same trigger | New entry discarded; active journey continues |
| 4.2 | Active user re-triggered different trigger | Higher-priority new trigger DROPs current journey; lower-priority discarded |
| 5.1 | move_on_click per-ad evaluation | Independent per ad; mixed journeys supported |
| 5.2 | Click + duration simultaneous | When move_on_click=True, duration is NEVER evaluated; click is the only mechanism |
| 5.3 | DROPPED journey re-entry | No cooling; treated as NEW on re-triggering; allow_reentry does not apply |
| 6.1 | Historical-active user with new trigger | Same interrupt logic as Decision 4.2 applies |
| 6.2 | Synthetic trigger row fields | Trigger_Date = simulation_start_date; Segment from state or "Historical" |
| 7.1 | Cooling boundary condition | `as_of_date >= cooling_period_end` → RE_ENTRY (inclusive boundary) |
| 7.2 | allow_reentry=False eligibility | EXCLUDED immediately; cooling period irrelevant; allow_reentry evaluated first |
| 8.1 | cooling_override with allow_reentry=False | No-op; CoolingOverrideService returns state unchanged |
| 8.2 | cooling_override scope | Global; applies to all triggers |
| 9.1 | Journey completion definition | Terminal ad click (click-gated) OR duration elapsed (duration-based) |
| 9.2 | Non-completing user at run end | Remains ACTIVE; no automatic DROP; carries forward |
| 10.1 | Weekly counter cross-run | Calendar-week scoped; carry forward; reset on first Monday of new run |
| 10.2 | Daily vs weekly cap | Weekly cap only (DEFAULT_FREQUENCY_MAX); no daily cap |
| 11.1 | Historical completion + same trigger in file | RE_ENTRY (historical completion honored) |
| 11.2 | Historical completion + different trigger | Different trigger unaffected; NEW for new trigger; TCC scoped per-trigger |
| 11.3 | Multiple historical completions | Most recent Completion_Date governs |
| 12.1 | RE_ENTRY journey start position | Always Ad_1; behavioral profile preserved |
| 12.2 | RE_ENTRY with changed ad sequence | Current config's sequence; trigger_ads_key updated |
| 12.3 | SKIPPED user re-triggering | Treated as NEW; behavioral profile preserved |
| 13.1 | Previously EXCLUDED + allow_reentry=True | Re-evaluated per current config; may become RE_ENTRY |
| 13.2 | NOT_STARTED + SKIPPED in previous state | Treated as NEW |
| 14.1 | historical_df vs previous_state_df conflict | previous_state_df wins absolutely; historical_df only used for absent users |
| 14.2 | Campaign_ID mismatch in multi-run | Mismatched campaign_id rows discarded; user treated as NEW |
| 14.3 | Ad sequence changed between runs | trigger_ads_key drift → journey reset to Ad_1 with WARNING |
| 15.1 | TCC attribution when user switches triggers | Historical engagement attributed to original trigger only |
| 15.2 | Zero engagement_rate_target | remaining_capacity=0; TCC floor does NOT apply; impression-only |
| 15.3 | Within-run cross-trigger re-triggering | Not supported; COMPLETED users cannot switch triggers mid-run |
| 15.4 | Per-trigger cooling period | Not in scope; cooling_period_days is global only |

---

## IMPLEMENTATION ENFORCEMENT

This document is binding. The following gates must be added to the implementation workflow:

1. **Wave 1 entry gate:** Engineering lead must confirm awareness of Decisions 1.1, 1.2, 3.1, 3.2 before writing any trigger-file processing code.

2. **Wave 2 entry gate:** Engineering lead must confirm awareness of Decisions 2.1, 2.2, 4.1, 4.2, 5.1, 5.2, 5.3 before modifying `JourneyEngine` or `EngagementGenerator`.

3. **Wave 3 entry gate:** Engineering lead must confirm awareness of Decisions 6.1, 6.2, 11.1, 11.2, 11.3 before implementing `HistoricalStateReconstructor`.

4. **Wave 4 entry gate:** Engineering lead must confirm awareness of Decisions 7.1, 7.2, 8.1, 8.2, 9.1, 9.2, 15.1, 15.2 before modifying `CoolingOverrideService`, `AudienceManager`, or `BehaviorEngine`.

5. **Wave 5 entry gate:** Engineering lead must confirm all 35 decisions are reflected in acceptance criteria tests before declaring Wave 5 complete.

---

## SIGN-OFF REQUIRED

This document must be signed off by the Product Owner before Wave 1 implementation begins. Any deviation from a Recommended Decision must be documented as a numbered amendment to this document, not as an undocumented implementation choice.

| Role | Name | Sign-Off Date |
|------|------|--------------|
| Product Owner | | |
| CTO | | |
| Principal Architect | | |
| QA Director | | |
| Release Manager | | |

---

*Document: TDM-001 | TRIGGER_AND_REENTRY_DECISION_MATRIX.md | v1.0 | 2026-06-23*
