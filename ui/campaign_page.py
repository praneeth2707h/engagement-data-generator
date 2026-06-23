"""Page 2 — Campaign Setup.

Lets the user define:
  * Campaign identity (ID, name)
  * Simulation date range
  * Ads (channel, vendor, CTR target, duration, order)
  * Triggers (name, priority, engagement rate target)
  * Segments (name, priority, distribution %)
  * Channels (name, CTR, open rate)

Writes a config dict to session_state that business_rules_page.py
can then augment with cap overrides.
"""
from __future__ import annotations
import logging
from datetime import date, timedelta

import streamlit as st

from ui.state import get_config_dict, set_config_dict, get_trigger_df

logger = logging.getLogger(__name__)

_CHANNEL_OPTIONS = ["Display", "Email", "WhatsApp",
                    "Endemic_Display", "Programmatic_Display", "Banner"]


def _default_config() -> dict:
    """Return a minimal sensible default config dict."""
    today = date.today()
    return {
        "campaign_id":    "CAMPAIGN_001",
        "campaign_name":  "New Campaign",
        "vendor":         "VendorX",
        "simulation_start_date": today.isoformat(),
        "simulation_end_date":   (today + timedelta(days=29)).isoformat(),
        "cooling_period_days":   14,
        "weekly_impression_cap": 7,
        "weekly_engagement_cap": 3,
        "weekly_click_cap":      3,
        "weekly_open_cap":       5,
        "allow_reentry":         True,
        "historical_engagement_window": "Last_90_Days",
        "ads": [
            {"ad_name": "Ad_A", "ad_order": 1, "duration_days": 7,
             "move_on_click": False, "channel": "Display",
             "vendor": None, "target_ctr": 0.10},
        ],
        "triggers": [
            {"trigger_name": "T1", "priority": 1,
             "engagement_rate_target": 0.20, "distribution_pct": 100.0},
        ],
        "segments": [],
        "channels": [],
        "rules": [
            {"rule_id": "R-001", "rule_name": "Default",
             "severity": "Soft", "enabled": True, "threshold": None},
        ],
    }


def render() -> None:
    """Render the Campaign Setup page."""
    st.header("⚙️ Campaign Setup")

    # Seed defaults if nothing configured yet
    cfg = get_config_dict() or _default_config()

    # ── Identity ─────────────────────────────────────────────────────────
    st.subheader("Campaign Identity")
    col1, col2 = st.columns(2)
    cfg["campaign_id"]   = col1.text_input("Campaign ID",   value=cfg.get("campaign_id", ""))
    cfg["campaign_name"] = col2.text_input("Campaign Name", value=cfg.get("campaign_name", ""))
    cfg["vendor"]        = st.text_input("Default Vendor",  value=cfg.get("vendor", ""))

    # ── Simulation dates ──────────────────────────────────────────────────
    st.subheader("Simulation Period")
    col1, col2 = st.columns(2)

    try:
        start_default = date.fromisoformat(cfg.get("simulation_start_date", date.today().isoformat()))
    except ValueError:
        start_default = date.today()
    try:
        end_default = date.fromisoformat(cfg.get("simulation_end_date", (date.today() + timedelta(29)).isoformat()))
    except ValueError:
        end_default = date.today() + timedelta(29)

    sim_start = col1.date_input("Start Date", value=start_default)
    sim_end   = col2.date_input("End Date",   value=end_default)

    if isinstance(sim_end, date) and isinstance(sim_start, date) and sim_end < sim_start:
        st.error("End date must be on or after start date.")
    else:
        cfg["simulation_start_date"] = sim_start.isoformat()
        cfg["simulation_end_date"]   = sim_end.isoformat()
        n_days = (sim_end - sim_start).days + 1
        st.caption(f"Simulation length: **{n_days}** days")

    # ── Ads ───────────────────────────────────────────────────────────────
    st.subheader("Journey Ads")
    st.caption("Define the ordered sequence of ads a user moves through.")

    ads = cfg.get("ads", [])
    n_ads = st.number_input("Number of Ads", min_value=1, max_value=10,
                             value=max(1, len(ads)), step=1)
    # Resize list
    while len(ads) < n_ads:
        ads.append({"ad_name": f"Ad_{chr(65+len(ads))}", "ad_order": len(ads)+1,
                    "duration_days": 7, "move_on_click": False,
                    "channel": "Display", "vendor": None, "target_ctr": 0.10})
    ads = ads[:n_ads]

    for i, ad in enumerate(ads):
        with st.expander(f"Ad {i+1}: {ad.get('ad_name','')}", expanded=(i == 0)):
            c1, c2, c3 = st.columns(3)
            ad["ad_name"]      = c1.text_input("Ad Name",    value=ad.get("ad_name", f"Ad_{i}"),   key=f"ad_name_{i}")
            ad["channel"]      = c2.selectbox("Channel",     options=_CHANNEL_OPTIONS,
                                               index=_CHANNEL_OPTIONS.index(ad.get("channel","Display")),
                                               key=f"ad_ch_{i}")
            ad["vendor"]       = c3.text_input("Vendor Override (blank = default)",
                                               value=ad.get("vendor") or "", key=f"ad_vend_{i}") or None
            c1, c2, c3 = st.columns(3)
            ad["ad_order"]      = i + 1
            ad["duration_days"] = c1.number_input("Duration (days)", min_value=1, max_value=365,
                                                   value=int(ad.get("duration_days", 7)), key=f"ad_dur_{i}")
            ad["target_ctr"]    = c2.number_input("Target CTR", min_value=0.001, max_value=1.0,
                                                   value=float(ad.get("target_ctr", 0.10)),
                                                   step=0.01, format="%.3f", key=f"ad_ctr_{i}")
            ad["move_on_click"] = c3.checkbox("Advance on Click", value=bool(ad.get("move_on_click", False)),
                                               key=f"ad_moc_{i}")
    cfg["ads"] = ads

    # ── Triggers ──────────────────────────────────────────────────────────
    st.subheader("Triggers")
    st.caption("Each trigger represents a cohort of users entering the journey.")

    # Auto-populate trigger names from trigger file if available
    trigger_df = get_trigger_df()
    auto_triggers: list[str] = []
    if trigger_df is not None and "Trigger_Name" in trigger_df.columns:
        auto_triggers = sorted(trigger_df["Trigger_Name"].dropna().unique().tolist())

    triggers = cfg.get("triggers", [])
    n_triggers = st.number_input("Number of Triggers", min_value=1, max_value=10,
                                  value=max(1, len(triggers)), step=1)
    while len(triggers) < n_triggers:
        name = auto_triggers[len(triggers)] if len(triggers) < len(auto_triggers) else f"T{len(triggers)+1}"
        triggers.append({"trigger_name": name, "priority": len(triggers)+1,
                         "engagement_rate_target": 0.20, "distribution_pct": 0.0})
    triggers = triggers[:n_triggers]

    if auto_triggers:
        st.info(f"Detected trigger names from file: {', '.join(auto_triggers)}")

    for i, t in enumerate(triggers):
        with st.expander(f"Trigger {i+1}: {t.get('trigger_name','')}", expanded=(i == 0)):
            c1, c2, c3 = st.columns(3)
            t["trigger_name"]            = c1.text_input("Trigger Name", value=t.get("trigger_name",""), key=f"t_name_{i}")
            t["priority"]                = c2.number_input("Priority", min_value=1, max_value=100,
                                                            value=int(t.get("priority", i+1)), key=f"t_pri_{i}")
            t["engagement_rate_target"]  = c3.number_input("Engagement Rate Target",
                                                            min_value=0.001, max_value=1.0,
                                                            value=float(t.get("engagement_rate_target", 0.20)),
                                                            step=0.01, format="%.3f", key=f"t_ter_{i}")
    cfg["triggers"] = triggers

    # ── Segments ──────────────────────────────────────────────────────────
    st.subheader("Segments (optional)")

    auto_segments: list[str] = []
    if trigger_df is not None and "Segment" in trigger_df.columns:
        auto_segments = sorted(trigger_df["Segment"].dropna().unique().tolist())
        if auto_segments:
            st.info(f"Detected segment names from file: {', '.join(auto_segments)}")

    segments = cfg.get("segments", [])
    n_segs = st.number_input("Number of Segments (0 = none)", min_value=0, max_value=10,
                              value=len(segments), step=1)
    while len(segments) < n_segs:
        name = auto_segments[len(segments)] if len(segments) < len(auto_segments) else f"Seg_{len(segments)+1}"
        segments.append({"segment_name": name, "priority": len(segments)+1, "distribution_pct": 0.0})
    segments = segments[:n_segs]

    for i, s in enumerate(segments):
        c1, c2, c3 = st.columns(3)
        s["segment_name"]    = c1.text_input("Segment Name",    value=s.get("segment_name",""), key=f"s_name_{i}")
        s["priority"]        = c2.number_input("Priority",      min_value=1, value=int(s.get("priority",i+1)), key=f"s_pri_{i}")
        s["distribution_pct"]= c3.number_input("Distribution %", min_value=0.0, max_value=100.0,
                                                value=float(s.get("distribution_pct", 0.0)),
                                                step=1.0, format="%.1f", key=f"s_dist_{i}")
    cfg["segments"] = segments

    # ── Save ──────────────────────────────────────────────────────────────
    st.divider()
    if st.button("💾 Save Campaign Setup", type="primary"):
        if not cfg.get("campaign_id","").strip():
            st.error("Campaign ID is required.")
        elif not cfg.get("vendor","").strip():
            st.error("Default Vendor is required.")
        elif not cfg.get("ads"):
            st.error("At least one ad is required.")
        elif not cfg.get("triggers"):
            st.error("At least one trigger is required.")
        else:
            set_config_dict(cfg)
            st.success("✅ Campaign setup saved. Proceed to Business Rules.")
            logger.info("Campaign config saved: %s", cfg.get("campaign_id"))

    if get_config_dict():
        st.caption("✅ Campaign setup already saved.")


__all__ = ["render"]
