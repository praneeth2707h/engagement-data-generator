# TRIGGER JOURNEY REMEDIATION
## Engagement Data Generator — Trigger-Specific Journey Logic

**Document ID:** TJR-001  
**Version:** 1.0  
**Date:** 2026-06-23  
**Parent:** ARCHITECTURE_REMEDIATION_PACKAGE.md (ARP-001)  
**Defects Addressed:** CRIT-002, CRIT-007, CRIT-008, HIGH-004

---

## SECTION 1 — CURRENT STATE ASSESSMENT

### 1.1 Global Ad Sequence Architecture

`ConfigRegistry.ads: tuple[AdConfig, ...]` defines one journey for the entire campaign. `JourneyEngine` is constructed once per `EngagementGenerator` instance, with `config.ads` as the ad sequence. Every user — regardless of their trigger — advances through the same ads in the same order.

This is architecturally correct for single-trigger campaigns. For multi-trigger campaigns where different triggers represent fundamentally different engagement pathways (e.g., "New Prescriber" trigger gets a 3-ad sequence; "Existing Patient" trigger gets a 1-ad sequence), the current design is not capable.

### 1.2 EngagementGenerator Daily Loop — Current

```python
def generate(self, state_df, simulation_start, simulation_end):
    df = state_df.copy()
    for sim_date in date_range(simulation_start, simulation_end):
        # All users processed by a single JourneyEngine instance
        df = self._je.advance(df, sim_date)  # ← same JourneyEngine for all triggers
        # TCC enforcement by trigger
        df = self._apply_tcc(df, sim_date)
        # Event generation
        daily_events = self._be.generate_events(df, sim_date)
        ...
```

`self._je` is a single `JourneyEngine` instance built from `config.ads`. There is no per-trigger routing.

### 1.3 CTR/TER Accuracy — Current Failure Mode

**Observed:** CTR=0% when target=2%.

**Root cause analysis:**

Step 1 — Target allocation: `EngagementGenerator._init_capacity_tracker()` computes `remaining_capacity = ceil(n_users * engagement_rate_target) - historically_engaged`. At 2% TER with 100 users, `remaining_capacity = ceil(2) - 0 = 2`. So only 2 users are allowed to have qualifying events.

Step 2 — BehaviorEngine event generation: For each user, `BehaviorEngine` computes a composite engagement score. For a user on a Display channel ad, a Click event is generated if `random_draw < target_ctr * composite_score`. With composite_score ≈ 0.5 (neutral initialization) and target_ctr = 0.10: probability ≈ 0.05. With 100 users simulated over 7 days, the expected number of Click events = `100 users × 7 days × 0.05` = 35 expected clicks total. But TCC allows only 2 qualifying events. So after 2 clicks are consumed, remaining_capacity=0, and BehaviorEngine suppresses qualifying events for all users via the far-future cooldown trick.

The problem: TCC correctly limits total qualifying events to 2, but those 2 qualifying events may already exist (from the first 1-2 days of simulation). After they are consumed, observed CTR = 2/700 = 0.3% — not 0%, but well below target.

The **actual** observed CTR=0% failure arises when `remaining_capacity=0` is computed at initialization because `historically_engaged >= ceil(n_users * engagement_rate_target)`. In this case, TCC blocks ALL qualifying events for the entire simulation — and no clicks are generated at all, producing CTR=0%.

**Example:** 100 users, 2% TER target → capacity=2. If historical file has ≥2 historically engaged users (common), remaining_capacity=0 at Day 1. All users get far-future cooldown. CTR=0%.

### 1.4 Journey Progression Gating — Current State

`JourneyEngine` advances users based on `move_on_click=True/False` and duration. There is no explicit gating enforcing that a user on Ad_N must have produced a Click event on Ad_(N-1) before advancing. With `move_on_click=True`, a click is required to advance to the next ad. But `move_on_click=False` (duration-based) means users advance automatically after `duration_days` regardless of click history.

`ValidationEngine` does not currently check the causal chain. There is no VR-J001 rule verifying that users on Ad_2 have at least one Click event for Ad_1.

### 1.5 Journey Status in Events (HIGH-004)

`BehaviorEngine.generate_events()` receives the full `state_df` slice. The function `_should_generate_event()` checks engagement cooldown, weekly caps, and TCC, but does not gate on `journey_status`. Users with `journey_status=Not_Started` (initialized at Stage 1, not yet advanced by JourneyEngine at the start of Day 1) can receive events if their composite score exceeds a threshold.

---

## SECTION 2 — DESIRED STATE

### 2.1 Trigger-Specific Ad Sequences

Each `TriggerConfig` may define its own `ads: tuple[AdConfig, ...] | None`. When present, users entering via that trigger advance through the trigger's ad sequence only. When absent, the campaign-level `ConfigRegistry.ads` is the fallback.

`EngagementGenerator` must partition the state DataFrame by trigger, construct a trigger-scoped `JourneyEngine` for each partition, advance each partition independently, then reassemble.

### 2.2 TriggerJourneyResolver

A new lightweight service `TriggerJourneyResolver` encapsulates trigger-to-ads resolution:

```python
class TriggerJourneyResolver:
    def __init__(self, config: ConfigRegistry) -> None:
        self._config = config
        # Pre-build JourneyEngine per trigger at construction time
        self._engines: dict[str, JourneyEngine] = {}
        for trigger in config.triggers:
            ads = trigger.get_effective_ads(config.ads)
            self._engines[trigger.trigger_name] = JourneyEngine(
                config, ads_override=ads
            )
        # Fallback for users with no trigger or unknown trigger
        self._default_engine = JourneyEngine(config)

    def get_engine(self, trigger_name: str | None) -> JourneyEngine:
        """Return the JourneyEngine for the given trigger.
        Falls back to default engine for unknown/null triggers.
        """
        if trigger_name and trigger_name in self._engines:
            return self._engines[trigger_name]
        return self._default_engine
```

### 2.3 JourneyEngine — ads_override Parameter

`JourneyEngine.__init__` must accept an optional `ads_override: tuple[AdConfig, ...] | None`. When provided, the override tuple is used instead of `config.ads` for all internal lookups:

```python
def __init__(
    self,
    config: ConfigRegistry,
    ads_override: tuple[AdConfig, ...] | None = None,
) -> None:
    effective_ads = ads_override if ads_override is not None else config.ads
    # build _ads_sorted, _ad_by_name, _next_ad, _first_ad from effective_ads
    ...
```

### 2.4 EngagementGenerator — Per-Trigger Cohort Processing

```python
def generate(self, state_df, simulation_start, simulation_end):
    df = state_df.copy()
    resolver = TriggerJourneyResolver(self._config)

    for sim_date in date_range(simulation_start, simulation_end):
        # Per-trigger journey advancement
        updated_parts = []
        for trigger_name, cohort in df.groupby("trigger_name", dropna=False):
            engine = resolver.get_engine(trigger_name)
            updated_parts.append(engine.advance(cohort.copy(), sim_date))
        df = pd.concat(updated_parts, ignore_index=False).sort_index()

        # TCC enforcement (unchanged)
        df = self._apply_tcc(df, sim_date)

        # Event generation (with journey_status gate — HIGH-004 fix)
        active_df = df[df["journey_status"] == JourneyStatus.ACTIVE.value].copy()
        daily_events = self._be.generate_events(active_df, sim_date)
        ...
```

### 2.5 CTR/TER Accuracy Redesign

The root cause is that `remaining_capacity` can be 0 at simulation start when historical engagement fills the TCC ceiling. The fix has two components:

**Fix A — TCC floor:** `remaining_capacity` must have a minimum value of 1 when `engagement_rate_target > 0`. A campaign with a non-zero TER target must always allow at least 1 qualifying event per trigger, regardless of historical engagement.

```python
remaining_capacity = max(1, ceil(n_users * target_rate) - historically_engaged)
# Only when engagement_rate_target > 0
```

**Fix B — Targeted cohort selection for low-TER:** When `remaining_capacity / n_users < 0.05` (less than 5%), the current uniform-probability approach produces CTR near 0% because random draws rarely exceed threshold. Instead, a targeted cohort mechanism must be used:

1. At simulation start, pre-select a cohort of `remaining_capacity` users ranked by descending composite engagement score.
2. Assign these users an `engagement_boost = True` flag in state_df.
3. BehaviorEngine applies a `boost_multiplier = 3.0` to composite score for boosted users.
4. Non-boosted users continue receiving impressions but have very low qualifying-event probability.

This ensures the target qualifying-event count is reliably reached without inflating CTR for the majority of users.

**Fix C — CTR measurement accuracy:** Observed CTR must be measured correctly:

```
CTR = n_click_events / n_impression_events (for Display channels)
Open Rate = n_open_events / n_send_events (for Email/WhatsApp channels)
TER = n_qualifying_events / n_unique_users_with_any_event
```

The current `_METRICS_COLS` includes `actual_ctr_display` and `actual_open_rate_email/wa`. These must be computed from the event DataFrame, not from the target values.

### 2.6 Journey Progression Gating Validation (CRIT-008)

`ValidationEngine` must add rule VR-J001:

For each user in `events_df` who has events on Ad_N (where N > 1), there must exist at least one Click event for Ad_(N-1) for the same user. If `move_on_click=False`, the advance is duration-based and this check does not apply (users advance without clicking). The rule only fires for journeys where at least one ad has `move_on_click=True`.

Implementation:

```python
def _check_journey_causal_chain(self, events_df: pd.DataFrame) -> list[dict]:
    """VR-J001: Verify click-gated journey progression."""
    violations = []
    # Only check click-gated ads
    click_gated_ads = {ad.ad_name for ad in self._config.ads if ad.move_on_click}
    if not click_gated_ads:
        return violations  # no click-gated ads; rule not applicable

    # For each user with events on Ad_N (click-gated), check for Click on Ad_(N-1)
    for uid, user_events in events_df.groupby("user_id"):
        # Build set of (ad_name, action_type) pairs for this user
        user_pairs = set(zip(user_events["current_ad"], user_events["action_type"]))
        for ad in self._config.ads:
            if ad.ad_name not in click_gated_ads:
                continue
            prev_ad = self._config.get_ad_by_order(ad.ad_order - 1)
            if prev_ad is None:
                continue  # Ad_1 has no predecessor
            # If user has any event on ad.ad_name, check for Click on prev_ad
            on_current_ad = any(a == ad.ad_name for (a, _) in user_pairs)
            has_prev_click = (prev_ad.ad_name, "Click") in user_pairs
            if on_current_ad and not has_prev_click:
                violations.append({
                    "user_id": uid,
                    "rule_id": "VR-J001",
                    "ad_name": ad.ad_name,
                    "prev_ad_name": prev_ad.ad_name,
                    "detail": f"User on {ad.ad_name} (step {ad.ad_order}) with no Click event on {prev_ad.ad_name}",
                })
    return violations
```

---

## SECTION 3 — GAP ANALYSIS

### Gap G-TJR-001: JourneyEngine has no ads_override parameter

**Current:** `JourneyEngine.__init__(config)` uses `config.ads` exclusively.  
**Required:** `JourneyEngine.__init__(config, ads_override=None)` uses override when provided.  
**Files:** `core/journey_engine.py`.

### Gap G-TJR-002: EngagementGenerator uses single JourneyEngine for all triggers

**Current:** Single `self._je` constructed in `__init__`.  
**Required:** `TriggerJourneyResolver` per run; per-trigger cohort processing in the daily loop.  
**Files:** `core/engagement_generator.py`, `core/trigger_journey_resolver.py` (new).

### Gap G-TJR-003: TCC remaining_capacity can be 0 at simulation start

**Current:** `remaining_capacity = ceil(n_users * rate) - historically_engaged` — no floor.  
**Required:** `remaining_capacity = max(1, ceil(...) - ...)` when rate > 0.  
**Files:** `core/engagement_generator.py` (or `core/audience_manager.py` depending on ownership).

### Gap G-TJR-004: No targeted cohort selection for low-TER targets

**Current:** Uniform probability across all users; low-TER campaigns get CTR=0%.  
**Required:** Pre-selected boost cohort; `engagement_boost` flag; `boost_multiplier=3.0` in BehaviorEngine.  
**Files:** `core/engagement_generator.py`, `core/behavior_engine.py`.

### Gap G-TJR-005: No VR-J001 journey causal chain rule

**Current:** ValidationEngine has no causal chain rules.  
**Required:** VR-J001 through VR-J005 added.  
**Files:** `core/validation_engine.py`.

### Gap G-TJR-006: BehaviorEngine processes NOT_STARTED users

**Current:** No journey_status gate in BehaviorEngine.  
**Required:** Hard gate before event generation.  
**Files:** `core/behavior_engine.py`.

---

## SECTION 4 — ARCHITECTURE CHANGES

### 4.1 JourneyEngine Modification

**Modified:** `core/journey_engine.py`

```python
def __init__(
    self,
    config: ConfigRegistry,
    ads_override: tuple[AdConfig, ...] | None = None,
) -> None:
    """Initialize JourneyEngine.

    Args:
        config: Campaign ConfigRegistry.
        ads_override: If provided, use these ads instead of config.ads.
                      Must be non-empty. Used by TriggerJourneyResolver
                      for trigger-specific ad sequences.
    """
    effective_ads = ads_override if ads_override is not None else config.ads

    if not effective_ads:
        raise InputValidationError(
            "config.ads",
            "JourneyEngine requires at least one ad; received empty tuple.",
        )

    self._config = config
    # All ad maps built from effective_ads, not config.ads
    self._ads_sorted: list[AdConfig] = sorted(effective_ads, key=lambda a: a.ad_order)
    self._ad_by_name: dict[str, AdConfig] = {a.ad_name: a for a in effective_ads}
    self._next_ad: dict[str, str | None] = {
        self._ads_sorted[i].ad_name: (
            self._ads_sorted[i+1].ad_name if i+1 < len(self._ads_sorted) else None
        )
        for i in range(len(self._ads_sorted))
    }
    self._first_ad: AdConfig = self._ads_sorted[0]
    self._duration_map = {a.ad_name: a.duration_days for a in effective_ads}
    self._move_on_click_map = {a.ad_name: a.move_on_click for a in effective_ads}
    self._channel_map = {a.ad_name: a.channel for a in effective_ads}
    self._vendor_map = {
        a.ad_name: (a.vendor if a.vendor is not None else config.default_vendor)
        for a in effective_ads
    }
    self._logger = get_logger(__name__)
```

### 4.2 TriggerJourneyResolver — New Service

**New file:** `core/trigger_journey_resolver.py`

Full implementation (compact form):

```python
"""Resolves trigger → JourneyEngine mappings for per-trigger ad sequences.

References
----------
* CRIT-002 — Trigger-Specific Journeys
* TJR-001  — Trigger Journey Remediation document
"""
from __future__ import annotations
from models.config_registry import ConfigRegistry
from core.journey_engine import JourneyEngine
from utils.logger import get_logger

_logger = get_logger(__name__)


class TriggerJourneyResolver:
    """Pre-builds one JourneyEngine per trigger for the campaign.

    Args:
        config: Campaign ConfigRegistry.
    """

    def __init__(self, config: ConfigRegistry) -> None:
        self._config = config
        self._engines: dict[str, JourneyEngine] = {}

        for trigger in config.triggers:
            effective_ads = trigger.get_effective_ads(config.ads)
            self._engines[trigger.trigger_name] = JourneyEngine(
                config, ads_override=effective_ads
            )
            if trigger.ads is not None:
                _logger.info(
                    "TriggerJourneyResolver: trigger='%s' using %d trigger-specific ads",
                    trigger.trigger_name, len(trigger.ads),
                )
            else:
                _logger.debug(
                    "TriggerJourneyResolver: trigger='%s' using campaign-level ads",
                    trigger.trigger_name,
                )

        self._default_engine = JourneyEngine(config)

    def get_engine(self, trigger_name: str | None) -> JourneyEngine:
        """Return JourneyEngine for trigger_name; falls back to default."""
        if trigger_name and trigger_name in self._engines:
            return self._engines[trigger_name]
        return self._default_engine

    @property
    def trigger_names(self) -> list[str]:
        return list(self._engines.keys())


__all__ = ["TriggerJourneyResolver"]
```

### 4.3 EngagementGenerator Modifications

**Key changes to `core/engagement_generator.py`:**

1. Replace single `self._je` with `TriggerJourneyResolver` instantiated at the start of `generate()`.
2. Add per-trigger cohort loop in the daily processing step.
3. Add TCC floor (`max(1, ...)`) in `_init_capacity_tracker()`.
4. Add boost cohort selection for low-TER triggers.
5. Gate event generation on `journey_status=Active`.

**TCC floor fix:**

```python
def _init_capacity_tracker(self, state_df, ...) -> dict[str, int]:
    ...
    for trigger in self._config.triggers:
        n_trigger_users = len(trigger_cohorts.get(trigger.trigger_name, []))
        hist_count = int(state_df[
            (state_df["trigger_name"] == trigger.trigger_name)
            & (state_df["historical_engaged"] == True)
        ]["user_id"].nunique())
        raw_capacity = math.ceil(n_trigger_users * trigger.engagement_rate_target)
        # FIX: floor at 1 when rate > 0 (CRIT-007)
        remaining = max(1, raw_capacity - hist_count) if trigger.engagement_rate_target > 0 else 0
        capacity_tracker[trigger.trigger_name] = remaining
    return capacity_tracker
```

**Boost cohort selection:**

```python
def _select_boost_cohort(self, state_df: pd.DataFrame, capacity: int) -> set[str]:
    """Select top-scoring users for engagement boosting at low-TER.

    Returns set of user_ids that will receive engagement_boost=True.
    Only used when capacity < n_users * 0.05 (low-volume TER target).
    """
    if capacity >= len(state_df) * 0.05:
        return set()  # high-TER: no boost needed
    # Rank by engagement_score descending; select top `capacity` users
    ranked = state_df.nlargest(min(capacity * 2, len(state_df)), "engagement_score")
    return set(ranked["user_id"].head(capacity))
```

**BehaviorEngine boost_multiplier:**

```python
# In BehaviorEngine.generate_events():
def generate_events(
    self,
    state_df: pd.DataFrame,
    simulation_date: date,
    boost_user_ids: set[str] | None = None,  # NEW
) -> pd.DataFrame:
    # HIGH-004: gate on journey_status=Active
    active_mask = state_df["journey_status"] == JourneyStatus.ACTIVE.value
    df = state_df[active_mask].copy()
    if df.empty:
        return pd.DataFrame(columns=_EVENT_OUT_COLS)

    # Apply boost multiplier to composite score for selected users
    if boost_user_ids:
        boost_mask = df["user_id"].isin(boost_user_ids)
        df.loc[boost_mask, "engagement_score"] = (
            df.loc[boost_mask, "engagement_score"].clip(upper=1.0) * 3.0
        ).clip(upper=1.0)
    ...
```

### 4.4 ValidationEngine — New Rules

**Modified:** `core/validation_engine.py`

Add `_check_journey_causal_chain()` (see Section 2.6 above) and integrate into `validate()`.

Also add:

```python
def _check_no_not_started_events(self, events_df: pd.DataFrame) -> list[dict]:
    """VR-J002: No events for NOT_STARTED users."""
    if "journey_status" not in events_df.columns:
        return []
    bad = events_df[events_df["journey_status"] == "Not_Started"]
    if bad.empty:
        return []
    return [{
        "rule_id": "VR-J002",
        "severity": "Hard",
        "detail": f"{len(bad)} event(s) for users with journey_status=Not_Started",
        "user_ids": bad["user_id"].unique().tolist()[:10],
    }]
```

---

## SECTION 5 — DATA MODEL CHANGES

### New state_df Column: engagement_boost

A new boolean column `engagement_boost` is added to the simulation state DataFrame during `EngagementGenerator.generate()`. It is a transient column (not persisted to `final_state_df`) used only within the daily loop to signal BehaviorEngine boost.

```python
# In EngagementGenerator.generate(), before daily loop:
boost_cohorts: dict[str, set[str]] = {}
for trigger_name, cap in capacity_tracker.items():
    trigger_cohort_df = state_df[state_df["trigger_name"] == trigger_name]
    boost_cohorts[trigger_name] = self._select_boost_cohort(trigger_cohort_df, cap)

df["engagement_boost"] = df["user_id"].apply(
    lambda uid, tname: uid in boost_cohorts.get(tname, set()),
    # vectorized equivalent:
)
# Vectorized form:
df["engagement_boost"] = df.apply(
    lambda row: row["user_id"] in boost_cohorts.get(row["trigger_name"], set()),
    axis=1,
)
```

Note: this `apply` is acceptable for the pre-loop setup step (called once, not per-day). A vectorized form using `.isin()` per trigger can be used as optimization.

### Updated _EVENT_OUT_COLS

```python
_EVENT_OUT_COLS: tuple[str, ...] = (
    "campaign_id", "user_id", "simulation_date", "channel",
    "action_type", "current_ad", "vendor", "trigger_name", "segment",
    "journey_status",   # NEW — for VR-J002 validation
    "journey_step",     # NEW — for VR-J001 causal chain
)
```

---

## SECTION 6 — USER STATE CHANGES

### journey_step Written by JourneyEngine

When `JourneyEngine._start_journeys()` places a user on the first ad: `journey_step = 1`.

When `JourneyEngine._advance_active()` advances to the next ad: `journey_step = next_ad.ad_order`.

When `JourneyEngine._complete_journeys()` completes the journey: `journey_step = None`.

This requires `journey_step` in `_STATE_REQUIRED_COLS`.

### trigger_ads_key Written at Journey Start

When `JourneyEngine._start_journeys()` starts a journey:

```python
# Compute fingerprint from the engine's effective ads
ads_names = "|".join(a.ad_name for a in self._ads_sorted)
import hashlib
key = hashlib.md5(ads_names.encode()).hexdigest()[:8]
df.loc[mask_start, "trigger_ads_key"] = key
```

This allows downstream detection of mid-run ad sequence changes.

---

## SECTION 7 — UI CHANGES

### Campaign Page — Per-Trigger Ad Journey

```python
# In campaign_page.py, inside the trigger expander:
for i, t in enumerate(triggers):
    with st.expander(f"Trigger {i+1}: {t.get('trigger_name','')}", expanded=(i == 0)):
        # ... existing trigger fields (trigger_name, priority, engagement_rate_target) ...

        # NEW: Per-trigger ad sequence
        use_custom_ads = st.checkbox(
            "Use custom ad sequence for this trigger",
            value=bool(t.get("ads") is not None),
            key=f"t_custom_ads_{i}",
            help="When enabled, this trigger uses its own ad journey instead of the campaign-level ads."
        )
        if use_custom_ads:
            t_ads = t.get("ads") or []
            n_t_ads = st.number_input(
                f"Number of Ads for {t.get('trigger_name','this trigger')}",
                min_value=1, max_value=10,
                value=max(1, len(t_ads)),
                step=1,
                key=f"t_n_ads_{i}"
            )
            while len(t_ads) < n_t_ads:
                t_ads.append({
                    "ad_name": f"Ad_{t.get('trigger_name','T')}_{len(t_ads)+1}",
                    "ad_order": len(t_ads)+1,
                    "duration_days": 7,
                    "move_on_click": False,
                    "channel": "Display",
                    "vendor": None,
                    "target_ctr": 0.10,
                })
            t_ads = t_ads[:n_t_ads]
            for j, t_ad in enumerate(t_ads):
                c1, c2, c3 = st.columns(3)
                t_ad["ad_name"] = c1.text_input("Ad Name", value=t_ad.get("ad_name",""), key=f"t_ad_name_{i}_{j}")
                t_ad["channel"] = c2.selectbox("Channel", options=_CHANNEL_OPTIONS,
                                                index=_CHANNEL_OPTIONS.index(t_ad.get("channel","Display")),
                                                key=f"t_ad_ch_{i}_{j}")
                t_ad["duration_days"] = c3.number_input("Duration (days)", min_value=1,
                                                          value=int(t_ad.get("duration_days",7)),
                                                          key=f"t_ad_dur_{i}_{j}")
                t_ad["ad_order"] = j + 1
            t["ads"] = t_ads
        else:
            t["ads"] = None
```

### Business Rules Page — Per-Trigger CTR Targets

When a trigger has custom ads, the CTR target section must render those ads alongside campaign-level ads.

---

## SECTION 8 — VALIDATION CHANGES

### New Validation Rules (Summary)

| Rule ID | Severity | Check | Gate condition |
|---------|----------|-------|----------------|
| VR-J001 | Hard | User on Ad_N with no Click on Ad_(N-1) | Only for click-gated ads |
| VR-J002 | Hard | Events with journey_status=Not_Started | Always |
| VR-J003 | Soft | CTR within ±20% of target | Per ad |
| VR-J004 | Soft | TER within ±20% of target | Per trigger |
| VR-J005 | Hard | Duplicate (user_id, date, ad_name, action_type) | Always |

### ValidationEngine.validate() Integration

```python
def validate(self, events_df, audience_df) -> tuple:
    ...
    # NEW rules:
    causal_violations = self._check_journey_causal_chain(events_df)
    not_started_violations = self._check_no_not_started_events(events_df)
    ctr_violations = self._check_ctr_accuracy(events_df)
    ter_violations = self._check_ter_accuracy(events_df, audience_df)
    duplicate_violations = self._check_duplicate_events(events_df)
    ...
```

---

## SECTION 9 — MIGRATION STRATEGY

### JourneyEngine ads_override

The `ads_override=None` default means all existing `JourneyEngine` instantiations continue to work. The `TriggerJourneyResolver` passes `ads_override=effective_ads` when constructing trigger-specific engines.

### EngagementGenerator Cohort Loop

The per-trigger cohort loop using `df.groupby("trigger_name")` is backward compatible with single-trigger campaigns — `groupby` on a single value produces one group, and the behavior is identical to the current single-engine path.

### TCC Floor Change

The `max(1, ...)` floor is a behavioral change: campaigns where `historically_engaged >= ceil(n * rate)` previously got `remaining_capacity=0` (CTR=0%). After the fix, these campaigns get `remaining_capacity=1`. This is the intended correction (CRIT-007). Existing test assertions for `remaining_capacity=0` when historical engagement fills TCC must be updated.

---

## SECTION 10 — BACKWARD COMPATIBILITY ASSESSMENT

| Change | Backward Compatible | Notes |
|--------|--------------------|-|
| `JourneyEngine` ads_override param | YES | Default None; existing code unchanged |
| `TriggerJourneyResolver` | YES | New service; EngagementGenerator uses it internally |
| Per-trigger cohort loop | YES | Single trigger = single group = same behavior |
| TCC floor `max(1, ...)` | BEHAVIORAL CHANGE | CTR=0% bug fixed; test assertions must update |
| Boost cohort selection | YES | No-op when `capacity >= n_users * 0.05` |
| `BehaviorEngine` journey_status gate | BEHAVIORAL CHANGE | NOT_STARTED events removed |
| New validation rules VR-J001–J005 | POTENTIALLY BREAKING | Hard rules may fail existing test fixtures |
| `journey_step` in events | YES | New column; existing tests unaffected if column not asserted |

---

## SECTION 11 — PERFORMANCE IMPACT

| Change | Impact | Notes |
|--------|--------|-------|
| `TriggerJourneyResolver` construction | O(T) JourneyEngine builds at start | T ≤ 10; negligible |
| Per-trigger cohort groupby in daily loop | O(N) groupby per day | Same O(N) as current; groupby is vectorized |
| Boost cohort `nlargest()` | O(N log k) once per trigger | Called once pre-loop; fast |
| VR-J001 causal chain check | O(U * A) | U=users, A=ads; vectorized groupby; fast at 100k |
| VR-J002 NOT_STARTED check | O(E) | E=events; single column comparison |
| `journey_step` writes in JourneyEngine | O(N) per day | One extra column assignment; negligible |

No performance regression vs Stage 16 SLAs.

---

## SECTION 12 — RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Per-trigger cohort state corruption (rows lost in groupby) | Low | High | Assert `len(reassembled_df) == len(pre_loop_df)` in debug builds |
| Boost multiplier inflates CTR for non-boosted users | Low | Medium | Boost applied to `engagement_score` in copy; original score not mutated |
| TCC floor causes capacity overrun | Low | Medium | Floor of 1 = 1 qualifying event maximum beyond historical; trivial overrun |
| VR-J001 false positive for duration-based journeys | Medium | Low | Gate on `move_on_click=True` per ad; no false positives |
| `trigger_ads_key` stale after config change mid-run | Not applicable | N/A | Config is frozen (ConfigRegistry is frozen=True) |

---

## SECTION 13 — ACCEPTANCE CRITERIA

1. Given Trigger_A with `ads=(Ad_A1, Ad_A2)` and Trigger_B with `ads=(Ad_B1,)`, simulation output shows: Trigger_A users have events on Ad_A1 and Ad_A2 only; Trigger_B users have events on Ad_B1 only.

2. Given `engagement_rate_target=0.02` and `historically_engaged=2` users out of 100 users, `remaining_capacity ≥ 1` and observed CTR > 0%.

3. Observed CTR for a 2% TER target is within ±20% of target CTR (i.e., between 1.6% and 2.4%) in an end-to-end simulation with 1,000 users.

4. Given a user on Ad_2 in `events_df` with no Click event for Ad_1 (and Ad_1 has `move_on_click=True`), VR-J001 FAILS for that user.

5. `events_df` contains no rows with `journey_status="Not_Started"`.

6. `TriggerJourneyResolver` with a config containing 3 triggers (2 with custom ads, 1 without) correctly returns trigger-specific JourneyEngines for the first two and the campaign default for the third.

7. `JourneyEngine(config, ads_override=(AdConfig(...),))` builds correctly and uses the override ads, not `config.ads`.

---

## SECTION 14 — DEFINITION OF DONE

- [ ] `core/journey_engine.py` accepts `ads_override` parameter; uses it in all lookups.
- [ ] `core/trigger_journey_resolver.py` created with full implementation.
- [ ] `core/engagement_generator.py` uses `TriggerJourneyResolver`; per-trigger cohort loop.
- [ ] `core/engagement_generator.py` TCC floor `max(1, ...)` applied.
- [ ] `core/engagement_generator.py` boost cohort selection implemented.
- [ ] `core/behavior_engine.py` accepts `boost_user_ids` and applies multiplier.
- [ ] `core/behavior_engine.py` gates on `journey_status=Active` before event generation.
- [ ] `core/validation_engine.py` implements VR-J001 through VR-J005.
- [ ] `ui/campaign_page.py` exposes per-trigger custom ad sequence UI.
- [ ] All acceptance criteria tests pass.
- [ ] Full regression suite passes with 0 failures.
- [ ] Stage 16 scale tests pass without SLA degradation.

---

## SECTION 15 — REGRESSION TEST REQUIREMENTS

### New Test Files

**`tests/test_core/test_trigger_journey_resolver.py`**
- `test_resolver_builds_engine_per_trigger`
- `test_resolver_uses_trigger_specific_ads`
- `test_resolver_falls_back_to_config_ads`
- `test_resolver_unknown_trigger_uses_default`
- `test_resolver_null_trigger_uses_default`

**`tests/test_core/test_journey_engine.py` — additions**
- `test_journey_engine_ads_override_used`
- `test_journey_engine_ads_override_none_uses_config_ads`
- `test_journey_engine_journey_step_set_on_start`
- `test_journey_engine_journey_step_updated_on_advance`
- `test_journey_engine_journey_step_none_on_completion`

**`tests/test_core/test_engagement_generator.py` — additions**
- `test_per_trigger_cohort_users_use_correct_journey`
- `test_tcc_floor_min_one_when_rate_nonzero`
- `test_low_ter_boost_cohort_produces_nonzero_ctr`
- `test_ctr_accuracy_within_20pct_of_target`

**`tests/test_core/test_validation_engine.py` — additions**
- `test_vr_j001_fires_for_ad2_without_ad1_click`
- `test_vr_j001_no_fire_for_duration_advance`
- `test_vr_j002_fires_for_not_started_event`
- `test_vr_j003_ctr_accuracy_soft_rule`
- `test_vr_j004_ter_accuracy_soft_rule`
- `test_vr_j005_duplicate_events_hard_rule`

**`tests/test_e2e/test_multitrigger_certification.py` — additions**
- `test_mt_011_trigger_specific_ads_journey`
- `test_mt_012_trigger_specific_ads_events_isolated`

---

*Document: TJR-001 | TRIGGER_JOURNEY_REMEDIATION.md | v1.0 | 2026-06-23*
