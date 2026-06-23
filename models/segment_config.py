"""Immutable configuration for a single user segment."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SegmentConfig:
    """Immutable configuration for a single user segment.

    Segments classify users for targeting and reporting. Priority 1 = highest.

    Attributes:
        segment_name: Unique segment identifier.
        priority: Assignment priority. Lower number = higher priority. Must be >= 1.
        distribution_pct: Expected % of triggered users in this segment (0.0–100.0).
    """
    segment_name: str
    priority: int
    distribution_pct: float = 0.0

    def __post_init__(self) -> None:
        if self.priority < 1:
            raise ValueError(
                f"SegmentConfig '{self.segment_name}': priority must be >= 1, got {self.priority}"
            )
        if not (0.0 <= self.distribution_pct <= 100.0):
            raise ValueError(
                f"SegmentConfig '{self.segment_name}': distribution_pct must be 0.0–100.0, "
                f"got {self.distribution_pct}"
            )


__all__ = ["SegmentConfig"]
