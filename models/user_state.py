from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date

from models.enums import EligibilityStatus, JourneyStatus, BehaviorProfile, ChannelType  # REM-002: Channel → ChannelType

from utils.constants import DEFAULT_CHANNEL_AFFINITY as _DEFAULT_CHANNEL_AFFINITY
from utils.constants import DEFAULT_ENGAGEMENT_SCORE as _DEFAULT_ENGAGEMENT_SCORE
from utils.constants import DEFAULT_CREATIVE_AFFINITY as _DEFAULT_CREATIVE_AFFINITY

@dataclass
class UserState:
    """Mutable state record for a single user within a campaign run.

    Primary key: (campaign_id, user_id). State is updated in-place by the
    Journey, Behavior, and Timing engines each simulation day.

    Creative affinities are stored as a dict[ad_name → float32-range value].
    DataFrame representation uses dynamic columns Creative_Affinity_{ad_name}.
    """
    campaign_id: str
    user_id: str
    trigger_name: str | None
    segment: str | None
    eligibility_status: str
    journey_status: str
    journey_start_date: date | None
    current_ad: str | None
    days_in_ad: int | None
    ad_click_received: bool
    journey_completion_date: date | None
    cooling_period_end: date | None
    behavior_profile: str
    engagement_score: float
    channel_affinity_display: float
    channel_affinity_email: float
    channel_affinity_whatsapp: float
    last_engagement_date: date | None
    engagement_cooldown_end: date | None
    weekly_impressions: int
    weekly_clicks: int
    weekly_opens: int
    weekly_engagements: int
    total_lifetime_engagements: int
    last_reached_date: date | None
    run_count: int
    state_as_of_date: date
    trigger_history: str | None
    first_trigger_name: str | None
    first_trigger_date: date | None
    total_trigger_appearances: int
    channel: str | None
    vendor: str | None
    historical_engaged: bool = False
    """True if this user had at least one qualifying engagement in the historical
    window (BIZ-004 / BIZ-011). Set by Stage 3 (User State Init).
    Read by Stage 4 (Audience Resolution) compute_remaining_capacity()."""

    is_valid: bool = True
    """True while all evaluated validation rules pass. Set to False by
    ValidationEngine when any hard or soft rule FAIL is recorded for this user.
    Read by Stage 11 (Excel Export) for ValidationReport generation."""

    creative_affinities: dict[str, float] = field(default_factory=dict)

    @classmethod
    def new(
        cls,
        campaign_id: str,
        user_id: str,
        state_as_of_date: date,
        ad_names: list[str],
    ) -> "UserState":
        """Create a brand-new user state with all defaults.

        New users get:
          - EligibilityStatus.NEW, JourneyStatus.NOT_STARTED
          - BehaviorProfile.MODERATE
          - engagement_score = 0.5
          - channel affinities = 0.5 (neutral per R-CA-003)
          - creative_affinities = {ad_name: 0.5 for each ad}
          - all counters = 0

        Args:
            campaign_id: Campaign identifier.
            user_id: User identifier.
            state_as_of_date: The date this state is initialized.
            ad_names: List of all ad names in the campaign journey.

        Returns:
            A new UserState with default values.
        """
        return cls(
            campaign_id=campaign_id,
            user_id=user_id,
            trigger_name=None,
            segment=None,
            eligibility_status=EligibilityStatus.NEW.value,
            journey_status=JourneyStatus.NOT_STARTED.value,
            journey_start_date=None,
            current_ad=None,
            days_in_ad=None,
            ad_click_received=False,
            journey_completion_date=None,
            cooling_period_end=None,
            behavior_profile=BehaviorProfile.MODERATE.value,
            engagement_score=_DEFAULT_ENGAGEMENT_SCORE,
            channel_affinity_display=_DEFAULT_CHANNEL_AFFINITY,
            channel_affinity_email=_DEFAULT_CHANNEL_AFFINITY,
            channel_affinity_whatsapp=_DEFAULT_CHANNEL_AFFINITY,
            last_engagement_date=None,
            engagement_cooldown_end=None,
            weekly_impressions=0,
            weekly_clicks=0,
            weekly_opens=0,
            weekly_engagements=0,
            total_lifetime_engagements=0,
            last_reached_date=None,
            run_count=0,
            state_as_of_date=state_as_of_date,
            trigger_history=None,
            first_trigger_name=None,
            first_trigger_date=None,
            total_trigger_appearances=0,
            channel=None,
            vendor=None,
            creative_affinities={ad: _DEFAULT_CREATIVE_AFFINITY for ad in ad_names},
        )

    def get_channel_affinity(self, channel_name: str) -> float:
        """Return channel affinity for the given channel name.

        Args:
            channel_name: One of "Display", "Email", "WhatsApp" (or sub-types).

        Returns:
            Float affinity value in [0.0, 1.0]. Defaults to 0.5 if unknown.
        """
        normalized = channel_name.strip()
        if normalized in {"Display", "Endemic_Display", "Programmatic_Display", "Banner"}:
            return self.channel_affinity_display
        elif normalized == "Email":
            return self.channel_affinity_email
        elif normalized == "WhatsApp":
            return self.channel_affinity_whatsapp
        return _DEFAULT_CHANNEL_AFFINITY

    def get_creative_affinity(self, ad_name: str) -> float:
        """Return creative affinity for the given ad name.

        Args:
            ad_name: Ad name matching an AdConfig.ad_name.

        Returns:
            Float affinity in [0.0, 1.0]. Returns 0.5 if not found.
        """
        return self.creative_affinities.get(ad_name, _DEFAULT_CHANNEL_AFFINITY)

    def reset_weekly_counters(self) -> None:
        """Reset all weekly counters to 0. Called at ISO week boundary (Monday). C-003."""
        self.weekly_impressions = 0
        self.weekly_clicks = 0
        self.weekly_opens = 0
        self.weekly_engagements = 0

    def is_in_cooldown(self, as_of: date) -> bool:
        """Return True if user is currently in engagement cooldown."""
        if self.engagement_cooldown_end is None:
            return False
        return as_of <= self.engagement_cooldown_end

    def is_in_journey_cooling(self, as_of: date) -> bool:
        """Return True if user is currently in post-journey cooling period."""
        if self.cooling_period_end is None:
            return False
        return as_of <= self.cooling_period_end

    def primary_key(self) -> tuple[str, str]:
        """Return composite primary key (campaign_id, user_id). ARCH-002."""
        return (self.campaign_id, self.user_id)


__all__ = ["UserState"]
