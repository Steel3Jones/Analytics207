from __future__ import annotations

from pathlib import Path
from typing import Optional
import os

import pandas as pd
import streamlit as st

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))
PIR_PATH   = DATA_DIR / "core" / "teams_power_index_v50.parquet"
TEAMS_PATH = DATA_DIR / "core" / "teams_team_season_core_v50.parquet"


def inject_true_strength_ratings_css() -> None:
    st.markdown(
        """
        <style>
        .tsr-table { width: 100%; table-layout: fixed; border-collapse: collapse; }
        .tsr-table th, .tsr-table td { white-space: nowrap; text-overflow: ellipsis; overflow: hidden; text-align: center; vertical-align: middle; }
        .tsr-table th { padding: 0.25rem 0.55rem; font-size: 0.82rem; }
        .tsr-table td { padding: 0.25rem 0.55rem; font-size: 0.82rem; }

        .pill-base { display:inline-flex; align-items:center; justify-content:center; padding:0.05rem 0.55rem; border-radius:999px;
                     font-size:0.72rem; line-height:1.1; font-weight:700; min-width:3.0rem; gap:0.25rem; }

        .heal-pill  { background: rgba(59, 130, 246, 0.10); border: 1px solid rgba(59, 130, 246, 0.70); color: #60a5fa; }
        .model-pill { background: rgba(168, 85, 247, 0.10); border: 1px solid rgba(168, 85, 247, 0.75); color: #a855f7; }

        .delta-pill-up   { background: rgba(34, 197, 94, 0.10); border: 1px solid rgba(34, 197, 94, 0.75); color: #22c55e; }
        .delta-pill-down { background: rgba(239, 68, 68, 0.10); border: 1px solid rgba(239, 68, 68, 0.75); color: #ef4444; }
        .delta-pill-even { background: rgba(148, 163, 184, 0.10); border: 1px solid rgba(148, 163, 184, 0.65); color: #64748b; }

        .tier-pill-1 { background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.8); color: #22c55e; }
        .tier-pill-2 { background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.8); color: #38bdf8; }
        .tier-pill-3 { background: rgba(234, 179, 8, 0.12); border: 1px solid rgba(234, 179, 8, 0.8); color: #eab308; }
        .tier-pill-4 { background: rgba(148, 163, 184, 0.12); border: 1px solid rgba(148, 163, 184, 0.75); color: #64748b; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=3600)
def load_pir() -> pd.DataFrame:
    if not PIR_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(PIR_PATH).copy()
    for col in ["TeamKey", "Gender"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
    return df


@st.cache_data(ttl=3600)
def load_teams() -> pd.DataFrame:
    if not TEAMS_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(TEAMS_PATH).copy()
    for col in ["TeamKey", "Team", "Gender", "Class", "Region"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
    if "Class" in df.columns:
        df["Class"] = (
            df["Class"]
            .str.upper()
            .str.replace("CLASS", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.strip()
        )
    if "Region" in df.columns:
        df["Region"] = df["Region"].str.title()
    for col in ["TI", "NetEff", "MarginPG"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if {"Wins", "Losses"}.issubset(df.columns):
        df["Record"] = (
            df["Wins"].fillna(0).astype(int).astype(str)
            + "-"
            + df["Losses"].fillna(0).astype(int).astype(str)
        )
    elif "Record" not in df.columns:
        df["Record"] = ""
    return df


def format_heal_seed_pill(seed: Optional[float]) -> str:
    if pd.isna(seed):
        return ""
    try:
        v = int(seed)
    except Exception:
        return ""
    return f"<div class='pill-base heal-pill'>{v}</div>"


def format_model_rank_pill(rank: Optional[float]) -> str:
    if pd.isna(rank):
        return ""
    try:
        v = int(rank)
    except Exception:
        return ""
    return f"<div class='pill-base model-pill'>{v}</div>"


def format_delta_pill(delta: Optional[float]) -> str:
    if pd.isna(delta):
        return ""
    try:
        v = int(delta)
    except Exception:
        return ""
    if v > 0:
        return f"<div class='pill-base delta-pill-up'>+{v}</div>"
    if v < 0:
        return f"<div class='pill-base delta-pill-down'>{v}</div>"
    return "<div class='pill-base delta-pill-even'>0</div>"


def build_table(teams: pd.DataFrame, gender: str, cls: str, region: str) -> pd.DataFrame:
    if teams.empty:
        return pd.DataFrame()

    q = teams.copy()

    if "Gender" in q.columns:
        q = q[q["Gender"] == gender.title()]
    if "Class" in q.columns:
        q = q[q["Class"] == cls.upper()]
    if "Region" in q.columns:
        q = q[q["Region"] == region.title()]

    if q.empty:
        return pd.DataFrame()

    if "TI" in q.columns:
        sort_key = "TI"
        sort_asc = False
    elif "Games" in q.columns:
        sort_key = "Games"
        sort_asc = False
    else:
        sort_key = "Wins" if "Wins" in q.columns else q.columns[0]
        sort_asc = False

    q = q.sort_values([sort_key], ascending=[sort_asc]).reset_index(drop=True)
    q["HEAL_SEED_FALLBACK"] = q.index + 1
    q["HEAL_SEED"] = q["HEAL_SEED_FALLBACK"]

    pir_col = "PIR"
    if pir_col in q.columns and pd.to_numeric(q[pir_col], errors="coerce").notna().any():
        q = q.sort_values([pir_col], ascending=[False]).reset_index(drop=True)
        q["MODEL_RANK"] = q.index + 1
    else:
        q["MODEL_RANK"] = pd.NA

    q["DELTA"] = q["HEAL_SEED"] - q["MODEL_RANK"]
    q = q.sort_values(["MODEL_RANK"], ascending=[True]).reset_index(drop=True)

    pir_disp = pd.to_numeric(q.get("PIR", pd.NA), errors="coerce")

    out = pd.DataFrame({
        "MODEL RANK":     q["MODEL_RANK"].astype("Int64"),
        "HEAL SEED":      q["HEAL_SEED"].astype("Int64"),
        "Δ MODEL - HEAL": q["DELTA"],
        "TEAM":           q.get("Team", ""),
        "RECORD":         q.get("Record", ""),
        "PIR":            pir_disp.round(1),
        "HEAL TI":        pd.to_numeric(q.get("TI", pd.NA), errors="coerce").round(2)
                          if "TI" in q.columns else pd.NA,
        "NET EFFICIENCY": pd.to_numeric(q.get("NetEff", pd.NA), errors="coerce").round(2),
    })

    return out


def render_table(df: pd.DataFrame) -> None:
    df2 = df.copy()
    df2["MODEL RANK"]     = df2["MODEL RANK"].apply(format_model_rank_pill)
    df2["HEAL SEED"]      = df2["HEAL SEED"].apply(format_heal_seed_pill)
    df2["Δ MODEL - HEAL"] = df2["Δ MODEL - HEAL"].apply(format_delta_pill)
    html = df2.to_html(escape=False, index=False, classes="tsr-table")
    st.markdown(html, unsafe_allow_html=True)


def main() -> None:
    apply_global_layout_tweaks()
    inject_true_strength_ratings_css()
    st.set_page_config(
        page_title="Power Index Rating – Analytics207.com",
        page_icon="🧠",
        layout="wide",
    )
    render_logo()
    render_page_header(
        title="📊POWER INDEX RATINGS",
        definition="Power Index Rating (PIR) (n.): How 🧠 The model stacks up against the Heal Point system.",
        subtitle=(
            "Compare data-driven strength numbers to official Heal Points to see when the model and the system "
            "agree, and when they send teams on different paths"
        ),
    )

    st.write("")
    st.write("")

    teams = load_teams()
    pir   = load_pir()

    if teams.empty:
        st.warning("Team data not found.")
        render_footer()
        return

    if not pir.empty:
        pir_small = pir[["TeamKey", "Gender", "PowerIndex_Display"]].copy()
        pir_small = pir_small.rename(columns={"PowerIndex_Display": "PIR"})
        teams = teams.merge(pir_small, on=["TeamKey", "Gender"], how="left", suffixes=("", "_PIR"))

    cols = st.columns(3)
    with cols[0]:
        gender = st.selectbox("Gender", ["Boys", "Girls"], index=0)
    with cols[1]:
        cls = st.selectbox("Class", ["A", "B", "C", "D", "S"], index=0)
    with cols[2]:
        region = st.selectbox("Region", ["North", "South"], index=0)

    table = build_table(teams, gender=gender, cls=cls, region=region)

    if table.empty:
        st.warning("No teams found for this selection.")
    else:
        st.caption(f"{gender} • Class {cls} • {region} • PIR ranking with Heal comparison")
        render_table(table)

    render_footer()


if __name__ == "__main__":
    main()
