"""Project-wide custom exception classes for the Engagement Data Generator.

All exceptions raised by production modules must derive from one of the
base classes defined here.  This ensures callers can catch project-specific
errors with a single except clause if needed.

References
----------
* ARCH-006  — self-registering rule classes use ConfigError for invalid configs
* VAL-001   — hard validation errors surface as ValidationError
* CFG-005   — SchemaVersionError on config snapshot version mismatch
* PROJECT_HANDOFF.md §Infrastructure — exceptions.py lists all four exception types
"""


class EngagementDataGeneratorError(Exception):
    """Base exception for all project-specific errors."""


class ConfigError(EngagementDataGeneratorError):
    """Raised when a ConfigRegistry or config-loading operation encounters an
    invalid or inconsistent configuration value.

    Examples
    --------
    * scoring weights do not sum to 1.0 ±0.001
    * simulation_end_date precedes simulation_start_date
    * required field is missing or the wrong type
    """


class ValidationError(EngagementDataGeneratorError):
    """Raised by hard validation rules (HR-001 through HR-015) when a
    blocking invariant is violated in the simulation output."""


class SchemaVersionError(EngagementDataGeneratorError):
    """Raised when a JSON config snapshot's schema_version does not match
    CONFIG_SCHEMA_VERSION (CFG-005).

    Attributes
    ----------
    found:    The schema_version string present in the file.
    expected: The CONFIG_SCHEMA_VERSION this build requires.
    file_name: Source file or label for error context.
    """

    def __init__(self, found: str, expected: str, file_name: str = "") -> None:
        self.found = found
        self.expected = expected
        self.file_name = file_name
        location = f" in {file_name!r}" if file_name else ""
        super().__init__(
            f"Config schema version mismatch{location}: "
            f"found {found!r}, expected {expected!r}. "
            "Re-save the config with the current application version."
        )


class InputValidationError(EngagementDataGeneratorError):
    """Raised when an input file (trigger file, historical file, config JSON)
    fails structural validation — missing columns, null primary keys, malformed
    JSON, or missing required keys.

    Attributes
    ----------
    file_name: The file being validated (for error context).
    detail:    Human-readable description of the specific problem.
    """

    def __init__(self, file_name: str, detail: str) -> None:
        self.file_name = file_name
        self.detail = detail
        super().__init__(f"Input validation failed for {file_name!r}: {detail}")


class SimulationError(EngagementDataGeneratorError):
    """Raised by the simulation pipeline when an unrecoverable runtime error
    occurs (e.g. missing stage output, stage contract violation)."""


__all__ = [
    "EngagementDataGeneratorError",
    "ConfigError",
    "ValidationError",
    "SchemaVersionError",
    "InputValidationError",
    "SimulationError",
]
