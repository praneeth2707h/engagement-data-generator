"""Tests for models/config_registry.py — MT-010, REM-011, REM-012."""
import pytest
from datetime import date
from models.ad_config import AdConfig
from models.config_registry import ConfigRegistry
from models.enums import HistoricalWindow, RuleSeverity
from models.rule_config import RuleConfig
from models.segment_config import SegmentConfig
from models.trigger_config import TriggerConfig
from utils.exceptions import ConfigError


# ---------------------------------------------------------------------------
# make_registry() — REM-011 + REM-012 corrected helper
# ---------------------------------------------------------------------------

def make_registry(**kwargs) -> ConfigRegistry:
    """Construct a valid ConfigRegistry with all post-REM-008 field names.

    REM-011: TriggerConfig uses canonical 4-field keyword constructor.
    REM-012: All ConfigRegistry field names match post-REM-008 dataclass.
    """
    ads = (
        AdConfig("Ad_B", 2, 7, False, "Email", None, 0.05),
        AdConfig("Ad_A", 1, 5, True, "Display", "VendorX", 0.10),
    )
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.20),
    )
    rules = {
        "R-001": RuleConfig("R-001", "Test", RuleSeverity.SOFT.value, True, None)
    }
    defaults = dict(
        campaign_id="CAMP-001",
        campaign_name="Test Campaign",
        config_schema_version="2.0",
        simulation_start_date=date(2024, 1, 1),
        simulation_end_date=date(2024, 3, 31),
        ads=ads,
        default_vendor="DefaultVendor",
        cooling_period_days=14,
        triggers=triggers,
        segments=(),
        channels=(),
        rule_configs=rules,
        ter_mode="TER",
        historical_engagement_window=HistoricalWindow.LAST_90.value,
        historical_window_days=None,
        historical_campaign_match="Strict",
        historical_campaign_ids=(),
        behavior_score_decay_days=30,
        engagement_score_floor=0.0,
        engagement_score_ceiling=1.0,
        engagement_cooldown_days=3,
        weekly_impression_cap=5,
        weekly_click_cap=3,
        weekly_open_cap=5,
        weekly_engagement_cap=2,
        affinity_boost_on_click=0.05,
        affinity_decay_no_engage=0.02,
        affinity_floor=0.0,
        affinity_ceiling=1.0,
        channel_affinity_weight=0.5,
        creative_affinity_weight=0.5,
        fatigue_impression_threshold=3,
        fatigue_decay_factor=0.5,
        fatigue_recovery_days=7,
        admin_override=False,
        allow_reentry=True,
        reentry_cooldown_days=0,
    )
    defaults.update(kwargs)
    return ConfigRegistry(**defaults)


# ---------------------------------------------------------------------------
# Basic construction
# ---------------------------------------------------------------------------

def test_make_registry_constructs_without_error():
    reg = make_registry()
    assert reg.campaign_id == "CAMP-001"


def test_simulation_days_derived():
    reg = make_registry(
        simulation_start_date=date(2024, 1, 1),
        simulation_end_date=date(2024, 1, 31),
    )
    assert reg.simulation_days == 31


def test_default_vendor_field():
    reg = make_registry(default_vendor="VendorXYZ")
    assert reg.default_vendor == "VendorXYZ"


def test_rule_configs_field():
    reg = make_registry()
    assert "R-001" in reg.rule_configs


def test_weekly_impression_cap_field():
    reg = make_registry(weekly_impression_cap=10)
    assert reg.weekly_impression_cap == 10


def test_weekly_engagement_cap_field():
    reg = make_registry(weekly_engagement_cap=4)
    assert reg.weekly_engagement_cap == 4


def test_historical_campaign_match_field():
    reg = make_registry(historical_campaign_match="Strict")
    assert reg.historical_campaign_match == "Strict"


def test_historical_window_days_field():
    reg = make_registry(historical_window_days=60)
    assert reg.historical_window_days == 60


# ---------------------------------------------------------------------------
# MT-010 — ConfigRegistry validation error tests
# ---------------------------------------------------------------------------

def test_config_registry_end_before_start():
    """simulation_end_date before simulation_start_date → ConfigError."""
    with pytest.raises(ConfigError):
        make_registry(
            simulation_start_date=date(2024, 3, 31),
            simulation_end_date=date(2024, 1, 1),
        )


def test_config_registry_empty_ads():
    """No AdConfigs → ConfigError."""
    with pytest.raises(ConfigError):
        make_registry(ads=())


def test_config_registry_empty_triggers():
    """No TriggerConfigs → ConfigError."""
    with pytest.raises(ConfigError):
        make_registry(triggers=())


# ---------------------------------------------------------------------------
# TriggerConfig canonical constructor (REM-011 verification)
# ---------------------------------------------------------------------------

def test_trigger_config_canonical_constructor():
    """TriggerConfig(trigger_name=, priority=, engagement_rate_target=) is valid."""
    tc = TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.20)
    assert tc.trigger_name == "T1"
    assert tc.priority == 1
    assert tc.engagement_rate_target == 0.20
    assert tc.distribution_pct == 0.0


# ---------------------------------------------------------------------------
# get_ad_names / get_ad_by_name / get_ad_by_order
# ---------------------------------------------------------------------------

def test_get_ad_names_sorted_by_order():
    reg = make_registry()
    # Ad_B has order=2, Ad_A has order=1 → sorted: ["Ad_A", "Ad_B"]
    assert reg.get_ad_names() == ["Ad_A", "Ad_B"]


def test_get_ad_by_name_found():
    reg = make_registry()
    ad = reg.get_ad_by_name("Ad_A")
    assert ad is not None
    assert ad.ad_name == "Ad_A"


def test_get_ad_by_name_not_found():
    reg = make_registry()
    assert reg.get_ad_by_name("NoSuchAd") is None


def test_get_ad_by_order():
    reg = make_registry()
    ad = reg.get_ad_by_order(1)
    assert ad is not None
    assert ad.ad_order == 1


# ---------------------------------------------------------------------------
# get_effective_vendor
# ---------------------------------------------------------------------------

def test_get_effective_vendor_uses_ad_vendor():
    reg = make_registry()
    ad = reg.get_ad_by_name("Ad_A")  # vendor="VendorX"
    assert reg.get_effective_vendor(ad) == "VendorX"


def test_get_effective_vendor_falls_back_to_default():
    reg = make_registry()
    ad = reg.get_ad_by_name("Ad_B")  # vendor=None
    assert reg.get_effective_vendor(ad) == "DefaultVendor"


# ---------------------------------------------------------------------------
# get_trigger_by_name
# ---------------------------------------------------------------------------

def test_get_trigger_by_name_found():
    reg = make_registry()
    t = reg.get_trigger_by_name("T1")
    assert t is not None
    assert t.trigger_name == "T1"


def test_get_trigger_by_name_not_found():
    reg = make_registry()
    assert reg.get_trigger_by_name("NoSuchTrigger") is None


def test_config_registry_rejects_trigger_with_priority_below_one():
    """ConfigRegistry.__post_init__ or TriggerConfig.__post_init__ must reject priority < 1 (ARCH-019)."""
    import pytest
    from utils.exceptions import ConfigError
    with pytest.raises((ConfigError, ValueError)):
        make_registry(
            triggers=(
                TriggerConfig(trigger_name="T_bad", priority=0, engagement_rate_target=0.10),
            )
        )
