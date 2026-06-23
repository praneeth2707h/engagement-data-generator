# DATA MODEL REMEDIATION
## Engagement Data Generator — Data Model Changes

**Document ID:** DMR-001  
**Version:** 1.0  
**Date:** 2026-06-23  
**Parent:** ARCHITECTURE_REMEDIATION_PACKAGE.md (ARP-001)  
**Defects Addressed:** HIGH-001, HIGH-003, HIGH-005, CRIT-002 (partial), CRIT-008 (partial)

---

## SECTION 1 — CURRENT STATE ASSESSMENT

### 1.1 Column Name Definitions — Scattered and Inconsistent

Column names are defined independently in at least four locations:

- `upload_page.py`: `_TRIGGER_REQUIRED_COLS = {"Campaign_ID", "User_ID", "Trigger_Name", "Segment"}` and `_HISTORICAL_REQUIRED_COLS = {"user_id", "campaign_id"}` (lowercase — wrong)
- `schema_validator.py`: `TRIGGER_FILE_REQUIRED_COLUMNS = ["User_ID", "Trigger_Name", "Trigger_Date", "Segment"]` and `HISTORICAL_FILE_REQUIRED_COLUMNS = ["User_ID", "Date", "Action", "Channel"]`
- `simulation_orchestrator.py`: `_TRIGGER_REQUIRED_COLS: frozenset[str] = frozenset({"Campaign_ID", "User_ID", "Trigger_Name", "Segment"})`
- `engagement_generator.py`: `_STATE_REQUIRED_COLS: tuple[str, ...]` defined inline

None of these are derived from a shared authority. There is no canonical mapping between external file column names (`Campaign_ID`) and internal DataFrame column names (`campaign_id`).

### 1.2 TriggerConfig — No Journey Ownership

```python
@dataclass(frozen=True)
class TriggerConfig:
    trigger_name: str
    priority: int
    engagement_rate_target: float
    distribution_pct: float = 0.0
```

`TriggerConfig` owns no ad sequence. The global `ConfigRegistry.ads: tuple[AdConfig, ...]` serves all triggers identically. There is no way to configure Trigger_A to use [Ad_A1, Ad_A2] while Trigger_B uses [Ad_B1].

### 1.3 UserState — Missing Journey Metadata Fields

`UserState` tracks `current_ad: str | None` and `days_in_ad: int | None` but not the 1-based journey step position. Journey step must currently be computed by looking up `current_ad` in `config.get_ad_by_name()` — this is expensive and unavailable in contexts where `config` is not present (e.g., historical reconstruction).

### 1.4 Historical File Schema — 4 Columns Only

`HISTORICAL_FILE_REQUIRED_COLUMNS = ["User_ID", "Date", "Action", "Channel"]`

This schema cannot support journey reconstruction. There is no way to determine from this data: which ad a user was on, what step they were on, which trigger they belong to, or whether they completed the journey.

### 1.5 User_ID Type Safety Gap

`upload_page.py`:
```python
return pd.read_csv(uploaded_file)           # User_ID may be int64
return pd.read_excel(uploaded_file)         # User_ID may be int64
```

`input_loader.py`:
```python
df = pd.read_csv(file_path, dtype=str)      # User_ID always str
df = pd.read_excel(file_path, dtype=str)    # User_ID always str
```

The upload page reads without `dtype=str`, so numeric User_IDs (1001, 1002, ...) are loaded as `int64`. All downstream code expects `str`. The MD5 seed computation `hashlib.md5(user_id.encode())` will fail with `AttributeError: 'int' object has no attribute 'encode'`.

---

## SECTION 2 — DESIRED STATE

### 2.1 CanonicalSchema — Single Source of Truth

A new module `utils/canonical_schema.py` defines every column name used anywhere in the system, with both the external representation (as it appears in user-supplied files and Excel output) and the internal representation (as it appears in simulation DataFrames).

The module exposes:
- `EXTERNAL_*` constants: external file column names
- `INTERNAL_*` constants: internal DataFrame column names  
- `TRIGGER_FILE_REQUIRED_COLUMNS`: authoritative list for trigger file validation
- `HISTORICAL_FILE_REQUIRED_COLUMNS`: authoritative list for historical file validation (4-column + 4-column extended)
- `to_internal(col: str) -> str`: maps external → internal
- `to_external(col: str) -> str`: maps internal → external

### 2.2 TriggerConfig — Trigger-Owned Ad Sequence

```python
@dataclass(frozen=True)
class TriggerConfig:
    trigger_name: str
    priority: int
    engagement_rate_target: float
    distribution_pct: float = 0.0
    ads: tuple[AdConfig, ...] | None = None   # NEW — None = use ConfigRegistry.ads
```

When `ads` is not None, it defines the complete, ordered ad journey for all users entering via this trigger. When `ads is None`, `ConfigRegistry.ads` is used as the fallback.

### 2.3 UserState — journey_step Field

```python
@dataclass
class UserState:
    ...
    journey_step: int | None = None          # NEW — 1-based current ad order position
    trigger_ads_key: str | None = None       # NEW — MD5 of trigger's ads tuple for change detection
    cooling_override_applied: bool = False   # NEW — audit: True if CoolingOverrideService set RE_ENTRY
```

### 2.4 Extended Historical Schema

The historical file gains four optional columns. Their presence enables journey reconstruction; their absence is handled gracefully.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| User_ID | str | YES | User identifier |
| Date | date | YES | Engagement date |
| Action | str | YES | Click, Open, Impression, Sent |
| Channel | str | YES | Email, Display, WhatsApp, etc. |
| Ad_Name | str | NO* | Ad name from ConfigRegistry.ads |
| Journey_Step | int | NO* | 1-based position of Ad_Name in journey |
| Trigger_Name | str | NO* | Trigger that drove this engagement |
| Completion_Date | date | NO* | Date journey was completed (terminal ad); null if not yet complete |

*Required for journey reconstruction (CRIT-001/004/005). Optional for backward compatibility with legacy 4-column files.

### 2.5 User_ID Type Safety

All upload paths must coerce User_ID to `str` before the DataFrame enters any pipeline stage. This is a hard contract: `str(user_id)` is called at the earliest possible point in the data flow.

---

## SECTION 3 — GAP ANALYSIS

### Gap G-DM-001: No canonical column name authority

**Current:** 4 independent definitions, partially contradicting each other.  
**Required:** Single `CanonicalSchema` module imported by all others.  
**Files affected:** `utils/canonical_schema.py` (NEW), `upload_page.py`, `schema_validator.py`, `simulation_orchestrator.py`, `engagement_generator.py`, `user_state_manager.py`, `excel_exporter.py`.

### Gap G-DM-002: TriggerConfig owns no ads

**Current:** `TriggerConfig` has 4 fields; no `ads` field.  
**Required:** `ads: tuple[AdConfig, ...] | None = None` field added.  
**Files affected:** `models/trigger_config.py`, `core/config_loader.py` (must parse trigger-level ads), `ui/campaign_page.py` (must expose per-trigger ad UI).

### Gap G-DM-003: UserState missing journey_step

**Current:** Journey step derivable only via config lookup.  
**Required:** `journey_step: int | None` stored directly on UserState.  
**Files affected:** `models/user_state.py`, `core/journey_engine.py` (must write journey_step on advance), `core/user_state_manager.py` (must reconcile).

### Gap G-DM-004: Historical schema insufficient for reconstruction

**Current:** 4 columns: User_ID, Date, Action, Channel.  
**Required:** 8 columns: + Ad_Name, Journey_Step, Trigger_Name, Completion_Date.  
**Files affected:** `utils/schema_validator.py`, `core/input_loader.py`, `core/historical_state_reconstructor.py` (NEW).

### Gap G-DM-005: User_ID type unsafe in upload path

**Current:** `pd.read_csv(uploaded_file)` with no `dtype` — numeric User_IDs become int64.  
**Required:** `pd.read_csv(uploaded_file, dtype=str)` everywhere.  
**Files affected:** `ui/upload_page.py`.

---

## SECTION 4 — ARCHITECTURE CHANGES

### 4.1 CanonicalSchema Module

**New file:** `utils/canonical_schema.py`

Full column registry:

```python
# External column names (user-facing, Title_Case)
EXTERNAL_CAMPAIGN_ID   = "Campaign_ID"
EXTERNAL_USER_ID       = "User_ID"
EXTERNAL_TRIGGER_NAME  = "Trigger_Name"
EXTERNAL_TRIGGER_DATE  = "Trigger_Date"
EXTERNAL_SEGMENT       = "Segment"
EXTERNAL_DATE          = "Date"
EXTERNAL_ACTION        = "Action"
EXTERNAL_CHANNEL       = "Channel"
EXTERNAL_AD_NAME       = "Ad_Name"
EXTERNAL_JOURNEY_STEP  = "Journey_Step"
EXTERNAL_COMPLETION_DATE = "Completion_Date"

# Internal column names (simulation DataFrames, snake_case)
INTERNAL_CAMPAIGN_ID   = "campaign_id"
INTERNAL_USER_ID       = "user_id"
INTERNAL_TRIGGER_NAME  = "trigger_name"
INTERNAL_SEGMENT       = "segment"
INTERNAL_JOURNEY_STEP  = "journey_step"
...

# Authoritative required column lists
TRIGGER_FILE_REQUIRED_COLUMNS: list[str] = [
    EXTERNAL_USER_ID,
    EXTERNAL_TRIGGER_NAME,
    EXTERNAL_TRIGGER_DATE,
    EXTERNAL_SEGMENT,
]

HISTORICAL_FILE_REQUIRED_COLUMNS: list[str] = [
    EXTERNAL_USER_ID,
    EXTERNAL_DATE,
    EXTERNAL_ACTION,
    EXTERNAL_CHANNEL,
]

HISTORICAL_FILE_EXTENDED_COLUMNS: list[str] = [
    EXTERNAL_AD_NAME,
    EXTERNAL_JOURNEY_STEP,
    EXTERNAL_TRIGGER_NAME,
    EXTERNAL_COMPLETION_DATE,
]

def historical_file_has_extended_schema(df: pd.DataFrame) -> bool:
    """Return True if all 4 extended columns are present."""
    return all(c in df.columns for c in HISTORICAL_FILE_EXTENDED_COLUMNS)
```

### 4.2 TriggerConfig Changes

**Modified file:** `models/trigger_config.py`

```python
from models.ad_config import AdConfig

@dataclass(frozen=True)
class TriggerConfig:
    trigger_name: str
    priority: int
    engagement_rate_target: float
    distribution_pct: float = 0.0
    ads: tuple[AdConfig, ...] | None = None

    def __post_init__(self) -> None:
        # existing validations unchanged
        ...
        # NEW: if ads provided, must be non-empty
        if self.ads is not None and len(self.ads) == 0:
            raise ValueError(
                f"TriggerConfig '{self.trigger_name}': ads must be non-empty if provided."
            )

    def get_effective_ads(
        self, fallback: tuple[AdConfig, ...]
    ) -> tuple[AdConfig, ...]:
        """Return trigger-scoped ads if defined, else fallback (ConfigRegistry.ads)."""
        if self.ads is not None:
            return self.ads
        return fallback

    def ads_fingerprint(self) -> str:
        """Return MD5 hex of the sorted ad names for change detection."""
        import hashlib
        names = "|".join(sorted(a.ad_name for a in (self.ads or ())))
        return hashlib.md5(names.encode()).hexdigest()[:8]
```

### 4.3 UserState Changes

**Modified file:** `models/user_state.py`

Three new fields added with defaults:

```python
@dataclass
class UserState:
    ...
    journey_step: int | None = None
    """1-based position of current_ad in the trigger's ad sequence.
    None when journey_status != Active. Set by JourneyEngine on advance.
    """

    trigger_ads_key: str | None = None
    """8-char MD5 fingerprint of the trigger's ad sequence at journey start.
    Used to detect ad sequence changes between simulation runs.
    """

    cooling_override_applied: bool = False
    """True if CoolingOverrideService forced this user into RE_ENTRY.
    Audit field; not used in simulation logic.
    """
```

`UserState.new()` must initialize all three to `None`, `None`, `False` respectively.

### 4.4 JourneyEngine Changes for journey_step

`JourneyEngine._start_journeys()` must set `journey_step = 1` when placing a user on the first ad.

`JourneyEngine._advance_active()` — when advancing to next ad, must set `journey_step` to the new ad's order.

`JourneyEngine._complete_journeys()` — must set `journey_step = None` on completion.

This requires `journey_step` to be present in `state_df` and in `_STATE_REQUIRED_COLS`.

---

## SECTION 5 — DATA MODEL CHANGES (DETAILED)

### 5.1 UserState Field Inventory (Complete)

| Field | Type | New/Modified | Notes |
|-------|------|-------------|-------|
| campaign_id | str | — | unchanged |
| user_id | str | MUST BE STR | HIGH-003: enforce str in upload |
| trigger_name | str\|None | — | unchanged |
| segment | str\|None | — | unchanged |
| eligibility_status | str | — | unchanged |
| journey_status | str | — | unchanged |
| journey_start_date | date\|None | — | unchanged |
| current_ad | str\|None | — | unchanged |
| days_in_ad | int\|None | — | unchanged |
| journey_step | int\|None | **NEW** | 1-based; None when not Active |
| trigger_ads_key | str\|None | **NEW** | 8-char fingerprint |
| ad_click_received | bool | — | unchanged |
| journey_completion_date | date\|None | — | unchanged |
| cooling_period_end | date\|None | — | unchanged |
| cooling_override_applied | bool | **NEW** | audit flag; default False |
| behavior_profile | str | — | unchanged |
| engagement_score | float | — | unchanged |
| channel_affinity_display | float | — | unchanged |
| channel_affinity_email | float | — | unchanged |
| channel_affinity_whatsapp | float | — | unchanged |
| last_engagement_date | date\|None | — | unchanged |
| engagement_cooldown_end | date\|None | — | unchanged |
| weekly_impressions | int | — | unchanged |
| weekly_clicks | int | — | unchanged |
| weekly_opens | int | — | unchanged |
| weekly_engagements | int | — | unchanged |
| total_lifetime_engagements | int | — | unchanged |
| last_reached_date | date\|None | — | unchanged |
| run_count | int | — | unchanged |
| state_as_of_date | date | — | unchanged |
| trigger_history | str\|None | — | unchanged |
| first_trigger_name | str\|None | — | unchanged |
| first_trigger_date | date\|None | — | unchanged |
| total_trigger_appearances | int | — | unchanged |
| channel | str\|None | — | unchanged |
| vendor | str\|None | — | unchanged |
| historical_engaged | bool | — | unchanged |
| is_valid | bool | — | unchanged |
| creative_affinities | dict[str,float] | — | unchanged |

### 5.2 AdConfig — No Changes

`AdConfig` requires no changes. It is used as-is in `TriggerConfig.ads`.

### 5.3 ConfigRegistry — Minor Change

`ConfigRegistry.ads` remains. It is now the campaign-level default. When a `TriggerConfig` has its own `ads`, those take precedence for that trigger. `ConfigRegistry.__post_init__` validation: if any trigger has `ads is not None`, those ads are validated for internal ordering consistency.

```python
# NEW in ConfigRegistry.__post_init__:
for t in self.triggers:
    effective_ads = t.ads if t.ads is not None else self.ads
    orders = [a.ad_order for a in effective_ads]
    if sorted(orders) != list(range(1, len(orders)+1)):
        raise ConfigError(
            f"TriggerConfig '{t.trigger_name}' ads have non-consecutive "
            f"ad_order values: {sorted(orders)}"
        )
```

---

## SECTION 6 — USER STATE CHANGES

See `USER_STATE_REMEDIATION.md` for complete specification. Summary relevant to data model:

`USER_STATE_REQUIRED_COLUMNS` in `schema_validator.py` must be updated:
```python
USER_STATE_REQUIRED_COLUMNS: list[str] = [
    "campaign_id", "user_id", "eligibility_status", "journey_status",
    "behavior_profile", "engagement_score", "state_as_of_date",
    "historical_engaged", "is_valid",
    "journey_step",           # NEW
    "trigger_ads_key",        # NEW
    "cooling_override_applied",  # NEW
]
```

---

## SECTION 7 — UI CHANGES

### Upload Page

```python
# BEFORE (HIGH-003 bug):
def _read_upload(uploaded_file) -> pd.DataFrame | None:
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)

# AFTER (HIGH-003 fix):
def _read_upload(uploaded_file) -> pd.DataFrame | None:
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file, dtype=str)
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file, dtype=str)
```

Additionally:

```python
# BEFORE (HIGH-002 bug):
_TRIGGER_REQUIRED_COLS = {"Campaign_ID", "User_ID", "Trigger_Name", "Segment"}
_HISTORICAL_REQUIRED_COLS = {"user_id", "campaign_id"}

# AFTER (HIGH-002 fix):
from utils.canonical_schema import (
    TRIGGER_FILE_REQUIRED_COLUMNS,
    HISTORICAL_FILE_REQUIRED_COLUMNS,
)
# Use these directly — no local definitions
```

### Campaign Page — Per-Trigger Ad Sequence UI

See `TRIGGER_JOURNEY_REMEDIATION.md` Section 7 for full UI specification. The campaign page must allow per-trigger ad sequences. The config dict schema is extended:

```python
# Per-trigger ads (optional):
cfg["triggers"][i]["ads"] = [
    {"ad_name": "...", "ad_order": 1, "duration_days": 7, ...},
    ...
]
# None = use campaign-level ads
```

---

## SECTION 8 — VALIDATION CHANGES

### Schema Validation for Extended Historical File

`input_loader.load_historical_file()` must:
1. Load the file.
2. Check for 4 required base columns (unchanged).
3. Call `CanonicalSchema.historical_file_has_extended_schema(df)`.
4. If extended columns present: validate `Journey_Step` is integer ≥ 1, `Ad_Name` is non-null for rows with qualifying actions, `Completion_Date` is parseable as date or null.
5. If extended columns absent: log INFO "Historical file lacks extended schema; journey reconstruction disabled."

### TriggerConfig Validation

`TriggerConfig.__post_init__` must validate that when `ads` is not None, all `ad_order` values form a consecutive sequence starting at 1.

---

## SECTION 9 — MIGRATION STRATEGY

### 9.1 CanonicalSchema Rollout

Step 1: Create `utils/canonical_schema.py` with all constants.  
Step 2: Update `schema_validator.py` to import from `CanonicalSchema` — no logic change, only import change.  
Step 3: Update `simulation_orchestrator.py` `_TRIGGER_REQUIRED_COLS` to use `CanonicalSchema`.  
Step 4: Update `upload_page.py` validation constants to use `CanonicalSchema`.  
Step 5: Update all other modules that define column names as local string literals.  
Step 6: Run `grep -r '"Campaign_ID"\|"User_ID"\|"Trigger_Name"' --include="*.py"` to confirm no remaining local definitions outside `canonical_schema.py`.

### 9.2 TriggerConfig ads Field

The `ads = None` default means no existing `TriggerConfig` construction site needs modification. The `config_loader.py` must be updated to optionally parse trigger-level ads from JSON/dict config. The campaign page UI stores trigger-level ads in `cfg["triggers"][i]["ads"]` — `config_loader.py` must read this when present.

### 9.3 UserState New Fields Migration

`UserStateManager._reconcile_user_state_columns()` (already exists for `creative_affinities`) must be extended to fill missing `journey_step`, `trigger_ads_key`, `cooling_override_applied` columns from `previous_state_df` with defaults when those columns are absent. This handles the case where a V1 state_df is passed as `previous_state_df` into a V2 simulation run.

---

## SECTION 10 — BACKWARD COMPATIBILITY ASSESSMENT

| Change | Backward Compatible | Notes |
|--------|------|-------|
| `CanonicalSchema` module (new) | YES | Pure addition; existing code unchanged until imports updated |
| `TriggerConfig.ads = None` | YES | Default None; all existing TriggerConfig instances unaffected |
| `UserState.journey_step = None` | YES | Default None; existing state DataFrames get None fill |
| `UserState.trigger_ads_key = None` | YES | Default None |
| `UserState.cooling_override_applied = False` | YES | Default False |
| Extended historical schema | YES | New columns optional; existing 4-col files unchanged |
| `upload_page.py dtype=str` | BREAKING | Int User_IDs become str; test fixtures with int User_IDs must be updated |

---

## SECTION 11 — PERFORMANCE IMPACT

| Change | Impact | Notes |
|--------|--------|-------|
| `journey_step` column in state_df | +1 int column per user row | ~8 bytes/user; negligible at 100k |
| `trigger_ads_key` column in state_df | +1 str column per user row | ~10 bytes/user; negligible |
| `cooling_override_applied` column | +1 bool column per user row | ~1 byte/user; negligible |
| `CanonicalSchema` imports | Zero runtime cost | Module-level constants |
| `TriggerConfig.get_effective_ads()` | O(1) per call | Single None check |
| Extended historical file parsing | +O(H) for 4 extra columns | Negligible vs existing IO cost |

---

## SECTION 12 — RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| `CanonicalSchema` rollout introduces import cycles | Low | Medium | `canonical_schema.py` must import nothing from the project (only stdlib) |
| `TriggerConfig.ads` order validation too strict | Low | Medium | Allow non-consecutive orders with WARNING (not ERROR) initially |
| `dtype=str` breaks existing unit test fixtures | High | Low | Systematic find-and-replace in conftest.py; create helper `_str_uid(n)` |
| `journey_step` not updated by JourneyEngine — stale value | Medium | Medium | Add assertion in tests: `journey_step == config.get_ad_by_name(current_ad).ad_order` |
| Extended historical schema partially populated | Medium | Low | Defensive loading: treat all 4 extended cols as optional individually |

---

## SECTION 13 — ACCEPTANCE CRITERIA

1. `python -c "from utils.canonical_schema import TRIGGER_FILE_REQUIRED_COLUMNS; print(TRIGGER_FILE_REQUIRED_COLUMNS)"` succeeds with no import errors.

2. `grep -r '"Campaign_ID"\|"User_ID"\|"Trigger_Name"\|"Trigger_Date"' --include="*.py" engagement_data_generator/` returns results only from `canonical_schema.py` and test fixtures; no production module defines column names as local string literals.

3. `TriggerConfig(trigger_name="T", priority=1, engagement_rate_target=0.2, ads=(AdConfig(...),))` succeeds; `.get_effective_ads(fallback)` returns the trigger's own ads.

4. `UserState.new(campaign_id="C", user_id="U1", state_as_of_date=date.today(), ad_names=[])` has `.journey_step is None`, `.trigger_ads_key is None`, `.cooling_override_applied == False`.

5. Uploading a CSV with `User_ID` column containing `[1001, 1002, 1003]` via `upload_page._read_upload()` produces a DataFrame where `df["User_ID"].dtype == object` (str).

6. Loading a historical file with 8 columns (including `Ad_Name`, `Journey_Step`, `Trigger_Name`, `Completion_Date`) succeeds and `CanonicalSchema.historical_file_has_extended_schema(df) == True`.

7. Loading a historical file with only 4 base columns succeeds with no errors; `historical_file_has_extended_schema(df) == False`.

---

## SECTION 14 — DEFINITION OF DONE

- [ ] `utils/canonical_schema.py` created with all constants and helper functions.
- [ ] `schema_validator.py` imports all column lists from `CanonicalSchema`; no local definitions remain.
- [ ] `simulation_orchestrator.py` imports `_TRIGGER_REQUIRED_COLS` from `CanonicalSchema`.
- [ ] `upload_page.py` imports required-column lists from `CanonicalSchema`; all reads use `dtype=str`.
- [ ] `models/trigger_config.py` has `ads: tuple[AdConfig, ...] | None = None` field with validation.
- [ ] `models/user_state.py` has `journey_step`, `trigger_ads_key`, `cooling_override_applied` fields.
- [ ] `models/user_state.py` `UserState.new()` initializes all three new fields.
- [ ] `core/journey_engine.py` writes `journey_step` on start, advance, and completion.
- [ ] `utils/schema_validator.py` `USER_STATE_REQUIRED_COLUMNS` includes the three new fields.
- [ ] All new fields reconciled in `UserStateManager._reconcile_user_state_columns()`.
- [ ] `tests/test_utils/test_canonical_schema.py` passes.
- [ ] Full regression suite passes with 0 failures after Wave 1 changes.

---

## SECTION 15 — REGRESSION TEST REQUIREMENTS

### New Tests Required

**`tests/test_utils/test_canonical_schema.py`**
- `test_all_external_constants_title_case`: all EXTERNAL_* constants are Title_Case.
- `test_all_internal_constants_snake_case`: all INTERNAL_* constants are snake_case.
- `test_trigger_required_columns_match_schema_validator`: `TRIGGER_FILE_REQUIRED_COLUMNS` matches what `schema_validator.py` uses.
- `test_historical_required_columns_match_schema_validator`: same for historical.
- `test_has_extended_schema_true`: returns True when all 4 extended columns present.
- `test_has_extended_schema_false_missing_one`: returns False when any extended column absent.
- `test_no_import_cycles`: importing `canonical_schema` from a fresh Python context raises no ImportError.

**`tests/test_models/test_trigger_config.py` — additions**
- `test_trigger_config_no_ads_default_none`: `TriggerConfig(...).ads is None`.
- `test_trigger_config_with_ads`: construction with non-empty ads tuple succeeds.
- `test_trigger_config_empty_ads_raises`: `ads=()` raises ValueError.
- `test_get_effective_ads_uses_trigger_ads_when_set`: returns trigger ads, not fallback.
- `test_get_effective_ads_uses_fallback_when_none`: returns fallback when ads=None.

**`tests/test_models/test_user_state.py` — additions**
- `test_user_state_new_journey_step_none`.
- `test_user_state_new_trigger_ads_key_none`.
- `test_user_state_new_cooling_override_applied_false`.

**`tests/test_ui/test_smoke.py` — additions**
- `test_read_upload_csv_numeric_user_id_is_str`: upload CSV with int User_ID, verify dtype=object.
- `test_read_upload_excel_numeric_user_id_is_str`: same for Excel.

---

*Document: DMR-001 | DATA_MODEL_REMEDIATION.md | v1.0 | 2026-06-23*
