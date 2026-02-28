from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import streamlit as st
import layout as L


# ----------------------------
# Page config
# ----------------------------
st.set_page_config(
    page_title="📘 Glossary (v30) | ANALYTICS207",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------
# Project paths
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # pages/ -> project root
CATALOG_PATH = PROJECT_ROOT / "data" / "metrics_catalog_v30.csv"


# ----------------------------
# Layout resolver (no layout.py edits)
# ----------------------------
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
spacer = _pick("spacer", "spacerlines")


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
if render_logo:
    render_logo()
if render_header:
    render_header(
        title="Glossary (v30)",
        definition="Searchable reference for metrics, fields, and model outputs.",
        subtitle="Backed by data/metrics_catalog_v30.csv",
    )
else:
    st.title("Glossary (v30)")
    st.caption("Backed by data/metrics_catalog_v30.csv")

_sp(1)


# ----------------------------
# Load catalog
# ----------------------------
@st.cache_data(show_spinner=False)
def load_catalog(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    return df


if not CATALOG_PATH.exists():
    st.error(f"Missing catalog file: {CATALOG_PATH}")
    st.stop()

df = load_catalog(CATALOG_PATH)

# We intentionally do NOT require/use 'source' in this UI
required = ["metric_key", "label", "group", "description", "active", "calculation"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"metrics_catalog_v30.csv is missing columns: {missing}")
    st.stop()

for c in [
    "metric_key",
    "label",
    "short_label",
    "group",
    "format",
    "unit",
    "description",
    "active",
    "calculation",
]:
    if c in df.columns:
        df[c] = df[c].astype(str).str.strip()


# ----------------------------
# Filters (TOP, full width)
# ----------------------------
st.subheader("Find metrics")

f1, f2, f3 = st.columns([0.52, 0.28, 0.20], gap="large")
with f1:
    q = st.text_input(
        "Search",
        value="",
        placeholder="Search key, label, group, description, calculation…",
    )
with f2:
    show_inactive = st.checkbox("Show inactive metrics", value=False)
with f3:
    st.caption(f"Catalog rows: {len(df):,}")

groups = sorted([g for g in df["group"].unique().tolist() if g])
group_sel = st.multiselect("Group filter", options=groups, default=[])

# Apply filters
d = df.copy()

if not show_inactive:
    d = d[d["active"] == "1"]

if group_sel:
    d = d[d["group"].isin(group_sel)]

q_norm = q.strip().lower()
if q_norm:
    hay = (
        d["metric_key"]
        + " " + d["label"]
        + " " + d.get("short_label", "")
        + " " + d["group"]
        + " " + d["description"]
        + " " + d["calculation"]
    ).str.lower()
    d = d[hay.str.contains(q_norm, na=False)]

d = d.sort_values(["group", "label", "metric_key"], ascending=[True, True, True])

st.divider()


# ----------------------------
# TWO COLUMNS ONLY: Results + Details
# ----------------------------
col_results, col_details = st.columns([0.64, 0.36], gap="large")

with col_results:
    st.subheader("Results")
    st.caption(f"{len(d):,} match(es)")

    show_cols = ["label", "metric_key", "group"]
    st.dataframe(
        d[show_cols],
        use_container_width=True,
        hide_index=True,
        height=650,
    )

    if len(d) == 0:
        selected_key = None
    else:
        selected_key = st.selectbox(
            "Select a metric",
            options=d["metric_key"].tolist(),
            index=0,
            format_func=lambda k: f"{d.loc[d['metric_key'] == k, 'label'].iloc[0]} ({k})",
        )

with col_details:
    st.subheader("Details")

    if not selected_key:
        st.info("No metric selected.")
    else:
        row = d.loc[d["metric_key"] == selected_key].iloc[0].to_dict()

        label = (row.get("label") or "").strip()
        short_label = (row.get("short_label") or "").strip()
        unit = (row.get("unit") or "").strip()
        fmt = (row.get("format") or "").strip()
        group = (row.get("group") or "").strip()
        desc = (row.get("description") or "").strip()
        calc = (row.get("calculation") or "").strip()

        st.markdown(f"### {label}")

        meta = [f"**Key:** `{selected_key}`"]
        if short_label:
            meta.append(f"**Short:** `{short_label}`")
        if group:
            meta.append(f"**Group:** {group}")
        if unit:
            meta.append(f"**Unit:** {unit}")
        if fmt:
            meta.append(f"**Format:** `{fmt}`")
        st.markdown("  \n".join(meta))

        st.markdown("#### Description")
        st.write(desc if desc else "—")

        st.markdown("#### Calculation")
        st.write(calc if calc else "Calculation note pending.")


_sp(2)
if render_footer:
    render_footer()
else:
    st.caption("© 2026 Analytics207")
