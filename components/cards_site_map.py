from __future__ import annotations

import html
import textwrap
from dataclasses import dataclass
from typing import Iterable

import streamlit as st


@dataclass(frozen=True)
class SiteSection:
    group: str        # e.g. "Core", "Ratings"
    title: str        # e.g. "Schedules"
    desc: str         # short description
    icon: str         # emoji
    path: str | None  # streamlit page path or None if disabled


def inject_site_map_card_css() -> None:
    st.markdown(
        """
        <style>
        .a207-site-map-card {
            position: relative;
            border-radius: 18px;
            padding: 1.4rem 1.6rem 1.3rem 1.6rem;
            background: radial-gradient(circle at top left, #111827, #020617);
            color: #e5e7eb;
            box-shadow:
                0 20px 35px rgba(15, 23, 42, 0.9),
                inset 0 0 0 1px rgba(148, 163, 184, 0.18);
            overflow: hidden;
        }

        .a207-site-map-card::before {
            content: "";
            position: absolute;
            inset: -40%;
            background:
                radial-gradient(circle at 0% 0%, rgba(56, 189, 248, 0.18), transparent 55%),
                radial-gradient(circle at 100% 0%, rgba(167, 139, 250, 0.16), transparent 52%);
            mix-blend-mode: screen;
            opacity: 0.85;
            pointer-events: none;
        }

        .a207-site-map-inner {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: minmax(0, 1.3fr) minmax(0, 1.7fr);
            gap: 1.4rem;
        }

        @media (max-width: 900px) {
            .a207-site-map-inner {
                grid-template-columns: minmax(0, 1fr);
            }
        }

        .a207-site-map-hero-kicker {
            font-size: 0.75rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: #a5b4fc;
            margin-bottom: 0.2rem;
            font-weight: 600;
        }

        .a207-site-map-hero-title {
            font-size: 1.65rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            color: #f9fafb;
            margin-bottom: 0.25rem;
        }

        .a207-site-map-hero-sub {
            font-size: 0.9rem;
            color: #cbd5f5;
            max-width: 34rem;
            margin-bottom: 0.7rem;
        }

        .a207-site-map-hero-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.18rem 0.65rem;
            border-radius: 999px;
            background: rgba(15, 118, 110, 0.25);
            border: 1px solid rgba(34, 197, 94, 0.35);
            color: #bbf7d0;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .a207-site-map-hero-pill-dot {
            width: 6px;
            height: 6px;
            border-radius: 999px;
            background: #22c55e;
            box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.3);
        }

        .a207-site-map-groups {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 0.55rem 0.8rem;
        }

        .a207-site-map-group {
            background: rgba(15, 23, 42, 0.88);
            border-radius: 14px;
            padding: 0.55rem 0.65rem;
            border: 1px solid rgba(148, 163, 184, 0.45);
            box-shadow:
                0 10px 18px rgba(15, 23, 42, 0.9),
                inset 0 0 0 0.5px rgba(248, 250, 252, 0.03);
        }

        .a207-site-map-group-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.35rem;
            margin-bottom: 0.35rem;
        }

        .a207-site-map-group-name {
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #e5e7eb;
        }

        .a207-site-map-group-count {
            font-size: 0.7rem;
            color: #9ca3af;
            white-space: nowrap;
        }

        .a207-site-map-links {
            display: flex;
            flex-wrap: wrap;
            gap: 0.15rem 0.35rem;
        }

        .a207-site-map-link {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.16rem 0.45rem;
            border-radius: 999px;
            background: rgba(15, 23, 42, 1.0);
            border: 1px solid rgba(75, 85, 99, 0.85);
            font-size: 0.78rem;
            color: #e5e7eb;
            cursor: pointer;
            text-decoration: none;
        }

        .a207-site-map-link span {
            white-space: nowrap;
        }

        .a207-site-map-link-disabled {
            opacity: 0.35;
            cursor: not-allowed;
        }

        .a207-site-map-link-icon {
            font-size: 0.9rem;
        }

        .a207-site-map-link-chevron {
            font-size: 0.7rem;
            opacity: 0.7;
        }

        .a207-site-map-footer {
            margin-top: 0.5rem;
            font-size: 0.75rem;
            color: #9ca3af;
        }

        .a207-site-map-footer span {
            color: #e5e7eb;
            font-weight: 500;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_site_map_card(
    sections: Iterable[SiteSection],
    *,
    kicker: str = "Explore the model",
    title: str = "Pick where you want to go next.",
    sub: str = "Every part of ANALYTICS207 is wired into the same engine — this is the map of everything that matters.",
    pill_text: str = "Live for 2025–26",
) -> None:
    inject_site_map_card_css()

    secs = list(sections)
    if not secs:
        return

    grouped: dict[str, list[SiteSection]] = {}
    for s in secs:
        grouped.setdefault(s.group, []).append(s)

    kicker_html = html.escape(kicker or "")
    title_html = html.escape(title or "")
    sub_html = html.escape(textwrap.shorten(sub or "", width=180, placeholder="…"))
    pill_html = html.escape(pill_text or "")

    # Build the HTML shell; links themselves will be streamlit elements
    st.markdown(
        f"""
        <div class="a207-site-map-card">
          <div class="a207-site-map-inner">
            <div>
              <div class="a207-site-map-hero-kicker">{kicker_html}</div>
              <div class="a207-site-map-hero-title">{title_html}</div>
              <div class="a207-site-map-hero-sub">{sub_html}</div>
              <div class="a207-site-map-hero-pill">
                <span class="a207-site-map-hero-pill-dot"></span>
                <span>{pill_html}</span>
              </div>
            </div>
            <div>
              <div class="a207-site-map-groups">
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Now render the groups and links underneath, visually sitting inside the card
    # (the CSS makes them feel like part of the same block)
    cols = st.columns(len(grouped) or 1)

    for (group_name, col) in zip(grouped.keys(), cols):
        grp_items = grouped[group_name]
        with col:
            st.markdown(
                f"""
                <div class="a207-site-map-group">
                  <div class="a207-site-map-group-header">
                    <div class="a207-site-map-group-name">{html.escape(group_name)}</div>
                    <div class="a207-site-map-group-count">{len(grp_items)} sections</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Render links under the header div
            link_container = st.container()
            with link_container:
                st.markdown(
                    '<div class="a207-site-map-links">', unsafe_allow_html=True
                )
                st.markdown("</div>", unsafe_allow_html=True)

            for s in grp_items:
                label = f"{s.icon} {s.title}".strip()
                if s.path:
                    st.page_link(s.path, label=label, icon=None, help=s.desc)
                else:
                    st.button(
                        label,
                        disabled=True,
                        help="Coming soon",
                        key=f"site_map_disabled_{group_name}_{s.title}",
                    )

    st.markdown(
        """
        <div class="a207-site-map-footer">
          All sections are powered by the same rating, schedule, and simulations stack –
          nothing lives in a silo. <span>Every click stays inside the data model.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
