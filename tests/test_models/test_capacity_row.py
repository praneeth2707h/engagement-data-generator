"""Tests for models/capacity_row.py — RemainingCapacityRow.

Coverage targets (MT-006 from PHASE_2_EXECUTION_PLAN.md):
- compute()       → TCC formula with math.ceil() (TCC-001 regression test)
- is_at_capacity()→ True when remaining_capacity <= 0
- utilization_pct()→ percentage calculation + zero-division guard

TCC-001 regression
------------------
The canonical regression test is test_compute_ceil_not_floor(): 101 users at
10% must produce target_engaged_users = 11 (not 10).  If this test ever fails
it means math.ceil() was replaced with int() or math.floor().

References
----------
* TCC-001    — defect: int() used instead of math.ceil()
* REM-003    — fix: replaced int() with math.ceil()
* MT-006     — missing tests added here (PHASE_2_EXECUTION_PLAN.md Wave 5)
* PHASE_2_EXECUTION_PLAN.md §9 completion checklist — both tests required
"""
import pytest

from models.capacity_row import RemainingCapacityRow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(
    *,
    total_users: int = 100,
    target_engagement_rate: float = 0.10,
    historical_engaged_users: int = 0,
    target_engaged_users: int = 10,
    remaining_capacity: int = 10,
) -> RemainingCapacityRow:
    """Create a RemainingCapacityRow with explicit field values for unit tests.

    Use this helper when you want to test is_at_capacity() or utilization_pct()
    in isolation, without going through compute().
    """
    return RemainingCapacityRow(
        total_users=total_users,
        target_engagement_rate=target_engagement_rate,
        historical_engaged_users=historical_engaged_users,
        target_engaged_users=target_engaged_users,
        remaining_capacity=remaining_capacity,
    )


# ---------------------------------------------------------------------------
# compute() — TCC formula correctness
# ---------------------------------------------------------------------------

class TestCompute:
    """Tests for RemainingCapacityRow.compute()."""

    def test_compute_ceil_not_floor(self) -> None:
        """TCC-001 regression: 101 users × 10% must give 11, not 10.

        int(101 * 0.10) = int(10.1) = 10  (WRONG — floor truncation)
        math.ceil(101 * 0.10) = ceil(10.1) = 11  (CORRECT)

        This test will fail if math.ceil() is ever replaced with int() or
        math.floor().  It is the primary acceptance criterion for REM-003.
        """
        row = RemainingCapacityRow.compute(
            total_users=101,
            target_engagement_rate=0.10,
            historical_engaged_users=0,
        )
        assert row.target_engaged_users == 11, (
            "TCC-001: expected ceil(101*0.10)=11; "
            f"got {row.target_engaged_users}. "
            "math.ceil() must be used, not int()."
        )
        assert row.remaining_capacity == 11

    def test_compute_exact_boundary(self) -> None:
        """100 users × 10% = exactly 10.0 — ceil(10.0) = 10."""
        row = RemainingCapacityRow.compute(
            total_users=100,
            target_engagement_rate=0.10,
            historical_engaged_users=0,
        )
        assert row.target_engaged_users == 10
        assert row.remaining_capacity == 10

    def test_compute_remaining_clamps_to_zero(self) -> None:
        """When historical >= target, remaining_capacity must be 0 (not negative)."""
        row = RemainingCapacityRow.compute(
            total_users=50,
            target_engagement_rate=0.10,
            historical_engaged_users=100,  # already over target
        )
        # target_engaged = ceil(50 * 0.10) = ceil(5.0) = 5
        assert row.target_engaged_users == 5
        assert row.remaining_capacity == 0, (
            "remaining_capacity must be max(0, ...) — never negative"
        )

    def test_compute_zero_users(self) -> None:
        """Zero trigger-file users → target = 0, remaining = 0."""
        row = RemainingCapacityRow.compute(
            total_users=0,
            target_engagement_rate=0.10,
            historical_engaged_users=0,
        )
        assert row.target_engaged_users == 0
        assert row.remaining_capacity == 0

    def test_compute_zero_historical(self) -> None:
        """No prior engagements → remaining == target."""
        row = RemainingCapacityRow.compute(
            total_users=200,
            target_engagement_rate=0.25,
            historical_engaged_users=0,
        )
        # ceil(200 * 0.25) = ceil(50.0) = 50
        assert row.target_engaged_users == 50
        assert row.remaining_capacity == 50

    def test_compute_partial_historical(self) -> None:
        """Partial prior engagement reduces remaining_capacity correctly."""
        row = RemainingCapacityRow.compute(
            total_users=100,
            target_engagement_rate=0.20,
            historical_engaged_users=12,
        )
        # ceil(100 * 0.20) = 20; 20 - 12 = 8
        assert row.target_engaged_users == 20
        assert row.remaining_capacity == 8

    def test_compute_stores_inputs(self) -> None:
        """compute() preserves all input values on the returned row."""
        row = RemainingCapacityRow.compute(
            total_users=75,
            target_engagement_rate=0.40,
            historical_engaged_users=5,
        )
        assert row.total_users == 75
        assert row.target_engagement_rate == pytest.approx(0.40)
        assert row.historical_engaged_users == 5


# ---------------------------------------------------------------------------
# is_at_capacity()
# ---------------------------------------------------------------------------

class TestIsAtCapacity:
    """Tests for RemainingCapacityRow.is_at_capacity()."""

    def test_is_at_capacity_when_zero(self) -> None:
        """remaining_capacity == 0 → at capacity."""
        row = _make_row(remaining_capacity=0)
        assert row.is_at_capacity() is True

    def test_is_at_capacity_when_negative(self) -> None:
        """remaining_capacity < 0 → at capacity (over-consumed via direct construction)."""
        row = _make_row(remaining_capacity=-5)
        assert row.is_at_capacity() is True

    def test_is_at_capacity_when_positive(self) -> None:
        """remaining_capacity > 0 → NOT at capacity."""
        row = _make_row(remaining_capacity=10)
        assert row.is_at_capacity() is False

    def test_is_at_capacity_when_one(self) -> None:
        """remaining_capacity == 1 → still capacity available."""
        row = _make_row(remaining_capacity=1)
        assert row.is_at_capacity() is False


# ---------------------------------------------------------------------------
# utilization_pct()
# ---------------------------------------------------------------------------

class TestUtilizationPct:
    """Tests for RemainingCapacityRow.utilization_pct()."""

    def test_utilization_pct_basic(self) -> None:
        """40 of 100 engaged → 40.0%."""
        row = _make_row(
            target_engaged_users=100,
            historical_engaged_users=40,
        )
        assert row.utilization_pct() == pytest.approx(40.0)

    def test_utilization_pct_zero_target(self) -> None:
        """target_engaged_users == 0 → 0.0% (zero-division guard).

        This is the MT-006 zero-division guard test required by the
        PHASE_2_EXECUTION_PLAN.md completion checklist.
        """
        row = _make_row(
            target_engaged_users=0,
            historical_engaged_users=0,
        )
        assert row.utilization_pct() == 0.0

    def test_utilization_pct_fully_consumed(self) -> None:
        """100 of 100 engaged → 100.0%."""
        row = _make_row(
            target_engaged_users=100,
            historical_engaged_users=100,
        )
        assert row.utilization_pct() == pytest.approx(100.0)

    def test_utilization_pct_over_consumed(self) -> None:
        """Historical > target (can happen after target-rate reduction) → > 100%."""
        row = _make_row(
            target_engaged_users=10,
            historical_engaged_users=15,
        )
        assert row.utilization_pct() == pytest.approx(150.0)

    def test_utilization_pct_zero_historical(self) -> None:
        """No prior engagement → 0.0% utilization."""
        row = _make_row(
            target_engaged_users=50,
            historical_engaged_users=0,
        )
        assert row.utilization_pct() == pytest.approx(0.0)
