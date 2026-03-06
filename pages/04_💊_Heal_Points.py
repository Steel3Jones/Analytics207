from __future__ import annotations


from pathlib import Path
import os


import pandas as pd
import streamlit as st
import plotly.graph_objects as go


from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
)
from auth import login_gate, logout_button, is_subscribed



from sidebar_auth import render_sidebar_auth
render_sidebar_auth()

st.set_page_config(
    page_title="📊 The Heal Points",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)


SHOW_LOCKS = False


# ============================================================
# CSS
# ============================================================


def _inject_heal_css() -> None:
    st.markdown("""
<style>
/* ── FILTER CARD ── */
.heal-filter-card {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.18);
    border-radius: 14px;
    padding: 1rem 1.2rem 0.8rem;
    margin-bottom: 1rem;
}

/* ── HERO STATS ── */
.heal-hero {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 1rem;
}
.heal-hero-stat {
    flex: 1;
    min-width: 110px;
    background: radial-gradient(circle at top left, #142040, #060c1a);
    border: 1px solid rgba(96,165,250,0.22);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    text-align: center;
}
.heal-hero-val {
    font-size: 1.6rem;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.01em;
}
.heal-hero-lbl {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: #64748b;
    margin-top: 3px;
}

/* ── SECTION HEAD ── */
.heal-section-head {
    display: inline-block;
    background: rgba(96,165,250,0.10);
    border: 1px solid rgba(96,165,250,0.22);
    border-radius: 999px;
    padding: 0.20rem 0.85rem;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #93c5fd;
    margin-bottom: 0.6rem;
}

/* ── TABLE WRAPPER ── */
.heal-card {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.18);
    border-radius: 14px;
    padding: 1rem 1rem 0.5rem;
    margin-bottom: 1rem;
    overflow: hidden;
}

/* ── TABLE ── */
.heal-table {
    width: 100%;
    table-layout: fixed;
    border-collapse: collapse;
}
.heal-table th, .heal-table td {
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
    text-align: center;
    vertical-align: middle;
}
.heal-table th {
    padding: 0.30rem 0.55rem;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #f59e0b;
    background: rgba(15,23,42,0.95);
    border-bottom: 2px solid rgba(245,158,11,0.35);
    position: sticky;
    top: 0;
}
.heal-table td {
    padding: 0.30rem 0.55rem;
    font-size: 0.83rem;
    color: #e2e8f0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    transition: background 0.15s;
}
.heal-table tr:hover td {
    background: rgba(245,158,11,0.07);
}
.heal-table tr.row-in td  {
    border-left: 3px solid rgba(34,197,94,0.75);
    background: rgba(34,197,94,0.03);
}
.heal-table tr.row-out td {
    border-left: 3px solid rgba(239,68,68,0.55);
    background: rgba(239,68,68,0.02);
}
.heal-table tr.row-in:hover td  { background: rgba(34,197,94,0.08); }
.heal-table tr.row-out:hover td { background: rgba(239,68,68,0.07); }

/* cut line */
.heal-table tr.cut-line td {
    border-top: 2px solid rgba(245,158,11,0.70);
    border-bottom: none;
    padding: 0;
}
.cut-line-inner {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 10px;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #f59e0b;
    background: rgba(245,158,11,0.06);
}
.cut-line-inner::before, .cut-line-inner::after {
    content: "";
    flex: 1;
    height: 1px;
    background: rgba(245,158,11,0.30);
}

/* seed badge */
.seed-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    font-size: 0.72rem;
    font-weight: 800;
    background: rgba(96,165,250,0.12);
    border: 1px solid rgba(96,165,250,0.30);
    color: #93c5fd;
}
.seed-badge.top3 {
    background: rgba(245,158,11,0.15);
    border-color: rgba(245,158,11,0.55);
    color: #fbbf24;
}

/* team name cell */
.team-name-cell {
    text-align: left !important;
    font-weight: 600;
    color: #f1f5f9;
    padding-left: 8px !important;
}

/* TI value coloring */
.ti-high  { color: #4ade80; font-weight: 700; }
.ti-mid   { color: #facc15; font-weight: 600; }
.ti-low   { color: #f87171; font-weight: 600; }
.ti-base  { color: #cbd5e1; }

/* ── PILLS ── */
.pill-base {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.08rem 0.5rem;
    border-radius: 999px;
    font-size: 0.70rem;
    line-height: 1.2;
    font-weight: 700;
    min-width: 3.2rem;
}
.status-pill-in {
    background: rgba(34,197,94,0.15);
    border: 1px solid rgba(34,197,94,0.65);
    color: #4ade80;
}
.status-pill-out {
    background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.65);
    color: #f87171;
}

/* ── BUBBLE WATCH ── */
.bubble-card {
    background: radial-gradient(circle at top left, #1a1206, #060c1a);
    border: 1px solid rgba(245,158,11,0.30);
    border-radius: 14px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 1rem;
}
.bubble-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.83rem;
}
.bubble-row:last-child { border-bottom: none; }
.bubble-seed  { color: #f59e0b; font-weight: 800; min-width: 28px; }
.bubble-team  { flex: 1; color: #f1f5f9; font-weight: 600; }
.bubble-ti    { color: #94a3b8; font-size: 0.75rem; }
.bubble-delta { font-size: 0.72rem; font-weight: 700; padding: 2px 7px; border-radius: 999px; }
.delta-safe   { background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.4); }
.delta-danger { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.4); }
.delta-bubble { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.4); }
</style>
""", unsafe_allow_html=True)


# ============================================================
# FILTERS
# ============================================================


def render_heal_filters() -> None:
    cols = st.columns(3)
    with cols[0]:
        st.selectbox("Gender", ["Boys", "Girls"], index=0, key="heal_gender")
    with cols[1]:
        st.selectbox("Class", ["All", "A", "B", "C", "D", "S"], index=2, key="heal_class")
    with cols[2]:
        st.selectbox("Region", ["All", "North", "South"], index=1, key="heal_region")


# ============================================================
# DATA
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))
TEAMS_SEASON_PATH = DATA_DIR / "core" / "teams_team_season_core_v50.parquet"


BRACKET_SIZES: dict[tuple[str, str, str], int] = {
    ("Boys",  "A", "North"):  8,
    ("Boys",  "A", "South"): 11,
    ("Boys",  "B", "North"):  9,
    ("Boys",  "B", "South"): 10,
    ("Boys",  "C", "North"): 10,
    ("Boys",  "C", "South"): 10,
    ("Boys",  "D", "North"): 10,
    ("Boys",  "D", "South"):  8,
    ("Boys",  "S", "North"):  8,
    ("Boys",  "S", "South"):  8,
    ("Girls", "A", "North"):  8,
    ("Girls", "A", "South"): 11,
    ("Girls", "B", "North"):  9,
    ("Girls", "B", "South"): 10,
    ("Girls", "C", "North"): 10,
    ("Girls", "C", "South"): 10,
    ("Girls", "D", "North"): 10,
    ("Girls", "D", "South"):  8,
    ("Girls", "S", "North"):  8,
    ("Girls", "S", "South"):  8,
}


@st.cache_data
def load_heal_data() -> pd.DataFrame:
    df = pd.read_parquet(TEAMS_SEASON_PATH).copy()
    for col in ["Team", "Gender", "Class", "Region"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
    if "Class" in df.columns:
        df["Class"] = (df["Class"].astype(str).str.strip().str.upper()
                       .str.replace("CLASS", "", regex=False)
                       .str.replace(" ", "", regex=False).str.strip())
    if "Region" in df.columns:
        df["Region"] = df["Region"].astype(str).str.strip().str.title()
    for col in ["TI", "PI", "ProjectedSeed"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if {"Wins", "Losses"}.issubset(df.columns):
        df["Record"] = (df["Wins"].fillna(0).astype(int).astype(str) + "-" +
                        df["Losses"].fillna(0).astype(int).astype(str))
    elif "Record" in df.columns:
        df["Record"] = df["Record"].astype(str).str.replace(r"-0$", "", regex=True)
    else:
        df["Record"] = ""
    return df


# ============================================================
# BUILD TABLE
# ============================================================


def build_heal_table(heal: pd.DataFrame) -> tuple[pd.DataFrame, int | None, str]:
    gender = st.session_state.get("heal_gender", "Boys")
    cls    = st.session_state.get("heal_class",  "All")
    region = st.session_state.get("heal_region", "All")

    q = heal.copy()
    if "Gender" in q.columns:
        q = q[q["Gender"] == str(gender).strip().title()]
    if q.empty:
        return pd.DataFrame(), None, "TI"

    if cls != "All" and "Class" in q.columns:
        q = q[q["Class"] == cls.upper()]
    if region != "All" and "Region" in q.columns:
        q = q[q["Region"] == region.title()]
    if q.empty:
        return pd.DataFrame(), None, "TI"

    if "TI" in q.columns and "PI" in q.columns:
        q = q.sort_values(["TI", "PI"], ascending=[False, False]).reset_index(drop=True)
        rank_col = "TI"
    elif "TI" in q.columns:
        q = q.sort_values("TI", ascending=False).reset_index(drop=True)
        rank_col = "TI"
    elif "PI" in q.columns:
        q = q.sort_values("PI", ascending=False).reset_index(drop=True)
        rank_col = "PI"
    else:
        q = q.reset_index(drop=True)
        rank_col = "TI"

    q["SEED"] = q.index + 1

    cut = None
    if cls != "All" and region != "All":
        cut = BRACKET_SIZES.get((gender.title(), cls.upper(), region.title()))
        if cut is None:
            cut = 10
        q["IN/OUT"] = q["SEED"].apply(lambda s: "IN" if s <= cut else "OUT")
    else:
        q["IN/OUT"] = ""

    out = pd.DataFrame({
        "SEED":    q["SEED"],
        "TEAM":    q.get("Team", ""),
        "RECORD":  q.get("Record", ""),
        "PI":      q["PI"].round(2) if "PI" in q.columns else pd.Series([None] * len(q)),
        "TI":      q["TI"].round(2) if "TI" in q.columns else pd.Series([None] * len(q)),
        "IN/OUT":  q["IN/OUT"],
        "_status": q["IN/OUT"].astype(str),
    })

    return out, cut, rank_col


# ============================================================
# RENDER TABLE
# ============================================================


def _ti_class(val) -> str:
    try:
        v = float(val)
        if v >= 0.60: return "ti-high"
        if v >= 0.40: return "ti-mid"
        if v >= 0.20: return "ti-low"
        return "ti-base"
    except Exception:
        return "ti-base"


def _format_status_pill(val: str) -> str:
    if val == "IN":
        return '<span class="pill-base status-pill-in">IN</span>'
    if val == "OUT":
        return '<span class="pill-base status-pill-out">OUT</span>'
    return ""


def _seed_badge(seed_val) -> str:
    try:
        s = int(seed_val)
        cls = "seed-badge top3" if s <= 3 else "seed-badge"
        return f'<span class="{cls}">{s}</span>'
    except Exception:
        return str(seed_val)


def render_heal_table(df: pd.DataFrame, cut: int | None = None) -> None:
    cut_inserted = False
    rows_html = ""

    for i, row in df.iterrows():
        status = str(df.at[i, "_status"]) if "_status" in df.columns else ""
        seed   = row.get("SEED", i + 1)

        # Insert cut line divider before first OUT row
        if cut is not None and status == "OUT" and not cut_inserted:
            rows_html += (
                '<tr class="cut-line">'
                '<td colspan="6"><div class="cut-line-inner">— Bracket Cut Line —</div></td>'
                '</tr>\n'
            )
            cut_inserted = True

        row_cls = "row-in" if status == "IN" else ("row-out" if status == "OUT" else "")

        seed_html   = _seed_badge(seed)
        team_html   = f'<span style="font-weight:600;color:#f1f5f9;">{row.get("TEAM","")}</span>'
        record_html = f'<span style="color:#94a3b8;font-size:0.78rem;">{row.get("RECORD","")}</span>'

        pi_raw  = row.get("PI", "")
        ti_raw  = row.get("TI", "")
        try:    pi_html = f'<span style="color:#93c5fd;">{float(pi_raw):.2f}</span>'
        except: pi_html = f'<span style="color:#475569;">—</span>'
        try:    ti_html = f'<span class="{_ti_class(ti_raw)}">{float(ti_raw):.4f}</span>'
        except: ti_html = f'<span style="color:#475569;">—</span>'

        inout_html = _format_status_pill(status)

        rows_html += (
            f'<tr class="{row_cls}">'
            f'<td style="text-align:center;">{seed_html}</td>'
            f'<td style="text-align:left;padding-left:8px;">{team_html}</td>'
            f'<td>{record_html}</td>'
            f'<td>{pi_html}</td>'
            f'<td>{ti_html}</td>'
            f'<td>{inout_html}</td>'
            f'</tr>\n'
        )

    header_labels = ["#", "Team", "Record", "PI", "TI", "Status"]
    headers = "".join(f"<th>{h}</th>" for h in header_labels)

    html = f"""
<div class="heal-card">
<table class="heal-table">
  <thead><tr>{headers}</tr></thead>
  <tbody>{rows_html}</tbody>
</table>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# HERO STATS
# ============================================================


def render_heal_hero(df: pd.DataFrame, cut: int | None) -> None:
    if df.empty:
        return
    total  = len(df)
    n_in   = int((df.get("_status", pd.Series(dtype=str)) == "IN").sum())
    n_out  = total - n_in if cut is not None else 0
    ti_col = pd.to_numeric(df.get("TI", pd.Series(dtype=float)), errors="coerce")
    avg_ti = ti_col.mean()
    top_ti = ti_col.max()

    def _stat(val, lbl, color="#60a5fa"):
        return (
            f'<div class="heal-hero-stat">'
            f'<div class="heal-hero-val" style="color:{color};">{val}</div>'
            f'<div class="heal-hero-lbl">{lbl}</div>'
            f'</div>'
        )

    cards = _stat(str(total), "Teams Tracked", "#93c5fd")
    if cut is not None:
        cards += _stat(str(n_in),  "In The Bracket", "#4ade80")
        cards += _stat(str(n_out), "On The Outside", "#f87171")
    cards += _stat(f"{avg_ti:.4f}" if not pd.isna(avg_ti) else "—", "Avg TI", "#facc15")
    cards += _stat(f"{top_ti:.4f}" if not pd.isna(top_ti) else "—", "Top TI", "#a78bfa")

    st.markdown(f'<div class="heal-hero">{cards}</div>', unsafe_allow_html=True)


# ============================================================
# BUBBLE WATCH
# ============================================================


def render_bubble_watch(df: pd.DataFrame, cut: int | None, window: int = 3) -> None:
    if cut is None or df.empty:
        return

    bubble = df[(df["SEED"] >= cut - window) & (df["SEED"] <= cut + window)].copy()
    if bubble.empty:
        return

    rows = ""
    for _, row in bubble.iterrows():
        seed   = int(row.get("SEED", 0))
        team   = str(row.get("TEAM", ""))
        record = str(row.get("RECORD", ""))
        ti_raw = row.get("TI", "")
        try:    ti_str = f"TI {float(ti_raw):.4f}"
        except: ti_str = ""

        delta  = seed - cut
        if delta <= 0:
            delta_lbl = f"#{seed} · {abs(delta)} spot{'s' if abs(delta)!=1 else ''} safe"
            delta_cls = "delta-safe"
        elif delta == 1:
            delta_lbl = "First out"
            delta_cls = "delta-danger"
        else:
            delta_lbl = f"#{seed} · {delta} out"
            delta_cls = "delta-danger"

        if seed == cut:
            delta_lbl = "Last seed in"
            delta_cls = "delta-bubble"
        if seed == cut + 1:
            delta_lbl = "First out"
            delta_cls = "delta-danger"

        rows += (
            f'<div class="bubble-row">'
            f'<span class="bubble-seed">#{seed}</span>'
            f'<span class="bubble-team">{team} <span style="color:#475569;font-weight:400;font-size:0.75rem;">{record}</span></span>'
            f'<span class="bubble-ti">{ti_str}</span>'
            f'<span class="bubble-delta {delta_cls}">{delta_lbl}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="heal-section-head">🫧 Bracket Bubble Watch</div>'
        f'<div class="bubble-card">{rows}</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# CHART
# ============================================================


def render_heal_strength_snapshot(heal_table: pd.DataFrame, cut: int | None) -> None:
    if heal_table.empty:
        st.caption("No teams for this slice yet.")
        return
    if "TI" not in heal_table.columns:
        st.caption("No TI values available.")
        return

    df = heal_table.copy().sort_values("TI", ascending=True)
    df["_status"] = df.get("_status", df.get("IN/OUT", "")).fillna("").astype(str)

    colors = df["_status"].map({
        "IN":  "#4ade80",
        "OUT": "#f87171",
        "":   "#60a5fa",
    }).fillna("#60a5fa").tolist()

    border_colors = df["_status"].map({
        "IN":  "rgba(74,222,128,0.6)",
        "OUT": "rgba(248,113,113,0.5)",
        "":   "rgba(96,165,250,0.4)",
    }).fillna("rgba(96,165,250,0.4)").tolist()

    ti_vals  = pd.to_numeric(df["TI"], errors="coerce").fillna(0).tolist()
    teams    = df["TEAM"].astype(str).tolist()
    seeds    = df["SEED"].astype(str).tolist()
    records  = df["RECORD"].astype(str).tolist()
    statuses = df["_status"].tolist()

    hover = [
        f"<b>#{s} {t}</b><br>TI: {ti:.4f}<br>Record: {r}<br>Status: {st_}"
        for s, t, ti, r, st_ in zip(seeds, teams, ti_vals, records, statuses)
    ]

    fig = go.Figure()

    if cut is not None and cut <= len(df):
        sorted_df = heal_table.sort_values("TI", ascending=False).reset_index(drop=True)
        if cut <= len(sorted_df) and cut > 0:
            cut_ti = float(sorted_df.at[cut - 1, "TI"]) if pd.notna(sorted_df.at[cut - 1, "TI"]) else None
            if cut_ti is not None:
                fig.add_vline(
                    x=cut_ti,
                    line_color="rgba(245,158,11,0.7)",
                    line_width=2,
                    line_dash="dash",
                    annotation_text="BRACKET CUT",
                    annotation_font_color="#f59e0b",
                    annotation_font_size=10,
                    annotation_position="top right",
                )

    fig.add_trace(go.Bar(
        x=ti_vals,
        y=teams,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(color=border_colors, width=1.2),
            opacity=0.88,
        ),
        text=[f"  #{s}  {ti:.4f}" for s, ti in zip(seeds, ti_vals)],
        textposition="inside",
        textfont=dict(color="#0f172a", size=10, family="ui-sans-serif"),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover,
    ))

    fig.add_trace(go.Scatter(
        x=ti_vals,
        y=teams,
        mode="text",
        text=[f" {ti:.4f}" for ti in ti_vals],
        textposition="middle right",
        textfont=dict(color="rgba(226,232,240,0.7)", size=9),
        hoverinfo="skip",
        showlegend=False,
    ))

    n_teams = len(df)
    bar_h   = max(22, min(36, 600 // max(n_teams, 1)))
    height  = max(380, n_teams * bar_h + 80)

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=60, t=40, b=30),
        plot_bgcolor="rgba(9,14,28,1)",
        paper_bgcolor="rgba(9,14,28,1)",
        font=dict(color="#e2e8f0", size=11, family="ui-sans-serif, system-ui"),
        xaxis=dict(
            title="Tournament Index (TI)",
            title_font=dict(color="#f59e0b", size=11),
            tickfont=dict(color="rgba(148,163,184,0.8)", size=10),
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=False,
            showline=False,
        ),
        yaxis=dict(
            tickfont=dict(color="#e2e8f0", size=11),
            gridcolor="rgba(255,255,255,0.03)",
            showgrid=False,
        ),
        bargap=0.28,
        showlegend=False,
        title=dict(
            text="<b>Tournament Index Strength Snapshot</b>  "
                 "<span style='font-size:11px;color:#9ca3af;'>— sorted lowest to highest, cut line in gold</span>",
            font=dict(color="#f1f5f9", size=13),
            x=0,
            xanchor="left",
            pad=dict(b=10),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    apply_global_layout_tweaks()
    _inject_heal_css()

    user = login_gate(required=False)
    logout_button()

    render_logo()
    render_page_header(
        title="📋 Maine Heal Points",
        definition="Maine Heal Points (n.): The official standings that decide who's in and where they're seeded.",
        subtitle="Track records, opponent value, and tournament index to see how the Heal Point formula ranks every team on the road to playoffs.",
    )
    st.write("")
    st.write("")
    render_heal_filters()

    heal = load_heal_data()
    table, cut, rank_col = build_heal_table(heal)

    gender = st.session_state.get("heal_gender", "Boys")
    cls    = st.session_state.get("heal_class",  "All")
    region = st.session_state.get("heal_region", "All")

    if table.empty:
        st.warning("No teams found for this selection.")
    else:
        # Hero stats bar
        render_heal_hero(table, cut)

        if cut is not None:
            st.caption(f"{gender} · Class {cls} · {region} · Top {cut} qualify · Ranked by {rank_col}")
        else:
            st.caption(f"{gender} · Ranked by {rank_col} · Select Class + Region to see IN/OUT bracket cut")

        # Standings table with cut line divider
        st.markdown('<div class="heal-section-head">📋 Heal Point Standings</div>', unsafe_allow_html=True)
        render_heal_table(table, cut)

        # Bubble watch (only when a specific bracket is selected)
        if cut is not None:
            st.write("")
            render_bubble_watch(table, cut)

        st.write("")
        st.markdown('<div class="heal-section-head">📊 Tournament Index Snapshot</div>', unsafe_allow_html=True)
        render_heal_strength_snapshot(table, cut)

    render_footer()


if __name__ == "__main__":
    main()
