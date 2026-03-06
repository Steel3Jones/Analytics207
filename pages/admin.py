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
# ADMIN GATE
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

.adm-section-head {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.3rem; font-weight: 800;
    text-transform: uppercase; color: #f8fafc;
    margin-bottom: 1rem;
}
.adm-stat-card {
    background: rgba(15,23,42,0.7);
    border: 1px solid rgba(148,163,184,0.15);
    border-radius: 14px; padding: 1rem 1.1rem;
    font-family: 'Barlow Condensed', sans-serif;
}
.adm-stat-label {
    font-size: 0.62rem; letter-spacing: 0.18em;
    text-transform: uppercase; color: #64748b; margin-bottom: 0.2rem;
}
.adm-stat-value { font-size: 2rem; font-weight: 900; }

.adm-user-card {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.18);
    border-radius: 12px; padding: 14px 16px; margin-bottom: 10px;
}
.adm-row {
    display: flex; align-items: center; gap: 12px;
    padding: 9px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.84rem; color: #e2e8f0;
}
.adm-row:last-child { border-bottom: none; }
.adm-table-wrap {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.15);
    border-radius: 12px; overflow-x: auto; margin: 8px 0 16px;
}
</style>
""", unsafe_allow_html=True)

if callable(render_logo):
    render_logo()

# ─────────────────────────────────────────────
# JWT / SESSION HELPERS
# ─────────────────────────────────────────────

def _is_jwt_error(e: Exception) -> bool:
    msg = str(e).lower()
    return "jwt" in msg or "expired" in msg or "pgrst303" in msg or "401" in msg

def _jwt_banner() -> None:
    """Show a session-expired banner and stop rendering."""
    st.markdown(
        '<div style="background:rgba(239,68,68,0.10);border:1px solid rgba(239,68,68,0.35);'
        'border-left:4px solid #f87171;border-radius:10px;padding:14px 20px;margin-bottom:16px;">'
        '<div style="font-size:0.88rem;font-weight:800;color:#fca5a5;margin-bottom:4px;">Session Expired</div>'
        '<div style="font-size:0.80rem;color:#fecaca;line-height:1.55;">'
        'Your admin session JWT has expired. Sign out and sign back in, then return to this page.'
        '</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("🔄 Clear Cache & Retry"):
        st.cache_data.clear()
        st.rerun()

# ─────────────────────────────────────────────
# SHARED LOADERS
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


@st.cache_data(ttl=60)
def load_profiles():
    """Try common profile/user table names."""
    sb = get_supabase()
    for table in ["profiles", "user_profiles", "users"]:
        try:
            res = sb.table(table).select("*").execute()
            if res.data is not None:
                return pd.DataFrame(res.data), table
        except Exception:
            continue
    return pd.DataFrame(), None


@st.cache_data(ttl=60)
def load_subscribers():
    """Try common subscription table names."""
    sb = get_supabase()
    for table in ["subscribers", "subscriptions", "subscriber_roles", "user_roles"]:
        try:
            res = sb.table(table).select("*").execute()
            if res.data is not None:
                return pd.DataFrame(res.data), table
        except Exception:
            continue
    return pd.DataFrame(), None


@st.cache_data(ttl=60)
def load_pick5() -> pd.DataFrame:
    sb = get_supabase()
    try:
        res = sb.table("pick_5_rosters").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_contact_messages():
    sb = get_supabase()
    for table in ["contact_messages", "pressbox_messages"]:
        try:
            res = sb.table(table).select("*").order("Timestamp", desc=True).limit(200).execute()
            if res.data is not None:
                return pd.DataFrame(res.data), table
        except Exception:
            continue
    return pd.DataFrame(), None


def _safe_load_logs() -> pd.DataFrame | None:
    """Returns None on JWT error (caller should stop rendering)."""
    try:
        return load_logs()
    except Exception as e:
        if _is_jwt_error(e):
            return None
        raise


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

st.markdown("""
<div style="font-family:'Barlow Condensed',sans-serif;">
  <div style="font-size:0.7rem;letter-spacing:0.2em;text-transform:uppercase;color:#fbbf24;margin-bottom:0.3rem;">
    Analytics207 · Admin
  </div>
  <div style="font-size:2.4rem;font-weight:900;text-transform:uppercase;color:#f8fafc;margin-bottom:0.2rem;">
    Operations Dashboard
  </div>
  <div style="font-size:0.88rem;color:#64748b;margin-bottom:1.2rem;">
    Pipeline health · Users & subscribers · Fan engagement
  </div>
</div>
""", unsafe_allow_html=True)

if st.button("🔄 Refresh Now"):
    st.cache_data.clear()
    st.rerun()

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab_pipeline, tab_users, tab_fans = st.tabs([
    "⚙️ Pipeline",
    "👥 Users & Subscribers",
    "🎮 Fan Engagement",
])

# ════════════════════════════════════════════════════════════════════════
# TAB 1 — PIPELINE (existing content)
# ════════════════════════════════════════════════════════════════════════

with tab_pipeline:
    df = _safe_load_logs()

    if df is None:
        _jwt_banner()
        st.stop()

    if df.empty:
        st.warning("No scraper logs found yet. Run your orchestrator once to start seeing data here.")
    else:
        # ── Summary stat cards ───────────────────────────────────────────
        latest     = df.sort_values("ran_at").groupby("scraper_name").last().reset_index()
        total      = len(latest)
        success_ct = len(latest[latest["status"] == "success"])
        failed_ct  = len(latest[latest["status"] == "failed"])
        partial_ct = len(latest[latest["status"] == "partial"])

        orch = df[df["scraper_name"] == "NIGHTLY_ORCHESTRATOR"].head(1)
        last_run_str = "Never"
        if not orch.empty:
            last_run = orch.iloc[0]["ran_at"]
            last_run_str = last_run.strftime("%b %d · %I:%M %p UTC")

        col1, col2, col3, col4, col5 = st.columns(5)

        def stat_card(col, label, value, color="#f8fafc", bg="rgba(15,23,42,0.7)", border="rgba(148,163,184,0.15)"):
            col.markdown(
                f'<div style="background:{bg};border:1px solid {border};border-radius:14px;padding:1rem 1.1rem;'
                f'font-family:\'Barlow Condensed\',sans-serif;">'
                f'<div style="font-size:0.62rem;letter-spacing:0.18em;text-transform:uppercase;color:#64748b;margin-bottom:0.2rem;">{label}</div>'
                f'<div style="font-size:2rem;font-weight:900;color:{color};">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        stat_card(col1, "Last Nightly Run",  last_run_str, "#7dd3fc")
        stat_card(col2, "Scrapers Tracked",  total,        "#f8fafc")
        stat_card(col3, "✓ Healthy",  success_ct, "#4ade80", "rgba(34,197,94,0.08)",   "rgba(34,197,94,0.2)")
        stat_card(col4, "✗ Failed",   failed_ct,  "#f87171", "rgba(239,68,68,0.08)",   "rgba(239,68,68,0.2)")
        stat_card(col5, "⚠ Partial",  partial_ct, "#fbbf24", "rgba(251,191,36,0.08)",  "rgba(251,191,36,0.2)")

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

        # ── Pipeline status grid ─────────────────────────────────────────
        st.markdown('<div class="adm-section-head">Pipeline Status — Last Run Per Scraper</div>', unsafe_allow_html=True)

        PIPELINE_ORDER = [
            "NIGHTLY_ORCHESTRATOR", "MPA_SCRAPER_V50", "MPA_SCORES_SCRAPER_V50",
            "JOIN_SCORES_V50", "FIX_HOME_AWAY_TEAM_NAMES", "NIGHTLY_BUILD_V50",
            "SCRAPE_POSTSEASON", "GIT_PUSH", "SCORE_STUMP_PICKS", "SCORE_SURVIVOR_PICKS",
        ]
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
                ran_str  = ran_at.strftime("%b %d · %I:%M %p") if pd.notna(ran_at) else "—"
                dur_str  = f"{duration}s" if duration else "—"
                rec_str  = f"{records:,}" if records else "—"
                if status == "success":
                    sc, sb2, sborder, si = "#4ade80", "rgba(34,197,94,0.08)",  "rgba(34,197,94,0.2)",  "✓"
                elif status == "failed":
                    sc, sb2, sborder, si = "#f87171", "rgba(239,68,68,0.08)",  "rgba(239,68,68,0.2)",  "✗"
                else:
                    sc, sb2, sborder, si = "#fbbf24", "rgba(251,191,36,0.08)", "rgba(251,191,36,0.2)", "⚠"
                error_html = (
                    f'<div style="margin-top:0.5rem;padding:0.4rem 0.6rem;background:rgba(239,68,68,0.1);'
                    f'border-radius:6px;font-size:0.75rem;color:#fca5a5;word-break:break-word;">{error}</div>'
                    if error and status == "failed" else ""
                )
                col.markdown(
                    f'<div style="background:{sb2};border:1px solid {sborder};border-radius:14px;'
                    f'padding:1rem 1.2rem;margin-bottom:0.85rem;font-family:\'Barlow\',sans-serif;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">'
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:0.85rem;font-weight:800;'
                    f'text-transform:uppercase;letter-spacing:0.08em;color:#f8fafc;">{name.replace("_"," ")}</div>'
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:0.88rem;font-weight:800;color:{sc};">{si} {status.upper()}</div>'
                    f'</div>'
                    f'<div style="display:flex;gap:1.5rem;font-size:0.78rem;color:#64748b;">'
                    f'<span>🕐 {ran_str}</span><span>⏱ {dur_str}</span><span>📊 {rec_str} records</span>'
                    f'</div>{error_html}</div>',
                    unsafe_allow_html=True,
                )
            else:
                col.markdown(
                    f'<div style="background:rgba(15,23,42,0.4);border:1px solid rgba(148,163,184,0.08);'
                    f'border-radius:14px;padding:1rem 1.2rem;margin-bottom:0.85rem;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:0.85rem;font-weight:800;'
                    f'text-transform:uppercase;letter-spacing:0.08em;color:#334155;">{name.replace("_"," ")}</div>'
                    f'<div style="font-size:0.78rem;color:#334155;">No data yet</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

        # ── Recent log table ─────────────────────────────────────────────
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="adm-section-head">Recent Run History</div>', unsafe_allow_html=True)

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            scraper_options  = ["All"] + sorted(df["scraper_name"].unique().tolist())
            selected_scraper = st.selectbox("Filter by scraper", scraper_options)
        with fc2:
            selected_status = st.selectbox("Filter by status", ["All", "success", "failed", "partial"])
        with fc3:
            show_n = st.selectbox("Show last N runs", [25, 50, 100, 200], index=0)

        filtered = df.copy()
        if selected_scraper != "All":
            filtered = filtered[filtered["scraper_name"] == selected_scraper]
        if selected_status != "All":
            filtered = filtered[filtered["status"] == selected_status]
        filtered = filtered.head(show_n)

        display_df = filtered[["scraper_name","status","ran_at","duration_seconds","records_processed","error_message"]].copy()
        display_df["ran_at"] = display_df["ran_at"].dt.strftime("%Y-%m-%d %H:%M UTC")
        display_df.columns = ["Scraper","Status","Ran At","Duration (s)","Records","Error"]

        def color_status(val):
            if val == "success": return "color: #4ade80"
            if val == "failed":  return "color: #f87171"
            if val == "partial": return "color: #fbbf24"
            return ""

        st.dataframe(
            display_df.style.applymap(color_status, subset=["Status"]),
            use_container_width=True, hide_index=True,
        )

        # ── 7-day health bars ────────────────────────────────────────────
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="adm-section-head">Pipeline Health — Last 7 Days</div>', unsafe_allow_html=True)
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)
        recent = df[df["ran_at"] >= cutoff]
        if not recent.empty:
            health = recent.groupby("scraper_name")["status"].apply(
                lambda x: round((x == "success").sum() / len(x) * 100, 1)
            ).reset_index()
            health.columns = ["Scraper", "Success Rate (%)"]
            health = health.sort_values("Success Rate (%)", ascending=False)
            h1, h2 = st.columns(2)
            for idx, row in health.iterrows():
                col = h1 if idx % 2 == 0 else h2
                rate = row["Success Rate (%)"]
                bc = "#4ade80" if rate >= 90 else "#fbbf24" if rate >= 70 else "#f87171"
                col.markdown(
                    f'<div style="margin-bottom:0.6rem;">'
                    f'<div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#94a3b8;margin-bottom:0.25rem;">'
                    f'<span>{row["Scraper"].replace("_"," ")}</span>'
                    f'<span style="color:{bc};font-weight:700;">{rate}%</span></div>'
                    f'<div style="background:rgba(15,23,42,0.8);border-radius:999px;height:6px;overflow:hidden;">'
                    f'<div style="width:{rate}%;height:100%;background:{bc};border-radius:999px;"></div></div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No runs in the last 7 days yet.")


# ════════════════════════════════════════════════════════════════════════
# TAB 2 — USERS & SUBSCRIBERS
# ════════════════════════════════════════════════════════════════════════

with tab_users:
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    profiles_df, profiles_table = load_profiles()
    subs_df,     subs_table     = load_subscribers()

    # ── Hero stat cards ──────────────────────────────────────────────────
    def _ucard(col, label, value, color, bg, border):
        col.markdown(
            f'<div style="background:{bg};border:1px solid {border};border-radius:14px;'
            f'padding:1rem 1.1rem;font-family:\'Barlow Condensed\',sans-serif;">'
            f'<div style="font-size:0.62rem;letter-spacing:0.18em;text-transform:uppercase;'
            f'color:#64748b;margin-bottom:0.2rem;">{label}</div>'
            f'<div style="font-size:2rem;font-weight:900;color:{color};">{value}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if not profiles_df.empty:
        total_users = len(profiles_df)

        # Try to identify subscriber vs free from profiles
        sub_col = next((c for c in ["is_subscribed","subscribed","tier","role","plan"] if c in profiles_df.columns), None)
        if sub_col:
            sub_mask    = profiles_df[sub_col].astype(str).str.lower().isin(["true","1","subscriber","paid","pro","premium"])
            total_subs  = int(sub_mask.sum())
            total_free  = total_users - total_subs
        else:
            total_subs = "—"
            total_free = "—"

        # New this week
        date_col = next((c for c in ["created_at","joined_at","signup_at"] if c in profiles_df.columns), None)
        new_this_week = "—"
        if date_col:
            profiles_df[date_col] = pd.to_datetime(profiles_df[date_col], utc=True, errors="coerce")
            cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)
            new_this_week = int((profiles_df[date_col] >= cutoff).sum())

        u1, u2, u3, u4 = st.columns(4)
        _ucard(u1, "Total Users",       total_users,    "#f8fafc", "rgba(15,23,42,0.7)",      "rgba(148,163,184,0.15)")
        _ucard(u2, "Subscribers",       total_subs,     "#4ade80", "rgba(34,197,94,0.08)",    "rgba(34,197,94,0.2)")
        _ucard(u3, "Free Users",        total_free,     "#60a5fa", "rgba(96,165,250,0.08)",   "rgba(96,165,250,0.2)")
        _ucard(u4, "New This Week",     new_this_week,  "#fbbf24", "rgba(251,191,36,0.08)",   "rgba(251,191,36,0.2)")

        st.caption(f"Source: `{profiles_table}` table · {total_users} rows")
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # ── Subscriber table (if separate) ───────────────────────────────
        if not subs_df.empty:
            st.markdown('<div class="adm-section-head">Subscriber Records</div>', unsafe_allow_html=True)
            st.caption(f"Source: `{subs_table}` table · {len(subs_df)} rows")
            st.dataframe(subs_df.head(50), use_container_width=True, hide_index=True)

        # ── Recent signups ────────────────────────────────────────────────
        if date_col:
            st.markdown('<div class="adm-section-head">Recent Signups</div>', unsafe_allow_html=True)
            recent_users = (
                profiles_df.sort_values(date_col, ascending=False)
                .head(25)
            )
            show_cols = [c for c in ["email","display_name","full_name","role","tier","is_subscribed","created_at"] if c in recent_users.columns]
            if show_cols:
                st.dataframe(recent_users[show_cols], use_container_width=True, hide_index=True)
            else:
                st.dataframe(recent_users.head(25), use_container_width=True, hide_index=True)

    elif not subs_df.empty:
        # Only subscribers table found
        total_subs = len(subs_df)
        u1, u2 = st.columns(2)
        _ucard(u1, "Subscriber Records", total_subs, "#4ade80", "rgba(34,197,94,0.08)", "rgba(34,197,94,0.2)")
        st.caption(f"Source: `{subs_table}` · {total_subs} rows")
        st.markdown('<div class="adm-section-head">Subscriber Table</div>', unsafe_allow_html=True)
        st.dataframe(subs_df.head(50), use_container_width=True, hide_index=True)

    else:
        st.markdown(
            '<div style="background:rgba(96,165,250,0.07);border:1px solid rgba(96,165,250,0.25);'
            'border-radius:12px;padding:16px 20px;margin-top:8px;">'
            '<div style="font-size:0.88rem;font-weight:700;color:#93c5fd;margin-bottom:6px;">No user tables found yet</div>'
            '<div style="font-size:0.80rem;color:#bfdbfe;line-height:1.6;">'
            'Looked for: <code>profiles</code>, <code>user_profiles</code>, <code>users</code>, '
            '<code>subscribers</code>, <code>subscriptions</code>, <code>subscriber_roles</code>, <code>user_roles</code>.<br>'
            'Create one of these tables in Supabase and this section will populate automatically.'
            '</div></div>',
            unsafe_allow_html=True,
        )

    # ── Contact messages preview ─────────────────────────────────────────
    contact_df, contact_table = load_contact_messages()
    if not contact_df.empty:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="adm-section-head">Pressbox Inbox</div>', unsafe_allow_html=True)
        st.caption(f"{len(contact_df)} messages · source: `{contact_table}`")
        st.dataframe(contact_df.head(25), use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════
# TAB 3 — FAN ENGAGEMENT
# ════════════════════════════════════════════════════════════════════════

with tab_fans:
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    pick5_df = load_pick5()

    # ── Pick 5 ───────────────────────────────────────────────────────────
    st.markdown('<div class="adm-section-head">💎 Pick 5 Challenge</div>', unsafe_allow_html=True)

    if not pick5_df.empty:
        total_picks      = len(pick5_df)
        total_managers   = pick5_df["Manager"].nunique()  if "Manager"  in pick5_df.columns else "—"
        total_weeks      = pick5_df["WeekID"].nunique()   if "WeekID"   in pick5_df.columns else "—"
        total_game_ids   = pick5_df["GameID"].nunique()   if "GameID"   in pick5_df.columns else "—"

        f1, f2, f3, f4 = st.columns(4)
        for col, label, val, color in [
            (f1, "Total Picks Submitted", total_picks,    "#60a5fa"),
            (f2, "Unique Managers",        total_managers, "#4ade80"),
            (f3, "Weeks Active",           total_weeks,    "#fbbf24"),
            (f4, "Unique Games Picked",    total_game_ids, "#a78bfa"),
        ]:
            col.markdown(
                f'<div style="background:radial-gradient(circle at top left,#0f1e38,#080f1e);'
                f'border:1px solid rgba(96,165,250,0.18);border-radius:14px;padding:1rem 1.1rem;'
                f'font-family:\'Barlow Condensed\',sans-serif;">'
                f'<div style="font-size:0.62rem;letter-spacing:0.18em;text-transform:uppercase;color:#94a3b8;margin-bottom:0.2rem;">{label}</div>'
                f'<div style="font-size:2rem;font-weight:900;color:{color};">{val}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # Weekly participation
        if "WeekID" in pick5_df.columns and "Manager" in pick5_df.columns:
            st.markdown("**Participation by week**")
            weekly = (
                pick5_df.groupby("WeekID")
                .agg(Managers=("Manager", "nunique"), Picks=("Manager", "count"))
                .reset_index()
                .sort_values("WeekID", ascending=False)
            )
            st.dataframe(weekly, use_container_width=True, hide_index=True)

        # Top managers by points
        if "Manager" in pick5_df.columns and "ActualPts" in pick5_df.columns:
            st.markdown("**All-time leaderboard**")
            pick5_df["Pts"] = pd.to_numeric(pick5_df["ActualPts"], errors="coerce").fillna(0)
            lb = (
                pick5_df.groupby("Manager")
                .agg(TotalPts=("Pts","sum"), Picks=("Manager","count"), Weeks=("WeekID","nunique"))
                .reset_index()
                .sort_values("TotalPts", ascending=False)
                .reset_index(drop=True)
            )
            st.dataframe(lb, use_container_width=True, hide_index=True)

        # Class breakdown
        if "Class" in pick5_df.columns:
            st.markdown("**Picks by class**")
            cls_counts = pick5_df["Class"].value_counts().reset_index()
            cls_counts.columns = ["Class", "Picks"]
            st.dataframe(cls_counts, use_container_width=True, hide_index=True)

        st.caption(f"Source: `pick_5_rosters` · {total_picks} rows total")

    else:
        st.info("No Pick 5 data yet — picks will appear here once players start submitting.")

    # ── Other fan tables ─────────────────────────────────────────────────
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="adm-section-head">Other Fan Tables</div>', unsafe_allow_html=True)

    sb = get_supabase()
    other_tables = ["survivor_picks", "stump_picks", "fan_votes", "bracket_picks"]
    found_any = False

    cols2 = st.columns(2)
    for i, table in enumerate(other_tables):
        try:
            res = sb.table(table).select("*").limit(1).execute()
            # If no error, table exists — get full count
            count_res = sb.table(table).select("*", count="exact").execute()
            row_count = count_res.count if hasattr(count_res, "count") and count_res.count else len(count_res.data or [])
            found_any = True

            # Get unique user count if possible
            if count_res.data:
                tdf = pd.DataFrame(count_res.data)
                user_col = next((c for c in ["user_id","Manager","manager","player"] if c in tdf.columns), None)
                uniq = tdf[user_col].nunique() if user_col else "—"
            else:
                uniq = "—"

            cols2[i % 2].markdown(
                f'<div style="background:radial-gradient(circle at top left,#0f1e38,#080f1e);'
                f'border:1px solid rgba(96,165,250,0.18);border-radius:12px;padding:14px 16px;margin-bottom:10px;">'
                f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.10em;text-transform:uppercase;color:#94a3b8;margin-bottom:6px;">{table}</div>'
                f'<div style="font-size:1.6rem;font-weight:900;color:#60a5fa;">{row_count:,}</div>'
                f'<div style="font-size:0.76rem;color:#94a3b8;margin-top:2px;">{uniq} unique participants</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        except Exception:
            pass

    if not found_any:
        st.markdown(
            '<div style="background:rgba(96,165,250,0.07);border:1px solid rgba(96,165,250,0.20);'
            'border-radius:10px;padding:14px 18px;font-size:0.82rem;color:#bfdbfe;">'
            'No additional fan tables found. Checked: '
            + ", ".join(f"<code>{t}</code>" for t in other_tables)
            + '. Add new tables and they will appear here automatically.'
            '</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
if callable(render_footer):
    render_footer()
else:
    st.caption("© 2026 Analytics207 · Admin")
