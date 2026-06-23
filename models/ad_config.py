"""Immutable configuration for a single Ad in the journey."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AdConfig:
    """Immutable configuration for a single Ad in the journey.

    Attributes:
        ad_name: Unique ad identifier (alphanumeric + underscore).
        ad_order: 1-based position in the journey sequence.
        duration_days: How many days a user stays on this ad.
        move_on_click: If True, advance to next ad on click.
        channel: Channel name (e.g., "Email", "Display").
        vendor: Per-ad vendor override. None means use campaign-level vendor.
        target_ctr: Target click-through rate. None falls back to channel default.
    """
    ad_name: str
    ad_order: int
    duration_days: int
    move_on_click: bool
    channel: str
    vendor: str | None
    target_ctr: float | None

    def creative_affinity_column(self) -> str:
        return f"Creative_Affinity_{self.ad_name}"

    def is_display_channel(self) -> bool:
        return self.channel in {"Endemic_Display", "Programmatic_Display", "Banner", "Display"}

    def is_email_channel(self) -> bool:
        return self.channel == "Email"

    def is_whatsapp_channel(self) -> bool:
        return self.channel == "WhatsApp"


__all__ = ["AdConfig"]
