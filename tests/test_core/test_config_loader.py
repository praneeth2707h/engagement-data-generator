"""Tests for core/config_loader.py — Wave 3 (REM-005 through REM-008).

Covers
------
* _load_trigger_configs()  — REM-005
* _load_segment_configs()  — REM-006
* _load_channel_configs()  — REM-007
* load_config_from_dict()  — REM-008 (field renames, _REQUIRED_TOP_KEYS, full build)
* load_config_from_json()  — file-path entry point

Validation requirements satisfied
----------------------------------
* Minimal valid config loads successfully (no TypeError, no ConfigError).
* Invalid config raises ConfigError or InputValidationError as appropriate.
* Missing required sections raise InputValidationError.
* TriggerConfig loads with correct field values.
* SegmentConfig loads with correct field values.
* ChannelConfig loads with correct field values.
* ConfigRegistry builds successfully with all fields populated correctly.

References
----------
* PHASE_2_EXECUTION_PLAN.md §Wave 3
* MM-001 (TriggerConfig), MM-002 (SegmentConfig), MM-003 (ChannelConfig),
  MM-004 (ConfigRegistry), LM-001 (config_loader TypeError).
"""
from __future__ import annotations

import json
import sys
import os
import pathlib
import pytest

# ---------------------------------------------------------------------------
# Path setup — allow running from any cwd
# ---------------------------------------------------------------------------
_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.config_loader import (
    load_config_from_dict,
    load_config_from_json,
    _load_trigger_configs,
    _load_segment_configs,
    _load_channel_configs,
    _REQUIRED_TOP_KEYS,
)
from models.config_registry import ConfigRegistry
from models.trigger_config import TriggerConfig
from models.segment_config import SegmentConfig
from models.channel_config import ChannelConfig
from utils.exceptions import InputValidationError, SchemaVersionError
from utils.exceptions import ConfigError
from utils.version import CONFIG_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

def _minimal_dict(**overrides) -> dict:
    """Return the smallest valid config dict that load_config_from_dict accepts."""
    base = {
        "campaign_id": "TEST-001",
        "campaign_name": "Test Campaign",
        "simulation_start_date": "2026-01-01",
        "simulation_end_date": "2026-01-31",
        "vendor": "VendorX",
        "historical_engagement_window": "Last_90_Days",
        "ads": [
            {
                "ad_name": "Ad1",
                "ad_order": 1,
                "duration_days": 7,
                "move_on_click": False,
                "target_ctr": 0.05,
            }
        ],
        "triggers": [
            {
                "trigger_name": "T1",
                "priority": 1,
                "engagement_rate_target": 0.10,
            }
        ],
        "rules": [],
    }
    base.update(overrides)
    return base


# ===========================================================================
# TestRequiredTopKeys — REM-008 (_REQUIRED_TOP_KEYS correctness)
# ===========================================================================

class TestRequiredTopKeys:
    """_REQUIRED_TOP_KEYS must not contain 'target_engagement_rate'."""

    def test_target_engagement_rate_not_in_required_keys(self) -> None:
        """Engagement rates are per-trigger; no top-level key (MM-004 fix)."""
        assert "target_engagement_rate" not in _REQUIRED_TOP_KEYS

    def test_campaign_id_in_required_keys(self) -> None:
        assert "campaign_id" in _REQUIRED_TOP_KEYS

    def test_simulation_start_date_in_required_keys(self) -> None:
        assert "simulation_start_date" in _REQUIRED_TOP_KEYS

    def test_simulation_end_date_in_required_keys(self) -> None:
        assert "simulation_end_date" in _REQUIRED_TOP_KEYS

    def test_vendor_in_required_keys(self) -> None:
        assert "vendor" in _REQUIRED_TOP_KEYS

    def test_historical_engagement_window_in_required_keys(self) -> None:
        assert "historical_engagement_window" in _REQUIRED_TOP_KEYS

    def test_ads_in_required_keys(self) -> None:
        assert "ads" in _REQUIRED_TOP_KEYS

    def test_triggers_in_required_keys(self) -> None:
        assert "triggers" in _REQUIRED_TOP_KEYS

    def test_rules_in_required_keys(self) -> None:
        assert "rules" in _REQUIRED_TOP_KEYS


# ===========================================================================
# TestLoadTriggerConfigs — REM-005
# ===========================================================================

class TestLoadTriggerConfigs:
    """_load_trigger_configs() uses only the 4 canonical TriggerConfig fields."""

    def test_single_trigger_canonical_fields(self) -> None:
        raw = [{"trigger_name": "Email_T1", "priority": 2, "engagement_rate_target": 0.15, "distribution_pct": 25.0}]
        result = _load_trigger_configs(raw)
        assert len(result) == 1
        t = result[0]
        assert t.trigger_name == "Email_T1"
        assert t.priority == 2
        assert t.engagement_rate_target == 0.15
        assert t.distribution_pct == 25.0

    def test_distribution_pct_defaults_to_zero(self) -> None:
        """distribution_pct is optional — omitting it must default to 0.0 (not KeyError)."""
        raw = [{"trigger_name": "T1", "priority": 1, "engagement_rate_target": 0.10}]
        result = _load_trigger_configs(raw)
        assert result[0].distribution_pct == 0.0

    def test_priority_defaults_to_one(self) -> None:
        raw = [{"trigger_name": "T1", "engagement_rate_target": 0.10}]
        result = _load_trigger_configs(raw)
        assert result[0].priority == 1

    def test_multiple_triggers(self) -> None:
        raw = [
            {"trigger_name": "T1", "priority": 1, "engagement_rate_target": 0.10},
            {"trigger_name": "T2", "priority": 2, "engagement_rate_target": 0.20, "distribution_pct": 50.0},
        ]
        result = _load_trigger_configs(raw)
        assert len(result) == 2
        assert result[1].trigger_name == "T2"
        assert result[1].engagement_rate_target == 0.20

    def test_returns_list_of_trigger_config_instances(self) -> None:
        raw = [{"trigger_name": "T1", "priority": 1, "engagement_rate_target": 0.05}]
        result = _load_trigger_configs(raw)
        assert all(isinstance(t, TriggerConfig) for t in result)

    def test_no_wrong_fields_segment_filter(self) -> None:
        """segment_filter was a buggy field — TriggerConfig must not have it."""
        t = TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.1)
        assert not hasattr(t, "segment_filter")

    def test_no_wrong_fields_max_users(self) -> None:
        """max_users was a buggy field — TriggerConfig must not have it."""
        t = TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.1)
        assert not hasattr(t, "max_users")

    def test_no_wrong_fields_enabled(self) -> None:
        """enabled was a buggy field — TriggerConfig must not have it."""
        t = TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.1)
        assert not hasattr(t, "enabled")


# ===========================================================================
# TestLoadSegmentConfigs — REM-006
# ===========================================================================

class TestLoadSegmentConfigs:
    """_load_segment_configs() uses only the 3 canonical SegmentConfig fields."""

    def test_single_segment_canonical_fields(self) -> None:
        raw = [{"segment_name": "HCP", "priority": 1, "distribution_pct": 60.0}]
        result = _load_segment_configs(raw)
        assert len(result) == 1
        s = result[0]
        assert s.segment_name == "HCP"
        assert s.priority == 1
        assert s.distribution_pct == 60.0

    def test_distribution_pct_defaults_to_zero(self) -> None:
        raw = [{"segment_name": "HCP", "priority": 1}]
        result = _load_segment_configs(raw)
        assert result[0].distribution_pct == 0.0

    def test_priority_defaults_to_one(self) -> None:
        raw = [{"segment_name": "HCP"}]
        result = _load_segment_configs(raw)
        assert result[0].priority == 1

    def test_none_input_returns_empty_list(self) -> None:
        """segments section is optional — None must return []."""
        assert _load_segment_configs(None) == []

    def test_empty_list_returns_empty_list(self) -> None:
        assert _load_segment_configs([]) == []

    def test_multiple_segments(self) -> None:
        raw = [
            {"segment_name": "HCP", "priority": 1, "distribution_pct": 60.0},
            {"segment_name": "NP", "priority": 2, "distribution_pct": 40.0},
        ]
        result = _load_segment_configs(raw)
        assert len(result) == 2

    def test_returns_list_of_segment_config_instances(self) -> None:
        raw = [{"segment_name": "HCP", "priority": 1}]
        result = _load_segment_configs(raw)
        assert all(isinstance(s, SegmentConfig) for s in result)

    def test_no_wrong_field_description(self) -> None:
        """description was a buggy field — SegmentConfig must not have it."""
        s = SegmentConfig(segment_name="HCP", priority=1)
        assert not hasattr(s, "description")

    def test_no_wrong_field_behavior_profile_weights(self) -> None:
        """behavior_profile_weights was a buggy field."""
        s = SegmentConfig(segment_name="HCP", priority=1)
        assert not hasattr(s, "behavior_profile_weights")


# ===========================================================================
# TestLoadChannelConfigs — REM-007
# ===========================================================================

class TestLoadChannelConfigs:
    """_load_channel_configs() uses all 9 canonical ChannelConfig fields."""

    def _email_raw(self, **overrides) -> dict:
        base = {
            "channel_name": "Email",
            "target_ctr": 0.05,
            "target_open_rate": 0.20,
            "email_day1_min": 0.10,
            "email_day1_max": 0.30,
            "email_day2_min": 0.05,
            "email_day2_max": 0.15,
            "email_day3_min": 0.02,
            "email_day3_max": 0.10,
        }
        base.update(overrides)
        return base

    def test_all_nine_fields_populated(self) -> None:
        result = _load_channel_configs([self._email_raw()])
        c = result[0]
        assert c.channel_name == "Email"
        assert c.target_ctr == 0.05
        assert c.target_open_rate == 0.20
        assert c.email_day1_min == 0.10
        assert c.email_day1_max == 0.30
        assert c.email_day2_min == 0.05
        assert c.email_day2_max == 0.15
        assert c.email_day3_min == 0.02
        assert c.email_day3_max == 0.10

    def test_nullable_fields_default_to_none(self) -> None:
        """Non-email channels may omit the email timing fields."""
        raw = [{"channel_name": "Display", "target_ctr": 0.02}]
        result = _load_channel_configs(raw)
        c = result[0]
        assert c.target_open_rate is None
        assert c.email_day1_min is None
        assert c.email_day1_max is None
        assert c.email_day2_min is None
        assert c.email_day2_max is None
        assert c.email_day3_min is None
        assert c.email_day3_max is None

    def test_none_input_returns_empty_list(self) -> None:
        assert _load_channel_configs(None) == []

    def test_empty_list_returns_empty_list(self) -> None:
        assert _load_channel_configs([]) == []

    def test_multiple_channels(self) -> None:
        raw = [
            self._email_raw(),
            {"channel_name": "Display", "target_ctr": 0.02},
        ]
        result = _load_channel_configs(raw)
        assert len(result) == 2
        assert result[1].channel_name == "Display"

    def test_returns_list_of_channel_config_instances(self) -> None:
        result = _load_channel_configs([self._email_raw()])
        assert all(isinstance(c, ChannelConfig) for c in result)

    def test_no_wrong_field_daily_cap(self) -> None:
        """daily_cap was a buggy field — ChannelConfig must not have it."""
        c = ChannelConfig(channel_name="Email", target_ctr=0.05)
        assert not hasattr(c, "daily_cap")

    def test_no_wrong_field_weekly_cap(self) -> None:
        """weekly_cap was a buggy field — ChannelConfig must not have it."""
        c = ChannelConfig(channel_name="Email", target_ctr=0.05)
        assert not hasattr(c, "weekly_cap")

    def test_no_wrong_field_enabled(self) -> None:
        """enabled was a buggy field — ChannelConfig must not have it."""
        c = ChannelConfig(channel_name="Email", target_ctr=0.05)
        assert not hasattr(c, "enabled")


# ===========================================================================
# TestMinimalValidConfig — end-to-end happy path
# ===========================================================================

class TestMinimalValidConfig:
    """Minimal valid config loads successfully without TypeError or ConfigError."""

    def test_returns_config_registry_instance(self) -> None:
        result = load_config_from_dict(_minimal_dict())
        assert isinstance(result, ConfigRegistry)

    def test_campaign_id_preserved(self) -> None:
        result = load_config_from_dict(_minimal_dict(campaign_id="CAMP-XYZ"))
        assert result.campaign_id == "CAMP-XYZ"

    def test_campaign_name_preserved(self) -> None:
        result = load_config_from_dict(_minimal_dict(campaign_name="My Campaign"))
        assert result.campaign_name == "My Campaign"

    def test_campaign_name_defaults_to_campaign_id(self) -> None:
        """If campaign_name is absent, default to campaign_id value."""
        d = _minimal_dict()
        del d["campaign_name"]
        result = load_config_from_dict(d)
        assert result.campaign_name == result.campaign_id

    def test_simulation_days_computed(self) -> None:
        result = load_config_from_dict(_minimal_dict(
            simulation_start_date="2026-01-01",
            simulation_end_date="2026-01-31",
        ))
        assert result.simulation_days == 31

    def test_vendor_maps_to_default_vendor(self) -> None:
        """REM-008: JSON 'vendor' key → ConfigRegistry.default_vendor."""
        result = load_config_from_dict(_minimal_dict(vendor="AcmeVendor"))
        assert result.default_vendor == "AcmeVendor"

    def test_config_schema_version_set(self) -> None:
        result = load_config_from_dict(_minimal_dict())
        assert result.config_schema_version == CONFIG_SCHEMA_VERSION

    def test_triggers_are_tuple(self) -> None:
        result = load_config_from_dict(_minimal_dict())
        assert isinstance(result.triggers, tuple)

    def test_ads_are_tuple(self) -> None:
        result = load_config_from_dict(_minimal_dict())
        assert isinstance(result.ads, tuple)

    def test_segments_are_tuple(self) -> None:
        result = load_config_from_dict(_minimal_dict())
        assert isinstance(result.segments, tuple)

    def test_channels_are_tuple(self) -> None:
        result = load_config_from_dict(_minimal_dict())
        assert isinstance(result.channels, tuple)

    def test_scoring_weights_default_to_constants(self) -> None:
        from utils.constants import (
            DEFAULT_WEIGHT_ENGAGEMENT, DEFAULT_WEIGHT_PROFILE,
            DEFAULT_WEIGHT_CREATIVE, DEFAULT_WEIGHT_CHANNEL, DEFAULT_WEIGHT_RECENCY,
        )
        result = load_config_from_dict(_minimal_dict())
        assert result.scoring_weight_engagement == DEFAULT_WEIGHT_ENGAGEMENT
        assert result.scoring_weight_profile == DEFAULT_WEIGHT_PROFILE
        assert result.scoring_weight_creative == DEFAULT_WEIGHT_CREATIVE
        assert result.scoring_weight_channel == DEFAULT_WEIGHT_CHANNEL
        assert result.scoring_weight_recency == DEFAULT_WEIGHT_RECENCY

    def test_custom_scoring_weights_accepted(self) -> None:
        d = _minimal_dict()
        d.update({
            "scoring_weight_engagement": 0.40,
            "scoring_weight_profile": 0.20,
            "scoring_weight_creative": 0.15,
            "scoring_weight_channel": 0.15,
            "scoring_weight_recency": 0.10,
        })
        result = load_config_from_dict(d)
        assert result.scoring_weight_engagement == 0.40
        assert result.scoring_weight_recency == 0.10


# ===========================================================================
# TestMissingRequiredKeys — REM-008 / _REQUIRED_TOP_KEYS
# ===========================================================================

class TestMissingRequiredKeys:
    """Missing required top-level keys raise InputValidationError."""

    @pytest.mark.parametrize("missing_key", _REQUIRED_TOP_KEYS)
    def test_missing_required_key_raises(self, missing_key: str) -> None:
        d = _minimal_dict()
        del d[missing_key]
        with pytest.raises(InputValidationError):
            load_config_from_dict(d)

    def test_error_mentions_missing_key(self) -> None:
        d = _minimal_dict()
        del d["campaign_id"]
        with pytest.raises(InputValidationError, match="campaign_id"):
            load_config_from_dict(d)


# ===========================================================================
# TestSchemaVersionCheck
# ===========================================================================

class TestSchemaVersionCheck:
    """schema_version mismatch raises SchemaVersionError; absent key is fine."""

    def test_matching_schema_version_accepted(self) -> None:
        d = _minimal_dict(schema_version=CONFIG_SCHEMA_VERSION)
        result = load_config_from_dict(d)
        assert isinstance(result, ConfigRegistry)

    def test_wrong_schema_version_raises(self) -> None:
        d = _minimal_dict(schema_version="1.0")
        with pytest.raises(SchemaVersionError):
            load_config_from_dict(d)

    def test_absent_schema_version_accepted(self) -> None:
        """schema_version key is optional — omitting it must not raise."""
        d = _minimal_dict()
        assert "schema_version" not in d
        result = load_config_from_dict(d)
        assert isinstance(result, ConfigRegistry)

    def test_schema_version_error_has_found_attr(self) -> None:
        d = _minimal_dict(schema_version="0.9")
        with pytest.raises(SchemaVersionError) as exc_info:
            load_config_from_dict(d)
        assert exc_info.value.found == "0.9"

    def test_schema_version_error_has_expected_attr(self) -> None:
        d = _minimal_dict(schema_version="0.9")
        with pytest.raises(SchemaVersionError) as exc_info:
            load_config_from_dict(d)
        assert exc_info.value.expected == CONFIG_SCHEMA_VERSION


# ===========================================================================
# TestInvalidConfigValues — ConfigError propagation from ConfigRegistry
# ===========================================================================

class TestInvalidConfigValues:
    """ConfigRegistry.__post_init__ invariant violations surface as ConfigError."""

    def test_end_before_start_raises_config_error(self) -> None:
        d = _minimal_dict(
            simulation_start_date="2026-02-01",
            simulation_end_date="2026-01-01",
        )
        with pytest.raises(ConfigError):
            load_config_from_dict(d)

    def test_bad_scoring_weight_sum_raises_config_error(self) -> None:
        d = _minimal_dict()
        d.update({
            "scoring_weight_engagement": 0.10,
            "scoring_weight_profile": 0.10,
            "scoring_weight_creative": 0.10,
            "scoring_weight_channel": 0.10,
            "scoring_weight_recency": 0.10,
        })
        with pytest.raises(ConfigError):
            load_config_from_dict(d)

    def test_bad_date_string_raises_input_validation_error(self) -> None:
        d = _minimal_dict(simulation_start_date="not-a-date")
        with pytest.raises(InputValidationError):
            load_config_from_dict(d)


# ===========================================================================
# TestConfigRegistryBuildsSuccessfully — full object validation
# ===========================================================================

class TestConfigRegistryBuildsSuccessfully:
    """ConfigRegistry builds with all Wave 3 field renames applied correctly."""

    def _full_dict(self) -> dict:
        return {
            "campaign_id": "FULL-001",
            "campaign_name": "Full Build Test",
            "simulation_start_date": "2026-03-01",
            "simulation_end_date": "2026-03-30",
            "vendor": "FullVendor",
            "historical_engagement_window": "Last_90_Days",
            "historical_campaign_match": "Strict",
            "historical_window_days": 90,
            "historical_campaign_ids": ["PREV-001", "PREV-002"],
            "cooling_period_days": 14,
            "ter_mode": "TER",
            "behavior_score_decay_days": 30,
            "engagement_score_floor": 0.0,
            "engagement_score_ceiling": 1.0,
            "engagement_cooldown_days": 3,
            "weekly_impression_cap": 7,
            "weekly_click_cap": 3,
            "weekly_open_cap": 7,
            "weekly_engagement_cap": 5,
            "affinity_boost_on_click": 0.05,
            "affinity_decay_no_engage": 0.02,
            "affinity_floor": 0.0,
            "affinity_ceiling": 1.0,
            "channel_affinity_weight": 0.5,
            "creative_affinity_weight": 0.5,
            "fatigue_impression_threshold": 3,
            "fatigue_decay_factor": 0.5,
            "fatigue_recovery_days": 7,
            "admin_override": False,
            "allow_reentry": True,
            "reentry_cooldown_days": 0,
            "ads": [
                {"ad_name": "Ad1", "ad_order": 1, "duration_days": 7, "move_on_click": False, "target_ctr": 0.05},
                {"ad_name": "Ad2", "ad_order": 2, "duration_days": 5, "move_on_click": True, "target_ctr": 0.08},
            ],
            "triggers": [
                {"trigger_name": "T1", "priority": 1, "engagement_rate_target": 0.10, "distribution_pct": 60.0},
                {"trigger_name": "T2", "priority": 2, "engagement_rate_target": 0.05, "distribution_pct": 40.0},
            ],
            "segments": [
                {"segment_name": "HCP", "priority": 1, "distribution_pct": 70.0},
                {"segment_name": "NP", "priority": 2, "distribution_pct": 30.0},
            ],
            "channels": [
                {
                    "channel_name": "Email",
                    "target_ctr": 0.05,
                    "target_open_rate": 0.20,
                    "email_day1_min": 0.10,
                    "email_day1_max": 0.30,
                    "email_day2_min": 0.05,
                    "email_day2_max": 0.15,
                    "email_day3_min": 0.02,
                    "email_day3_max": 0.10,
                },
                {"channel_name": "Display", "target_ctr": 0.02},
            ],
            "rules": [
                {"rule_id": "HR-001", "rule_name": "No double-send", "severity": "Hard", "enabled": True},
            ],
        }

    def test_full_build_succeeds(self) -> None:
        result = load_config_from_dict(self._full_dict())
        assert isinstance(result, ConfigRegistry)

    def test_ads_count(self) -> None:
        result = load_config_from_dict(self._full_dict())
        assert len(result.ads) == 2

    def test_triggers_count(self) -> None:
        result = load_config_from_dict(self._full_dict())
        assert len(result.triggers) == 2

    def test_segments_count(self) -> None:
        result = load_config_from_dict(self._full_dict())
        assert len(result.segments) == 2

    def test_channels_count(self) -> None:
        result = load_config_from_dict(self._full_dict())
        assert len(result.channels) == 2

    def test_rule_configs_populated(self) -> None:
        result = load_config_from_dict(self._full_dict())
        assert "HR-001" in result.rule_configs

    def test_historical_campaign_ids_tuple(self) -> None:
        result = load_config_from_dict(self._full_dict())
        assert result.historical_campaign_ids == ("PREV-001", "PREV-002")

    def test_weekly_impression_cap_from_json(self) -> None:
        result = load_config_from_dict(self._full_dict())
        assert result.weekly_impression_cap == 7

    def test_ter_mode_set(self) -> None:
        result = load_config_from_dict(self._full_dict())
        assert result.ter_mode == "TER"

    def test_simulation_days_full(self) -> None:
        result = load_config_from_dict(self._full_dict())
        # 2026-03-01 to 2026-03-30 = 30 days
        assert result.simulation_days == 30

    def test_email_channel_fields(self) -> None:
        result = load_config_from_dict(self._full_dict())
        email = result.get_channel_config("Email")
        assert email is not None
        assert email.target_open_rate == 0.20
        assert email.email_day1_min == 0.10
        assert email.email_day3_max == 0.10

    def test_trigger_engagement_rate_target(self) -> None:
        result = load_config_from_dict(self._full_dict())
        t1 = result.get_trigger_by_name("T1")
        assert t1 is not None
        assert t1.engagement_rate_target == 0.10

    def test_segment_priority(self) -> None:
        result = load_config_from_dict(self._full_dict())
        hcp = result.get_segment_by_name("HCP")
        assert hcp is not None
        assert hcp.priority == 1


# ===========================================================================
# TestLoadConfigFromJson — file-based entry point
# ===========================================================================

class TestLoadConfigFromJson:
    """load_config_from_json() — basic file I/O and error paths."""

    def test_loads_valid_json_file(self, tmp_path) -> None:
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(_minimal_dict()), encoding="utf-8")
        result = load_config_from_json(cfg_file)
        assert isinstance(result, ConfigRegistry)
        assert result.campaign_id == "TEST-001"

    def test_missing_file_raises_file_not_found(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            load_config_from_json(tmp_path / "nonexistent.json")

    def test_malformed_json_raises_input_validation_error(self, tmp_path) -> None:
        cfg_file = tmp_path / "bad.json"
        cfg_file.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(InputValidationError):
            load_config_from_json(cfg_file)

    def test_snapshot_format_unwrapped(self, tmp_path) -> None:
        """Snapshot format: {"schema_version": "2.0", "config": {...}}."""
        snapshot = {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "config": _minimal_dict(),
        }
        cfg_file = tmp_path / "snapshot.json"
        cfg_file.write_text(json.dumps(snapshot), encoding="utf-8")
        result = load_config_from_json(cfg_file)
        assert isinstance(result, ConfigRegistry)

    def test_snapshot_wrong_version_raises_schema_version_error(self, tmp_path) -> None:
        snapshot = {
            "schema_version": "0.1",
            "config": _minimal_dict(),
        }
        cfg_file = tmp_path / "old.json"
        cfg_file.write_text(json.dumps(snapshot), encoding="utf-8")
        with pytest.raises(SchemaVersionError):
            load_config_from_json(cfg_file)

    def test_accepts_string_path(self, tmp_path) -> None:
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(_minimal_dict()), encoding="utf-8")
        result = load_config_from_json(str(cfg_file))
        assert isinstance(result, ConfigRegistry)
