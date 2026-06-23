"""Project version constants.

References
----------
* PROJECT_HANDOFF.md §Infrastructure — "utils/version.py fully implemented"
* CFG-005 — CONFIG_SCHEMA_VERSION = "2.0" written to every JSON snapshot
"""

APP_VERSION: str = "1.0.0"
"""Application version string."""

CONFIG_SCHEMA_VERSION: str = "2.0"
"""Config snapshot schema version. Mismatch raises SchemaVersionError.

Written into every config snapshot by config_io.save_config_snapshot().
Validated by config_io.load_config_snapshot() and core/config_loader.py.
Bump when the ConfigRegistry schema changes in an incompatible way.
"""

__all__ = ["APP_VERSION", "CONFIG_SCHEMA_VERSION"]
