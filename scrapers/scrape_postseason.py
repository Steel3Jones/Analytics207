#!/usr/bin/env python3
"""
scrapers/scrape_postseason.py
Region determined by: 1) manual overrides, 2) parquet team lookup
Writes:
  - data/tournament/tournament_2026_bracket.csv   (raw scraped + patched)
  - data/tournament/2026/tournament_2026.parquet  (enriched with predictions)
"""

from __future__ import annotations
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEAMS_PATH   = PROJECT_ROOT / "data" / "core" / "teams_team_season_core_v50.parquet"
OUT_PATH     = PROJECT_ROOT / "data" / "tournament" / "tournament_2026_bracket.csv"
PARQUET_OUT  = PROJECT_ROOT / "data" / "tournament" / "2026" / "tournament_2026.parquet"

CURRENT_SEASON = 2026

CLASS_MAP   = {2: "A", 3: "B", 4: "C", 5: "D", 9: "S"}
TOURNAMENTS = {"Boys": 100, "Girls": 101}
BASE_URL    = "https://www.mpa.cc/TournamentCentralBrackets.aspx?TournamentID={tid}&DivisionID={did}"

ROUND_NORM = {
    "preliminary": "Prelim",
    "quarterfinal": "QF",
    "semifinal": "SF",
    "regional final": "Final",
    "state final": "State",
}

# ── Manual patches ─────────────────────────────────────────────────────────
POST_SCRAPE_PATCHES: list[dict] = [
    dict(Season=2026, Gender="Boys", Class="D", Region="North",
         Round="QF", GameID="2026-BD-N-QF4",
         Seed1=1, Team1="Machias Memorial", Score1=None,
         Seed2=8, Team2="Central Aroostook Sr", Score2=None),

    dict(Season=2026, Gender="Boys", Class="D", Region="North",
         Round="SF", GameID="2026-BD-N-SF2",
         Seed1=1, Team1="Machias Memorial", Score1=None,
         Seed2=5, Team2="Hodgdon HS", Score2=None),

    dict(Season=2026, Gender="Boys", Class="A", Region="South",
         Round="SF", GameID="2026-BA-S-SF-SCH",
         Seed1=8, Team1="Scarborough", Score1=59,
         Seed2=5, Team2="Cheverus", Score2=68),

    dict(Season=2026, Gender="Boys", Class="A", Region="South",
         Round="SF", GameID="2026-BA-S-SF-POR",
         Seed1=6, Team1="Portland", Score1=61,
         Seed2=2, Team2="Sanford", Score2=51),

    dict(Season=2026, Gender="Boys", Class="A", Region="North",
         Round="Final", GameID="2026-BA-N-F1",
         Seed1=1, Team1="Camden Hills Regional", Score1=None,
         Seed2=3, Team2="Brunswick", Score2=None),

    dict(Season=2026, Gender="Boys", Class="A", Region="South",
         Round="Final", GameID="2026-BA-S-F1",
         Seed1=5, Team1="Cheverus", Score1=None,
         Seed2=6, Team2="Portland", Score2=None),
]

TEAM_REGION_OVERRIDES: dict[str, str] = {
    "machias":              "North",  "central aroostook":    "North",
    "fort fairfield":       "North",  "fort kent":            "North",
    "bangor christian":     "North",  "hodgdon":              "North",
    "katahdin":             "North",  "madawaska":            "North",
    "penobscot valley":     "North",  "deer isle stonington": "North",
    "easton":               "North",  "jonesport beals":      "North",
    "lee academy":          "North",  "penquis valley":       "North",
    "piscataquis":          "North",  "schenck":              "North",
    "southern aroostook":   "North",  "stearns":              "North",
    "van buren":            "North",  "washburn":             "North",
    "wisdom":               "North",  "woodland":             "North",
    "buckfield":            "South",  "carrabec":             "South",
    "forest hills":         "South",  "islesboro":            "South",
    "madison":              "South",  "monmouth":             "South",
    "mount abram":          "South",  "old orchard beach":    "South",
    "pine tree":            "South",  "richmond":             "South",
    "temple":               "South",  "vinalhaven":           "South",
    "wiscasset":            "South",
    "ashland":              "North",  "east grand":           "North",
    "narraguagus":          "North",  "searsport":            "North",
    "shead":                "North",
    "greenville":           "South",  "north haven":          "South",
    "rangeley":             "South",  "upper kennebec":       "South",
    "valley":               "South",
    "mt abram":             "South",
    "north yarmouth":       "South",
    "south portland":       "South",
    "portland":             "South",
    "scarborough":          "South",
    "cheverus":             "South",
    "sanford":              "South",
    "windham":              "South",
    "thornton academy":     "South",
    "bonny eagle":          "South",
    "kennebunk":            "South",
    "westbrook":            "South",
    "massabesic":           "South",
    "falmouth":             "South",
    "camden hills":         "North",
    "brunswick":            "North",
    "edward little":        "North",
    "hampden academy":      "North",
    "skowhegan":            "North",
    "bangor":               "North",
    "lewiston":             "North",
    "mt blue":              "North",
}


def normalize_name(name: str) -> str:
    n = name.lower().strip()
    n = n.replace("-", " ").replace(".", "").replace("/", " ")
    for suffix in [" high school", " hs", " regional", " community", " academy",
                   " area", " school", " senior", " sr", " consolidated",
                   " consolidate", " district", " memorial", " pchs"]:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    n = re.sub(r"[^a-z0-9 ]", "", n).strip()
    n = re.sub(r"\bmt\b", "mount", n)
    return n




def build_region_lookup(gender: str, cls: str) -> dict[str, str]:
    if not TEAMS_PATH.exists():
        return {}
    df = pd.read_parquet(TEAMS_PATH)
    for col in ["Team", "Gender", "Class", "Region"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
    if "Class" in df.columns:
        df["Class"] = (df["Class"].str.upper()
                       .str.replace("CLASS", "", regex=False)
                       .str.replace(" ", "", regex=False).str.strip())
    if "Region" in df.columns:
        df["Region"] = df["Region"].str.title()
    mask = (df["Gender"] == gender.title()) & (df["Class"] == cls.upper())
    sub  = df[mask][["Team", "Region"]].dropna()
    return {normalize_name(t): r for t, r in zip(sub["Team"], sub["Region"])}


def lookup_region(team_name: str, parquet_lookup: dict[str, str]) -> str | None:
    key = normalize_name(team_name)

    if key in TEAM_REGION_OVERRIDES:
        return TEAM_REGION_OVERRIDES[key]
    if key in parquet_lookup:
        return parquet_lookup[key]

    best_match, best_region = "", None
    for lk, region in parquet_lookup.items():
        if len(lk) > len(best_match):
            if lk == key or f" {lk} " in f" {key} " or f" {lk} " in f" {key} ":
                best_match = lk
                best_region = region
    if best_region:
        return best_region

    best_match, best_region = "", None
    for ok, region in TEAM_REGION_OVERRIDES.items():
        if len(ok) > len(best_match):
            if ok == key or f" {ok} " in f" {key} " or f" {key} " in f" {ok} ":
                best_match = ok
                best_region = region
    return best_region


def parse_game_text(text: str) -> dict | None:
    text = re.sub(r"\(\d+\s*OT\)", "", text, flags=re.IGNORECASE).strip()
    tokens = text.split()
    if len(tokens) < 4:
        return None

    def is_int(s): return re.fullmatch(r"\d+", s) is not None

    if not is_int(tokens[0]):
        return None

    seed1   = int(tokens[0])
    int_pos = [i for i in range(1, len(tokens)) if is_int(tokens[i])]
    if len(int_pos) < 2:
        return None

    split_idx = None
    for i in range(len(int_pos) - 1):
        if int_pos[i + 1] == int_pos[i] + 1:
            split_idx = int_pos[i]
            break

    if split_idx is None:
        seed2_pos = int_pos[1]
        return dict(seed1=seed1,
                    team1=" ".join(tokens[1:seed2_pos]).strip(), score1=None,
                    seed2=int(tokens[seed2_pos]),
                    team2=" ".join(tokens[seed2_pos + 1:]).strip(), score2=None)

    team1  = " ".join(tokens[1:split_idx]).strip()
    score1 = float(tokens[split_idx])
    seed2  = int(tokens[split_idx + 1])
    rest   = tokens[split_idx + 2:]

    if rest and re.fullmatch(r"\d{1,3}", rest[-1]):
        score2 = float(rest[-1])
        team2  = " ".join(rest[:-1]).strip()
    else:
        score2 = None
        team2  = " ".join(rest).strip()

    return dict(seed1=seed1, team1=team1, score1=score1,
                seed2=seed2, team2=team2, score2=score2) if team1 and team2 else None


def scrape_bracket(gender: str, cls: str, tid: int, did: int) -> list[dict]:
    url  = BASE_URL.format(tid=tid, did=did)
    soup = BeautifulSoup(requests.get(url, timeout=15).text, "html.parser")

    parquet_lookup = build_region_lookup(gender, cls)
    rows           = []
    game_counts    = {"North": {v: 0 for v in ROUND_NORM.values()},
                      "South": {v: 0 for v in ROUND_NORM.values()},
                      "Unknown": {v: 0 for v in ROUND_NORM.values()}}
    current_round  = "QF"

    for tag in soup.find_all(True):
        text  = tag.get_text(" ", strip=True)
        lower = text.lower()

        if not tag.find("a") and len(text) < 60:
            for key, val in ROUND_NORM.items():
                if lower.startswith(key):
                    if val != current_round:
                        print(f"  [{gender} {cls}] Round → {val}  "
                              f"(tag={tag.name}, text={text[:60]})")
                    current_round = val
                    break

        a_tag = tag.find("a", recursive=False)
        if a_tag:
            raw_text = re.sub(r"\(\d+\s*OT\)", "", a_tag.get_text(" ", strip=True),
                              flags=re.IGNORECASE).strip()
        elif tag.name == "li" and not tag.find("a"):
            raw_text = re.sub(r"\(\d+\s*OT\)", "", text, flags=re.IGNORECASE).strip()
        else:
            continue

        parsed = parse_game_text(raw_text)
        if not parsed:
            continue
        if len(parsed["team1"]) < 3 or len(parsed["team2"]) < 3:
            continue

        region = (lookup_region(parsed["team1"], parquet_lookup)
               or lookup_region(parsed["team2"], parquet_lookup)
               or "Unknown")

        if region == "Unknown" and parsed["team1"] in ("A", "B", "C", "D", "S"):
            continue

        game_counts[region][current_round] += 1
        n       = game_counts[region][current_round]
        abbr    = {"Prelim": "P", "QF": "QF", "SF": "SF",
                   "Final": "F", "State": "ST"}.get(current_round, current_round)
        game_id = f"{CURRENT_SEASON}-{gender[0]}{cls}-{region[0]}-{abbr}{n}"

        print(f"  [{gender} {cls}] {current_round} | {region} | "
              f"#{parsed['seed1']} {parsed['team1']} vs "
              f"#{parsed['seed2']} {parsed['team2']}")

        rows.append(dict(
            Season=CURRENT_SEASON, Gender=gender, Class=cls, Region=region,
            Round=current_round, GameID=game_id,
            Seed1=parsed["seed1"], Team1=parsed["team1"], Score1=parsed["score1"],
            Seed2=parsed["seed2"], Team2=parsed["team2"], Score2=parsed["score2"],
        ))

    scored   = [r for r in rows if r["Score1"] is not None and r["Score2"] is not None]
    unscored = [r for r in rows if not (r["Score1"] is not None and r["Score2"] is not None)]

    seen: dict[tuple, set] = {}
    kept = []

    for r in scored:
        key = (r["Region"], r["Round"])
        seen.setdefault(key, set())
        t1 = normalize_name(r["Team1"])
        t2 = normalize_name(r["Team2"])
        if t1 not in seen[key] and t2 not in seen[key]:
            seen[key].update([t1, t2])
            kept.append(r)

    for r in unscored:
        key = (r["Region"], r["Round"])
        seen.setdefault(key, set())
        t1 = normalize_name(r["Team1"])
        t2 = normalize_name(r["Team2"])
        if t1 not in seen[key] and t2 not in seen[key]:
            seen[key].update([t1, t2])
            kept.append(r)

    return kept


def build_parquet(df: pd.DataFrame) -> None:
    if TEAMS_PATH.exists():
        teams_df = pd.read_parquet(TEAMS_PATH)
        for c in ["Team", "Gender", "Class", "Region"]:
            if c in teams_df.columns:
                teams_df[c] = teams_df[c].astype(str).str.strip()
        if "Gender" in teams_df.columns:
            teams_df["Gender"] = teams_df["Gender"].str.title()
        if "Class" in teams_df.columns:
            teams_df["Class"] = (teams_df["Class"].str.upper()
                                 .str.replace("CLASS", "", regex=False)
                                 .str.replace(" ", "", regex=False).str.strip())
        if "Region" in teams_df.columns:
            teams_df["Region"] = teams_df["Region"].str.title()
        teams_df["_norm"] = teams_df["Team"].apply(normalize_name)
    else:
        teams_df = pd.DataFrame()

    def find_team(team_name, gender, cls, region):
        if teams_df.empty or "NetEff" not in teams_df.columns:
            return None
        norm = normalize_name(team_name)
        m = teams_df[
            (teams_df["_norm"] == norm) &
            (teams_df["Gender"] == gender) &
            (teams_df["Class"] == cls) &
            (teams_df["Region"] == region)
        ]
        if not m.empty:
            return m.iloc[0]
        m = teams_df[
            (teams_df["_norm"] == norm) &
            (teams_df["Gender"] == gender) &
            (teams_df["Class"] == cls)
        ]
        if not m.empty:
            return m.iloc[0]
        return None

    prob1_list, prob2_list, margin_list = [], [], []

    for _, row in df.iterrows():
        r1 = find_team(row["Team1"], row["Gender"], row["Class"], row["Region"])
        r2 = find_team(row["Team2"], row["Gender"], row["Class"], row["Region"])
        ne1 = float(pd.to_numeric(r1["NetEff"], errors="coerce")) if r1 is not None else float("nan")
        ne2 = float(pd.to_numeric(r2["NetEff"], errors="coerce")) if r2 is not None else float("nan")

        if pd.notna(ne1) and pd.notna(ne2):
            margin = ne1 - ne2
            prob1 = float(1.0 / (1.0 + 10.0 ** (-(margin * 20.0) / 400.0)))
        else:
            margin, prob1 = 0.0, 0.5
            if r1 is None:
                print(f"  ⚠️  No match: {row['Team1']} (norm: {normalize_name(row['Team1'])})")
            if r2 is None:
                print(f"  ⚠️  No match: {row['Team2']} (norm: {normalize_name(row['Team2'])})")

        prob1_list.append(round(prob1, 4))
        prob2_list.append(round(1.0 - prob1, 4))
        margin_list.append(round(margin, 4))

    pq = df.copy()
    pq["PredWinProb1"] = prob1_list
    pq["PredWinProb2"] = prob2_list
    pq["PredMargin"]   = margin_list
    pq["PredScore1"]   = float("nan")
    pq["PredScore2"]   = float("nan")
    pq["PredTotal"]    = float("nan")
    pq["PredWinner"]   = [
        r.Team1 if p >= 0.5 else r.Team2
        for r, p in zip(df.itertuples(index=False), prob1_list)
    ]
    pq["Winner"] = pq.apply(
        lambda r: r["Team1"] if pd.notna(r["Score1"]) and pd.notna(r["Score2"])
                  and r["Score1"] > r["Score2"]
                  else (r["Team2"] if pd.notna(r["Score1"]) and pd.notna(r["Score2"])
                  else None), axis=1
    )
    pq["OT"]        = None
    pq["ScrapeUTC"] = pd.Timestamp.utcnow().isoformat()
    pq["TeamKey1"]  = (pq["Team1"].astype(str) + "|" + pq["Gender"] + "|"
                       + pq["Class"] + "|" + pq["Region"])
    pq["TeamKey2"]  = (pq["Team2"].astype(str) + "|" + pq["Gender"] + "|"
                       + pq["Class"] + "|" + pq["Region"])
    pq["PIR1"]      = float("nan")
    pq["PIR2"]      = float("nan")

    PARQUET_OUT.parent.mkdir(parents=True, exist_ok=True)
    pq.to_parquet(PARQUET_OUT, index=False)
    print(f"Saved parquet  → {PARQUET_OUT}  ({len(pq)} rows)")



def main():
    all_rows = []
    for gender, tid in TOURNAMENTS.items():
        for did, cls in CLASS_MAP.items():
            print(f"Scraping {gender} Class {cls}...")
            try:
                rows = scrape_bracket(gender, cls, tid, did)
                all_rows.extend(rows)
                print(f"  → {len(rows)} games")
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(0.5)

    df = pd.DataFrame(all_rows)

    # ── Apply manual patches ───────────────────────────────────────────────
    if POST_SCRAPE_PATCHES:
        for patch in POST_SCRAPE_PATCHES:
            if int(patch["Season"]) != CURRENT_SEASON:
                continue

            t1_norm = normalize_name(patch["Team1"])
            t2_norm = normalize_name(patch["Team2"])

            already_mask = (
                (df["Gender"] == patch["Gender"]) &
                (df["Class"]  == patch["Class"])  &
                (df["Region"] == patch["Region"]) &
                (df["Round"]  == patch["Round"])  &
                (df["Team1"].apply(normalize_name) == t1_norm) &
                (df["Team2"].apply(normalize_name) == t2_norm)
            )

            if not already_mask.any():
                df = pd.concat([df, pd.DataFrame([patch])], ignore_index=True)
                print(f"  ✏️  Patched: {patch['Gender']} {patch['Class']} "
                      f"{patch['Region']} {patch['Round']} — "
                      f"#{patch['Seed1']} {patch['Team1']} vs "
                      f"#{patch['Seed2']} {patch['Team2']}")
            elif patch.get("Score1") is not None and patch.get("Score2") is not None:
                upgrade_mask = already_mask & df["Score1"].isna()
                if upgrade_mask.any():
                    df.loc[upgrade_mask, "Score1"] = patch["Score1"]
                    df.loc[upgrade_mask, "Score2"] = patch["Score2"]
                    print(f"  ✏️  Score upgrade: {patch['Team1']} {patch['Score1']} "
                          f"vs {patch['Team2']} {patch['Score2']}")

    # ── Final dedup safety net ─────────────────────────────────────────────
    df["_done"] = df["Score1"].notna() & df["Score2"].notna()
    df = df.sort_values("_done", ascending=False)

    seen_teams: dict[tuple, set] = {}
    keep_idx = []
    for idx, row in df.iterrows():
        key = (row["Gender"], row["Class"], row["Region"], row["Round"])
        seen_teams.setdefault(key, set())
        t1 = normalize_name(str(row["Team1"]))
        t2 = normalize_name(str(row["Team2"]))
        if t1 not in seen_teams[key] and t2 not in seen_teams[key]:
            seen_teams[key].update([t1, t2])
            keep_idx.append(idx)

    df = df.loc[keep_idx].drop(columns=["_done"]).reset_index(drop=True)

    # ── Write CSV ──────────────────────────────────────────────────────────
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved CSV      → {OUT_PATH}  ({len(df)} rows)")
    print(df.groupby(["Gender", "Class", "Region", "Round"]).size().to_string())

    unknowns = df[df["Region"] == "Unknown"][["Gender", "Class", "Round", "Team1", "Team2"]]
    if not unknowns.empty:
        print("\n⚠️  UNKNOWN REGION TEAMS — add to TEAM_REGION_OVERRIDES:")
        print(unknowns.to_string(index=False))
    else:
        print("\n✅ No unknown regions!")

    # ── Write parquet ──────────────────────────────────────────────────────
    build_parquet(df)


if __name__ == "__main__":
    main()
