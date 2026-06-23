"""Tests for models/enums.py — ARCH-015 compliance."""
import pytest
from models.enums import EligibilityStatus


def test_eligibility_status_has_canonical_values():
    """All 6 canonical EligibilityStatus values must exist (ARCH-015)."""
    assert EligibilityStatus.NEW.value      == "New"
    assert EligibilityStatus.ACTIVE.value   == "Active"
    assert EligibilityStatus.COOLING.value  == "Cooling"
    assert EligibilityStatus.RE_ENTRY.value == "Re_Entry"
    assert EligibilityStatus.SKIPPED.value  == "Skipped"
    assert EligibilityStatus.EXCLUDED.value == "Excluded"


def test_eligibility_status_reentry_uses_underscore():
    """RE_ENTRY string value must be 'Re_Entry' (underscore, not hyphen — ARCH-015)."""
    assert EligibilityStatus.RE_ENTRY.value == "Re_Entry"
    assert EligibilityStatus("Re_Entry") == EligibilityStatus.RE_ENTRY


def test_eligibility_status_deprecated_values_still_importable():
    """Deprecated values ELIGIBLE/INELIGIBLE/COMPLETED must remain importable (backward compat)."""
    assert EligibilityStatus.ELIGIBLE.value   == "Eligible"
    assert EligibilityStatus.INELIGIBLE.value == "Ineligible"
    assert EligibilityStatus.COMPLETED.value  == "Completed"
