#!/usr/bin/env python3
# FIX_HOME_AWAY_TEAM_NAMES.py

from __future__ import annotations

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "data" / "truth.csv"
OUTPUT_FILE = ROOT / "data" / "truth.csv"  # overwrite in place


def first_token(x: object) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    if not s:
        return ""
    return s.split()[0].lower()


def tok_match(a: object, b: object) -> bool:
    ta = first_token(a)
    tb = first_token(b)
    return bool(ta) and bool(tb) and ta == tb


def compute_home_away(row: pd.Series) -> tuple[object, object, str]:
    """
    Returns (home_fixed, away_fixed, decision_code)

    decision_code:
      - "keep"        : keep Team1->Home, Team2->Away (because it matches)
      - "flip"        : flip Team2->Home, Team1->Away (because it matches)
      - "fill"        : Home/Away missing; fill from Team1/Team2
      - "unchanged"   : ambiguous; leave existing Home/Away as-is
      - "noop"        : missing Team1/Team2; leave as-is
    """
    t1 = row.get("Team1")
    t2 = row.get("Team2")
    home = row.get("HomeTeam")
    away = row.get("AwayTeam")

    if pd.isna(t1) or pd.isna(t2):
        return home, away, "noop"

    if pd.isna(home) or pd.isna(away):
        return t1, t2, "fill"

    keep_ok = tok_match(home, t1) and tok_match(away, t2)
    flip_ok = tok_match(home, t2) and tok_match(away, t1)

    if keep_ok and not flip_ok:
        return t1, t2, "keep"
    if flip_ok and not keep_ok:
        return t2, t1, "flip"

    # If both are true (rare token collision) or neither is true, do nothing.
    return home, away, "unchanged"


def main() -> None:
    print(f"Reading joined games from: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)

    required = {"GameID", "Team1", "Team2", "HomeTeam", "AwayTeam"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise ValueError(f"Missing required columns for home/away fix: {missing}")

    # GameID sanity
    if df["GameID"].isna().any():
        bad = df.loc[df["GameID"].isna(), ["GameID", "Date", "Gender", "Team1", "Team2"]].head(20)
        raise ValueError(f"truth.csv has null GameID values. Sample:\n{bad}")

    if df["GameID"].duplicated().any():
        dup = df.loc[df["GameID"].duplicated(), "GameID"].astype(str).unique().tolist()[:30]
        raise ValueError(f"truth.csv has duplicate GameID values (sample): {dup}")

    out = df.apply(lambda r: pd.Series(compute_home_away(r), index=["HomeTeam_fix", "AwayTeam_fix", "HAFixDecision"]), axis=1)
    df["HomeTeam"] = out["HomeTeam_fix"]
    df["AwayTeam"] = out["AwayTeam_fix"]
    df["HAFixDecision"] = out["HAFixDecision"]

    # Log what happened
    counts = df["HAFixDecision"].value_counts(dropna=False).to_dict()
    print("Home/Away fix decisions:", counts)

    amb = df.loc[df["HAFixDecision"].eq("unchanged"), ["GameID", "Date", "Gender", "Team1", "Team2", "HomeTeam", "AwayTeam"]].head(25)
    if len(amb):
        if len(amb) > 10:
            print(f"WARNING: {len(amb)} ambiguous rows could not be resolved — review manually")
    print("Ambiguous rows left unchanged — sample:")
    print(amb.to_string(index=False))


    df = df.drop(columns=["HAFixDecision"])


    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✓ Wrote {len(df)} games with fixed home/away names to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
