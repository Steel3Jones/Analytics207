from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timezone
from auth import get_supabase, is_admin
from sidebar_auth import render_sidebar_auth
from auth import logout_button
import layout as L

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Admin — Analytics207",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar_auth()
logout_button()

render_logo   = getattr(L, "render_logo",   None)
render_footer = getattr(L, "render_footer", None)

# ─────────────────────────────────────────────
# ADMIN GATE — only admin role can see this
# ─────────────────────────────────────────────

if not is_admin():
    st.error("🔒 Access denied. Admin only.")
    st.stop()

# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Barlow:wght@400;500;600&display=swap');
.block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

if callable(render_logo):
    render_logo()

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_logs() -> pd.DataFrame:
    sb = get_supabase()
    res = sb.table("scraper_logs") \
            .select("*") \
            .order("ran_at", desc=True) \
            .limit(500) \
            .execute()
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    df["ran_at"] = pd.to_datetime(df["ran_at"], utc=True)
    return df

df = load_logs()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

st.markdown("""
<div style="font-family:'Barlow Condensed',sans-serif;">
  <div style="font-size:0.7rem;letter-spacing:0.2em;text-transform:uppercase;color:#fbbf24;margin-bottom:0.3rem;">
    Analytics207 · Admin
  </div>
  <div style="font-size:2.4rem;font-weight:900;text-transform:uppercase;color:#f8fafc;margin-bottom:0.2rem;">
    Scraper Dashboard
  </div>
  <div style="font-size:0.88rem;color:#64748b;margin-bottom:1.5rem;">
    Live view of nightly pipeline health · Auto-refreshes every 30 seconds
  </div>
</div>
""", unsafe_allow_html=True)

if st.button("🔄 Refresh Now"):
    st.cache_data.clear()
    st.rerun()

if df.empty:
    st.warning("No scraper logs found yet. Run your orchestrator once to start seeing data here.")
    st.stop()

# ─────────────────────────────────────────────
# SUMMARY STAT CARDS
# ─────────────────────────────────────────────

# Get last run for each scraper
latest = df.sort_values("ran_at").groupby("scraper_name").last().reset_index()

total        = len(latest)
success_ct   = len(latest[latest["status"] == "success"])
failed_ct    = len(latest[latest["status"] == "failed"])
partial_ct   = len(latest[latest["status"] == "partial"])

# Last orchestrator run
orch = df[df["scraper_name"] == "NIGHTLY_ORCHESTRATOR"].head(1)
last_run_str = "Never"
if not orch.empty:
    last_run = orch.iloc[0]["ran_at"]
    last_run_str = last_run.strftime("%b %d · %I:%M %p UTC")

col1, col2, col3, col4, col5 = st.columns(5)

def stat_card(col, label, value, color="#f8fafc", bg="rgba(15,23,42,0.7)", border="rgba(148,163,184,0.15)"):
    col.markdown(f"""
<div style="
  background:{bg}; border:1px solid {border};
  border-radius:14px; padding:1rem 1.1rem;
  font-family:'Barlow Condensed',sans-serif;
">
  <div style="font-size:0.62rem;letter-spacing:0.18em;text-transform:uppercase;color:#64748b;margin-bottom:0.2rem;">{label}</div>
  <div style="font-size:2rem;font-weight:900;color:{color};">{value}</div>
</div>
""", unsafe_allow_html=True)

stat_card(col1, "Last Nightly Run",  last_run_str,         "#7dd3fc")
stat_card(col2, "Scrapers Tracked",  total,                "#f8fafc")
stat_card(col3, "✓ Healthy",         success_ct,           "#4ade80", bg="rgba(34,197,94,0.08)",  border="rgba(34,197,94,0.2)")
stat_card(col4, "✗ Failed",          failed_ct,            "#f87171", bg="rgba(239,68,68,0.08)",  border="rgba(239,68,68,0.2)")
stat_card(col5, "⚠ Partial",         partial_ct,           "#fbbf24", bg="rgba(251,191,36,0.08)", border="rgba(251,191,36,0.2)")

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SCRAPER STATUS GRID
# ─────────────────────────────────────────────

st.markdown("""
<div style="font-family:'Barlow Condensed',sans-serif;font-size:1.3rem;font-weight:800;
text-transform:uppercase;color:#f8fafc;margin-bottom:1rem;">
  Pipeline Status — Last Run Per Scraper
</div>
""", unsafe_allow_html=True)

# Define pipeline order
PIPELINE_ORDER = [
    "NIGHTLY_ORCHESTRATOR",
    "MPA_SCRAPER_V50",
    "MPA_SCORES_SCRAPER_V50",
    "JOIN_SCORES_V50",
    "FIX_HOME_AWAY_TEAM_NAMES",
    "NIGHTLY_BUILD_V50",
    "SCRAPE_POSTSEASON",
    "GIT_PUSH",
    "SCORE_STUMP_PICKS",
    "SCORE_SURVIVOR_PICKS",
]

# Merge latest with pipeline order
latest_map = latest.set_index("scraper_name").to_dict("index")

cols = st.columns(2)
for i, name in enumerate(PIPELINE_ORDER):
    col = cols[i % 2]
    row = latest_map.get(name)

    if row:
        status   = row.get("status", "unknown")
        ran_at   = row.get("ran_at")
        duration = row.get("duration_seconds", 0)
        records  = row.get("records_processed", 0)
        error    = row.get("error_message", "")

        ran_str = ran_at.strftime("%b %d · %I:%M %p") if pd.notna(ran_at) else "—"
        dur_str = f"{duration}s" if duration else "—"
        rec_str = f"{records:,}" if records else "—"

        if status == "success":
            status_color = "#4ade80"
            status_bg    = "rgba(34,197,94,0.08)"
            status_border= "rgba(34,197,94,0.2)"
            status_icon  = "✓"
        elif status == "failed":
            status_color = "#f87171"
            status_bg    = "rgba(239,68,68,0.08)"
            status_border= "rgba(239,68,68,0.2)"
            status_icon  = "✗"
        else:
            status_color = "#fbbf24"
            status_bg    = "rgba(251,191,36,0.08)"
            status_border= "rgba(251,191,36,0.2)"
            status_icon  = "⚠"

        error_html = f"""
        <div style="margin-top:0.5rem;padding:0.4rem 0.6rem;
          background:rgba(239,68,68,0.1);border-radius:6px;
          font-size:0.75rem;color:#fca5a5;word-break:break-word;">
          {error}
        </div>""" if error and status == "failed" else ""

        col.markdown(f"""
<div style="
  background:{status_bg}; border:1px solid {status_border};
  border-radius:14px; padding:1rem 1.2rem; margin-bottom:0.85rem;
  font-family:'Barlow',sans-serif;
">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:0.85rem;
      font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:#f8fafc;">
      {name.replace("_", " ")}
    </div>
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:0.88rem;
      font-weight:800;color:{status_color};">
      {status_icon} {status.upper()}
    </div>
  </div>
  <div style="display:flex;gap:1.5rem;font-size:0.78rem;color:#64748b;">
    <span>🕐 {ran_str}</span>
    <span>⏱ {dur_str}</span>
    <span>📊 {rec_str} records</span>
  </div>
  {error_html}
</div>
""", unsafe_allow_html=True)

    else:
        col.markdown(f"""
<div style="
  background:rgba(15,23,42,0.4); border:1px solid rgba(148,163,184,0.08);
  border-radius:14px; padding:1rem 1.2rem; margin-bottom:0.85rem;
  font-family:'Barlow',sans-serif;
">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:0.85rem;
      font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:#334155;">
      {name.replace("_", " ")}
    </div>
    <div style="font-size:0.78rem;color:#334155;">No data yet</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# RECENT LOG TABLE
# ─────────────────────────────────────────────

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="font-family:'Barlow Condensed',sans-serif;font-size:1.3rem;font-weight:800;
text-transform:uppercase;color:#f8fafc;margin-bottom:1rem;">
  Recent Run History
</div>
""", unsafe_allow_html=True)

# Filters
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    scraper_options = ["All"] + sorted(df["scraper_name"].unique().tolist())
    selected_scraper = st.selectbox("Filter by scraper", scraper_options)

with filter_col2:
    status_options = ["All", "success", "failed", "partial"]
    selected_status = st.selectbox("Filter by status", status_options)

with filter_col3:
    show_n = st.selectbox("Show last N runs", [25, 50, 100, 200], index=0)

# Apply filters
filtered = df.copy()
if selected_scraper != "All":
    filtered = filtered[filtered["scraper_name"] == selected_scraper]
if selected_status != "All":
    filtered = filtered[filtered["status"] == selected_status]
filtered = filtered.head(show_n)

# Display
display_df = filtered[[
    "scraper_name", "status", "ran_at",
    "duration_seconds", "records_processed", "error_message"
]].copy()

display_df["ran_at"] = display_df["ran_at"].dt.strftime("%Y-%m-%d %H:%M UTC")
display_df.columns = ["Scraper", "Status", "Ran At", "Duration (s)", "Records", "Error"]

def color_status(val):
    if val == "success": return "color: #4ade80"
    if val == "failed":  return "color: #f87171"
    if val == "partial": return "color: #fbbf24"
    return ""

styled = display_df.style.applymap(color_status, subset=["Status"])
st.dataframe(styled, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# DATA HEALTH SECTION
# ─────────────────────────────────────────────

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="font-family:'Barlow Condensed',sans-serif;font-size:1.3rem;font-weight:800;
text-transform:uppercase;color:#f8fafc;margin-bottom:1rem;">
  Pipeline Health — Last 7 Days
</div>
""", unsafe_allow_html=True)

# Success rate per scraper over last 7 days
cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)
recent = df[df["ran_at"] >= cutoff]

if not recent.empty:
    health = recent.groupby("scraper_name")["status"].apply(
        lambda x: round((x == "success").sum() / len(x) * 100, 1)
    ).reset_index()
    health.columns = ["Scraper", "Success Rate (%)"]
    health = health.sort_values("Success Rate (%)", ascending=False)

    h_col1, h_col2 = st.columns(2)
    for idx, row in health.iterrows():
        col = h_col1 if idx % 2 == 0 else h_col2
        rate = row["Success Rate (%)"]
        bar_color = "#4ade80" if rate >= 90 else "#fbbf24" if rate >= 70 else "#f87171"
        col.markdown(f"""
<div style="margin-bottom:0.6rem;">
  <div style="display:flex;justify-content:space-between;
    font-family:'Barlow Condensed',sans-serif;font-size:0.78rem;
    color:#94a3b8;margin-bottom:0.25rem;">
    <span>{row['Scraper'].replace('_',' ')}</span>
    <span style="color:{bar_color};font-weight:700;">{rate}%</span>
  </div>
  <div style="background:rgba(15,23,42,0.8);border-radius:999px;height:6px;overflow:hidden;">
    <div style="width:{rate}%;height:100%;background:{bar_color};border-radius:999px;"></div>
  </div>
</div>
""", unsafe_allow_html=True)
else:
    st.info("No runs in the last 7 days yet.")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
if callable(render_footer):
    render_footer()
else:
    st.caption("© 2026 Analytics207 · Admin")