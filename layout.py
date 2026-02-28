from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd
import streamlit as st


# ---------- paths ----------
def _project_root() -> Path:
    return Path(__file__).resolve().parent


# ---------- global layout / CSS ----------
def apply_global_layout_tweaks() -> None:
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"] {
            background: #070b12;
            width: 100%;
        }

        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            width: 100%;
        }

        /*
        Hide Streamlit chrome WITHOUT collapsing layout.
        Use visibility hidden (safer) instead of display none.
        */
        header[data-testid="stHeader"] { visibility: hidden !important; height: 0 !important; }
        div[data-testid="stToolbar"] { visibility: hidden !important; height: 0 !important; }
        #MainMenu { visibility: hidden; }

        /* hide only Streamlit's own footer */
        footer[data-testid="stFooter"] { visibility: hidden; height: 0 !important; }

        div[data-testid="stVerticalBlock"] > div {
            gap: 0.9rem;
        }

        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div {
            background: #0b1220;
            border: 1px solid rgba(255,255,255,0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------- logo ----------
def render_logo(width: int = 420, gap_px: int = 2) -> None:
    logo_path = _project_root() / "web" / "static" / "img" / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=width)
    st.markdown(f"<div style='height:{gap_px}px'></div>", unsafe_allow_html=True)


# ---------- header ----------
def render_page_header(
    title: str,
    definition: str = "",
    subtitle: str = "",
    title_size_px: int = 38,
    def_size_px: int = 20,
    sub_size_px: int = 14,
    line_height_px: int = 5,
    line_margin_top_px: int = 8,
    line_margin_bottom_px: int = 6,
    italic_definition: bool = True,
) -> None:
    italic_css = "font-style:italic;" if italic_definition else ""
    st.markdown(
        f"""
        <div>
        <div style="margin-top:-20px;">
          <div style="color:#e5e7eb;font-size:{title_size_px}px;line-height:1.1;font-weight:700;">
            {title}
          </div>
          {f'<div style="color:#fbbf24;font-size:{def_size_px}px;margin-top:6px;{italic_css}">{definition}</div>' if definition else ''}
          {f'<div style="color:#cbd5e1;font-size:{sub_size_px}px;margin-top:6px;max-width:760px;">{subtitle}</div>' if subtitle else ''}
        </div>

        <div style="
          height:{line_height_px}px;
          background: linear-gradient(90deg, #fbbf24, #f59e0b, #fb7185);
          border-radius: 999px;
          margin: {line_margin_top_px}px 0 {line_margin_bottom_px}px 0;
        "></div>
        """,
        unsafe_allow_html=True,
    )


# ---------- footer (same gradient bar) ----------
def render_footer() -> None:
    st.markdown(
        """
        <style>
        .a207-footer-wrap {
            margin-top: 24px;
            padding-bottom: 16px;
            color: rgba(148,163,184,0.9);
            font-size: 12px;
        }

        .a207-footer-line {
            height: 5px;
            background: linear-gradient(90deg, #fbbf24, #f59e0b, #fb7185);
            border-radius: 999px;
            margin: 10px 0 8px 0;
        }

        .a207-footer-title-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 2px;
            font-size: 12px;
        }

        .a207-footer-logo {
            height: 20px;
            width: auto;
            opacity: 0.95;
        }

        .a207-footer-title-text {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-weight: 600;
            color: rgba(226,232,240,0.95);
        }

        .a207-footer-sub {
            color: rgba(156,163,175,0.95);
            margin-bottom: 6px;
            font-size: 12px;
        }

        .a207-footer-links-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 4px;
            font-size: 12px;
        }

        .a207-footer-link {
            color: rgba(203,213,225,0.95);
            text-decoration: none;
            white-space: nowrap;
        }

        .a207-footer-link:hover {
            text-decoration: underline;
        }

        .a207-footer-meta {
            color: rgba(156,163,175,0.9);
            font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    logo_path = _project_root() / "web" / "static" / "img" / "logo.png"
    logo_html = ""
    if logo_path.exists():
        import base64
        data = logo_path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        logo_html = f'<img src="data:image/png;base64,{b64}" class="a207-footer-logo">'

    st.markdown(
        f"""
<div class="a207-footer-wrap">
  <div class="a207-footer-line"></div>

  <div class="a207-footer-title-row">
    {logo_html}
    <div class="a207-footer-title-text">
      <span>🧠</span>
      <span>The Model</span>
    </div>
  </div>

  <div class="a207-footer-sub">
    Inside the data model behind our sports insights.
  </div>

  <div class="a207-footer-links-row">
    <a class="a207-footer-link" href="/about">About</a>
    <span>·</span>
    <a class="a207-footer-link" href="/docs">Documentation</a>
    <span>·</span>
    <a class="a207-footer-link" href="/support">Support</a>
    <span>·</span>
    <a class="a207-footer-link" href="/report-data-issue">Report data issue</a>
    <span>·</span>
    <a class="a207-footer-link" href="/status">Status</a>
  </div>

  <div class="a207-footer-meta">
    <a class="a207-footer-link" href="/privacy">Privacy</a>
    <span>·</span>
    <a class="a207-footer-link" href="/terms">Terms</a>
    <span>·</span>
    © 2026 Analytics207.com
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


# ---------- small helpers ----------
def spacer(lines: int = 1) -> None:
    for _ in range(max(0, int(lines))):
        st.write("")


def confidence_pill_html(p: float) -> str:
    if pd.isna(p):
        return ""
    p = float(p)

    if p >= 0.80:
        border, bg = "#34d399", "rgba(52,211,153,0.18)"
    elif p >= 0.60:
        border, bg = "#60a5fa", "rgba(96,165,250,0.18)"
    elif p >= 0.50:
        border, bg = "#fb923c", "rgba(251,146,60,0.18)"
    else:
        border, bg = "#9ca3af", "rgba(156,163,175,0.15)"

    pct = f"{p * 100:.0f}%"
    return f"""
    <span style="
        display:inline-block;
        padding:4px 10px;
        border-radius:999px;
        border:1px solid {border};
        background:{bg};
        color:#e5e7eb;
        font-size:12px;
        line-height:1;
        min-width:44px;
        text-align:center;
    ">{pct}</span>
    """


def result_icon_html(ok: Optional[bool]) -> str:
    if ok is None:
        return ""
    if ok:
        return '<span style="color:#34d399;font-size:16px;">✓</span>'
    return '<span style="color:#f87171;font-size:16px;">✕</span>'


def render_performance_strip(
    total_games: int,
    played_games: int,
    correct_games: int,
    label: str = "Performance",
) -> None:
    acc = (correct_games / played_games) if played_games else np.nan
    acc_text = f"{acc * 100:.0f}%" if not pd.isna(acc) else ""
    st.markdown(
        f"""
        <div style="background:#0b1220;padding:14px 16px;border-radius:14px;
                            border:1px solid rgba(255,255,255,0.06);margin-top:10px;">
          <div style="color:#e5e7eb;font-size:18px;margin-bottom:8px;">{label}</div>
          <div style="display:flex;gap:14px;flex-wrap:wrap;">
            <div style="color:#cbd5e1;">Games shown <span style="color:#e5e7eb;">{total_games}</span></div>
            <div style="color:#cbd5e1;">Played <span style="color:#e5e7eb;">{played_games}</span></div>
            <div style="color:#cbd5e1;">Correct picks <span style="color:#e5e7eb;">{correct_games}</span></div>
            <div style="color:#cbd5e1;">Pick accuracy <span style="color:#e5e7eb;">{acc_text}</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@dataclass
class TableColumn:
    header: str
    key: str
    kind: str = "text"
    # kinds: text, mono, pill_conf, final_score, result_icon


def render_html_table(
    df: pd.DataFrame,
    columns: Sequence[TableColumn],
    title: str = "",
    class_name: str = "ph",
) -> None:
    st.markdown(
        f"""
        <style>
        .ph-wrap {{ background:#0b1220;padding:18px;border-radius:16px;
                    border:1px solid rgba(255,255,255,0.06);margin-top:10px; }}
        .ph-title {{ font-size:26px;color:#e5e7eb;margin-bottom:10px; }}
        table.{class_name} {{ width:100%;border-collapse:collapse;font-size:13px; }}
        table.{class_name} thead th {{ padding:10px;color:#cbd5e1;
            border-bottom:1px solid rgba(255,255,255,0.08);text-align:left; }}
        table.{class_name} tbody td {{ padding:10px;color:#e5e7eb;
            border-bottom:1px solid rgba(255,255,255,0.06);vertical-align:middle; }}
        table.{class_name} tbody tr:hover {{ background:rgba(255,255,255,0.03); }}
        .mono {{ font-variant-numeric: tabular-nums; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    header_html = "".join(f"<th>{c.header}</th>" for c in columns)

    rows: list[str] = []
    for _, r in df.iterrows():
        tds: list[str] = []
        for c in columns:
            if c.kind == "mono":
                tds.append(f"<td class='mono'>{r.get(c.key, '')}</td>")
            elif c.kind == "pill_conf":
                val = r.get(c.key, np.nan)
                tds.append(f"<td>{confidence_pill_html(val) if pd.notna(val) else ''}</td>")
            elif c.kind == "final_score":
                hs = r.get("HomeScore", np.nan)
                aw = r.get("AwayScore", np.nan)
                score = ""
                if pd.notna(hs) and pd.notna(aw) and (float(hs) + float(aw)) > 0:
                    score = f"{int(hs)}-{int(aw)}"
                tds.append(f"<td class='mono'>{score}</td>")
            elif c.kind == "result_icon":
                tds.append(f"<td>{result_icon_html(r.get(c.key, None))}</td>")
            else:
                tds.append(f"<td>{r.get(c.key, '')}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")

    body_html = "".join(rows) if rows else f"<tr><td colspan='{len(columns)}'>No rows.</td></tr>"

    st.markdown(
        f"""
        <div class="ph-wrap">
          {f'<div class="ph-title">{title}</div>' if title else ''}
          <table class="{class_name}">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{body_html}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- Backwards-compatible aliases for your Home.py _pick() ---
def applygloballayouttweaks() -> None:
    apply_global_layout_tweaks()


def renderlogo(width: int = 420, gappx: int = 2) -> None:
    render_logo(width=width, gap_px=gappx)


def renderpageheader(*args, **kwargs) -> None:
    render_page_header(*args, **kwargs)


def renderfooter() -> None:
    render_footer()
