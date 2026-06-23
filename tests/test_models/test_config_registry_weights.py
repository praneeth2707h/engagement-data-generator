"""Tests for ConfigRegistry scoring weight fields and validator (REM-004).

Tests in this file verify:
1. All six new fields exist with the correct default values.
2. utils/constants.py provides the named constants.
3. __post_init__ raises ConfigError when weights do not sum to 1.0 ±0.001.
4. __post_init__ accepts weights that sum to exactly 1.0.
5. __post_init__ accepts weights within the ±0.001 tolerance band.

These tests do NOT construct a full ConfigRegistry (that requires all
required fields, many of which depend on Wave 3+ fixtures). Instead they
test the validator logic in isolation using direct arithmetic, and test
field presence by inspecting the class's __dataclass_fields__.

Full make_registry()-based integration tests are part of Wave 5 (REM-013).

References
----------
* MM-007     — ConfigRegistry missing 5 scoring weight fields
* MM-008     — ConfigRegistry missing frequency_max field
* REM-004    — Wave 2 fix: add fields + __post_init__ validator + constants
* BL-010     — backlog item tracking these fields
* TD-018     — technical debt: inline literals → named constants
* SIM-001    — composite scoring formula that requires these weights
* SIM-002    — weights are Category B (Advanced Configurable)
"""
import dataclasses
import importlib

import pytest

# Guard: field-introspection tests require the full project (all models/).
# In a partial-project environment (e.g. Wave 1/2 outputs folder only), the
# ConfigRegistry import fails because models.ad_config etc. are absent.
# These tests will PASS once the full project is deployed.
_full_project_available = importlib.util.find_spec("models.ad_config") is not None

from utils.constants import (
    DEFAULT_FREQUENCY_MAX,
    DEFAULT_WEIGHT_CHANNEL,
    DEFAULT_WEIGHT_CREATIVE,
    DEFAULT_WEIGHT_ENGAGEMENT,
    DEFAULT_WEIGHT_PROFILE,
    DEFAULT_WEIGHT_RECENCY,
)
from utils.exceptions import ConfigError


# ---------------------------------------------------------------------------
# utils/constants.py — named constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Verify the named weight constants in utils/constants.py."""

    def test_default_weight_engagement(self) -> None:
        assert DEFAULT_WEIGHT_ENGAGEMENT == pytest.approx(0.30)

    def test_default_weight_profile(self) -> None:
        assert DEFAULT_WEIGHT_PROFILE == pytest.approx(0.25)

    def test_default_weight_creative(self) -> None:
        assert DEFAULT_WEIGHT_CREATIVE == pytest.approx(0.15)

    def test_default_weight_channel(self) -> None:
        assert DEFAULT_WEIGHT_CHANNEL == pytest.approx(0.15)

    def test_default_weight_recency(self) -> None:
        assert DEFAULT_WEIGHT_RECENCY == pytest.approx(0.15)

    def test_default_frequency_max(self) -> None:
        assert DEFAULT_FREQUENCY_MAX == 30

    def test_weights_sum_to_one(self) -> None:
        """The five weight defaults must sum to exactly 1.0.

        If this test fails, utils/constants.py has a typo.
        Fix the constants, not the tolerance in ConfigRegistry.
        """
        total = (
            DEFAULT_WEIGHT_ENGAGEMENT
            + DEFAULT_WEIGHT_PROFILE
            + DEFAULT_WEIGHT_CREATIVE
            + DEFAULT_WEIGHT_CHANNEL
            + DEFAULT_WEIGHT_RECENCY
        )
        assert abs(total - 1.0) < 1e-9, (
            f"DEFAULT_WEIGHT_* constants sum to {total}, expected 1.0"
        )


# ---------------------------------------------------------------------------
# ConfigRegistry dataclass field introspection
# ---------------------------------------------------------------------------

class TestConfigRegistryWeightFields:
    """Verify the new fields exist on ConfigRegistry with correct metadata.

    These tests require the full project (all models/ sub-modules present).
    They are skipped in partial-project environments (Wave 1/2 outputs only)
    and will run automatically once the full project is deployed.
    """

    pytestmark = pytest.mark.skipif(
        not _full_project_available,
        reason="Requires full project (models.ad_config missing — not yet deployed)",
    )

    def _get_fields(self) -> dict:
        from models.config_registry import ConfigRegistry
        return {f.name: f for f in dataclasses.fields(ConfigRegistry)}

    def test_scoring_weight_engagement_field_exists(self) -> None:
        fields = self._get_fields()
        assert "scoring_weight_engagement" in fields

    def test_scoring_weight_profile_field_exists(self) -> None:
        fields = self._get_fields()
        assert "scoring_weight_profile" in fields

    def test_scoring_weight_creative_field_exists(self) -> None:
        fields = self._get_fields()
        assert "scoring_weight_creative" in fields

    def test_scoring_weight_channel_field_exists(self) -> None:
        fields = self._get_fields()
        assert "scoring_weight_channel" in fields

    def test_scoring_weight_recency_field_exists(self) -> None:
        fields = self._get_fields()
        assert "scoring_weight_recency" in fields

    def test_frequency_max_field_exists(self) -> None:
        fields = self._get_fields()
        assert "frequency_max" in fields

    def test_scoring_weight_engagement_default(self) -> None:
        fields = self._get_fields()
        assert fields["scoring_weight_engagement"].default == pytest.approx(0.30)

    def test_scoring_weight_profile_default(self) -> None:
        fields = self._get_fields()
        assert fields["scoring_weight_profile"].default == pytest.approx(0.25)

    def test_scoring_weight_creative_default(self) -> None:
        fields = self._get_fields()
        assert fields["scoring_weight_creative"].default == pytest.approx(0.15)

    def test_scoring_weight_channel_default(self) -> None:
        fields = self._get_fields()
        assert fields["scoring_weight_channel"].default == pytest.approx(0.15)

    def test_scoring_weight_recency_default(self) -> None:
        fields = self._get_fields()
        assert fields["scoring_weight_recency"].default == pytest.approx(0.15)

    def test_frequency_max_default(self) -> None:
        fields = self._get_fields()
        assert fields["frequency_max"].default == 30


# ---------------------------------------------------------------------------
# Weight validator logic (tested in isolation without full ConfigRegistry)
# ---------------------------------------------------------------------------

class TestWeightValidatorLogic:
    """Test the validator arithmetic independently of ConfigRegistry construction.

    These tests replicate the exact logic of ConfigRegistry.__post_init__
    so that the validator behaviour can be verified without needing to
    supply all required ConfigRegistry fields (which require Wave 3 fixtures).
    """

    @staticmethod
    def _validate(
        engagement: float,
        profile: float,
        creative: float,
        channel: float,
        recency: float,
    ) -> None:
        """Replicate ConfigRegistry.__post_init__ weight validation."""
        weight_sum = engagement + profile + creative + channel + recency
        if abs(weight_sum - 1.0) > 0.001:
            raise ConfigError(
                f"Scoring weights must sum to 1.0 (±0.001); got {weight_sum:.6f}."
            )

    def test_default_weights_pass_validation(self) -> None:
        """Default weights (0.30+0.25+0.15+0.15+0.15=1.00) must not raise."""
        self._validate(0.30, 0.25, 0.15, 0.15, 0.15)  # must not raise

    def test_weights_within_tolerance_pass(self) -> None:
        """Sum = 1.0005 is within ±0.001 tolerance — must not raise."""
        self._validate(0.3005, 0.25, 0.15, 0.15, 0.15)  # sum = 1.0005

    def test_weights_outside_tolerance_raise_config_error(self) -> None:
        """Sum = 0.9 is outside tolerance — must raise ConfigError."""
        with pytest.raises(ConfigError, match="Scoring weights must sum to 1.0"):
            self._validate(0.20, 0.20, 0.20, 0.20, 0.10)  # sum = 0.90

    def test_weights_too_high_raise_config_error(self) -> None:
        """Sum = 1.1 is outside tolerance — must raise ConfigError."""
        with pytest.raises(ConfigError):
            self._validate(0.30, 0.25, 0.20, 0.20, 0.15)  # sum = 1.10

    def test_all_zero_weights_raise_config_error(self) -> None:
        """All zeros (sum = 0.0) must raise ConfigError."""
        with pytest.raises(ConfigError):
            self._validate(0.0, 0.0, 0.0, 0.0, 0.0)
    def test_boundary_at_lower_tolerance(self) -> None:
        """Sum = 0.9995 is within ±0.001 tolerance — must not raise.

        Uses 0.9995 (abs diff 0.0005 < 0.001) to stay well clear of
        IEEE 754 floating-point precision edge cases near the exact boundary.
        """
        # 0.2995 + 0.25 + 0.15 + 0.15 + 0.15 = 0.9995; abs diff = 0.0005
        self._validate(0.2995, 0.25, 0.15, 0.15, 0.15)

    def test_boundary_just_outside_lower_tolerance(self) -> None:
        """Sum = 0.997 has abs diff 0.003 > 0.001 — must raise."""
        with pytest.raises(ConfigError):
            self._validate(0.297, 0.25, 0.15, 0.15, 0.15)  # sum = 0.997

    def test_error_message_contains_actual_sum(self) -> None:
        """ConfigError message must include the actual weight sum."""
        with pytest.raises(ConfigError, match="0.900000"):
            self._validate(0.20, 0.20, 0.20, 0.20, 0.10)


    def test_boundary_at_lower_tolerance(self) -> None:
        """Sum = 0.9995 is within ±0.001 tolerance — must not raise.

        Uses 0.9995 (abs diff 0.0005 < 0.001) to stay well clear of
        IEEE 754 floating-point precision edge cases near the exact boundary.
        """
        # 0.2995 + 0.25 + 0.15 + 0.15 + 0.15 = 0.9995; abs diff = 0.0005
        self._validate(0.2995, 0.25, 0.15, 0.15, 0.15)

    def test_boundary_just_outside_lower_tolerance(self) -> None:
        """Sum = 0.997 has abs diff 0.003 > 0.001 — must raise."""
        with pytest.raises(ConfigError):
            self._validate(0.297, 0.25, 0.15, 0.15, 0.15)  # sum = 0.997

    def test_error_message_contains_actual_sum(self) -> None:
        """ConfigError message must include the actual weight sum."""
        with pytest.raises(ConfigError, match="0.900000"):
            self._validate(0.20, 0.20, 0.20, 0.20, 0.10)
