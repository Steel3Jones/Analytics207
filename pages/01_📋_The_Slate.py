from __future__ import annotations


from pathlib import Path
import os
import datetime as dt


import numpy as np
import pandas as pd
import streamlit as st

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
    page_title="📅 The Full Slate",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)


SHOW_LOCKS = True



def _inject_schedule_css() -> None:
    st.markdown("""
<style>
/* ── SECTION PILL HEADS ── */
.sl-section-head {
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
    margin-top: 1.2rem;
}

/* ── HERO STAT ROW ── */
.sl-hero {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 0.4rem;
}
.sl-hero-stat {
    flex: 1;
    min-width: 110px;
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.16);
    border-radius: 12px;
    padding: 0.85rem 0.9rem;
    text-align: center;
}
.sl-hero-val {
    font-size: 1.75rem;
    font-weight: 900;
    line-height: 1.1;
    letter-spacing: -0.02em;
}
.sl-hero-lbl {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: #64748b;
    margin-top: 3px;
}

/* ── MARQUEE CARDS ── */
.sl-marquee-grid {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 0.4rem;
}
.sl-marquee-card {
    flex: 1;
    min-width: 220px;
    background: radial-gradient(circle at top left, #1c1400, #080f1e);
    border: 1px solid rgba(245,158,11,0.25);
    border-radius: 14px;
    padding: 1rem 1.1rem;
}
.sl-marquee-tag {
    font-size: 0.65rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #f59e0b;
    margin-bottom: 6px;
}
.sl-marquee-matchup {
    font-size: 1.0rem;
    font-weight: 800;
    color: #fef3c7;
    margin-bottom: 4px;
}
.sl-marquee-meta {
    font-size: 0.76rem;
    color: #78716c;
    margin-bottom: 8px;
}
.sl-marquee-fav {
    font-size: 0.78rem;
    color: #94a3b8;
}

/* ── SCHEDULE TABLE CARD ── */
.sl-table-wrap {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.18);
    border-radius: 14px;
    padding: 0.85rem 0.85rem 0.5rem;
    overflow-x: auto;
    margin-bottom: 1rem;
}
.sl-table {
    width: 100%;
    border-collapse: collapse;
    min-width: 580px;
    font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
}
.sl-table th {
    padding: 0.28rem 0.55rem;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: #60a5fa;
    background: rgba(9,14,28,0.9);
    border-bottom: 2px solid rgba(96,165,250,0.30);
    text-align: left;
    white-space: nowrap;
    font-weight: 700;
}
.sl-table td {
    padding: 0.30rem 0.55rem;
    font-size: 0.82rem;
    color: #e2e8f0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    white-space: nowrap;
}
.sl-table tr:hover td { background: rgba(96,165,250,0.04); }
.sl-table .td-center { text-align: center; }
.sl-table .td-muted  { color: #64748b; font-size: 0.78rem; }
.sl-table .td-winner { color: #4ade80; font-weight: 700; }
.sl-table .td-date   { color: #94a3b8; font-size: 0.78rem; }

/* ── PILL BADGES ── */
.pill-base {
    display: inline-flex; align-items: center; justify-content: center;
    padding: 0.05rem 0.45rem; border-radius: 999px;
    font-size: 0.72rem; line-height: 1; font-weight: 700; min-width: 3.0rem;
}
.lock-pill {
    background: rgba(245,158,11,0.12);
    border: 1px solid rgba(245,158,11,0.65);
    color: #fbbf24;
    min-width: 7rem;
    font-size: 0.65rem;
    letter-spacing: .04em;
}
.value-pill { background: rgba(148,163,184,0.10); border: 1px solid rgba(148,163,184,0.35); color: #e5e7eb; }
</style>
""", unsafe_allow_html=True)


def _section_header(icon: str, label: str) -> None:
    st.markdown(f'<div class="sl-section-head">{icon} {label}</div>', unsafe_allow_html=True)



def render_schedules_filters() -> None:
    cols = st.columns(5)
    with cols[0]:
        st.selectbox("Gender", ["Boys", "Girls"], index=0, key="gender")
    with cols[1]:
        st.selectbox("Class", ["All", "A", "B", "C", "D", "S"], index=0, key="class")
    with cols[2]:
        st.selectbox("Region", ["All", "North", "South"], index=0, key="region")
    with cols[3]:
        st.selectbox("Status", ["Upcoming", "Final", "All"], index=1, key="status")
    with cols[4]:
        st.text_input("Team (optional)", value="", key="team_query", placeholder="Type a school name")
    with st.expander("Date range (optional)", expanded=False):
        rcols = st.columns(2)
        with rcols[0]:
            st.date_input("Start", value=None, key="date_start")
        with rcols[1]:
            st.date_input("End", value=None, key="date_end")



def _clean_gameids(s: pd.Series) -> pd.Series:
    x = s.astype(str).str.strip()
    x = x.str.replace(r"\.0$", "", regex=True)
    x = x.str.replace(",", "", regex=True)
    return x



@st.cache_data(ttl=3600)
def load_schedule_data() -> pd.DataFrame:
    project_root = Path(__file__).resolve().parent.parent
    data_dir = Path(os.environ.get("DATA_DIR", project_root / "data"))


    core_path = data_dir / "core" / "games_game_core_v50.parquet"
    pred_path = data_dir / "predictions" / "games_predictions_current.parquet"


    games = pd.read_parquet(core_path)
    preds = pd.read_parquet(pred_path)


    if "GameID" not in games.columns:
        raise RuntimeError(f"Core parquet missing GameID: {core_path}")
    if "GameID" not in preds.columns:
        raise RuntimeError(f"Preds parquet missing GameID: {pred_path}")


    games = games.copy()
    preds = preds.copy()


    games["GameID"] = _clean_gameids(games["GameID"])
    preds["GameID"] = _clean_gameids(preds["GameID"])


    drop_if_present = [
        "PredHomeWinProb", "PredMargin", "PredHomeScore", "PredAwayScore",
        "PredTotalPoints", "FavoriteIsHome", "FavoriteTeamKey", "FavProb",
        "ModelCorrect", "ActualMargin", "CoreVersion",
    ]
    games = games.drop(columns=[c for c in drop_if_present if c in games.columns], errors="ignore")


    required_pred = ["GameID", "PredHomeWinProb", "PredMargin"]
    missing = [c for c in required_pred if c not in preds.columns]
    if missing:
        raise RuntimeError(f"Preds parquet missing columns {missing}: {pred_path}")


    pred_cols = required_pred + (["CoreVersion"] if "CoreVersion" in preds.columns else [])
    preds = preds[pred_cols].drop_duplicates(subset=["GameID"], keep="first")


    df = games.merge(preds, on="GameID", how="left")


    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].astype(str).str.strip().str.title()
        df = df[df["Gender"].isin(["Boys", "Girls"])]
    for col in ["Home", "Away", "HomeClass", "AwayClass", "HomeRegion", "AwayRegion"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "Played" in df.columns:
        df["Played"] = df["Played"].astype("boolean")
    for col in ["PredHomeWinProb", "PredMargin"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


    return df.reset_index(drop=True)



def apply_schedule_filters(df: pd.DataFrame) -> pd.DataFrame:
    gender = st.session_state.get("gender", "Boys")
    cls = st.session_state.get("class", "All")
    region = st.session_state.get("region", "All")
    status = st.session_state.get("status", "Final")
    team_query = (st.session_state.get("team_query") or "").strip().lower()


    if "Gender" in df.columns:
        df = df[df["Gender"] == gender]
    if cls != "All" and "HomeClass" in df.columns:
        df = df[df["HomeClass"] == cls]
    if region != "All" and "HomeRegion" in df.columns:
        df = df[df["HomeRegion"] == region]


    if "Played" in df.columns and "Date" in df.columns:
        is_final = df["Played"].fillna(False)
        today = dt.date.today()
        if status == "Upcoming":
            df = df[(~is_final) & (df["Date"] >= today)]
        elif status == "Final":
            df = df[is_final]


    d0 = st.session_state.get("date_start")
    d1 = st.session_state.get("date_end")
    if d0:
        df = df[df["Date"] >= d0]
    if d1:
        df = df[df["Date"] <= d1]


    if team_query and "Home" in df.columns and "Away" in df.columns:
        df = df[
            df["Home"].str.lower().str.contains(team_query)
            | df["Away"].str.lower().str.contains(team_query)
        ]


    df = df.sort_values("Date", ascending=(status != "Final"))
    df = df.reset_index(drop=True)


    today = dt.date.today()
    tomorrow = today + dt.timedelta(days=1)
    if "Date" in df.columns:
        future_mask = df["Date"].apply(
            lambda d: pd.Timestamp(d).date() > tomorrow if pd.notna(d) else False
        )
        for col in ["PredMargin", "PredHomeWinProb"]:
            if col in df.columns:
                df.loc[future_mask, col] = np.nan


    return df



def render_stat_cards(df_all: pd.DataFrame, df_filtered: pd.DataFrame) -> None:
    total = len(df_filtered)
    played = df_filtered["Played"].fillna(False).astype(bool) if "Played" in df_filtered.columns else pd.Series(False, index=df_filtered.index)
    n_final = int(played.sum())
    n_upcoming = int((~played).sum())

    pred_margin = pd.to_numeric(df_filtered.get("PredMargin"), errors="coerce")
    home_scores = pd.to_numeric(df_filtered.get("HomeScore"), errors="coerce")
    away_scores = pd.to_numeric(df_filtered.get("AwayScore"), errors="coerce")
    actual_margin = home_scores - away_scores

    finals_mask = played & pred_margin.notna() & actual_margin.notna()
    if finals_mask.sum() > 0:
        correct = np.where(
            pred_margin[finals_mask] > 0, actual_margin[finals_mask] > 0,
            np.where(pred_margin[finals_mask] < 0, actual_margin[finals_mask] < 0, False)
        )
        accuracy = f"{correct.mean() * 100:.1f}%"
    else:
        accuracy = "—"

    phwp = pd.to_numeric(df_filtered.get("PredHomeWinProb"), errors="coerce")
    fav_prob = np.where(
        np.isfinite(phwp.to_numpy(dtype=float)),
        np.maximum(phwp.to_numpy(dtype=float), 1.0 - phwp.to_numpy(dtype=float)), np.nan)
    valid_conf = fav_prob[~np.isnan(fav_prob)]
    avg_conf = f"{valid_conf.mean() * 100:.0f}%" if len(valid_conf) > 0 else "—"

    cards = [
        ("Games", str(total),      "#60a5fa"),
        ("Upcoming", str(n_upcoming), "#34d399"),
        ("Final",    str(n_final),    "#60a5fa"),
        ("Accuracy", accuracy,        "#a78bfa"),
        ("Avg Conf", avg_conf,        "#f59e0b"),
    ]

    inner = "".join(
        f'<div class="sl-hero-stat">'
        f'<div class="sl-hero-val" style="color:{col};">{val}</div>'
        f'<div class="sl-hero-lbl">{lbl}</div>'
        f'</div>'
        for lbl, val, col in cards
    )
    st.markdown(f'<div class="sl-hero">{inner}</div>', unsafe_allow_html=True)



def render_marquee_matchups(df_all: pd.DataFrame, gender: str) -> None:
    today = dt.date.today()
    season_over = False

    pool = pd.DataFrame()
    if "Date" in df_all.columns and "Played" in df_all.columns:
        upcoming = df_all[
            (df_all["Played"].fillna(True) == False) &
            (df_all["Date"] >= today) &
            (df_all["Gender"] == gender)
        ].copy()
        if upcoming.empty:
            # Season over — fall back to most recent played games
            season_over = True
            pool = df_all[
                (df_all["Played"].fillna(False) == True) &
                (df_all["Gender"] == gender)
            ].copy()
            if "Date" in pool.columns:
                last_date = pool["Date"].max()
                pool = pool[pool["Date"] == last_date]
        else:
            pool = upcoming

    if pool.empty:
        return

    phwp = pd.to_numeric(pool.get("PredHomeWinProb"), errors="coerce")
    pred_margin = pd.to_numeric(pool.get("PredMargin"), errors="coerce")
    fav_prob_series = phwp.combine(1.0 - phwp, np.fmax)

    candidates = pool.copy()
    candidates["_conf"] = fav_prob_series
    candidates = candidates.dropna(subset=["_conf", "PredMargin"])
    candidates = candidates[candidates["_conf"] > 0]
    top3 = candidates.nlargest(3, "_conf")

    if top3.empty:
        return

    if season_over:
        _section_header("🏆", "Season Highlights")
    else:
        _section_header("🔥", "Marquee Matchups")

    cards_html = ""
    for _, row in top3.iterrows():
        home  = str(row.get("Home", "TBD"))
        away  = str(row.get("Away", "TBD"))
        d     = row.get("Date")
        date_s = d.strftime("%a %b %d").replace(" 0", " ") if pd.notna(d) and hasattr(d, "strftime") else str(d)
        pm    = float(row.get("PredMargin", 0))
        conf  = float(row.get("_conf", 0.5)) * 100
        fav   = home if pm > 0 else away
        spread = f"{abs(pm):.1f}"
        conf_col = "#4ade80" if conf >= 80 else ("#f59e0b" if conf >= 70 else "#94a3b8")

        tag_label = "🏆 Season Highlight" if season_over else "🔥 Marquee Matchup"
        cards_html += (
            f'<div class="sl-marquee-card">'
            f'<div class="sl-marquee-tag">{tag_label}</div>'
            f'<div class="sl-marquee-matchup">{away} @ {home}</div>'
            f'<div class="sl-marquee-meta">{date_s} &nbsp;·&nbsp; Spread: -{spread} &nbsp;·&nbsp; '
            f'<span style="color:{conf_col};font-weight:700;">{conf:.0f}% confidence</span></div>'
            f'<div class="sl-marquee-fav">Favorite: <strong style="color:#fde68a;">{fav}</strong></div>'
            f'</div>'
        )

    st.markdown(f'<div class="sl-marquee-grid">{cards_html}</div>', unsafe_allow_html=True)



def _format_locked_value(kind: str, unlock_date: dt.date | None = None) -> str:
    if unlock_date:
        date_str = ("🔒 Unlocks " + unlock_date.strftime("%a %b %d").replace(" 0", " "))
    else:
        date_str = "🔒 Subscribe to Unlock"
    return f"<div class='pill-base lock-pill'>{date_str}</div>"



def _format_unlocked_value(kind: str, value: float | None) -> str:
    if value is None or pd.isna(value):
        return ""
    label_val = f"{value:+.1f}" if kind == "spread" else f"{value:.1f}%"
    return f"<div class='pill-base value-pill'>{label_val}</div>"



def add_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    is_sub = is_subscribed()
    lock_it = SHOW_LOCKS and (not is_sub)


    today = dt.date.today()
    tomorrow = today + dt.timedelta(days=1)


    def _should_lock(game_date) -> bool:
        if game_date is None or pd.isna(game_date):
            return False
        return pd.Timestamp(game_date).date() > tomorrow


    def _unlock_date(game_date) -> dt.date | None:
        if game_date is None or pd.isna(game_date):
            return None
        return pd.Timestamp(game_date).date()


    out = pd.DataFrame()
    out["Date"] = df.get("Date")


    home = df.get("Home")
    away = df.get("Away")
    out["Home"] = home.fillna("") if home is not None else ""
    out["Away"] = away.fillna("") if away is not None else ""


    pred_margin = pd.to_numeric(df.get("PredMargin"), errors="coerce")
    phwp = pd.to_numeric(df.get("PredHomeWinProb"), errors="coerce")


    def _favorite(pm, ht, at):
        if pm is None or pd.isna(pm): return ""
        if pm > 0: return ht
        if pm < 0: return at
        return "Pick'em"


    out["Favorite"] = [
        _favorite(pm, ht, at)
        for pm, ht, at in zip(pred_margin, out["Home"], out["Away"], strict=False)
    ]


    fav_prob = np.where(
        np.isfinite(phwp.to_numpy(dtype=float)),
        np.maximum(phwp.to_numpy(dtype=float), 1.0 - phwp.to_numpy(dtype=float)),
        np.nan,
    )


    dates = df.get("Date", pd.Series([None] * len(df)))


    if lock_it:
        out["Spread"] = [_format_locked_value("spread") for _ in dates]
        out["Confidence"] = [_format_locked_value("confidence") for _ in dates]
    else:
        out["Spread"] = [
            _format_locked_value("spread", _unlock_date(d))
            if _should_lock(d) else _format_unlocked_value("spread", v)
            for d, v in zip(dates, pred_margin)
        ]
        out["Confidence"] = [
            _format_locked_value("confidence", _unlock_date(d))
            if _should_lock(d) else _format_unlocked_value("confidence", (p * 100.0) if np.isfinite(p) else None)
            for d, p in zip(dates, fav_prob)
        ]


    home_scores = pd.to_numeric(df.get("HomeScore"), errors="coerce")
    away_scores = pd.to_numeric(df.get("AwayScore"), errors="coerce")


    out["Final score"] = [
        f"{int(h)}–{int(a)}" if pd.notna(h) and pd.notna(a) else ""
        for h, a in zip(home_scores, away_scores, strict=False)
    ]


    out["Winner"] = [
        (ht if h > a else (at if a > h else "Tie")) if pd.notna(h) and pd.notna(a) else ""
        for ht, at, h, a in zip(out["Home"], out["Away"], home_scores, away_scores, strict=False)
    ]


    played = df.get("Played")
    played_bool = played.fillna(False).astype(bool) if played is not None else pd.Series(False, index=df.index)
    actual_margin = home_scores - away_scores
    model_correct = np.where(
        played_bool.to_numpy(),
        np.where(
            pred_margin.to_numpy() > 0, actual_margin.to_numpy() > 0,
            np.where(pred_margin.to_numpy() < 0, actual_margin.to_numpy() < 0, np.nan)
        ),
        np.nan,
    )


    out["Model"] = [
        ("✅" if bool(v) else "❌") if (v is not None and not (isinstance(v, float) and np.isnan(v))) else ""
        for v in model_correct
    ]


    return out



def render_schedule_table(display_df: pd.DataFrame) -> None:
    _section_header("📋", "Schedule")

    locked = SHOW_LOCKS and (not is_subscribed())
    spread_hdr  = "🔒 Spread"     if locked else "Spread"
    conf_hdr    = "🔒 Confidence" if locked else "Confidence"

    cols = ["Date", "Away", "Home", "Favorite", spread_hdr, conf_hdr, "Final score", "Winner", "Model"]
    df2  = display_df.rename(columns={"Spread": spread_hdr, "Confidence": conf_hdr})

    # Build thead
    th_s = "padding:0.28rem 0.55rem;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.10em;color:#60a5fa;background:rgba(9,14,28,0.9);border-bottom:2px solid rgba(96,165,250,0.30);white-space:nowrap;font-weight:700;"
    thead = "".join(f'<th style="{th_s}">{c}</th>' for c in cols if c in df2.columns)

    # Build tbody
    rows_html = ""
    for _, row in df2.iterrows():
        row_style = "border-bottom:1px solid rgba(255,255,255,0.04);"
        td = lambda val, extra="": f'<td style="padding:0.30rem 0.55rem;font-size:0.82rem;color:#e2e8f0;{extra}">{val}</td>'

        date_val    = row.get("Date", "")
        away_val    = row.get("Away", "")
        home_val    = row.get("Home", "")
        fav_val     = row.get("Favorite", "")
        spread_val  = row.get(spread_hdr, "")
        conf_val    = row.get(conf_hdr, "")
        score_val   = row.get("Final score", "")
        winner_val  = row.get("Winner", "")
        model_val   = row.get("Model", "")

        cells = (
            td(date_val,   "color:#94a3b8;font-size:0.78rem;")
            + td(away_val)
            + td(home_val)
            + td(f'<span style="color:#fde68a;font-weight:600;">{fav_val}</span>' if fav_val else "")
            + td(spread_val,  "text-align:center;")
            + td(conf_val,    "text-align:center;")
            + td(score_val,   "color:#94a3b8;font-size:0.80rem;text-align:center;")
            + td(f'<span style="color:#4ade80;font-weight:700;">{winner_val}</span>' if winner_val else "",
                 "text-align:center;")
            + td(model_val,   "text-align:center;font-size:0.90rem;")
        )
        rows_html += f'<tr style="{row_style}">{cells}</tr>'

    html = (
        f'<div class="sl-table-wrap">'
        f'<table class="sl-table" style="width:100%;border-collapse:collapse;min-width:580px;">'
        f'<thead><tr>{thead}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    if locked:
        st.markdown(
            '<div style="font-size:0.80rem;color:#78716c;margin-top:0.4rem;">'
            '🔒 Spread &amp; Confidence unlock with a subscription.</div>',
            unsafe_allow_html=True,
        )


def main() -> None:
    apply_global_layout_tweaks()
    _inject_schedule_css()

    user = login_gate(required=False)
    logout_button()

    render_logo()

    render_page_header(
        title="📅 The Full Slate",
        definition="Schedules (n.): The nightly slate of game with 🧠The Model baked in",
        subtitle="Every game, time and place, plus context that explains what you're seeing.",
    )
    st.write("")

    df_all = load_schedule_data()
    df_filtered = apply_schedule_filters(df_all.copy())

    _section_header("📊", "At a Glance")
    render_stat_cards(df_all, df_filtered)

    gender = st.session_state.get("gender", "Boys")
    if is_subscribed():
        render_marquee_matchups(df_all, gender)
    else:
        _section_header("🔥", "Marquee Matchups")
        st.markdown(
            '<div style="background:radial-gradient(circle at top left,#1c1400,#080f1e);'
            'border:1px solid rgba(245,158,11,0.20);border-radius:14px;'
            'padding:1.1rem 1.3rem;color:#78716c;font-size:0.88rem;">'
            '🔒 Top confidence games coming up — subscriber only.</div>',
            unsafe_allow_html=True,
        )

    _section_header("🎛️", "Filters")
    render_schedules_filters()

    display_df = add_display_columns(df_filtered)
    render_schedule_table(display_df)

    render_footer()


if __name__ == "__main__":
    main()

