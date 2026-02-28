from __future__ import annotations

from pathlib import Path
import os
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
    page_title="📅 The Full Slate",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

SHOW_LOCKS = False


def _inject_schedule_css() -> None:
    st.markdown(
        """
        <style>
        .schedule-table { width: 100%; table-layout: fixed; border-collapse: collapse; }
        .schedule-table th,
        .schedule-table td {
            white-space: nowrap; text-overflow: ellipsis; overflow: hidden;
            text-align: center; vertical-align: middle;
        }
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
        th .header-lock { margin-right: 0.25rem; font-size: 0.9rem; vertical-align: middle; color: #f59e0b; }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    # Base data directory: env var in prod, ./data in local dev
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

    # Blank out predictions beyond tomorrow — display layer shows unlock date
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
    """5 stat cards: Games in View, Upcoming, Final, Model Accuracy, Avg Confidence."""

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
        ("🗓️", "Games in View", str(total),       "#60a5fa"),
        ("⏳", "Upcoming",      str(n_upcoming),   "#34d399"),
        ("✅", "Final",         str(n_final),      "#60a5fa"),
        ("🎯", "Model Accuracy", accuracy,         "#60a5fa"),
        ("📊", "Avg Confidence", avg_conf,        "#60a5fa"),
    ]

    card_html = ""
    for icon, label, value, color in cards:
        card_html += f"""
        <div style="
            background: #0d1626;
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 14px;
            padding: 18px 20px 14px;
            flex: 1;
            min-width: 140px;
        ">
            <div style="font-size:11px; font-weight:700; color:rgba(148,163,184,0.7);
                        letter-spacing:.12em; text-transform:uppercase; margin-bottom:6px;">
                {icon} {label}
            </div>
            <div style="font-size:28px; font-weight:900; color:{color}; letter-spacing:-.02em;">
                {value}
            </div>
        </div>"""

    html = f"""
<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0; background:transparent; font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="display:flex; gap:12px; flex-wrap:wrap; padding:4px 0 16px;">
    {card_html}
  </div>
</body></html>"""

    components.html(html, height=110, scrolling=False)


def render_marquee_matchups(df_filtered: pd.DataFrame) -> None:
    """Top 3 highest-confidence upcoming or recent games."""

    phwp = pd.to_numeric(df_filtered.get("PredHomeWinProb"), errors="coerce")
    pred_margin = pd.to_numeric(df_filtered.get("PredMargin"), errors="coerce")
    fav_prob_series = phwp.combine(1.0 - phwp, np.fmax)

    candidates = df_filtered.copy()
    candidates["_conf"] = fav_prob_series
    candidates = candidates.dropna(subset=["_conf", "PredMargin"])
    candidates = candidates[candidates["_conf"] > 0]
    top3 = candidates.nlargest(3, "_conf")

    if top3.empty:
        return

    cards_html = ""
    for _, row in top3.iterrows():
        home = str(row.get("Home", "TBD"))
        away = str(row.get("Away", "TBD"))
        date = str(row.get("Date", ""))
        pm = float(row.get("PredMargin", 0))
        conf = float(row.get("_conf", 0.5)) * 100
        fav = home if pm > 0 else away
        spread = f"{abs(pm):.1f}"

        cards_html += f"""
        <div style="
            background: #0d1626;
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 14px;
            padding: 16px 18px;
            flex: 1;
            min-width: 220px;
        ">
            <div style="font-size:11px;font-weight:800;color:rgba(245,158,11,0.85);
                        letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">
                🔥 Marquee Matchup
            </div>
            <div style="font-size:15px;font-weight:800;color:#f1f5f9;margin-bottom:4px;">
                {away} @ {home}
            </div>
            <div style="font-size:11px;color:rgba(203,213,225,0.6);margin-bottom:10px;">
                {date} &nbsp;·&nbsp; Spread: -{spread} &nbsp;·&nbsp; {conf:.0f}% confidence
            </div>
            <div style="font-size:12px;color:rgba(148,163,184,0.7);">
                Favorite: <span style="color:#fde68a;font-weight:700;">{fav}</span>
            </div>
        </div>"""

    html = f"""
<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0; background:transparent; font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="font-size:16px;font-weight:900;color:#f1f5f9;margin-bottom:12px;padding-top:4px;">
    🔥 Marquee Matchups
  </div>
  <div style="display:flex; gap:12px; flex-wrap:wrap; padding-bottom:8px;">
    {cards_html}
  </div>
</body></html>"""

    components.html(html, height=175, scrolling=False)


def _format_locked_value(kind: str, unlock_date: dt.date | None = None) -> str:
    if unlock_date:
        date_str = unlock_date.strftime("🔒 Unlocks %a %b %-d")
    else:
        date_str = "🔒 Coming Soon"
    return f"<div class='pill-base lock-pill'>{date_str}</div>"


def _format_unlocked_value(kind: str, value: float | None) -> str:
    if value is None or pd.isna(value):
        return ""
    label_val = f"{value:+.1f}" if kind == "spread" else f"{value:.1f}%"
    return f"<div class='pill-base value-pill'>{label_val}</div>"


def add_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    is_sub = st.session_state.get("is_subscriber", False)
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
    st.markdown("### Schedule")
    st.caption("Filter by Team, switch Status between Upcoming/Final, and use date range for deeper digging.")

    df2 = display_df.copy()

    if SHOW_LOCKS and (not st.session_state.get("is_subscriber", False)):
        rename_map = {
            "Spread": "<span class='header-lock'>🔒</span>Spread",
            "Confidence": "<span class='header-lock'>🔒</span>Confidence",
        }
    else:
        rename_map = {"Spread": "Spread", "Confidence": "Confidence"}

    df2 = df2.rename(columns=rename_map)
    html = df2.to_html(escape=False, index=False, classes="schedule-table")
    html = html.replace("<th ", "<th style=\"padding: 0.25rem 0.55rem; font-size: 0.8rem;\" ")
    html = html.replace("<td ", "<td style=\"padding: 0.25rem 0.55rem; font-size: 0.8rem;\" ")
    st.markdown(html, unsafe_allow_html=True)

    if SHOW_LOCKS and (not st.session_state.get("is_subscriber", False)):
        st.info("🔒 Spread + Confidence are locked previews for non‑subscribers.")


def main() -> None:
    apply_global_layout_tweaks()
    _inject_schedule_css()

    render_logo()
    render_page_header(
        title="📅 The Full Slate",
        definition="Schedules (n.): The nightly slate of game with 🧠The Model baked in",
        subtitle="Every game, time and place, plus context that explains what you're seeing.",
    )
    st.write("")

    df_all = load_schedule_data()
    df_filtered = apply_schedule_filters(df_all.copy())

    render_marquee_matchups(df_filtered)
    render_stat_cards(df_all, df_filtered)
    render_schedules_filters()

    display_df = add_display_columns(df_filtered)
    render_schedule_table(display_df)

    render_footer()


if __name__ == "__main__":
    main()
