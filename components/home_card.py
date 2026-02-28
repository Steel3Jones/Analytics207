from __future__ import annotations

import html
import streamlit as st


def inject_home_card_css() -> None:
    st.markdown(
        """
<style>
:root{
  --tr-bg0: rgba(2, 6, 23, 0.94);
  --tr-bg1: rgba(15, 23, 42, 0.94);
  --tr-border: rgba(148, 163, 184, 0.24);
  --tr-text: rgba(248, 250, 252, 0.98);
  --tr-sub: rgba(148, 163, 184, 0.92);
}

/* Base card */
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

  /* allow bottom-anchoring of the description */
  display: flex;
  flex-direction: column;
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

/* PREMIUM (default) = BLUE */
.tr-card.core{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(56,189,248,0.20),
    0 0 34px rgba(56,189,248,0.26);
}
.tr-card.core::after{
  background: radial-gradient(circle at 30% 30%, rgba(56,189,248,0.25), transparent 62%);
}
.tr-card.core .tr-accent{
  background: linear-gradient(90deg, #38bdf8, #0ea5e9);
}

/* CORE (free) = YELLOW */
.tr-card.ratings{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(239,239,68,0.30),
    0 0 40px rgba(248,248,113,0.38);
}
.tr-card.ratings::after{
  background: radial-gradient(circle at 30% 30%, rgba(250,204,21,0.32), transparent 62%);
}
.tr-card.ratings .tr-accent{
  background: linear-gradient(90deg, #facc15, #eab308);
}

/* PREMIUM top row = RED */
.tr-card.tourn{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(239,68,68,0.30),
    0 0 40px rgba(248,113,113,0.38);
}
.tr-card.tourn::after{
  background: radial-gradient(circle at 30% 30%, rgba(248,113,113,0.38), transparent 62%);
}
.tr-card.tourn .tr-accent{
  background: linear-gradient(90deg, #ef4444, #f97316);
}

/* Optional variants */
.tr-card.challenges{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(129,140,248,0.22),
    0 0 34px rgba(129,140,248,0.28);
}
.tr-card.challenges::after{
  background: radial-gradient(circle at 30% 30%, rgba(129,140,248,0.30), transparent 62%);
}
.tr-card.challenges .tr-accent{
  background: linear-gradient(90deg, #6366f1, #a855f7);
}

.tr-card.stories{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(34,197,94,0.20),
    0 0 34px rgba(34,197,94,0.24);
}
.tr-card.stories::after{
  background: radial-gradient(circle at 30% 30%, rgba(34,197,94,0.25), transparent 62%);
}
.tr-card.stories .tr-accent{
  background: linear-gradient(90deg, #22c55e, #4ade80);
}

/* Spotlight overlay */
.tr-card::after{
  content:"";
  position:absolute;
  inset:-120px -150px auto auto;
  width: 420px;
  height: 420px;
  pointer-events:none;
  background: radial-gradient(circle at 30% 30%, rgba(148,163,184,0.12), rgba(0,0,0,0.00) 62%);
}

/* Bottom data band */
.tr-card::before{
  content:"";
  position:absolute;
  left:0; right:0; bottom:0;
  height: 80px;
  background:
    linear-gradient(120deg, rgba(15,23,42,0.0), rgba(15,23,42,0.75)),
    repeating-linear-gradient(
      135deg,
      rgba(148,163,184,0.10),
      rgba(148,163,184,0.10) 2px,
      transparent 2px,
      transparent 6px
    );
  opacity: 0.9;
  pointer-events:none;
}

/* Accent bar */
.tr-accent{
  position:absolute;
  top:0; left:0; right:0;
  height: 4px;
  background: linear-gradient(90deg, #94a3b8, #64748b);
  opacity: 0.96;
}

/* Header / content */
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
  font-size: clamp(28px, 1.8vw, 36px);
  font-weight: 1000;
  letter-spacing: -0.03em;
  color: rgba(248,250,252,0.99);
  font-variant-numeric: tabular-nums;
  line-height: 1.05;
  position: relative;
  z-index: 1;
  text-shadow: 0 2px 18px rgba(0,0,0,0.55);
}

/* Anchor the description to the bottom */
.tr-sub{
  margin-top: auto;
  padding-top: 10px;
  font-size: 13px;
  line-height: 1.35;
  color: var(--tr-sub);
  position: relative;
  z-index: 1;
}

/* Corner ribbon */
.tr-ribbon{
  position: absolute;
  top: 12px;
  right: -56px;
  transform: rotate(45deg);
  width: 190px;
  padding: 6px 0;
  text-align: center;

  font-size: 11px;
  font-weight: 950;
  letter-spacing: 0.14em;
  text-transform: uppercase;

  color: rgba(2,6,23,0.95);
  background: linear-gradient(135deg, #fbbf24, #fb7185);
  border: 1px solid rgba(248,250,252,0.35);
  box-shadow: 0 12px 22px rgba(0,0,0,0.35);

  z-index: 3;
  pointer-events: none;
}

/* Variant-aware colors */
.tr-card.core .tr-ribbon{
  background: linear-gradient(135deg, #38bdf8, #0ea5e9);
  color: rgba(2,6,23,0.95);
}
.tr-card.ratings .tr-ribbon{
  background: linear-gradient(135deg, #facc15, #eab308);
}
.tr-card.tourn .tr-ribbon{
  background: linear-gradient(135deg, #fb7185, #f97316);
}
.tr-card.challenges .tr-ribbon{
  background: linear-gradient(135deg, #a78bfa, #6366f1);
  color: rgba(2,6,23,0.95);
}
.tr-card.stories .tr-ribbon{
  background: linear-gradient(135deg, #4ade80, #22c55e);
  color: rgba(2,6,23,0.95);
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_home_card(
    container,
    kicker: str,
    title: str,
    sub: str,
    metric: str | float | int | None,
    pill: str = "MODEL-POWERED",
    variant: str = "core",
    ribbon_text: str = "CORE",
    path: str | None = None,
) -> None:
    # path is intentionally ignored in this "no links" version.
    v = (variant or "core").strip().lower()
    if v not in {"core", "ratings", "tourn", "challenges", "stories"}:
        v = "core"

    kicker_html = html.escape(str(kicker or ""))
    title_html = html.escape(str(title or ""))
    sub_html = html.escape(str(sub or ""))

    metric_txt = "" if metric is None else str(metric)
    metric_html = html.escape(metric_txt)

    ribbon = ""
    if ribbon_text is not None and str(ribbon_text).strip():
        ribbon = f'<div class="tr-ribbon">{html.escape(str(ribbon_text).strip())}</div>'

    with container:
        st.markdown(
            f"""
<div class="tr-card {v}">
  {ribbon}
  <div class="tr-accent"></div>

  <div class="tr-head">
    <div class="tr-kicker">{kicker_html}</div>
  </div>

  <div class="tr-title">{title_html}</div>
  <div class="tr-metric">{metric_html}</div>
  <div class="tr-sub">{sub_html}</div>
</div>
            """,
            unsafe_allow_html=True,
        )
