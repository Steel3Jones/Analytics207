from __future__ import annotations

from pathlib import Path
import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
)

st.set_page_config(
    page_title="🎯 The Projector | Analytics207",
    page_icon="🎯",
    layout="wide",
)
apply_global_layout_tweaks()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GAMES_PATH   = PROJECT_ROOT / "data" / "core"        / "games_game_core_v50.parquet"
PRED_PATH    = PROJECT_ROOT / "data" / "predictions" / "games_predictions_current.parquet"
TEAMS_PATH   = PROJECT_ROOT / "data" / "core"        / "teams_team_season_core_v50.parquet"

# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_data():
    games = pd.read_parquet(GAMES_PATH)
    preds = pd.read_parquet(PRED_PATH)
    teams = pd.read_parquet(TEAMS_PATH)

    # Normalize GameID
    for df in [games, preds]:
        df["GameID"] = (
            df["GameID"].astype(str).str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )

    # Drop any pred-like cols from games before merge
    drop_cols = ["PredHomeWinProb", "PredMargin", "FavoriteTeamKey",
                 "FavProb", "PredHomeScore", "PredAwayScore"]
    games = games.drop(columns=[c for c in drop_cols if c in games.columns], errors="ignore")

    df = games.merge(
        preds[["GameID", "PredHomeWinProb", "PredMargin"]],
        on="GameID", how="left"
    )

    df["Date"]          = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df["PredHomeWinProb"] = pd.to_numeric(df["PredHomeWinProb"], errors="coerce")
    df["PredMargin"]    = pd.to_numeric(df["PredMargin"],      errors="coerce")
    df["Played"]        = df["Played"].fillna(False).astype(bool)

    for col in ["Home", "Away", "Gender", "HomeClass", "AwayClass",
                "HomeRegion", "AwayRegion"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()

    # Derived columns
    df["FavProb"] = df["PredHomeWinProb"].apply(
        lambda p: max(float(p), 1.0 - float(p)) if pd.notna(p) else np.nan
    )
    df["AbsMargin"] = df["PredMargin"].abs()

    def _fav(row):
        if pd.isna(row.get("PredMargin")): return ""
        return row["Home"] if row["PredMargin"] > 0 else row["Away"]

    def _dog(row):
        if pd.isna(row.get("PredMargin")): return ""
        return row["Away"] if row["PredMargin"] > 0 else row["Home"]

    df["Favorite"] = df.apply(_fav, axis=1)
    df["Underdog"]  = df.apply(_dog, axis=1)

    # Team TI lookup for travel risk context
    for col in ["TeamKey", "Team", "Gender", "Class", "Region", "TI"]:
        if col in teams.columns:
            teams[col] = teams[col].astype(str).str.strip()
    if "TI" in teams.columns:
        teams["TI"] = pd.to_numeric(teams["TI"], errors="coerce")

    return df, teams


df_all, teams_df = load_data()

today      = dt.date.today()
week_end   = today + dt.timedelta(days=7)

upcoming = df_all[
    (~df_all["Played"]) &
    (df_all["Date"] >= today) &
    (df_all["Date"] <= week_end) &
    df_all["PredHomeWinProb"].notna()
].copy()


# ─────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────

render_logo()
render_page_header(
    title="🎯 The Projector",
    definition="The Projector (n.): The model's preview of the week ahead.",
    subtitle=(
        "Top matchups, upset alerts, lock of the week, and games to circle on your "
        "calendar — refreshed nightly with the latest predictions."
    ),
)
st.write("")

# ─────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────

fc1, fc2, fc3 = st.columns(3)
with fc1:
    sel_gender = st.selectbox("Gender", ["All", "Boys", "Girls"])
with fc2:
    sel_class  = st.selectbox("Class",  ["All", "A", "B", "C", "D", "S"])
with fc3:
    sel_region = st.selectbox("Region", ["All", "North", "South"])

view = upcoming.copy()
if sel_gender != "All" and "Gender" in view.columns:
    view = view[view["Gender"] == sel_gender]
if sel_class  != "All" and "HomeClass" in view.columns:
    view = view[view["HomeClass"] == sel_class]
if sel_region != "All" and "HomeRegion" in view.columns:
    view = view[view["HomeRegion"] == sel_region]

st.write("")

# ─────────────────────────────────────────────
# HERO SUMMARY CARDS
# ─────────────────────────────────────────────

def render_projector_hero(df: pd.DataFrame) -> None:
    n_games   = len(df)
    n_tossups = int((df["FavProb"] <= 0.60).sum()) if "FavProb" in df.columns else 0
    n_locks   = int((df["FavProb"] >= 0.85).sum()) if "FavProb" in df.columns else 0
    avg_m     = df["AbsMargin"].mean()              if "AbsMargin" in df.columns else np.nan

    cards = [
        ("📅", "Games This Week",        str(n_games),                             "#f59e0b"),
        ("⚔️",  "Toss-Ups  (≤60%)",      str(n_tossups),                           "#3b82f6"),
        ("🔒", "Locks  (≥85%)",           str(n_locks),                             "#10b981"),
        ("📐", "Avg Projected Margin",   f"{avg_m:.1f} pts" if pd.notna(avg_m) else "—", "#8b5cf6"),
    ]

    card_html = ""
    for icon, label, val, color in cards:
        card_html += f"""
        <div style="flex:1;min-width:160px;background:#0d1626;
                    border:1px solid rgba(255,255,255,0.09);
                    border-top:3px solid {color};border-radius:14px;
                    padding:16px 18px 14px;">
          <div style="font-size:20px;margin-bottom:6px;">{icon}</div>
          <div style="font-size:24px;font-weight:900;color:#f1f5f9;">{val}</div>
          <div style="font-size:11px;color:rgba(203,213,225,0.55);margin-top:4px;">{label}</div>
        </div>"""

    html = f"""<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0;background:transparent;
             font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="display:flex;gap:14px;flex-wrap:wrap;padding:4px 0 8px;">{card_html}</div>
</body></html>"""
    components.html(html, height=130, scrolling=False)


render_projector_hero(view)
st.write("")

# ─────────────────────────────────────────────
# GAME CARD HTML
# ─────────────────────────────────────────────

def game_card_html(row: pd.Series, badge: str, badge_color: str) -> str:
    home    = str(row.get("Home",       ""))
    away    = str(row.get("Away",       ""))
    date    = str(row.get("Date",       ""))
    prob    = row.get("PredHomeWinProb", np.nan)
    margin  = row.get("PredMargin",     np.nan)
    cls     = str(row.get("HomeClass",  ""))
    region  = str(row.get("HomeRegion", ""))
    gender  = str(row.get("Gender",     ""))

    prob_home = f"{prob*100:.0f}%"       if pd.notna(prob)   else "—"
    prob_away = f"{(1-prob)*100:.0f}%"   if pd.notna(prob)   else "—"
    margin_s  = f"{abs(margin):.1f} pts" if pd.notna(margin) else "—"
    fav_home  = pd.notna(margin) and margin > 0
    bar_w     = f"{max(prob, 1-prob)*100:.1f}%" if pd.notna(prob) else "50%"

    return f"""
<div style="background:#0d1626;border:1px solid rgba(255,255,255,0.09);
            border-radius:14px;padding:14px 16px 12px;margin-bottom:10px;
            font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="display:flex;justify-content:space-between;
              align-items:center;margin-bottom:10px;">
    <span style="font-size:10px;color:rgba(148,163,184,0.55);">
      {date} · {gender} Class {cls} {region}
    </span>
    <span style="background:{badge_color};color:#0f172a;font-size:9px;
                 font-weight:900;letter-spacing:.12em;text-transform:uppercase;
                 padding:3px 10px;border-radius:999px;">{badge}</span>
  </div>

  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;">
    <!-- Away -->
    <div style="flex:1;text-align:left;">
      <div style="font-size:13px;font-weight:{'600' if fav_home else '900'};
                  color:{'rgba(203,213,225,0.55)' if fav_home else '#f1f5f9'};">{away}</div>
      <div style="font-size:12px;color:#fde68a;font-weight:700;margin-top:2px;">{prob_away}</div>
    </div>
    <!-- Center -->
    <div style="text-align:center;padding:0 8px;">
      <div style="font-size:11px;color:rgba(148,163,184,0.35);font-weight:700;">@</div>
      <div style="font-size:10px;color:rgba(148,163,184,0.35);margin-top:2px;">{margin_s}</div>
    </div>
    <!-- Home -->
    <div style="flex:1;text-align:right;">
      <div style="font-size:13px;font-weight:{'900' if fav_home else '600'};
                  color:{'#f1f5f9' if fav_home else 'rgba(203,213,225,0.55)'};">{home}</div>
      <div style="font-size:12px;color:#fde68a;font-weight:700;margin-top:2px;">{prob_home}</div>
    </div>
  </div>

  <!-- Probability bar -->
  <div style="margin-top:8px;height:4px;border-radius:999px;
              background:rgba(148,163,184,0.12);overflow:hidden;">
    <div style="height:100%;width:{bar_w};
                {'margin-left:0' if fav_home else f'margin-left:calc(100% - {bar_w})'};
                background:linear-gradient(90deg,#f59e0b,#d97706);
                border-radius:999px;"></div>
  </div>
</div>""".strip()


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab_watch, tab_upsets, tab_lock, tab_full = st.tabs([
    "🔥 Games to Watch",
    "😱 Upset Alerts",
    "🔒 Lock of the Week",
    "📋 Full Week Schedule",
])

# ── TAB 1 — GAMES TO WATCH ────────────────────────────────────────────

with tab_watch:
    st.markdown("### 🔥 Must-Watch Games This Week")
    st.caption("Closest projected margins — these are the games most likely to go either way.")
    st.write("")

    if view.empty:
        st.info("No upcoming games found for this filter combination.")
    else:
        tossups = view[view["FavProb"].notna()].sort_values("FavProb").head(10)
        col1, col2 = st.columns(2)

        for i, (_, row) in enumerate(tossups.iterrows()):
            fp = row.get("FavProb", 0.5)
            if fp <= 0.55:
                badge, color = "TOSS-UP",   "#f59e0b"
            elif fp <= 0.65:
                badge, color = "CLOSE GAME","#3b82f6"
            else:
                badge, color = "WATCH",     "#64748b"

            html = game_card_html(row, badge, color)
            with (col1 if i % 2 == 0 else col2):
                components.html(html, height=132, scrolling=False)

# ── TAB 2 — UPSET ALERTS ─────────────────────────────────────────────

with tab_upsets:
    st.markdown("### 😱 Upset Alerts")
    st.caption(
        "Games where the model has strong conviction — but upsets here would shake the rankings. "
        "Heavy favorites are not immune."
    )
    st.write("")

    if view.empty:
        st.info("No upcoming games found for this filter combination.")
    else:
        alert_pool = (
            view[view["FavProb"].notna() & (view["FavProb"] >= 0.72)]
            .sort_values("FavProb", ascending=False)
            .head(10)
        )

        if alert_pool.empty:
            st.info("No heavy-favorite games in this view this week.")
        else:
            col1, col2 = st.columns(2)
            for i, (_, row) in enumerate(alert_pool.iterrows()):
                fp = row.get("FavProb", 0.5)
                if fp >= 0.90:
                    badge, color = "UPSET WATCH 🚨", "#dc2626"
                elif fp >= 0.80:
                    badge, color = "UPSET ALERT",    "#f97316"
                else:
                    badge, color = "SLIGHT RISK",    "#f59e0b"

                html = game_card_html(row, badge, color)
                with (col1 if i % 2 == 0 else col2):
                    components.html(html, height=132, scrolling=False)

# ── TAB 3 — LOCK OF THE WEEK ──────────────────────────────────────────

with tab_lock:
    st.markdown("### 🔒 Lock of the Week")
    st.caption("The model's single highest-confidence prediction for the week ahead.")
    st.write("")

    if view.empty or view["FavProb"].isna().all():
        st.info("No games to evaluate this week.")
    else:
        lock_row = view.loc[view["FavProb"].idxmax()]

        home   = str(lock_row.get("Home",       ""))
        away   = str(lock_row.get("Away",       ""))
        date   = str(lock_row.get("Date",       ""))
        prob   = lock_row.get("PredHomeWinProb", np.nan)
        margin = lock_row.get("PredMargin",     np.nan)
        cls    = str(lock_row.get("HomeClass",  ""))
        region = str(lock_row.get("HomeRegion", ""))
        gender = str(lock_row.get("Gender",     ""))

        fav_team = home if (pd.notna(margin) and margin > 0) else away
        fav_prob = max(prob, 1 - prob) if pd.notna(prob) else np.nan
        prob_s   = f"{fav_prob*100:.1f}%" if pd.notna(fav_prob) else "—"
        margin_s = f"{abs(margin):.1f}"   if pd.notna(margin)   else "—"

        # Confidence label
        if pd.notna(fav_prob):
            if fav_prob >= 0.92:   conf, conf_color = "ELITE LOCK",  "#22c55e"
            elif fav_prob >= 0.85: conf, conf_color = "STRONG LOCK", "#10b981"
            else:                  conf, conf_color = "LEAN",        "#f59e0b"
        else:
            conf, conf_color = "—", "#64748b"

        lock_html = f"""
<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0;background:transparent;
             font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
<div style="max-width:560px;margin:0 auto;">
  <div style="background:linear-gradient(135deg,rgba(245,158,11,0.15),rgba(217,119,6,0.08));
              border:2px solid rgba(245,158,11,0.4);border-radius:20px;
              padding:32px;text-align:center;">

    <div style="font-size:44px;margin-bottom:10px;">🔒</div>

    <div style="font-size:10px;color:rgba(245,158,11,0.9);font-weight:800;
                letter-spacing:.18em;text-transform:uppercase;margin-bottom:14px;">
      Lock of the Week
    </div>

    <div style="font-size:28px;font-weight:900;color:#f1f5f9;margin-bottom:4px;">
      {fav_team}
    </div>

    <div style="font-size:13px;color:rgba(203,213,225,0.65);margin-bottom:20px;">
      {away} @ {home}&nbsp;&nbsp;·&nbsp;&nbsp;{date}
      &nbsp;&nbsp;·&nbsp;&nbsp;{gender} Class {cls} {region}
    </div>

    <div style="display:flex;justify-content:center;gap:40px;margin-bottom:20px;">
      <div>
        <div style="font-size:32px;font-weight:900;color:#fde68a;">{prob_s}</div>
        <div style="font-size:10px;color:rgba(148,163,184,0.55);margin-top:3px;">
          Win Probability
        </div>
      </div>
      <div>
        <div style="font-size:32px;font-weight:900;color:#fde68a;">{margin_s} pts</div>
        <div style="font-size:10px;color:rgba(148,163,184,0.55);margin-top:3px;">
          Projected Margin
        </div>
      </div>
    </div>

    <div style="display:inline-block;background:{conf_color};color:#0f172a;
                font-size:10px;font-weight:900;letter-spacing:.14em;
                text-transform:uppercase;padding:5px 16px;border-radius:999px;">
      {conf}
    </div>

  </div>
</div>
</body></html>"""
        components.html(lock_html, height=310, scrolling=False)

        st.write("")
        st.markdown("#### Other High-Confidence Games This Week")
        other_locks = (
            view[view["FavProb"].notna() & (view["FavProb"] >= 0.80)]
            .sort_values("FavProb", ascending=False)
            .head(8)
        )

        if not other_locks.empty:
            col1, col2 = st.columns(2)
            for i, (_, row) in enumerate(other_locks.iterrows()):
                fp   = row.get("FavProb", 0.5)
                html = game_card_html(row, f"{fp*100:.0f}% confidence", "#10b981")
                with (col1 if i % 2 == 0 else col2):
                    components.html(html, height=132, scrolling=False)

# ── TAB 4 — FULL WEEK SCHEDULE ────────────────────────────────────────

with tab_full:
    st.markdown(f"### 📋 Full Schedule  —  {today.strftime('%b %d')} through {week_end.strftime('%b %d')}")
    st.caption("All upcoming games in your filter window with model projections.")
    st.write("")

    if view.empty:
        st.info("No upcoming games found for this filter combination.")
    else:
        disp = view.copy()

        disp["Win Prob (Home)"] = disp["PredHomeWinProb"].apply(
            lambda p: f"{p*100:.0f}%" if pd.notna(p) else "—"
        )
        disp["Proj. Margin"] = disp["PredMargin"].apply(
            lambda m: f"{abs(m):.1f} pts" if pd.notna(m) else "—"
        )
        disp["Confidence"] = disp["FavProb"].apply(
            lambda p: (
                "Very High" if p >= 0.85 else
                "High"      if p >= 0.70 else
                "Medium"    if p >= 0.58 else
                "Toss-Up"
            ) if pd.notna(p) else "—"
        )

        show_cols = [c for c in [
            "Date", "Away", "Home", "Gender", "HomeClass", "HomeRegion",
            "Favorite", "Proj. Margin", "Win Prob (Home)", "Confidence",
        ] if c in disp.columns]

        st.dataframe(
            disp[show_cols].sort_values("Date"),
            hide_index=True,
            use_container_width=True,
        )

render_footer()
