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

st.set_page_config(
    page_title="📊 The Heal Points",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# AUTH / LOCKING
# ============================================================

SHOW_LOCKS = False


def render_auth_demo_toggle() -> None:
    with st.sidebar:
        st.toggle(
            "Subscriber demo",
            value=bool(st.session_state.get("is_subscriber", False)),
            key="is_subscriber",
            help="Dev toggle: simulates signed-in subscriber access.",
        )


def _is_subscriber() -> bool:
    return bool(st.session_state.get("is_subscriber", False))


def _lock_it() -> bool:
    return bool(SHOW_LOCKS) and (not _is_subscriber())


# ============================================================
# CSS
# ============================================================


def _inject_heal_css() -> None:
    st.markdown("""
<style>
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
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: #f59e0b;
    background: rgba(15,23,42,0.95);
    border-bottom: 1px solid rgba(245,158,11,0.3);
}
.heal-table td {
    padding: 0.28rem 0.55rem;
    font-size: 0.82rem;
    color: #f1f5f9;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.heal-table tr:hover td {
    background: rgba(245,158,11,0.06);
}
.heal-table tr.row-in td  { border-left: 3px solid rgba(34,197,94,0.7); }
.heal-table tr.row-out td { border-left: 3px solid rgba(239,68,68,0.5); }


.pill-base {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.05rem 0.45rem;
    border-radius: 999px;
    font-size: 0.72rem;
    line-height: 1;
    font-weight: 700;
    min-width: 3.0rem;
}
.lock-pill {
    background: rgba(245,158,11,0.12);
    border: 1px solid rgba(245,158,11,0.65);
    color: #fbbf24;
}
.status-pill-in {
    background: rgba(34,197,94,0.15);
    border: 1px solid rgba(34,197,94,0.7);
    color: #4ade80;
}
.status-pill-out {
    background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.7);
    color: #f87171;
}
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
            cut = 10  # fallback only if truly missing
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


def _format_status_pill(val: str) -> str:
    if val == "IN":
        return '<div class="pill-base status-pill-in">IN</div>'
    if val == "OUT":
        return '<div class="pill-base status-pill-out">OUT</div>'
    return ""


def render_heal_table(df: pd.DataFrame) -> None:
    display = df.drop(columns=["_status"], errors="ignore").copy()

    if "IN/OUT" in display.columns:
        display["IN/OUT"] = display["IN/OUT"].apply(_format_status_pill)

    rows_html = ""
    for i, row in display.iterrows():
        status = df.at[i, "_status"] if "_status" in df.columns else ""
        row_cls = "row-in" if status == "IN" else ("row-out" if status == "OUT" else "")
        cells = "".join(f"<td>{v}</td>" for v in row)
        rows_html += f'<tr class="{row_cls}">{cells}</tr>\n'

    headers = "".join(f"<th>{c}</th>" for c in display.columns)
    html = f"""
<table class="heal-table">
  <thead><tr>{headers}</tr></thead>
  <tbody>{rows_html}</tbody>
</table>"""
    st.markdown(html, unsafe_allow_html=True)


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
    render_auth_demo_toggle()
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
        if cut is not None:
            st.caption(f"{gender} • Class {cls} • {region} • Top {cut} = IN • Ranking: {rank_col}")
        else:
            st.caption(f"{gender} • Ranking: {rank_col} • Choose Class + Region to show IN/OUT cut line")

        render_heal_table(table)
        st.write("")
        render_heal_strength_snapshot(table, cut)

    render_footer()


if __name__ == "__main__":
    main()
