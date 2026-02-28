from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
import pandas as pd
import streamlit as st


# =============================
# GLOBAL THEME / LAYOUT
# =============================
def apply_global_layout_tweaks() -> None:
    """
    One place for global CSS + Streamlit tweaks.
    Safe to call on every page.
    """
    st.markdown(
        """
        <style>
        /* Reduce top padding a bit */
        .block-container { padding-top: 1.5rem; }

        /* Default background (works with your dark tables) */
        html, body, [data-testid="stAppViewContainer"] {
            background: #070b12;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_logo() -> None:
    """
    Stub. If you already have a logo renderer, keep using it.
    This exists so pages can import from layout.py consistently.
    """
    # If you already render a logo in the sidebar/header, leave this empty or implement.
    return


def render_page_header(title: str, definition: str = "", subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div style="margin-bottom:12px;">
          <div style="color:#e5e7eb;font-size:34px;line-height:1.1;margin:0;">{title}</div>
          {f'<div style="color:#94a3b8;font-size:14px;margin-top:6px;">{definition}</div>' if definition else ''}
          {f'<div style="color:#64748b;font-size:13px;margin-top:4px;">{subtitle}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
        <div style="margin-top:24px;color:#475569;font-size:12px;">
          <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:10px;"></div>
          Built with Streamlit
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================
# UI COMPONENTS YOU LIKE
# =============================
def spacer(lines: int = 1) -> None:
    for _ in range(max(1, int(lines))):
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
        white-space:nowrap;
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


def render_performance_strip(total_games: int, played_games: int, correct_games: int, label: str = "Performance") -> None:
    acc = (correct_games / played_games) if played_games else np.nan
    acc_text = f"{acc * 100:.0f}%" if not pd.isna(acc) else ""
    st.markdown(
        f"""
        <div style="background:#0b1220;padding:14px 16px;border-radius:14px;border:1px solid rgba(255,255,255,0.06);margin-top:10px;">
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
    kind: str = "text"  # text | mono | pill_conf | final_score | result_icon


def render_html_table(
    df: pd.DataFrame,
    columns: Sequence[TableColumn],
    title: str = "",
    class_name: str = "ph",
) -> None:
    st.markdown(
        f"""
        <style>
        .ph-wrap {{ background: #0b1220; padding: 18px 18px 8px 18px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.06); margin-top: 10px; }}
        .ph-title {{ font-size: 28px; color:#e5e7eb; margin: 0 0 12px 0; }}
        table.{class_name} {{ width:100%; border-collapse: collapse; font-size: 13px; }}
        table.{class_name} thead th {{ text-align:left; padding: 10px; color:#cbd5e1; border-bottom: 1px solid rgba(255,255,255,0.08); }}
        table.{class_name} tbody td {{ padding: 10px; color:#e5e7eb; border-bottom: 1px solid rgba(255,255,255,0.06); vertical-align: middle; }}
        table.{class_name} tbody tr:hover {{ background: rgba(255,255,255,0.03); }}
        .mono {{ font-variant-numeric: tabular-nums; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    header_html = "".join([f"<th>{c.header}</th>" for c in columns])

    rows = []
    for _, r in df.iterrows():
        tds = []
        for c in columns:
            if c.kind == "mono":
                tds.append(f"<td class='mono'>{r.get(c.key, '')}</td>")
            elif c.kind == "pill_conf":
                val = r.get(c.key, np.nan)
                html = confidence_pill_html(val) if pd.notna(val) else ""
                tds.append(f"<td>{html}</td>")
            elif c.kind == "final_score":
                hs = r.get("HomeScore", np.nan)
                aw = r.get("AwayScore", np.nan)
                score = ""
                if pd.notna(hs) and pd.notna(aw) and (float(hs) + float(aw)) > 0:
                    score = f"{int(hs)}-{int(aw)}"
                tds.append(f"<td class='mono'>{score}</td>")
            elif c.kind == "result_icon":
                ok = r.get(c.key, None)
                tds.append(f"<td>{result_icon_html(ok)}</td>")
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
