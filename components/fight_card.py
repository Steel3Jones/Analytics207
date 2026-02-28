# components/fight_card.py
from __future__ import annotations

import math
from typing import Optional

import pandas as pd
import streamlit as st


def _fmt_pct(x: Optional[float]) -> str:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "—"
        return f"{float(x):.1f}%"
    except Exception:
        return "—"


def _fmt_num(x: Optional[float], decimals: int = 2) -> str:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "—"
        return f"{float(x):.{decimals}f}"
    except Exception:
        return "—"


def _fmt_int(x: Optional[int]) -> str:
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


def inject_fight_card_css() -> None:
    st.markdown(
        """
<style>
/* ---- Fight Card ---- */
.a207-fightcard {
  background: #0b1220;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  padding: 18px 18px 16px 18px;
  position: relative;
  overflow: hidden;
}

.a207-fightcard:before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(900px 300px at 15% 0%, rgba(245,158,11,0.14), transparent 60%),
              radial-gradient(900px 300px at 85% 0%, rgba(59,130,246,0.14), transparent 60%);
  pointer-events: none;
}

.a207-fightgrid {
  display: grid;
  grid-template-columns: 1fr 220px 1fr;
  gap: 14px;
  position: relative;
  z-index: 1;
}

@media (max-width: 980px) {
  .a207-fightgrid { grid-template-columns: 1fr; }
  .a207-vs { order: -1; }
}

.a207-side {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 14px 14px 12px 14px;
}

.a207-kicker {
  color: rgba(203,213,225,0.92);
  font-size: 12px;
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.a207-title {
  color: #e5e7eb;
  font-size: 28px;
  font-weight: 800;
  line-height: 1.05;
  margin-bottom: 6px;
}

.a207-sub {
  color: rgba(203,213,225,0.92);
  font-size: 13px;
  margin-bottom: 10px;
}

.a207-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
}

.a207-metric {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 10px 10px 9px 10px;
}

.a207-metric-label {
  color: rgba(156,163,175,0.92);
  font-size: 12px;
  margin-bottom: 4px;
}

.a207-metric-value {
  color: #e5e7eb;
  font-size: 16px;
  font-weight: 700;
}

.a207-vs {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 8px;
  border-radius: 16px;
  border: 1px dashed rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.02);
}

.a207-vs-big {
  font-size: 46px;
  font-weight: 900;
  line-height: 1;
  background: linear-gradient(90deg, #fbbf24, #f59e0b, #fb7185);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin-bottom: 8px;
}

.a207-ribbon {
  font-size: 12px;
  color: rgba(226,232,240,0.95);
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(15,23,42,0.55);
  margin-bottom: 8px;
  text-align: center;
}

.a207-cta {
  font-size: 12px;
  color: rgba(203,213,225,0.92);
  text-align: center;
}

.a207-belt {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.06);
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: space-between;
  position: relative;
  z-index: 1;
}

.a207-belt-left {
  color: rgba(226,232,240,0.95);
  font-weight: 700;
}

.a207-belt-right {
  color: rgba(148,163,184,0.95);
  font-size: 12px;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_fight_card(
    *,
    model_acc: Optional[float],
    model_total_games: Optional[int],
    model_upset_rate: Optional[float],
    model_brier: Optional[float],
    model_mae: Optional[float],
    crowd_managers: Optional[int],
    crowd_submissions: Optional[int],
    crowd_weeks: Optional[int],
    crowd_last_submit,
    status_ribbon: str = "Locked: awaiting Game Day votes",
    cta_text: str = "Vote on Game Day + play Pick‑5 to power the CROWD score",
    belt_left: str = "CROWD BELT",
    belt_right: str = "Unlocked once poll votes are logged per game (GameID)",
) -> None:
    html = f"""
<div class="a207-fightcard">
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
    """
    st.markdown(html, unsafe_allow_html=True)
