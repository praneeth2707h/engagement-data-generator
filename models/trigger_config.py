"""Immutable configuration for a single trigger segment."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerConfig:
    """Immutable configuration for a single trigger segment.

    Triggers determine which users enter the journey. Priority 1 = highest.

    Attributes:
        trigger_name: Unique trigger identifier.
        priority: Evaluation priority. Lower number = higher priority. Must be >= 1.
        engagement_rate_target: Target engagement rate for this trigger (0.0–1.0).
        distribution_pct: Expected % of triggered users (0.0–100.0). Default 0.0.
    """
    trigger_name: str
    priority: int
    engagement_rate_target: float
    distribution_pct: float = 0.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.engagement_rate_target <= 1.0):
            raise ValueError(
                f"TriggerConfig '{self.trigger_name}': engagement_rate_target must be 0.0–1.0, "
                f"got {self.engagement_rate_target}"
            )
        if not (0.0 <= self.distribution_pct <= 100.0):
            raise ValueError(
                f"TriggerConfig '{self.trigger_name}': distribution_pct must be 0.0–100.0, "
                f"got {self.distribution_pct}"
            )
        if self.priority < 1:
            raise ValueError(
                f"TriggerConfig '{self.trigger_name}': priority must be >= 1, got {self.priority}"
            )


__all__ = ["TriggerConfig"]
