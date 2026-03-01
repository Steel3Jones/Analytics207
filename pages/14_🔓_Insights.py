from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
import os

import streamlit as st
import layout as L
from auth import login_gate, logout_button

# ----------------------------
# Config
# ----------------------------


from sidebar_auth import render_sidebar_auth

render_sidebar_auth()



st.set_page_config(
    page_title="💡 Insights | ANALYTICS207",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGE_SIZE_DEFAULT = 20

# ----------------------------
# Layout resolver (no layout.py edits)
# ----------------------------
def _pick(*names: str) -> Optional[Callable]:
    for n in names:
        fn = getattr(L, n, None)
        if callable(fn):
            return fn
    return None

apply_layout  = _pick("apply_global_layout_tweaks", "applygloballayouttweaks")
render_logo   = _pick("render_logo", "renderlogo")
render_header = _pick("render_page_header", "renderpageheader")
render_footer = _pick("render_footer", "renderfooter")
spacer        = _pick("spacer", "spacerlines")

def _sp(n: int = 1) -> None:
    if callable(spacer):
        try:
            spacer(n)
            return
        except Exception:
            pass
    for _ in range(max(0, int(n))):
        st.write("")

if apply_layout:
    apply_layout()
login_gate(required=False)
logout_button()

if render_logo:
    render_logo()
if render_header:
    render_header(
        title="Insights",
        definition="Insights (n.): Where the model meets the moments.",
        subtitle="Blog-style posts that connect the stats to the story across gyms all over Maine.",
    )
else:
    st.title("Insights")
    st.caption("Blog-style posts that connect the stats to the story across gyms all over Maine.")

# ----------------------------
# Filesystem
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSIGHTS_DIR = PROJECT_ROOT / "Insights"
IMAGES_DIR   = INSIGHTS_DIR / "images"

if not INSIGHTS_DIR.exists():
    st.error(f"Insights folder not found at {INSIGHTS_DIR}")
    st.stop()

files_all = sorted(INSIGHTS_DIR.glob("*.md"), reverse=True)
if not files_all:
    st.info("No insights yet.")
    st.stop()

# ----------------------------
# Parsing helpers
# ----------------------------
def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()

def clean_line(s: str) -> str:
    invisible = ["\ufeff", "\u200b", "\u200c", "\u200d", "\u2060", "\u00a0"]
    for ch in invisible:
        s = s.replace(ch, "")
    return s.strip()

@dataclass
class ParsedArticle:
    image_name: Optional[str]
    title_text: Optional[str]
    body_markdown: str

def parse_article(lines: list[str]) -> ParsedArticle:
    image_name: Optional[str] = None
    title_text: Optional[str] = None
    body_lines: list[str] = []
    header_regex = re.compile(r"^(#{1,6})\s*(.+)$")

    for line in lines:
        cleaned = clean_line(line)

        if image_name is None and "IMAGE:" in cleaned.upper():
            image_name = cleaned.split(":", 1)[1].strip()
            continue

        if title_text is None:
            m = header_regex.match(cleaned)
            if m and len(m.group(1)) == 1:
                title_text = m.group(2).strip()
                continue

        body_lines.append(line)

    return ParsedArticle(
        image_name=image_name,
        title_text=title_text,
        body_markdown="\n".join(body_lines).strip(),
    )

def display_name(p: Path) -> str:
    return p.stem.replace("_", " ")

# ----------------------------
# UI: two-mode navigator
# ----------------------------
left, right = st.columns([0.32, 0.68], gap="large")

with left:
    st.subheader("Browse")

    mode = st.radio(
        "Mode",
        ["Search", "Recent"],
        horizontal=True,
        label_visibility="visible",
    )

    selected: Optional[Path] = None

    if mode == "Search":
        q = st.text_input("Search titles", value="", placeholder="Type to filter…")
        q_norm = q.strip().lower()

        filtered = [
            p for p in files_all
            if q_norm in display_name(p).lower()
        ] if q_norm else files_all

        st.caption(f"{len(filtered)} match(es)")

        if filtered:
            selected = st.selectbox(
                "Select an insight",
                options=filtered,
                format_func=display_name,
                index=0,
                label_visibility="collapsed",
            )
        else:
            st.info("No matches. Try a different search.")

    else:
        page_size = st.selectbox("Per page", [10, 20, 30, 50], index=[10, 20, 30, 50].index(PAGE_SIZE_DEFAULT))
        total = len(files_all)
        total_pages = max(1, (total + page_size - 1) // page_size)

        if "insights_page" not in st.session_state:
            st.session_state.insights_page = 1

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("◀ Prev", use_container_width=True, disabled=st.session_state.insights_page <= 1):
                st.session_state.insights_page -= 1
        with c2:
            st.write(f"Page {st.session_state.insights_page} / {total_pages}")
        with c3:
            if st.button("Next ▶", use_container_width=True, disabled=st.session_state.insights_page >= total_pages):
                st.session_state.insights_page += 1

        start = (st.session_state.insights_page - 1) * page_size
        end = start + page_size
        page_items = files_all[start:end]

        selected = st.radio(
            "Select an insight",
            options=page_items,
            format_func=display_name,
            label_visibility="collapsed",
        )

    _sp(1)
    

with right:
    if not selected:
        st.info("Select an insight to view it.")
    else:
        lines = read_lines(selected)
        parsed = parse_article(lines)

        if parsed.image_name:
            img_path = IMAGES_DIR / parsed.image_name
            if img_path.exists():
                st.image(str(img_path), use_container_width=True)
            else:
                st.warning(f"Image not found: {img_path}")

        if parsed.title_text:
            st.header(parsed.title_text)
        else:
            st.header(display_name(selected))

        if parsed.body_markdown:
            st.markdown(parsed.body_markdown)
        else:
            st.info("This insight is empty.")

_sp(2)
if render_footer:
    render_footer()
