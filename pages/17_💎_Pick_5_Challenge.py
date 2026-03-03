# pages/17__Pick_5_Challenge.py
from __future__ import annotations

from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_footer,
    render_page_header,
)
from auth import login_gate, logout_button, get_supabase, SUPABASE_URL, SUPABASE_KEY

from sidebar_auth import render_sidebar_auth
render_sidebar_auth()

st.set_page_config(
    page_title="💎 Pick 5 Challenge – Analytics207",
    page_icon="💎",
    layout="wide",
)

apply_global_layout_tweaks()
login_gate(required=False)
logout_button()
render_logo()
render_page_header(
    title="💎 PICK 5 CHALLENGE",
    definition="Pick 5 Challenge (n.): One game per class. Pick a side. Bold upsets pay more.",
    subtitle="Powered by THE MODEL — upset bonus points scale with prediction confidence. Max 20 pts/week.",
)

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
_user      = st.session_state.get("user")
_signed_in = _user is not None

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
ROOT     = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

GAMES_ANALYTICS_FILE = DATA_DIR / "core"        / "games_analytics_v50.parquet"
PRED_FILE            = DATA_DIR / "predictions" / "games_predictions_current.parquet"
WEEKLY_WINNERS_FILE  = DATA_DIR / "pick5"       / "pick5_weekly_winners_v50.parquet"

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
CLASS_ORDER = ["A", "B", "C", "D", "S"]
CLASS_COLOR = {"A": "#f43f5e", "B": "#f97316", "C": "#facc15", "D": "#4ade80", "S": "#60a5fa"}
CLASS_LABEL = {"A": "Class A", "B": "Class B", "C": "Class C", "D": "Class D", "S": "Class S"}
GENDER_ICON = {"Boys": "♂️", "Girls": "♀️"}
TOP_N_GAMES = 6

HIDDEN = ["_gid", "_team", "_upset", "_pts", "_fav", "_fav_pct", "_played", "_final"]

# ─────────────────────────────────────────────
# POINT HELPERS
# ─────────────────────────────────────────────
def upset_pts(fav_pct: float) -> int:
    if fav_pct >= 80: return 4
    if fav_pct >= 70: return 3
    if fav_pct >= 60: return 2
    return 1

def pts_label(pts: int) -> str:
    return {4: "+4 🔥🔥 HUGE UPSET", 3: "+3 🔥 UPSET", 2: "+2 SLIGHT UPSET", 1: "+1 FAVORITE"}[pts]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def _clean_gameids(s: pd.Series) -> pd.Series:
    x = s.astype(str).str.strip()
    x = x.str.replace(r"\.0$", "", regex=True)
    x = x.str.replace(",", "", regex=False)
    return x

def week_bounds(anchor) -> tuple[pd.Timestamp, pd.Timestamp]:
    anchor = pd.Timestamp(anchor).normalize()
    sunday = anchor - pd.Timedelta(days=(anchor.weekday() + 1) % 7)
    return sunday, sunday + pd.Timedelta(days=6)

def fmt_week(d) -> str:
    s, e = week_bounds(d)
    return f"{s.strftime('%b %d')} – {e.strftime('%b %d, %Y')}"

# ─────────────────────────────────────────────
# LOADERS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_games() -> pd.DataFrame:
    if not GAMES_ANALYTICS_FILE.exists() or not PRED_FILE.exists():
        return pd.DataFrame()

    analytics = pd.read_parquet(GAMES_ANALYTICS_FILE).copy()
    preds     = pd.read_parquet(PRED_FILE).copy()
    analytics["GameID"] = _clean_gameids(analytics["GameID"])
    preds["GameID"]     = _clean_gameids(preds["GameID"])

    pred_keep = [c for c in ["GameID", "PredHomeWinProb", "PredMargin"] if c in preds.columns]
    preds = preds[pred_keep].drop_duplicates(subset=["GameID"], keep="first")
    df = analytics.merge(preds, on="GameID", how="left")

    df["Date"]     = pd.to_datetime(df.get("Date"), errors="coerce")
    df["DateOnly"] = df["Date"].dt.normalize()

    for col in ["Home", "Away", "Gender", "HomeClass", "AwayClass"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
        df = df[df["Gender"].isin(["Boys", "Girls"])].copy()

    if "PredHomeWinProb" in df.columns:
        p = pd.to_numeric(df["PredHomeWinProb"], errors="coerce")
        df["FavoriteIsHome"] = p >= 0.5
        df["FavProb"]        = p.where(p >= 0.5, 1.0 - p)
        df["FavProbPct"]     = df["FavProb"] * 100.0
    else:
        df["FavoriteIsHome"] = False
        df["FavProb"]        = np.nan
        df["FavProbPct"]     = np.nan

    fih             = df["FavoriteIsHome"].fillna(False).astype(bool)
    df["Favorite"]  = np.where(fih, df["Home"], df["Away"])
    df["Underdog"]  = np.where(fih, df["Away"], df["Home"])
    df["UpshotPts"] = df["FavProbPct"].apply(
        lambda x: upset_pts(float(x)) if pd.notna(x) else 1
    )

    if "HomeScore" in df.columns and "AwayScore" in df.columns:
        hs  = pd.to_numeric(df["HomeScore"], errors="coerce")
        as_ = pd.to_numeric(df["AwayScore"], errors="coerce")
        df["_Played"]     = hs.notna() & as_.notna()
        df["_HomeWon"]    = hs > as_
        df["_FinalScore"] = (
            hs.fillna(0).astype(int).astype(str) + "–" +
            as_.fillna(0).astype(int).astype(str)
        ).where(df["_Played"], "")
    else:
        df["_Played"]     = False
        df["_HomeWon"]    = False
        df["_FinalScore"] = ""

    return df.reset_index(drop=True)


def load_rosters() -> pd.DataFrame:
    """Load pick_5_rosters from Supabase."""
    cols = ["Manager","WeekID","WeekLabel","Class","Gender","GameID","Matchup",
            "GameDate","Pick","IsUpset","FavPct","MaxPts","ActualPts","Result","LockedAt","user_id"]
    try:
        sb  = get_supabase()
        res = sb.table("pick_5_rosters").select("*").execute()
        if not res.data:
            return pd.DataFrame(columns=cols)
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame(columns=cols)


def save_roster_row(row: dict) -> None:
    """Upsert a pick into pick_5_rosters via Supabase (service role)."""
    try:
        from supabase import create_client

        user = st.session_state.get("user")

        service_key = st.secrets.get("SUPABASE_SERVICE_KEY", "")
        sb = create_client(SUPABASE_URL, service_key)

        row["user_id"] = str(user.id) if user else ""
        sb.table("pick_5_rosters").upsert(
            row,
            on_conflict="user_id,WeekID,Class",
        ).execute()

    except Exception as e:
        st.error(f"Save failed: {e}")


# ─────────────────────────────────────────────
# BUILD PICK TABLE
# ─────────────────────────────────────────────
def build_pick_table(
    cls_games: pd.DataFrame,
    current_pick: dict | None,
    show_gender_col: bool = False,
) -> pd.DataFrame:
    rows = []
    for _, g in cls_games.iterrows():
        gid     = str(g.get("GameID", ""))
        fav     = str(g["Favorite"])
        dog     = str(g["Underdog"])
        fav_pct = float(g["FavProbPct"]) if pd.notna(g["FavProbPct"]) else 50.0
        dog_pct = 100.0 - fav_pct
        pts     = int(g["UpshotPts"])
        gender  = str(g.get("Gender", ""))
        g_icon  = GENDER_ICON.get(gender, "") if show_gender_col else ""
        datestr = g["Date"].strftime("%b %d") if pd.notna(g["Date"]) else "TBD"
        played  = bool(g.get("_Played", False))
        final   = str(g.get("_FinalScore", ""))

        dog_active = (
            current_pick is not None
            and current_pick.get("game_id") == gid
            and current_pick.get("team") == dog
        )
        fav_active = (
            current_pick is not None
            and current_pick.get("game_id") == gid
            and current_pick.get("team") == fav
        )

        base = {
            "Dog %":    round(dog_pct, 1),
            "Fav %":    round(fav_pct, 1),
            "Date":     datestr,
            "G":        g_icon,
            "_gid":     gid,
            "_upset_gender": gender,
            "_upset":   True,
            "_pts":     pts,
            "_fav":     fav,
            "_fav_pct": fav_pct,
            "_played":  played,
            "_final":   final,
        }

        rows.append({**base,
            "✓":        dog_active,
            "Pick":     dog,
            "Opponent": fav,
            "Role":     "🔥 Underdog",
            "Pts":      pts_label(pts),
            "_team":    dog,
            "_upset":   True,
        })
        rows.append({**base,
            "✓":        fav_active,
            "Pick":     fav,
            "Opponent": dog,
            "Role":     "✅ Favorite",
            "Pts":      "+1 FAVORITE",
            "_team":    fav,
            "_upset":   False,
            "_pts":     1,
        })

    return pd.DataFrame(rows)


def filter_cls_games(week_games: pd.DataFrame, cls: str) -> pd.DataFrame:
    cls_games = (
        week_games[
            (week_games["HomeClass"].astype(str).str.strip() == cls) |
            (week_games["AwayClass"].astype(str).str.strip() == cls)
        ]
        .drop_duplicates(subset=["GameID"])
        .copy()
    )
    if cls_games.empty:
        return cls_games

    cls_games["_tier"] = cls_games["UpshotPts"]
    frames = []
    for tier_val in [4, 3, 2, 1]:
        frames.append(
            cls_games[cls_games["_tier"] == tier_val]
            .sort_values("FavProbPct", ascending=False)
            .head(2)
        )
    return (
        pd.concat(frames)
        .drop_duplicates(subset=["GameID"])
        .head(TOP_N_GAMES)
        .reset_index(drop=True)
    )


# ─────────────────────────────────────────────
# LOAD + CONTROLS
# ─────────────────────────────────────────────
games_df = load_games()
if games_df.empty:
    st.error("Could not load game data.")
    render_footer()
    st.stop()

today          = pd.Timestamp(datetime.today().date())
w_start, w_end = week_bounds(today)
week_id        = f"{w_start.strftime('%Y-%m-%d')}_to_{w_end.strftime('%Y-%m-%d')}"
wlabel         = fmt_week(today)

manager_name = ""
if _signed_in:
    _meta = getattr(_user, "user_metadata", {}) or {}
    manager_name = (
        _meta.get("display_name")
        or _meta.get("full_name")
        or getattr(_user, "email", "").split("@")[0]
    )

ctrl1, ctrl2, ctrl3 = st.columns([2, 1, 1])
with ctrl1:
    if _signed_in:
        st.markdown(f"**Playing as:** {manager_name}")
    else:
        components.html("""
<style>* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: transparent; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; color: #f1f5f9; }</style>
<div style="background:linear-gradient(135deg,#0f172a,#1a1a2e);
            border:1px solid rgba(96,165,250,0.3);border-radius:14px;
            padding:20px 24px;text-align:center;">
  <div style="font-size:1.5rem;margin-bottom:6px;">🔑</div>
  <div style="font-size:0.95rem;font-weight:700;color:#93c5fd;margin-bottom:4px;">Sign in to make your picks</div>
  <div style="font-size:0.78rem;color:#94a3b8;">Free account required to participate. Leaderboard visible to everyone.</div>
</div>
""", height=120, scrolling=False)
with ctrl2:
    slate_mode = st.selectbox("Gender slate", ["Boys", "Girls", "Both"], index=0)
with ctrl3:
    with st.expander("⚙️ Options"):
        anchor = st.date_input("Week anchor", value=today.date(), key="p5_anchor")
        w_start, w_end = week_bounds(anchor)
        week_id        = f"{w_start.strftime('%Y-%m-%d')}_to_{w_end.strftime('%Y-%m-%d')}"
        wlabel         = fmt_week(anchor)
        dev_mode = st.toggle("🛠 Dev mode (include played games)", value=False)

st.caption(f"📅 **{wlabel}**")
if dev_mode:
    st.warning("🛠 Dev mode — showing all games including played.", icon="⚠️")

with st.expander("📐 How point values work", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    for col, (pts, label, desc, color) in zip(
        [c1, c2, c3, c4],
        [(1,"Favorite","Any odds","#6b7280"),
         (2,"+2 pts","60–69% fav","#facc15"),
         (3,"+3 pts","70–79% fav","#f97316"),
         (4,"+4 pts","80%+ fav","#f43f5e")],
    ):
        col.markdown(
            f'<div style="text-align:center;padding:10px;border-radius:10px;'
            f'background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);">'
            f'<div style="font-size:1.8rem;font-weight:900;color:{color};line-height:1;">+{pts}</div>'
            f'<div style="font-size:0.78rem;font-weight:800;color:#e2e8f0;margin-top:4px;">{label}</div>'
            f'<div style="font-size:0.68rem;color:rgba(148,163,184,0.6);">{desc}</div></div>',
            unsafe_allow_html=True,
        )
    st.caption("Pick the underdog to earn bonus pts. One pick per class. 5 picks total. Max 20 pts/week.")

st.divider()

# ─────────────────────────────────────────────
# SIGN-IN GATE
# ─────────────────────────────────────────────
if not _signed_in:
    st.markdown("### 🎯 Pick Slate")
    st.info("🔑 **Sign in with a free account** to make your picks. Browse the leaderboard below!")
    st.divider()

    st.markdown("### 🏆 Leaderboard")
    tab_week, tab_season = st.tabs(["This Week", "Season"])
    rosters = load_rosters()
    with tab_week:
        if rosters.empty or "WeekID" not in rosters.columns:
            st.info("No picks submitted yet.")
        else:
            wk_data = rosters[rosters["WeekID"].astype(str) == str(week_id)].copy()
            if wk_data.empty:
                st.info("No picks for this week yet — be the first!")
            else:
                wk_data["Pts"] = pd.to_numeric(wk_data.get("ActualPts", pd.Series(dtype=str)), errors="coerce").fillna(0)
                lb = (
                    wk_data.groupby("Manager", dropna=False)
                    .agg(TotalPts=("Pts", "sum"), Picks=("Class", "count"))
                    .reset_index()
                    .sort_values("TotalPts", ascending=False)
                    .reset_index(drop=True)
                )
                for i, row in lb.iterrows():
                    rank = i + 1
                    icon = "🥇" if rank==1 else ("🥈" if rank==2 else ("🥉" if rank==3 else f"#{rank}"))
                    c1, c2, c3 = st.columns([1, 6, 2])
                    c1.markdown(f"**{icon}**")
                    c2.markdown(f"**{row['Manager']}** · {int(row['Picks'])} picks")
                    c3.markdown(f'<div style="text-align:right;color:#fde68a;font-weight:900;">+{int(row["TotalPts"])} pts</div>', unsafe_allow_html=True)
    with tab_season:
        src = rosters if not rosters.empty else pd.DataFrame()
        if not src.empty and "ActualPts" in src.columns:
            src["Pts"] = pd.to_numeric(src["ActualPts"], errors="coerce").fillna(0)
            season_lb = (
                src.groupby("Manager", dropna=False)
                .agg(TotalPts=("Pts", "sum"), Weeks=("WeekID", "nunique"))
                .reset_index()
                .sort_values("TotalPts", ascending=False)
                .reset_index(drop=True)
            )
            for i, row in season_lb.iterrows():
                rank = i + 1
                icon = "🥇" if rank==1 else ("🥈" if rank==2 else ("🥉" if rank==3 else f"#{rank}"))
                c1, c2, c3 = st.columns([1, 6, 2])
                c1.markdown(f"**{icon}**")
                c2.markdown(f"**{row['Manager']}** · {int(row['Weeks'])} week(s)")
                c3.markdown(f'<div style="text-align:right;color:#fde68a;font-weight:900;">+{int(row["TotalPts"])} pts</div>', unsafe_allow_html=True)
        else:
            st.info("Season standings available once weekly results are scored.")
    render_footer()
    st.stop()

# ─────────────────────────────────────────────
# FILTER WEEK GAMES
# ─────────────────────────────────────────────
week_games = games_df[
    (games_df["DateOnly"] >= w_start) &
    (games_df["DateOnly"] <= w_end) &
    (games_df["FavProbPct"].notna())
].copy()

if not dev_mode and "_Played" in week_games.columns:
    week_games = week_games[~week_games["_Played"].fillna(False)].copy()

genders_to_show = (
    ["Boys"] if slate_mode == "Boys"
    else ["Girls"] if slate_mode == "Girls"
    else ["Boys", "Girls"]
)
week_games = week_games[week_games["Gender"].isin(genders_to_show)].copy()
show_gender_col = (slate_mode == "Both")

# ─────────────────────────────────────────────
# PICK SLATE
# ─────────────────────────────────────────────
st.markdown("### 🎯 Make Your Picks")
st.caption(
    "Check the row for the **team you want to pick**. "
    "One pick per class — **5 picks total**. "
    + ("♂️/♀️ column shows which gender slate the game is from." if show_gender_col else "")
)

picks: dict[str, dict | None] = {}

for cls in CLASS_ORDER:
    cls_hex   = CLASS_COLOR[cls]
    ss_key    = f"p5_{week_id}_{cls}"
    current   = st.session_state.get(ss_key)
    cls_games = filter_cls_games(week_games, cls)

    n_games    = len(cls_games)
    pick_badge = ""
    if current:
        tc        = {4:"#f43f5e",3:"#f97316",2:"#facc15",1:"#94a3b8"}.get(current["pts"],"#94a3b8")
        g_icon    = GENDER_ICON.get(current.get("gender", ""), "")
        pick_badge = (
            f' &nbsp;·&nbsp; <span style="color:{tc};font-weight:900;">'
            f'✓ {g_icon} {current["team"]} +{current["pts"]} pts</span>'
        )

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'border-bottom:2px solid {cls_hex}33;padding:6px 0 10px;margin:28px 0 8px;">'
        f'<div style="width:10px;height:10px;border-radius:50%;background:{cls_hex};"></div>'
        f'<span style="font-size:1rem;font-weight:900;color:{cls_hex};'
        f'letter-spacing:0.06em;text-transform:uppercase;">{CLASS_LABEL[cls]}</span>'
        f'<span style="font-size:0.72rem;color:rgba(148,163,184,0.5);">'
        f'{n_games} game{"s" if n_games!=1 else ""}{pick_badge}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if cls_games.empty:
        st.caption(f"No Class {cls} games found for this week.")
        picks[cls] = None
        continue

    tbl = build_pick_table(cls_games, current, show_gender_col=show_gender_col)

    display_cols = (
        ["✓", "G", "Pick", "Opponent", "Role", "Dog %", "Fav %", "Pts", "Date"]
        if show_gender_col else
        ["✓", "Pick", "Opponent", "Role", "Dog %", "Fav %", "Pts", "Date"]
    )
    disabled_cols = (
        ["G", "Pick", "Opponent", "Role", "Dog %", "Fav %", "Pts", "Date"]
        if show_gender_col else
        ["Pick", "Opponent", "Role", "Dog %", "Fav %", "Pts", "Date"]
    )

    col_cfg = {
        "✓":        st.column_config.CheckboxColumn("✓", width="small"),
        "G":        st.column_config.TextColumn("", width="small"),
        "Pick":     st.column_config.TextColumn("Pick", width="medium"),
        "Opponent": st.column_config.TextColumn("Opponent", width="medium"),
        "Role":     st.column_config.TextColumn("Role", width="small"),
        "Dog %":    st.column_config.NumberColumn("Dog %", format="%.1f%%", width="small"),
        "Fav %":    st.column_config.NumberColumn("Fav %", format="%.1f%%", width="small"),
        "Pts":      st.column_config.TextColumn("Pts if Correct", width="medium"),
        "Date":     st.column_config.TextColumn("Date", width="small"),
    }

    edited = st.data_editor(
        tbl[display_cols + HIDDEN + ["_upset_gender"]],
        column_config=col_cfg,
        column_order=display_cols,
        hide_index=True,
        use_container_width=True,
        disabled=disabled_cols + HIDDEN + ["_upset_gender"],
        key=f"de_{week_id}_{cls}",
        height=min(36 * len(tbl) + 38, 420),
    )

    checked_rows = edited[edited["✓"] == True]
    if len(checked_rows) > 1:
        if current:
            new_rows = checked_rows[checked_rows["_team"] != current.get("team")]
            checked_rows = new_rows.iloc[[0]] if not new_rows.empty else checked_rows.iloc[[0]]
        else:
            checked_rows = checked_rows.iloc[[0]]
        st.toast(f"⚠️ One pick per class — kept: {checked_rows.iloc[0]['Pick']}", icon="⚠️")

    if not checked_rows.empty:
        row        = checked_rows.iloc[0]
        gender_val = str(row.get("_upset_gender", genders_to_show[0]))
        new_pick   = {
            "team":    str(row["_team"]),
            "pts":     int(row["_pts"]),
            "game_id": str(row["_gid"]),
            "upset":   bool(row["_upset"]),
            "cls":     cls,
            "gender":  gender_val,
            "fav_pct": float(row["_fav_pct"]),
            "matchup": (
                f"{row['_team']} vs {row['_fav']}" if row["_upset"]
                else f"{row['_fav']} vs {row['Pick']}"
            ),
            "date": "",
        }
        if new_pick != current:
            st.session_state[ss_key] = new_pick
            st.rerun()
        picks[cls] = new_pick
    else:
        if current:
            st.session_state[ss_key] = None
            st.rerun()
        picks[cls] = None

st.divider()

# ─────────────────────────────────────────────
# SUMMARY TABLE
# ─────────────────────────────────────────────
st.markdown("### 📋 Your Picks This Week")

total_pts  = 0
all_picked = True
rows_html  = []

for cls in CLASS_ORDER:
    p       = picks.get(cls)
    cls_hex = CLASS_COLOR[cls]
    if p:
        total_pts += p["pts"]
        tier_color = {4:"#f43f5e",3:"#f97316",2:"#facc15",1:"#94a3b8"}.get(p["pts"],"#94a3b8")
        fav_pct    = p.get("fav_pct", 50.0)
        dog_pct    = 100.0 - fav_pct
        is_upset   = p.get("upset", False)
        g_icon     = GENDER_ICON.get(p.get("gender", ""), "")
        conf_str   = (
            f"{dog_pct:.0f}% dog → +{p['pts']} pts" if is_upset
            else f"{fav_pct:.0f}% conf · +1 pt"
        )
        rows_html.append(
            f'<tr>'
            f'<td style="color:{cls_hex};font-weight:900;padding:8px 12px;">{CLASS_LABEL[cls]}</td>'
            f'<td style="color:#e2e8f0;font-weight:800;padding:8px 12px;">{g_icon} {p["team"]}</td>'
            f'<td style="color:rgba(148,163,184,0.7);font-size:0.82rem;padding:8px 12px;">{p.get("matchup","—")}</td>'
            f'<td style="color:rgba(148,163,184,0.6);font-size:0.80rem;padding:8px 12px;">{conf_str}</td>'
            f'<td style="color:{tier_color};font-weight:900;text-align:right;padding:8px 12px;">+{p["pts"]}</td>'
            f'</tr>'
        )
    else:
        all_picked = False
        rows_html.append(
            f'<tr style="opacity:0.35;">'
            f'<td style="color:{cls_hex};font-weight:900;padding:8px 12px;">{CLASS_LABEL[cls]}</td>'
            f'<td style="color:rgba(148,163,184,0.4);font-style:italic;padding:8px 12px" colspan="3">No pick yet</td>'
            f'<td style="text-align:right;padding:8px 12px;color:rgba(148,163,184,0.3);">—</td>'
            f'</tr>'
        )

if total_pts:
    rows_html.append(
        f'<tr style="border-top:1px solid rgba(245,158,11,0.3);">'
        f'<td colspan="4" style="color:#f1f5f9;font-weight:900;padding:10px 12px;font-size:0.95rem;">TOTAL</td>'
        f'<td style="color:#fde68a;font-weight:900;font-size:1.1rem;text-align:right;padding:10px 12px;">+{total_pts}</td>'
        f'</tr>'
    )

st.markdown(
    f'<table style="width:100%;border-collapse:collapse;background:rgba(8,15,30,0.6);'
    f'border:1px solid rgba(255,255,255,0.08);border-radius:12px;overflow:hidden;'
    f'font-family:ui-sans-serif,system-ui,sans-serif;">'
    f'<thead><tr style="border-bottom:1px solid rgba(255,255,255,0.08);">'
    f'<th style="text-align:left;color:rgba(148,163,184,0.6);font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase;padding:8px 12px;font-weight:700;">Class</th>'
    f'<th style="text-align:left;color:rgba(148,163,184,0.6);font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase;padding:8px 12px;font-weight:700;">Pick</th>'
    f'<th style="text-align:left;color:rgba(148,163,184,0.6);font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase;padding:8px 12px;font-weight:700;">Matchup</th>'
    f'<th style="text-align:left;color:rgba(148,163,184,0.6);font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase;padding:8px 12px;font-weight:700;">Confidence</th>'
    f'<th style="text-align:right;color:rgba(148,163,184,0.6);font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase;padding:8px 12px;font-weight:700;">Pts</th>'
    f'</tr></thead>'
    f'<tbody>{"".join(rows_html)}</tbody>'
    f'</table>',
    unsafe_allow_html=True,
)

st.write("")

# ─────────────────────────────────────────────
# SUBMIT
# ─────────────────────────────────────────────
if not all_picked:
    missing = [f"Class {c}" for c in CLASS_ORDER if not picks.get(c)]
    st.warning(f"Still need: {', '.join(missing)}")
else:
    if dev_mode:
        st.warning("🛠 Dev mode — submitting with played games included.", icon="⚠️")
    if st.button("💾 Lock In My Picks", type="primary"):
        for cls in CLASS_ORDER:
            p = picks.get(cls)
            if p:
                save_roster_row({
                    "Manager":   manager_name,
                    "WeekID":    week_id,
                    "WeekLabel": wlabel,
                    "Class":     cls,
                    "Gender":    p.get("gender", ""),
                    "GameID":    p.get("game_id", ""),
                    "Matchup":   p.get("matchup", ""),
                    "GameDate":  p.get("date", ""),
                    "Pick":      p["team"],
                    "IsUpset":   bool(p.get("upset", False)),
                    "FavPct":    float(round(p.get("fav_pct", 0), 1)),
                    "MaxPts":    float(p["pts"]),
                    "ActualPts": None,
                    "Result":    None,
                    "LockedAt":  datetime.utcnow().isoformat(timespec="seconds"),
                })
        st.success(f"✅ **{manager_name}** — picks locked! Max this week: **+{total_pts} pts**.")
        st.balloons()

st.divider()

# ─────────────────────────────────────────────
# LEADERBOARD
# ─────────────────────────────────────────────
st.markdown("### 🏆 Leaderboard")
tab_week, tab_season = st.tabs(["This Week", "Season"])
rosters = load_rosters()

with tab_week:
    if rosters.empty or "WeekID" not in rosters.columns:
        st.info("No picks submitted yet.")
    else:
        wk_data = rosters[rosters["WeekID"].astype(str) == str(week_id)].copy()
        if wk_data.empty:
            st.info("No picks for this week yet — be the first!")
        else:
            wk_data["Pts"] = pd.to_numeric(wk_data.get("ActualPts", pd.Series(dtype=str)), errors="coerce").fillna(0)
            lb = (
                wk_data.groupby("Manager", dropna=False)
                .agg(TotalPts=("Pts", "sum"), Picks=("Class", "count"))
                .reset_index()
                .sort_values("TotalPts", ascending=False)
                .reset_index(drop=True)
            )
            for i, row in lb.iterrows():
                rank = i + 1
                icon = "🥇" if rank==1 else ("🥈" if rank==2 else ("🥉" if rank==3 else f"#{rank}"))
                c1, c2, c3 = st.columns([1, 6, 2])
                c1.markdown(f"**{icon}**")
                c2.markdown(f"**{row['Manager']}** · {int(row['Picks'])} picks")
                c3.markdown(f'<div style="text-align:right;color:#fde68a;font-weight:900;">+{int(row["TotalPts"])} pts</div>', unsafe_allow_html=True)

with tab_season:
    src = rosters if not rosters.empty else pd.DataFrame()
    if not src.empty and "ActualPts" in src.columns:
        src["Pts"] = pd.to_numeric(src["ActualPts"], errors="coerce").fillna(0)
        season_lb = (
            src.groupby("Manager", dropna=False)
            .agg(TotalPts=("Pts", "sum"), Weeks=("WeekID", "nunique"))
            .reset_index()
            .sort_values("TotalPts", ascending=False)
            .reset_index(drop=True)
        )
        for i, row in season_lb.iterrows():
            rank = i + 1
            icon = "🥇" if rank==1 else ("🥈" if rank==2 else ("🥉" if rank==3 else f"#{rank}"))
            c1, c2, c3 = st.columns([1, 6, 2])
            c1.markdown(f"**{icon}**")
            c2.markdown(f"**{row['Manager']}** · {int(row['Weeks'])} week(s)")
            c3.markdown(f'<div style="text-align:right;color:#fde68a;font-weight:900;">+{int(row["TotalPts"])} pts</div>', unsafe_allow_html=True)
    else:
        st.info("Season standings available once weekly results are scored.")

render_footer()
