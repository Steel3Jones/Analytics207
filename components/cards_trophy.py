from __future__ import annotations

import html
import streamlit as st


def inject_trophy_card_css() -> None:
    st.markdown(
        """
<style>
:root{
  --tr-bg0: rgba(2, 6, 23, 0.94);
  --tr-bg1: rgba(15, 23, 42, 0.94);
  --tr-border: rgba(148, 163, 184, 0.24);
  --tr-text: rgba(248, 250, 252, 0.98);
  --tr-muted: rgba(203, 213, 225, 0.82);
  --tr-sub: rgba(148, 163, 184, 0.92);

  --gold0: rgba(250, 204, 21, 0.24);
  --blue0: rgba(56, 189, 248, 0.22);
  --green0: rgba(34, 197, 94, 0.22);
  --red0: rgba(239, 68, 68, 0.22);
}

.tr-card{
  position: relative;
  border-radius: 18px;
  padding: 14px 16px 14px 16px;
  border: 1px solid var(--tr-border);
  background: linear-gradient(180deg, var(--tr-bg1), var(--tr-bg0));
  overflow: hidden;
  min-height: 154px;
  box-shadow: 0 16px 42px rgba(0,0,0,0.48);
  transform: translateY(0px);
  transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
}

@media (prefers-reduced-motion: reduce) {
  .tr-card { transition: none; }
}

@media (prefers-reduced-motion: no-preference) {
  .tr-card:hover{
    transform: translateY(-2px);
    border-color: rgba(226,232,240,0.28);
    box-shadow: 0 18px 52px rgba(0,0,0,0.55);
  }
}

/* Variant glows */
.tr-card.gold{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(250,204,21,0.10),
    0 0 30px rgba(250,204,21,0.10);
}
.tr-card.blue{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(56,189,248,0.10),
    0 0 30px rgba(56,189,248,0.12);
}
.tr-card.green{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(34,197,94,0.10),
    0 0 30px rgba(34,197,94,0.10);
}
.tr-card.red{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(239,68,68,0.10),
    0 0 30px rgba(239,68,68,0.12);
}

/* Spotlight overlay (tinted by variant) */
.tr-card::after{
  content:"";
  position:absolute;
  inset:-120px -150px auto auto;
  width: 420px;
  height: 420px;
  pointer-events:none;
  background: radial-gradient(circle at 30% 30%, var(--gold0), rgba(0,0,0,0.00) 62%);
}
.tr-card.blue::after{ background: radial-gradient(circle at 30% 30%, var(--blue0), rgba(0,0,0,0.00) 62%); }
.tr-card.green::after{ background: radial-gradient(circle at 30% 30%, var(--green0), rgba(0,0,0,0.00) 62%); }
.tr-card.red::after{ background: radial-gradient(circle at 30% 30%, var(--red0), rgba(0,0,0,0.00) 62%); }

/* Trophy watermark (stronger + more visible) */
.tr-card::before{
  content:"🏆";
  position:absolute;
  right: 18px;
  bottom: 12px;
  font-size: 78px;
  opacity: 0.14;
  transform: rotate(-10deg);
  pointer-events:none;
}

/* Accent bar */
.tr-accent{
  position:absolute;
  top:0; left:0; right:0;
  height: 6px;
  background: linear-gradient(90deg, #fbbf24, #f59e0b, #fb7185);
  opacity: 0.96;
}
.tr-card.gold .tr-accent{ background: linear-gradient(90deg, #fbbf24, #f59e0b, #fb7185); }
.tr-card.blue .tr-accent{ background: linear-gradient(90deg, #38bdf8, #818cf8); }
.tr-card.green .tr-accent{ background: linear-gradient(90deg, #22c55e, #a3e635); }
.tr-card.red .tr-accent{ background: linear-gradient(90deg, #ef4444, #f97316); }

/* Corner ribbon */
.tr-ribbon{
  position: absolute;
  top: 12px;
  right: -46px;
  transform: rotate(45deg);
  width: 150px;
  text-align: center;
  padding: 6px 0;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(2,6,23,0.95);
  background: rgba(250,204,21,0.92);
  box-shadow: 0 10px 26px rgba(0,0,0,0.35);
}
.tr-card.blue .tr-ribbon{ background: rgba(56,189,248,0.92); color: rgba(2,6,23,0.95); }
.tr-card.green .tr-ribbon{ background: rgba(34,197,94,0.92); color: rgba(2,6,23,0.95); }
.tr-card.red .tr-ribbon{ background: rgba(239,68,68,0.92); color: rgba(2,6,23,0.98); }

.tr-head{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap: 10px;
  margin-top: 6px;
  position: relative;
  z-index: 1;
}

.tr-kicker{
  font-size: 11px;
  font-weight: 950;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(226,232,240,0.86);
  line-height: 1.1;
}

.tr-chip{
  display:inline-flex;
  align-items:center;
  gap: 7px;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.55);
  color: rgba(248,250,252,0.92);
  white-space: nowrap;
}

.tr-chip .dot{
  width: 8px; height: 8px;
  border-radius: 999px;
  background: #fbbf24;
  opacity: 0.95;
}
.tr-card.blue .tr-chip .dot{ background: #38bdf8; }
.tr-card.green .tr-chip .dot{ background: #22c55e; }
.tr-card.red .tr-chip .dot{ background: #ef4444; }

.tr-title{
  margin-top: 12px;
  font-size: clamp(16px, 1.10vw, 20px);
  font-weight: 950;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--tr-text);
  position: relative;
  z-index: 1;
}

.tr-metric{
  margin-top: 8px;
  font-size: clamp(34px, 2.10vw, 46px);
  font-weight: 1000;
  letter-spacing: -0.05em;
  color: rgba(248,250,252,0.99);
  font-variant-numeric: tabular-nums;
  line-height: 1.05;
  position: relative;
  z-index: 1;
  text-shadow: 0 2px 18px rgba(0,0,0,0.55);
}

.tr-sub{
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.35;
  color: var(--tr-sub);
  position: relative;
  z-index: 1;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_trophy_card(
    container,
    kicker: str,
    title: str,
    sub: str,
    metric: str | float | int | None,
    pill: str = "STATEWIDE",
    variant: str = "gold",
    ribbon_text: str = "Champion",
) -> None:
    v = (variant or "gold").strip().lower()
    if v not in {"gold", "blue", "green", "red"}:
        v = "gold"

    kicker_html = html.escape(str(kicker or ""))
    title_html = html.escape(str(title or ""))
    sub_html = html.escape(str(sub or ""))
    pill_html = html.escape(str(pill or ""))
    ribbon_html = html.escape(str(ribbon_text or "Champion"))

    metric_txt = "" if metric is None else str(metric)
    metric_html = html.escape(metric_txt)

    with container:
        st.markdown(
            f"""
<div class="tr-card {v}">
  <div class="tr-accent"></div>
  <div class="tr-ribbon">{ribbon_html}</div>

  <div class="tr-head">
    <div class="tr-kicker">{kicker_html}</div>
    <div class="tr-chip"><span class="dot"></span>{pill_html}</div>
  </div>

  <div class="tr-title">{title_html}</div>
  <div class="tr-metric">{metric_html}</div>
  <div class="tr-sub">{sub_html}</div>
</div>
            """,
            unsafe_allow_html=True,
        )
