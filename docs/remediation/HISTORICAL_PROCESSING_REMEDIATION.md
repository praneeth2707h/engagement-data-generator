# HISTORICAL PROCESSING REMEDIATION
## Engagement Data Generator — Historical Data Processing Changes

**Document ID:** HPR-001  
**Version:** 1.0  
**Date:** 2026-06-23  
**Parent:** ARCHITECTURE_REMEDIATION_PACKAGE.md (ARP-001)  
**Defects Addressed:** CRIT-001, CRIT-003, CRIT-004, CRIT-005, HIGH-005

---

## SECTION 1 — CURRENT STATE ASSESSMENT

### 1.1 Historical Data Flow — Current

```
Caller supplies historical_df
        ↓
SimulationOrchestrator.run(historical_df=historical_df)
        ↓
AudienceManager.resolve(..., historical_df=historical_df)
        ↓
AudienceManager.compute_remaining_capacity(historical_df)
  → counts distinct engaged users in window
  → subtracts from TCC ceiling
        ↓
ARCH-RISK-003 fix: stamps historical_engaged=True in audience_df
        ↓
historical_df DISCARDED — no further use
```

Historical data never reaches journey reconstruction, user state initialization, or audience augmentation. It is a read-once capacity input.

### 1.2 Historical File Schema — Current

```
Required: User_ID, Date, Action, Channel
Optional: Campaign_ID (defaulted per BIZ-019)
```

No ad-level, journey-level, or trigger-level information is captured. It is impossible to determine from this data which ad a user was on, where they were in the journey, or whether they completed the journey.

### 1.3 Historical Window Filtering — Current

`ConfigRegistry.get_historical_cutoff_date(as_of)` computes the cutoff for the configured window:
- `ALL_TIME` → None (no cutoff)
- `LAST_90` → `as_of - 90 days`
- `LAST_180` → `as_of - 180 days`
- `LAST_365` → `as_of - 365 days`
- `CUSTOM` → `as_of - historical_window_days`

The ARCH-RISK-003 fix applies this window correctly when stamping `historical_engaged`. `AudienceManager.compute_remaining_capacity()` also applies this window. This filtering logic is correct and must be preserved.

### 1.4 load_historical_file — Current

`input_loader.load_historical_file()` correctly:
- Reads CSV or Excel with `dtype=str`
- Handles `Campaign_ID` BIZ-019 defaulting
- Deduplicates on 5-column key (C-005)
- Applies cutoff_date filter
- Applies campaign_match_mode filter
- Filters to qualifying actions only

This function is sound. Changes required are additive: extended column parsing and validation.

### 1.5 What is Missing

1. **Ad-level engagement records** — no `Ad_Name` column in the historical file.
2. **Journey step** — no `Journey_Step` column.
3. **Trigger context** — no `Trigger_Name` column for per-trigger journey resolution.
4. **Completion marker** — no `Completion_Date` column; cannot distinguish mid-journey from completed.
5. **Journey reconstruction service** — `HistoricalStateReconstructor` does not exist.
6. **Audience augmentation** — historically-active users absent from trigger_df are not processed.

---

## SECTION 2 — DESIRED STATE

### 2.1 Extended Historical Schema

The historical engagement file is extended to an 8-column schema. The 4 new columns are optional — their presence enables journey reconstruction; their absence is handled gracefully with no disruption to existing capacity-counting behavior.

```
REQUIRED (4 columns — current):
  User_ID         str    Unique user identifier
  Date            date   Date of engagement
  Action          str    Click, Open, Impression, Sent
  Channel         str    Email, Display, WhatsApp, etc.

OPTIONAL — journey reconstruction (4 additional columns):
  Ad_Name         str    Ad name from ConfigRegistry journey
  Journey_Step    int    1-based position of Ad_Name in journey sequence
  Trigger_Name    str    Trigger_Name that drove this user's journey entry
  Completion_Date date   Date journey was completed; null if not yet complete
```

### 2.2 Historical Schema Detection

`CanonicalSchema.historical_file_has_extended_schema(df)` returns True when all 4 optional columns are present. The presence of any subset (e.g., `Ad_Name` only) is treated as absent — all 4 must be present to enable reconstruction.

### 2.3 Historical Data Pipeline — Desired

```
Caller supplies historical_df (4-col or 8-col)
        ↓
SimulationOrchestrator.run(historical_df=historical_df)
        ↓
[EXISTING] ARCH-RISK-003: AudienceManager capacity counting + historical_engaged stamping
        ↓
[NEW] IF extended schema detected:
  HistoricalStateReconstructor.reconstruct(historical_df, as_of_date=sim_start)
    → reconstructed_state_df (one row per historical user)
        ↓
  Three-way merge in UserStateManager.initialize_user_states(
    trigger_df, previous_state_df, reconstructed_state_df
  )
        ↓
  [NEW] CRIT-003: Augment trigger audience with reconstructed ACTIVE users
        absent from trigger_df
```

### 2.4 HistoricalStateReconstructor — Full Specification

See `USER_STATE_REMEDIATION.md` Section 4.1 for the constructor and method contract. This section defines the reconstruction algorithm in detail.

#### 2.4.1 User Classification

After loading and filtering, users in the historical file fall into four categories:

| Category | Criteria | Reconstructed State |
|----------|----------|-------------------|
| Active | No Completion_Date; most recent qualifying Action on Ad_N | journey_status=Active, current_ad=Ad_N, eligibility_status=ACTIVE |
| Cooling | Has Completion_Date; as_of_date ≤ Completion_Date + cooling_period_days | journey_status=Completed, eligibility_status=COOLING |
| Re-Entry | Has Completion_Date; as_of_date > Completion_Date + cooling_period_days | journey_status=Completed, eligibility_status=RE_ENTRY |
| No qualifying history | No rows after qualifying action filter | Treated as NEW; excluded from reconstructed_state_df |

#### 2.4.2 days_in_ad Calculation

For active users, `days_in_ad` is the number of days elapsed since the most recent engagement on their current ad:

```
days_in_ad = (as_of_date - most_recent_Ad_Name_engagement_date).days
```

This value is capped at `ad.duration_days` to prevent the JourneyEngine from immediately advancing a user on Day 1 of reconstruction:

```
days_in_ad = min(days_elapsed, ad.duration_days - 1)
```

This leaves the user one day away from advancing, which is correct — they should advance on the next simulation day if they have been waiting the full duration.

#### 2.4.3 journey_start_date Reconstruction

`journey_start_date` is set to the date of the earliest engagement on Ad_1 (the first ad) for this user in the historical record. If Ad_1 engagement is not present (user entered mid-journey via historical carry-forward), `journey_start_date` is set to the date of their first historical engagement overall.

#### 2.4.4 Trigger Resolution

The reconstructed row uses `Trigger_Name` from the most recent historical record as the user's `trigger_name`. This determines which trigger-specific ad sequence to use during reconstruction and during the live simulation.

#### 2.4.5 Missing Field Defaults

Fields not derivable from historical data receive safe defaults:
- `engagement_score = 0.5` (neutral)
- `behavior_profile = BehaviorProfile.MODERATE`
- `channel_affinity_* = 0.5`
- `creative_affinities = {ad_name: 0.5 for ad in effective_ads}`
- `weekly_impressions/clicks/opens/engagements = 0` (fresh week)
- `total_lifetime_engagements = count of qualifying actions in historical_df for this user`
- `last_engagement_date = most recent qualifying engagement date`
- `run_count = 0`

---

## SECTION 3 — GAP ANALYSIS

### Gap G-HPR-001: Historical schema has no ad-level data

**Current:** `["User_ID", "Date", "Action", "Channel"]` — no journey context.  
**Required:** Extended schema with `Ad_Name`, `Journey_Step`, `Trigger_Name`, `Completion_Date`.  
**Affected files:** `utils/canonical_schema.py` (new), `utils/schema_validator.py`, `core/input_loader.py`.

### Gap G-HPR-002: load_historical_file does not parse extended columns

**Current:** Only 4 columns parsed; additional columns silently dropped by not being referenced.  
**Required:** Extended columns parsed when present; `Journey_Step` cast to int, `Completion_Date` parsed as date, `Ad_Name` validated non-null for qualifying events.  
**Affected files:** `core/input_loader.py`.

### Gap G-HPR-003: No HistoricalStateReconstructor service

**Current:** Service does not exist.  
**Required:** `core/historical_state_reconstructor.py` with full reconstruction algorithm.  
**Affected files:** New file.

### Gap G-HPR-004: Orchestrator does not invoke reconstruction

**Current:** `historical_df` passed to `AudienceManager` only.  
**Required:** Orchestrator invokes `HistoricalStateReconstructor` pre-Stage 1; passes result to Stage 1.  
**Affected files:** `core/simulation_orchestrator.py`.

### Gap G-HPR-005: Audience does not include historically-active users absent from trigger file

**Current:** `AudienceManager.resolve()` accepts only users in `trigger_df`.  
**Required:** After reconstruction, historically-active users not in `trigger_df` are injected into the audience.  
**Affected files:** `core/simulation_orchestrator.py`, `core/audience_manager.py`.

---

## SECTION 4 — ARCHITECTURE CHANGES

### 4.1 input_loader.load_historical_file() Changes

**Modified function:** `core/input_loader.load_historical_file()`

New step added after existing deduplication:

```python
# Step 4b (NEW): Parse extended schema columns if present
from utils.canonical_schema import (
    EXTERNAL_AD_NAME, EXTERNAL_JOURNEY_STEP,
    EXTERNAL_TRIGGER_NAME, EXTERNAL_COMPLETION_DATE,
    historical_file_has_extended_schema,
)

if historical_file_has_extended_schema(df):
    logger.info("%s: Extended historical schema detected; parsing journey fields.", file_path.name)

    # Journey_Step must be integer ≥ 1
    df[EXTERNAL_JOURNEY_STEP] = pd.to_numeric(
        df[EXTERNAL_JOURNEY_STEP], errors="coerce"
    ).astype("Int64")  # nullable int
    invalid_steps = df[EXTERNAL_JOURNEY_STEP].isna() | (df[EXTERNAL_JOURNEY_STEP] < 1)
    if invalid_steps.any():
        n_invalid = int(invalid_steps.sum())
        logger.warning(
            "%s: %d rows have invalid Journey_Step (null or < 1); these rows excluded.",
            file_path.name, n_invalid,
        )
        df = df[~invalid_steps].reset_index(drop=True)

    # Completion_Date: parse as date, allow null
    if EXTERNAL_COMPLETION_DATE in df.columns:
        df[EXTERNAL_COMPLETION_DATE] = pd.to_datetime(
            df[EXTERNAL_COMPLETION_DATE], errors="coerce"
        ).dt.date

    # Ad_Name: validate non-null for qualifying action rows
    qualifying_mask = df.apply(
        lambda r: r["Action"] in QUALIFYING_ACTIONS.get(r["Channel"], set()), axis=1
    )
    missing_ad_name = qualifying_mask & df[EXTERNAL_AD_NAME].isna()
    if missing_ad_name.any():
        logger.warning(
            "%s: %d qualifying-action rows have null Ad_Name; journey reconstruction may be incomplete.",
            file_path.name, int(missing_ad_name.sum()),
        )
else:
    logger.info(
        "%s: Basic 4-column historical schema; journey reconstruction not available.",
        file_path.name,
    )
```

### 4.2 HistoricalStateReconstructor — Implementation

**New file:** `core/historical_state_reconstructor.py`

```python
"""Pre-Stage 1 — Historical State Reconstruction.

Reconstructs UserState-compatible rows from an extended historical engagement
file. Only invoked when all four extended columns are present:
  Ad_Name, Journey_Step, Trigger_Name, Completion_Date.

This service is a pure function: given historical_df and ConfigRegistry, it
returns a DataFrame. It does not modify any global state.

References
----------
* CRIT-001 — Historical Journey Continuation
* CRIT-003 — Historical Audience Continuity
* CRIT-004 — Historical State Reconstruction
* CRIT-005 — Cooling Period from History
* HPR-001  — Historical Processing Remediation document
"""
from __future__ import annotations

from datetime import date, timedelta
import pandas as pd

from models.config_registry import ConfigRegistry
from models.enums import EligibilityStatus, JourneyStatus, BehaviorProfile
from models.user_state import UserState
from utils.canonical_schema import (
    EXTERNAL_USER_ID, EXTERNAL_DATE, EXTERNAL_ACTION,
    EXTERNAL_AD_NAME, EXTERNAL_JOURNEY_STEP,
    EXTERNAL_TRIGGER_NAME, EXTERNAL_COMPLETION_DATE,
)
from utils.constants import (
    DEFAULT_ENGAGEMENT_SCORE, DEFAULT_CHANNEL_AFFINITY, DEFAULT_CREATIVE_AFFINITY
)
from utils.logger import get_logger

_logger = get_logger(__name__)


class HistoricalStateReconstructor:
    """Reconstruct user state from extended historical engagement data.

    Args:
        config: ConfigRegistry for the campaign run.
    """

    def __init__(self, config: ConfigRegistry) -> None:
        self._config = config

    def reconstruct(
        self,
        historical_df: pd.DataFrame,
        as_of_date: date,
    ) -> pd.DataFrame:
        """Build UserState-compatible rows for each user in historical_df.

        Returns:
            DataFrame with one row per distinct User_ID. Columns match
            USER_STATE_REQUIRED_COLUMNS plus all journey fields.
            Empty DataFrame if historical_df is empty.
        """
        if historical_df.empty:
            return pd.DataFrame()

        cfg = self._config
        rows = []
        grouped = historical_df.groupby(EXTERNAL_USER_ID)

        for uid, user_df in grouped:
            user_df = user_df.sort_values(EXTERNAL_DATE, ascending=False)

            # Determine trigger
            trigger_name = (
                user_df[EXTERNAL_TRIGGER_NAME].dropna().iloc[0]
                if EXTERNAL_TRIGGER_NAME in user_df.columns and not user_df[EXTERNAL_TRIGGER_NAME].dropna().empty
                else None
            )
            trigger = cfg.get_trigger_by_name(trigger_name) if trigger_name else None
            effective_ads = (
                trigger.get_effective_ads(cfg.ads) if trigger else cfg.ads
            )
            ad_names = [a.ad_name for a in sorted(effective_ads, key=lambda x: x.ad_order)]

            # Check for journey completion
            if EXTERNAL_COMPLETION_DATE in user_df.columns:
                completed = user_df[user_df[EXTERNAL_COMPLETION_DATE].notna()]
            else:
                completed = pd.DataFrame()

            if not completed.empty:
                completion_date = completed[EXTERNAL_COMPLETION_DATE].max()
                if hasattr(completion_date, 'date'):
                    completion_date = completion_date.date()
                cooling_end = completion_date + timedelta(days=cfg.cooling_period_days)
                es = (
                    EligibilityStatus.RE_ENTRY.value
                    if as_of_date > cooling_end
                    else EligibilityStatus.COOLING.value
                )
                state = self._build_base_state(
                    uid, trigger_name, cfg.campaign_id, as_of_date, ad_names,
                    user_df,
                )
                state.update({
                    "eligibility_status": es,
                    "journey_status": JourneyStatus.COMPLETED.value,
                    "journey_completion_date": completion_date,
                    "cooling_period_end": cooling_end,
                    "current_ad": None,
                    "journey_step": None,
                    "days_in_ad": None,
                })
            else:
                # Mid-journey: use most recent Ad_Name engagement
                qualifying_df = user_df[
                    user_df[EXTERNAL_ACTION].isin({"Click", "Open"})
                ]
                if qualifying_df.empty:
                    qualifying_df = user_df  # fall back to any row

                most_recent = qualifying_df.iloc[0]
                current_ad = most_recent.get(EXTERNAL_AD_NAME)
                journey_step_raw = most_recent.get(EXTERNAL_JOURNEY_STEP)
                journey_step = int(journey_step_raw) if journey_step_raw is not None else 1

                eng_date = most_recent[EXTERNAL_DATE]
                if hasattr(eng_date, 'date'):
                    eng_date = eng_date.date()
                days_elapsed = (as_of_date - eng_date).days

                # Cap days_in_ad to prevent immediate advance
                ad_config = next(
                    (a for a in effective_ads if a.ad_name == current_ad), None
                )
                max_days = (ad_config.duration_days - 1) if ad_config else days_elapsed
                days_in_ad = min(days_elapsed, max_days)

                state = self._build_base_state(
                    uid, trigger_name, cfg.campaign_id, as_of_date, ad_names,
                    user_df,
                )
                state.update({
                    "eligibility_status": EligibilityStatus.ACTIVE.value,
                    "journey_status": JourneyStatus.ACTIVE.value,
                    "current_ad": current_ad,
                    "journey_step": journey_step,
                    "days_in_ad": days_in_ad,
                })

            rows.append(state)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        _logger.info(
            "HistoricalStateReconstructor: reconstructed %d users "
            "(%d active, %d cooling, %d re_entry)",
            len(df),
            int((df["journey_status"] == JourneyStatus.ACTIVE.value).sum()),
            int((df["eligibility_status"] == EligibilityStatus.COOLING.value).sum()),
            int((df["eligibility_status"] == EligibilityStatus.RE_ENTRY.value).sum()),
        )
        return df

    def _build_base_state(
        self,
        uid: str,
        trigger_name: str | None,
        campaign_id: str,
        as_of_date: date,
        ad_names: list[str],
        user_df: pd.DataFrame,
    ) -> dict:
        """Build the base state dict with fields derivable from any historical data."""
        qualifying = user_df[user_df[EXTERNAL_ACTION].isin({"Click", "Open"})]
        total_eng = len(qualifying)
        last_eng = None
        if not qualifying.empty:
            last_eng = qualifying[EXTERNAL_DATE].max()
            if hasattr(last_eng, 'date'):
                last_eng = last_eng.date()

        first_date = user_df[EXTERNAL_DATE].min()
        if hasattr(first_date, 'date'):
            first_date = first_date.date()

        return {
            "campaign_id": campaign_id,
            "user_id": str(uid),
            "trigger_name": trigger_name,
            "segment": None,
            "eligibility_status": EligibilityStatus.NEW.value,  # overridden by caller
            "journey_status": JourneyStatus.NOT_STARTED.value,  # overridden by caller
            "journey_start_date": first_date,
            "current_ad": None,
            "days_in_ad": None,
            "journey_step": None,
            "ad_click_received": False,
            "journey_completion_date": None,
            "cooling_period_end": None,
            "cooling_override_applied": False,
            "behavior_profile": BehaviorProfile.MODERATE.value,
            "engagement_score": DEFAULT_ENGAGEMENT_SCORE,
            "channel_affinity_display": DEFAULT_CHANNEL_AFFINITY,
            "channel_affinity_email": DEFAULT_CHANNEL_AFFINITY,
            "channel_affinity_whatsapp": DEFAULT_CHANNEL_AFFINITY,
            "last_engagement_date": last_eng,
            "engagement_cooldown_end": None,
            "weekly_impressions": 0,
            "weekly_clicks": 0,
            "weekly_opens": 0,
            "weekly_engagements": 0,
            "total_lifetime_engagements": total_eng,
            "last_reached_date": last_eng,
            "run_count": 0,
            "state_as_of_date": as_of_date,
            "trigger_history": trigger_name,
            "first_trigger_name": trigger_name,
            "first_trigger_date": first_date,
            "total_trigger_appearances": 1,
            "channel": None,
            "vendor": None,
            "historical_engaged": True,
            "is_valid": True,
            "trigger_ads_key": None,
            "creative_affinities": {ad: DEFAULT_CREATIVE_AFFINITY for ad in ad_names},
        }


__all__ = ["HistoricalStateReconstructor"]
```

### 4.3 Audience Augmentation — _augment_trigger_df

A new helper in `simulation_orchestrator.py`:

```python
def _augment_trigger_df(
    trigger_df: pd.DataFrame,
    hist_active_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add historically-active users absent from trigger_df to the trigger DataFrame.

    Synthesizes trigger-file rows for historically-active users. Required columns:
    Campaign_ID, User_ID, Trigger_Name, Segment. Values sourced from reconstructed state.

    Args:
        trigger_df: Original trigger DataFrame.
        hist_active_df: Rows from reconstructed_state_df where journey_status=Active
                        AND user_id not in trigger_df.

    Returns:
        Extended trigger_df with synthetic rows appended.
    """
    synth_rows = pd.DataFrame({
        "Campaign_ID": hist_active_df["campaign_id"].values,
        "User_ID":     hist_active_df["user_id"].values,
        "Trigger_Name": hist_active_df["trigger_name"].fillna("Historical").values,
        "Segment":     hist_active_df["segment"].fillna("Historical").values,
        "Trigger_Date": pd.Timestamp("today").date(),
        "_synthetic_historical": True,  # flag for downstream identification
    })
    return pd.concat([trigger_df, synth_rows], ignore_index=True)
```

---

## SECTION 5 — DATA MODEL CHANGES

See `DATA_MODEL_REMEDIATION.md` Section 2.4 for the extended historical schema table.

Key data model constraints for the extended schema:

1. `Journey_Step` must be a positive integer (≥ 1). Rows with `Journey_Step < 1` or null are excluded from reconstruction with a WARNING log.
2. `Ad_Name` values must be valid ad names from the campaign's configured ads. Unknown ad names are accepted (WARNING logged) but the user is reconstructed at `journey_step=1` as a fallback.
3. `Completion_Date` must be ≤ `Date` for the same row (a completion cannot post-date the engagement record). Violations are corrected by taking the maximum of the two.
4. `Trigger_Name` values need not match configured trigger names — unrecognized trigger names result in use of the campaign-level `ConfigRegistry.ads` as the fallback journey.

---

## SECTION 6 — USER STATE CHANGES

`HistoricalStateReconstructor` writes `historical_engaged=True` for all reconstructed users. This is consistent with the ARCH-RISK-003 behavior: users found in historical data are already engaged and reduce TCC capacity.

The reconstructed `total_lifetime_engagements` field is populated from the count of qualifying actions in the historical file. This seeds the engagement counter correctly for users who had prior engagement history.

---

## SECTION 7 — UI CHANGES

### Upload Page — Extended Schema Guidance

When a historical file with extended schema is detected, display additional confirmation:

```python
if hist_ok:
    from utils.canonical_schema import historical_file_has_extended_schema
    if historical_file_has_extended_schema(get_historical_df()):
        st.success(
            "✅ Historical file loaded with extended schema — "
            "**journey reconstruction enabled**."
        )
    else:
        st.info(
            "ℹ️ Historical file loaded (basic schema). "
            "Journey reconstruction is not available. "
            "To enable journey reconstruction, include columns: "
            "Ad_Name, Journey_Step, Trigger_Name, Completion_Date."
        )
```

### Results Page — Reconstruction Summary

`SimulationResult` must carry a new optional field `reconstruction_summary: dict | None` populated by the orchestrator when reconstruction runs. The results page displays this summary.

---

## SECTION 8 — VALIDATION CHANGES

### Extended Schema Validation in input_loader

Three new validation checks when extended schema is detected:

1. `Journey_Step` must be integer ≥ 1 (hard gate: invalid rows excluded).
2. `Ad_Name` should be non-null for qualifying action rows (soft warning; nulls permitted but logged).
3. `Completion_Date` should be ≤ `Date` for the same row (soft warning; corrected in place).

### VR-H001: Historical Reconstruction Consistency (Advisory)

After simulation, check that users with `historical_engaged=True` and reconstructed `journey_status=Active` appear in `events_df` on their reconstructed `current_ad`. If they do not appear (possible if TCC blocked them), emit advisory VR-H001.

---

## SECTION 9 — MIGRATION STRATEGY

### 9.1 Existing Historical Files (4 columns)

Fully backward compatible. `historical_file_has_extended_schema()` returns False; reconstruction is skipped; capacity counting behavior unchanged.

### 9.2 Generating Extended Historical Files

For existing customers with data in 4-column format: a migration utility script `scripts/migrate_historical_file.py` must be written. It takes an existing 4-column historical file plus a campaign config and attempts to backfill `Ad_Name` and `Journey_Step` from engagement patterns (if ad duration/timing is known). `Trigger_Name` and `Completion_Date` require manual backfill or are left null.

This migration utility is out-of-scope for the remediation waves but must be documented in `PROJECT_RELEASE_PACKAGE.md`.

### 9.3 Multi-Run Chain with Historical Reconstruction

In a multi-run chain (Run1 → Run2 → Run3), `previous_state_df` from Run1 is preferred over `reconstructed_state_df` from the historical file (see three-way merge priority in `USER_STATE_REMEDIATION.md`). The historical file is only used for users absent from `previous_state_df`. This means Run2 and later runs should rely on `previous_state_df` for state continuity; historical reconstruction is primarily useful for the first run of a new simulation.

---

## SECTION 10 — BACKWARD COMPATIBILITY ASSESSMENT

| Change | Backward Compatible | Notes |
|--------|--------------------|-|
| Extended historical schema | YES | New columns optional; 4-col files load unchanged |
| `load_historical_file` extended parsing | YES | Only parses new columns when present |
| `HistoricalStateReconstructor` | YES | Only invoked when extended schema present |
| Audience augmentation | YES | Only runs when reconstruction produces Active users |
| `reconstruction_summary` in SimulationResult | YES | Optional field; None when not used |

---

## SECTION 11 — PERFORMANCE IMPACT

| Change | Scale | Impact |
|--------|-------|--------|
| `load_historical_file` extended parsing | O(H) | ~1ms overhead per 100k rows for date parsing |
| `HistoricalStateReconstructor.reconstruct()` | O(H) groupby | ~50ms at 100k historical rows (vectorized groupby) |
| Audience augmentation | O(A) | A = active historical users; typically small |
| Advisory validation rule VR-H001 | O(E + U) | E = events, U = users; same order as existing rules |

All impacts are pre-Stage 1 and do not affect the critical path (EngagementGenerator daily loop). Stage 16 SLAs unaffected.

---

## SECTION 12 — RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Reconstruction wrong for users with multiple journeys (re-entry history) | Medium | High | Use most recent Completion_Date; reconstruct from last journey only |
| days_in_ad capped incorrectly at (duration-1) | Low | Medium | Test: user on last day advances correctly on Day 1 of simulation |
| Historically-active users injected with wrong Trigger_Name | Medium | Medium | `_augment_trigger_df` uses "Historical" as fallback trigger |
| Extended schema detected when partial columns present | Low | Medium | `has_extended_schema` requires ALL 4 columns; partial presence = False |
| Journey step mismatch between historical and current config | Medium | Medium | Log warning; cap journey_step at len(effective_ads); start at last valid step |

---

## SECTION 13 — ACCEPTANCE CRITERIA

1. `load_historical_file()` successfully loads an 8-column historical CSV; `Journey_Step` column dtype is int; `Completion_Date` column dtype is date (nullable).

2. `load_historical_file()` successfully loads a 4-column historical CSV; no error; extended columns absent from returned DataFrame.

3. `HistoricalStateReconstructor.reconstruct()` with a user having their last qualifying engagement on Ad_B (step 2) 5 days ago produces `current_ad="Ad_B"`, `journey_step=2`, `days_in_ad=min(5, ad.duration_days-1)`.

4. `HistoricalStateReconstructor.reconstruct()` with a user having `Completion_Date=D` and `cooling_period_days=14`, `as_of_date=D+10`, produces `eligibility_status=COOLING`, `cooling_period_end=D+14`.

5. `HistoricalStateReconstructor.reconstruct()` with `as_of_date=D+20` produces `eligibility_status=RE_ENTRY`.

6. A simulation run with an 8-column historical file and 10 historically-active users not in `trigger_df` produces `events_df` containing records for those 10 users.

7. A simulation run with a 4-column historical file produces identical results to the current baseline (capacity counting unchanged, no reconstruction attempted).

8. `SimulationResult.reconstruction_summary` is populated when extended schema is used.

---

## SECTION 14 — DEFINITION OF DONE

- [ ] `utils/canonical_schema.py` defines all 8 historical column constants and `historical_file_has_extended_schema()`.
- [ ] `core/input_loader.load_historical_file()` parses extended columns when present.
- [ ] `core/historical_state_reconstructor.py` implemented and tested.
- [ ] `core/simulation_orchestrator.py` invokes `HistoricalStateReconstructor` pre-Stage 1.
- [ ] `core/simulation_orchestrator.py` augments trigger audience with historically-active users.
- [ ] `SimulationResult` has `reconstruction_summary: dict | None` field.
- [ ] `upload_page.py` shows extended schema detection message.
- [ ] `results_page.py` shows reconstruction summary when available.
- [ ] All acceptance criteria tests pass.
- [ ] Full regression suite passes with 0 failures.

---

## SECTION 15 — REGRESSION TEST REQUIREMENTS

### New Test Files

**`tests/test_core/test_historical_state_reconstructor.py`** — full unit coverage (see `USER_STATE_REMEDIATION.md` Section 15).

**`tests/test_core/test_input_loader.py` — additions**
- `test_load_historical_file_extended_schema_journey_step_int`
- `test_load_historical_file_extended_schema_completion_date_parsed`
- `test_load_historical_file_basic_schema_no_extended_columns`
- `test_load_historical_file_invalid_journey_step_excluded`
- `test_load_historical_file_partial_extended_schema_treated_as_basic`

**`tests/test_e2e/test_historical_window_certification.py` — additions**
- `test_hw_011_historically_active_users_continue_journey`
- `test_hw_012_historically_completed_users_in_cooling`
- `test_hw_013_historically_completed_users_re_entry`
- `test_hw_014_4col_historical_file_unchanged_behavior`
- `test_hw_015_historical_users_not_in_trigger_injected`

---

*Document: HPR-001 | HISTORICAL_PROCESSING_REMEDIATION.md | v1.0 | 2026-06-23*
