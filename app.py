"""Engagement Data Generator — Streamlit MVP (Stage 11).

Entry point:
    streamlit run app.py

Navigation (sidebar):
    1. Upload Files
    2. Campaign Setup
    3. Business Rules
    4. Run Simulation
    5. Results
"""
from __future__ import annotations

import streamlit as st

# ── Page config must be first Streamlit call ──────────────────────────────
st.set_page_config(
    page_title="Engagement Data Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.state import init_session_state, KEY_ACTIVE_PAGE

# Initialise session state on every rerun
init_session_state()

# ── Sidebar navigation ────────────────────────────────────────────────────
PAGES: list[tuple[str, str]] = [
    ("📁 Upload Files",    "upload"),
    ("🏷️ Campaign Setup",  "campaign"),
    ("📐 Business Rules",  "rules"),
    ("🚀 Run Simulation",  "run"),
    ("📊 Results",         "results"),
]

st.sidebar.title("📊 Engagement Data Generator")
st.sidebar.markdown("---")

# Determine which page is active
active = st.session_state.get(KEY_ACTIVE_PAGE, "upload")

for label, key in PAGES:
    is_current = active == key
    if st.sidebar.button(
        label,
        key=f"nav_{key}",
        use_container_width=True,
        type="primary" if is_current else "secondary",
    ):
        st.session_state[KEY_ACTIVE_PAGE] = key
        active = key

st.sidebar.markdown("---")

# Quick status indicators in sidebar
from ui.state import get_trigger_df, get_config_dict, get_result

tdf = get_trigger_df()
cfg = get_config_dict()
res = get_result()

st.sidebar.markdown("**Status**")
st.sidebar.markdown(
    f"{'✅' if tdf is not None else '⬜'} Data uploaded"
)
st.sidebar.markdown(
    f"{'✅' if cfg is not None else '⬜'} Campaign configured"
)
st.sidebar.markdown(
    f"{'✅' if res is not None else '⬜'} Simulation run"
)

if res is not None:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Last Run**")
    st.sidebar.metric("Quality",  f"{res.quality_score:.1f}/100")
    st.sidebar.metric("Realism",  f"{res.realism_score:.1f}/100")
    st.sidebar.metric("Events",   f"{res.n_events:,}")

# ── Route to active page ─────────────────────────────────────────────────
active = st.session_state.get(KEY_ACTIVE_PAGE, "upload")

if active == "upload":
    from ui.upload_page import render
    render()
elif active == "campaign":
    from ui.campaign_page import render
    render()
elif active == "rules":
    from ui.business_rules_page import render
    render()
elif active == "run":
    from ui.run_page import render
    render()
elif active == "results":
    from ui.results_page import render
    render()
else:
    st.error(f"Unknown page: {active!r}")
