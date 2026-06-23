"""Excel and DataFrame column utilities for the Engagement Data Generator.

Provides reconcile_creative_affinity_columns(), which is the single approved
function for expanding and synchronising Creative_Affinity_{ad_name} columns
in the pipeline state DataFrame (ARCH-012 / FR-USM-007).

References
----------
* ARCH-012  — dynamic creative affinity columns stored as dict in dataclass,
              expanded to Creative_Affinity_{ad_name} columns in DataFrame
* FR-USM-007 — reconcile_creative_affinity_columns() lives here, NOT in
               utils/schema_validator.py
* PROJECT_DECISIONS.md — DEFAULT_CREATIVE_AFFINITY = 0.5 from utils/constants.py
"""
from __future__ import annotations

import pandas as pd

from models.config_registry import ConfigRegistry
from utils.constants import DEFAULT_CREATIVE_AFFINITY
from utils.logger import get_logger

logger = get_logger(__name__)

_CA_PREFIX = "Creative_Affinity_"


def reconcile_creative_affinity_columns(
    state_df: pd.DataFrame,
    config: ConfigRegistry,
) -> pd.DataFrame:
    """Expand and synchronise Creative_Affinity_{ad_name} columns in state_df.

    Called by UserStateManager.initialize_user_states() after building the
    state DataFrame from a mix of new UserState records (which carry a
    `creative_affinities` dict column) and returning rows (which already
    carry individual Creative_Affinity_* columns).

    Steps (in order):
    1. If a `creative_affinities` dict column is present, expand each dict
       entry to a ``Creative_Affinity_{ad_name}`` column, then drop the dict
       column.
    2. For each ad in config.get_ad_names(), ensure a
       ``Creative_Affinity_{ad_name}`` column exists; add it with value
       DEFAULT_CREATIVE_AFFINITY if absent, and fill any NaN values.
    3. Drop any ``Creative_Affinity_*`` columns whose ad name is no longer in
       config.ads (handles config ad removal across runs).
    4. Cast all ``Creative_Affinity_*`` columns to ``float32``.

    Args:
        state_df: Pipeline state DataFrame, potentially containing a
            ``creative_affinities`` dict column or pre-existing
            ``Creative_Affinity_*`` columns, or both after a concat.
        config: ConfigRegistry for the current run. Used to obtain the
            authoritative ad list via ``config.get_ad_names()``.

    Returns:
        A new DataFrame with ``creative_affinities`` removed (if present)
        and exactly one ``Creative_Affinity_{ad_name}`` float32 column per
        ad in config.ads.

    Notes:
        This function always returns a copy — the input is never mutated.
        ARCH-012: no inline 0.5 literals; DEFAULT_CREATIVE_AFFINITY imported
        from utils/constants.py.
    """
    df = state_df.copy()

    ad_names = config.get_ad_names()
    expected_cols = [f"{_CA_PREFIX}{ad}" for ad in ad_names]

    # ── Step 1: Expand creative_affinities dict column if present ──────────
    if "creative_affinities" in df.columns:
        if len(df) > 0:
            raw = df["creative_affinities"].tolist()
            # Each element is a dict {ad_name: float}; normalise to a DataFrame
            expanded = pd.json_normalize(raw)
            if not expanded.empty:
                # Rename bare ad_name keys to Creative_Affinity_{ad_name}
                rename_map = {
                    k: f"{_CA_PREFIX}{k}"
                    for k in expanded.columns
                    if not k.startswith(_CA_PREFIX)
                }
                expanded = expanded.rename(columns=rename_map)
                expanded.index = df.index
                for col in expanded.columns:
                    df[col] = expanded[col]
        df = df.drop(columns=["creative_affinities"])

    # ── Step 2: Add missing columns; fill NaN in existing ones ─────────────
    for col in expected_cols:
        if col not in df.columns:
            df[col] = DEFAULT_CREATIVE_AFFINITY
        else:
            df[col] = df[col].fillna(DEFAULT_CREATIVE_AFFINITY)

    # ── Step 3: Drop columns for ads no longer in config ───────────────────
    expected_set = set(expected_cols)
    stale = [c for c in df.columns if c.startswith(_CA_PREFIX) and c not in expected_set]
    if stale:
        logger.debug(
            "reconcile_creative_affinity_columns: dropping stale columns %s", stale
        )
        df = df.drop(columns=stale)

    # ── Step 4: Cast all Creative_Affinity_* columns to float32 ───────────
    for col in expected_cols:
        if col in df.columns:
            df[col] = df[col].astype("float32")

    return df


__all__ = ["reconcile_creative_affinity_columns"]
