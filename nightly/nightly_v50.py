from __future__ import annotations

# ======================================================================================
# NIGHTLY V50
# - truth.csv is the single source
# - games_game_core_v50.parquet        : lean game facts (no preds)
# - teams_team_season_core_v50.parquet : lean team-season facts (no preds)
# - teams_team_season_analytics_v50.parquet : ALL ~150 catalog metrics per team-season
# - games_analytics_v50.parquet        : ALL game-level descriptive metrics
# - games_predictions_current.parquet  : predictions (written by pred engine, untouched)
# - games_public_v50.parquet           : facts + preds + grading (public bundle)
# - calibration parquets               : performance summary, games, calibration, spread
# - nightly_report_v50.parquet         : quick stats snapshot
# ======================================================================================

from pathlib import Path
import sys
import tempfile
import importlib.util
import shutil
import json
import argparse
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = Path(r"C:\ANALYTICS207")
DATADIR = ROOT / "data"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CORE_DIR  = DATADIR / "core"
PRED_DIR  = DATADIR / "predictions"
CAL_DIR   = DATADIR / "calibration"
PUB_DIR   = DATADIR / "public"

TRUTH_PATH = DATADIR / "truth.csv"

CORE_VERSION = "v50"

# Output paths
TEAMS_CORE_V50       = CORE_DIR / "teams_team_season_core_v50.parquet"
GAMES_CORE_V50       = CORE_DIR / "games_game_core_v50.parquet"
TEAMS_ANALYTICS_V50  = CORE_DIR / "teams_team_season_analytics_v50.parquet"
GAMES_ANALYTICS_V50  = CORE_DIR / "games_analytics_v50.parquet"
PRED_CURRENT         = PRED_DIR / "games_predictions_current.parquet"
PUBLIC_V50           = PUB_DIR  / "games_public_v50.parquet"
PERF_SUMMARY_V50     = CAL_DIR  / "performance_summary_v50.parquet"
PERF_GAMES_V50       = CAL_DIR  / "performance_games_v50.parquet"
PERF_CALIB_V50       = CAL_DIR  / "performance_calibration_v50.parquet"
PERF_SPREAD_V50      = CAL_DIR  / "performance_by_spread_v50.parquet"
NIGHTLY_REPORT_V50   = CAL_DIR  / "nightly_report_v50.parquet"

PRED_ENGINE_SCRIPT = ROOT / "walkforward" / "v34" / "pred_engine_walkforward_joint.py"

PRED_COLS         = ["PredHomeWinProb", "PredMargin", "PredHomeScore", "PredAwayScore", "PredTotalPoints"]
PRED_DERIVED_COLS = ["PredWinnerKey", "PredWinnerProb", "PredWinnerProbPct", "PredSpreadAbs"]
PRED_META_COLS    = ["CoreVersion", "PredBuildID"]
PRED_ALL_COLS     = ["GameID", "HomeKey", "AwayKey"] + PRED_META_COLS + PRED_COLS + PRED_DERIVED_COLS

BANNED_FACTS_COLS = set(PRED_COLS + PRED_DERIVED_COLS + [
    "FavProb", "FavProbPct", "FavoriteIsHome", "FavoriteTeamKey", "ModelCorrect"
])

# ── Team of the Week ──────────────────────────────────────────────────────────
TOTW_DIR      = DATADIR / "totw"
TOTW_NOMINEES = TOTW_DIR / "team_of_week_nominees_v50.parquet"

# Weights
_TOTW_W_MARGIN   = 0.45
_TOTW_W_OPP      = 0.30
_TOTW_W_SURPRISE = 0.20
_TOTW_W_WINPCT   = 0.05


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

def atomic_write_parquet(df: pd.DataFrame, outpath: Path) -> None:
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet", dir=str(outpath.parent)) as tmp:
        tmppath = Path(tmp.name)
    df.to_parquet(tmppath, index=False)
    tmppath.replace(outpath)


def clean_gameids(s: pd.Series) -> pd.Series:
    x = s.astype(str).str.strip()
    x = x.str.replace(r"\.0$", "", regex=True)
    x = x.str.replace(",", "", regex=False)
    return x


def season_from_date(dt) -> str | None:
    if pd.isna(dt):
        return None
    try:
        y = dt.year
        return f"{y}-{str(y+1)[-2:]}" if dt.month >= 7 else f"{y-1}-{str(y)[-2:]}"
    except Exception:
        return None


def parse_div(div: str) -> tuple[str, str]:
    d = str(div) if div is not None else ""
    if "-" not in d:
        return ("Unknown", "Unknown")
    region, cls = d.split("-", 1)
    return (region.strip().title(), cls.strip().upper())


def build_team_key(team: str, gender: str, cls: str, region: str) -> str:
    return f"{str(team).strip()}{str(gender).strip()}{str(cls).strip()}{str(region).strip()}"


def assert_unique_key(df: pd.DataFrame, key: str, name: str) -> None:
    if key not in df.columns:
        raise RuntimeError(f"{name} missing key: {key}")
    if df[key].isna().any():
        raise RuntimeError(f"{name} has nulls in {key}")
    if df[key].duplicated().any():
        raise RuntimeError(f"{name} duplicate {key}: {int(df[key].duplicated().sum())}")


def assert_no_pred_cols(df: pd.DataFrame, name: str) -> None:
    bad = [c for c in df.columns if c in BANNED_FACTS_COLS or str(c).startswith("Pred")]
    if bad:
        raise RuntimeError(f"{name} contains banned pred columns: {bad}")


def require_non_null(df: pd.DataFrame, cols: list[str], name: str) -> None:
    bad = [c for c in cols if c in df.columns and df[c].isna().any()]
    if bad:
        raise RuntimeError(f"{name} nulls in required cols: {bad}")


# --------------------------------------------------------------------------------------
# Load truth
# --------------------------------------------------------------------------------------

def load_truth(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "ScrapedAt" in df.columns:
        df["ScrapedAt"] = pd.to_datetime(df["ScrapedAt"], errors="coerce")
    for col in ["Gender", "Team1", "Team2", "HomeTeam", "AwayTeam", "Winner", "Loser"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df["Gender"] = df["Gender"].astype(str).str.strip().str.title()
    df["Season"] = df["Date"].apply(season_from_date)
    df["GameID"] = clean_gameids(df["GameID"])
    return df


# --------------------------------------------------------------------------------------
# Build game core (lean, no preds)
# --------------------------------------------------------------------------------------


def build_games_core(truth: pd.DataFrame) -> pd.DataFrame:
    g = truth.copy()

    def build_games_core(truth: pd.DataFrame) -> pd.DataFrame:
        g = truth.copy()

    # Build division lookup from Team1 rows ONLY (authoritative)
    team_div: dict[str, str] = {}
    if "SchoolDivision" in g.columns and "Team1" in g.columns:
        for _, row in g.iterrows():
            t1  = str(row.get("Team1", "")).strip()
            div = str(row.get("SchoolDivision", "")).strip()
            if t1 and div and div != "nan":
                team_div[t1] = div

    def get_div(team: str) -> str:
        return team_div.get(str(team).strip(), "Unknown-Unknown")

    g["Home"] = g["HomeTeam"].astype(str).str.strip()
    g["Away"] = g["AwayTeam"].astype(str).str.strip()

    # Canonical team name normalization — fixes split TeamKeys from alternate spellings
    _NAME_MAP = {
    "Mount Blue High School": "Mount Blue",
    "Mt. Blue": "Mount Blue",

    "Ashland": "Ashland District",
    "Ashland Community": "Ashland District",

    "East Grand School": "East Grand",
    "East Grand HS": "East Grand",

    "Falmouth High School": "Falmouth",

    "Houlton High School": "Houlton",

    "Islesboro": "Islesboro Central",
    "Islesboro School": "Islesboro Central",

    "Fryeburg": "Fryeburg Academy",
    "Fryeburg High School": "Fryeburg Academy",
}

    g["Home"] = g["Home"].replace(_NAME_MAP)
    g["Away"] = g["Away"].replace(_NAME_MAP)


    g["HomeDivision"] = g["Home"].apply(get_div)
    g["AwayDivision"] = g["Away"].apply(get_div)

    g["HomeRegion"], g["HomeClass"] = zip(*g["HomeDivision"].map(parse_div))
    g["AwayRegion"], g["AwayClass"] = zip(*g["AwayDivision"].map(parse_div))

    g["HomeKey"] = g.apply(lambda r: build_team_key(r["Home"], r.get("Gender",""), r["HomeClass"], r["HomeRegion"]), axis=1)
    g["AwayKey"] = g.apply(lambda r: build_team_key(r["Away"], r.get("Gender",""), r["AwayClass"], r["AwayRegion"]), axis=1)

    g["HomeScore"] = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
    g["AwayScore"] = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
    g["Played"]    = g["HomeScore"].notna() & g["AwayScore"].notna()
    g["Margin"]    = np.where(g["Played"], g["HomeScore"] - g["AwayScore"], np.nan)
    g["WinnerTeam"] = np.where(
        g["Played"] & (g["HomeScore"] > g["AwayScore"]), g["Home"],
        np.where(g["Played"] & (g["AwayScore"] > g["HomeScore"]), g["Away"], None)
    )
    g["IsNeutral"] = g["HomeTeam"].astype(str).str.lower().eq(g["AwayTeam"].astype(str).str.lower())
    if "NeutralSite" in g.columns:
        g["IsNeutral"] = g["NeutralSite"].fillna(False).astype(bool)

    for c in ["TI", "PI", "Rank"]:
        if c not in g.columns:
            g[c] = np.nan

    # per-team TI/PI using Team1 rows
    tmr = g[["GameID","Team1","TI","PI","Rank"]].copy()
    tmr["Team1"] = tmr["Team1"].astype(str).str.strip()
    tmr = tmr.rename(columns={"Team1":"MT","TI":"MTI","PI":"MPI","Rank":"MRank"})
    g = g.merge(tmr[["GameID","MT","MTI","MPI","MRank"]], how="left",
                left_on=["GameID","Home"], right_on=["GameID","MT"]).drop(columns=["MT"], errors="ignore")
    g = g.rename(columns={"MTI":"HomeTI","MPI":"HomePI","MRank":"HomeRank"})
    g = g.merge(tmr[["GameID","MT","MTI","MPI","MRank"]], how="left",
                left_on=["GameID","Away"], right_on=["GameID","MT"], suffixes=("","_a")).drop(columns=["MT"], errors="ignore")
    g = g.rename(columns={"MTI":"AwayTI","MPI":"AwayPI","MRank":"AwayRank"})

    keep = ["GameID","Date","Season","Gender","Home","Away","HomeKey","AwayKey",
            "HomeClass","AwayClass","HomeRegion","AwayRegion","HomeDivision","AwayDivision",
            "HomeScore","AwayScore","Played","Margin","IsNeutral","WinnerTeam",
            "HomeTI","HomePI","HomeRank","AwayTI","AwayPI","AwayRank","ScrapedAt"]
    keep = [c for c in keep if c in g.columns]

    # drop junk teams
    g = g[g["Home"].astype(str).str.strip().str.lower() != "nan"]
    g = g[~g["Home"].astype(str).str.lower().str.contains("middle school", na=False)]
    g = g[~g["Away"].astype(str).str.lower().str.contains("middle school", na=False)]

    out = g.drop_duplicates(subset="GameID").reset_index(drop=True)[keep].copy()
    out["CoreVersion"] = CORE_VERSION
    out["GameID"] = clean_gameids(out["GameID"])
    assert_unique_key(out, "GameID", "games_core_v50")
    assert_no_pred_cols(out, "games_core_v50")
    return out



# --------------------------------------------------------------------------------------
# Build teams core (lean)
# --------------------------------------------------------------------------------------

def build_teams_core(games: pd.DataFrame) -> pd.DataFrame:
    g = games.copy()
    rows = []
    for side, key_col, team_col, for_col, against_col in [
        ("home", "HomeKey", "Home", "HomeScore", "AwayScore"),
        ("away", "AwayKey", "Away", "AwayScore", "HomeScore"),
    ]:
        tmp = g[[key_col, team_col, "Season", "Gender", for_col, against_col,
                  "Played", "IsNeutral", "HomeTI" if side=="home" else "AwayTI",
                  "HomePI" if side=="home" else "AwayPI",
                  "HomeClass" if side=="home" else "AwayClass",
                  "HomeRegion" if side=="home" else "AwayRegion"]].copy()
        tmp.columns = ["TeamKey","Team","Season","Gender","For","Against",
                       "Played","IsNeutral","TI","PI","Class","Region"]
        tmp["IsHome"] = side == "home"
        rows.append(tmp)

    long = pd.concat(rows, ignore_index=True)
    long["For"]     = pd.to_numeric(long["For"], errors="coerce")
    long["Against"] = pd.to_numeric(long["Against"], errors="coerce")
    longp = long[long["Played"].fillna(False)].copy()
    longp["Margin"] = longp["For"] - longp["Against"]
    longp["Win"]    = (longp["Margin"] > 0).astype(int)
    longp["Loss"]   = (longp["Margin"] < 0).astype(int)
    longp["Tie"]    = (longp["Margin"] == 0).astype(int)

    grp = ["TeamKey","Team","Season","Gender"]
    teams = longp.groupby(grp, dropna=False).agg(
        Class=("Class", lambda s: s.dropna().mode().iloc[0] if s.notna().any() else np.nan),
        Region=("Region", lambda s: s.dropna().mode().iloc[0] if s.notna().any() else np.nan),
        Games=("Margin","count"),
        Wins=("Win","sum"),
        Losses=("Loss","sum"),
        Ties=("Tie","sum"),
        PointsFor=("For","sum"),
        PointsAgainst=("Against","sum"),
        PPG=("For","mean"),
        OPPG=("Against","mean"),
        MarginPG=("Margin","mean"),
        TI=("TI", lambda s: pd.to_numeric(s, errors="coerce").dropna().iloc[-1] if pd.to_numeric(s, errors="coerce").notna().any() else np.nan),
        PI=("PI", lambda s: pd.to_numeric(s, errors="coerce").dropna().iloc[-1] if pd.to_numeric(s, errors="coerce").notna().any() else np.nan),
    ).reset_index()

    teams["WinPct"]  = teams["Wins"] / teams["Games"].replace(0, np.nan)
    teams["OffEff"]  = teams["PPG"]
    teams["DefEff"]  = teams["OPPG"]
    teams["NetEff"]  = teams["PPG"] - teams["OPPG"]
    teams["Record"]  = teams.apply(lambda r: f"{int(r.Wins)}-{int(r.Losses)}-{int(r.Ties)}", axis=1)
    teams["CoreVersion"] = CORE_VERSION

        # Only fill display columns — leave TI/PI as NaN so sorting works correctly
    for col in ["NetEff", "MarginPG", "PPG", "OPPG"]:
        if col in teams.columns:
            teams[col] = teams[col].fillna(0.0)



    assert_no_pred_cols(teams, "teams_core_v50")
    return teams


# --------------------------------------------------------------------------------------
# Build teams analytics (full ~150-col catalog)
# --------------------------------------------------------------------------------------

def build_teams_analytics(truth: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    t = truth.copy()
    g = games.copy()
    t["GameID"] = clean_gameids(t["GameID"])
    g["GameID"] = clean_gameids(g["GameID"])

    # Build long table from games_core (one row per team per game, both perspectives)
    # truth.csv only has home-team rows so we cannot rely on it for per-team records
    rows = []
    for side, team_col, key_col, for_col, against_col, class_col, region_col, ti_col, pi_col, rank_col, opp_team_col, opp_key_col, opp_class_col, opp_region_col, opp_pi_col in [
        ("home", "Home", "HomeKey", "HomeScore", "AwayScore", "HomeClass", "HomeRegion", "HomeTI", "HomePI", "HomeRank", "Away", "AwayKey", "AwayClass", "AwayRegion", "AwayPI"),
        ("away", "Away", "AwayKey", "AwayScore", "HomeScore", "AwayClass", "AwayRegion", "AwayTI", "AwayPI", "AwayRank", "Home", "HomeKey", "HomeClass", "HomeRegion", "HomePI"),
    ]:
        tmp = g[["GameID","Date","Season","Gender","Played","IsNeutral",
                  team_col, key_col, for_col, against_col,
                  class_col, region_col, ti_col, pi_col, rank_col,
                  opp_team_col, opp_key_col, opp_class_col, opp_region_col,
                  opp_pi_col]].copy()
        tmp = tmp.rename(columns={
            team_col:        "Team1",
            key_col:         "TeamKey",
            for_col:         "For",
            against_col:     "Against",
            class_col:       "SchoolClass",
            region_col:      "SchoolRegion",
            ti_col:          "TI",
            pi_col:          "PI",
            rank_col:        "Rank",
            opp_team_col:    "OppTeam",
            opp_key_col:     "OppKey",
            opp_class_col:   "OppClass",
            opp_region_col:  "OppRegion",
            opp_pi_col:      "OppPI",
        })
        tmp["IsHome"] = (side == "home")
        rows.append(tmp)

    t2 = pd.concat(rows, ignore_index=True)

    # Pull GamesScheduled and GameNum from truth (Team1 perspective where available)
    t_extra = t[["GameID","Team1","GamesScheduled","GameNum","ScrapedAt","OppPreliminaryIndex"]].copy()
    t_extra["GameID"] = clean_gameids(t_extra["GameID"])
    t2 = t2.merge(t_extra, on=["GameID","Team1"], how="left")
    # Fill null OppPI with OppPreliminaryIndex from truth (Team1 perspective only)
    t2["OppPI"] = pd.to_numeric(t2["OppPI"], errors="coerce")
    opp_idx = pd.to_numeric(t2["OppPreliminaryIndex"], errors="coerce")
    t2["OppPI"] = t2["OppPI"].fillna(opp_idx)


    t2["For"]     = pd.to_numeric(t2["For"],     errors="coerce")
    t2["Against"] = pd.to_numeric(t2["Against"], errors="coerce")
    t2["Played"]  = t2["Played"].fillna(False)
    t2["IsNeutral"] = t2["IsNeutral"].fillna(False)

    # Derive flags from scores (reliable)
    t2["Margin"]   = t2["For"] - t2["Against"]
    t2["WinFlag"]  = (t2["Margin"] > 0).astype(int)
    t2["LossFlag"] = (t2["Margin"] < 0).astype(int)
    t2["TieFlag"]  = (t2["Margin"] == 0).astype(int)

    t2["TI"]    = pd.to_numeric(t2["TI"],    errors="coerce")
    t2["PI"]    = pd.to_numeric(t2["PI"],    errors="coerce")
    t2["Rank"]  = pd.to_numeric(t2["Rank"],  errors="coerce")
    t2["OppPI"] = pd.to_numeric(t2["OppPI"], errors="coerce")
    t2["Date"]  = pd.to_datetime(t2["Date"], errors="coerce")
    t2["GameNum"] = pd.to_numeric(t2["GameNum"], errors="coerce").fillna(0).astype(int)
    t2["GamesScheduled"] = pd.to_numeric(t2["GamesScheduled"], errors="coerce")

    # Division
    t2["SchoolDivision"] = t2["SchoolClass"].astype(str).str.strip() + "-" + t2["SchoolRegion"].astype(str).str.strip()

    # Gender from games_core
    t2["Gender"] = t2["Gender"].astype(str).str.strip().str.title()

    # Season
    t2["Season"] = t2["Date"].apply(season_from_date)

    played = t2[t2["Played"]].copy()

    grp = ["Team1","Gender","Season","SchoolClass","SchoolRegion","SchoolDivision"]






    def build(sub: pd.DataFrame) -> pd.Series:
        sub = sub.sort_values("Date")
        margins = sub["Margin"].values
        fors    = sub["For"].values
        agains  = sub["Against"].values
        wins    = sub["WinFlag"].values
        losses  = sub["LossFlag"].values
        ties    = sub["TieFlag"].values
        n       = len(sub)
        opp_pi  = sub["OppPI"].values
        dates   = sub["Date"].values

        # Basic
        games   = int(n)
        w       = int(wins.sum())
        l       = int(losses.sum())
        ti_     = int(ties.sum())
        winpct  = float(w / games) if games else np.nan
        pts_for = float(np.nansum(fors))
        pts_ag  = float(np.nansum(agains))
        ppg     = float(np.nanmean(fors)) if games else np.nan
        oppg    = float(np.nanmean(agains)) if games else np.nan
        mpg     = float(np.nanmean(margins)) if games else np.nan
        mstd    = float(np.nanstd(margins)) if games else np.nan
        mstd10  = float(np.nanstd(margins[-10:])) if games >= 2 else np.nan
        gs      = float(sub["GamesScheduled"].dropna().iloc[-1]) if sub["GamesScheduled"].notna().any() else np.nan
        grem    = float(gs - games) if not np.isnan(gs) else np.nan
        hi_score = float(np.nanmax(fors)) if games else np.nan
        lo_score = float(np.nanmin(fors)) if games else np.nan
        hi_marg  = float(np.nanmax(margins)) if games else np.nan
        lo_marg  = float(np.nanmin(margins)) if games else np.nan

        # Last N
        l5ppg      = float(np.nanmean(fors[-5:]))   if games >= 1 else np.nan
        l5mpg      = float(np.nanmean(margins[-5:])) if games >= 1 else np.nan
        l10mpg     = float(np.nanmean(margins[-10:])) if games >= 1 else np.nan

        # Efficiency (same as PPG/OPPG for team-total data)
        off_eff = ppg
        def_eff = oppg
        net_eff = ppg - oppg if (ppg == ppg and oppg == oppg) else np.nan

        # Home/Away/Neutral splits
        home_sub    = sub[sub["IsHome"] & ~sub["IsNeutral"]]
        away_sub    = sub[~sub["IsHome"] & ~sub["IsNeutral"]]
        neut_sub    = sub[sub["IsNeutral"]]
        hg = len(home_sub); hw = int(home_sub["WinFlag"].sum()); hl = int(home_sub["LossFlag"].sum())
        hwpct = float(hw/hg) if hg else np.nan
        hmpg  = float(home_sub["Margin"].mean()) if hg else np.nan
        rg = len(away_sub); rw = int(away_sub["WinFlag"].sum()); rl = int(away_sub["LossFlag"].sum())
        rwpct = float(rw/rg) if rg else np.nan
        rmpg  = float(away_sub["Margin"].mean()) if rg else np.nan
        ng = len(neut_sub); nw = int(neut_sub["WinFlag"].sum()); nl_ = int(neut_sub["LossFlag"].sum())
        nwpct = float(nw/ng) if ng else np.nan
        nmpg  = float(neut_sub["Margin"].mean()) if ng else np.nan
        hr_diff = (hmpg - rmpg) if (hmpg == hmpg and rmpg == rmpg) else np.nan

        # Close/blowout
        abs_m = np.abs(margins)
        close_mask   = abs_m <= 6
        blowout_mask = abs_m >= 15
        one_poss     = abs_m <= 3
        close_g  = int(close_mask.sum())
        close_w  = int((wins[close_mask]).sum())
        close_l  = int((losses[close_mask]).sum())
        cwpct    = float(close_w/close_g) if close_g else np.nan
        cgrate   = float(close_g/games) if games else np.nan
        one_rate = float(one_poss.sum()/games) if games else np.nan
        clutch_close = int((wins[abs_m <= 4]).sum())
        clutch_total = int((abs_m <= 4).sum())
        clutch_wpct  = float(clutch_close/clutch_total) if clutch_total else np.nan
        blow_g  = int(blowout_mask.sum())
        blow_w  = int((wins[blowout_mask]).sum())
        blow_l  = int((losses[blowout_mask]).sum())
        bwrate  = float(blow_g/games) if games else np.nan
        blow_mpg= float(np.nanmean(np.abs(margins[blowout_mask]))) if blow_g else np.nan

        # Margin buckets
        def mbucket(lo, hi):
            mask = (abs_m >= lo) & (abs_m <= hi)
            g_ = int(mask.sum()); w_ = int((wins[mask]).sum())
            return g_, w_, float(w_/g_) if g_ else np.nan
        g03,w03,wp03 = mbucket(0,3)
        g410,w410,wp410 = mbucket(4,10)
        g1120,w1120,wp1120 = mbucket(11,20)
        mask21 = abs_m >= 21
        g21 = int(mask21.sum()); w21 = int((wins[mask21]).sum())
        wp21 = float(w21/g21) if g21 else np.nan

        # Streaks
        streak = 0
        if n > 0:
            last = wins[-1] if wins[-1] else -losses[-1]
            for i in range(n-1, -1, -1):
                if wins[i] and last > 0:
                    streak += 1
                elif losses[i] and last < 0:
                    streak -= 1
                else:
                    break
        streak_label = f"W{abs(streak)}" if streak > 0 else (f"L{abs(streak)}" if streak < 0 else "T0")
        max_win_streak = max_loss_streak = cur_w = cur_l = 0
        for i in range(n):
            if wins[i]:
                cur_w += 1; cur_l = 0
            elif losses[i]:
                cur_l += 1; cur_w = 0
            max_win_streak  = max(max_win_streak, cur_w)
            max_loss_streak = max(max_loss_streak, cur_l)

        # Early/late season phase
        early_mask = sub["GameNum"] <= 5
        late_mask  = sub["GameNum"] > 10
        early_sub  = sub[early_mask]; late_sub = sub[late_mask]
        early_g = len(early_sub); early_w = int(early_sub["WinFlag"].sum())
        early_mpg = float(early_sub["Margin"].mean()) if early_g else np.nan
        late_g  = len(late_sub);  late_w  = int(late_sub["WinFlag"].sum())
        late_mpg  = float(late_sub["Margin"].mean()) if late_g else np.nan
        is_late_skew = int(late_g > early_g)

        # Division splits
        div = str(sub["SchoolDivision"].iloc[0]) if "SchoolDivision" in sub.columns and n else ""


        opp_divs = sub["OppClass"].astype(str).str.strip()
        team_class = sub["SchoolClass"].astype(str).str.strip() if "SchoolClass" in sub.columns else pd.Series([""] * len(sub), index=sub.index)
        in_div_wins    = int(sub[(opp_divs == team_class) & (sub["WinFlag"]==1)].shape[0])
        cross_div_wins = int(sub[(opp_divs != team_class) & (sub["WinFlag"]==1)].shape[0])


        # Rest days
        rest_days = pd.Series(dates).diff().dt.days.dropna()
        avg_rest     = float(rest_days.mean()) if len(rest_days) else np.nan
        short_rest_g = int((rest_days <= 1).sum())
        short_rest_s = float(short_rest_g / games) if games else np.nan
        long_rest_g  = int((rest_days >= 4).sum())
        long_rest_s  = float(long_rest_g / games) if games else np.nan

        #        # OWP / OOWP / RPI — true opponent win pct from actual records
        valid_opp_pi = opp_pi[~np.isnan(opp_pi)]
        opp_keys = sub["OppKey"].dropna().unique().tolist() if "OppKey" in sub.columns else []
        team_key = sub["TeamKey"].iloc[0] if "TeamKey" in sub.columns and n else ""

        # OWP: average win% of all opponents (excluding games vs this team)
        opp_wps = []
        opp_owp_map = {}  # keyed by opp_key -> that opponent's OWP
        for _ok in opp_keys:
            _opp_games = played[played["TeamKey"] == _ok]
            # Exclude games this opponent played against US
            _opp_games = _opp_games[_opp_games["OppKey"] != team_key] if "OppKey" in _opp_games.columns else _opp_games
            if not _opp_games.empty:
                _og = len(_opp_games)
                _ow = int(_opp_games["WinFlag"].sum())
                _wp = _ow / _og
                opp_wps.append(_wp)
                opp_owp_map[_ok] = _wp
        owp = float(np.mean(opp_wps)) if opp_wps else np.nan

        # OOWP: for each opponent, compute THEIR opponents' average win%
        opp_oowps = []
        for _ok in opp_keys:
            _opp_games = played[played["TeamKey"] == _ok]
            if "OppKey" in _opp_games.columns:
                _opp_opp_keys = _opp_games["OppKey"].dropna().unique()
                _o2_wps = [opp_owp_map[k] for k in _opp_opp_keys if k in opp_owp_map]
                if _o2_wps:
                    opp_oowps.append(float(np.mean(_o2_wps)))
        oowp = float(np.mean(opp_oowps)) if opp_oowps else np.nan

        # RPI: NCAA standard weights
        wp_rpi = winpct if not np.isnan(winpct) else 0.0
        owp_r  = owp    if not np.isnan(owp)    else 0.0
        oowp_r = oowp   if not np.isnan(oowp)   else 0.0
        rpi    = float(0.25 * wp_rpi + 0.50 * owp_r + 0.25 * oowp_r) if games else np.nan

        # SOS: opponent average win% on 0-100 scale (intuitive display)
        sos_ewp = float(owp * 100.0) if not np.isnan(owp) else np.nan

        # Pythagorean Expected Wins (exponent 11.5 tuned for HS basketball)
        _pyth_exp = 11.5
        if ppg == ppg and oppg == oppg and ppg + oppg > 0:
            ewp = (ppg ** _pyth_exp) / (ppg ** _pyth_exp + oppg ** _pyth_exp)
            exp_wins = float(ewp * games)
        else:
            exp_wins = np.nan
        sched_adj = float(w - exp_wins) if exp_wins == exp_wins else np.nan
        luck_z = float((w - exp_wins) / max(1, n**0.5)) if exp_wins == exp_wins else np.nan

        # Quadrant records (Q1=top opp PI, Q4=bottom)
        pi_arr = opp_pi
        q1_mask = pi_arr >= 30; q2_mask = (pi_arr >= 20) & (pi_arr < 30)
        q3_mask = (pi_arr >= 10) & (pi_arr < 20); q4_mask = pi_arr < 10

        def qr(mask):
            gq=int(mask.sum()); wq=int((wins[mask]).sum()); lq=int((losses[mask]).sum())
            return gq, wq, lq
        q1g,q1w,q1l = qr(q1_mask); q2g,q2w,q2l = qr(q2_mask)
        q3g,q3w,q3l = qr(q3_mask); q4g,q4w,q4l = qr(q4_mask)

        # Opponent tiers (by NetEff proxy: use OppPI bins)
        top_mask    = pi_arr >= 28; mid_mask = (pi_arr >= 15) & (pi_arr < 28); bot_mask = pi_arr < 15

        def tier(mask):
            tg=int(mask.sum()); tw=int((wins[mask]).sum()); tl=int((losses[mask]).sum())
            twpct=float(tw/tg) if tg else np.nan
            tmpg=float(np.nanmean(margins[mask])) if tg else np.nan
            tne=float(np.nanmean(fors[mask]-agains[mask])) if tg else np.nan
            return tg,tw,tl,twpct,tmpg,tne
        tg_t,tw_t,tl_t,twp_t,tmp_t,tne_t = tier(top_mask)
        tg_m,tw_m,tl_m,twp_m,tmp_m,tne_m = tier(mid_mask)
        tg_b,tw_b,tl_b,twp_b,tmp_b,tne_b = tier(bot_mask)

        # Vs Top 25 (Rank <= 25)
        ranks = pd.to_numeric(sub["Rank"], errors="coerce").values
        top25_mask = ranks <= 25
        t25g=int(top25_mask.sum()); t25w=int((wins[top25_mask]).sum()); t25l=int((losses[top25_mask]).sum())
        t25wpct=float(t25w/t25g) if t25g else np.nan
        t25mpg=float(np.nanmean(margins[top25_mask])) if t25g else np.nan

                # Resume
        opp_teams = sub["OppTeam"].values

        # Best win — highest PI opponent that was actually a win
        win_pi = np.where(wins == 1, pi_arr, np.nan)
        if not np.all(np.isnan(win_pi)):
            best_opp_idx  = int(np.nanargmax(win_pi))
            best_win      = str(opp_teams[best_opp_idx])
            best_win_marg = float(margins[best_opp_idx])
        else:
            best_win = best_win_marg = np.nan

        # Worst loss — lowest PI opponent that was actually a loss
        loss_pi = np.where(losses == 1, pi_arr, np.nan)
        if losses.sum() > 0 and not np.all(np.isnan(loss_pi)):
            worst_opp_idx = int(np.nanargmin(loss_pi))
        else:
            worst_opp_idx = None

        worst_loss      = str(opp_teams[worst_opp_idx]) if worst_opp_idx is not None else np.nan
        worst_loss_marg = float(margins[worst_opp_idx]) if worst_opp_idx is not None else np.nan
        quality_wins    = int((wins[pi_arr >= 25]).sum()) if not np.all(np.isnan(pi_arr)) else 0
        bad_losses      = int((losses[pi_arr < 10]).sum()) if not np.all(np.isnan(pi_arr)) else 0



        # TI/PI/Rank (latest)
        ti_val   = float(sub["TI"].dropna().iloc[-1])   if sub["TI"].notna().any()   else np.nan
        pi_val   = float(sub["PI"].dropna().iloc[-1])   if sub["PI"].notna().any()   else np.nan
        rank_val = float(sub["Rank"].dropna().iloc[-1]) if sub["Rank"].notna().any() else np.nan
        proj_seed = int(round(rank_val)) if rank_val == rank_val else np.nan
        qualified = int(rank_val <= 16) if rank_val == rank_val else 0

        last_date   = sub["Date"].max()
        scraped_at  = sub["ScrapedAt"].max() if "ScrapedAt" in sub.columns else pd.NaT

        return pd.Series({
            # Identity
            "TeamKey": build_team_key(
                sub["Team1"].iloc[0]      if "Team1"       in sub.columns else "",
                sub["Gender"].iloc[0]     if "Gender"      in sub.columns else "",
                sub["SchoolClass"].iloc[0]if "SchoolClass" in sub.columns else "",
                sub["SchoolRegion"].iloc[0]if "SchoolRegion"in sub.columns else "",
            ),
            

            # Basic record
            "Games": games, "Wins": w, "Losses": l, "Ties": ti_,
            "Record": f"{w}-{l}-{ti_}", "WinPct": winpct,
            "GamesScheduled": gs, "GamesRemaining": grem,
            # Scoring
            "PointsFor": pts_for, "PointsAgainst": pts_ag,
            "PPG": ppg, "OPPG": oppg, "MarginPG": mpg,
            "MarginStd": mstd, "MarginStdL10": mstd10,
            "L5PPG": l5ppg, "L5MarginPG": l5mpg, "Last5MarginPG": l5mpg,
            "Last10MarginPG": l10mpg,
            "HighestScore": hi_score, "LowestScore": lo_score,
            "HighestMargin": hi_marg, "LowestMargin": lo_marg,
            # Efficiency
            "OffEff": off_eff, "DefEff": def_eff, "NetEff": net_eff,
            # SOS / RPI
            "SOS_EWP": sos_ewp, "ExpectedWins": exp_wins,
            "ScheduleAdjWins": sched_adj, "LuckZ": luck_z,
            "WP": winpct, "OWP": owp, "OOWP": oowp, "RPI": rpi,
            # Quadrants
            "Q1_Games": q1g, "Q1_Wins": q1w, "Q1_Losses": q1l,
            "Q2_Games": q2g, "Q2_Wins": q2w, "Q2_Losses": q2l,
            "Q3_Games": q3g, "Q3_Wins": q3w, "Q3_Losses": q3l,
            "Q4_Games": q4g, "Q4_Wins": q4w, "Q4_Losses": q4l,
            # Home/Away/Neutral
            "HomeGames": hg, "HomeWins": hw, "HomeLosses": hl,
            "HomeWinPct": hwpct, "HomeMarginPG": hmpg,
            "RoadGames": rg, "RoadWins": rw, "RoadLosses": rl,
            "RoadWinPct": rwpct, "RoadMarginPG": rmpg,
            "HomeRoadDiff": hr_diff,
            "NeutralGames": ng, "NeutralWins": nw, "NeutralLosses": nl_,
            "NeutralWinPct": nwpct, "NeutralMarginPG": nmpg,
            # Close/blowout
            "CloseGames": close_g, "CloseWins": close_w, "CloseLosses": close_l,
            "CloseWinPct": cwpct, "CloseGameRate": cgrate,
            "OnePossessionRate": one_rate, "ClutchCloseGameWinPct": clutch_wpct,
            "BlowoutGames": blow_g, "BlowoutWins": blow_w, "BlowoutLosses": blow_l,
            "BlowoutRate": bwrate, "BlowoutMarginPG": blow_mpg,
            # Margin buckets
            "GamesMargin0to3": g03, "WinsMargin0to3": w03, "WinPctMargin0to3": wp03,
            "GamesMargin4to10": g410, "WinsMargin4to10": w410, "WinPctMargin4to10": wp410,
            "GamesMargin11to20": g1120, "WinsMargin11to20": w1120, "WinPctMargin11to20": wp1120,
            "GamesMargin21plus": g21, "WinsMargin21plus": w21, "WinPctMargin21plus": wp21,
            # Streaks
            "Streak": streak, "StreakLabel": streak_label,
            "WinsInRow": max_win_streak, "LossesInRow": max_loss_streak,
            # Season phase
            "EarlyGames": early_g, "EarlyWins": early_w, "EarlyMarginPG": early_mpg,
            "LateGames": late_g, "LateWins": late_w, "LateMarginPG": late_mpg,
            "IsLateSkew": is_late_skew,
            # Division
            "InDivisionWins": in_div_wins, "CrossDivisionWins": cross_div_wins,
            # Rest
            "AvgRestDays": avg_rest, "ShortRestGames": short_rest_g,
            "ShortRestShare": short_rest_s, "LongRestGames": long_rest_g,
            "LongRestShare": long_rest_s,
            # Opponent tiers
            "GamesVsTop": tg_t, "WinsVsTop": tw_t, "LossesVsTop": tl_t,
            "WinPctVsTop": twp_t, "MarginVsTop": tmp_t, "NetEffVsTop": tne_t,
            "GamesVsMiddle": tg_m, "WinsVsMiddle": tw_m, "LossesVsMiddle": tl_m,
            "WinPctVsMiddle": twp_m, "MarginVsMiddle": tmp_m, "NetEffVsMiddle": tne_m,
            "GamesVsBottom": tg_b, "WinsVsBottom": tw_b, "LossesVsBottom": tl_b,
            "WinPctVsBottom": twp_b, "MarginVsBottom": tmp_b, "NetEffVsBottom": tne_b,
            # Vs Top 25
            "GamesVsTop25": t25g, "WinsVsTop25": t25w, "LossesVsTop25": t25l,
            "WinPctVsTop25": t25wpct, "MarginVsTop25": t25mpg,
            # Resume
            "BestWin": best_win, "BestWinMargin": best_win_marg,
            "WorstLoss": worst_loss, "WorstLossMargin": worst_loss_marg,
            "QualityWins": quality_wins, "BadLosses": bad_losses,
            "Top25Wins": t25w, "Top25Losses": t25l,
            # TI/PI/Rank
            "TI": ti_val, "PI": pi_val, "Rank": rank_val,
            "ProjectedSeed": proj_seed, "Qualified": qualified,
            # Metadata
            "LastGameDate": last_date, "ScrapedAt": scraped_at,
            "CoreVersion": CORE_VERSION,
        })

    out = played.groupby(grp, dropna=False).apply(build, include_groups=False).reset_index()

    # rename group key columns to final names
    out = out.rename(columns={
        "Team1":         "Team",
        "SchoolClass":   "Class",
        "SchoolRegion":  "Region",
        "SchoolDivision": "Division",
    })

    # drop duplicate columns that build() also returned inside the Series
    seen = set()
    dedup_cols = []
    for c in out.columns:
        if c not in seen:
            seen.add(c)
            dedup_cols.append(c)
    out = out[dedup_cols]

    assert_no_pred_cols(out, "teams_analytics_v50")
    return out




# --------------------------------------------------------------------------------------
# Build games analytics (full descriptive, no preds)
# --------------------------------------------------------------------------------------


def build_games_analytics(games: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    g = games.copy()
    t = truth.copy()
    t["GameID"] = clean_gameids(t["GameID"])
    g["GameID"] = clean_gameids(g["GameID"])


    # Pull one truth row per GameID (Team1 perspective)
    t_game = (
        t.sort_values(["GameID","GameNum"])
         .drop_duplicates(subset="GameID", keep="first")
    )
    cols_to_add = [c for c in ["GameNum","Rank","RecordText","GamesPlayed",
                                "GamesScheduled","OppDiv","OppPreliminaryIndex",
                                "WinPoints","ScrapedAt"]
                   if c in t_game.columns]
    g = g.merge(t_game[["GameID"] + cols_to_add], on="GameID", how="left",
                suffixes=("","_t"))


    g["TotalPoints"] = g["HomeScore"] + g["AwayScore"]
    g["AbsMargin"]   = g["Margin"].abs()
    g["HomeWinFlag"] = (g["HomeScore"] > g["AwayScore"]).astype(int)
    g["AwayWinFlag"] = (g["AwayScore"] > g["HomeScore"]).astype(int)
    g["TieFlag"]     = (g["HomeScore"] == g["AwayScore"]).astype(int)
    g["IsClose"]     = (g["AbsMargin"] <= 6).astype(int)
    g["IsBlowout"]   = (g["AbsMargin"] >= 15).astype(int)
    g["IsOnePossession"] = (g["AbsMargin"] <= 3).astype(int)


    def class_order(c):
        return {"D":1,"C":2,"B":3,"A":4,"S":5}.get(str(c).strip().upper(), np.nan)


    g["HomeClassOrder"] = g["HomeClass"].map(class_order)
    g["AwayClassOrder"] = g["AwayClass"].map(class_order)
    g["ClassMatchupType"] = np.where(
        g["HomeClassOrder"].isna() | g["AwayClassOrder"].isna(), "Unknown",
        np.where(g["HomeClassOrder"] == g["AwayClassOrder"], "SameClass",
        np.where(g["HomeClassOrder"] > g["AwayClassOrder"], "HomeUpClass", "HomeDownClass"))
    )
    g["DivisionMatchupType"] = np.where(
        g["HomeDivision"] == g["AwayDivision"], "SameDivision", "CrossDivision"
    )
    g["RegionMatchupType"] = np.where(
        g["HomeRegion"] == g["AwayRegion"], "SameRegion", "CrossRegion"
    )
    g["GameNum"] = pd.to_numeric(g.get("GameNum", 0), errors="coerce").fillna(0).astype(int)
    g["SeasonPhase"] = pd.cut(
        g["GameNum"], bins=[-1,5,10,1000], labels=["Early","Mid","Late"]
    ).astype(object).astype(str)


    g["MarginBucket"] = pd.cut(
        g["AbsMargin"],
        bins=[-1,3,6,10,15,21,999],
        labels=["0-3","4-6","7-10","11-15","16-21","21+"]
    ).astype(object).astype(str)


    g["TotalPointsBucket"] = pd.cut(
        g["TotalPoints"].fillna(0),
        bins=[0,80,100,120,140,999],
        labels=["<80","80-100","100-120","120-140","140+"]
    ).astype(object).astype(str)


    g["OppPreliminaryIndex"] = pd.to_numeric(g.get("OppPreliminaryIndex", np.nan), errors="coerce")
    g["OppQualityTier"] = pd.cut(
        g["OppPreliminaryIndex"],
        bins=[-1,30,50,70,101],
        labels=["Low","Mid","High","Elite"]
    ).astype(object).astype(str)


    drop_cols = ["HomeClassOrder","AwayClassOrder"]
    g = g.drop(columns=[c for c in drop_cols if c in g.columns], errors="ignore")


    g["CoreVersion"] = CORE_VERSION
    assert_no_pred_cols(g, "games_analytics_v50")
    assert_unique_key(g, "GameID", "games_analytics_v50")
    return g



# --------------------------------------------------------------------------------------
# Prediction engine
# --------------------------------------------------------------------------------------

def run_pred_engine() -> None:
    if not PRED_ENGINE_SCRIPT.exists():
        raise FileNotFoundError(f"Missing pred engine: {PRED_ENGINE_SCRIPT}")
    spec = importlib.util.spec_from_file_location("pred_engine_v50", str(PRED_ENGINE_SCRIPT))
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "main"):
        raise RuntimeError("Pred engine has no main()")
    mod.main()
    if not PRED_CURRENT.exists():
        raise RuntimeError(f"Pred engine did not write: {PRED_CURRENT}")


# --------------------------------------------------------------------------------------
# Public bundle (facts + preds + grading)
# --------------------------------------------------------------------------------------

def build_public_bundle(games: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    g = games.copy(); p = pred.copy()
    g["GameID"] = clean_gameids(g["GameID"])
    p["GameID"] = clean_gameids(p["GameID"])
    keep_p = [c for c in PRED_ALL_COLS if c in p.columns]
    p2 = p[keep_p].drop_duplicates("GameID")
    out = g.merge(p2, on="GameID", how="left", suffixes=("","_pred"))

    hs    = pd.to_numeric(out["HomeScore"], errors="coerce")
    as_   = pd.to_numeric(out["AwayScore"], errors="coerce")
    pl    = out["Played"].fillna(False)
    phwp  = pd.to_numeric(out["PredHomeWinProb"], errors="coerce")
    pm    = pd.to_numeric(out["PredMargin"], errors="coerce")
    am    = np.where(pl, hs - as_, np.nan)
    out["ActualMargin"]   = am
    out["FavoriteIsHome"] = phwp >= 0.5
    out["FavProb"]        = np.where(out["FavoriteIsHome"].fillna(False), phwp, 1.0 - phwp)
    out["ModelCorrect"]   = np.where(pl, (pm > 0) == (pd.Series(am) > 0), np.nan)

    keep = [
        "GameID","Date","Season","Gender","Home","Away","HomeKey","AwayKey",
        "HomeClass","AwayClass","HomeRegion","AwayRegion",
        "HomeScore","AwayScore","Played","IsNeutral","WinnerTeam","Margin",
        "PredHomeWinProb","PredMargin","PredHomeScore","PredAwayScore","PredTotalPoints",
        "PredWinnerKey","PredWinnerProbPct","PredSpreadAbs","PredBuildID",
        "ActualMargin","FavoriteIsHome","FavProb","ModelCorrect","CoreVersion",
    ]
    cols = [c for c in keep if c in out.columns]
    out  = out[cols].copy()
    assert_unique_key(out, "GameID", "games_public_v50")
    return out


# --------------------------------------------------------------------------------------
# Performance / calibration
# --------------------------------------------------------------------------------------

def build_performance(public: pd.DataFrame):
    df     = public.copy()
    played = df[df["Played"].fillna(False)].copy()
    if played.empty:
        empty_summary = pd.DataFrame([{"TotalGames":0,"CorrectGames":0,
            "OverallAccuracy":0.0,"UpsetRate":0.0,"MAE":0.0,"RMSE":0.0,
            "Within5Pts":0.0,"Within10Pts":0.0,"BrierScore":0.0}])
        return (empty_summary,
                pd.DataFrame(columns=["Date","Home","Away","HomeScore","AwayScore",
                    "Favorite","FavProbPct","ModelCorrect","PredMargin","ActualMargin","Gender"]),
                pd.DataFrame(columns=["ConfBucket","Games","Correct","HitRate","AvgProb"]),
                pd.DataFrame(columns=["SpreadBucket","Games","Correct","HitRate","AvgSpread","MAE"]))

    hs   = pd.to_numeric(played["HomeScore"], errors="coerce")
    as_  = pd.to_numeric(played["AwayScore"], errors="coerce")
    out_h= np.where(hs > as_, 1.0, np.where(hs < as_, 0.0, 0.5))
    phwp = pd.to_numeric(played["PredHomeWinProb"], errors="coerce")
    pm   = pd.to_numeric(played["PredMargin"], errors="coerce")
    am   = pd.to_numeric(played["ActualMargin"], errors="coerce")
    fih  = played["FavoriteIsHome"].fillna(False)
    fav  = np.where(fih, played["Home"], played["Away"])
    favp = np.where(fih, phwp, 1.0 - phwp)
    mc   = played["ModelCorrect"].fillna(False)

    perf_games = pd.DataFrame({
        "Date": played["Date"], "Home": played["Home"], "Away": played["Away"],
        "HomeScore": played["HomeScore"], "AwayScore": played["AwayScore"],
        "Favorite": fav, "FavProbPct": 100.0 * favp, "ModelCorrect": mc,
        "PredMargin": pm, "ActualMargin": am,
        "Gender": played.get("Gender", np.nan),
    })

    n   = len(perf_games)
    cor = int(pd.Series(mc).fillna(False).sum())
    acc = float(100.0 * cor / n) if n else 0.0
    err = (pm - am).abs()
    mae  = float(err.mean())    if err.notna().any() else 0.0
    rmse = float(np.sqrt(((pm - am)**2).mean())) if pm.notna().any() else 0.0
    w5   = float(100.0 * (err <= 5).mean())  if err.notna().any() else 0.0
    w10  = float(100.0 * (err <= 10).mean()) if err.notna().any() else 0.0
    brier= float(((phwp - out_h)**2).mean()) if phwp.notna().any() else 0.0

    summary = pd.DataFrame([{"TotalGames":n,"CorrectGames":cor,"OverallAccuracy":acc,
        "UpsetRate":100.0-acc,"MAE":mae,"RMSE":rmse,
        "Within5Pts":w5,"Within10Pts":w10,"BrierScore":brier}])

    tmp = perf_games.copy()
    tmp["ConfBucket"] = pd.cut(tmp["FavProbPct"].clip(50,100),
        bins=[50,60,70,80,90,101], labels=["50-59","60-69","70-79","80-89","90-100"], right=False
    ).astype(object).astype(str)
    calib = (tmp.dropna(subset=["ConfBucket"])
               .groupby("ConfBucket", dropna=True, observed=True)
               .agg(Games=("ModelCorrect","size"),
                    Correct=("ModelCorrect", lambda s: int(pd.Series(s).fillna(False).sum())),
                    HitRate=("ModelCorrect", lambda s: float(100.0*pd.Series(s).fillna(False).mean())),
                    AvgProb=("FavProbPct","mean")).reset_index())


    tmp2 = perf_games.copy()
    tmp2["AbsSpread"] = pm.abs()
    tmp2["SpreadBucket"] = pd.cut(tmp2["AbsSpread"],
        bins=[0,2,5,8,12,100], labels=["0-2","2-5","5-8","8-12","12+"], right=False
    ).astype(object).astype(str)
    spreadperf = (tmp2.dropna(subset=["SpreadBucket"])
                     .groupby("SpreadBucket", dropna=True, observed=True)
                     .apply(lambda sub: pd.Series({
                         "Games": len(sub),
                         "Correct": int(pd.Series(sub["ModelCorrect"]).fillna(False).sum()),
                         "HitRate": float(100.0*pd.Series(sub["ModelCorrect"]).fillna(False).mean()),
                         "AvgSpread": float(pd.to_numeric(sub["AbsSpread"],errors="coerce").mean()),
                         "MAE": float((pd.to_numeric(sub["PredMargin"],errors="coerce")
                                       - pd.to_numeric(sub["ActualMargin"],errors="coerce")).abs().mean()),
                     }), include_groups=False).reset_index())
    return summary, perf_games, calib, spreadperf



# --------------------------------------------------------------------------------------
# Nightly report
# --------------------------------------------------------------------------------------

def build_nightly_report(games: pd.DataFrame, pred: pd.DataFrame, public: pd.DataFrame) -> pd.DataFrame:
    played = public[public["Played"].fillna(False)]
    mae = acc = np.nan
    if not played.empty and {"PredMargin","ActualMargin","ModelCorrect"}.issubset(played.columns):
        mae = float((pd.to_numeric(played["PredMargin"],errors="coerce")
                     - pd.to_numeric(played["ActualMargin"],errors="coerce")).abs().mean())
        acc = float(100.0 * played["ModelCorrect"].fillna(False).mean())
    wp = pd.to_numeric(pred.get("PredHomeWinProb", np.nan), errors="coerce")
    pm = pd.to_numeric(pred.get("PredMargin", np.nan), errors="coerce")
    return pd.DataFrame([{
        "BuiltAtUTC": datetime.now(timezone.utc).isoformat(),
        "TotalGames": len(games),
        "PlayedGames": int(games["Played"].fillna(False).sum()),
        "UnplayedGames": int((~games["Played"].fillna(False)).sum()),
        "PredWinProbMin":  float(wp.min())      if wp.notna().any() else np.nan,
        "PredWinProbMax":  float(wp.max())      if wp.notna().any() else np.nan,
        "PredWinProbMean": float(wp.mean())     if wp.notna().any() else np.nan,
        "PredMarginAbsMean": float(pm.abs().mean()) if pm.notna().any() else np.nan,
        "PublicPlayedMAE": mae,
        "PublicPlayedAccuracyPct": acc,
        "CoreVersion": CORE_VERSION,
    }])


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-contract", action="store_true")
    return ap.parse_args()

def build_team_of_week(
    games: pd.DataFrame,
    teams: pd.DataFrame,
    public: pd.DataFrame,
) -> None:
    from datetime import timedelta

    def _week_id(d: pd.Timestamp) -> str:
        mon = d - timedelta(days=d.weekday())
        sun = mon + timedelta(days=6)
        return f"{mon.strftime('%Y-%m-%d')}_to_{sun.strftime('%Y-%m-%d')}"

    g = games[games["Played"].fillna(False)].copy()
    g["Date"] = pd.to_datetime(g["Date"], errors="coerce")
    g = g[g["Date"].notna()].copy()
    if g.empty:
        print("   TOTW: no played games found, skipping.")
        return

    g["WeekID"] = g["Date"].apply(_week_id)
    g["Season"] = g["Date"].apply(season_from_date)

    opp_mpg = (
        teams[["TeamKey", "MarginPG"]].copy()
        .rename(columns={"TeamKey": "OppKey", "MarginPG": "OppMarginPG"})
    )

    has_surprise = "ActualMargin" in public.columns and "PredMargin" in public.columns
    if has_surprise:
        pub = public[["GameID", "HomeKey", "AwayKey", "ActualMargin", "PredMargin"]].copy()
        pub["ActualMargin"] = pd.to_numeric(pub["ActualMargin"], errors="coerce")
        pub["PredMargin"]   = pd.to_numeric(pub["PredMargin"],   errors="coerce")
        pub["SurpHome"]     =  pub["ActualMargin"] - pub["PredMargin"]
        pub["SurpAway"]     = -pub["SurpHome"]
        surp_home = pub[["GameID", "HomeKey", "SurpHome"]].rename(
            columns={"HomeKey": "TeamKey", "SurpHome": "Surprise"})
        surp_away = pub[["GameID", "AwayKey", "SurpAway"]].rename(
            columns={"AwayKey": "TeamKey", "SurpAway": "Surprise"})
        surprise = pd.concat([surp_home, surp_away], ignore_index=True)

    sides = [
        ("HomeKey", "Home", "HomeScore", "AwayScore", "AwayKey", "HomeClass", "HomeRegion"),
        ("AwayKey", "Away", "AwayScore", "HomeScore", "HomeKey", "AwayClass", "AwayRegion"),
    ]
    rows = []
    for key_col, team_col, for_col, against_col, opp_key_col, cls_col, reg_col in sides:
        tmp = g[["GameID", "WeekID", "Season", "Gender",
                 key_col, team_col, for_col, against_col,
                 opp_key_col, cls_col, reg_col]].copy()
        tmp.columns = ["GameID", "WeekID", "Season", "Gender",
                       "TeamKey", "Team", "For", "Against",
                       "OppKey", "Class", "Region"]
        rows.append(tmp)

    long = pd.concat(rows, ignore_index=True)
    long["For"]     = pd.to_numeric(long["For"],     errors="coerce")
    long["Against"] = pd.to_numeric(long["Against"], errors="coerce")
    long = long[long["For"].notna() & long["Against"].notna()].copy()
    long["Margin"]  = long["For"] - long["Against"]

    long = long.merge(opp_mpg, on="OppKey", how="left")
    if has_surprise:
        long = long.merge(surprise, on=["GameID", "TeamKey"], how="left")
    else:
        long["Surprise"] = np.nan

    grp_cols = ["WeekID", "Season", "Gender", "Class", "Region", "TeamKey", "Team"]

    def _score(sub: pd.DataFrame) -> pd.Series:
        g_    = len(sub)
        w_    = int((sub["Margin"] > 0).sum())
        l_    = int((sub["Margin"] < 0).sum())
        avgm  = float(sub["Margin"].mean())
        avgopp = float(pd.to_numeric(sub["OppMarginPG"], errors="coerce").mean())
        avgs  = float(pd.to_numeric(sub["Surprise"],    errors="coerce").mean())
        wpct  = w_ / g_ if g_ else 0.0
        avgopp = 0.0 if np.isnan(avgopp) else avgopp
        avgs   = 0.0 if np.isnan(avgs)   else avgs
        score = (
            _TOTW_W_MARGIN   * avgm   +
            _TOTW_W_OPP      * avgopp +
            _TOTW_W_SURPRISE * avgs   +
            _TOTW_W_WINPCT   * wpct * 100.0
        )
        return pd.Series({
            "Games":        g_,
            "Wins":         w_,
            "Losses":       l_,
            "WinPct":       round(wpct,  4),
            "AvgMargin":    round(avgm,  2),
            "AvgOppRating": round(avgopp, 2),
            "AvgSurprise":  round(avgs,  2),
            "WeeklyScore":  round(score, 4),
        })

    scored = (
        long.groupby(grp_cols, dropna=False)
        .apply(_score, include_groups=False)
        .reset_index()
    )

    scored["Segment"] = (
        scored["Gender"].astype(str).str.strip() + "_" +
        scored["Class"].astype(str).str.strip()  + "_" +
        scored["Region"].astype(str).str.strip()
    )
    scored = scored.sort_values(
        ["WeekID", "Segment", "WeeklyScore"], ascending=[True, True, False]
    )
    scored["RankInSegment"] = (
        scored.groupby(["WeekID", "Segment"], dropna=False).cumcount() + 1
    )
    nominees = scored[scored["RankInSegment"] <= 2].copy()
    nominees["BuiltAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    col_order = [
        "WeekID", "Season", "Segment", "Gender", "Class", "Region",
        "TeamKey", "Team", "RankInSegment",
        "Games", "Wins", "Losses", "WinPct",
        "AvgMargin", "AvgOppRating", "AvgSurprise", "WeeklyScore",
        "BuiltAt",
    ]
    nominees = nominees[[c for c in col_order if c in nominees.columns]]

    TOTW_DIR.mkdir(parents=True, exist_ok=True)
    if TOTW_NOMINEES.exists():
        existing  = pd.read_parquet(TOTW_NOMINEES)
        new_weeks = set(nominees["WeekID"].unique())
        existing  = existing[~existing["WeekID"].isin(new_weeks)]
        out       = pd.concat([existing, nominees], ignore_index=True)
    else:
        out = nominees.copy()

    out = out.sort_values(["WeekID", "Segment", "RankInSegment"]).reset_index(drop=True)
    atomic_write_parquet(out, TOTW_NOMINEES)
    print(f"   TOTW: {len(nominees)} nominee rows across "
          f"{nominees['WeekID'].nunique()} week(s) → {TOTW_NOMINEES}")


# ============================================================
# STEP 11 — Trophy Room v50
# ============================================================
TROPHY_V50_PATH = CORE_DIR / "trophy_room_v50.parquet"

def build_trophy_room_v50(
    teams: pd.DataFrame,
    season: str = "2026",
) -> pd.DataFrame:

    def _sf(x, d=0.0):
        try:
            v = float(x)
            return v if np.isfinite(v) else d
        except Exception:
            return d

    def _record(row):
        w = int(_sf(row.get("Wins",   0)))
        l = int(_sf(row.get("Losses", 0)))
        return f"{w}-{l}-0"

    TROPHIES = [
        # Strength & resume
        ("Top PIR",             10, "Strength & resume",    10, "PIR",               True),
        ("Top TI",              20, "Strength & resume",    10, "TI",                True),
        ("Best SOS",            30, "Strength & resume",    10, "SOS_EWP",           True),
        ("Most Quality Wins",   40, "Strength & resume",    10, "QualityWins",       True),
        ("Fewest Bad Losses",   50, "Strength & resume",    10, "BadLosses",         False),
        ("Top 25% Wins",        60, "Strength & resume",    10, "Top25Wins",         True),
        ("Best Win%",           70, "Strength & resume",    10, "WinPct",            True),
        # Offense & defense
        ("Highest PPG",         10, "Offense & defense",    20, "PPG",               True),
        ("Lowest OPPG",         20, "Offense & defense",    20, "OPPG",              False),
        ("Best Net Margin",     30, "Offense & defense",    20, "MarginPG",          True),
        ("Best Sched Adj Wins", 40, "Offense & defense",    20, "ScheduleAdjWins",   True),
        # Clutch & dominance
        ("Best Close Win%",     10, "Clutch & dominance",   30, "CloseWinPct",       True),
        ("Best Blowout Rate",   20, "Clutch & dominance",   30, "BlowoutRate",       True),
        ("Best Blowout Margin", 30, "Clutch & dominance",   30, "BlowoutMarginPG",   True),
        ("One Possession Rate", 40, "Clutch & dominance",   30, "OnePossessionRate", True),
        # Road, home & neutral
        ("Best Road Win%",      10, "Road, home & neutral", 40, "RoadWinPct",        True),
        ("Best Home Win%",      20, "Road, home & neutral", 40, "HomeWinPct",        True),
        ("Best Road Margin",    30, "Road, home & neutral", 40, "RoadMarginPG",      True),
        ("Best Home Margin",    40, "Road, home & neutral", 40, "HomeMarginPG",      True),
        ("Home/Road Split",     50, "Road, home & neutral", 40, "HomeRoadDiff",      True),
        # Momentum & streaks
        ("Best L5 Margin",      10, "Momentum & streaks",   50, "L5MarginPG",        True),
        ("Best L5 PPG",         20, "Momentum & streaks",   50, "L5PPG",             True),
        # Consistency & grit
        ("Most Consistent",     10, "Consistency & grit",   60, "MarginStd",         False),
        ("Best vs Top Tier",    20, "Consistency & grit",   60, "WinPctVsTop",       True),
        ("Best vs Top 25",      30, "Consistency & grit",   60, "WinPctVsTop25",     True),
        ("Lowest Luck Z",       40, "Consistency & grit",   60, "LuckZ",             False),
    ]

    # Minimum TOTAL games to qualify
    MIN_GAMES = {
        "default":          5,
        "CloseWinPct":      3,
        "BlowoutRate":      5,
        "BlowoutMarginPG":  5,
        "RoadWinPct":       3,
        "HomeWinPct":       3,
        "WinPctVsTop":      3,
        "WinPctVsTop25":    2,
        "MarginStd":        5,
        "LuckZ":            5,
        "ScheduleAdjWins":  5,
        "SOS_EWP":          5,
        "L5MarginPG":       5,
        "L5PPG":            5,
    }

    # Minimum WINS required for rate/pct trophies
    MIN_WINS = {
        "BlowoutRate":      3,
        "BlowoutMarginPG":  3,
        "CloseWinPct":      2,
        "RoadWinPct":       2,
        "HomeWinPct":       2,
        "WinPctVsTop":      1,
        "WinPctVsTop25":    1,
        "WinPct":           3,
    }

    # Skip trophy if winner's value is 0 (meaningless zero winners)
    SKIP_IF_ZERO = {
        "QualityWins", "Top25Wins", "BlowoutRate",
        "BlowoutMarginPG", "BlowoutWins",
    }

    SCOPES = [
        ("Gender",            ["Gender"]),
        ("GenderClass",       ["Gender", "Class"]),
        ("GenderClassRegion", ["Gender", "Class", "Region"]),
    ]

    rows = []

    for scope_label, group_cols in SCOPES:
        for group_keys, grp in teams.groupby(group_cols, dropna=True):
            if not isinstance(group_keys, tuple):
                group_keys = (group_keys,)

            key_map = dict(zip(group_cols, group_keys))
            gender = str(key_map.get("Gender", ""))
            cls    = str(key_map.get("Class",  ""))
            region = str(key_map.get("Region", ""))

            if len(grp) < 2:
                continue

            for trophy_name, trophy_sort, category, cat_sort, col, higher in TROPHIES:
                if col not in grp.columns:
                    continue

                sub = grp.copy()
                sub[col] = pd.to_numeric(sub[col], errors="coerce")
                sub = sub[sub[col].notna()]
                if sub.empty:
                    continue

                # Minimum games filter
                min_g = MIN_GAMES.get(col, MIN_GAMES["default"])
                if "Games" in sub.columns:
                    sub = sub[pd.to_numeric(sub["Games"], errors="coerce").fillna(0) >= min_g]
                if sub.empty:
                    continue

                # Minimum wins filter
                min_w = MIN_WINS.get(col)
                if min_w is not None and "Wins" in sub.columns:
                    sub = sub[pd.to_numeric(sub["Wins"], errors="coerce").fillna(0) >= min_w]
                if sub.empty:
                    continue

                # BlowoutRate: must have blowout WINS specifically
                                
                if col == "BlowoutRate" and "BlowoutWins" in sub.columns:
                    sub = sub[pd.to_numeric(sub["BlowoutWins"], errors="coerce").fillna(0) >= 3]
                if sub.empty:
                    continue

                # Most Consistent requires a winning record
                if col == "MarginStd" and "WinPct" in sub.columns:
                    sub = sub[pd.to_numeric(sub["WinPct"], errors="coerce").fillna(0) >= 0.500]
                if sub.empty:
                    continue


                # Most Consistent requires a winning record
                if col == "MarginStd" and "WinPct" in sub.columns:
                    sub = sub[pd.to_numeric(sub["WinPct"], errors="coerce").fillna(0) >= 0.500]
                if sub.empty:
                    continue


                winner = (
                    sub.nlargest(1, col).iloc[0]
                    if higher
                    else sub.nsmallest(1, col).iloc[0]
                )

                # Skip meaningless zero values
                metric_val = float(_sf(winner.get(col)))
                if col in SKIP_IF_ZERO and metric_val == 0.0:
                    continue

                rows.append({
                    "Season":       season,
                    "Scope":        scope_label,
                    "Gender":       gender,
                    "Class":        cls,
                    "Region":       region,
                    "Category":     category,
                    "CategorySort": int(cat_sort),
                    "TrophyName":   trophy_name,
                    "TrophySort":   int(trophy_sort),
                    "CardKicker":   category,
                    "CardTitle":    str(winner.get("Team", "")),
                    "CardSub":      _record(winner),
                    "CardMetric":   metric_val,
                })

    df = pd.DataFrame(rows)

    for c in ["Season", "Scope", "Gender", "Class", "Region",
              "Category", "TrophyName", "CardKicker", "CardTitle", "CardSub"]:
        if c in df.columns:
            df[c] = df[c].astype(str)
    for c in ["CategorySort", "TrophySort"]:
        if c in df.columns:
            df[c] = df[c].astype(int)
    if "CardMetric" in df.columns:
        df["CardMetric"] = df["CardMetric"].astype(float)

    atomic_write_parquet(df, TROPHY_V50_PATH)
    print(f"  ✅ trophy_room_v50  →  {len(df)} trophies  →  {TROPHY_V50_PATH}")
    return df




# --------------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------------


def main() -> None:
    parse_args()

    for d in [CORE_DIR, PRED_DIR, CAL_DIR, PUB_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    print("NIGHTLY V50 START"); import sys; sys.stdout.flush()

    print("1) Loading truth.csv"); sys.stdout.flush()
    truth = load_truth(TRUTH_PATH)

    print("2) Building game core (lean facts)"); sys.stdout.flush()
    games = build_games_core(truth)
    atomic_write_parquet(games, GAMES_CORE_V50)

    print("3) Building teams core (lean facts)"); sys.stdout.flush()
    teams_core = build_teams_core(games)
    atomic_write_parquet(teams_core, TEAMS_CORE_V50)

    print("4) Building teams analytics (~150 metrics)"); sys.stdout.flush()
    teams_analytics = build_teams_analytics(truth, games)
    atomic_write_parquet(teams_analytics, TEAMS_ANALYTICS_V50)

    # 3b) Backfill TI in teams_core from analytics where missing
    try:
        tc = teams_core.copy()
        ta = teams_analytics[["TeamKey", "TI"]].copy()

        tc["TeamKey"] = tc["TeamKey"].astype(str).str.strip()
        ta["TeamKey"] = ta["TeamKey"].astype(str).str.strip()
        ta["TI"] = pd.to_numeric(ta["TI"], errors="coerce")

        merged = tc.merge(ta, on="TeamKey", how="left", suffixes=("", "_ana"))
        if "TI_ana" in merged.columns:
            merged["TI"] = merged["TI_ana"].where(
                merged["TI_ana"].notna(), merged.get("TI")
            )
            merged = merged.drop(columns=["TI_ana"])

        atomic_write_parquet(merged, TEAMS_CORE_V50)
        print("   Backfilled TI in teams_core from analytics.")
        sys.stdout.flush()
    except Exception as e:
        print("   WARNING: TI backfill failed:", e)
        sys.stdout.flush()

    print("5) Building games analytics (descriptive)"); sys.stdout.flush()
    games_analytics = build_games_analytics(games, truth)
    atomic_write_parquet(games_analytics, GAMES_ANALYTICS_V50)

    print("6) Running prediction engine"); sys.stdout.flush()
    arch = PRED_DIR / "archives"
    arch.mkdir(exist_ok=True)
    if PRED_CURRENT.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        shutil.copy2(PRED_CURRENT, arch / f"games_predictions_current__before__{stamp}.parquet")
    run_pred_engine()
    pred = pd.read_parquet(PRED_CURRENT).copy()
    pred["GameID"] = clean_gameids(pred["GameID"])

    print("7) Building public bundle (facts + preds + grading)"); sys.stdout.flush()
    public = build_public_bundle(games, pred)
    atomic_write_parquet(public, PUBLIC_V50)

    print("8) Building performance / calibration"); sys.stdout.flush()
    perf_summary, perf_games, perf_calib, perf_spread = build_performance(public)
    atomic_write_parquet(perf_summary, PERF_SUMMARY_V50)
    atomic_write_parquet(perf_games,   PERF_GAMES_V50)
    atomic_write_parquet(perf_calib,   PERF_CALIB_V50)
    atomic_write_parquet(perf_spread,  PERF_SPREAD_V50)

    print("9) Building nightly report"); sys.stdout.flush()
    report = build_nightly_report(games, pred, public)
    atomic_write_parquet(report, NIGHTLY_REPORT_V50)

    print("10) Building Team of the Week nominees"); sys.stdout.flush()
    build_team_of_week(games, teams_core, public)

    print("11) Building Trophy Room"); sys.stdout.flush()
    build_trophy_room_v50(teams_analytics)

    print(f"  --- V50 OUTPUTS ---")
    print(f"  games_core        {GAMES_CORE_V50}  shape={games.shape}")
    print(f"  teams_core        {TEAMS_CORE_V50}  shape={teams_core.shape}")
    print(f"  teams_analytics   {TEAMS_ANALYTICS_V50}  shape={teams_analytics.shape}")
    print(f"  games_analytics   {GAMES_ANALYTICS_V50}  shape={games_analytics.shape}")
    print(f"  public            {PUBLIC_V50}  shape={public.shape}")
    print(f"  perf_summary      {PERF_SUMMARY_V50}")
    print(f"  nightly_report    {NIGHTLY_REPORT_V50}")
    print(f"  trophy_room_v50   {TROPHY_V50_PATH}")
    print("V50 SUCCESS"); sys.stdout.flush()


if __name__ == "__main__":
    main()
