"""Immutable configuration for a single delivery channel."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelConfig:
    """Immutable configuration for a single delivery channel.

    Nine fields total. Display channels have no open rate or timing distribution.
    Email/WhatsApp have open rates and day 1–3 timing fractions.

    Attributes:
        channel_name: Channel identifier (e.g., "Email", "Display").
        target_ctr: Target click-through rate.
        target_open_rate: Target open rate. None for Display channels.
        email_day1_min/max: Min/max fraction of opens expected on Day 1 after send.
        email_day2_min/max: Min/max fraction expected on Day 2 after send.
        email_day3_min/max: Min/max fraction expected on Day 3 after send.
    """
    channel_name: str
    target_ctr: float
    target_open_rate: float | None = None
    email_day1_min: float | None = None
    email_day1_max: float | None = None
    email_day2_min: float | None = None
    email_day2_max: float | None = None
    email_day3_min: float | None = None
    email_day3_max: float | None = None

    def is_display(self) -> bool:
        return self.channel_name in {"Endemic_Display", "Programmatic_Display", "Banner", "Display"}

    def is_email(self) -> bool:
        return self.channel_name == "Email"

    def is_whatsapp(self) -> bool:
        return self.channel_name == "WhatsApp"

    def has_timing_distribution(self) -> bool:
        return self.email_day1_min is not None

    def get_day_range(self, day: int) -> tuple[float, float] | None:
        if day == 1:
            if self.email_day1_min is not None and self.email_day1_max is not None:
                return (self.email_day1_min, self.email_day1_max)
        elif day == 2:
            if self.email_day2_min is not None and self.email_day2_max is not None:
                return (self.email_day2_min, self.email_day2_max)
        elif day == 3:
            if self.email_day3_min is not None and self.email_day3_max is not None:
                return (self.email_day3_min, self.email_day3_max)
        return None


__all__ = ["ChannelConfig"]
