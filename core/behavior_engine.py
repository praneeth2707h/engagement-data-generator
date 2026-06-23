"""Stage 6 — Behavior Processing.

BehaviorEngine simulates realistic user engagement behavior for one simulation
day. It computes composite engagement scores (SIM-001), generates engagement
events (Impression, Sent, Open, Click) per channel, enforces fatigue and
weekly-cap rules, and updates user-state fields owned by this stage.

Architecture references
-----------------------
* ARCH-003  — Stage 6 in the 11-stage pipeline
* ARCH-011  — No iterrows(); vectorised operations only
* ARCH-012  — float32 for engagement_score and affinity fields
* BIZ-023/C-003 — weekly counter reset on ISO Monday boundary
* SIM-001   — composite engagement score formula (five weighted components + jitter)
* SIM-019   — per-user deterministic RNG via hashlib MD5
* ENG-001..ENG-015 — engagement scoring and event-generation rules
* FAT-001..FAT-007 — fatigue and frequency rules
* CHA-001..CHA-008 — channel affinity rules
* CA-001..CA-008   — creative affinity rules

Days-in-ad semantics note:
    BehaviorEngine does NOT advance users between ads; that is JourneyEngine's
    responsibility.  BehaviorEngine writes ``ad_click_received = True`` for
    users who produce a Click, which JourneyEngine reads on the next advance().

    -- No iterrows(); all classification and event-generation logic
    -- uses vectorised boolean-mask operations.
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta

import numpy as np
import pandas as pd

from models.config_registry import ConfigRegistry
from models.enums import ActionType, BehaviorProfile, JourneyStatus
from utils.exceptions import InputValidationError
from utils.logger import get_logger

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Profile component lookup (ENG-004 / ENG-005)
# ---------------------------------------------------------------------------
_PROFILE_MULTIPLIERS: dict[str, float] = {
    BehaviorProfile.HIGHLY_ENGAGED.value: 2.0,
    BehaviorProfile.MODERATE.value: 1.0,
    BehaviorProfile.PASSIVE.value: 0.4,
    BehaviorProfile.DORMANT.value: 0.1,
}
_MAX_PROFILE_MUL: float = 2.0  # max(HIGHLY_ENGAGED)
_PROFILE_COMPONENT: dict[str, float] = {
    k: v / _MAX_PROFILE_MUL for k, v in _PROFILE_MULTIPLIERS.items()
}

# Display-family channel names
_DISPLAY_CHANNELS: frozenset[str] = frozenset(
    {"Display", "Endemic_Display", "Programmatic_Display", "Banner"}
)

# "Sent" action name for Email/WhatsApp reach events (not in ActionType enum)
_ACTION_SENT = "Sent"

# Qualifying actions per channel (BIZ-011 / ENG-014)
_QUALIFYING: dict[str, frozenset[str]] = {
    "display": frozenset({ActionType.CLICK.value}),
    "email":   frozenset({ActionType.OPEN.value, ActionType.CLICK.value}),
    "whatsapp": frozenset({ActionType.OPEN.value, ActionType.CLICK.value}),
}

# Required columns for BehaviorEngine.process()
_STATE_REQUIRED_COLS: tuple[str, ...] = (
    "user_id", "journey_status", "current_ad", "channel", "vendor",
    "behavior_profile", "engagement_score",
    "channel_affinity_display", "channel_affinity_email",
    "channel_affinity_whatsapp",
    "weekly_impressions", "weekly_clicks", "weekly_opens", "weekly_engagements",
    "total_lifetime_engagements", "last_reached_date", "last_engagement_date",
    "engagement_cooldown_end", "ad_click_received",
)

# Events DataFrame column order
_EVENT_COLS = ("user_id", "simulation_date", "channel", "action_type", "current_ad", "vendor")

# Default open rates for channels without explicit ChannelConfig
_DEFAULT_OPEN_RATE: float = 0.25
_DEFAULT_CTR: float = 0.05


class BehaviorEngine:
    """Stage 6 — Behavior Processing.

    Simulates per-user engagement behavior for one simulation day.

    Args:
        config: ConfigRegistry for the current campaign run.

    Ownership — columns written by this engine:
        weekly_impressions, weekly_clicks, weekly_opens, weekly_engagements,
        total_lifetime_engagements, last_reached_date, last_engagement_date,
        engagement_cooldown_end, ad_click_received, engagement_score,
        channel_affinity_display, channel_affinity_email,
        channel_affinity_whatsapp, Creative_Affinity_{ad_name}.
    """

    def __init__(self, config: ConfigRegistry) -> None:
        self._config = config
        self._ad_names: list[str] = config.get_ad_names()
        self._ad_target_ctr: dict[str, float] = {
            ad.ad_name: (ad.target_ctr if ad.target_ctr is not None else _DEFAULT_CTR)
            for ad in config.ads
        }
        self._channel_cfgs = {ch.channel_name: ch for ch in config.channels}

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def process(
        self,
        state_df: pd.DataFrame,
        simulation_date: date,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Process all eligible users for one simulation day.

        Args:
            state_df: Current user state DataFrame. NOT mutated.
            simulation_date: Current simulation date.

        Returns:
            (updated_state_df, events_df) where events_df columns are:
            user_id, simulation_date, channel, action_type, current_ad, vendor.

        Raises:
            InputValidationError: If required columns are missing from state_df.
        """
        self._validate_columns(state_df)
        df = state_df.copy()

        # FAT-001 / FAT-002: Reset weekly counters on ISO Monday FIRST
        df = self._reset_weekly_counters_if_monday(df, simulation_date)

        mask_reach = self._get_reach_eligible_mask(df)
        if not mask_reach.any():
            return df, _empty_events_df()

        mask_qualify = mask_reach & self._get_qualify_eligible_mask(df, simulation_date)

        scores = self._compute_composite_scores(df, simulation_date)
        draws  = self._draw_random_values(df, simulation_date)

        parts: list[pd.DataFrame] = []

        mask_display = mask_reach & df["channel"].isin(_DISPLAY_CHANNELS)
        if mask_display.any():
            parts.append(self._process_display(
                df, scores, draws,
                mask_display, mask_qualify & mask_display,
                simulation_date,
            ))

        mask_email = mask_reach & (df["channel"] == "Email")
        if mask_email.any():
            parts.append(self._process_email(
                df, scores, draws,
                mask_email, mask_qualify & mask_email,
                simulation_date,
            ))

        mask_wa = mask_reach & (df["channel"] == "WhatsApp")
        if mask_wa.any():
            parts.append(self._process_whatsapp(
                df, scores, draws,
                mask_wa, mask_qualify & mask_wa,
                simulation_date,
            ))

        _non_empty = [p for p in parts if not p.empty]
        events_df = (
            pd.concat(_non_empty, ignore_index=True)
            if _non_empty else _empty_events_df()
        )

        df = self._update_state_from_events(df, events_df, simulation_date)
        df = self._update_affinities(df, events_df)
        return df, events_df

    def compute_composite_scores(
        self,
        state_df: pd.DataFrame,
        simulation_date: date,
    ) -> pd.Series:
        """Public wrapper: SIM-001 composite scores for all rows."""
        return self._compute_composite_scores(state_df, simulation_date)

    def reset_weekly_counters(
        self,
        state_df: pd.DataFrame,
        simulation_date: date,
    ) -> pd.DataFrame:
        """Public wrapper: reset weekly counters if simulation_date is Monday."""
        return self._reset_weekly_counters_if_monday(state_df.copy(), simulation_date)

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def _validate_columns(self, state_df: pd.DataFrame) -> None:
        missing = [c for c in _STATE_REQUIRED_COLS if c not in state_df.columns]
        if missing:
            raise InputValidationError(
                "state_df",
                f"BehaviorEngine.process(): missing required column(s): {missing}",
            )

    # -----------------------------------------------------------------------
    # Weekly reset (FAT-001 / C-003)
    # -----------------------------------------------------------------------

    def _reset_weekly_counters_if_monday(
        self, df: pd.DataFrame, simulation_date: date
    ) -> pd.DataFrame:
        if simulation_date.weekday() == 0:  # ISO Monday
            for col in ("weekly_impressions", "weekly_clicks", "weekly_opens", "weekly_engagements"):
                if col in df.columns:
                    df[col] = 0
            _logger.debug("BehaviorEngine: weekly counters reset [%s]", simulation_date)
        return df

    # -----------------------------------------------------------------------
    # Eligibility
    # -----------------------------------------------------------------------

    def _get_reach_eligible_mask(self, df: pd.DataFrame) -> pd.Series:
        """Users eligible for reach events: journey_status==Active AND current_ad set."""
        return (
            (df["journey_status"] == JourneyStatus.ACTIVE.value)
            & df["current_ad"].notna()
        )

    def _get_qualify_eligible_mask(
        self, df: pd.DataFrame, simulation_date: date
    ) -> pd.Series:
        """Additional filter for qualifying events: not in cooldown AND under weekly cap."""
        sim_ts = pd.Timestamp(simulation_date)
        cooldown_ts = pd.to_datetime(
            df.get("engagement_cooldown_end", pd.Series([None] * len(df), index=df.index)),
            errors="coerce",
        )
        mask_no_cooldown = cooldown_ts.isna() | (cooldown_ts < sim_ts)
        mask_under_cap   = df["weekly_engagements"] < self._config.weekly_engagement_cap
        return mask_no_cooldown & mask_under_cap

    # -----------------------------------------------------------------------
    # Composite score (SIM-001)
    # -----------------------------------------------------------------------

    def _compute_composite_scores(
        self, df: pd.DataFrame, simulation_date: date
    ) -> pd.Series:
        cfg = self._config
        eng  = df["engagement_score"].fillna(0.5).astype(float)
        prof = df["behavior_profile"].astype(str).map(_PROFILE_COMPONENT).fillna(0.5).astype(float)
        cre  = self._get_current_creative_affinity(df)
        cha  = self._get_current_channel_affinity(df)
        rec  = self._compute_reach_recency(df, simulation_date)

        weighted = (
            cfg.scoring_weight_engagement * eng
            + cfg.scoring_weight_profile * prof
            + cfg.scoring_weight_creative * cre
            + cfg.scoring_weight_channel * cha
            + cfg.scoring_weight_recency * rec
        )
        jitter = self._compute_jitter(df, simulation_date)
        return pd.Series(
            np.clip(weighted.values + jitter.values, 0.0, 1.0),
            index=df.index,
            dtype=float,
        )

    def _get_current_creative_affinity(self, df: pd.DataFrame) -> pd.Series:
        """Creative affinity for each user's current_ad (vectorised over ads)."""
        result = pd.Series(0.5, index=df.index, dtype=float)
        for ad_name in self._ad_names:
            col = f"Creative_Affinity_{ad_name}"
            if col in df.columns:
                mask = df["current_ad"] == ad_name
                if mask.any():
                    result = result.where(~mask, df[col].astype(float))
        return result.fillna(0.5)

    def _get_current_channel_affinity(self, df: pd.DataFrame) -> pd.Series:
        """Channel affinity for each user's current channel."""
        ch = df.get("channel", pd.Series("", index=df.index)).fillna("")
        result = pd.Series(0.5, index=df.index, dtype=float)
        result = result.where(~ch.isin(_DISPLAY_CHANNELS),
                              df["channel_affinity_display"].astype(float))
        result = result.where(ch != "Email",
                              df["channel_affinity_email"].astype(float))
        result = result.where(ch != "WhatsApp",
                              df["channel_affinity_whatsapp"].astype(float))
        return result.fillna(0.5)

    def _compute_reach_recency(
        self, df: pd.DataFrame, simulation_date: date
    ) -> pd.Series:
        freq_max = float(self._config.frequency_max)
        sim_ts   = pd.Timestamp(simulation_date)
        last_r   = pd.to_datetime(
            df.get("last_reached_date", pd.Series([None] * len(df), index=df.index)),
            errors="coerce",
        )
        never    = last_r.isna()
        days     = (sim_ts - last_r).dt.days.fillna(0).astype(float)
        vals     = np.where(never, 1.0, np.clip(1.0 - days / freq_max, 0.0, 1.0))
        return pd.Series(vals, index=df.index, dtype=float)

    def _compute_jitter(
        self, df: pd.DataFrame, simulation_date: date
    ) -> pd.Series:
        """Deterministic per-user jitter in [0, 0.05] (SIM-019)."""
        ord_ = simulation_date.toordinal()
        seeds = (
            df["user_id"]
            .apply(lambda uid: int(hashlib.md5(uid.encode()).hexdigest(), 16))
            .add(ord_)
            .mod(2**32)
        )
        jitter = np.array([
            np.random.default_rng(int(s)).uniform(0.0, 0.05)
            for s in seeds
        ])
        return pd.Series(jitter, index=df.index, dtype=float)

    # -----------------------------------------------------------------------
    # Per-user deterministic random draws (SIM-019)
    # -----------------------------------------------------------------------

    def _draw_random_values(
        self, df: pd.DataFrame, simulation_date: date
    ) -> dict[str, pd.Series]:
        """Three independent random draws per user (impression, open, click)."""
        ord_  = simulation_date.toordinal()
        uids  = df["user_id"].tolist()

        def _draws(offset: int) -> pd.Series:
            seeds = [
                (int(hashlib.md5(u.encode()).hexdigest(), 16) + ord_ + offset) % (2**32)
                for u in uids
            ]
            arr = np.array([np.random.default_rng(s).random() for s in seeds])
            return pd.Series(arr, index=df.index, dtype=float)

        return {
            "impression": _draws(100),
            "open":       _draws(200),
            "click":      _draws(300),
        }

    # -----------------------------------------------------------------------
    # Event generation
    # -----------------------------------------------------------------------

    def _process_display(
        self,
        df: pd.DataFrame,
        scores: pd.Series,
        draws: dict[str, pd.Series],
        mask_reach: pd.Series,
        mask_qualify: pd.Series,
        sim_date: date,
    ) -> pd.DataFrame:
        """Display: Impression for all reach-eligible; Click on same day (HR-003/HR-004)."""
        imp_cap  = self._config.weekly_impression_cap
        mask_imp = mask_reach & (df["weekly_impressions"] < imp_cap)

        imp_df = _build_events(df, mask_imp, sim_date, ActionType.IMPRESSION.value)

        # Click only if impression generated AND qualify-eligible
        mask_click_cand = mask_imp & mask_qualify
        ctrs = df["current_ad"].map(self._ad_target_ctr).fillna(_DEFAULT_CTR)
        p_click = pd.Series(
            np.clip(2.0 * scores.values * ctrs.values, 0.0, 1.0), index=df.index
        )
        mask_clicked = mask_click_cand & (draws["click"] < p_click)
        click_df = _build_events(df, mask_clicked, sim_date, ActionType.CLICK.value)

        return pd.concat([imp_df, click_df], ignore_index=True)

    def _process_email(
        self,
        df: pd.DataFrame,
        scores: pd.Series,
        draws: dict[str, pd.Series],
        mask_reach: pd.Series,
        mask_qualify: pd.Series,
        sim_date: date,
    ) -> pd.DataFrame:
        """Email: Sent for all reach-eligible; Open/Click if qualify-eligible."""
        imp_cap  = self._config.weekly_impression_cap
        mask_sent = mask_reach & (df["weekly_impressions"] < imp_cap)
        sent_df   = _build_events(df, mask_sent, sim_date, _ACTION_SENT)

        open_rate = self._get_open_rate("Email")
        ctrs      = df["current_ad"].map(self._ad_target_ctr).fillna(_DEFAULT_CTR)
        p_open    = pd.Series(
            np.clip(2.0 * scores.values * open_rate, 0.0, 1.0), index=df.index
        )
        mask_opened = mask_sent & mask_qualify & (draws["open"] < p_open)
        open_df     = _build_events(df, mask_opened, sim_date, ActionType.OPEN.value)

        # Click requires an open this same day (phase 5 same-day model)
        p_click   = pd.Series(
            np.clip(2.0 * scores.values * ctrs.values, 0.0, 1.0), index=df.index
        )
        mask_clicked = mask_opened & (draws["click"] < p_click)
        click_df     = _build_events(df, mask_clicked, sim_date, ActionType.CLICK.value)

        return pd.concat([sent_df, open_df, click_df], ignore_index=True)

    def _process_whatsapp(
        self,
        df: pd.DataFrame,
        scores: pd.Series,
        draws: dict[str, pd.Series],
        mask_reach: pd.Series,
        mask_qualify: pd.Series,
        sim_date: date,
    ) -> pd.DataFrame:
        """WhatsApp: same causal chain as Email (Sent → Open → Click)."""
        imp_cap    = self._config.weekly_impression_cap
        mask_sent  = mask_reach & (df["weekly_impressions"] < imp_cap)
        sent_df    = _build_events(df, mask_sent, sim_date, _ACTION_SENT)

        open_rate  = self._get_open_rate("WhatsApp")
        ctrs       = df["current_ad"].map(self._ad_target_ctr).fillna(_DEFAULT_CTR)
        p_open     = pd.Series(
            np.clip(2.0 * scores.values * open_rate, 0.0, 1.0), index=df.index
        )
        mask_opened = mask_sent & mask_qualify & (draws["open"] < p_open)
        open_df     = _build_events(df, mask_opened, sim_date, ActionType.OPEN.value)

        p_click      = pd.Series(
            np.clip(2.0 * scores.values * ctrs.values, 0.0, 1.0), index=df.index
        )
        mask_clicked = mask_opened & (draws["click"] < p_click)
        click_df     = _build_events(df, mask_clicked, sim_date, ActionType.CLICK.value)

        return pd.concat([sent_df, open_df, click_df], ignore_index=True)

    # -----------------------------------------------------------------------
    # State update from events
    # -----------------------------------------------------------------------

    def _update_state_from_events(
        self,
        df: pd.DataFrame,
        events_df: pd.DataFrame,
        simulation_date: date,
    ) -> pd.DataFrame:
        if events_df.empty:
            return df

        # ── Reach events (Impression / Sent) ─────────────────────────────
        reach_mask_ev = events_df["action_type"].isin(
            {ActionType.IMPRESSION.value, _ACTION_SENT}
        )
        reach_users = set(events_df.loc[reach_mask_ev, "user_id"])
        if reach_users:
            m = df["user_id"].isin(reach_users)
            df.loc[m, "weekly_impressions"] = df.loc[m, "weekly_impressions"] + 1
            df.loc[m, "last_reached_date"]  = simulation_date

        # ── Open events ───────────────────────────────────────────────────
        open_users = set(events_df.loc[
            events_df["action_type"] == ActionType.OPEN.value, "user_id"
        ])
        if open_users:
            m = df["user_id"].isin(open_users)
            df.loc[m, "weekly_opens"] = df.loc[m, "weekly_opens"] + 1

        # ── Click events ──────────────────────────────────────────────────
        click_users = set(events_df.loc[
            events_df["action_type"] == ActionType.CLICK.value, "user_id"
        ])
        if click_users:
            m = df["user_id"].isin(click_users)
            df.loc[m, "weekly_clicks"]     = df.loc[m, "weekly_clicks"] + 1
            df.loc[m, "ad_click_received"] = True

        # ── Qualifying events (BIZ-011) ────────────────────────────────────
        qual_mask_ev = _qualifying_mask(events_df)
        qual_users   = set(events_df.loc[qual_mask_ev, "user_id"])
        if qual_users:
            m   = df["user_id"].isin(qual_users)
            end = simulation_date + timedelta(days=self._config.engagement_cooldown_days)
            df.loc[m, "weekly_engagements"]       = df.loc[m, "weekly_engagements"] + 1
            df.loc[m, "total_lifetime_engagements"] = (
                df.loc[m, "total_lifetime_engagements"] + 1
            )
            df.loc[m, "last_engagement_date"]   = simulation_date
            df.loc[m, "engagement_cooldown_end"] = end

        # ── Engagement score nudge ────────────────────────────────────────
        floor_  = self._config.engagement_score_floor
        ceil_   = self._config.engagement_score_ceiling
        if qual_users:
            m = df["user_id"].isin(qual_users)
            df.loc[m, "engagement_score"] = np.clip(
                df.loc[m, "engagement_score"].astype(float) + 0.02, floor_, ceil_
            ).astype("float32")
        reach_only = reach_users - qual_users
        if reach_only:
            m = df["user_id"].isin(reach_only)
            df.loc[m, "engagement_score"] = np.clip(
                df.loc[m, "engagement_score"].astype(float) - 0.01, floor_, ceil_
            ).astype("float32")

        return df

    # -----------------------------------------------------------------------
    # Affinity updates (CHA-005/006, CA-006/007)
    # -----------------------------------------------------------------------

    def _update_affinities(
        self, df: pd.DataFrame, events_df: pd.DataFrame
    ) -> pd.DataFrame:
        if events_df.empty:
            return df

        cfg    = self._config
        boost  = cfg.affinity_boost_on_click
        decay  = cfg.affinity_decay_no_engage
        floor_ = cfg.affinity_floor
        ceil_  = cfg.affinity_ceiling

        qual_mask_ev = _qualifying_mask(events_df)

        # Channel affinity
        channel_map = {
            "channel_affinity_display":   _DISPLAY_CHANNELS,
            "channel_affinity_email":     {"Email"},
            "channel_affinity_whatsapp":  {"WhatsApp"},
        }
        for col, ch_set in channel_map.items():
            reach_ev = events_df["channel"].isin(ch_set) & events_df["action_type"].isin(
                {ActionType.IMPRESSION.value, _ACTION_SENT}
            )
            qual_ev  = qual_mask_ev & events_df["channel"].isin(ch_set)

            ch_qual  = set(events_df.loc[qual_ev,  "user_id"])
            ch_reach = set(events_df.loc[reach_ev, "user_id"])
            ch_decay = ch_reach - ch_qual

            if ch_qual:
                m = df["user_id"].isin(ch_qual)
                df.loc[m, col] = np.clip(
                    df.loc[m, col].astype(float) + boost, floor_, ceil_
                ).astype("float32")
            if ch_decay:
                m = df["user_id"].isin(ch_decay)
                df.loc[m, col] = np.clip(
                    df.loc[m, col].astype(float) - decay, floor_, ceil_
                ).astype("float32")

        # Creative affinity (per ad)
        for ad_name in self._ad_names:
            col = f"Creative_Affinity_{ad_name}"
            if col not in df.columns:
                continue
            reach_ev = events_df["action_type"].isin(
                {ActionType.IMPRESSION.value, _ACTION_SENT}
            ) & (events_df["current_ad"] == ad_name)
            qual_ev  = qual_mask_ev & (events_df["current_ad"] == ad_name)

            ad_qual  = set(events_df.loc[qual_ev,  "user_id"])
            ad_reach = set(events_df.loc[reach_ev, "user_id"])
            ad_decay = ad_reach - ad_qual

            if ad_qual:
                m = df["user_id"].isin(ad_qual)
                df.loc[m, col] = np.clip(
                    df.loc[m, col].astype(float) + boost, floor_, ceil_
                ).astype("float32")
            if ad_decay:
                m = df["user_id"].isin(ad_decay)
                df.loc[m, col] = np.clip(
                    df.loc[m, col].astype(float) - decay, floor_, ceil_
                ).astype("float32")

        return df

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _get_open_rate(self, channel: str) -> float:
        """Return target open rate for channel from ChannelConfig or default."""
        ch_cfg = self._channel_cfgs.get(channel)
        if ch_cfg is not None and ch_cfg.target_open_rate is not None:
            return ch_cfg.target_open_rate
        return _DEFAULT_OPEN_RATE


# ---------------------------------------------------------------------------
# Module-level helpers (no self required)
# ---------------------------------------------------------------------------

def _empty_events_df() -> pd.DataFrame:
    return pd.DataFrame(columns=list(_EVENT_COLS))


def _build_events(
    df: pd.DataFrame,
    mask: pd.Series,
    sim_date: date,
    action_type: str,
) -> pd.DataFrame:
    """Build a slice of the events DataFrame from a boolean mask."""
    if not mask.any():
        return _empty_events_df()
    subset = df.loc[mask, ["user_id", "channel", "current_ad", "vendor"]].copy()
    subset["simulation_date"] = sim_date
    subset["action_type"]     = action_type
    subset["vendor"]          = subset["vendor"].fillna("")
    return subset[list(_EVENT_COLS)].reset_index(drop=True)


def _qualifying_mask(events_df: pd.DataFrame) -> pd.Series:
    """Boolean mask for qualifying events per BIZ-011 / ENG-014."""
    disp_click  = events_df["channel"].isin(_DISPLAY_CHANNELS) & (
        events_df["action_type"] == ActionType.CLICK.value
    )
    email_qual  = (events_df["channel"] == "Email") & events_df["action_type"].isin(
        {ActionType.OPEN.value, ActionType.CLICK.value}
    )
    wa_qual     = (events_df["channel"] == "WhatsApp") & events_df["action_type"].isin(
        {ActionType.OPEN.value, ActionType.CLICK.value}
    )
    return disp_click | email_qual | wa_qual


__all__ = ["BehaviorEngine"]
