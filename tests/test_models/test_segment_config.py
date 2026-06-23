"""Tests for models/segment_config.py — MT-009."""
import pytest
from models.segment_config import SegmentConfig


# ---------------------------------------------------------------------------
# MT-009 — SegmentConfig validation tests
# ---------------------------------------------------------------------------

def test_segment_config_valid_construction():
    sc = SegmentConfig(segment_name="Seg1", priority=1)
    assert sc.segment_name == "Seg1"
    assert sc.priority == 1
    assert sc.distribution_pct == 0.0


def test_segment_config_with_distribution_pct():
    sc = SegmentConfig(segment_name="Seg2", priority=2, distribution_pct=40.0)
    assert sc.distribution_pct == 40.0


def test_segment_config_distribution_pct_above_100():
    with pytest.raises(ValueError):
        SegmentConfig(segment_name="Seg1", priority=1, distribution_pct=100.01)


def test_segment_config_priority_below_one():
    with pytest.raises(ValueError):
        SegmentConfig(segment_name="Seg1", priority=0)


def test_segment_config_distribution_pct_zero():
    sc = SegmentConfig(segment_name="Seg1", priority=1, distribution_pct=0.0)
    assert sc.distribution_pct == 0.0


def test_segment_config_distribution_pct_boundary_100():
    sc = SegmentConfig(segment_name="Seg1", priority=1, distribution_pct=100.0)
    assert sc.distribution_pct == 100.0
