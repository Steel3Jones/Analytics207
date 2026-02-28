#!/usr/bin/env python3
from __future__ import annotations


import re
import pandas as pd
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


GAMES_IN = DATA_DIR / "games_raw_v30.csv"
SCORES_IN = DATA_DIR / "games_scores_v30.csv"
TRUTH_OUT = DATA_DIR / "truth.csv"



# Single canonicalization rules (keep this in ONE place)
NAMEFIXES = {
    "Sumner Charles M. Learning Campus": "Sumner Memorial",
    "Sumner Memorial": "Sumner Memorial",
    "Southern Aroostook Community School": "Southern Aroostook",
    "Van Buren District Secondary School": "Van Buren District",
    "Camden Hills Regional High School": "Camden Hills Regional",
    "Camden Hills Regional": "Camden Hills Regional",
    "Houlton High School": "Houlton HS",
    "Houlton HS": "Houlton HS",
    "Hodgdon HS": "Hodgdon HS",
    "Islesboro Central School": "Islesboro Central",
    "Cony HS": "Cony HS",
    "Fort Fairfield HS": "Fort Fairfield HS",
    "Katahdin HS": "Katahdin HS",
    "Madawaska HS": "Madawaska HS",
    "Oxford Hills Comprehensive High School": "Oxford Hills",
    "Oxford Hills Comprehensive": "Oxford Hills",
    "Penquis Valley HS": "Penquis Valley HS",
    "Rangeley Lakes Regional": "Rangeley Lakes Regional",
    "Richmond HS": "Richmond HS",
    "Searsport HS": "Searsport HS",
    "Stearns Sr.": "Stearns Sr.",
    "Temple Academy": "Temple Academy",
    "Washburn District": "Washburn District",
    "Mt. Blue": "Mount Blue",
    "Mt. Abram": "Mount Abram",
    "Mt. Ararat": "Mount Ararat",
    "DexterPCHS": "Dexter Regional",
    "Dexter Regional": "Dexter Regional",
    "Fort Kent Community": "Fort Kent Community",
    "Buckfield HS": "Buckfield HS",
    "Wiscasset HS": "Wiscasset HS",
    "Hall-Dale HS": "Hall-Dale HS",
    "Monmouth Academy": "Monmouth Academy",
    "North Yarmouth Academy": "North Yarmouth Academy",
    "Old Orchard Beach": "Old Orchard Beach",
    "Telstar Regional": "Telstar Regional",
    "Boothbay Region": "Boothbay Region",
    "Upper Kennebec Valley High School": "Valley HS",
    "Pine Tree Academy": "Pine Tree Academy",
    "Forest Hills Consolidated": "Forest Hills Consolidated",
    "Vinalhaven": "Vinalhaven",
    "Mount Blue High School": "Mount Blue",
}


def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def clean_name(x) -> str | None:
    if pd.isna(x):
        return None
    s = _norm_spaces(str(x))
    if not s:
        return None

    # normalize common patterns
    s = re.sub(r"^Mt\.?\s+", "Mount ", s)
    s = s.replace("Highschool", "High School").replace("High-school", "High School")
    s = s.replace("H.S.", "HS")

    # Strip common long-form suffixes from scores scraper
    for suffix in [
        " High School", " Regional High School", " Senior High School",
        " Academy School", " High", " School", " HS"
    ]:
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break

    s = _norm_spaces(s)
    return NAMEFIXES.get(s, s)


def main() -> None:
    print(f"Reading base games from: {GAMES_IN}")
    print(f"Reading scores from: {SCORES_IN}")

    games = pd.read_csv(GAMES_IN)
    scores = pd.read_csv(SCORES_IN)

    if "GameID" not in games.columns or "GameID" not in scores.columns:
        raise ValueError("Both inputs must contain GameID")

    # ── DEDUP scores before merge to prevent fanout ──────────────────────────
    before_dedup = len(scores)
    scores = scores.drop_duplicates(subset="GameID", keep="last")
    after_dedup = len(scores)
    if before_dedup != after_dedup:
        print(f"  ⚠ Dropped {before_dedup - after_dedup} duplicate GameIDs from scores file")
    else:
        print("✓ Scores file has unique GameID values")
    # ────────────────────────────────────────────────────────────────────────

    merged = games.merge(
        scores[["GameID", "HomeTeam", "AwayTeam", "HomeScore", "AwayScore"]],
        on="GameID",
        how="left",
        suffixes=("", "_score"),
    )

    # ── ASSERT no fanout ─────────────────────────────────────────────────────
    assert len(merged) == len(games), \
        f"Merge fanout! games={len(games)}, merged={len(merged)} — duplicate GameIDs still present"
    # ────────────────────────────────────────────────────────────────────────

    # Prefer score-side values when present
    for col in ["HomeTeam", "AwayTeam", "HomeScore", "AwayScore"]:
        scol = f"{col}_score"
        if scol in merged.columns:
            merged[col] = merged[col].where(merged[col].notna(), merged[scol])
            merged = merged.drop(columns=[scol])

    num_scored = int(pd.to_numeric(merged.get("HomeScore"), errors="coerce").notna().sum())
    print(f"✓ Games with scores after merge: {num_scored} of {len(merged)} total")

    # Canonicalize names everywhere (critical for downstream joins/pages)
    for col in ["Team1", "Team2", "HomeTeam", "AwayTeam", "Winner", "Loser"]:
        if col in merged.columns:
            merged[col] = merged[col].map(clean_name)

    # Fill home/away if missing (don't guess-flip; just fill deterministically)
    if "HomeTeam" in merged.columns and "AwayTeam" in merged.columns:
        need_ha = merged["HomeTeam"].isna() | merged["AwayTeam"].isna()
        if "Team1" in merged.columns and "Team2" in merged.columns:
            merged.loc[need_ha, "HomeTeam"] = merged.loc[need_ha, "HomeTeam"].fillna(merged.loc[need_ha, "Team1"])
            merged.loc[need_ha, "AwayTeam"] = merged.loc[need_ha, "AwayTeam"].fillna(merged.loc[need_ha, "Team2"])

    # Report true mismatches after canonicalization
    if {"Team1", "Team2", "HomeTeam", "AwayTeam"}.issubset(merged.columns):
        scored = pd.to_numeric(merged.get("HomeScore"), errors="coerce").notna()
        mismatch = merged[scored & (
            (merged["HomeTeam"].notna() & merged["Team1"].notna() & (merged["HomeTeam"] != merged["Team1"])) |
            (merged["AwayTeam"].notna() & merged["Team2"].notna() & (merged["AwayTeam"] != merged["Team2"]))
        )]
        if len(mismatch):
            print(f"WARNING: {len(mismatch)} scored games still have Team1/Team2 != Home/Away after canonicalization")
            cols = [c for c in ["GameID","Date","Gender","Team1","Team2","HomeTeam","AwayTeam","HomeScore","AwayScore"] if c in mismatch.columns]
            print(mismatch[cols].head(30))

    # ── SAFETY NET: drop unscored phantom rows ──────────────────────────────
    before = len(merged)
    merged = merged[merged["Result"] != "normal"].copy()
    after = len(merged)
    if before != after:
        print(f"  ⚠ Safety net dropped {before - after} 'normal' rows in JOIN stage")
    else:
        print("  ✓ No phantom 'normal' rows found — scraper filter working correctly")
    # ────────────────────────────────────────────────────────────────────────

    merged.to_csv(TRUTH_OUT, index=False)
    print(f"✓ Wrote {len(merged)} rows to {TRUTH_OUT}")


if __name__ == "__main__":
    main()
