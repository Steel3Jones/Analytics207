from __future__ import annotations

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
    spacer,
)

from components.cards_trophy import inject_trophy_card_css, render_trophy_card

st.set_page_config(
    page_title="🏆 Trophy Room – Analytics207.com",
    page_icon="🏆",
    layout="wide",
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TROPHY_V50_FILE = DATA_DIR / "core" / "trophy_room_v50.parquet"

@st.cache_data(ttl=300)
def load_trophy_room_v50() -> pd.DataFrame:
    if TROPHY_V50_FILE.exists():
        return pd.read_parquet(TROPHY_V50_FILE)
    return pd.DataFrame()

def _last_update_mmddyyyy(df: pd.DataFrame) -> str:
    for col in ["BuildDate", "BuildTS", "LastUpdated", "UpdatedAt", "AsOfDate", "ComputedAt"]:
        if col in df.columns:
            s = df[col].dropna()
            if not s.empty:
                try:
                    dt = pd.to_datetime(s.iloc[0])
                    return dt.strftime("%m/%d/%Y")
                except Exception:
                    pass
    try:
        ts = TROPHY_V50_FILE.stat().st_mtime
        return datetime.fromtimestamp(ts).strftime("%m/%d/%Y")
    except Exception:
        return "unknown"

def _render_update_note(df: pd.DataFrame) -> None:
    asof = _last_update_mmddyyyy(df)
    st.markdown(
        f"""
        <div style="
            margin-top: 10px;
            display: flex;
            justify-content: center;
        ">
          <div style="
              font-size: 12.5px;
              line-height: 1;
              color: rgba(255,255,255,0.72);
              padding: 8px 12px;
              border-radius: 999px;
              border: 1px solid rgba(255,255,255,0.10);
              background:
                linear-gradient(90deg,
                  rgba(255,198,0,0.10) 0%,
                  rgba(255,77,77,0.08) 45%,
                  rgba(253,94,126,0.10) 100%
                );
              backdrop-filter: blur(6px);
              -webkit-backdrop-filter: blur(6px);
          ">
            Data and trophies updated nightly &bull; Last update:
            <span style="color: rgba(255,255,255,0.92)">{asof}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

apply_global_layout_tweaks()
render_logo()

render_page_header(
    title="🏆 Trophy Room",
    definition=(
        "Trophy Room (n.): Awards, champions, and season trophy leaders. "
        "Updated nightly! Can your team hold on?"
    ),
    subtitle=(
        "Statewide leaders across rating, dominance, clutch wins, "
        "home/road splits, and consistency."
    ),
)

inject_trophy_card_css()

df = load_trophy_room_v50()

if df.empty:
    st.info(
        "No trophy data available yet. "
        "Run the nightly builder to generate trophy_room_v50.parquet."
    )
    spacer(2)
    render_footer()
    st.stop()

def _sorted_vals(series: pd.Series) -> list[str]:
    vals = [x for x in series.dropna().unique().tolist() if str(x).strip() != ""]
    return sorted([str(x) for x in vals])

def _strip_trailing_dot0(s: str) -> str:
    s = str(s)
    return s[:-2] if s.endswith(".0") else s

def format_metric(trophy_name: str, x) -> str:
    if x is None:
        return ""
    try:
        v = float(x)
    except Exception:
        return str(x)

    name = (trophy_name or "").lower()

    if ("win%" in name) or ("rate" in name) or ("pct" in name) or ("25%" in name):
        txt = f"{v * 100:.1f}%" if abs(v) <= 1.5 else f"{v:.1f}%"
        return _strip_trailing_dot0(txt)

    if "margin" in name or "blowout" in name:
        txt = f"{v:+.1f}"
        return _strip_trailing_dot0(txt)

    if ("points per game" in name) or ("ppg" in name) or ("oppg" in name):
        txt = f"{v:.1f}"
        return _strip_trailing_dot0(txt)

    if (
        ("eff" in name) or ("rpi" in name) or ("sos" in name)
        or ("tsr" in name) or ("pi" in name) or ("ti" in name)
    ):
        txt = f"{v:.1f}"
        return _strip_trailing_dot0(txt)

    if "streak" in name:
        return f"{int(round(v))}"

    if abs(v) >= 100:
        return f"{v:.0f}"
    if abs(v) >= 10:
        txt = f"{v:.1f}"
        return _strip_trailing_dot0(txt)
    txt = f"{v:.2f}"
    return _strip_trailing_dot0(txt)

def scope_pill(scope: str, cls: str, region: str) -> str:
    scope  = str(scope  or "")
    cls    = str(cls    or "")
    region = str(region or "")
    if scope == "Gender":
        return "STATEWIDE"
    if scope == "GenderClass":
        return f"CLASS {cls}".strip()
    if scope == "GenderClassRegion":
        if region and cls:
            return f"{region.upper()}-{cls.upper()}"
        return "REGION"
    return "TROPHY"

CATEGORY_EMOJI = {
    "Strength & resume":    "🧾",
    "Clutch & dominance":   "🎯",
    "Offense & defense":    "🛡️",
    "Road, home & neutral": "🗺️",
    "Momentum & streaks":   "🔥",
    "Consistency & grit":   "🧱",
}

CATEGORY_VARIANT = {
    "Strength & resume":    "gold",
    "Clutch & dominance":   "red",
    "Offense & defense":    "blue",
    "Road, home & neutral": "green",
    "Momentum & streaks":   "red",
    "Consistency & grit":   "gold",
}

RIBBON_BY_CATEGORY = {
    "Strength & resume":    "ELITE",
    "Clutch & dominance":   "CLUTCH",
    "Offense & defense":    "TWO-WAY",
    "Road, home & neutral": "TRAVEL TESTED",
    "Momentum & streaks":   "HEATING UP",
    "Consistency & grit":   "STEADY",
}

def ribbon_for(cat_name: str, trophy_name: str) -> str:
    t = (trophy_name or "").lower()
    cat_name = cat_name or ""

    if "road" in t:
        return "ROAD WARRIOR"
    if "home" in t:
        return "HOME FORTRESS"
    if "neutral" in t:
        return "NEUTRAL BOSS"
    if "split" in t:
        return "SPLIT PERSONALITY"

    if "offeff" in t or "points per game" in t:
        return "FIREPOWER"
    if "defeff" in t or "toughest defense" in t:
        return "LOCKDOWN"
    if "neteff" in t:
        return "TWO-WAY"

    if "clutch" in t:
        return "CLUTCH"
    if "close" in t:
        return "CLOSEOUT"
    if "blowout" in t:
        return "POWER"

    if "last5" in t or "last10" in t:
        return "SURGING"
    if "streak" in t:
        return "ON A RUN"

    if "consistent" in t or "std" in t:
        return "STEADY"

    # "top 25% wins" and plain "win%" both route here
    if "25%" in t or "top 25" in t:
        return "GIANT KILLER"
    if "win%" in t:
        return "WINNING"

    if "tsr" in t or "rpi" in t or "sos" in t or "pi" in t or "ti" in t:
        return "ELITE"

    return RIBBON_BY_CATEGORY.get(cat_name, "TROPHY")

# ── FILTERS ──────────────────────────────────────────────────────────────────
genders = _sorted_vals(df.get("Gender", pd.Series(dtype=object)))
if not genders:
    st.error("Trophy parquet is missing Gender values.")
    spacer(2)
    render_footer()
    st.stop()

classes = ["All"] + _sorted_vals(df.get("Class",  pd.Series(dtype=object)))
regions = ["All"] + _sorted_vals(df.get("Region", pd.Series(dtype=object)))

c1, c2, c3 = st.columns(3)

default_gender_idx = genders.index("Boys") if "Boys" in genders else 0

gender = c1.selectbox("Gender", genders, index=default_gender_idx)
cls    = c2.selectbox("Class",  classes, index=0)

region_disabled = cls == "All"
region = c3.selectbox(
    "Region",
    regions,
    index=0,
    disabled=region_disabled,
    help=("Pick a Class to enable Region filtering." if region_disabled else None),
)

if cls == "All":
    region = "All"

if cls == "All" and region == "All":
    scope = "Gender"
elif region == "All":
    scope = "GenderClass"
else:
    scope = "GenderClassRegion"

view = df[df["Scope"].astype(str).eq(scope)].copy()
view = view[view["Gender"].astype(str).eq(gender)]

if scope in ("GenderClass", "GenderClassRegion") and cls != "All":
    view = view[view["Class"].astype(str).eq(cls)]
if scope == "GenderClassRegion" and region != "All":
    view = view[view["Region"].astype(str).eq(region)]

if view.empty:
    st.info("No trophy winners for this slice yet.")
    spacer(2)
    render_footer()
    st.stop()

if "CategorySort" not in view.columns:
    view["CategorySort"] = 99
if "TrophySort" not in view.columns:
    view["TrophySort"] = 0

view = view.sort_values(
    ["CategorySort", "Category", "TrophySort", "TrophyName"],
    ascending=[True, True, True, True],
    na_position="last",
)

# ── RENDER CARDS ─────────────────────────────────────────────────────────────
for (cat_name, cat_sort), group in view.groupby(
    ["Category", "CategorySort"], sort=False, dropna=False
):
    cat_name = cat_name if isinstance(cat_name, str) and cat_name.strip() else "Other"
    emoji   = CATEGORY_EMOJI.get(cat_name, "🏆")
    variant = CATEGORY_VARIANT.get(cat_name, "gold")

    st.markdown(f"### {emoji} {cat_name}")

    cols = st.columns(4)
    for i, row in enumerate(group.itertuples(index=False)):
        trophy_name = getattr(row, "TrophyName", cat_name)
        metric_txt  = format_metric(trophy_name, getattr(row, "CardMetric", None))
        pill        = scope_pill(
            getattr(row, "Scope",  scope),
            getattr(row, "Class",  cls    if cls    != "All" else ""),
            getattr(row, "Region", region if region != "All" else ""),
        )
        ribbon_text = ribbon_for(cat_name, str(trophy_name))

        render_trophy_card(
            cols[i % 4],
            kicker=str(trophy_name),
            title=getattr(row, "CardTitle", ""),
            sub=getattr(row, "CardSub", ""),
            metric=metric_txt,
            pill=pill,
            variant=variant,
            ribbon_text=ribbon_text,
        )

    spacer(1)

_render_update_note(df)
spacer(2)
render_footer()
