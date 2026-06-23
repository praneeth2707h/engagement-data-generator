"""Project-wide named constants for the Engagement Data Generator.

All magic numbers used in model field defaults or algorithmic formulas must
be sourced from this module rather than scattered as inline literals.  Keeping
defaults here prevents them from drifting independently across the codebase.

Design notes
------------
* Constants are module-level names (not an Enum) so they can be used directly
  as dataclass field defaults without a `.value` dereference.
* Changing a constant here changes the default everywhere it is imported.
  Any such change requires a review of the corresponding Wave 5 tests that
  assert the concrete default value.

References
----------
* SIM-001  — composite scoring formula weights
* SIM-002  — weights are Category B (Advanced Configurable) in ConfigRegistry
* REM-004  — added in Wave 2 of Phase 2 remediation (BL-040, TD-018)
* PROJECT_DECISIONS.md — all defaults recorded alongside their decision rationale
"""

# ---------------------------------------------------------------------------
# Scoring weight defaults (SIM-001 / SIM-002)
# These five values MUST sum to 1.0. The ConfigRegistry.__post_init__
# validator enforces this at construction time (tolerance ±0.001).
# ---------------------------------------------------------------------------

DEFAULT_WEIGHT_ENGAGEMENT: float = 0.30
"""Weight for the engagement_score component of the composite score."""

DEFAULT_WEIGHT_PROFILE: float = 0.25
"""Weight for the behavior-profile component of the composite score."""

DEFAULT_WEIGHT_CREATIVE: float = 0.15
"""Weight for the creative-affinity component of the composite score."""

DEFAULT_WEIGHT_CHANNEL: float = 0.15
"""Weight for the channel-affinity component of the composite score."""

DEFAULT_WEIGHT_RECENCY: float = 0.15
"""Weight for the reach-recency component of the composite score."""

# Sanity assertion: weights must sum to exactly 1.0 at module load time.
# This will surface an error immediately if a future edit inadvertently
# introduces a sum ≠ 1.0 in this file before it propagates to running code.
_WEIGHT_SUM = (
    DEFAULT_WEIGHT_ENGAGEMENT
    + DEFAULT_WEIGHT_PROFILE
    + DEFAULT_WEIGHT_CREATIVE
    + DEFAULT_WEIGHT_CHANNEL
    + DEFAULT_WEIGHT_RECENCY
)
assert abs(_WEIGHT_SUM - 1.0) < 1e-9, (
    f"DEFAULT_WEIGHT_* constants do not sum to 1.0; got {_WEIGHT_SUM}. "
    "Fix the values in utils/constants.py."
)

# ---------------------------------------------------------------------------
# Reach-recency normalisation
# ---------------------------------------------------------------------------

DEFAULT_FREQUENCY_MAX: int = 30
"""Maximum days-since-last-reach used in the recency normalisation formula.

Values above this are clamped to 0.0 recency; values of 0 produce 1.0 recency.
Sourced from Technical_Design_Addendum §ReachRecency (MM-008 / REM-004).
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_WEIGHT_ENGAGEMENT",
    "DEFAULT_WEIGHT_PROFILE",
    "DEFAULT_WEIGHT_CREATIVE",
    "DEFAULT_WEIGHT_CHANNEL",
    "DEFAULT_WEIGHT_RECENCY",
    "DEFAULT_FREQUENCY_MAX",
]

# ── Default initialization values for UserState fields ────────────────────
# Used by UserState.new() and UserStateManager.initialize().
# All three default to 0.5 (neutral/mid-range) to avoid cold-start bias.
DEFAULT_ENGAGEMENT_SCORE   = 0.5   # Initial engagement_score for new users
DEFAULT_CHANNEL_AFFINITY   = 0.5   # Initial channel_affinity_* for new users
DEFAULT_CREATIVE_AFFINITY  = 0.5   # Initial creative_affinities[ad] for new users

# ── Trigger history serialization ─────────────────────────────────────────
# Pipe delimiter for trigger_history string field (ARCH-017).
# All code that reads or writes trigger_history must use this constant.
TRIGGER_HISTORY_DELIMITER  = "|"
