"""Config loader — builds ConfigRegistry from JSON / dict.

Wave 3 remediation (REM-005 through REM-008, 2026-06-22):

REM-005: Rewrote _load_trigger_configs() — removed segment_filter, max_users,
         enabled, description (wrong fields); added engagement_rate_target and
         distribution_pct (correct fields).
REM-006: Rewrote _load_segment_configs() — removed description,
         behavior_profile_weights (wrong fields); added priority and
         distribution_pct (correct fields).
REM-007: Rewrote _load_channel_configs() — removed daily_cap, weekly_cap,
         enabled (wrong fields); added all 9 correct ChannelConfig fields.
REM-008: Rewrote load_config_from_dict() — renamed 6 wrong field names,
         deleted journeys_per_user (not a ConfigRegistry field), added
         21 missing fields with JSON-read-or-default logic.
         Fixed _REQUIRED_TOP_KEYS — removed "target_engagement_rate"
         (engagement rates are per-trigger, not top-level).

References
----------
* MM-001 — TriggerConfig field mismatches (RESOLVED REM-005)
* MM-002 — SegmentConfig field mismatches (RESOLVED REM-006)
* MM-003 — ChannelConfig field mismatches (RESOLVED REM-007)
* MM-004 / LM-001 — ConfigRegistry constructor mismatches (RESOLVED REM-008)
* PHASE_2_EXECUTION_PLAN.md §Wave 3
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import date
from typing import Any

from models.config_registry import ConfigRegistry
from models.rule_config import RuleConfig
from models.ad_config import AdConfig
from models.trigger_config import TriggerConfig
from models.segment_config import SegmentConfig
from models.channel_config import ChannelConfig
from models.enums import (
    RuleSeverity,
    HistoricalWindow,
    HistoricalCampaignMatchMode,
)
from utils.constants import (
    DEFAULT_WEIGHT_ENGAGEMENT,
    DEFAULT_WEIGHT_PROFILE,
    DEFAULT_WEIGHT_CREATIVE,
    DEFAULT_WEIGHT_CHANNEL,
    DEFAULT_WEIGHT_RECENCY,
    DEFAULT_FREQUENCY_MAX,
)
from utils.version import CONFIG_SCHEMA_VERSION
from utils.exceptions import SchemaVersionError, InputValidationError
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Required top-level JSON keys.
#
# Engagement rates are validated per-trigger inside TriggerConfig.__post_init__,
# NOT at the top-level config key level.  There is no top-level
# "target_engagement_rate" key (MM-004 / REM-008 — removed from required keys).
# ---------------------------------------------------------------------------
_REQUIRED_TOP_KEYS = [
    "campaign_id",
    "simulation_start_date",
    "simulation_end_date",
    "vendor",
    "historical_engagement_window",
    "ads",
    "triggers",
    "rules",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str, field_name: str) -> date:
    """Parse ISO date string or raise InputValidationError."""
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError) as e:
        raise InputValidationError(
            file_name="config.json",
            detail=f"Cannot parse '{field_name}' as date: {value!r}",
        ) from e


# ---------------------------------------------------------------------------
# Sub-loaders
# ---------------------------------------------------------------------------

def _load_rule_configs(rules_list: list[dict]) -> dict[str, RuleConfig]:
    """Build dict of rule_id → RuleConfig from raw JSON list."""
    configs: dict[str, RuleConfig] = {}
    for r in rules_list:
        rule_id = r.get("rule_id", "")
        configs[rule_id] = RuleConfig(
            rule_id=rule_id,
            rule_name=r.get("rule_name", rule_id),
            severity=r.get("severity", RuleSeverity.SOFT.value),
            enabled=bool(r.get("enabled", True)),
            severity_override=r.get("severity_override"),
        )
    return configs


def _load_ad_configs(ads_list: list[dict]) -> list[AdConfig]:
    """Build list of AdConfig from raw JSON list."""
    configs = []
    for a in ads_list:
        configs.append(AdConfig(
            ad_name=a["ad_name"],
            ad_order=int(a.get("ad_order", 1)),
            duration_days=int(a.get("duration_days", 7)),
            move_on_click=bool(a.get("move_on_click", False)),
            channel=a.get("channel", "Email"),
            vendor=a.get("vendor"),
            target_ctr=float(a["target_ctr"]) if a.get("target_ctr") is not None else None,
        ))
    return configs


def _load_trigger_configs(triggers_list: list[dict]) -> list[TriggerConfig]:
    """Build list of TriggerConfig from raw JSON list.

    REM-005: Uses only the 4 canonical TriggerConfig fields.
    Removed: segment_filter, max_users, enabled, description (MM-001).
    Added:   engagement_rate_target, distribution_pct.
    """
    configs = []
    for t in triggers_list:
        configs.append(TriggerConfig(
            trigger_name=t["trigger_name"],
            priority=int(t.get("priority", 1)),
            engagement_rate_target=float(t["engagement_rate_target"]),
            distribution_pct=float(t.get("distribution_pct", 0.0)),
        ))
    return configs


def _load_segment_configs(segments_list: list[dict] | None) -> list[SegmentConfig]:
    """Build list of SegmentConfig from raw JSON list (may be absent).

    REM-006: Uses only the 3 canonical SegmentConfig fields.
    Removed: description, behavior_profile_weights (MM-002).
    Added:   priority, distribution_pct.
    """
    if not segments_list:
        return []
    configs = []
    for s in segments_list:
        configs.append(SegmentConfig(
            segment_name=s["segment_name"],
            priority=int(s.get("priority", 1)),
            distribution_pct=float(s.get("distribution_pct", 0.0)),
        ))
    return configs


def _load_channel_configs(channels_list: list[dict] | None) -> list[ChannelConfig]:
    """Build list of ChannelConfig from raw JSON list (may be absent).

    REM-007: Uses all 9 canonical ChannelConfig fields.
    Removed: daily_cap, weekly_cap, enabled (MM-003).
    Added:   target_ctr, target_open_rate, email_day1–3 min/max (all 9 fields).
    All 6 nullable fields default to None when absent from the JSON dict.
    """
    if not channels_list:
        return []
    configs = []
    for c in channels_list:
        configs.append(ChannelConfig(
            channel_name=c["channel_name"],
            target_ctr=float(c["target_ctr"]),
            target_open_rate=float(c["target_open_rate"]) if c.get("target_open_rate") is not None else None,
            email_day1_min=float(c["email_day1_min"]) if c.get("email_day1_min") is not None else None,
            email_day1_max=float(c["email_day1_max"]) if c.get("email_day1_max") is not None else None,
            email_day2_min=float(c["email_day2_min"]) if c.get("email_day2_min") is not None else None,
            email_day2_max=float(c["email_day2_max"]) if c.get("email_day2_max") is not None else None,
            email_day3_min=float(c["email_day3_min"]) if c.get("email_day3_min") is not None else None,
            email_day3_max=float(c["email_day3_max"]) if c.get("email_day3_max") is not None else None,
        ))
    return configs


# ---------------------------------------------------------------------------
# Primary loader
# ---------------------------------------------------------------------------

def load_config_from_dict(data: dict[str, Any]) -> ConfigRegistry:
    """Build ConfigRegistry from a raw Python dict (e.g. parsed from JSON).

    Validates schema_version if present. Validates required top-level keys.
    All optional fields fall back to sensible defaults when absent from dict.

    Args:
        data: Dictionary with campaign configuration.

    Returns:
        Populated ConfigRegistry.

    Raises:
        SchemaVersionError: If schema_version key is present but mismatched.
        InputValidationError: If required keys are missing or unparseable.
        ConfigError: If ConfigRegistry.__post_init__ rejects the values.

    Wave 3 changes (REM-008):
        Renamed: vendor → default_vendor
                 historical_campaign_match_mode → historical_campaign_match
                 custom_historical_days → historical_window_days
                 max_weekly_impressions → weekly_impression_cap
                 max_weekly_engagements → weekly_engagement_cap
                 rules → rule_configs
                 schema_version → config_schema_version
        Deleted: journeys_per_user (not a ConfigRegistry field)
                 target_engagement_rate (not a top-level field — per-trigger)
        Added:   campaign_name, ter_mode, historical_campaign_ids,
                 behavior_score_decay_days, engagement_score_floor,
                 engagement_score_ceiling, weekly_click_cap, weekly_open_cap,
                 affinity_boost_on_click, affinity_decay_no_engage,
                 affinity_floor, affinity_ceiling, channel_affinity_weight,
                 creative_affinity_weight, fatigue_impression_threshold,
                 fatigue_decay_factor, fatigue_recovery_days, admin_override,
                 allow_reentry, reentry_cooldown_days, plus all six
                 scoring weight fields from REM-004.
    """
    # ------------------------------------------------------------------
    # Schema version check
    # ------------------------------------------------------------------
    if "schema_version" in data:
        found = data["schema_version"]
        if found != CONFIG_SCHEMA_VERSION:
            raise SchemaVersionError(
                found=str(found),
                expected=CONFIG_SCHEMA_VERSION,
                file_name="config dict",
            )

    # ------------------------------------------------------------------
    # Required key check
    # ------------------------------------------------------------------
    missing = [k for k in _REQUIRED_TOP_KEYS if k not in data]
    if missing:
        raise InputValidationError(
            file_name="config dict",
            detail=f"Missing required config keys: {missing}",
        )

    # ------------------------------------------------------------------
    # Build sub-objects
    # ------------------------------------------------------------------
    rule_configs = _load_rule_configs(data.get("rules", []))
    ads = _load_ad_configs(data.get("ads", []))
    triggers = _load_trigger_configs(data.get("triggers", []))
    segments = _load_segment_configs(data.get("segments"))
    channels = _load_channel_configs(data.get("channels"))

    # ------------------------------------------------------------------
    # Build ConfigRegistry (REM-008 — all field names corrected)
    # ------------------------------------------------------------------
    registry = ConfigRegistry(
        # --- Identity ---
        campaign_id=data["campaign_id"],
        campaign_name=data.get("campaign_name", data["campaign_id"]),  # default to campaign_id
        config_schema_version=CONFIG_SCHEMA_VERSION,                   # WAS schema_version=

        # --- Simulation bounds ---
        simulation_start_date=_parse_date(data["simulation_start_date"], "simulation_start_date"),
        simulation_end_date=_parse_date(data["simulation_end_date"], "simulation_end_date"),

        # --- Journey & delivery ---
        ads=tuple(ads),
        default_vendor=data["vendor"],                                 # WAS vendor=
        cooling_period_days=int(data.get("cooling_period_days", 90)),

        # --- Triggers & segments ---
        triggers=tuple(triggers),
        segments=tuple(segments),

        # --- Channels ---
        channels=tuple(channels),

        # --- Validation rules ---
        rule_configs=rule_configs,                                      # WAS rules=

        # --- TER / engagement rate mode ---
        ter_mode=data.get("ter_mode", "TER"),

        # --- Historical engagement settings ---
        historical_engagement_window=data.get(
            "historical_engagement_window", HistoricalWindow.LAST_90.value
        ),
        historical_window_days=(                                        # WAS custom_historical_days=
            int(data["historical_window_days"])
            if data.get("historical_window_days") is not None else None
        ),
        historical_campaign_match=data.get(                            # WAS historical_campaign_match_mode=
            "historical_campaign_match", HistoricalCampaignMatchMode.STRICT.value
        ),
        historical_campaign_ids=tuple(data.get("historical_campaign_ids", [])),

        # --- Behavior & engagement scoring ---
        behavior_score_decay_days=int(data.get("behavior_score_decay_days", 30)),
        engagement_score_floor=float(data.get("engagement_score_floor", 0.0)),
        engagement_score_ceiling=float(data.get("engagement_score_ceiling", 1.0)),
        engagement_cooldown_days=int(data.get("engagement_cooldown_days", 0)),
        weekly_impression_cap=int(data.get("weekly_impression_cap",    # WAS max_weekly_impressions=
            data.get("max_weekly_impressions", 10))),
        weekly_click_cap=int(data.get("weekly_click_cap", 5)),
        weekly_open_cap=int(data.get("weekly_open_cap", 10)),
        weekly_engagement_cap=int(data.get("weekly_engagement_cap",    # WAS max_weekly_engagements=
            data.get("max_weekly_engagements", 10))),

        # --- Affinity parameters ---
        affinity_boost_on_click=float(data.get("affinity_boost_on_click", 0.05)),
        affinity_decay_no_engage=float(data.get("affinity_decay_no_engage", 0.02)),
        affinity_floor=float(data.get("affinity_floor", 0.0)),
        affinity_ceiling=float(data.get("affinity_ceiling", 1.0)),
        channel_affinity_weight=float(data.get("channel_affinity_weight", 0.5)),
        creative_affinity_weight=float(data.get("creative_affinity_weight", 0.5)),

        # --- Fatigue / frequency parameters ---
        fatigue_impression_threshold=int(data.get("fatigue_impression_threshold", 3)),
        fatigue_decay_factor=float(data.get("fatigue_decay_factor", 0.5)),
        fatigue_recovery_days=int(data.get("fatigue_recovery_days", 7)),

        # --- Admin / override flags ---
        admin_override=bool(data.get("admin_override", False)),
        allow_reentry=bool(data.get("allow_reentry", True)),
        reentry_cooldown_days=int(data.get("reentry_cooldown_days", 0)),

        # --- Scoring weights (REM-004 / Wave 2 — read from JSON or use constants) ---
        scoring_weight_engagement=float(
            data.get("scoring_weight_engagement", DEFAULT_WEIGHT_ENGAGEMENT)
        ),
        scoring_weight_profile=float(
            data.get("scoring_weight_profile", DEFAULT_WEIGHT_PROFILE)
        ),
        scoring_weight_creative=float(
            data.get("scoring_weight_creative", DEFAULT_WEIGHT_CREATIVE)
        ),
        scoring_weight_channel=float(
            data.get("scoring_weight_channel", DEFAULT_WEIGHT_CHANNEL)
        ),
        scoring_weight_recency=float(
            data.get("scoring_weight_recency", DEFAULT_WEIGHT_RECENCY)
        ),
        frequency_max=int(data.get("frequency_max", DEFAULT_FREQUENCY_MAX)),
    )

    logger.info(
        "ConfigRegistry built: campaign_id=%r, %d ads, %d triggers, %d segments, %d rules.",
        registry.campaign_id,
        len(registry.ads),
        len(registry.triggers),
        len(registry.segments),
        len(registry.rule_configs),
    )
    return registry


def load_config_from_json(file_path: str | Path) -> ConfigRegistry:
    """Load ConfigRegistry from a JSON config file on disk.

    Supports both raw config JSON and snapshot-wrapped JSON.
    In snapshot format, the "config" key is unwrapped before parsing.

    Args:
        file_path: Path to JSON file.

    Returns:
        Populated ConfigRegistry.

    Raises:
        FileNotFoundError: If the file does not exist.
        SchemaVersionError: On schema version mismatch.
        InputValidationError: On parse errors or missing keys.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            raise InputValidationError(
                file_name=str(file_path),
                detail=f"Malformed JSON: {e}",
            ) from e

    # Detect snapshot format ({"schema_version": ..., "config": {...}})
    if "config" in raw and "schema_version" in raw:
        found_version = raw["schema_version"]
        if found_version != CONFIG_SCHEMA_VERSION:
            raise SchemaVersionError(
                found=str(found_version),
                expected=CONFIG_SCHEMA_VERSION,
                file_name=str(file_path),
            )
        data = raw["config"]
    else:
        data = raw

    logger.info("Loading config from: %s", file_path)
    return load_config_from_dict(data)


__all__ = [
    "load_config_from_dict",
    "load_config_from_json",
]
