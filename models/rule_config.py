"""Immutable configuration for a single validation rule."""
from __future__ import annotations
from dataclasses import dataclass
from models.enums import RuleSeverity


@dataclass(frozen=True)
class RuleConfig:
    """Immutable configuration for a single validation rule.

    Attributes:
        rule_id: Unique rule identifier (e.g., "HR-001").
        rule_name: Human-readable rule name.
        severity: Rule severity — "Hard", "Soft", or "Advisory".
        enabled: Whether this rule is active during validation.
        severity_override: Optional override to demote severity.
    """
    rule_id: str
    rule_name: str
    severity: str  # Use RuleSeverity enum values
    enabled: bool
    severity_override: str | None = None

    def effective_severity(self) -> str:
        if self.severity_override is not None:
            return self.severity_override
        return self.severity

    def is_hard(self) -> bool:
        return self.effective_severity() == RuleSeverity.HARD.value

    def is_soft(self) -> bool:
        return self.effective_severity() == RuleSeverity.SOFT.value

    def is_advisory(self) -> bool:
        return self.effective_severity() == RuleSeverity.ADVISORY.value


__all__ = ["RuleConfig"]
