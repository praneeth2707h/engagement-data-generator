"""Project-wide enumerations for the Engagement Data Generator.

All enums used in production code are defined here. Enum .value strings
match the DataFrame cell values defined in utils/constants.py — always use
enums in logic and enum.value for DataFrame operations.

References
----------
* PROJECT_HANDOFF.md §Infrastructure — "models/enums.py fully implemented"
* Technical_Design_Addendum.md §HistoricalWindow, §HistoricalCampaignMatchMode
"""
from __future__ import annotations
from enum import Enum


class RuleSeverity(str, Enum):
    """Severity levels for validation rules (Validation_Rules_Catalog.md)."""
    HARD = "Hard"
    SOFT = "Soft"
    ADVISORY = "Advisory"


class EligibilityStatus(str, Enum):
    """User eligibility states for journey entry (User_State_Dictionary.md).

    Canonical values (Phase 3+ — ARCH-015):
        NEW      — user has never entered this campaign.
        ACTIVE   — user is currently in an active journey.
        COOLING  — user completed a journey; cooling period still running.
        RE_ENTRY — cooling period expired; user eligible to re-enter (allow_reentry=True).
        SKIPPED  — user was in-scope but excluded due to capacity constraints.
        EXCLUDED — user is permanently ineligible (hard exclusion, DROPPED journey,
                   or allow_reentry=False).

    Deprecated (Phase 1/2 placeholder values — do not use in Phase 3+):
        ELIGIBLE   — deprecated alias; use ACTIVE.
        INELIGIBLE — deprecated alias; use SKIPPED.
        COMPLETED  — deprecated alias; use COOLING or RE_ENTRY depending on cooling state.
    """
    # ── Phase 3 canonical values ─────────────────────────────────────────
    NEW      = "New"
    ACTIVE   = "Active"
    COOLING  = "Cooling"
    RE_ENTRY = "Re_Entry"
    SKIPPED  = "Skipped"
    EXCLUDED = "Excluded"

    # ── Deprecated — retained for backward import compatibility only ─────
    # Do not use these in any Phase 3+ code. They will be removed in V2.
    ELIGIBLE   = "Eligible"    # deprecated — use ACTIVE
    INELIGIBLE = "Ineligible"  # deprecated — use SKIPPED
    COMPLETED  = "Completed"   # deprecated — use COOLING or RE_ENTRY



class JourneyStatus(str, Enum):
    """User journey progression states (User_State_Dictionary.md)."""
    NOT_STARTED = "Not_Started"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    DROPPED = "Dropped"


class BehaviorProfile(str, Enum):
    """User behavior profile classifications (Technical_Design.md §SIM-003)."""
    HIGHLY_ENGAGED = "Highly_Engaged"
    MODERATE = "Moderate"
    PASSIVE = "Passive"
    DORMANT = "Dormant"


class ChannelType(str, Enum):
    """Delivery channel types (Architecture_v2.md §Channels)."""
    EMAIL = "Email"
    WHATSAPP = "WhatsApp"
    ENDEMIC_DISPLAY = "Endemic_Display"
    PROGRAMMATIC_DISPLAY = "Programmatic_Display"
    BANNER = "Banner"
    DISPLAY = "Display"


class ActionType(str, Enum):
    """User action types for engagement event recording (Output_Data_Dictionary.md)."""
    IMPRESSION = "Impression"
    OPEN = "Open"
    CLICK = "Click"


class HistoricalWindow(str, Enum):
    """Historical engagement lookback window options (Technical_Design_Addendum.md)."""
    ALL_TIME = "All_Time"
    LAST_90 = "Last_90_Days"
    LAST_180 = "Last_180_Days"
    LAST_365 = "Last_365_Days"
    CUSTOM = "Custom"


class HistoricalCampaignMatchMode(str, Enum):
    """How prior campaign data is matched against the current campaign.

    STRICT  — only include records from campaigns listed in historical_campaign_ids.
    ALL     — include records from any campaign for the user.
    """
    STRICT = "Strict"
    ALL = "All"


class RuleStatus(str, Enum):
    """Outcome status returned by a validation rule evaluation."""
    PASS = "Pass"
    FAIL = "Fail"
    SKIP = "Skip"


__all__ = [
    "RuleSeverity",
    "EligibilityStatus",
    "JourneyStatus",
    "BehaviorProfile",
    "ChannelType",
    "ActionType",
    "HistoricalWindow",
    "HistoricalCampaignMatchMode",
    "RuleStatus",
]
