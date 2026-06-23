"""Page 3 — Business Rules.

Exposes all business-user-configurable simulation parameters:
  * CTR targets per ad (overridable from campaign defaults)
  * Open Rate targets per channel
  * TER targets per trigger (overridable from campaign defaults)
  * Segment Mix targets (distribution %)
  * Journey lengths (ad duration days)
  * Weekly Impression Cap
  * Weekly Engagement Cap
  * Weekly Click Cap / Open Cap
  * Cooling period

Changes are merged into the config dict already in session_state.
No code changes required to adjust business rules.
"""
from __future__ import annotations
import logging

import streamlit as st

from ui.state import get_config_dict, set_config_dict

logger = logging.getLogger(__name__)


def render() -> None:
    """Render the Business Rules page."""
    st.header("📐 Business Rules")

    cfg = get_config_dict()
    if cfg is None:
        st.warning("Complete **Campaign Setup** first before adjusting business rules.")
        return

    st.markdown(
        "Adjust the parameters below to control how the simulation behaves. "
        "No code changes are required."
    )

    # ── CTR Targets ───────────────────────────────────────────────────────
    st.subheader("CTR Targets")
    st.caption("Click-through rate target per ad. Used by ValidationEngine to assess CTR achievement.")

    ads = cfg.get("ads", [])
    for i, ad in enumerate(ads):
        ad["target_ctr"] = st.slider(
            f"{ad.get('ad_name','Ad')} — CTR Target",
            min_value=0.001, max_value=0.50,
            value=float(ad.get("target_ctr", 0.10)),
            step=0.005, format="%.3f",
            key=f"br_ctr_{i}",
            help=f"Channel: {ad.get('channel','?')}"
        )
    cfg["ads"] = ads

    st.divider()

    # ── Open Rate Targets ─────────────────────────────────────────────────
    st.subheader("Open Rate Targets")
    st.caption("For Email and WhatsApp channels. Not applicable to Display.")

    channels = cfg.get("channels", [])
    email_ch = [c for c in channels if c.get("channel_name") in ("Email", "WhatsApp")]

    # If no channels configured yet, offer a quick add
    if not email_ch:
        st.info(
            "No Email/WhatsApp channels configured. "
            "If your ads use Email or WhatsApp, add channel configs below."
        )
        if st.checkbox("Add Email channel config", key="br_add_email"):
            channels.append({
                "channel_name": "Email",
                "target_ctr": 0.05,
                "target_open_rate": 0.25,
            })
            cfg["channels"] = channels
            set_config_dict(cfg)
            st.rerun()
        if st.checkbox("Add WhatsApp channel config", key="br_add_wa"):
            channels.append({
                "channel_name": "WhatsApp",
                "target_ctr": 0.10,
                "target_open_rate": 0.40,
            })
            cfg["channels"] = channels
            set_config_dict(cfg)
            st.rerun()
    else:
        for ch in channels:
            if ch.get("channel_name") in ("Email", "WhatsApp"):
                col1, col2 = st.columns(2)
                ch["target_ctr"] = col1.number_input(
                    f"{ch['channel_name']} — CTR Target",
                    min_value=0.001, max_value=0.50,
                    value=float(ch.get("target_ctr", 0.05)),
                    step=0.005, format="%.3f",
                    key=f"br_ch_ctr_{ch['channel_name']}"
                )
                ch["target_open_rate"] = col2.number_input(
                    f"{ch['channel_name']} — Open Rate Target",
                    min_value=0.001, max_value=1.0,
                    value=float(ch.get("target_open_rate", 0.25)),
                    step=0.01, format="%.3f",
                    key=f"br_ch_or_{ch['channel_name']}"
                )
        cfg["channels"] = channels

    st.divider()

    # ── TER Targets ───────────────────────────────────────────────────────
    st.subheader("Trigger Engagement Rate (TER) Targets")
    st.caption("Fraction of triggered users expected to take a qualifying action.")

    triggers = cfg.get("triggers", [])
    for i, t in enumerate(triggers):
        t["engagement_rate_target"] = st.slider(
            f"{t.get('trigger_name','Trigger')} — TER Target",
            min_value=0.01, max_value=1.0,
            value=float(t.get("engagement_rate_target", 0.20)),
            step=0.01, format="%.2f",
            key=f"br_ter_{i}"
        )
    cfg["triggers"] = triggers

    st.divider()

    # ── Segment Mix Targets ───────────────────────────────────────────────
    st.subheader("Segment Mix Targets")
    segments = cfg.get("segments", [])

    if not segments:
        st.info("No segments configured. Add segments in Campaign Setup to control distribution targets.")
    else:
        st.caption("Expected % of triggered users assigned to each segment.")
        total_pct = 0.0
        for i, s in enumerate(segments):
            s["distribution_pct"] = st.slider(
                f"{s.get('segment_name','Segment')} — Distribution %",
                min_value=0.0, max_value=100.0,
                value=float(s.get("distribution_pct", 0.0)),
                step=1.0, format="%.0f%%",
                key=f"br_seg_{i}"
            )
            total_pct += s["distribution_pct"]
        cfg["segments"] = segments
        if total_pct > 100.0:
            st.warning(f"Segment distributions sum to {total_pct:.0f}% (exceeds 100%). Adjust targets.")
        else:
            st.caption(f"Total configured: **{total_pct:.0f}%** of users")

    st.divider()

    # ── Journey Lengths ───────────────────────────────────────────────────
    st.subheader("Journey Lengths")
    st.caption("Duration (days) each user spends on each ad before advancing.")

    ads = cfg.get("ads", [])
    for i, ad in enumerate(ads):
        ad["duration_days"] = st.number_input(
            f"{ad.get('ad_name','Ad')} ({ad.get('channel','?')}) — Duration (days)",
            min_value=1, max_value=365,
            value=int(ad.get("duration_days", 7)),
            step=1,
            key=f"br_dur_{i}"
        )
    cfg["ads"] = ads

    st.divider()

    # ── Frequency & Cap Rules ─────────────────────────────────────────────
    st.subheader("Frequency & Cap Rules")

    col1, col2 = st.columns(2)
    cfg["weekly_impression_cap"] = col1.number_input(
        "Weekly Impression Cap",
        min_value=1, max_value=100,
        value=int(cfg.get("weekly_impression_cap", 7)),
        step=1,
        help="Max impressions per user per ISO week."
    )
    cfg["weekly_engagement_cap"] = col2.number_input(
        "Weekly Engagement Cap",
        min_value=1, max_value=100,
        value=int(cfg.get("weekly_engagement_cap", 3)),
        step=1,
        help="Max qualifying engagements (clicks/opens) per user per ISO week."
    )

    col1, col2 = st.columns(2)
    cfg["weekly_click_cap"] = col1.number_input(
        "Weekly Click Cap",
        min_value=1, max_value=100,
        value=int(cfg.get("weekly_click_cap", 3)),
        step=1
    )
    cfg["weekly_open_cap"] = col2.number_input(
        "Weekly Open Cap",
        min_value=1, max_value=100,
        value=int(cfg.get("weekly_open_cap", 5)),
        step=1
    )

    cfg["cooling_period_days"] = st.number_input(
        "Cooling Period (days)",
        min_value=0, max_value=365,
        value=int(cfg.get("cooling_period_days", 14)),
        step=1,
        help="Days a user must wait after completing a journey before re-entering."
    )

    cfg["allow_reentry"] = st.checkbox(
        "Allow Re-entry after cooling period",
        value=bool(cfg.get("allow_reentry", True))
    )

    st.divider()

    # ── Save ──────────────────────────────────────────────────────────────
    if st.button("💾 Save Business Rules", type="primary"):
        set_config_dict(cfg)
        st.success("✅ Business rules saved. Proceed to Run Simulation.")
        logger.info("Business rules saved for campaign: %s", cfg.get("campaign_id"))

    st.caption(
        "All changes above are applied automatically when you run the simulation. "
        "Click **Save Business Rules** to persist your changes in this session."
    )


__all__ = ["render"]
