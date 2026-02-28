from __future__ import annotations

import html
import streamlit as st


def inject_team_center_card_css() -> None:
    st.markdown(
        """
<style>
:root{
  --tc-bg0: rgba(2, 6, 23, 0.94);
  --tc-bg1: rgba(15, 23, 42, 0.94);
  --tc-border: rgba(148, 163, 184, 0.24);
  --tc-text: rgba(248, 250, 252, 0.98);
  --tc-sub: rgba(148, 163, 184, 0.92);

  --boys0: rgba(56, 189, 248, 0.22);
  --girls0: rgba(244, 114, 182, 0.20);
}

.tc-card{
  position: relative;
  border-radius: 18px;
  padding: 14px 16px 14px 16px;
  border: 1px solid var(--tc-border);
  background: linear-gradient(180deg, var(--tc-bg1), var(--tc-bg0));
  overflow: hidden;
  min-height: 170px;
  box-shadow: 0 16px 42px rgba(0,0,0,0.48);
  transform: translateY(0px);
  transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
}

@media (prefers-reduced-motion: reduce) {
  .tc-card { transition: none; }
}

@media (prefers-reduced-motion: no-preference) {
  .tc-card:hover{
    transform: translateY(-2px);
    border-color: rgba(226,232,240,0.28);
    box-shadow: 0 18px 52px rgba(0,0,0,0.55);
  }
}

.tc-card.boys{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(56,189,248,0.10),
    0 0 30px rgba(56,189,248,0.12);
}
.tc-card.girls{
  box-shadow:
    0 16px 42px rgba(0,0,0,0.48),
    0 0 0 1px rgba(244,114,182,0.10),
    0 0 30px rgba(244,114,182,0.12);
}

/* Spotlight overlay */
.tc-card::after{
  content:"";
  position:absolute;
  inset:-120px -150px auto auto;
  width: 420px;
  height: 420px;
  pointer-events:none;
  background: radial-gradient(circle at 30% 30%, rgba(250,204,21,0.18), rgba(0,0,0,0.00) 62%);
}
.tc-card.boys::after{ background: radial-gradient(circle at 30% 30%, var(--boys0), rgba(0,0,0,0.00) 62%); }
.tc-card.girls::after{ background: radial-gradient(circle at 30% 30%, var(--girls0), rgba(0,0,0,0.00) 62%); }

/* Watermark */
.tc-card::before{
  content:"🏫";
  position:absolute;
  right: 18px;
  bottom: 10px;
  font-size: 78px;
  opacity: 0.10;
  transform: rotate(-10deg);
  pointer-events:none;
}
.tc-card.boys::before{ content:"🏀"; opacity: 0.10; }
.tc-card.girls::before{ content:"🏀"; opacity: 0.10; }

/* Accent bar */
.tc-accent{
  position:absolute;
  top:0; left:0; right:0;
  height: 6px;
  background: linear-gradient(90deg, #fbbf24, #f59e0b, #fb7185);
  opacity: 0.96;
}
.tc-card.boys .tc-accent{ background: linear-gradient(90deg, #38bdf8, #60a5fa); }
.tc-card.girls .tc-accent{ background: linear-gradient(90deg, #f472b6, #fb7185); }

/* Ribbon */
.tc-ribbon{
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
.tc-card.boys .tc-ribbon{ background: rgba(56,189,248,0.92); color: rgba(2,6,23,0.95); }
.tc-card.girls .tc-ribbon{ background: rgba(244,114,182,0.92); color: rgba(2,6,23,0.95); }

/* Head row */
.tc-head{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap: 10px;
  margin-top: 6px;
  position: relative;
  z-index: 1;
}

.tc-kicker{
  font-size: 11px;
  font-weight: 950;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(226,232,240,0.86);
  line-height: 1.1;
}

.tc-chip{
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
  max-width: 100%;
}

.tc-chip .dot{
  width: 8px; height: 8px;
  border-radius: 999px;
  background: #fbbf24;
  opacity: 0.95;
}
.tc-card.boys .tc-chip .dot{ background: #38bdf8; }
.tc-card.girls .tc-chip .dot{ background: #f472b6; }

/* Title + metric */
.tc-title{
  margin-top: 12px;
  font-size: clamp(16px, 1.10vw, 20px);
  font-weight: 950;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--tc-text);
  position: relative;
  z-index: 1;
}

.tc-metric{
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

.tc-sub{
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.35;
  color: var(--tc-sub);
  position: relative;
  z-index: 1;
}

/* Mini grid */
.tc-grid{
  margin-top: 10px;
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
  position: relative;
  z-index: 1;
}
.tc-kv{
  padding: 10px 10px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(11,18,32,0.55);
}
.tc-kv .k{
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 900;
  color: rgba(148,163,184,0.90);
  margin-bottom: 4px;
}
.tc-kv .v{
  font-size: 14px;
  font-weight: 900;
  color: rgba(248,250,252,0.96);
  font-variant-numeric: tabular-nums;
}
.tc-kv .v.mono{
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_team_gender_hero_card(
    container,
    *,
    school_name: str,
    gender_label: str,
    record: str | None,
    division: str | None,
    games_tracked: int | None = None,
    context_line: str | None = None,
    variant: str = "boys",
) -> None:
    v = (variant or "boys").strip().lower()
    if v not in {"boys", "girls"}:
        v = "boys"

    school_html = html.escape(str(school_name or ""))
    gender_html = html.escape(str(gender_label or "").upper())
    record_html = html.escape(str(record or "—"))
    division_txt = str(division or "?").strip()
    division_html = html.escape(division_txt)

    ribbon_html = html.escape("BOYS" if v == "boys" else "GIRLS")

    ctx = (context_line or "").strip()
    chip_txt = f"Division {division_txt}"
    if ctx:
        chip_txt = f"{chip_txt} • {ctx}"
    chip_html = html.escape(chip_txt)

    games_txt = "—"
    if games_tracked is not None:
        try:
            games_txt = f"{int(games_tracked)} games tracked"
        except Exception:
            games_txt = "—"
    games_html = html.escape(games_txt)

    with container:
        st.markdown(
            f"""
<div class="tc-card {v}">
  <div class="tc-accent"></div>
  <div class="tc-ribbon">{ribbon_html}</div>

  <div class="tc-head">
    <div class="tc-kicker">{school_html}</div>
    <div class="tc-chip"><span class="dot"></span>{chip_html}</div>
  </div>

  <div class="tc-title">{gender_html} PROGRAM</div>
  <div class="tc-metric">{record_html}</div>
  <div class="tc-sub">{games_html}</div>

  <div class="tc-grid">
    <div class="tc-kv">
      <div class="k">Division</div>
      <div class="v mono">{division_html}</div>
    </div>
    <div class="tc-kv">
      <div class="k">Record</div>
      <div class="v mono">{record_html}</div>
    </div>
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )


def render_team_center_header_cards(
    *,
    boys_container,
    girls_container,
    school_name: str,
    division: str | None,
    boys_record: str | None,
    girls_record: str | None,
    boys_games_tracked: int | None = None,
    girls_games_tracked: int | None = None,
    boys_context: str | None = None,
    girls_context: str | None = None,
) -> None:
    render_team_gender_hero_card(
        boys_container,
        school_name=school_name,
        gender_label="Boys",
        record=boys_record,
        division=division,
        games_tracked=boys_games_tracked,
        context_line=boys_context,
        variant="boys",
    )
    render_team_gender_hero_card(
        girls_container,
        school_name=school_name,
        gender_label="Girls",
        record=girls_record,
        division=division,
        games_tracked=girls_games_tracked,
        context_line=girls_context,
        variant="girls",
    )
