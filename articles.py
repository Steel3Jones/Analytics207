from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import streamlit as st
import layout as L


st.set_page_config(
    page_title="📝 Articles | ANALYTICS207",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

def _pick(*names: str) -> Optional[Callable]:
    for n in names:
        fn = getattr(L, n, None)
        if callable(fn):
            return fn
    return None

apply_layout = _pick("apply_global_layout_tweaks", "applygloballayouttweaks")
render_logo = _pick("render_logo", "renderlogo")
render_header = _pick("render_page_header", "renderpageheader")
render_footer = _pick("render_footer", "renderfooter")

if apply_layout:
    apply_layout()
if render_logo:
    render_logo()
if render_header:
    render_header(
        title="Articles",
        definition="Short writeups with images—no blog platform needed.",
        subtitle="Drop Markdown files into /Insights and images into /Insights/images.",
    )
else:
    st.title("Articles")

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # pages/ -> project root
INSIGHTS_DIR = PROJECT_ROOT / "Insights"
IMAGES_DIR = INSIGHTS_DIR / "images"

if not INSIGHTS_DIR.exists():
    st.error(f"Insights folder not found at: {INSIGHTS_DIR}")
    st.stop()

files = sorted(INSIGHTS_DIR.glob("*.md"), reverse=True)
if not files:
    st.info("No articles yet. Add a .md file to /Insights.")
    st.stop()

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
    image_name = None
    title_text = None
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

left, right = st.columns([0.30, 0.70], gap="large")

with left:
    st.subheader("Articles")
    selected = st.radio(
        label="",
        options=files,
        format_func=lambda p: p.stem.replace("_", " "),
    )
    st.caption("Tip: Put `IMAGE: yourfile.jpg` near the top of the .md")

with right:
    parsed = parse_article(read_lines(selected))

    if parsed.image_name:
        img_path = IMAGES_DIR / parsed.image_name
        if img_path.exists():
            st.image(str(img_path), use_container_width=True)
        else:
            st.warning(f"Image not found: {img_path}")

    if parsed.title_text:
        st.header(parsed.title_text)

    if parsed.body_markdown:
        st.markdown(parsed.body_markdown)
    else:
        st.info("This article is empty.")

if render_footer:
    render_footer()
