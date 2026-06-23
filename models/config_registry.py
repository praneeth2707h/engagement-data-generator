from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from models.ad_config import AdConfig
from models.channel_config import ChannelConfig
from models.rule_config import RuleConfig
from models.segment_config import SegmentConfig
from models.trigger_config import TriggerConfig
from models.enums import HistoricalWindow, HistoricalCampaignMatchMode  # REM-001: removed HistoricalMatchMode (wrong name) and TERMode (does not exist)
from utils.constants import (  # REM-004: named weight constants (BL-040, TD-018)
    DEFAULT_WEIGHT_ENGAGEMENT,
    DEFAULT_WEIGHT_PROFILE,
    DEFAULT_WEIGHT_CREATIVE,
    DEFAULT_WEIGHT_CHANNEL,
    DEFAULT_WEIGHT_RECENCY,
    DEFAULT_FREQUENCY_MAX,
)
from utils.exceptions import ConfigError


@dataclass(frozen=True)
class ConfigRegistry:
    """Central immutable configuration object for a single campaign run.

    Aggregates all campaign-level configuration: journey ads, triggers,
    segments, channels, rules, behavioral parameters, affinity settings,
    fatigue controls, historical engagement settings, and simulation bounds.

    Primary key: campaign_id. All engines receive a ConfigRegistry instance
    at construction time and treat it as read-only for the duration of the run.

    Fields follow Technical_Design.md Section 4.1 and the Addendum.
    """

    # -----------------------------------------------------------------------
    # Identity
    # -----------------------------------------------------------------------
    campaign_id: str
    campaign_name: str
    config_schema_version: str

    # -----------------------------------------------------------------------
    # Simulation bounds
    # -----------------------------------------------------------------------
    simulation_start_date: date
    simulation_end_date: date

    # -----------------------------------------------------------------------
    # Journey & delivery
    # -----------------------------------------------------------------------
    ads: tuple[AdConfig, ...]
    default_vendor: str
    cooling_period_days: int

    # -----------------------------------------------------------------------
    # Triggers & segments
    # -----------------------------------------------------------------------
    triggers: tuple[TriggerConfig, ...]
    segments: tuple[SegmentConfig, ...]

    # -----------------------------------------------------------------------
    # Channels
    # -----------------------------------------------------------------------
    channels: tuple[ChannelConfig, ...]

    # -----------------------------------------------------------------------
    # Validation rules
    # -----------------------------------------------------------------------
    rule_configs: dict[str, RuleConfig]

    # -----------------------------------------------------------------------
    # TER / engagement rate mode
    # -----------------------------------------------------------------------
    ter_mode: str  # TER mode string (no TERMode enum in V1 — plain string field)

    # -----------------------------------------------------------------------
    # Historical engagement settings (Addendum)
    # -----------------------------------------------------------------------
    historical_engagement_window: str  # HistoricalWindow enum value
    historical_window_days: int | None  # Used when window == CUSTOM
    historical_campaign_match: str  # HistoricalCampaignMatchMode enum value  # REM-001: was HistoricalMatchMode
    historical_campaign_ids: tuple[str, ...]  # Empty = current campaign only

    # -----------------------------------------------------------------------
    # Behavior & engagement scoring
    # -----------------------------------------------------------------------
    behavior_score_decay_days: int
    engagement_score_floor: float
    engagement_score_ceiling: float
    engagement_cooldown_days: int
    weekly_impression_cap: int
    weekly_click_cap: int
    weekly_open_cap: int
    weekly_engagement_cap: int

    # -----------------------------------------------------------------------
    # Affinity parameters
    # -----------------------------------------------------------------------
    affinity_boost_on_click: float
    affinity_decay_no_engage: float
    affinity_floor: float
    affinity_ceiling: float
    channel_affinity_weight: float
    creative_affinity_weight: float

    # -----------------------------------------------------------------------
    # Fatigue / frequency parameters
    # -----------------------------------------------------------------------
    fatigue_impression_threshold: int
    fatigue_decay_factor: float
    fatigue_recovery_days: int

    # -----------------------------------------------------------------------
    # Admin / override flags (Addendum)
    # -----------------------------------------------------------------------
    admin_override: bool
    allow_reentry: bool
    reentry_cooldown_days: int

    # -----------------------------------------------------------------------
    # Scoring weights (SIM-001 / SIM-002 — Category B: Advanced Configurable)
    # REM-004: added in Wave 2 of Phase 2 remediation (MM-007, MM-008, BL-010).
    # Default values sourced from utils/constants.py to avoid literal drift.
    # __post_init__ enforces that the five float weights sum to 1.0 ±0.001.
    # -----------------------------------------------------------------------
    scoring_weight_engagement: float = DEFAULT_WEIGHT_ENGAGEMENT
    """Weight for the engagement_score component (default 0.30)."""

    scoring_weight_profile: float = DEFAULT_WEIGHT_PROFILE
    """Weight for the behavior-profile component (default 0.25)."""

    scoring_weight_creative: float = DEFAULT_WEIGHT_CREATIVE
    """Weight for the creative-affinity component (default 0.15)."""

    scoring_weight_channel: float = DEFAULT_WEIGHT_CHANNEL
    """Weight for the channel-affinity component (default 0.15)."""

    scoring_weight_recency: float = DEFAULT_WEIGHT_RECENCY
    """Weight for the reach-recency component (default 0.15)."""

    frequency_max: int = DEFAULT_FREQUENCY_MAX
    """Max days since last reach for recency normalisation (default 30).

    A user reached frequency_max or more days ago receives a recency score
    of 0.0.  A user reached today receives 1.0.  Values are sourced from
    MM-008 / Technical_Design_Addendum §ReachRecency.
    """

    # -----------------------------------------------------------------------
    # Reserved fields (no-op in V1)
    # -----------------------------------------------------------------------
    strict_priority_validation: bool = False
    """Reserved for future strict-audit mode (CFG-NEW-001).

    When False (V1 default), identical-priority trigger ties are resolved
    alphabetically per ARCH-013.  When True (future V2), a ValidationError
    will be raised instead of applying the alphabetical tiebreak.
    This field is a no-op in V1 — it is present only to preserve the
    option without requiring a schema migration.
    """

    # -----------------------------------------------------------------------
    # Derived field (computed in __post_init__)
    # -----------------------------------------------------------------------
    simulation_days: int = field(init=False)

    def __post_init__(self) -> None:
        """Compute derived fields and run basic invariant checks.

        Checks performed (in order):
        1. simulation_end_date >= simulation_start_date.
        2. At least one AdConfig provided.
        3. At least one TriggerConfig provided.
        4. Scoring weights sum to 1.0 ±0.001 (REM-004 / SIM-001).

        simulation_days is derived from simulation_end_date - simulation_start_date + 1.
        Uses object.__setattr__ because the dataclass is frozen=True.
        """
        delta = (self.simulation_end_date - self.simulation_start_date).days + 1
        if delta < 1:
            raise ConfigError(
                f"simulation_end_date ({self.simulation_end_date}) must be >= "
                f"simulation_start_date ({self.simulation_start_date})."
            )
        object.__setattr__(self, "simulation_days", delta)

        if not self.ads:
            raise ConfigError("ConfigRegistry: at least one AdConfig is required.")
        if not self.triggers:
            raise ConfigError("ConfigRegistry: at least one TriggerConfig is required.")

        # ARCH-019: Defense-in-depth priority validation.
        # TriggerConfig.__post_init__ provides the primary guard (priority >= 1).
        # This guard catches any construction path that bypasses TriggerConfig validation.
        for t in self.triggers:
            if t.priority is None or t.priority < 1:
                raise ConfigError(
                    f"TriggerConfig '{t.trigger_name}' has invalid priority "
                    f"({t.priority!r}). All triggers must have an explicit "
                    f"integer priority >= 1. See ARCH-019."
                )

        # REM-004: Scoring weight sum validation (SIM-001 / SIM-002).
        # Tolerance of 0.001 accommodates IEEE 754 floating-point rounding
        # when weights are supplied from JSON (e.g., 0.333... × 3 != 1.0 exactly).
        weight_sum = (
            self.scoring_weight_engagement
            + self.scoring_weight_profile
            + self.scoring_weight_creative
            + self.scoring_weight_channel
            + self.scoring_weight_recency
        )
        if abs(weight_sum - 1.0) > 0.001:
            raise ConfigError(
                f"Scoring weights must sum to 1.0 (±0.001); got {weight_sum:.6f}. "
                f"Weights: engagement={self.scoring_weight_engagement}, "
                f"profile={self.scoring_weight_profile}, "
                f"creative={self.scoring_weight_creative}, "
                f"channel={self.scoring_weight_channel}, "
                f"recency={self.scoring_weight_recency}."
            )

    # -----------------------------------------------------------------------
    # Ad accessors
    # -----------------------------------------------------------------------

    def get_ad_names(self) -> list[str]:
        """Return ad names sorted by ad_order (ascending).

        Returns:
            List of ad_name strings in journey sequence order.
        """
        return [ad.ad_name for ad in sorted(self.ads, key=lambda a: a.ad_order)]

    def get_ad_by_name(self, ad_name: str) -> AdConfig | None:
        """Return the AdConfig with the given ad_name, or None if not found.

        O(n) linear scan over all ads.

        Args:
            ad_name: The ad identifier to look up.

        Returns:
            Matching AdConfig or None.
        """
        for ad in self.ads:
            if ad.ad_name == ad_name:
                return ad
        return None

    def get_ad_by_order(self, order: int) -> AdConfig | None:
        """Return the AdConfig at the given 1-based journey position, or None.

        O(n) linear scan over all ads.

        Args:
            order: 1-based ad_order index.

        Returns:
            Matching AdConfig or None.
        """
        for ad in self.ads:
            if ad.ad_order == order:
                return ad
        return None

    def get_effective_vendor(self, ad: AdConfig) -> str:
        """Return the effective vendor for an ad, applying per-ad override (I-001).

        Per-ad vendor (AdConfig.vendor) takes precedence over campaign-level
        default_vendor. If the ad has no vendor override, falls back to
        self.default_vendor.

        Args:
            ad: The AdConfig whose vendor to resolve.

        Returns:
            Vendor name string.
        """
        if ad.vendor is not None:
            return ad.vendor
        return self.default_vendor

    # -----------------------------------------------------------------------
    # Rule accessors
    # -----------------------------------------------------------------------

    def get_rule_config(self, rule_id: str) -> RuleConfig | None:
        """Return the RuleConfig for the given rule_id, or None if not found.

        Args:
            rule_id: Rule identifier (e.g., "HR-001").

        Returns:
            Matching RuleConfig or None.
        """
        return self.rule_configs.get(rule_id)

    def is_rule_enabled(self, rule_id: str) -> bool:
        """Return True if the rule exists and is enabled.

        Returns False if the rule_id is not found in rule_configs.

        Args:
            rule_id: Rule identifier to check.

        Returns:
            True if rule exists and RuleConfig.enabled is True, else False.
        """
        rule = self.rule_configs.get(rule_id)
        if rule is None:
            return False
        return rule.enabled

    # -----------------------------------------------------------------------
    # Trigger accessors
    # -----------------------------------------------------------------------

    def get_trigger_by_name(self, trigger_name: str) -> TriggerConfig | None:
        """Return the TriggerConfig with the given name, or None.

        Args:
            trigger_name: The trigger identifier to look up.

        Returns:
            Matching TriggerConfig or None.
        """
        for trigger in self.triggers:
            if trigger.trigger_name == trigger_name:
                return trigger
        return None

    def get_triggers_by_priority(self) -> list[TriggerConfig]:
        """Return all triggers sorted by priority ascending (1 = highest).

        Returns:
            List of TriggerConfig sorted by priority.
        """
        return sorted(self.triggers, key=lambda t: t.priority)

    # -----------------------------------------------------------------------
    # Segment accessors
    # -----------------------------------------------------------------------

    def get_segment_by_name(self, segment_name: str) -> SegmentConfig | None:
        """Return the SegmentConfig with the given name, or None.

        Args:
            segment_name: The segment identifier to look up.

        Returns:
            Matching SegmentConfig or None.
        """
        for segment in self.segments:
            if segment.segment_name == segment_name:
                return segment
        return None

    def get_segments_by_priority(self) -> list[SegmentConfig]:
        """Return all segments sorted by priority ascending (1 = highest).

        Returns:
            List of SegmentConfig sorted by priority.
        """
        return sorted(self.segments, key=lambda s: s.priority)

    # -----------------------------------------------------------------------
    # Channel accessors
    # -----------------------------------------------------------------------

    def get_channel_config(self, channel_name: str) -> ChannelConfig | None:
        """Return the ChannelConfig for the given channel name, or None.

        Args:
            channel_name: Channel identifier (e.g., "Email", "Display").

        Returns:
            Matching ChannelConfig or None.
        """
        for channel in self.channels:
            if channel.channel_name == channel_name:
                return channel
        return None

    # -----------------------------------------------------------------------
    # Historical window helpers
    # -----------------------------------------------------------------------

    def get_historical_cutoff_date(self, as_of: date) -> date | None:
        """Compute the historical cutoff date for the configured window.

        Returns None for All_Time (no cutoff). For CUSTOM, uses
        historical_window_days. For named windows, uses fixed day counts.

        Args:
            as_of: Reference date (typically simulation_start_date).

        Returns:
            Cutoff date, or None for All_Time.
        """
        from datetime import timedelta

        window = self.historical_engagement_window
        if window == HistoricalWindow.ALL_TIME.value:
            return None
        elif window == HistoricalWindow.LAST_90.value:
            return as_of - timedelta(days=90)
        elif window == HistoricalWindow.LAST_180.value:
            return as_of - timedelta(days=180)
        elif window == HistoricalWindow.LAST_365.value:
            return as_of - timedelta(days=365)
        elif window == HistoricalWindow.CUSTOM.value:
            days = self.historical_window_days or 0
            return as_of - timedelta(days=days)
        return None


__all__ = ["ConfigRegistry"]
