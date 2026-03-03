from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
import base64
from datetime import datetime

import streamlit as st
import layout as L
from auth import login_gate, logout_button
from sidebar_auth import render_sidebar_auth

st.set_page_config(
    page_title="💡 Insights | ANALYTICS207",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar_auth()

def _pick(*names: str) -> Optional[Callable]:
    for n in names:
        fn = getattr(L, n, None)
        if callable(fn):
            return fn
    return None

apply_layout  = _pick("apply_global_layout_tweaks", "applygloballayouttweaks")
render_logo   = _pick("render_logo", "renderlogo")
render_footer = _pick("render_footer", "renderfooter")
spacer        = _pick("spacer", "spacerlines")

def _sp(n: int = 1) -> None:
    if callable(spacer):
        try: spacer(n); return
        except Exception: pass
    for _ in range(max(0, int(n))): st.write("")

if apply_layout: apply_layout()
login_gate(required=False)
logout_button()

st.markdown("""
<style>
.hero-card {
    background: #1e2a3a;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.40);
    margin-bottom: 2rem;
    display: flex;
    flex-direction: column;
}
.hero-img { width: 100%; max-height: 420px; object-fit: cover; }
.hero-body { padding: 2rem 2.2rem 1.8rem; }
.hero-badge {
    display: inline-block;
    background: #e63946;
    color: #fff;
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 4px;
    margin-bottom: 0.7rem;
}
.hero-title {
    font-size: 2rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.2;
    margin: 0.3rem 0 0.7rem;
}
.hero-meta { font-size: 0.82rem; color: #a0aec0; margin-bottom: 0.9rem; }
.hero-excerpt {
    font-size: 1.05rem;
    color: #cbd5e0;
    line-height: 1.65;
    margin-bottom: 1.2rem;
}
.hero-tag {
    display: inline-block;
    background: rgba(99,102,241,0.2);
    color: #a5b4fc;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 20px;
    margin-right: 5px;
    margin-bottom: 4px;
}
.guest-badge {
    display: inline-block;
    background: #92400e;
    color: #fef3c7;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 6px;
    vertical-align: middle;
}
.article-card {
    background: #1e2a3a;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,0.30);
    margin-bottom: 1.2rem;
    transition: box-shadow 0.2s, transform 0.2s;
    cursor: pointer;
}
.article-card:hover {
    box-shadow: 0 8px 32px rgba(0,0,0,0.50);
    transform: translateY(-2px);
}
.card-img { width: 100%; height: 160px; object-fit: cover; }
.card-img-placeholder {
    width: 100%; height: 160px;
    background: linear-gradient(135deg, #1d3557 0%, #457b9d 100%);
    display: flex; align-items: center; justify-content: center;
}
.card-body { padding: 1rem 1.1rem 1rem; }
.card-title {
    font-size: 1rem;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.3;
    margin-bottom: 0.35rem;
}
.card-meta { font-size: 0.76rem; color: #a0aec0; margin-bottom: 0.5rem; }
.card-excerpt { font-size: 0.84rem; color: #cbd5e0; line-height: 1.5; }
.card-tag {
    display: inline-block;
    background: rgba(99,102,241,0.2);
    color: #a5b4fc;
    font-size: 0.68rem;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 20px;
    margin-right: 4px;
    margin-top: 6px;
}
.new-badge {
    display: inline-block;
    background: #e63946;
    color: #fff;
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 2px 7px;
    border-radius: 4px;
    margin-right: 6px;
    vertical-align: middle;
}
.reader-header {
    background: #1e2a3a;
    border-radius: 16px;
    padding: 2.5rem 3rem 2rem;
    box-shadow: 0 2px 16px rgba(0,0,0,0.30);
    margin-bottom: 1.5rem;
}
.reader-title {
    font-size: 2.1rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.2;
    margin-bottom: 0.5rem;
}
.reader-meta {
    font-size: 0.85rem;
    color: #a0aec0;
    border-bottom: 1px solid #2d3f55;
    padding-bottom: 1rem;
    margin-bottom: 0;
}
.reader-body {
    font-size: 1.05rem;
    color: #e2e8f0;
    line-height: 1.8;
    padding: 0 0.5rem;
}
.section-label {
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #a0aec0;
    margin-bottom: 1rem;
    border-bottom: 2px solid #2d3f55;
    padding-bottom: 0.4rem;
}
</style>
""", unsafe_allow_html=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSIGHTS_DIR = PROJECT_ROOT / "Insights"
IMAGES_DIR   = INSIGHTS_DIR / "images"

if not INSIGHTS_DIR.exists():
    st.error(f"Insights folder not found at {INSIGHTS_DIR}")
    st.stop()

FRONTMATTER_KEYS = {"IMAGE", "TITLE", "DATE", "AUTHOR", "TAGS", "EXCERPT", "EXTERNAL_URL"}

@dataclass
class Article:
    path: Path
    image_name: Optional[str]   = None
    title: Optional[str]        = None
    date_str: Optional[str]     = None
    author: str                 = "Analytics207 Staff"
    tags: list[str]             = field(default_factory=list)
    excerpt: Optional[str]      = None
    external_url: Optional[str] = None
    body: str                   = ""
    is_guest: bool              = False

    @property
    def date(self) -> Optional[datetime]:
        for fmt in ("%Y-%m-%d", "%Y_%m_%d", "%m/%d/%Y"):
            try: return datetime.strptime(self.date_str, fmt)
            except Exception: pass
        stem = self.path.stem
        m = re.match(r"(\d{4})_(\d{2})_(\d{2})", stem)
        if m:
            try: return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except Exception: pass
        return None

    @property
    def display_date(self) -> str:
        d = self.date
        return d.strftime("%B %d, %Y") if d else ""

    @property
    def season(self) -> str:
        d = self.date
        if not d: return "Unknown"
        y, m = d.year, d.month
        if m >= 11: return f"{y}-{y+1}"
        return f"{y-1}-{y}"

    @property
    def display_title(self) -> str:
        return self.title or self.path.stem.replace("_", " ")


def parse_article(path: Path) -> Article:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    art = Article(path=path)
    body_lines: list[str] = []
    header_done = False

    for line in lines:
        cl = line.strip().lstrip("\ufeff\u200b\u200c\u200d\u2060\u00a0")
        upper = cl.upper()

        if not header_done:
            matched = False
            for key in FRONTMATTER_KEYS:
                if upper.startswith(key + ":"):
                    val = cl[len(key)+1:].strip()
                    if key == "IMAGE":          art.image_name   = val
                    elif key == "TITLE":        art.title        = val
                    elif key == "DATE":         art.date_str     = val
                    elif key == "AUTHOR":
                        art.author   = val or "Analytics207 Staff"
                        art.is_guest = val not in ("", "Analytics207 Staff")
                    elif key == "TAGS":         art.tags         = [t.strip() for t in val.split(",") if t.strip()]
                    elif key == "EXCERPT":      art.excerpt      = val
                    elif key == "EXTERNAL_URL": art.external_url = val or None
                    matched = True
                    break
            if matched:
                continue
            if not cl:
                header_done = True
                continue
            m = re.match(r"^#\s+(.+)$", cl)
            if m and not art.title:
                art.title = m.group(1).strip()
                header_done = True
                continue

        body_lines.append(line)

    art.body = "\n".join(body_lines).strip()
    return art


def img_tag(path: Path, css_class: str, alt: str = "") -> str:
    if not path.exists():
        return '<div class="card-img-placeholder"><span style="color:#fff;font-size:2rem;">📊</span></div>'
    data = base64.b64encode(path.read_bytes()).decode()
    ext  = path.suffix.lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f'<img src="data:image/{mime};base64,{data}" class="{css_class}" alt="{alt}">'


def tag_pills(tags: list[str], cls: str = "card-tag") -> str:
    return "".join(f'<span class="{cls}">{t}</span>' for t in tags)


all_articles: list[Article] = []
for p in sorted(INSIGHTS_DIR.glob("*.md"), reverse=True):
    try:
        all_articles.append(parse_article(p))
    except Exception:
        pass

if render_logo: render_logo()

if not all_articles:
    st.info("No insights yet. Check back soon.")
    st.stop()

st.markdown(
    '<div style="padding:1.5rem 0 0.5rem;">'
    '<div style="font-size:0.72rem;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:#e63946;margin-bottom:0.3rem;">Analytics207 Publication</div>'
    '<div style="font-size:2.6rem;font-weight:900;color:#ffffff;line-height:1.1;">Insights</div>'
    '<div style="font-size:1.05rem;color:#a0aec0;margin-top:0.4rem;margin-bottom:1rem;">Where the model meets the moments — data-driven stories from gyms all over Maine.</div>'
    '</div>',
    unsafe_allow_html=True
)

seasons     = sorted({a.season for a in all_articles}, reverse=True)
all_tags    = sorted({t for a in all_articles for t in a.tags})
all_authors = sorted({a.author for a in all_articles})

fc1, fc2, fc3, fc4 = st.columns([1, 1, 1, 2])
with fc1:
    selected_season = st.selectbox("Season", ["All Seasons"] + seasons, label_visibility="visible")
with fc2:
    selected_tag = st.selectbox("Tag", ["All Tags"] + all_tags, label_visibility="visible")
with fc3:
    selected_author = st.selectbox("Author", ["All Authors"] + all_authors, label_visibility="visible")
with fc4:
    search_q = st.text_input("🔍 Search titles & excerpts", placeholder="e.g. Camden Hills, upset…")

filtered = all_articles
if selected_season != "All Seasons":
    filtered = [a for a in filtered if a.season == selected_season]
if selected_tag != "All Tags":
    filtered = [a for a in filtered if selected_tag in a.tags]
if selected_author != "All Authors":
    filtered = [a for a in filtered if a.author == selected_author]
if search_q.strip():
    q = search_q.strip().lower()
    filtered = [a for a in filtered if
                q in (a.display_title or "").lower() or
                q in (a.excerpt or "").lower()]

if "selected_insight" not in st.session_state:
    st.session_state.selected_insight = None

# ─── Reader view ──────────────────────────────────────────────────────────────
if st.session_state.selected_insight is not None:
    idx = st.session_state.selected_insight
    if 0 <= idx < len(filtered):
        art = filtered[idx]

        if st.button("← Back to Insights", key="back_btn"):
            st.session_state.selected_insight = None
            st.rerun()

        meta_parts = []
        if art.display_date: meta_parts.append(art.display_date)
        meta_parts.append(art.author)
        if art.is_guest: meta_parts.append('<span class="guest-badge">Guest</span>')
        if art.tags: meta_parts.append(tag_pills(art.tags))
        meta_html = " · ".join(meta_parts)

        if art.image_name:
            img_path = IMAGES_DIR / art.image_name
            if img_path.exists():
                st.image(str(img_path), use_container_width=True)

        st.markdown(
            '<div class="reader-header">'
            + '<div class="reader-title">' + art.display_title + '</div>'
            + '<div class="reader-meta">' + meta_html + '</div>'
            + '</div>',
            unsafe_allow_html=True
        )

        if art.external_url:
            st.markdown(
                '<a href="' + art.external_url + '" target="_blank" '
                'style="display:inline-block;margin-bottom:1.5rem;padding:10px 22px;'
                'background:#e63946;color:#fff;border-radius:8px;font-weight:700;text-decoration:none;">'
                'Read Full Article →</a>',
                unsafe_allow_html=True
            )
            if art.excerpt:
                st.markdown(art.excerpt)
        else:
            st.markdown(
                '<div class="reader-body">',
                unsafe_allow_html=True
            )
            st.markdown(art.body)
            st.markdown('</div>', unsafe_allow_html=True)

    _sp(2)
    if render_footer: render_footer()
    st.stop()

# ─── Hero ─────────────────────────────────────────────────────────────────────
if filtered:
    hero = filtered[0]
    img_html   = img_tag(IMAGES_DIR / hero.image_name, "hero-img", hero.display_title) if hero.image_name else ""
    guest_html = '<span class="guest-badge">Guest</span>' if hero.is_guest else ""
    tags_html  = tag_pills(hero.tags, "hero-tag")
    hero_meta  = hero.display_date + (" · " + hero.author if hero.author else "") + (" " + guest_html if guest_html else "")

    st.markdown(
        '<div class="hero-card">'
        + img_html
        + '<div class="hero-body">'
        + '<span class="hero-badge">★ Latest</span>'
        + '<div class="hero-title">' + hero.display_title + '</div>'
        + '<div class="hero-meta">' + hero_meta + '</div>'
        + '<div class="hero-excerpt">' + (hero.excerpt or "") + '</div>'
        + tags_html
        + '</div></div>',
        unsafe_allow_html=True
    )

    if st.button("Read Latest →", key="hero_btn", type="primary"):
        st.session_state.selected_insight = 0
        st.rerun()

# ─── Article grid ─────────────────────────────────────────────────────────────
rest = filtered[1:]
if rest:
    st.markdown('<div class="section-label">All Insights</div>', unsafe_allow_html=True)
    st.caption(f"{len(filtered)} article{'s' if len(filtered) != 1 else ''} — showing {len(rest)} below the featured post")

    PAGE_SIZE   = 9
    total_pages = max(1, (len(rest) + PAGE_SIZE - 1) // PAGE_SIZE)
    if "insights_page" not in st.session_state:
        st.session_state.insights_page = 1
    st.session_state.insights_page = min(st.session_state.insights_page, total_pages)

    start      = (st.session_state.insights_page - 1) * PAGE_SIZE
    page_items = rest[start: start + PAGE_SIZE]

    cols = st.columns(3, gap="medium")
    for i, art in enumerate(page_items):
        with cols[i % 3]:
            img_html   = img_tag(IMAGES_DIR / art.image_name, "card-img", art.display_title) if art.image_name else \
                         '<div class="card-img-placeholder"><span style="color:#fff;font-size:1.8rem;">📊</span></div>'
            new_html   = '<span class="new-badge">New</span>' if (start + i) < 3 else ""
            guest_html = '<span class="guest-badge">Guest</span>' if art.is_guest else ""
            tags_html  = tag_pills(art.tags)

            st.markdown(
                '<div class="article-card">'
                + img_html
                + '<div class="card-body">'
                + '<div class="card-meta">' + new_html + art.display_date + ' · ' + art.author + guest_html + '</div>'
                + '<div class="card-title">' + art.display_title + '</div>'
                + '<div class="card-excerpt">' + (art.excerpt or "") + '</div>'
                + '<div>' + tags_html + '</div>'
                + '</div></div>',
                unsafe_allow_html=True
            )

            if st.button("Read →", key=f"card_{start+i}", use_container_width=True):
                st.session_state.selected_insight = start + i + 1
                st.rerun()

    _sp(1)
    pc1, pc2, pc3 = st.columns([1, 2, 1])
    with pc1:
        if st.button("◀ Previous", disabled=st.session_state.insights_page <= 1, use_container_width=True):
            st.session_state.insights_page -= 1
            st.rerun()
    with pc2:
        st.markdown(
            '<div style="text-align:center;padding-top:6px;color:#a0aec0;font-size:0.85rem;">'
            + f'Page {st.session_state.insights_page} of {total_pages}</div>',
            unsafe_allow_html=True
        )
    with pc3:
        if st.button("Next ▶", disabled=st.session_state.insights_page >= total_pages, use_container_width=True):
            st.session_state.insights_page += 1
            st.rerun()

_sp(2)
if render_footer: render_footer()
