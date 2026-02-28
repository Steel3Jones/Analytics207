#!/usr/bin/env python
"""
build_travel_core_v26_from_directory.py

Fresh rebuild of travel_core_v26.parquet using:
- data/schooldirectory.csv           (SCHOOL NAME, ADDRESS, CITY, STATE, ZIP)
- data/games_game_core_v30.parquet   (game schedule with Home, Away)

Output:
- data/travel_core_v26.parquet       (one row per game with travel metrics)
- data/schools_geo.parquet           (School -> Lat/Lon)
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Tuple, Optional

import pandas as pd
import requests

# ---------------- CONFIG ----------------

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

SCHOOLS_FILE = DATA_DIR / "schooldirectory.csv"
GAMES_FILE   = DATA_DIR / "games_game_core_v30.parquet"
OUT_FILE     = DATA_DIR / "travel_core_v26.parquet"

# Travel assumptions (match Road Trips page)
PARENT_MPG       = 22.0
BUS_MPG          = 8.0
GAS_PRICE_PARENT = 3.50
GAS_PRICE_BUS    = 4.00
AVG_BUS_SPEED    = 45.0  # mph

# Geoapify
GEOAPIFY_API_KEY = "a16cc5bde0aa43a9b6fd21218f4b7333"
GEOCODE_URL      = "https://api.geoapify.com/v1/geocode/search"
ROUTING_URL      = "https://api.geoapify.com/v1/routing"
ROUTING_SLEEP_SEC = 0.25  # pause between routing calls


# ---------------- HELPERS ----------------


def require_files():
    missing = []
    for p in [SCHOOLS_FILE, GAMES_FILE]:
        if not p.exists():
            missing.append(str(p))
    if missing:
        raise FileNotFoundError("Missing required files:\n- " + "\n- ".join(missing))


def make_full_address(row: pd.Series) -> str:
    parts = [
        str(row.get("ADDRESS", "")).strip(),
        str(row.get("CITY",    "")).strip(),
        str(row.get("STATE",   "")).strip(),
        str(row.get("ZIP",     "")).strip(),
    ]
    return ", ".join([p for p in parts if p])


def geocode_address(addr: str) -> Tuple[Optional[float], Optional[float]]:
    params = {
        "text":   addr,
        "apiKey": GEOAPIFY_API_KEY,
        "limit":  1,
    }
    try:
        resp = requests.get(GEOCODE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data  = resp.json()
        feats = data.get("features", [])
        if not feats:
            return None, None
        props = feats[0]["properties"]
        return props.get("lat"), props.get("lon")
    except Exception as e:
        print(f"Geocode fail for {addr}: {e}", flush=True)
        return None, None


def haversine_miles(lat1, lon1, lat2, lon2) -> Optional[float]:
    try:
        if any(pd.isna([lat1, lon1, lat2, lon2])):
            return None
        R_km   = 6371.0
        phi1   = math.radians(lat1)
        phi2   = math.radians(lat2)
        dphi   = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        c  = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        km = R_km * c
        return km * 0.621371
    except Exception:
        return None


def routing_miles_minutes(lat1, lon1, lat2, lon2) -> Tuple[Optional[float], Optional[float]]:
    if any(pd.isna([lat1, lon1, lat2, lon2])):
        return None, None

    params = {
        "apiKey":    GEOAPIFY_API_KEY,
        "waypoints": f"{lon1},{lat1}|{lon2},{lat2}",  # ← FIXED: lon first
        "mode":      "drive",
    }
    try:
        resp = requests.get(ROUTING_URL, params=params, timeout=20)
        resp.raise_for_status()
        data  = resp.json()
        feats = data.get("features", [])
        if not feats:
            return None, None
        props  = feats[0]["properties"]
        dist_m = props.get("distance")
        time_s = props.get("time")
        miles   = dist_m / 1609.34     if dist_m is not None else None
        minutes = time_s / 60.0        if time_s is not None else None
        return miles, minutes
    except Exception as e:
        print(f"Routing fail for pair {lat1},{lon1} -> {lat2},{lon2}: {e}", flush=True)
        return None, None


# ---------------- MAIN BUILD STEPS ----------------


def load_schools() -> pd.DataFrame:
    df = pd.read_csv(SCHOOLS_FILE, dtype=str).fillna("")
    df = df.rename(columns={"SCHOOL NAME": "School"})
    df["FullAddress"] = df.apply(make_full_address, axis=1)
    return df


def geocode_schools(schools: pd.DataFrame) -> pd.DataFrame:
    print(f"Geocoding {len(schools)} schools...", flush=True)
    lats, lons = [], []
    for idx, row in schools.iterrows():
        if idx % 25 == 0:
            print(f"  at school {idx+1}/{len(schools)}...", flush=True)
        lat, lon = geocode_address(row["FullAddress"])
        lats.append(lat)
        lons.append(lon)
        time.sleep(0.1)
    schools["Lat"] = lats
    schools["Lon"] = lons
    return schools


def load_games() -> pd.DataFrame:
    games = pd.read_parquet(GAMES_FILE)
    if "Home" not in games.columns or "Away" not in games.columns:
        raise ValueError("games_game_core_v30.parquet must have Home and Away columns.")
    return games


def build_travel_for_games(schools_geo: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    school_lookup = schools_geo.set_index("School")[["Lat", "Lon"]].to_dict(orient="index")

    rows  = []
    total = len(games)
    print(f"Computing travel for {total} games...", flush=True)

    for idx, g in games.iterrows():
        if idx % 100 == 0:
            print(f"  at game {idx+1}/{total}...", flush=True)

        try:
            home_geo = school_lookup.get(g["Home"], {})
            away_geo = school_lookup.get(g["Away"], {})

            lat_h, lon_h = home_geo.get("Lat"), home_geo.get("Lon")
            lat_a, lon_a = away_geo.get("Lat"), away_geo.get("Lon")

            miles_oneway, minutes_oneway = routing_miles_minutes(lat_h, lon_h, lat_a, lon_a)
            if miles_oneway is None:
                miles_oneway    = haversine_miles(lat_h, lon_h, lat_a, lon_a)
                minutes_oneway  = (
                    miles_oneway / AVG_BUS_SPEED * 60.0 if miles_oneway is not None else None
                )

            miles_round = miles_oneway * 2.0 if miles_oneway is not None else None
            bus_hours   = miles_round / AVG_BUS_SPEED          if miles_round is not None else None
            parent_gas  = miles_round / PARENT_MPG * GAS_PRICE_PARENT if miles_round is not None else None
            bus_gas     = miles_round / BUS_MPG    * GAS_PRICE_BUS    if miles_round is not None else None

            row = {col: g[col] for col in games.columns}
            row.update({
                "MilesOneWay":   miles_oneway,
                "MilesRoundTrip": miles_round,
                "BusHours":      bus_hours,
                "ParentGasCost": parent_gas,
                "BusGasCost":    bus_gas,
                "TravelError":   None,
            })

        except Exception as e:
            row = {col: g[col] for col in games.columns}
            row.update({
                "MilesOneWay":   None,
                "MilesRoundTrip": None,
                "BusHours":      None,
                "ParentGasCost": None,
                "BusGasCost":    None,
                "TravelError":   str(e),
            })
            print(f"    !! error on game idx {idx}: {e}", flush=True)

        rows.append(row)
        time.sleep(ROUTING_SLEEP_SEC)

    return pd.DataFrame(rows)


def main():
    require_files()

    # ── Reuse existing schools_geo if available — skip re-geocoding ──
    geo_path = DATA_DIR / "schools_geo.parquet"
    if geo_path.exists():
        print("Loading existing schools_geo.parquet (skipping geocode step)...", flush=True)
        schools_geo = pd.read_parquet(geo_path)
    else:
        schools     = load_schools()
        schools_geo = geocode_schools(schools)
        schools_geo.to_parquet(geo_path, index=False)
        print(f"Wrote {geo_path}", flush=True)

    games        = load_games()
    travel_core  = build_travel_for_games(schools_geo, games)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    travel_core.to_parquet(OUT_FILE, index=False)
    print(f"Wrote {OUT_FILE} with {len(travel_core)} rows.", flush=True)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
