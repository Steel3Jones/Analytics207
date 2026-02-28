# 08__Bracketology.py – MPA Tournament Central
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import re
import random
import os

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from layout import apply_global_layout_tweaks, render_logo, render_page_header, render_footer

PROJECT_ROOT   = Path(__file__).resolve().parent.parent
DATA_DIR       = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))
TEAMS_PATH     = DATA_DIR / "core" / "teams_team_season_core_v50.parquet"
ANALYTICS_PATH = DATA_DIR / "core" / "teams_team_season_analytics_v50.parquet"
PIR_PATH       = DATA_DIR / "core" / "teams_power_index_v50.parquet"
BRACKET_PATH   = DATA_DIR / "tournament" / "2026" / "tournament_2026.parquet"

st.set_page_config(page_title="Bracketology | MPA", page_icon="🏆", layout="wide")
apply_global_layout_tweaks()

CARD_H  = 82
GAP     = 8
SLOT    = CARD_H + GAP
COL_W   = 215
COL_GAP = 36

QF_SLOT = {1: 0, 4: 1, 3: 2, 2: 3}
SF_SLOT = {1: 0, 3: 1}

SITE_MAP = {
    ("B","North"): "Cross Insurance Center, Bangor",
    ("C","North"): "Cross Insurance Center, Bangor",
    ("D","North"): "Cross Insurance Center, Bangor",
    ("S","North"): "Cross Insurance Center, Bangor",
    ("A","North"): "Augusta Civic Center",
    ("C","South"): "Augusta Civic Center",
    ("D","South"): "Augusta Civic Center",
    ("S","South"): "Augusta Civic Center",
    ("A","South"): "Portland Expo",
    ("B","South"): "Portland Expo",
}

FIELD_SIZES: Dict[Tuple[str, str], int] = {
    ("A", "North"):  8,
    ("A", "South"): 11,
    ("B", "North"):  9,
    ("B", "South"): 10,
    ("C", "North"): 10,
    ("C", "South"): 10,
    ("D", "North"): 10,
    ("D", "South"):  8,
    ("S", "North"):  8,
    ("S", "South"):  8,
}

# ─────────────────────────────────────────────
# NAME NORMALIZATION — matches scraper logic
# ─────────────────────────────────────────────

def normalize_name(name: str) -> str:
    n = name.lower().strip()
    n = n.replace("-", " ").replace(".", "").replace("/", " ")
    for suffix in [" high school", " hs", " regional", " community", " academy",
                   " area", " school", " senior", " sr", " consolidated",
                   " consolidate", " district", " memorial", " pchs"]:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    n = re.sub(r"[^a-z0-9 ]", "", n).strip()
    n = re.sub(r"\bmt\b", "mount", n)
    return n

def _fuzzy_find_team(df_teams: pd.DataFrame, team_name: str,
                     gender: str, cls: str) -> pd.Series | None:
    if df_teams is None or df_teams.empty:
        return None
    norm = normalize_name(team_name)
    sub = df_teams[(df_teams["Gender"] == gender) & (df_teams["Class"] == cls)].copy()
    if sub.empty:
        return None
    sub["_norm"] = sub["Team"].apply(normalize_name)
    match = sub[sub["_norm"] == norm]
    if not match.empty:
        return match.iloc[0]
    return None

# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────

@st.cache_data(ttl=900)
def load_bracket() -> pd.DataFrame:
    if not BRACKET_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(BRACKET_PATH)
    for c in ["Gender","Class","Region","Round","Team1","Team2","Winner"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
    if "Class" in df.columns:
        df["Class"] = (df["Class"].str.upper()
                       .str.replace("CLASS","",regex=False)
                       .str.replace(" ","",regex=False).str.strip())
    if "Region" in df.columns:
        df["Region"] = df["Region"].str.title()
    for c in ["Seed1","Seed2","Score1","Score2","PredWinProb1","PredWinProb2"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    s1_ok = df["Score1"].notna() if "Score1" in df.columns else pd.Series(False, index=df.index)
    s2_ok = df["Score2"].notna() if "Score2" in df.columns else pd.Series(False, index=df.index)
    df["Done"] = s1_ok & s2_ok
    return df

@st.cache_data(ttl=3600)
def load_teams() -> pd.DataFrame:
    src = ANALYTICS_PATH if ANALYTICS_PATH.exists() else TEAMS_PATH
    if not src.exists():
        return pd.DataFrame()

    df = pd.read_parquet(src)
    for c in ["TeamKey","Team","Gender","Class","Region"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
    if "Class" in df.columns:
        df["Class"] = (df["Class"].str.upper()
                       .str.replace("CLASS","",regex=False)
                       .str.replace(" ","",regex=False).str.strip())
    if "Region" in df.columns:
        df["Region"] = df["Region"].str.title()

    if PIR_PATH.exists():
        pir = pd.read_parquet(PIR_PATH).copy()
        for c in ["TeamKey","Gender"]:
            if c in pir.columns:
                pir[c] = pir[c].astype(str).str.strip()
        if "Gender" in pir.columns:
            pir["Gender"] = pir["Gender"].str.title()
        keep_pir = ["TeamKey","Gender","PowerIndex_Ridge","OffRating_Ridge","DefRating_Ridge"]
        keep_pir = [c for c in keep_pir if c in pir.columns]
        df = df.merge(pir[keep_pir], on=["TeamKey","Gender"], how="left")

    for c in ["TI","Wins","Losses","WinPct","NetEff","PPG","OPPG",
              "PowerIndex_Ridge","OffRating_Ridge","DefRating_Ridge",
              "SOS_EWP","RPI","LuckZ","Last10MarginPG","ClutchCloseGameWinPct"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if {"Wins","Losses"}.issubset(df.columns) and "Record" not in df.columns:
        df["Record"] = (df["Wins"].fillna(0).astype(int).astype(str) + "-" +
                        df["Losses"].fillna(0).astype(int).astype(str))
    return df

def get_round_games(df: pd.DataFrame, gender: str, cls: str,
                    region: str, rnd: str) -> List[dict]:
    sub = df[
        (df["Gender"]==gender) & (df["Class"]==cls) &
        (df["Region"]==region) & (df["Round"]==rnd)
    ].copy()
    if sub.empty:
        return []

    result = []
    for _, r in sub.iterrows():
        result.append(dict(
            seed1  = int(r["Seed1"])  if pd.notna(r.get("Seed1"))  else None,
            team1  = str(r["Team1"]),
            score1 = int(r["Score1"]) if pd.notna(r.get("Score1")) else None,
            seed2  = int(r["Seed2"])  if pd.notna(r.get("Seed2"))  else None,
            team2  = str(r["Team2"]),
            score2 = int(r["Score2"]) if pd.notna(r.get("Score2")) else None,
            prob1  = float(r["PredWinProb1"]) if pd.notna(r.get("PredWinProb1")) else 0.5,
            prob2  = float(r["PredWinProb2"]) if pd.notna(r.get("PredWinProb2")) else 0.5,
            done   = pd.notna(r.get("Score1")) and pd.notna(r.get("Score2")),
        ))

    slot_map = QF_SLOT if rnd == "QF" else (SF_SLOT if rnd == "SF" else {})
    return sorted(result,
                  key=lambda x: slot_map.get(x["seed1"] or 99, x["seed1"] or 99))

# ─────────────────────────────────────────────
# WINNER ADVANCEMENT — auto-advance at render time
# ─────────────────────────────────────────────

def _get_winner(row) -> Tuple:
    s1 = pd.to_numeric(row.get("Score1"), errors="coerce")
    s2 = pd.to_numeric(row.get("Score2"), errors="coerce")
    if pd.isna(s1) or pd.isna(s2):
        return None, None
    if s1 > s2:
        return str(row["Team1"]).strip(), row.get("Seed1")
    else:
        return str(row["Team2"]).strip(), row.get("Seed2")

def resolve_winners(df: pd.DataFrame, gender: str, cls: str, region: str) -> pd.DataFrame:
    df = df.copy()
    sub = (df["Gender"] == gender) & (df["Class"] == cls) & (df["Region"] == region)
    bracket = df[sub].copy()
    if bracket.empty:
        return df

    round_order = ["Prelim", "QF", "SF", "Final"]

    for rnd_idx in range(len(round_order) - 1):
        current_rnd = round_order[rnd_idx]
        next_rnd = round_order[rnd_idx + 1]

        current_games = bracket[bracket["Round"] == current_rnd].sort_values("Seed1", na_position="last")
        next_mask = sub & (df["Round"] == next_rnd)
        next_indices = df[next_mask].index.tolist()

        if current_games.empty or not next_indices:
            continue

        winners = []
        for _, g in current_games.iterrows():
            w_team, w_seed = _get_winner(g)
            if w_team:
                winners.append({"team": w_team, "seed": w_seed})

        if not winners:
            continue

        winner_idx = 0
        for game_idx in next_indices:
            t1 = str(df.at[game_idx, "Team1"]).strip() if pd.notna(df.at[game_idx, "Team1"]) else ""
            if (t1 == "" or t1.lower() == "tbd" or t1 == "nan") and winner_idx < len(winners):
                df.at[game_idx, "Team1"] = winners[winner_idx]["team"]
                if pd.notna(winners[winner_idx]["seed"]):
                    df.at[game_idx, "Seed1"] = winners[winner_idx]["seed"]
                winner_idx += 1

            t2 = str(df.at[game_idx, "Team2"]).strip() if pd.notna(df.at[game_idx, "Team2"]) else ""
            if (t2 == "" or t2.lower() == "tbd" or t2 == "nan") and winner_idx < len(winners):
                df.at[game_idx, "Team2"] = winners[winner_idx]["team"]
                if pd.notna(winners[winner_idx]["seed"]):
                    df.at[game_idx, "Seed2"] = winners[winner_idx]["seed"]
                winner_idx += 1

    return df

def build_state_game(df: pd.DataFrame, gender: str, cls: str,
                     df_teams: pd.DataFrame = None) -> dict | None:
    """Build State Final game dict dynamically from Regional Final winners."""
    north_champ, north_seed = None, None
    south_champ, south_seed = None, None

    n_final = df[
        (df["Gender"] == gender) & (df["Class"] == cls) &
        (df["Region"] == "North") & (df["Round"] == "Final")
    ]
    for _, g in n_final.iterrows():
        w, s = _get_winner(g)
        if w:
            north_champ, north_seed = w, s

    s_final = df[
        (df["Gender"] == gender) & (df["Class"] == cls) &
        (df["Region"] == "South") & (df["Round"] == "Final")
    ]
    for _, g in s_final.iterrows():
        w, s = _get_winner(g)
        if w:
            south_champ, south_seed = w, s

    if not north_champ and not south_champ:
        return None

    t1 = north_champ or "TBD"
    t2 = south_champ or "TBD"
    sd1 = int(north_seed) if pd.notna(north_seed) else None
    sd2 = int(south_seed) if pd.notna(south_seed) else None

    prob1, prob2 = 0.5, 0.5
    if df_teams is not None and north_champ and south_champ:
        a_row = _fuzzy_find_team(df_teams, north_champ, gender, cls)
        b_row = _fuzzy_find_team(df_teams, south_champ, gender, cls)
        if a_row is not None and b_row is not None:
            m = matchup_pred(a_row, b_row)
            prob1 = m["prob_a"]
            prob2 = 1.0 - prob1

    # Check if a State row exists with scores (future-proof)
    state_rows = df[
        (df["Gender"] == gender) & (df["Class"] == cls) & (df["Round"] == "State")
    ]
    sc1, sc2, done = None, None, False
    if not state_rows.empty:
        row = state_rows.iloc[0]
        s1v = pd.to_numeric(row.get("Score1"), errors="coerce")
        s2v = pd.to_numeric(row.get("Score2"), errors="coerce")
        if pd.notna(s1v) and pd.notna(s2v):
            sc1, sc2, done = int(s1v), int(s2v), True

    return dict(
        seed1=sd1, team1=t1, score1=sc1,
        seed2=sd2, team2=t2, score2=sc2,
        prob1=prob1, prob2=prob2, done=done,
    )

# ─────────────────────────────────────────────
# MATCHUP MODEL — PowerIndex_Ridge backbone
# ─────────────────────────────────────────────

def matchup_pred(a: pd.Series, b: pd.Series) -> Dict:
    pir_a = pd.to_numeric(a.get("PowerIndex_Ridge", np.nan), errors="coerce")
    pir_b = pd.to_numeric(b.get("PowerIndex_Ridge", np.nan), errors="coerce")

    if pd.notna(pir_a) and pd.notna(pir_b):
        margin = float(pir_a) - float(pir_b)
        prob_a = float(1.0 / (1.0 + 10.0 ** (-(margin * 20.0) / 400.0)))
    else:
        ne_a = pd.to_numeric(a.get("NetEff", np.nan), errors="coerce")
        ne_b = pd.to_numeric(b.get("NetEff", np.nan), errors="coerce")
        if pd.isna(ne_a) or pd.isna(ne_b):
            return dict(margin=0.0, prob_a=0.5, score_a=np.nan, score_b=np.nan)
        margin = float(ne_a) - float(ne_b)
        prob_a = float(1.0 / (1.0 + 10.0 ** (-(margin * 20.0) / 400.0)))

    ppg_a  = pd.to_numeric(a.get("PPG",  np.nan), errors="coerce")
    oppg_a = pd.to_numeric(a.get("OPPG", np.nan), errors="coerce")
    ppg_b  = pd.to_numeric(b.get("PPG",  np.nan), errors="coerce")
    oppg_b = pd.to_numeric(b.get("OPPG", np.nan), errors="coerce")
    if all(pd.notna(v) for v in [ppg_a, oppg_a, ppg_b, oppg_b]):
        total   = float((ppg_a + oppg_a + ppg_b + oppg_b) / 2.0)
        score_a = float((total + margin) / 2.0)
        score_b = float(total - score_a)
    else:
        score_a = score_b = np.nan

    return dict(margin=margin, prob_a=prob_a, score_a=score_a, score_b=score_b)

# ─────────────────────────────────────────────
# HTML CARD BUILDERS
# ─────────────────────────────────────────────

def card_html(g: dict) -> str:
    s1, t1, sc1 = g["seed1"], g["team1"], g["score1"]
    s2, t2, sc2 = g["seed2"], g["team2"], g["score2"]

    if g["done"] and sc1 is not None and sc2 is not None:
        win1 = sc1 > sc2
        bg1  = "rgba(34,197,94,0.13)"  if win1     else "transparent"
        bg2  = "rgba(34,197,94,0.13)"  if not win1 else "transparent"
        c1   = "#4ade80" if win1     else "rgba(203,213,225,0.55)"
        c2   = "#4ade80" if not win1 else "rgba(203,213,225,0.55)"
        r1   = '<span style="color:{};font-size:14px;font-weight:900;margin-left:auto">{}</span>'.format(c1, sc1)
        r2   = '<span style="color:{};font-size:14px;font-weight:900;margin-left:auto">{}</span>'.format(c2, sc2)
        hdr  = '<span style="color:#22c55e;font-size:9px;font-weight:800;letter-spacing:.1em">FINAL</span>'
    else:
        p1, p2 = g["prob1"], g["prob2"]
        fav1 = p1 >= p2
        bg1  = "rgba(245,158,11,0.09)" if fav1     else "transparent"
        bg2  = "rgba(245,158,11,0.09)" if not fav1 else "transparent"
        r1   = '<span style="color:rgba(245,158,11,0.8);font-size:10px;font-weight:800;margin-left:auto">{:.0f}%</span>'.format(p1*100)
        r2   = '<span style="color:rgba(245,158,11,0.8);font-size:10px;font-weight:800;margin-left:auto">{:.0f}%</span>'.format(p2*100)
        hdr  = '<span style="color:rgba(148,163,184,0.38);font-size:9px;font-weight:700;letter-spacing:.1em">UPCOMING</span>'

    rs = "display:flex;align-items:center;gap:5px;padding:3px 5px;border-radius:4px"
    ss = "color:rgba(148,163,184,0.5);font-size:10px;font-weight:700;min-width:13px"
    ns = "color:#f1f5f9;font-size:11px;font-weight:700;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:135px"

    return (
        '<div style="background:#0d1626;border:1px solid rgba(255,255,255,0.09);border-radius:8px;'
        'padding:6px 8px;height:{}px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center">'.format(CARD_H) +
        '<div style="margin-bottom:4px">{}</div>'.format(hdr) +
        '<div style="{};background:{};margin-bottom:2px">'.format(rs, bg1) +
        '<span style="{}">{}</span>'.format(ss, s1 or "?") +
        '<span style="{}">{}</span>'.format(ns, t1 or "TBD") + r1 + '</div>' +
        '<div style="{};background:{}">'.format(rs, bg2) +
        '<span style="{}">{}</span>'.format(ss, s2 or "?") +
        '<span style="{}">{}</span>'.format(ns, t2 or "TBD") + r2 + '</div></div>'
    )

def tbd_card(lbl1: str, lbl2: str, header: str = "UPCOMING") -> str:
    ns = "color:rgba(148,163,184,0.35);font-size:11px;font-style:italic"
    rs = "display:flex;align-items:center;gap:5px;padding:3px 5px"
    hc = "rgba(245,158,11,0.7)" if "STATE" in header or "FINAL" in header else "rgba(148,163,184,0.38)"
    return (
        '<div style="background:#0d1626;border:1px solid rgba(255,255,255,0.09);border-radius:8px;'
        'padding:6px 8px;height:{}px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center">'.format(CARD_H) +
        '<div style="margin-bottom:4px"><span style="color:{};font-size:9px;font-weight:800;letter-spacing:.1em">{}</span></div>'.format(hc, header) +
        '<div style="{};margin-bottom:2px"><span style="{}">{}</span></div>'.format(rs, ns, lbl1) +
        '<div style="{}"><span style="{}">{}</span></div></div>'.format(rs, ns, lbl2)
    )

def champ_card(team: str, seed: int | None) -> str:
    sd = str(seed) if seed else "?"
    return (
        '<div style="background:linear-gradient(135deg,rgba(245,158,11,0.18),rgba(234,179,8,0.08));'
        'border:2px solid rgba(245,158,11,0.6);border-radius:10px;'
        'padding:10px 12px;height:{}px;box-sizing:border-box;'
        'display:flex;flex-direction:column;align-items:center;justify-content:center;'
        'text-align:center">'.format(CARD_H) +
        '<div style="font-size:18px;margin-bottom:2px">🏆</div>' +
        '<div style="color:#fde68a;font-size:9px;font-weight:900;letter-spacing:.18em;'
        'text-transform:uppercase;margin-bottom:3px">GOLD BALL CHAMPION</div>' +
        '<div style="color:#f1f5f9;font-size:13px;font-weight:900;white-space:nowrap;'
        'overflow:hidden;text-overflow:ellipsis;max-width:190px">'
        '<span style="color:rgba(245,158,11,0.7);font-size:10px;font-weight:700;'
        'margin-right:4px">{}</span>{}</div></div>'.format(sd, team)
    )

# ─────────────────────────────────────────────
# BRACKET POSITION MATH
# ─────────────────────────────────────────────

def qf_top(i: int) -> int:
    return i * SLOT

def sf_top(i: int) -> int:
    return SLOT // 2 + i * 2 * SLOT

def fin_top(i: int) -> int:
    return SLOT // 2 + SLOT + i * 4 * SLOT

def prelim_top(n_qf: int, i: int, n_prelims: int) -> int:
    return (n_qf + i) * SLOT

# ─────────────────────────────────────────────
# REGION BRACKET HTML
# ─────────────────────────────────────────────

def build_region_html(prelims: List[dict], qf: List[dict],
                      sf: List[dict], final: List[dict],
                      has_prelim_col: bool) -> str:
    html   = ""
    col_x  = 0
    n_qf_games = len(qf)

    for i, g in enumerate(prelims):
        top = (n_qf_games + i) * SLOT
        html += '<div style="position:absolute;left:{}px;top:{}px;width:{}px">{}</div>'.format(
            col_x, top, COL_W, card_html(g))

    for i, g in enumerate(qf):
        html += '<div style="position:absolute;left:{}px;top:{}px;width:{}px">{}</div>'.format(
            col_x, qf_top(i), COL_W, card_html(g))
    col_x += COL_W + COL_GAP

    if sf:
        for i, g in enumerate(sf):
            html += '<div style="position:absolute;left:{}px;top:{}px;width:{}px">{}</div>'.format(
                col_x, sf_top(i), COL_W, card_html(g))
    else:
        html += '<div style="position:absolute;left:{}px;top:{}px;width:{}px">{}</div>'.format(
            col_x, sf_top(0), COL_W, tbd_card("QF Winner 1", "QF Winner 2"))
        html += '<div style="position:absolute;left:{}px;top:{}px;width:{}px">{}</div>'.format(
            col_x, sf_top(1), COL_W, tbd_card("QF Winner 3", "QF Winner 4"))
    col_x += COL_W + COL_GAP

    if final:
        for i, g in enumerate(final):
            html += '<div style="position:absolute;left:{}px;top:{}px;width:{}px">{}</div>'.format(
                col_x, fin_top(i), COL_W, card_html(g))
    else:
        html += '<div style="position:absolute;left:{}px;top:{}px;width:{}px">{}</div>'.format(
            col_x, fin_top(0), COL_W, tbd_card("SF Winner 1", "SF Winner 2", "REGIONAL FINAL"))

    return html

# ─────────────────────────────────────────────
# FULL BRACKET HTML
# ─────────────────────────────────────────────

def build_full_bracket_html(gender: str, cls: str, df: pd.DataFrame,
                            df_teams: pd.DataFrame = None) -> Tuple[str, int]:
    # Auto-advance winners through regional rounds
    df = resolve_winners(df, gender, cls, "North")
    df = resolve_winners(df, gender, cls, "South")

    def gr(region, rnd):
        return get_round_games(df, gender, cls, region, rnd)

    n_p  = gr("North","Prelim");  n_qf = gr("North","QF")
    n_sf = gr("North","SF");      n_fn = gr("North","Final")
    s_p  = gr("South","Prelim");  s_qf = gr("South","QF")
    s_sf = gr("South","SF");      s_fn = gr("South","Final")

    # Build State Final dynamically from Regional Final winners
    state_game = build_state_game(df, gender, cls, df_teams)

    prelim_html = ""
    prelim_h    = 0
    all_prelims = (n_p or []) + (s_p or [])

    if all_prelims:
        prelim_label_html = (
            '<div style="color:rgba(245,158,11,0.85);font-size:10px;font-weight:800;'
            'letter-spacing:.15em;text-transform:uppercase;margin-bottom:10px">'
            'Preliminary Round</div>'
        )
        cards_html = '<div style="display:flex;flex-wrap:wrap;gap:{}px">'.format(GAP)
        for g in all_prelims:
            cards_html += '<div style="width:{}px">{}</div>'.format(COL_W, card_html(g))
        cards_html += '</div>'
        prelim_html = prelim_label_html + cards_html
        rows    = (len(all_prelims) + 3) // 4
        prelim_h = rows * (CARD_H + GAP) + 36

    n_round_cols = 3
    state_col_x  = n_round_cols * (COL_W + COL_GAP)
    champ_col_x  = state_col_x + COL_W + COL_GAP
    n_qf_h       = max(len(n_qf), 4) * SLOT
    s_qf_h       = max(len(s_qf), 4) * SLOT
    region_sep   = 40

    n_fin_mid = fin_top(0) + CARD_H // 2
    s_fin_mid = n_qf_h + region_sep + fin_top(0) + CARD_H // 2
    state_y   = (n_fin_mid + s_fin_mid) // 2 - CARD_H // 2

    # Column headers
    has_champ = state_game and state_game["done"]
    hdrs = ["Quarterfinal", "Semifinal", "Regional Final", "State Final"]
    if has_champ:
        hdrs.append("Champion")
    hdr_html = ""
    for i, lbl in enumerate(hdrs):
        x = i * (COL_W + COL_GAP)
        hdr_html += (
            '<div style="position:absolute;left:{}px;width:{}px;'
            'color:rgba(245,158,11,0.85);font-size:10px;font-weight:800;'
            'letter-spacing:.15em;text-transform:uppercase">{}</div>'
        ).format(x, COL_W, lbl)

    lbl_sty    = ("color:rgba(148,163,184,0.32);font-size:9px;font-weight:800;"
                  "letter-spacing:.12em;text-transform:uppercase")
    north_html = build_region_html([], n_qf, n_sf, n_fn, False)
    south_html = build_region_html([], s_qf, s_sf, s_fn, False)

    # State Final card
    if state_game:
        sc = card_html(state_game)
    else:
        sc = tbd_card("North Champion", "South Champion", "STATE FINAL")

    # Champion card
    champ_html = ""
    if state_game and state_game["done"]:
        if state_game["score1"] is not None and state_game["score2"] is not None:
            if state_game["score1"] > state_game["score2"]:
                champ_team = state_game["team1"]
                champ_seed = state_game["seed1"]
            else:
                champ_team = state_game["team2"]
                champ_seed = state_game["seed2"]
            champ_html = '<div style="position:absolute;top:{}px;left:{}px;width:{}px">{}</div>'.format(
                state_y, champ_col_x, COL_W, champ_card(champ_team, champ_seed))

    hdr_h      = 26
    lbl_h      = 16
    north_top  = hdr_h + lbl_h
    south_top  = north_top + n_qf_h + region_sep
    total_w    = (champ_col_x + COL_W + 20) if has_champ else (state_col_x + COL_W + 20)
    bracket_h  = south_top + s_qf_h + 40

    bracket_html = (
        '<div style="position:relative;height:{}px;width:{}px">'.format(bracket_h, total_w) +
        '<div style="position:absolute;top:0;left:0;height:{}px;width:{}px">'.format(hdr_h, total_w) +
        '<div style="position:relative;height:{}px">{}</div></div>'.format(hdr_h, hdr_html) +
        '<div style="position:absolute;top:{}px;left:0;{}">NORTH</div>'.format(hdr_h, lbl_sty) +
        '<div style="position:absolute;top:{}px;left:0;width:{}px">'.format(north_top, total_w) +
        '<div style="position:relative;height:{}px">{}</div></div>'.format(n_qf_h + 10, north_html) +
        '<div style="position:absolute;top:{}px;left:0;{}">SOUTH</div>'.format(south_top - lbl_h, lbl_sty) +
        '<div style="position:absolute;top:{}px;left:0;width:{}px">'.format(south_top, total_w) +
        '<div style="position:relative;height:{}px">{}</div></div>'.format(s_qf_h + 10, south_html) +
        '<div style="position:absolute;top:{}px;left:{}px;width:{}px">{}</div>'.format(
            north_top + state_y, state_col_x, COL_W, sc) +
        champ_html +
        '</div>'
    )

    css = (
        '<style>*{box-sizing:border-box;margin:0;padding:0}'
        'body{background:#060d1a;font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;'
        'padding:12px 16px;overflow-x:auto;overflow-y:visible}</style>'
    )

    total_h = prelim_h + bracket_h + 20
    html    = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"/>' + css + '</head><body>' +
        ('<div style="margin-bottom:20px">' + prelim_html + '</div>' if prelim_html else '') +
        bracket_html + '</body></html>'
    )

    return html, total_h

# ─────────────────────────────────────────────
# MONTE CARLO — PowerIndex_Ridge backbone
# ─────────────────────────────────────────────

def run_live_odds(gender: str, cls: str, region: str,
                  df_bracket: pd.DataFrame,
                  df_teams: pd.DataFrame) -> Dict[str, float]:
    bracket_sub = df_bracket[
        (df_bracket["Gender"] == gender) &
        (df_bracket["Class"]  == cls)    &
        (df_bracket["Region"] == region)
    ].copy()

    if bracket_sub.empty:
        return {}

    eliminated = set()
    for _, g in bracket_sub[bracket_sub["Done"] == True].iterrows():
        s1 = pd.to_numeric(g.get("Score1"), errors="coerce")
        s2 = pd.to_numeric(g.get("Score2"), errors="coerce")
        if pd.notna(s1) and pd.notna(s2):
            eliminated.add(str(g["Team2"] if s1 > s2 else g["Team1"]).strip())

    all_teams = set()
    for _, g in bracket_sub.iterrows():
        all_teams.update([str(g["Team1"]).strip(), str(g["Team2"]).strip()])
    alive = all_teams - eliminated

    if not alive:
        return {}
    if len(alive) == 1:
        return {list(alive)[0]: 1.0}

    stats_sub = df_teams[
        (df_teams["Gender"] == gender) &
        (df_teams["Class"]  == cls)    &
        (df_teams["Region"] == region)
    ].copy()

    alive_rows = []
    for team_name in alive:
        match = stats_sub[stats_sub["Team"] == team_name]
        if match.empty:
            row = _fuzzy_find_team(df_teams, team_name, gender, cls)
            if row is not None:
                alive_rows.append(row)
            else:
                alive_rows.append(pd.Series({
                    "Team": team_name,
                    "PowerIndex_Ridge": np.nan,
                    "NetEff": np.nan,
                    "PPG": np.nan,
                    "OPPG": np.nan,
                    "TI": 0.0,
                }))
        else:
            alive_rows.append(match.iloc[0])

    N_SIMS = 5000
    wins: Dict[str, int] = {}

    def sim_round(teams):
        survivors = []
        mid = len(teams) // 2
        for i in range(mid):
            a = teams[i]
            b = teams[len(teams) - 1 - i]
            m = matchup_pred(a, b)
            survivors.append(a if random.random() < m["prob_a"] else b)
        if len(teams) % 2 == 1:
            survivors.append(teams[len(teams) // 2])
        return survivors

    for _ in range(N_SIMS):
        pool = sorted(
            alive_rows,
            key=lambda r: float(
                pd.to_numeric(r.get("PowerIndex_Ridge", np.nan), errors="coerce")
                if pd.notna(pd.to_numeric(r.get("PowerIndex_Ridge", np.nan), errors="coerce"))
                else pd.to_numeric(r.get("TI", 0), errors="coerce") or 0
            ),
            reverse=True,
        )
        while len(pool) > 1:
            pool = sim_round(pool)
        if pool:
            champ = str(pool[0].get("Team", ""))
            wins[champ] = wins.get(champ, 0) + 1

    return {k: v / N_SIMS for k, v in sorted(wins.items(), key=lambda x: -x[1])}

def run_state_odds(gender: str, cls: str,
                   df_bracket: pd.DataFrame,
                   df_teams: pd.DataFrame) -> Dict[str, float]:
    N_SIMS = 5000
    state_wins: Dict[str, int] = {}

    def sim_region_once(region: str):
        bracket_sub = df_bracket[
            (df_bracket["Gender"] == gender) &
            (df_bracket["Class"]  == cls)    &
            (df_bracket["Region"] == region)
        ].copy()
        if bracket_sub.empty:
            return None

        eliminated = set()
        for _, g in bracket_sub[bracket_sub["Done"] == True].iterrows():
            s1 = pd.to_numeric(g.get("Score1"), errors="coerce")
            s2 = pd.to_numeric(g.get("Score2"), errors="coerce")
            if pd.notna(s1) and pd.notna(s2):
                eliminated.add(str(g["Team2"] if s1 > s2 else g["Team1"]).strip())

        all_teams = set()
        for _, g in bracket_sub.iterrows():
            all_teams.update([str(g["Team1"]).strip(), str(g["Team2"]).strip()])
        alive = all_teams - eliminated
        if not alive:
            return None

        stats_sub = df_teams[
            (df_teams["Gender"] == gender) &
            (df_teams["Class"]  == cls)    &
            (df_teams["Region"] == region)
        ].copy()

        alive_rows = []
        for team_name in alive:
            match = stats_sub[stats_sub["Team"] == team_name]
            if match.empty:
                row = _fuzzy_find_team(df_teams, team_name, gender, cls)
                if row is not None:
                    alive_rows.append(row)
                else:
                    alive_rows.append(pd.Series({
                        "Team": team_name, "PowerIndex_Ridge": np.nan,
                        "NetEff": np.nan, "PPG": np.nan, "OPPG": np.nan, "TI": 0.0,
                    }))
            else:
                alive_rows.append(match.iloc[0])

        pool = sorted(
            alive_rows,
            key=lambda r: float(
                pd.to_numeric(r.get("PowerIndex_Ridge", np.nan), errors="coerce")
                if pd.notna(pd.to_numeric(r.get("PowerIndex_Ridge", np.nan), errors="coerce"))
                else pd.to_numeric(r.get("TI", 0), errors="coerce") or 0
            ),
            reverse=True,
        )

        def sim_round(teams):
            survivors = []
            mid = len(teams) // 2
            for i in range(mid):
                a, b = teams[i], teams[len(teams) - 1 - i]
                m = matchup_pred(a, b)
                survivors.append(a if random.random() < m["prob_a"] else b)
            if len(teams) % 2 == 1:
                survivors.append(teams[len(teams) // 2])
            return survivors

        while len(pool) > 1:
            pool = sim_round(pool)
        return pool[0] if pool else None

    for _ in range(N_SIMS):
        cn = sim_region_once("North")
        cs = sim_region_once("South")
        if cn is None or cs is None:
            continue
        m = matchup_pred(cn, cs)
        champ = cn if random.random() < m["prob_a"] else cs
        name  = str(champ.get("Team", ""))
        state_wins[name] = state_wins.get(name, 0) + 1

    total = sum(state_wins.values())
    return {k: v / total for k, v in sorted(state_wins.items(), key=lambda x: -x[1])} if total else {}

# ─────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────

render_logo()
render_page_header(
    title="🏆 Tournament Central",
    definition="2026 MPA Basketball Tournament — Live Bracket",
    subtitle="Results updated nightly. Sorted in bracket order (1,4,3,2). "
             "North on top · South on bottom · State Final on right.",
)
st.write("")

c1, c2 = st.columns(2)
with c1:
    gender = st.selectbox("Gender", ["Boys","Girls"])
with c2:
    cls = st.selectbox("Class", ["A","B","C","D","S"])

df_bracket = load_bracket()
df_teams   = load_teams()

if df_bracket.empty:
    st.error("No bracket data found. Expected: data/tournament/2026/tournament_2026.parquet")
    st.stop()

sub    = df_bracket[(df_bracket["Gender"]==gender) & (df_bracket["Class"]==cls)]
n_done = int(sub["Done"].sum()) if "Done" in sub.columns else 0
n_tot  = len(sub)

st.markdown(
    '<div style="font-family:ui-sans-serif,system-ui,sans-serif;color:rgba(203,213,225,0.7);'
    'font-size:12px;margin-bottom:8px">'
    '✅ <b style="color:#86efac">{}</b> games complete &nbsp;·&nbsp; '
    '⏳ <b style="color:#fde68a">{}</b> remaining</div>'.format(n_done, n_tot-n_done),
    unsafe_allow_html=True
)

# ── Hero banner ──────────────────────────────
site = SITE_MAP.get((cls, sub["Region"].iloc[0] if not sub.empty else ""), "Regional Site") if not sub.empty else ""
n_games_total = n_tot
n_complete    = n_done
n_remaining   = n_tot - n_done

hero_html = f"""
<!doctype html><html><head><meta charset="utf-8"/>
<style>
  .hero{{background:#060d1a;border:1px solid rgba(255,255,255,0.09);border-radius:18px;
    padding:20px 24px 18px;position:relative;overflow:hidden;
    font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
    box-shadow:0 24px 70px rgba(0,0,0,0.6);}}
  .hero:before{{content:"";position:absolute;inset:0;pointer-events:none;
    background:radial-gradient(900px 320px at 10% 0%,rgba(245,158,11,0.18),transparent 60%),
               radial-gradient(900px 320px at 90% 0%,rgba(59,130,246,0.18),transparent 60%);}}
  .eyebrow{{color:rgba(245,158,11,0.9);font-size:11px;font-weight:800;
    letter-spacing:.18em;text-transform:uppercase;margin-bottom:6px;position:relative;z-index:2;}}
  .headline{{color:#f1f5f9;font-size:26px;font-weight:900;letter-spacing:-.02em;
    margin:0 0 4px;position:relative;z-index:2;text-shadow:0 8px 28px rgba(0,0,0,0.5);}}
  .sub{{color:rgba(203,213,225,0.85);font-size:13px;margin:0 0 14px;position:relative;z-index:2;}}
  .pills{{display:flex;flex-wrap:wrap;gap:8px;position:relative;z-index:2;}}
  .pill{{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;
    font-size:12px;font-weight:600;border:1px solid rgba(255,255,255,0.12);}}
  .pill-gold{{background:rgba(245,158,11,0.18);color:#fde68a;border-color:rgba(245,158,11,0.35);}}
  .pill-green{{background:rgba(34,197,94,0.18);color:#86efac;border-color:rgba(34,197,94,0.35);}}
  .pill-blue{{background:rgba(59,130,246,0.18);color:#bfdbfe;border-color:rgba(59,130,246,0.35);}}
  .ribbon{{position:absolute;top:20px;right:16px;
    background:linear-gradient(135deg,#f59e0b,#d97706);color:#0f172a;
    font-size:10px;font-weight:900;letter-spacing:.14em;text-transform:uppercase;
    padding:4px 12px;border-radius:999px;box-shadow:0 4px 14px rgba(245,158,11,0.4);z-index:3;}}
</style></head>
<body style="margin:0;background:transparent;">
<div class="hero">
  <div class="ribbon">LIVE BRACKET</div>
  <div class="eyebrow">🏆 MPA Tournament Central</div>
  <div class="headline">2026 MPA {gender} Class {cls} Tournament</div>
  <div class="sub">North &amp; South Regions &nbsp;·&nbsp; State Final on right</div>
  <div class="pills">
    <span class="pill pill-green">✅ {n_complete} Games Complete</span>
    <span class="pill pill-blue">⏳ {n_remaining} Remaining</span>
    <span class="pill pill-gold">🏆 {n_games_total} Total Games</span>
  </div>
</div>
</body></html>"""

components.html(hero_html, height=145, scrolling=False)
st.write("")

tab_bracket, tab_odds = st.tabs(["📋 Bracket", "🎯 Championship Odds"])

with tab_bracket:
    try:
        html, height = build_full_bracket_html(gender, cls, df_bracket, df_teams)
        components.html(html, height=height, scrolling=False)
    except Exception as e:
        st.exception(e)

with tab_odds:
    st.markdown("### 🎯 Projected Championship Odds")
    st.caption("Monte Carlo — 5,000 runs per region using PowerIndex_Ridge (prediction engine ratings).")

    with st.spinner("Simulating…"):
        north_reg = run_live_odds(gender, cls, "North", df_bracket, df_teams)
        south_reg = run_live_odds(gender, cls, "South", df_bracket, df_teams)
        state_all = run_state_odds(gender, cls, df_bracket, df_teams)

    def render_odds_section(region_label: str, reg_odds: Dict[str, float]):
        if not reg_odds:
            st.caption(f"No data for {region_label}.")
            return
        st.markdown(f"**{region_label}**")
        for team, reg_prob in reg_odds.items():
            state_prob = state_all.get(team, 0.0)
            reg_bar  = f"{reg_prob   * 100:.1f}%"
            stat_bar = f"{state_prob * 100:.1f}%"
            html_row = f"""
<div style="margin-bottom:12px;font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="color:#f1f5f9;font-size:13px;font-weight:700;margin-bottom:4px;
              white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{team}</div>
  <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
    <span style="color:rgba(245,158,11,0.85);font-size:9px;font-weight:800;
                 letter-spacing:.1em;text-transform:uppercase;width:72px;">Regional</span>
    <div style="flex:1;height:7px;background:rgba(148,163,184,0.12);
                border-radius:999px;overflow:hidden;">
      <div style="height:100%;width:{reg_bar};
                  background:linear-gradient(90deg,#f59e0b,#d97706);
                  border-radius:999px;"></div>
    </div>
    <span style="color:#fde68a;font-size:12px;font-weight:800;
                 width:48px;text-align:right;">{reg_bar}</span>
  </div>
  <div style="display:flex;align-items:center;gap:6px;">
    <span style="color:rgba(99,179,237,0.85);font-size:9px;font-weight:800;
                 letter-spacing:.1em;text-transform:uppercase;width:72px;">State</span>
    <div style="flex:1;height:7px;background:rgba(148,163,184,0.12);
                border-radius:999px;overflow:hidden;">
      <div style="height:100%;width:{stat_bar};
                  background:linear-gradient(90deg,#3b82f6,#1d4ed8);
                  border-radius:999px;"></div>
    </div>
    <span style="color:#bfdbfe;font-size:12px;font-weight:800;
                 width:48px;text-align:right;">{stat_bar}</span>
  </div>
</div>""".strip()
            components.html(html_row, height=62, scrolling=False)

    render_odds_section("North", north_reg)
    st.write("")
    render_odds_section("South", south_reg)

render_footer()
