"""Tests for models/trigger_config.py — MT-008."""
import pytest
from models.trigger_config import TriggerConfig


# ---------------------------------------------------------------------------
# MT-008 — TriggerConfig validation tests
# ---------------------------------------------------------------------------

def test_trigger_config_valid_construction():
    tc = TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.20)
    assert tc.trigger_name == "T1"
    assert tc.priority == 1
    assert tc.engagement_rate_target == 0.20
    assert tc.distribution_pct == 0.0


def test_trigger_config_with_distribution_pct():
    tc = TriggerConfig(
        trigger_name="T2", priority=2, engagement_rate_target=0.15, distribution_pct=50.0
    )
    assert tc.distribution_pct == 50.0


def test_trigger_config_engagement_rate_below_zero():
    with pytest.raises(ValueError):
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=-0.01)


def test_trigger_config_engagement_rate_above_one():
    with pytest.raises(ValueError):
        TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=1.01)


def test_trigger_config_distribution_pct_above_100():
    with pytest.raises(ValueError):
        TriggerConfig(
            trigger_name="T1", priority=1, engagement_rate_target=0.20,
            distribution_pct=100.01,
        )


def test_trigger_config_priority_below_one():
    with pytest.raises(ValueError):
        TriggerConfig(trigger_name="T1", priority=0, engagement_rate_target=0.20)


def test_trigger_config_engagement_rate_boundary_zero():
    tc = TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=0.0)
    assert tc.engagement_rate_target == 0.0


def test_trigger_config_engagement_rate_boundary_one():
    tc = TriggerConfig(trigger_name="T1", priority=1, engagement_rate_target=1.0)
    assert tc.engagement_rate_target == 1.0
