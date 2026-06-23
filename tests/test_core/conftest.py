"""Shared fixtures for tests/test_core/.

Provides make_config(), make_trigger_df(), and make_state_df() — the three
fixtures referenced throughout the Wave 1 test suite (UserStateManager and
AudienceManager).

All fixtures produce minimal but fully-valid objects.  make_config() is
modelled directly on make_registry() from tests/test_models/test_config_registry.py
(REM-011 / REM-012 corrected field names).
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from models.ad_config import AdConfig
from models.config_registry import ConfigRegistry
from models.enums import HistoricalWindow, RuleSeverity
from models.rule_config import RuleConfig
from models.segment_config import SegmentConfig
from models.trigger_config import TriggerConfig


# ---------------------------------------------------------------------------
# make_config — minimal valid ConfigRegistry
# ---------------------------------------------------------------------------

def make_config(**kwargs) -> ConfigRegistry:
    """Return a minimal valid ConfigRegistry for tests.

    Defaults produce a two-ad, one-trigger campaign that satisfies all
    ConfigRegistry __post_init__ guards (scoring weights sum to 1.0,
    simulation_end >= simulation_start, at least one ad and trigger).

    Pass keyword overrides to adjust any field.  For example:

        make_config(allow_reentry=False)
        make_config(cooling_period_days=60)
        make_config(triggers=(TriggerConfig("T1", 1, 0.20), TriggerConfig("T2", 2, 0.15)))
    """
    ads = (
        AdConfig("Ad_A", 1, 5, True, "Display", "VendorX", 0.10),
        AdConfig("Ad_B", 2, 7, False, "Email", None, 0.05),
    )
    triggers = (
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.20),
    )
    rules = {
        "R-001": RuleConfig("R-001", "Test", RuleSeverity.SOFT.value, True, None)
    }
    defaults = dict(
        campaign_id="TEST_CAMPAIGN",
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
# make_trigger_df — minimal valid trigger DataFrame
# ---------------------------------------------------------------------------

def make_trigger_df(
    n: int = 3,
    campaign_id: str = "TEST_CAMPAIGN",
    trigger_name: str = "T1",
    segment: str = "Seg_A",
) -> pd.DataFrame:
    """Return a minimal trigger DataFrame with n unique users.

    Columns match the Stage 2 trigger file schema:
        Campaign_ID, User_ID, Trigger_Name, Segment, Trigger_Date.

    Args:
        n: Number of unique users to generate.
        campaign_id: Value used for the Campaign_ID column.
        trigger_name: Value used for the Trigger_Name column.
        segment: Value used for the Segment column.

    Returns:
        pd.DataFrame with n rows, all users in the same campaign.
    """
    return pd.DataFrame({
        "Campaign_ID": [campaign_id] * n,
        "User_ID": [f"U{i:03d}" for i in range(1, n + 1)],
        "Trigger_Name": [trigger_name] * n,
        "Segment": [segment] * n,
        "Trigger_Date": [date(2024, 1, 1)] * n,
    })


# ---------------------------------------------------------------------------
# make_state_df — minimal valid state DataFrame (via UserStateManager)
# ---------------------------------------------------------------------------

def make_state_df(n: int = 3, config: ConfigRegistry | None = None) -> pd.DataFrame:
    """Return an initialised state DataFrame for n users.

    Uses UserStateManager.initialize_user_states() so that the schema and
    dtypes are exactly what production code produces.

    Args:
        n: Number of users.
        config: ConfigRegistry to use.  Defaults to make_config().

    Returns:
        pd.DataFrame with n rows, all users with journey_status=Not_Started,
        eligibility_status=New, historical_engaged=False, is_valid=True.
    """
    from core.user_state_manager import UserStateManager

    cfg = config if config is not None else make_config()
    trigger_df = make_trigger_df(n=n, campaign_id=cfg.campaign_id)
    mgr = UserStateManager(cfg)
    return mgr.initialize_user_states(trigger_df, previous_state_df=None)
