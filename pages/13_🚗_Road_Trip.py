from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
from datetime import datetime
import os

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
)
from components.cards import inject_card_css, render_card
from auth import login_gate, logout_button

# --- PAGE CONFIG ---

from sidebar_auth import render_sidebar_auth
render_sidebar_auth()

st.set_page_config(
    page_title="🚌 Road Trips – Analytics207.com",
    page_icon="🚌",
    layout="wide",
)

apply_global_layout_tweaks()
login_gate(required=False)
logout_button()

ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))


# Travel assumptions
PARENT_MPG = 22.0
BUS_MPG = 8.0
GAS_PRICE_PARENT = 3.50
GAS_PRICE_BUS = 4.00
AVG_BUS_SPEED = 45.0
CAR_SPEED_PARENT = 55.0
CO2_PER_GAL_GAS = 19.6
CO2_PER_GAL_DIESEL = 22.4
PARENT_CARS_PER_TRIP = 10
BUS_LENGTH_FEET = 40.0

# --- HELPERS ---
def _safe_z(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    std = s.std(ddof=0)
    if std == 0 or np.isnan(std):
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / std

def _bucket_load(score):
    if pd.isna(score):
        return "Medium"
    if score >= 70:
        return "Heavy"
    if score <= 40:
        return "Light"
    return "Medium"

@st.cache_data(ttl=300)
def load_data():
    travel_path = DATA_DIR / "travel_core_v50.parquet"
    teams_path  = DATA_DIR / "core" / "teams_team_season_core_v50.parquet"
    geo_path    = DATA_DIR / "schools_geo.parquet"

    if not travel_path.exists():
        st.error("Missing travel_core_v50.parquet")
        st.stop()
    if not teams_path.exists():
        st.error("Missing teams_team_season_core_v50.parquet")
        st.stop()

    travel = pd.read_parquet(travel_path)
    teams  = pd.read_parquet(teams_path)
    geo    = pd.read_parquet(geo_path) if geo_path.exists() else pd.DataFrame()

    # Drop rows with no distance data
    travel = travel[travel["MilesRoundTrip"].notna()].copy()

    # Ensure numeric
    for col in ["MilesOneWay", "MilesRoundTrip", "BusHours", "ParentGasCost", "BusGasCost",
                "HomeTI", "AwayTI", "HomeScore", "AwayScore"]:
        if col in travel.columns:
            travel[col] = pd.to_numeric(travel[col], errors="coerce")

    # Recompute gas costs from miles (more reliable than stored values)
    travel["ParentGasCost"] = travel["MilesRoundTrip"] / PARENT_MPG * GAS_PRICE_PARENT
    travel["BusGasCost"]    = travel["MilesRoundTrip"] / BUS_MPG * GAS_PRICE_BUS
    travel["BusHours"]      = travel["MilesRoundTrip"] / AVG_BUS_SPEED

    # Date fields
    travel["Date"]      = pd.to_datetime(travel["Date"], errors="coerce")
    travel["Month"]     = travel["Date"].dt.month_name()
    travel["MonthNum"]  = travel["Date"].dt.month
    travel["DayOfWeek"] = travel["Date"].dt.day_name()

    # AwayWin flag
    travel["AwayWin"] = (
        travel["WinnerTeam"].astype(str).str.strip()
        == travel["Away"].astype(str).str.strip()
    )

    # Favorite flag using TI (higher TI = better team)
    travel["AwayShouldWin"] = travel["AwayTI"] > travel["HomeTI"]

    # Upset flag — away was favored but lost, or home was favored but lost on road
    travel["Upset"] = (
        (travel["AwayShouldWin"] & ~travel["AwayWin"]) |
        (~travel["AwayShouldWin"] & travel["AwayWin"])
    )

    return travel, teams, geo


# --- LOAD ---
render_logo()
render_page_header(
    title="🚌 Road Trips",
    definition="How far does your team actually go?",
    subtitle="Miles, hours, gas money, and fairness – sliceable by gender, class, and region.",
)
st.markdown("Miles, bus hours, gas costs, travel fairness, and the stats nobody asked for.")
st.divider()

travel_core, teams_core, geo = load_data()
inject_card_css()

# Played-only slice for stats
travel_played = travel_core[travel_core["Played"].fillna(False).astype(bool)].copy()

# =====================================================================
# STATEWIDE HERO STATS — above filters
# =====================================================================
total_miles_all      = travel_played["MilesRoundTrip"].sum(skipna=True)
total_bus_gas_all    = travel_played["BusGasCost"].sum(skipna=True)
total_bus_hours_all  = travel_played["BusHours"].sum(skipna=True)
earth_circumference  = 24901.0
earths               = total_miles_all / earth_circumference
tacos                = int(total_bus_gas_all / 3.00)
school_days          = total_bus_hours_all / 6.5
buses_end_to_end_mi  = (len(travel_played) * BUS_LENGTH_FEET) / 5280.0

st.markdown("## 🌍 Statewide Season Totals")
h1, h2, h3, h4 = st.columns(4)
with h1:
    st.markdown(f"""
    <div class="ms-stat">
        <div class="ms-stat-val">{total_miles_all:,.0f}</div>
        <div class="ms-stat-lbl">Total Miles Traveled</div>
    </div>""", unsafe_allow_html=True)
with h2:
    st.markdown(f"""
    <div class="ms-stat">
        <div class="ms-stat-val">{earths:.2f}x</div>
        <div class="ms-stat-lbl">Times Around the Earth</div>
    </div>""", unsafe_allow_html=True)
with h3:
    st.markdown(f"""
    <div class="ms-stat">
        <div class="ms-stat-val">${total_bus_gas_all:,.0f}</div>
        <div class="ms-stat-lbl">School Bus Gas Cost</div>
    </div>""", unsafe_allow_html=True)
with h4:
    st.markdown(f"""
    <div class="ms-stat">
        <div class="ms-stat-val">{tacos:,}</div>
        <div class="ms-stat-lbl">🌮 Tacos That Could've Been Bought</div>
    </div>""", unsafe_allow_html=True)

st.write("")
hb1, hb2, hb3, hb4 = st.columns(4)
with hb1:
    st.markdown(f"""
    <div class="ms-stat">
        <div class="ms-stat-val">{total_bus_hours_all:,.0f}</div>
        <div class="ms-stat-lbl">Total Hours on a Bus</div>
    </div>""", unsafe_allow_html=True)
with hb2:
    st.markdown(f"""
    <div class="ms-stat">
        <div class="ms-stat-val">{school_days:,.1f}</div>
        <div class="ms-stat-lbl">Equivalent School Days on a Bus</div>
    </div>""", unsafe_allow_html=True)
with hb3:
    st.markdown(f"""
    <div class="ms-stat">
        <div class="ms-stat-val">{buses_end_to_end_mi:,.1f} mi</div>
        <div class="ms-stat-lbl">Buses End-to-End in Miles</div>
    </div>""", unsafe_allow_html=True)
with hb4:
    co2_tons = (total_miles_all / BUS_MPG * CO2_PER_GAL_DIESEL) / 2000
    flights   = co2_tons / 0.045  # ~0.045 tons CO2 per BOS→NYC flight
    st.markdown(f"""
    <div class="ms-stat">
        <div class="ms-stat-val">{co2_tons:,.1f} tons</div>
        <div class="ms-stat-lbl">CO₂ (≈ {flights:,.0f} BOS→NYC flights)</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# =====================================================================
# BUILD TEAM TRAVEL TABLE
# =====================================================================
team_travel = (
    travel_core.groupby("AwayKey")
    .agg(
        SeasonMiles    =("MilesRoundTrip", "sum"),
        Trips          =("GameID",         "count"),
        AvgMiles       =("MilesRoundTrip", "mean"),
        LongestTrip    =("MilesOneWay",    "max"),
        TotalBusHours  =("BusHours",       "sum"),
        TotalParentGasCost=("ParentGasCost","sum"),
        TotalBusGasCost   =("BusGasCost",   "sum"),
    )
    .reset_index()
)

meta_cols = [c for c in ["TeamKey", "Team", "Gender", "Class", "Region"] if c in teams_core.columns]
team_travel = team_travel.merge(
    teams_core[meta_cols],
    left_on="AwayKey", right_on="TeamKey",
    how="left",
)

# Road record
road_results = travel_played.copy()
road_summary = (
    road_results.groupby("AwayKey")
    .agg(RoadGames=("GameID", "count"), RoadWins=("AwayWin", "sum"))
    .reset_index()
)
road_summary["RoadWinPct"] = road_summary["RoadWins"] / road_summary["RoadGames"]
team_travel = team_travel.merge(road_summary, on="AwayKey", how="left")

# Fairness & load (global)
if all(c in team_travel.columns for c in ["Gender", "Class", "Region"]):
    medians_all = team_travel.groupby(["Gender", "Class", "Region"])["SeasonMiles"].transform("median")
    with np.errstate(divide="ignore", invalid="ignore"):
        team_travel["FairnessIndex"] = (team_travel["SeasonMiles"] - medians_all) / medians_all
else:
    team_travel["FairnessIndex"] = np.nan

load_raw = 0.7 * _safe_z(team_travel["SeasonMiles"]) + 0.3 * _safe_z(team_travel["Trips"])
mn, mx = np.nanmin(load_raw), np.nanmax(load_raw)
team_travel["TravelLoadScore"] = 100 * (load_raw - mn) / (mx - mn) if mx > mn else 50.0
team_travel["TravelLoadBucket"] = team_travel["TravelLoadScore"].apply(_bucket_load)
team_travel["ParentCarHours"]   = team_travel["SeasonMiles"] / CAR_SPEED_PARENT

# =====================================================================
# GLOBAL FILTERS
# =====================================================================
f1, f2, f3 = st.columns(3)
with f1:
    gender_filter = st.selectbox("Gender", ["All"] + sorted(team_travel["Gender"].dropna().unique().tolist()), index=0)
with f2:
    class_filter = st.selectbox("Class", ["All"] + sorted(team_travel["Class"].dropna().unique().tolist()), index=0)
with f3:
    region_filter = st.selectbox("Region", ["All"] + sorted(team_travel["Region"].dropna().unique().tolist()), index=0)

team_travel_f = team_travel.copy()
if gender_filter != "All":
    team_travel_f = team_travel_f[team_travel_f["Gender"] == gender_filter]
if class_filter != "All":
    team_travel_f = team_travel_f[team_travel_f["Class"] == class_filter]
if region_filter != "All":
    team_travel_f = team_travel_f[team_travel_f["Region"] == region_filter]

travel_f = travel_core[travel_core["AwayKey"].isin(team_travel_f["AwayKey"])].copy()
travel_f_played = travel_f[travel_f["Played"].fillna(False).astype(bool)].copy()

slice_label = (
    f"{gender_filter if gender_filter != 'All' else 'All genders'}, "
    f"Class {class_filter if class_filter != 'All' else 'All'}, "
    f"{region_filter if region_filter != 'All' else 'All regions'}"
)
st.caption(f"Showing: {slice_label}")
st.divider()

# =====================================================================
# 1) HERO KPIs
# =====================================================================
total_miles      = travel_f["MilesRoundTrip"].sum(skipna=True)
total_bus_hours  = travel_f["BusHours"].sum(skipna=True)
total_parent_gas = travel_f["ParentGasCost"].sum(skipna=True)
total_bus_gas    = travel_f["BusGasCost"].sum(skipna=True)
n_teams          = team_travel_f["AwayKey"].nunique()

girls_keys  = team_travel_f[team_travel_f["Gender"] == "Girls"]["AwayKey"].tolist()
boys_keys   = team_travel_f[team_travel_f["Gender"] == "Boys"]["AwayKey"].tolist()
girls_miles = travel_f[travel_f["AwayKey"].isin(girls_keys)]["MilesRoundTrip"].sum(skipna=True)
boys_miles  = travel_f[travel_f["AwayKey"].isin(boys_keys)]["MilesRoundTrip"].sum(skipna=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    render_card(container=c1, kicker="All teams in view", title="🚌 Total Bus Miles",
        sub=f"Round-trip miles logged ({n_teams} teams)",
        metric=f"{total_miles:,.0f} mi",
        progress=(total_miles, max(total_miles, 1.0), "#22c55e"))
with c2:
    render_card(container=c2, kicker="By gender", title="👧👦 Girls vs Boys Miles",
        sub="Round-trip miles for each gender",
        metric=f"G {girls_miles:,.0f} • B {boys_miles:,.0f} mi" if (girls_miles > 0 or boys_miles > 0) else "N/A",
        progress=(girls_miles + boys_miles, max(girls_miles + boys_miles, 1.0), "#ec4899"))
with c3:
    render_card(container=c3, kicker="Gas money", title="⛽ Parents vs School",
        sub="Estimated fuel spend in this view",
        metric=f"${total_parent_gas:,.0f} • ${total_bus_gas:,.0f}",
        progress=(total_parent_gas + total_bus_gas, max(total_parent_gas + total_bus_gas, 1.0), "#f97316"))
with c4:
    render_card(container=c4, kicker="On the road", title="⏱️ Total Bus Hours",
        sub="Round-trip hours for all away games",
        metric=f"{total_bus_hours:,.0f} hrs",
        progress=(total_bus_hours, max(total_bus_hours, 1.0), "#0ea5e9"))

st.divider()

# =====================================================================
# 2) ROAD WARRIORS
# =====================================================================
st.markdown("### 🏆 Road Warriors")
st.markdown("Teams with the **most miles** and a real away schedule (5+ road games).")

warriors = team_travel_f[team_travel_f["RoadGames"].fillna(0) >= 5].sort_values("SeasonMiles", ascending=False)

if not warriors.empty:
    top_w = warriors.iloc[0]
    w1, w2, w3 = st.columns(3)
    with w1:
        render_card(container=w1, kicker="Top Road Warrior",
            title=str(top_w.get("Team", top_w.get("AwayKey", "Unknown"))),
            sub="Most round-trip miles in this view",
            metric=f"{top_w['SeasonMiles']:,.0f} mi",
            progress=(top_w["SeasonMiles"], max(top_w["SeasonMiles"], 1.0), "#22c55e"))
    with w2:
        wins  = int(top_w.get("RoadWins", 0) or 0)
        games = int(top_w.get("RoadGames", 0) or 0)
        render_card(container=w2, kicker="Away record", title="📊 Road W–L",
            sub="From travel data",
            metric=f"{wins}-{games - wins}",
            progress=(wins, max(games, 1), "#38bdf8"))
    with w3:
        render_card(container=w3, kicker="Bus time", title="🕒 Bus Hours (RT)",
            sub="Season total for this team",
            metric=f"{top_w['TotalBusHours']:,.1f} hrs",
            progress=(top_w["TotalBusHours"], max(top_w["TotalBusHours"], 1.0), "#0ea5e9"))

    cols = [c for c in ["Team","Gender","Class","Region","SeasonMiles","Trips",
                         "RoadGames","RoadWins","RoadWinPct","TotalBusHours"] if c in warriors.columns]
    wd = warriors.head(25)[cols].copy().rename(columns={
        "SeasonMiles":"Total Miles (RT)", "Trips":"Road Trips",
        "RoadGames":"Away Games", "RoadWins":"Away Wins",
        "RoadWinPct":"Away Win %", "TotalBusHours":"Bus Hours (RT)"})
    if "Total Miles (RT)" in wd.columns:
        wd["Total Miles (RT)"] = pd.to_numeric(wd["Total Miles (RT)"], errors="coerce").round(0).astype("Int64")
    if "Away Win %" in wd.columns:
        wd["Away Win %"] = (pd.to_numeric(wd["Away Win %"], errors="coerce") * 100).round(1)
    if "Bus Hours (RT)" in wd.columns:
        wd["Bus Hours (RT)"] = pd.to_numeric(wd["Bus Hours (RT)"], errors="coerce").round(1)
    st.dataframe(wd, hide_index=True, use_container_width=True)
else:
    st.info("No teams in this view have 5+ away games.")

st.divider()

# =====================================================================
# 3) ADVANCED TRAVEL STORY
# =====================================================================
st.markdown("### 📌 Advanced Travel Story")

tts = team_travel_f.copy()
if all(c in tts.columns for c in ["Gender","Class","Region"]):
    med = tts.groupby(["Gender","Class","Region"])["SeasonMiles"].transform("median")
    with np.errstate(divide="ignore", invalid="ignore"):
        tts["FairnessIndexSlice"] = (tts["SeasonMiles"] - med) / med
else:
    tts["FairnessIndexSlice"] = np.nan

load_raw2 = 0.7 * _safe_z(tts["SeasonMiles"]) + 0.3 * _safe_z(tts["Trips"])
mn2, mx2 = np.nanmin(load_raw2) if len(load_raw2) else 0.0, np.nanmax(load_raw2) if len(load_raw2) else 0.0
tts["TravelLoadScoreSlice"]  = 100 * (load_raw2 - mn2) / (mx2 - mn2) if mx2 > mn2 else 50.0
tts["TravelLoadBucketSlice"] = tts["TravelLoadScoreSlice"].apply(_bucket_load)
tts["ParentCarHoursSlice"]   = tts["SeasonMiles"] / CAR_SPEED_PARENT

unfair_teams        = tts[pd.to_numeric(tts["FairnessIndexSlice"], errors="coerce") >= 0.40].shape[0]
heavy_teams         = tts[tts["TravelLoadBucketSlice"] == "Heavy"].shape[0]
total_parent_car_hrs= tts["ParentCarHoursSlice"].sum(skipna=True)
total_slice_miles   = tts["SeasonMiles"].sum(skipna=True)
bus_co2  = (total_slice_miles / BUS_MPG) * CO2_PER_GAL_DIESEL
cars_co2 = (total_slice_miles / PARENT_MPG * PARENT_CARS_PER_TRIP) * CO2_PER_GAL_GAS
co2_saved= max(cars_co2 - bus_co2, 0.0)

ac1, ac2, ac3, ac4 = st.columns(4)
with ac1:
    render_card(container=ac1, kicker="Fairness", title="⚖️ High Travel Burden",
        sub="Teams ≥40% above typical miles",
        metric=f"{unfair_teams} teams",
        progress=(unfair_teams, max(unfair_teams, 1.0), "#a855f7"))
with ac2:
    render_card(container=ac2, kicker="Load", title="📦 Heavy Travel Schedules",
        sub="Teams tagged as heavy loads (70+ score)",
        metric=f"{heavy_teams} teams",
        progress=(heavy_teams, max(heavy_teams, 1.0), "#3b82f6"))
with ac3:
    render_card(container=ac3, kicker="Parents", title="🚗 Parent Car Hours",
        sub="Estimated parent driving time",
        metric=f"{total_parent_car_hrs:,.0f} hrs",
        progress=(total_parent_car_hrs, max(total_parent_car_hrs, 1.0), "#f59e0b"))
with ac4:
    render_card(container=ac4, kicker="Footprint", title="🌲 Bus vs Cars CO₂",
        sub=f"1 bus vs {PARENT_CARS_PER_TRIP} cars on every trip",
        metric=f"{co2_saved:,.0f} lbs saved",
        progress=(co2_saved, max(co2_saved, 1.0), "#22c55e"))

st.divider()

# =====================================================================
# 4) ALL TEAMS TABLE
# =====================================================================
st.markdown("### 📊 All Teams: Season Travel (Round Trip)")

display_cols = [c for c in ["Team","Gender","Class","Region","SeasonMiles","Trips",
    "AvgMiles","LongestTrip","TotalBusHours","TotalParentGasCost","TotalBusGasCost",
    "TravelLoadScoreSlice","TravelLoadBucketSlice","FairnessIndexSlice","ParentCarHoursSlice"] if c in tts.columns]
df = tts[display_cols].copy().rename(columns={
    "SeasonMiles":"Season Miles (RT)", "AvgMiles":"Avg Miles/Trip",
    "LongestTrip":"Longest Trip (1-way)", "TotalBusHours":"Bus Hours (RT)",
    "TotalParentGasCost":"Parent Gas $", "TotalBusGasCost":"Bus Gas $",
    "TravelLoadScoreSlice":"Load Score", "TravelLoadBucketSlice":"Load",
    "FairnessIndexSlice":"vs Typical %", "ParentCarHoursSlice":"Parent Car Hrs"})

for col in ["Season Miles (RT)","Longest Trip (1-way)","Parent Gas $","Bus Gas $","Load Score","Parent Car Hrs"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(0).astype("Int64")
if "Avg Miles/Trip" in df.columns:
    df["Avg Miles/Trip"] = pd.to_numeric(df["Avg Miles/Trip"], errors="coerce").round(1)
if "Bus Hours (RT)" in df.columns:
    df["Bus Hours (RT)"] = pd.to_numeric(df["Bus Hours (RT)"], errors="coerce").round(1)
if "vs Typical %" in df.columns:
    df["vs Typical %"] = (pd.to_numeric(df["vs Typical %"], errors="coerce") * 100).round(0).astype("Int64")

df = df.sort_values("Season Miles (RT)", ascending=False)
st.dataframe(df, hide_index=True, use_container_width=True)
st.caption("All mileage is round-trip unless labeled one-way. Estimates use simple assumptions.")

st.divider()

# =====================================================================
# PHASE 2 — COMPETITIVE ANALYTICS
# =====================================================================
st.markdown("## 🏆 Competitive Travel Analytics")

# ── Best road record by miles traveled ───────────────────────────────
# ── Best road record by miles traveled ───────────────────────────────
st.markdown("### 📈 Best Road Record by Miles Traveled")
st.markdown("Teams that win the most despite logging the most miles.")

road_perf = team_travel_f[team_travel_f["RoadGames"].fillna(0) >= 5].copy()
road_perf = road_perf[
    road_perf["SeasonMiles"].notna() &
    road_perf["RoadWinPct"].notna() &
    (road_perf["RoadWinPct"] > 0)
].copy()

# Sort by composite: high miles AND high win %
road_perf["CompositeScore"] = road_perf["SeasonMiles"] * road_perf["RoadWinPct"]
road_perf = road_perf.sort_values("CompositeScore", ascending=False).drop(columns=["CompositeScore"])

if not road_perf.empty:
    rp_cols = [c for c in ["Team","Gender","Class","Region","SeasonMiles","RoadGames","RoadWins","RoadWinPct"] if c in road_perf.columns]
    rp = road_perf[rp_cols].copy()
    rp["SeasonMiles"] = rp["SeasonMiles"].round(0).astype("Int64")
    rp["RoadWinPct"]  = (rp["RoadWinPct"] * 100).round(1)
    rp = rp.rename(columns={
        "SeasonMiles": "Season Miles",
        "RoadGames":   "Away Games",
        "RoadWins":    "Away Wins",
        "RoadWinPct":  "Win %",
    })
    st.dataframe(rp.head(20), hide_index=True, use_container_width=True)
else:
    st.info("Not enough road games in this view.")


# ── Home court advantage by region ────────────────────────────────────
st.markdown("### 🏠 Home Court Advantage by Region")
st.markdown("Do exhausted visitors lose more in certain regions?")

if "HomeRegion" in travel_played.columns:
    hca = travel_played.copy()
    hca["HomeWin"] = ~hca["AwayWin"]
    hca_summary = (
        hca.groupby("HomeRegion")
        .agg(Games=("GameID","count"), HomeWins=("HomeWin","sum"))
        .reset_index()
    )
    hca_summary["Home Win %"] = (hca_summary["HomeWins"] / hca_summary["Games"] * 100).round(1)
    hca_summary = hca_summary.rename(columns={"HomeRegion":"Region","HomeWins":"Home Wins"})
    st.dataframe(hca_summary, hide_index=True, use_container_width=True)
else:
    st.info("HomeRegion column not found.")

st.write("")

# ── Upset rate on long trips ──────────────────────────────────────────
st.markdown("### 😱 Upset Rate on Long Trips")
st.markdown("Do favorites lose more when the away trip is 150+ miles one way?")

if "Upset" in travel_played.columns and "AwayShouldWin" in travel_played.columns:
    tp_upsets = travel_played[travel_played["HomeTI"].notna() & travel_played["AwayTI"].notna()].copy()

    short_trip = tp_upsets[tp_upsets["MilesOneWay"] < 150]
    long_trip  = tp_upsets[tp_upsets["MilesOneWay"] >= 150]

    def upset_rate(df):
        if len(df) == 0:
            return 0.0
        return df["Upset"].sum() / len(df) * 100

    upset_data = pd.DataFrame({
        "Trip Length": ["Short (<150 mi)", "Long (150+ mi)"],
        "Games": [len(short_trip), len(long_trip)],
        "Upsets": [int(short_trip["Upset"].sum()), int(long_trip["Upset"].sum())],
        "Upset Rate %": [round(upset_rate(short_trip), 1), round(upset_rate(long_trip), 1)],
    })
    st.dataframe(upset_data, hide_index=True, use_container_width=True)

    if len(long_trip) > 0 and len(short_trip) > 0:
        diff = upset_rate(long_trip) - upset_rate(short_trip)
        direction = "higher" if diff > 0 else "lower"
        st.markdown(f"📍 Upset rate on long trips is **{abs(diff):.1f}% {direction}** than on short trips.")
else:
    st.info("TI data needed for upset rate calculation.")

st.write("")

# ── Back-to-back travel games ─────────────────────────────────────────
st.markdown("### 🔁 Back-to-Back Away Games")
st.markdown("Teams that played two away games within 48 hours.")

b2b_list = []
for key, grp in travel_played.groupby("AwayKey"):
    grp = grp.sort_values("Date")
    for i in range(1, len(grp)):
        delta = (grp.iloc[i]["Date"] - grp.iloc[i-1]["Date"]).total_seconds() / 3600
        if delta <= 48:
            b2b_list.append({
                "AwayKey": key,
                "Game1": grp.iloc[i-1]["Away"] + " @ " + grp.iloc[i-1]["Home"],
                "Game2": grp.iloc[i]["Away"] + " @ " + grp.iloc[i]["Home"],
                "HoursApart": round(delta, 1),
                "Miles_G1": grp.iloc[i-1]["MilesRoundTrip"],
                "Miles_G2": grp.iloc[i]["MilesRoundTrip"],
            })

if b2b_list:
    b2b_df = pd.DataFrame(b2b_list)
    b2b_df = b2b_df.merge(teams_core[["TeamKey","Team","Gender","Class","Region"]],
                           left_on="AwayKey", right_on="TeamKey", how="left")
    b2b_df["Combined Miles"] = (b2b_df["Miles_G1"] + b2b_df["Miles_G2"]).round(0).astype("Int64")
    b2b_show = b2b_df[["Team","Gender","Class","Region","Game1","Game2","HoursApart","Combined Miles"]].copy()
    b2b_show = b2b_show.sort_values("HoursApart")
    st.dataframe(b2b_show, hide_index=True, use_container_width=True)
    st.caption(f"{len(b2b_df)} back-to-back away game pairs found statewide.")
else:
    st.info("No back-to-back away games found.")

st.write("")

# ── Travel fatigue index ──────────────────────────────────────────────
st.markdown("### 😴 Travel Fatigue Index")
st.markdown("Miles traveled in the 7 days before each game — do tired teams lose more?")

fatigue_rows = []
for key, grp in travel_played.groupby("AwayKey"):
    grp = grp.sort_values("Date")
    for i, row in grp.iterrows():
        window_start = row["Date"] - pd.Timedelta(days=7)
        prior_miles  = grp[(grp["Date"] >= window_start) & (grp["Date"] < row["Date"])]["MilesRoundTrip"].sum()
        fatigue_rows.append({
            "AwayKey": key,
            "Date": row["Date"],
            "MilesPrior7Days": prior_miles,
            "AwayWin": row["AwayWin"],
        })

if fatigue_rows:
    fatigue_df = pd.DataFrame(fatigue_rows)
    fatigue_df["FatigueBucket"] = pd.cut(
        fatigue_df["MilesPrior7Days"],
        bins=[-1, 0, 100, 250, 9999],
        labels=["Fresh (0 mi)", "Light (1–100 mi)", "Moderate (101–250 mi)", "Heavy (250+ mi)"]
    )
    fatigue_summary = (
        fatigue_df.groupby("FatigueBucket", observed=True)
        .agg(Games=("AwayWin","count"), Wins=("AwayWin","sum"))
        .reset_index()
    )
    fatigue_summary["Away Win %" ] = (fatigue_summary["Wins"] / fatigue_summary["Games"] * 100).round(1)
    fatigue_summary = fatigue_summary.rename(columns={"FatigueBucket":"Travel Load Prior 7 Days"})
    st.dataframe(fatigue_summary, hide_index=True, use_container_width=True)
    st.caption("Win % for away teams based on how many miles they logged in the 7 days before each game.")

st.divider()

# =====================================================================
# PHASE 3 — FUN / COMEDY STATS
# =====================================================================
st.markdown("## 😂 Maine Basketball By The Numbers")
st.markdown("*The stats nobody asked for but everyone needs to know.*")

# ── This week ─────────────────────────────────────────────────────────
st.markdown("### 📅 This Week in Maine Basketball Travel")

today    = pd.Timestamp(datetime.now().date())
week_ago = today - pd.Timedelta(days=7)
this_week = travel_played[(travel_played["Date"] >= week_ago) & (travel_played["Date"] <= today)]

if not this_week.empty:
    week_miles = this_week["MilesRoundTrip"].sum(skipna=True)
    week_games = len(this_week)
    week_gas   = this_week["BusGasCost"].sum(skipna=True)
    top_trip   = this_week.loc[this_week["MilesRoundTrip"].idxmax()]
    wc1, wc2, wc3 = st.columns(3)
    with wc1:
        st.metric("Miles logged this week", f"{week_miles:,.0f} mi")
    with wc2:
        st.metric("Games played", f"{week_games}")
    with wc3:
        st.metric("Bus gas this week", f"${week_gas:,.0f}")
    st.markdown(
        f"🏆 **Longest trip this week:** {top_trip['Away']} @ {top_trip['Home']} — "
        f"{top_trip['MilesRoundTrip']:,.0f} miles RT"
    )
else:
    st.info("No games found in the last 7 days.")

st.write("")

# ── North vs South ────────────────────────────────────────────────────
st.markdown("### 🧭 North vs South: Who Travels More?")

if "AwayRegion" in travel_played.columns:
    region_miles = (
        travel_played.groupby("AwayRegion")["MilesRoundTrip"]
        .agg(["sum","mean","count"])
        .reset_index()
        .rename(columns={"sum":"Total Miles","mean":"Avg Miles/Trip","count":"Trips"})
        .sort_values("Total Miles", ascending=False)
    )
    region_miles["Total Miles"]    = region_miles["Total Miles"].round(0).astype(int)
    region_miles["Avg Miles/Trip"] = region_miles["Avg Miles/Trip"].round(1)
    north_avg = region_miles[region_miles["AwayRegion"] == "North"]["Avg Miles/Trip"].values
    south_avg = region_miles[region_miles["AwayRegion"] == "South"]["Avg Miles/Trip"].values
    if len(north_avg) and len(south_avg) and south_avg[0] > 0:
        st.markdown(
            f"📍 North teams average **{north_avg[0]:.0f} miles per trip** vs "
            f"South's **{south_avg[0]:.0f} miles** — "
            f"North travels **{north_avg[0]/south_avg[0]:.1f}x more** per road game."
        )
    st.dataframe(region_miles, hide_index=True, use_container_width=True)
else:
    st.info("AwayRegion column not found.")

st.write("")

# ── Cost per road win ─────────────────────────────────────────────────
st.markdown("### 💰 Cost Per Road Win")
st.markdown("*How much bus gas does it cost to earn a win away from home?*")

road_gas_wins = (
    travel_played[travel_played["AwayWin"] == True]
    .groupby("AwayKey")
    .apply(lambda x: (x["MilesRoundTrip"].sum(skipna=True) / BUS_MPG * GAS_PRICE_BUS))
    .reset_index()
    .rename(columns={0: "Gas on Winning Trips"})
)
road_counts2 = (
    travel_played.groupby("AwayKey")
    .agg(RoadWins=("AwayWin","sum"), RoadGames=("GameID","count"))
    .reset_index()
)
cost_per_win = road_gas_wins.merge(road_counts2, on="AwayKey", how="left")
cost_per_win = cost_per_win[cost_per_win["RoadWins"] > 0].copy()
cost_per_win["Cost Per Win"] = (cost_per_win["Gas on Winning Trips"] / cost_per_win["RoadWins"]).round(2)
cost_per_win = cost_per_win.merge(
    teams_core[["TeamKey","Team","Gender","Class","Region"]],
    left_on="AwayKey", right_on="TeamKey", how="left"
)
cost_per_win = cost_per_win.sort_values("Cost Per Win")
cpw_cols = [c for c in ["Team","Gender","Class","Region","RoadWins","RoadGames","Cost Per Win"] if c in cost_per_win.columns]
cpw_display = cost_per_win[cpw_cols].copy()
cpw_display["Cost Per Win"] = cpw_display["Cost Per Win"].apply(lambda x: f"${x:,.2f}")

cc1, cc2 = st.columns(2)
with cc1:
    st.markdown("**🏆 Most Efficient (cheapest wins)**")
    st.dataframe(cpw_display.head(10), hide_index=True, use_container_width=True)
with cc2:
    st.markdown("**💸 Most Expensive Road Wins**")
    st.dataframe(cpw_display.tail(10).iloc[::-1], hide_index=True, use_container_width=True)

st.write("")

# ── Miles by month ────────────────────────────────────────────────────
st.markdown("### 📆 Miles by Month — The Season Arc")

month_order = ["November","December","January","February","March"]
monthly = (
    travel_played.groupby(["MonthNum","Month"])["MilesRoundTrip"]
    .sum().reset_index().sort_values("MonthNum")
)
monthly = monthly[monthly["Month"].isin(month_order)]

if not monthly.empty:
    max_val = monthly["MilesRoundTrip"].max()
    fig = go.Figure(go.Bar(
        x=monthly["Month"],
        y=monthly["MilesRoundTrip"].round(0),
        marker_color="#fbbf24",
        text=monthly["MilesRoundTrip"].round(0).astype(int).apply(lambda x: f"{x:,} mi"),
        textposition="outside",
    ))
    fig.update_layout(
        paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
        font=dict(color="#94a3b8"),
        yaxis=dict(showgrid=False, visible=False, range=[0, max_val * 1.25]),
        xaxis=dict(showgrid=False),
        margin=dict(t=40, b=20, l=10, r=10),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

st.write("")

# ── Most isolated program ─────────────────────────────────────────────
st.markdown("### 🏝️ Most Isolated Program")
st.markdown("*The school whose nearest opponent is still the farthest away.*")

try:
    away_min = (
        travel_played.groupby("AwayKey")["MilesOneWay"]
        .min().reset_index().rename(columns={"MilesOneWay":"Nearest Opponent (mi)"})
    )
    away_min = away_min.merge(
        teams_core[["TeamKey","Team","Gender","Class","Region"]],
        left_on="AwayKey", right_on="TeamKey", how="left"
    ).sort_values("Nearest Opponent (mi)", ascending=False)
    top_iso = away_min.head(5)[["Team","Gender","Class","Region","Nearest Opponent (mi)"]].copy()
    top_iso["Nearest Opponent (mi)"] = top_iso["Nearest Opponent (mi)"].round(1)
    st.dataframe(top_iso, hide_index=True, use_container_width=True)
except Exception as e:
    st.info(f"Isolation data unavailable: {e}")

st.write("")

# ── Team that never left their zip code ──────────────────────────────
st.markdown("### 🏡 Team That Never Left Home")
st.markdown("*Lowest total away miles — they basically walked.*")

try:
    homebodies = team_travel.sort_values("SeasonMiles").head(10)
    hb_cols = [c for c in ["Team","Gender","Class","Region","SeasonMiles","Trips"] if c in homebodies.columns]
    hb = homebodies[hb_cols].copy()
    hb["SeasonMiles"] = hb["SeasonMiles"].round(1)
    hb = hb.rename(columns={"SeasonMiles":"Total Away Miles","Trips":"Away Games"})
    st.dataframe(hb, hide_index=True, use_container_width=True)
except Exception as e:
    st.info(f"Unavailable: {e}")

st.write("")

# ── Geographic center ─────────────────────────────────────────────────
st.markdown("### 📍 Geographic Center of Maine Basketball")
st.markdown("*Weighted by games played — where does Maine basketball actually live?*")

try:
    game_counts = (
        pd.concat([
            travel_played[["Home"]].rename(columns={"Home":"School"}),
            travel_played[["Away"]].rename(columns={"Away":"School"}),
        ]).groupby("School").size().reset_index(name="Games")
    )
    geo_weighted = geo.merge(game_counts, on="School", how="inner").dropna(subset=["Lat","Lon"])
    total_gw     = geo_weighted["Games"].sum()
    center_lat   = (geo_weighted["Lat"] * geo_weighted["Games"]).sum() / total_gw
    center_lon   = (geo_weighted["Lon"] * geo_weighted["Games"]).sum() / total_gw
    geo_weighted["DistToCenter"] = ((geo_weighted["Lat"] - center_lat)**2 + (geo_weighted["Lon"] - center_lon)**2)**0.5
    nearest = geo_weighted.loc[geo_weighted["DistToCenter"].idxmin(), "School"]

    gc1, gc2 = st.columns(2)
    with gc1:
        st.markdown(f"""
        <div class="ms-card" style="text-align:center;padding:24px;">
            <div style="font-size:2rem;">📍</div>
            <div style="font-size:0.7rem;color:#fbbf24;text-transform:uppercase;letter-spacing:.08em;margin:6px 0;">Geographic Center</div>
            <div style="font-size:1.2rem;font-weight:900;color:#f1f5f9;">{center_lat:.4f}°N, {abs(center_lon):.4f}°W</div>
            <div style="font-size:0.85rem;color:#64748b;margin-top:6px;">Nearest school: <strong style="color:#94a3b8;">{nearest}</strong></div>
        </div>""", unsafe_allow_html=True)
    with gc2:
        st.markdown(f"""
        <div class="ms-card" style="padding:24px;">
            <div style="font-size:0.7rem;color:#fbbf24;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">What This Means</div>
            <div style="font-size:0.9rem;color:#94a3b8;line-height:1.6;">
                The weighted center of all Maine basketball activity this season lands near
                <strong style="color:#f1f5f9;">{nearest}</strong>.
                Schools north of this point travel significantly farther on average than those to the south.
            </div>
        </div>""", unsafe_allow_html=True)
except Exception as e:
    st.info(f"Geographic center unavailable: {e}")

st.divider()

# =====================================================================
# PHASE 4 — SPIDER MAP
# =====================================================================
st.markdown("## 🗺️ Maine Basketball Spider Map")
st.markdown("*Every road trip drawn as a line. One line per unique matchup.*")

try:
    if not geo.empty:
        geo_lookup = geo.set_index("School")[["Lat","Lon"]].to_dict("index")

        # Unique matchups only
        matchups = (
            travel_played[["Home","Away"]]
            .drop_duplicates()
        )

        fig_map = go.Figure()

        for _, row in matchups.iterrows():
            home_geo = geo_lookup.get(row["Home"])
            away_geo = geo_lookup.get(row["Away"])
            if home_geo and away_geo:
                fig_map.add_trace(go.Scattergeo(
                    lon=[away_geo["Lon"], home_geo["Lon"]],
                    lat=[away_geo["Lat"], home_geo["Lat"]],
                    mode="lines",
                    line=dict(width=1, color="#38bdf8"),
                    opacity=0.5,
                    showlegend=False,
                    hoverinfo="skip",
                ))

        # Plot schools as dots
        schools_in_play = pd.concat([
            travel_played[["Home"]].rename(columns={"Home":"School"}),
            travel_played[["Away"]].rename(columns={"Away":"School"}),
        ]).drop_duplicates()

        schools_in_play = schools_in_play.merge(geo, on="School", how="inner")

        fig_map.add_trace(go.Scattergeo(
            lon=schools_in_play["Lon"],
            lat=schools_in_play["Lat"],
            mode="markers",
            marker=dict(size=6, color="#fbbf24", opacity=0.9),
            text=schools_in_play["School"],
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        ))

        fig_map.update_layout(
            geo=dict(
                scope="usa",
                showland=True,
                landcolor="#1e293b",
                showocean=True,
                oceancolor="#0f172a",
                showlakes=True,
                lakecolor="#0f172a",
                showrivers=False,
                showcountries=False,
                showsubunits=True,
                subunitcolor="#334155",
                center=dict(lat=45.2, lon=-69.0),
                projection_scale=12,
            ),
            paper_bgcolor="#0f172a",
            margin=dict(t=10, b=10, l=0, r=0),
            height=550,
        )
        st.plotly_chart(fig_map, use_container_width=True)
        st.caption(f"{len(matchups)} unique matchups plotted. Yellow dots = schools. Blue lines = road trips.")
    else:
        st.info("schools_geo.parquet not found — spider map unavailable.")
except Exception as e:
    st.info(f"Spider map unavailable: {e}")

st.divider()

# =====================================================================
# PHASE 4 — SCHOOL TRAVEL PASSPORT
# =====================================================================
st.markdown("## 🏫 School Travel Passport")
st.markdown("*Pick any school to see their complete road trip history this season.*")

all_schools = sorted(travel_played["Away"].dropna().unique().tolist())

pp_col1, pp_col2 = st.columns([3, 1])
with pp_col1:
    selected_school = st.selectbox("Select a school", all_schools, index=0)
with pp_col2:
    school_genders = sorted(
        travel_played[travel_played["Away"] == selected_school]["Gender"]
        .dropna().unique().tolist()
    )
    selected_gender = st.selectbox("Program", school_genders, index=0)

passport = travel_played[
    (travel_played["Away"] == selected_school) &
    (travel_played["Gender"] == selected_gender)
].copy()
passport = passport.sort_values("Date")


if not passport.empty:
    total_passport_miles = passport["MilesRoundTrip"].sum()
    total_passport_wins  = passport["AwayWin"].sum()
    total_passport_games = len(passport)
    total_passport_gas   = passport["BusGasCost"].sum()

    pa1, pa2, pa3, pa4 = st.columns(4)
    with pa1:
        st.metric("Road Miles", f"{total_passport_miles:,.0f} mi")
    with pa2:
        st.metric("Road Record", f"{int(total_passport_wins)}-{total_passport_games - int(total_passport_wins)}")
    with pa3:
        st.metric("Away Games", f"{total_passport_games}")
    with pa4:
        st.metric("Est. Bus Gas", f"${total_passport_gas:,.0f}")

    passport_show = passport[["Date","Home","Away","HomeScore","AwayScore","MilesRoundTrip","BusGasCost","AwayWin"]].copy()
    passport_show["Date"]           = passport_show["Date"].dt.strftime("%b %d")
    passport_show["Result"]         = passport_show["AwayWin"].map({True:"W", False:"L"})
    passport_show["Miles (RT)"]     = passport_show["MilesRoundTrip"].round(1)
    passport_show["Est. Bus Gas"]   = passport_show["BusGasCost"].apply(lambda x: f"${x:,.2f}")
    passport_show["Score"]          = passport_show.apply(
        lambda r: f"{int(r['AwayScore'])}-{int(r['HomeScore'])}"
        if pd.notna(r["AwayScore"]) and pd.notna(r["HomeScore"]) else "—", axis=1)

    cols_show = ["Date","Home","Score","Result","Miles (RT)","Est. Bus Gas"]
    st.dataframe(passport_show[cols_show], hide_index=True, use_container_width=True)

    # Longest winning streak on the road
    streak = longest = current = 0
    for w in passport["AwayWin"]:
        if w:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    st.markdown(f"🔥 **Longest road winning streak this season:** {longest} games")

    # Record when traveling 100+ miles
    long_road = passport[passport["MilesOneWay"] >= 100]
    if not long_road.empty:
        lr_wins = int(long_road["AwayWin"].sum())
        lr_games = len(long_road)
        st.markdown(f"✈️ **Record on trips 100+ miles away:** {lr_wins}-{lr_games - lr_wins} ({lr_games} games)")
    else:
        st.markdown("✈️ No trips 100+ miles found for this school.")
else:
    st.info(f"No away games found for {selected_school}.")

render_footer()
