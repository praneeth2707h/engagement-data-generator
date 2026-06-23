"""Trigger Capacity Consumption (TCC) row model.

This module defines RemainingCapacityRow — the per-trigger capacity record
produced by the Audience Manager (Stage 4 of the 11-stage pipeline).

TCC formula (PROJECT_HANDOFF.md Section 8, BIZ-003, BIZ-004):
    Target_Engaged_Users = ceil(Current_Trigger_File_Users × Target_Engagement_Rate)
    Remaining_Capacity   = max(0, Target_Engaged_Users − Historical_Engaged_Users)

Key correctness constraint (TCC-001 / REM-003):
    math.ceil() MUST be used — NOT int() (floor truncation).
    Example: 101 users × 10% → ceil(10.1) = 11, not 10.
    Using int() causes systematic under-generation of engagement events.

Design notes
------------
* RemainingCapacityRow is a plain dataclass (not frozen) because the
  Audience Manager may update remaining_capacity in-place as users are
  assigned during a single simulation day.
* The compute() classmethod is the only supported construction path that
  derives target_engaged_users and remaining_capacity from inputs.
  Direct construction is allowed for test fixtures.
* utilization_pct() guards against zero-division when target_engaged_users
  is 0 (e.g., trigger file is empty or engagement rate rounds to 0).

References
----------
* TCC-001    — defect: int() used instead of math.ceil() (RESOLVED by REM-003)
* DOC-002    — defect: docstring said "Floor" — updated to "Ceil" (REM-003)
* BIZ-003    — TCC and TER are separate; only TCC drives the engine
* BIZ-004    — Historical window default Last 90 Days (TCC only)
* ARCH-003   — Stage 4 (Audience Resolution) owns TCC computation
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class RemainingCapacityRow:
    """Per-trigger Trigger Capacity Consumption (TCC) record.

    Stores both the raw inputs and the two derived values
    (target_engaged_users, remaining_capacity) so that downstream stages
    can inspect the full picture without recomputing.

    Attributes
    ----------
    total_users:
        Number of users present in the trigger file for this trigger
        (i.e., Current_Trigger_File_Users in the TCC formula).
    target_engagement_rate:
        Fractional engagement rate target from TriggerConfig
        (e.g., 0.10 for 10%).
    historical_engaged_users:
        Count of users already engaged for this trigger within the
        configured historical window (TCC windowed denominator).
    target_engaged_users:
        Ceil(total_users × target_engagement_rate).  Computed by
        compute() — the number of users we aim to engage in this run.
    remaining_capacity:
        max(0, target_engaged_users − historical_engaged_users).
        The number of additional users the engine may engage today.
        Zero means this trigger is at or over capacity.

    Notes
    -----
    The "Ceil" in the class name and formula is intentional and load-bearing.
    Never substitute int() or math.floor() — doing so will cause systematic
    under-generation (TCC-001).
    """

    total_users: int
    target_engagement_rate: float
    historical_engaged_users: int
    target_engaged_users: int
    remaining_capacity: int

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def compute(
        cls,
        total_users: int,
        target_engagement_rate: float,
        historical_engaged_users: int,
    ) -> "RemainingCapacityRow":
        """Compute TCC for a single trigger and return the capacity row.

        Uses math.ceil() for Target_Engaged_Users (TCC-001 fix, REM-003).

        TCC formula:
            Target_Engaged_Users = ceil(total_users × target_engagement_rate)
            Remaining_Capacity   = max(0, target_engaged_users
                                         − historical_engaged_users)

        Args:
            total_users:
                Number of users in the trigger file for this trigger.
            target_engagement_rate:
                Fractional engagement rate target (0.0–1.0 inclusive).
            historical_engaged_users:
                Users already engaged within the historical window.

        Returns:
            RemainingCapacityRow with all five fields populated.

        Examples
        --------
        Boundary case that distinguishes ceil() from int() (floor):
            >>> row = RemainingCapacityRow.compute(101, 0.10, 0)
            >>> row.target_engaged_users
            11
            >>> row.remaining_capacity
            11

        Standard case:
            >>> row = RemainingCapacityRow.compute(100, 0.10, 3)
            >>> row.target_engaged_users
            10
            >>> row.remaining_capacity
            7
        """
        # REM-003: math.ceil() — never int() or math.floor()
        target_engaged = math.ceil(total_users * target_engagement_rate)
        remaining = max(0, target_engaged - historical_engaged_users)
        return cls(
            total_users=total_users,
            target_engagement_rate=target_engagement_rate,
            historical_engaged_users=historical_engaged_users,
            target_engaged_users=target_engaged,
            remaining_capacity=remaining,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_at_capacity(self) -> bool:
        """Return True when no further engagement capacity remains.

        Returns True when remaining_capacity <= 0, meaning the trigger
        has reached or exceeded its historical engagement target for this
        window.  The Audience Manager uses this to skip users for a trigger
        that is fully consumed.

        Returns:
            bool: True if remaining_capacity <= 0, False otherwise.
        """
        return self.remaining_capacity <= 0

    def utilization_pct(self) -> float:
        """Return the percentage of target engagement already consumed.

        Computed as (historical_engaged_users / target_engaged_users) × 100.
        Returns 0.0 when target_engaged_users is zero (empty trigger file
        or engagement rate rounds to zero) to avoid ZeroDivisionError.

        Returns:
            float: Utilization percentage in range [0.0, +inf).
            Values above 100.0 indicate the historical window already
            exceeded the current target (possible after target-rate reduction).
        """
        if self.target_engaged_users == 0:
            return 0.0
        return (self.historical_engaged_users / self.target_engaged_users) * 100.0


__all__ = ["RemainingCapacityRow"]
