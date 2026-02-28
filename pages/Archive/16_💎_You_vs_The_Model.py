# 16_💎_You_vs_The_Model_v30.py — CROWD vs THE MODEL (v30) — FULL PAGE (fixed)
from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
    spacer,
)

from components.cards import inject_card_css, render_card


# ----------------------------
# INLINE FIGHT CARD (auto-height)
# ----------------------------
def _fmt_pct(x) -> str:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "—"
        return f"{float(x):.1f}%"
    except Exception:
        return "—"


def _fmt_num(x, decimals: int = 2) -> str:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "—"
        return f"{float(x):.{decimals}f}"
    except Exception:
        return "—"


def _fmt_int(x) -> str:
    try:
        if x is None:
            return "—"
        return f"{int(x)}"
    except Exception:
        return "—"


def _fmt_dt(x) -> str:
    if x is None or pd.isna(x):
        return "—"
    try:
        return pd.Timestamp(x).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(x)


def render_fight_card_inline(
    *,
    model_acc,
    model_total_games,
    model_upset_rate,
    model_brier,
    model_mae,
    crowd_managers,
    crowd_submissions,
    crowd_weeks,
    crowd_last_submit,
    status_ribbon: str = "Locked: awaiting Game Day votes",
    cta_text: str = "Vote on Game Day + play Pick‑5 to power the CROWD score",
    belt_left: str = "CROWD BELT",
    belt_right: str = "Unlocks when poll votes are logged per game (GameID)",
) -> None:
    html = f"""
<style>
.a207-fightcard {{
  background: #0b1220;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  padding: 18px 18px 16px 18px;
  position: relative;
  overflow: hidden;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}}

.a207-fightcard:before {{
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(900px 300px at 15% 0%, rgba(245,158,11,0.14), transparent 60%),
              radial-gradient(900px 300px at 85% 0%, rgba(59,130,246,0.14), transparent 60%);
  pointer-events: none;
}}

.a207-fightgrid {{
  display: grid;
  grid-template-columns: 1fr 220px 1fr;
  gap: 14px;
  position: relative;
  z-index: 1;
}}

@media (max-width: 980px) {{
  .a207-fightgrid {{ grid-template-columns: 1fr; }}
  .a207-vs {{ order: -1; }}
}}

.a207-side {{
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 14px 14px 12px 14px;
}}

.a207-kicker {{
  color: rgba(203,213,225,0.92);
  font-size: 12px;
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: 6px;
}}

.a207-title {{
  color: #e5e7eb;
  font-size: 28px;
  font-weight: 800;
  line-height: 1.05;
  margin-bottom: 6px;
}}

.a207-sub {{
  color: rgba(203,213,225,0.92);
  font-size: 13px;
  margin-bottom: 10px;
}}

.a207-metrics {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
}}

.a207-metric {{
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 10px 10px 9px 10px;
}}

.a207-metric-label {{
  color: rgba(156,163,175,0.92);
  font-size: 12px;
  margin-bottom: 4px;
}}

.a207-metric-value {{
  color: #e5e7eb;
  font-size: 16px;
  font-weight: 700;
}}

.a207-vs {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 8px;
  border-radius: 16px;
  border: 1px dashed rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.02);
}}

.a207-vs-big {{
  font-size: 46px;
  font-weight: 900;
  line-height: 1;
  background: linear-gradient(90deg, #fbbf24, #f59e0b, #fb7185);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin-bottom: 8px;
}}

.a207-ribbon {{
  font-size: 12px;
  color: rgba(226,232,240,0.95);
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(15,23,42,0.55);
  margin-bottom: 8px;
  text-align: center;
}}

.a207-cta {{
  font-size: 12px;
  color: rgba(203,213,225,0.92);
  text-align: center;
}}

.a207-belt {{
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.06);
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: space-between;
  position: relative;
  z-index: 1;
}}

.a207-belt-left {{
  color: rgba(226,232,240,0.95);
  font-weight: 700;
}}

.a207-belt-right {{
  color: rgba(148,163,184,0.95);
  font-size: 12px;
}}
</style>

<div class="a207-fightcard" id="a207FightCard">
  <div class="a207-fightgrid">
    <div class="a207-side">
      <div class="a207-kicker">THE MODEL</div>
      <div class="a207-title">{_fmt_pct(model_acc)}</div>
      <div class="a207-sub">Season accuracy on {_fmt_int(model_total_games)} games</div>
      <div class="a207-metrics">
        <div class="a207-metric">
          <div class="a207-metric-label">Upset rate</div>
          <div class="a207-metric-value">{_fmt_pct(model_upset_rate)}</div>
        </div>
        <div class="a207-metric">
          <div class="a207-metric-label">Brier (↓ better)</div>
          <div class="a207-metric-value">{_fmt_num(model_brier, 3)}</div>
        </div>
        <div class="a207-metric">
          <div class="a207-metric-label">MAE (pts)</div>
          <div class="a207-metric-value">{_fmt_num(model_mae, 2)}</div>
        </div>
        <div class="a207-metric">
          <div class="a207-metric-label">Edge status</div>
          <div class="a207-metric-value">Active</div>
        </div>
      </div>
    </div>

    <div class="a207-vs">
      <div class="a207-vs-big">VS</div>
      <div class="a207-ribbon">{status_ribbon}</div>
      <div class="a207-cta">{cta_text}</div>
    </div>

    <div class="a207-side">
      <div class="a207-kicker">THE CROWD</div>
      <div class="a207-title">{_fmt_int(crowd_managers)} managers</div>
      <div class="a207-sub">{_fmt_int(crowd_submissions)} Pick‑5 submissions • {_fmt_int(crowd_weeks)} weeks</div>
      <div class="a207-metrics">
        <div class="a207-metric">
          <div class="a207-metric-label">Last submit</div>
          <div class="a207-metric-value">{_fmt_dt(crowd_last_submit)}</div>
        </div>
        <div class="a207-metric">
          <div class="a207-metric-label">Crowd score</div>
          <div class="a207-metric-value">Locked</div>
        </div>
        <div class="a207-metric">
          <div class="a207-metric-label">Upset hunting</div>
          <div class="a207-metric-value">Soon</div>
        </div>
        <div class="a207-metric">
          <div class="a207-metric-label">Head-to-head</div>
          <div class="a207-metric-value">Soon</div>
        </div>
      </div>
    </div>
  </div>

  <div class="a207-belt">
    <div class="a207-belt-left">{belt_left}</div>
    <div class="a207-belt-right">{belt_right}</div>
  </div>
</div>

<script>
  const sendHeight = () => {{
    const h = document.documentElement.scrollHeight || document.body.scrollHeight;
    window.parent.postMessage({{ type: "streamlit:setFrameHeight", height: h }}, "*");
  }};
  window.addEventListener("load", sendHeight);
  window.addEventListener("resize", sendHeight);
  setTimeout(sendHeight, 50);
  setTimeout(sendHeight, 250);
</script>
    """
    components.html(html, height=380, scrolling=False)


# ----------------------------
# SPLIT CARD (direct markdown render)
# ----------------------------
def inject_split_card_css() -> None:
    st.markdown(
        """
<style>
.a207-split-wrap{
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.08);
  background: #0b1220;
  padding: 12px 12px 12px 12px;
  position: relative;
  overflow: hidden;
}
.a207-split-wrap::before{
  content:"";
  position:absolute;
  inset:0;
  background: radial-gradient(900px 260px at 18% 0%, rgba(16,185,129,0.12), transparent 60%),
              radial-gradient(900px 260px at 82% 0%, rgba(59,130,246,0.12), transparent 60%);
  pointer-events:none;
}
.a207-split-head{
  position: relative;
  z-index: 1;
  font-size: 12px;
  font-weight: 950;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(226,232,240,0.92);
  margin: 0 0 10px 2px;
}
.a207-split-grid{
  position: relative;
  z-index: 1;
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 1100px){
  .a207-split-grid{ grid-template-columns: 1fr; }
}
.a207-split-side{
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.07);
  background: rgba(255,255,255,0.02);
  padding: 12px 12px;
  min-height: 110px;
  position: relative;
  overflow: hidden;
}
.a207-split-side.model::after{
  content:"";
  position:absolute;
  inset:-150px -160px auto auto;
  width:360px; height:360px;
  background: radial-gradient(circle at 30% 30%, rgba(16,185,129,0.18), rgba(0,0,0,0) 62%);
}
.a207-split-side.crowd::after{
  content:"";
  position:absolute;
  inset:-150px -160px auto auto;
  width:360px; height:360px;
  background: radial-gradient(circle at 30% 30%, rgba(59,130,246,0.18), rgba(0,0,0,0) 62%);
}
.a207-split-kicker{
  position: relative;
  z-index: 1;
  font-size: 11px;
  font-weight: 950;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(148,163,184,0.92);
}
.a207-split-big{
  position: relative;
  z-index: 1;
  margin-top: 8px;
  font-size: 30px;
  font-weight: 1000;
  letter-spacing: -0.04em;
  color: rgba(248,250,252,0.98);
  font-variant-numeric: tabular-nums;
  line-height: 1.05;
}
.a207-split-sub{
  position: relative;
  z-index: 1;
  margin-top: 6px;
  font-size: 13px;
  color: rgba(148,163,184,0.92);
  line-height: 1.35;
}
.a207-bar{
  position: relative;
  z-index: 1;
  margin-top: 10px;
  height: 10px;
  border-radius: 999px;
  background: rgba(148,163,184,0.18);
  overflow:hidden;
}
.a207-fill{
  height: 100%;
  border-radius: 999px;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_split_card(
    *,
    title: str,
    model_value: str,
    model_sub: str,
    model_progress: float | None,
    crowd_value: str,
    crowd_sub: str,
    crowd_progress: float | None,
) -> None:
    def _bar(fill: float | None, color: str) -> str:
        if fill is None:
            return ""
        f = max(0.0, min(1.0, float(fill)))
        return f"""
<div class="a207-bar">
  <div class="a207-fill" style="width:{f*100:.1f}%; background:{color};"></div>
</div>"""

    html = f"""
<div class="a207-split-wrap">
  <div class="a207-split-head">{title}</div>
  <div class="a207-split-grid">
    <div class="a207-split-side model">
      <div class="a207-split-kicker">THE MODEL</div>
      <div class="a207-split-big">{model_value}</div>
      <div class="a207-split-sub">{model_sub}</div>
      {_bar(model_progress, "#10b981")}
    </div>
    <div class="a207-split-side crowd">
      <div class="a207-split-kicker">THE CROWD</div>
      <div class="a207-split-big">{crowd_value}</div>
      <div class="a207-split-sub">{crowd_sub}</div>
      {_bar(crowd_progress, "#3b82f6")}
    </div>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


# ----------------------------
# HELPERS: rolling/season accuracy  (FIX for NameError)
# ----------------------------
def _rolling_acc_from_correct(df: pd.DataFrame, correct_col: str, window: int) -> float:
    if df is None or df.empty or correct_col not in df.columns:
        return np.nan
    g = df.copy()
    if "Date" in g.columns:
        g["Date"] = pd.to_datetime(g["Date"], errors="coerce")
        g = g.sort_values("Date")
    s = pd.to_numeric(g[correct_col], errors="coerce").fillna(0).astype(int)
    if len(s) == 0:
        return np.nan
    return float(s.rolling(window=window, min_periods=1).mean().iloc[-1] * 100.0)


def _season_acc_from_correct(df: pd.DataFrame, correct_col: str) -> float:
    if df is None or df.empty or correct_col not in df.columns:
        return np.nan
    s = pd.to_numeric(df[correct_col], errors="coerce").fillna(0).astype(int)
    if len(s) == 0:
        return np.nan
    return float(s.mean() * 100.0)


# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="🧠 You vs The Model (v30) – Analytics207.com",
    page_icon="🧠",
    layout="wide",
)
apply_global_layout_tweaks()
render_logo()
render_page_header(
    title="🧠 YOU vs THE MODEL",
    definition="Crowd vs THE MODEL (n.): a season-long head-to-head between fan instincts and model math.",
    subtitle="Drive participation: vote on Game Day + play Pick‑5 to build the CROWD score.",
)

inject_card_css()
inject_split_card_css()
st.divider()

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

PERF_SUMMARY_FILE = DATA_DIR / "performance_summary_v30.parquet"
PERF_GAMES_FILE = DATA_DIR / "performance_games_v30.parquet"
PICK5_SUBMISSIONS_FILE = DATA_DIR / "fantasy_rosters.csv"
PICK5_WINNERS_FILE = DATA_DIR / "pick5_weekly_winners_v26.parquet"
POLL_VOTES_CURRENT_FILE = DATA_DIR / "poll_votes_current.parquet"


# ----------------------------
# LOADERS
# ----------------------------
@st.cache_data(ttl=600, show_spinner=False)
def load_perf_summary() -> pd.DataFrame:
    if not PERF_SUMMARY_FILE.exists():
        return pd.DataFrame()
    return pd.read_parquet(PERF_SUMMARY_FILE).copy()


@st.cache_data(ttl=600, show_spinner=False)
def load_perf_games() -> pd.DataFrame:
    if not PERF_GAMES_FILE.exists():
        return pd.DataFrame()
    df = pd.read_parquet(PERF_GAMES_FILE).copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_pick5_submissions() -> pd.DataFrame:
    if not PICK5_SUBMISSIONS_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(PICK5_SUBMISSIONS_FILE).copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "CreatedAt" in df.columns:
        df["CreatedAt"] = pd.to_datetime(df["CreatedAt"], errors="coerce")
    if "Manager" in df.columns:
        df["Manager"] = df["Manager"].astype(str).str.strip()
    if "Week" in df.columns:
        df["Week"] = df["Week"].astype(str).str.strip()
    return df


@st.cache_data(ttl=600, show_spinner=False)
def load_pick5_winners() -> pd.DataFrame:
    if not PICK5_WINNERS_FILE.exists():
        return pd.DataFrame()
    return pd.read_parquet(PICK5_WINNERS_FILE).copy()


@st.cache_data(ttl=300, show_spinner=False)
def load_poll_votes_current() -> pd.DataFrame:
    if not POLL_VOTES_CURRENT_FILE.exists():
        return pd.DataFrame()
    df = pd.read_parquet(POLL_VOTES_CURRENT_FILE).copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


perf_summary = load_perf_summary()
perf_games = load_perf_games()
pick5_submissions = load_pick5_submissions()
poll_votes_current = load_poll_votes_current()


# ----------------------------
# HERO: FIGHT CARD
# ----------------------------
model_acc = model_upset = model_mae = model_brier = np.nan
model_total_games = 0

if not perf_summary.empty:
    r = perf_summary.iloc[0]
    model_acc = float(r.get("OverallAccuracy", np.nan))
    model_upset = float(r.get("UpsetRate", np.nan))
    model_total_games = int(r.get("TotalGames", 0) or 0)
    model_mae = float(r.get("MAE", np.nan))
    model_brier = float(r.get("BrierScore", np.nan))

crowd_managers = crowd_submissions = crowd_weeks = 0
crowd_last_submit = None

if not pick5_submissions.empty:
    crowd_submissions = len(pick5_submissions)
    if "Manager" in pick5_submissions.columns:
        crowd_managers = int(pick5_submissions["Manager"].dropna().nunique())
    if "Week" in pick5_submissions.columns:
        crowd_weeks = int(pick5_submissions["Week"].dropna().nunique())
    if "CreatedAt" in pick5_submissions.columns:
        crowd_last_submit = pick5_submissions["CreatedAt"].dropna().max()

st.markdown("### 🥊 Fight Card")
render_fight_card_inline(
    model_acc=model_acc,
    model_total_games=model_total_games,
    model_upset_rate=model_upset,
    model_brier=model_brier,
    model_mae=model_mae,
    crowd_managers=crowd_managers,
    crowd_submissions=crowd_submissions,
    crowd_weeks=crowd_weeks,
    crowd_last_submit=crowd_last_submit,
    status_ribbon="Locked: Game Day votes not live yet",
    cta_text="Vote on Game Day + play Pick‑5 to power the CROWD score",
    belt_left="CROWD BELT",
    belt_right="Unlocks when poll votes are logged per game (GameID)",
)

st.caption(
    "Goal: build the CROWD score through Game Day voting + Pick‑5 participation. "
    "Head-to-head accuracy unlocks when per-game poll votes are stored with GameID."
)

st.divider()


# ----------------------------
# MOMENTUM (THE MODEL vs THE CROWD)
# ----------------------------
st.markdown("### ⚡ Momentum (THE MODEL vs THE CROWD)")
st.caption("Model momentum is live now. Crowd momentum will unlock when Game Day poll votes are saved per game (GameID).")

model_roll10 = _rolling_acc_from_correct(perf_games, "ModelCorrect", 10)
model_roll25 = _rolling_acc_from_correct(perf_games, "ModelCorrect", 25)
model_season = _season_acc_from_correct(perf_games, "ModelCorrect")

crowd_ready = (not poll_votes_current.empty) and ("CrowdCorrect" in poll_votes_current.columns)
crowd_roll10 = _rolling_acc_from_correct(poll_votes_current, "CrowdCorrect", 10) if crowd_ready else np.nan
crowd_roll25 = _rolling_acc_from_correct(poll_votes_current, "CrowdCorrect", 25) if crowd_ready else np.nan
crowd_season = _season_acc_from_correct(poll_votes_current, "CrowdCorrect") if crowd_ready else np.nan

crowd_participation_value = f"{crowd_managers} managers"
crowd_participation_sub = f"{crowd_submissions} Pick‑5 submissions • {crowd_weeks} weeks"

c1, c2, c3 = st.columns(3)
with c1:
    render_split_card(
        title="Heat Check (rolling 10)",
        model_value=f"{model_roll10:.1f}%" if not np.isnan(model_roll10) else "—",
        model_sub="Rolling 10 games",
        model_progress=(model_roll10 / 100.0) if not np.isnan(model_roll10) else None,
        crowd_value=f"{crowd_roll10:.1f}%" if crowd_ready and not np.isnan(crowd_roll10) else "Locked",
        crowd_sub="Rolling 10 games (crowd picks)" if crowd_ready else crowd_participation_sub,
        crowd_progress=(crowd_roll10 / 100.0) if crowd_ready and not np.isnan(crowd_roll10) else None,
    )
with c2:
    render_split_card(
        title="Stability (rolling 25)",
        model_value=f"{model_roll25:.1f}%" if not np.isnan(model_roll25) else "—",
        model_sub="Rolling 25 games",
        model_progress=(model_roll25 / 100.0) if not np.isnan(model_roll25) else None,
        crowd_value=f"{crowd_roll25:.1f}%" if crowd_ready and not np.isnan(crowd_roll25) else "Locked",
        crowd_sub="Rolling 25 games (crowd picks)" if crowd_ready else crowd_participation_value,
        crowd_progress=(crowd_roll25 / 100.0) if crowd_ready and not np.isnan(crowd_roll25) else None,
    )
with c3:
    render_split_card(
        title="Season baseline",
        model_value=f"{model_season:.1f}%" if not np.isnan(model_season) else "—",
        model_sub="All games shown",
        model_progress=(model_season / 100.0) if not np.isnan(model_season) else None,
        crowd_value=f"{crowd_season:.1f}%" if crowd_ready and not np.isnan(crowd_season) else "Locked",
        crowd_sub="Season accuracy (crowd picks)" if crowd_ready else "Vote on Game Day to unlock accuracy",
        crowd_progress=(crowd_season / 100.0) if crowd_ready and not np.isnan(crowd_season) else None,
    )

st.divider()


# --- STOCK-CHART STYLE: normalized cumulative accuracy (starts at 1.00) ---
# Drop this into your page where the accuracy chart is now.

st.markdown("### 📈 Model vs Crowd (Season Track)")

x_mode = st.radio("X-axis", options=["Date", "Games"], horizontal=True, index=0)

def _cum_track(df: pd.DataFrame, correct_col: str, label: str) -> pd.DataFrame:
    if df is None or df.empty or correct_col not in df.columns:
        return pd.DataFrame()

    g = df.copy()
    g["Date"] = pd.to_datetime(g.get("Date", pd.NaT), errors="coerce")
    g = g.dropna(subset=["Date"]).sort_values("Date")

    c = pd.to_numeric(g[correct_col], errors="coerce").fillna(0).astype(int)
    games = np.arange(1, len(c) + 1, dtype=int)
    cum_acc = (c.cumsum() / games)  # 0..1
    track = 1.0 + (cum_acc - 0.50)  # normalized around 1.00 (coin-flip baseline)

    out = pd.DataFrame(
        {
            "Date": g["Date"].to_numpy(),
            "Games": games,
            "Track": track.to_numpy(),         # ~0.5..1.5 typical
            "CumAccPct": (cum_acc * 100.0).to_numpy(),
            "Series": label,
        }
    )
    return out


model_line = _cum_track(perf_games, "ModelCorrect", "THE MODEL")

crowd_ready = (not poll_votes_current.empty) and ("CrowdCorrect" in poll_votes_current.columns)
crowd_line = _cum_track(poll_votes_current, "CrowdCorrect", "THE CROWD") if crowd_ready else pd.DataFrame()

plot_df = pd.concat([model_line, crowd_line], ignore_index=True)

if plot_df.empty:
    st.info("Track will appear once model performance data is available.")
else:
    try:
        import altair as alt

        color_scale = alt.Scale(
            domain=["THE MODEL", "THE CROWD"],
            range=["#10b981", "#3b82f6"],
        )

        x_enc = alt.X("Date:T", title="Date") if x_mode == "Date" else alt.X("Games:Q", title="Games (cumulative)")

        chart = (
            alt.Chart(plot_df)
            .mark_line(strokeWidth=3)
            .encode(
                x=x_enc,
                y=alt.Y("Track:Q", title="Normalized track (1.00 = 50% baseline)"),
                color=alt.Color("Series:N", scale=color_scale, legend=alt.Legend(title="")),
                tooltip=[
                    alt.Tooltip("Series:N", title=""),
                    alt.Tooltip("Games:Q", title="Games", format=".0f"),
                    alt.Tooltip("CumAccPct:Q", title="Cumulative accuracy", format=".1f"),
                    alt.Tooltip("Track:Q", title="Track", format=".3f"),
                    alt.Tooltip("Date:T", title="Date", format="%b %d"),
                ],
            )
            .properties(height=340)
            .interactive()
        )

        # Baseline line at 1.00
        baseline = alt.Chart(pd.DataFrame({"y": [1.0]})).mark_rule(
            color="rgba(148,163,184,0.6)", strokeDash=[6, 6]
        ).encode(y="y:Q")

        st.altair_chart((chart + baseline), use_container_width=True)

        if not crowd_ready:
            st.caption("THE CROWD line will appear once Game Day poll votes are logged per game (GameID).")

    except Exception:
        st.info("Chart unavailable (Altair not installed).")



# ----------------------------
# CROWD: PICK‑5 ACTIVITY (LIVE NOW)
# ----------------------------
st.markdown("### 🏆 The CROWD: Pick‑5 Activity")
st.caption("This is live today (submissions). Weekly scoring/winners will return once schedules + upset gauges are available again.")

if pick5_submissions.empty:
    st.info("No Pick‑5 submissions found yet (data/fantasy_rosters.csv).")
else:
    left, right = st.columns([1.25, 1.0])

    with left:
        st.markdown("#### Latest submissions")
        cols = [
            c
            for c in [
                "Manager",
                "Week",
                "ClassA_Team",
                "ClassB_Team",
                "ClassC_Team",
                "ClassD_Team",
                "ClassS_Team",
                "CreatedAt",
            ]
            if c in pick5_submissions.columns
        ]
        show = pick5_submissions.copy()
        if "CreatedAt" in show.columns:
            show = show.sort_values("CreatedAt", ascending=False)
        st.dataframe(show[cols].head(12), hide_index=True, use_container_width=True)

    with right:
        st.markdown("#### Most active managers")
        if "Manager" in pick5_submissions.columns:
            counts = (
                pick5_submissions.dropna(subset=["Manager"])
                .groupby("Manager", dropna=True)
                .size()
                .reset_index(name="Submissions")
                .sort_values("Submissions", ascending=False)
                .head(12)
            )
            st.dataframe(counts, hide_index=True, use_container_width=True)
        else:
            st.info("Manager column not found in fantasy_rosters.csv.")

st.divider()


# ----------------------------
# LOCKED: GAME DAY POLLS
# ----------------------------
st.markdown("### 🗳️ Game Day Polls (unlock the CROWD score)")
st.caption("This section goes live when poll votes are stored per game with GameID.")

with st.container(border=True):
    st.markdown("#### What you'll get once voting goes live")
    st.markdown(
        """
- Head-to-head accuracy: CROWD vs THE MODEL on the same games
- Upset tracker: biggest wins when the CROWD fades the favorite
- Confidence traps: where the CROWD overreacts and the model stays disciplined
"""
    )
    st.info("Status: awaiting poll-vote dataset (recommended: data/poll_votes_current.parquet with GameID + CrowdCorrect).")

st.divider()


# ----------------------------
# OPTIONAL: PICK‑5 WINNERS
# ----------------------------
pick5_winners = load_pick5_winners()
if not pick5_winners.empty:
    st.markdown("### 🎯 Pick‑5 Weekly Champions (historical)")
    st.caption("Showing saved winners file when present.")
    st.dataframe(
        pick5_winners.sort_values("Week", ascending=False).head(12),
        hide_index=True,
        use_container_width=True,
    )
    st.divider()


# ----------------------------
# FOOTER + METHODOLOGY
# ----------------------------
st.markdown("### 📚 How to Read This Page")
st.markdown(
    """
- **THE MODEL**: Season performance (accuracy, upset rate, calibration).
- **THE CROWD**: Participation and Pick‑5 activity now; head-to-head results once Game Day voting is logged per game.
- **Driving participation**: Pick‑5 builds weekly engagement; polls build real-time crowd intelligence.
"""
)

spacer(2)
render_footer()
