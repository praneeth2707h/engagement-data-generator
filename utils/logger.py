"""Centralised logging setup for the Engagement Data Generator.

References
----------
* PROJECT_HANDOFF.md §Infrastructure — "utils/logger.py: get_logger() with StreamHandler + FileHandler"
"""
from __future__ import annotations
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger with a StreamHandler attached.

    Calling get_logger() multiple times with the same name returns the same
    Logger instance (Python's logging module guarantees this). Handlers are
    only added on the first call to avoid duplicate log lines.

    Args:
        name: Logger name — use __name__ in every caller.

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


__all__ = ["get_logger"]
