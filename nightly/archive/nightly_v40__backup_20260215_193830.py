from __future__ import annotations



# ======================================================================================
# NIGHTLY V40 (NO CORE_V30)
# - Single truth: facts cores are facts-only
# - Predictions are separate: predictions parquet is preds-only
# - Public bundle is the ONLY merged artifact (facts + preds + grading)
# - Heavy guardrails: schema locks, separation audits, keyset checks, stats report
# ======================================================================================



from pathlib import Path
import sys
import tempfile
import importlib.util
import shutil
from datetime import datetime, timezone



import numpy as np
import pandas as pd



# ----------------- Imports & Constants ------------------------------------------------




ROOT = Path(r"C:\ANALYTICS207")
DATADIR = ROOT / "data"


# Make project imports work when running as: py nightly\nightly_v40.py
# (This is the same pattern used by your working nightly build script.)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))




CORE_DIR = DATADIR / "core"
PRED_DIR = DATADIR / "predictions"
CAL_DIR = DATADIR / "calibration"
PUB_DIR = DATADIR / "public"




TRUTH_PATH = DATADIR / "truth.csv"




# v40 outputs
TEAMS_V40 = CORE_DIR / "teams_team_season_core_v40.parquet"
GAMES_FACTS_V40 = CORE_DIR / "games_game_core_v40.parquet"
PRED_CURRENT_V40 = PRED_DIR / "games_predictions_current.parquet"
PUBLIC_GAMES_V40 = PUB_DIR / "games_public_v40.parquet"




PERF_SUMMARY_V40 = CAL_DIR / "performance_summary_v40.parquet"
PERF_GAMES_V40 = CAL_DIR / "performance_games_v40.parquet"
PERF_CALIB_V40 = CAL_DIR / "performance_calibration_v40.parquet"
PERF_SPREAD_V40 = CAL_DIR / "performance_by_spread_v40.parquet"
NIGHTLY_REPORT_V40 = CAL_DIR / "nightly_report_v40.parquet"


# Optional compat filenames (these are v40-built artifacts written to legacy names)
COMPAT_WRITE = True
COMPAT_TEAMS = DATADIR / "teams_team_season_core_v30.parquet"
COMPAT_GAMES = DATADIR / "games_game_core_v30.parquet"
COMPAT_PREDS = DATADIR / "games_predictions_current.parquet"
COMPAT_PERF_GAMES = DATADIR / "performance_games_v30.parquet"
COMPAT_PERF_SUMMARY = DATADIR / "performance_summary_v30.parquet"
COMPAT_PERF_CALIB = DATADIR / "performance_calibration_v30.parquet"
COMPAT_PERF_SPREAD = DATADIR / "performance_by_spread_v30.parquet"


# Prediction engine script (should write COMPAT_PREDS OR we copy into it)
PRED_ENGINE_SCRIPT = ROOT / "walkforward" / "v34" / "pred_engine_walkforward_v40.py"


# Version strings
CORE_VERSION_V40 = "v40"
# Optional: if your engine stamps CoreVersion, keep it consistent here
# ENGINE_VERSION_EXPECTED = "v34cprod20260208"


PRED_COLS = ["PredHomeWinProb", "PredMargin", "PredHomeScore", "PredAwayScore", "PredTotalPoints"]
PRED_DERIVED_COLS = ["PredWinnerKey", "PredWinnerProb", "PredWinnerProbPct", "PredSpreadAbs"]
PRED_META_COLS = ["CoreVersion", "PredBuildID"]


PRED_ALL_COLS = ["GameID", "HomeKey", "AwayKey"] + PRED_META_COLS + PRED_COLS + PRED_DERIVED_COLS


# Facts-only: must not contain any of these
BANNED_FACTS_COLS = set(PRED_COLS + PRED_DERIVED_COLS + ["FavProb", "FavProbPct", "FavoriteIsHome", "FavoriteTeamKey", "ModelCorrect"])


# --------------------------------------------------------------------------------------
# Atomic I/O helpers
# --------------------------------------------------------------------------------------


def atomic_write_parquet(df: pd.DataFrame, outpath: Path) -> None:
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet", dir=str(outpath.parent)) as tmp:
        tmppath = Path(tmp.name)
    df.to_parquet(tmppath, index=False)
    tmppath.replace(outpath)


# --------------------------------------------------------------------------------------
# Compat v30 helpers (FIXED)
# - Your pasted file had Step 5 code executing at import-time and calling undefined
#   functions/vars (build_compat_teams_v30_from_v40, teams_facts, games_public).
# - This section defines the missing compat functions and ensures compat writes happen
#   inside main(), not at import time.
# --------------------------------------------------------------------------------------


def _latest_team_snapshot_from_games(
    games_public: pd.DataFrame,
    col_home: str,
    col_away: str,
    out_col: str,
) -> pd.DataFrame:
    g = games_public.copy()

    if "Date" in g.columns:
        g["Date"] = pd.to_datetime(g["Date"], errors="coerce")

    need = {"HomeKey", "AwayKey", col_home, col_away}
    missing = [c for c in need if c not in g.columns]
    if missing:
        return pd.DataFrame(columns=["TeamKey", out_col])

    cols_home = ["HomeKey", col_home]
    cols_away = ["AwayKey", col_away]
    if "Date" in g.columns:
        cols_home.insert(1, "Date")
        cols_away.insert(1, "Date")

    home = g[cols_home].rename(columns={"HomeKey": "TeamKey", col_home: out_col})
    away = g[cols_away].rename(columns={"AwayKey": "TeamKey", col_away: out_col})
    snap = pd.concat([home, away], ignore_index=True)

    snap["TeamKey"] = snap["TeamKey"].astype(str).str.strip()
    if "Date" in snap.columns:
        snap["Date"] = pd.to_datetime(snap["Date"], errors="coerce")
    snap[out_col] = pd.to_numeric(snap[out_col], errors="coerce")
    snap = snap.dropna(subset=["TeamKey", out_col])

    if snap.empty:
        return pd.DataFrame(columns=["TeamKey", out_col])

    if "Date" in snap.columns:
        snap = snap.sort_values(["TeamKey", "Date"])
    else:
        snap = snap.sort_values(["TeamKey"])

    snap = snap.drop_duplicates(subset=["TeamKey"], keep="last")
    return snap[["TeamKey", out_col]].copy()


def build_compat_teams_v30_from_v40(
    teams_v40: pd.DataFrame,
    games_v40_public: pd.DataFrame,
) -> pd.DataFrame:
    """
    Produce a v30-shaped teams file from v40 facts + the v40 public bundle.
    Uses your existing core_v30 module (file: C:\\ANALYTICS207\\core\\core_v30.py).
    """
    import core.core_v30 as cv30  # <-- FIX (was core.corev30)

    out = teams_v40.copy()
    if "TeamKey" in out.columns:
        out["TeamKey"] = out["TeamKey"].astype(str).str.strip()

    # Pull latest TI/PI/Rank snapshots if they exist in the public bundle
    out = out.merge(_latest_team_snapshot_from_games(games_v40_public, "HomeTI", "AwayTI", "TI"), on="TeamKey", how="left")
    out = out.merge(_latest_team_snapshot_from_games(games_v40_public, "HomePI", "AwayPI", "PI"), on="TeamKey", how="left")
    out = out.merge(_latest_team_snapshot_from_games(games_v40_public, "HomeRank", "AwayRank", "Rank"), on="TeamKey", how="left")

    # Compute TSR and tiers if possible (safe early season)
    games_played = games_v40_public.copy()
    if "Played" in games_played.columns:
        games_played = games_played[games_played["Played"].fillna(False)].copy()

    # Your core_v30 uses computetsrelov30/addtsrandtiersv30/ensureteamschemav30
    if hasattr(cv30, "computetsrelov30") and hasattr(cv30, "addtsrandtiersv30"):
        try:
            tsr_series = cv30.computetsrelov30(out, games_played)
        except Exception:
            tsr_series = None

        if tsr_series is not None and len(tsr_series) > 0 and "TeamKey" in out.columns:
            tsr_series.index = tsr_series.index.astype(str).str.strip()
            out = out.set_index("TeamKey", drop=False)
            out["TSR"] = tsr_series
            out = out.reset_index(drop=True)

        out = cv30.addtsrandtiersv30(out)

    if hasattr(cv30, "ensureteamschemav30"):
        out = cv30.ensureteamschemav30(out)

    return out


def build_compat_games_v30_from_v40(games_v40_public: pd.DataFrame) -> pd.DataFrame:
    """
    Produce a v30-shaped games file from the v40 public bundle.
    This is intentional: legacy pages expect Pred* columns in the games file.
    """
    import core.core_v30 as cv30  # <-- FIX (was core.corev30)

    out = games_v40_public.copy()
    if hasattr(cv30, "ensuregameschemav30"):
        out = cv30.ensuregameschemav30(out)
    return out



def build_compat_games_v30_from_v40(games_v40_public: pd.DataFrame) -> pd.DataFrame:
    """
    Produce a v30-shaped games file from the v40 public bundle.
    Legacy pages expect Pred* columns in the games file.
    """
    import core.core_v30 as cv30  # FIX: your module is core/core_v30.py

    out = games_v40_public.copy()
    if hasattr(cv30, "ensuregameschemav30"):
        out = cv30.ensuregameschemav30(out)
    return out

# --------------------------------------------------------------------------------------
# Guardrails / validations
# --------------------------------------------------------------------------------------


def clean_gameids(s: pd.Series) -> pd.Series:
    x = s.astype(str).str.strip()
    x = x.str.replace(r"\.0$", "", regex=True)
    x = x.str.replace(",", "", regex=False)
    return x


def assert_no_banned_facts_cols(df: pd.DataFrame, name: str) -> None:
    bad = [c for c in df.columns if c in BANNED_FACTS_COLS or str(c).startswith("Pred")]
    if bad:
        raise RuntimeError(f"{name} contains banned prediction/eval columns: {bad}")


def assert_unique_key(df: pd.DataFrame, key: str, name: str) -> None:
    if key not in df.columns:
        raise RuntimeError(f"{name} missing required key column: {key}")
    if df[key].isna().any():
        raise RuntimeError(f"{name} has missing {key}")
    if df[key].duplicated().any():
        dups = int(df[key].duplicated().sum())
        raise RuntimeError(f"{name} has duplicate {key} (count={dups})")


def assert_keyset_equal(games: pd.DataFrame, pred: pd.DataFrame) -> None:
    g_ids = set(clean_gameids(games["GameID"]).dropna().unique().tolist())
    p_ids = set(clean_gameids(pred["GameID"]).dropna().unique().tolist())
    if len(games) != len(pred):
        raise RuntimeError(f"Pred row mismatch: pred={len(pred)} games={len(games)}")
    if g_ids != p_ids:
        overlap = len(g_ids.intersection(p_ids))
        raise RuntimeError(f"Pred GameID set mismatch. overlap={overlap} games={len(g_ids)} pred={len(p_ids)}")


def validate_predictions(games_facts: pd.DataFrame, pred: pd.DataFrame) -> None:
    for c in PRED_ALL_COLS:
        if c not in pred.columns:
            raise RuntimeError(f"games_predictions_current missing required column: {c}")

    pred2 = pred.copy()
    pred2["GameID"] = clean_gameids(pred2["GameID"])
    games2 = games_facts.copy()
    games2["GameID"] = clean_gameids(games2["GameID"])

    assert_unique_key(pred2, "GameID", "predictions_current")
    assert_unique_key(games2, "GameID", "games_facts")
    assert_keyset_equal(games2, pred2)

    # numeric/range checks
    wp = pd.to_numeric(pred2["PredHomeWinProb"], errors="coerce")
    if wp.isna().any():
        raise RuntimeError("PredHomeWinProb has missing values")
    if (wp < 0).any() or (wp > 1).any():
        raise RuntimeError("PredHomeWinProb out of [0,1] range")

    pm = pd.to_numeric(pred2["PredMargin"], errors="coerce")
    if pm.isna().any():
        raise RuntimeError("PredMargin has missing values")


def validate_key_match(games_facts: pd.DataFrame, pred: pd.DataFrame) -> None:
    g = games_facts[["GameID", "HomeKey", "AwayKey"]].copy()
    p = pred[["GameID", "HomeKey", "AwayKey"]].copy()
    g["GameID"] = clean_gameids(g["GameID"])
    p["GameID"] = clean_gameids(p["GameID"])

    m = g.merge(p, on="GameID", how="left", suffixes=("_games", "_pred"))
    bad_home = (m["HomeKey_games"].astype(str).str.strip() != m["HomeKey_pred"].astype(str).str.strip()).sum()
    bad_away = (m["AwayKey_games"].astype(str).str.strip() != m["AwayKey_pred"].astype(str).str.strip()).sum()
    if bad_home or bad_away:
        raise RuntimeError(f"HomeKey/AwayKey mismatch between games and preds: bad_home={bad_home} bad_away={bad_away}")


# --------------------------------------------------------------------------------------
# Prediction engine runner
# --------------------------------------------------------------------------------------


def run_pred_engine() -> None:
    if not PRED_ENGINE_SCRIPT.exists():
        raise FileNotFoundError(f"Missing prediction engine at: {PRED_ENGINE_SCRIPT}")

    spec = importlib.util.spec_from_file_location("pred_engine_v40", str(PRED_ENGINE_SCRIPT))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load engine module: {PRED_ENGINE_SCRIPT}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]

    if not hasattr(mod, "main"):
        raise RuntimeError("Prediction engine has no main()")

    mod.main()  # type: ignore[attr-defined]

    # Engine is expected to write to COMPAT_PREDS (legacy name) so existing tooling stays happy.
    if not COMPAT_PREDS.exists():
        raise RuntimeError(f"Engine did not write expected preds file: {COMPAT_PREDS}")


# --------------------------------------------------------------------------------------
# Core facts build (v40) from truth.csv
# --------------------------------------------------------------------------------------


def load_truth_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "ScrapedAt" in df.columns:
        df["ScrapedAt"] = pd.to_datetime(df["ScrapedAt"], errors="coerce")

    # Normalize some common string columns (safe if absent)
    for col in ["Gender", "Team1", "Team2", "HomeTeam", "AwayTeam", "Winner", "Loser"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].astype(str).str.strip().str.title()

    return df


def parse_div(div: str) -> tuple[str, str]:
    d = str(div) if div is not None else ""
    if "-" not in d:
        return ("Unknown", "Unknown")
    region, cls = d.split("-", 1)
    return (region.strip().title(), cls.strip().upper())


def coalesce_bool_series(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    for c in candidates:
        if c in df.columns:
            s = df[c]
            if s.dtype == bool:
                return s
            ss = s.astype(str).str.strip().str.lower()
            return ss.isin(["true", "t", "1", "y", "yes"])
    return None


def build_team_key(team: str, gender: str, cls: str, region: str) -> str:
    return f"{str(team).strip()}{str(gender).strip()}{str(cls).strip()}{str(region).strip()}"


def build_games_facts_v40(truth: pd.DataFrame) -> pd.DataFrame:
    g = truth.copy()

    # Season: year of Date if available
    if "Date" in g.columns:
        g["Season"] = g["Date"].dt.year.astype("Int64").astype(str)
    else:
        g["Season"] = pd.Series([None] * len(g), dtype=object)

    # Home/Away names
    if "HomeTeam" not in g.columns or "AwayTeam" not in g.columns:
        raise RuntimeError("truth.csv must include HomeTeam and AwayTeam columns")
    g["Home"] = g["HomeTeam"].astype(str).str.strip()
    g["Away"] = g["AwayTeam"].astype(str).str.strip()

    # Map each team -> division snapshot from SchoolDivision if present
    team_div_map: dict[str, str] = {}
    if "SchoolDivision" in g.columns:
        for _, row in g.iterrows():
            div = row.get("SchoolDivision", None)
            div = str(div).strip() if div is not None else ""
            if not div:
                continue
            for tc in ["Team1", "Team2", "HomeTeam", "AwayTeam"]:
                if tc in g.columns:
                    t = row.get(tc, None)
                    t = str(t).strip() if t is not None else ""
                    if t and t not in team_div_map:
                        team_div_map[t] = div

    def get_team_div(team: str) -> str:
        return team_div_map.get(str(team).strip(), "Unknown-Unknown")

    g["HomeDivision"] = g["Home"].apply(get_team_div)
    g["AwayDivision"] = g["Away"].apply(get_team_div)

    home_parsed = g["HomeDivision"].map(parse_div)
    away_parsed = g["AwayDivision"].map(parse_div)

    g["HomeRegion"] = [r for r, _ in home_parsed]
    g["HomeClass"] = [c for _, c in home_parsed]
    g["AwayRegion"] = [r for r, _ in away_parsed]
    g["AwayClass"] = [c for _, c in away_parsed]

    # Team keys
    if "Gender" not in g.columns:
        g["Gender"] = None

    g["HomeKey"] = g.apply(lambda r: build_team_key(r["Home"], r.get("Gender", ""), r["HomeClass"], r["HomeRegion"]), axis=1)
    g["AwayKey"] = g.apply(lambda r: build_team_key(r["Away"], r.get("Gender", ""), r["AwayClass"], r["AwayRegion"]), axis=1)

    # Scores / Played / Margin / WinnerTeam
    g["HomeScore"] = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
    g["AwayScore"] = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
    g["Played"] = g["HomeScore"].notna() & g["AwayScore"].notna()
    g["Margin"] = np.where(g["Played"], g["HomeScore"] - g["AwayScore"], np.nan)

    g["WinnerTeam"] = np.where(
        g["Played"] & (g["HomeScore"] > g["AwayScore"]),
        g["Home"],
        np.where(
            g["Played"] & (g["AwayScore"] > g["HomeScore"]),
            g["Away"],
            None,
        ),
    )

    # Neutral detection
    neutral = coalesce_bool_series(g, ["NeutralSite", "Neutral", "IsNeutral", "NeutralFlag"])
    if neutral is None:
        if "Site" in g.columns:
            neutral = g["Site"].astype(str).str.lower().str.contains("neutral", na=False)
        elif "LocationType" in g.columns:
            neutral = g["LocationType"].astype(str).str.lower().eq("neutral")
        else:
            neutral = pd.Series([False] * len(g), dtype=bool)
    g["IsNeutral"] = neutral

    # Ensure GameID exists
    if "GameID" not in g.columns:
        raise RuntimeError("truth.csv must include GameID column")

    # Add opponent-strength columns if present in truth (optional)
    for c in ["TI", "PI", "Rank"]:
        if c not in g.columns:
            g[c] = np.nan

    if "Team1" in g.columns:
        tmr = g[["GameID", "Team1", "TI", "PI", "Rank"]].copy()
        tmr["Team1"] = tmr["Team1"].astype(str).str.strip()
        tmr = tmr.rename(columns={"Team1": "MetricTeam", "TI": "MetricTI", "PI": "MetricPI", "Rank": "MetricRank"})

        g = g.merge(
            tmr[["GameID", "MetricTeam", "MetricTI", "MetricPI", "MetricRank"]],
            how="left",
            left_on=["GameID", "Home"],
            right_on=["GameID", "MetricTeam"],
        )
        g = g.rename(columns={"MetricTI": "HomeTI", "MetricPI": "HomePI", "MetricRank": "HomeRank"})
        g = g.drop(columns=["MetricTeam"], errors="ignore")

        g = g.merge(
            tmr[["GameID", "MetricTeam", "MetricTI", "MetricPI", "MetricRank"]],
            how="left",
            left_on=["GameID", "Away"],
            right_on=["GameID", "MetricTeam"],
            suffixes=("", "_away"),
        )
        g = g.rename(columns={"MetricTI": "AwayTI", "MetricPI": "AwayPI", "MetricRank": "AwayRank"})
        g = g.drop(columns=["MetricTeam"], errors="ignore")
    else:
        g["HomeTI"] = np.nan
        g["HomePI"] = np.nan
        g["HomeRank"] = np.nan
        g["AwayTI"] = np.nan
        g["AwayPI"] = np.nan
        g["AwayRank"] = np.nan

    # Canonical facts columns to keep (narrow, stable)
    keep = [
        "GameID", "Date", "Season", "Gender",
        "Home", "Away", "HomeKey", "AwayKey",
        "HomeClass", "AwayClass", "HomeRegion", "AwayRegion",
        "HomeDivision", "AwayDivision",
        "HomeScore", "AwayScore", "Played", "Margin", "IsNeutral", "WinnerTeam",
        "HomeTI", "HomePI", "HomeRank", "AwayTI", "AwayPI", "AwayRank",
        "ScrapedAt",
    ]
    keep = [c for c in keep if c in g.columns]
    out = g.drop_duplicates(subset="GameID").reset_index(drop=True)[keep].copy()
    out["CoreVersion"] = CORE_VERSION_V40

    # Normalize IDs
    out["GameID"] = clean_gameids(out["GameID"])

    # Guardrails
    assert_unique_key(out, "GameID", "games_facts_v40")
    assert_no_banned_facts_cols(out, "games_facts_v40")

    return out


def build_teams_facts_v40(games_facts: pd.DataFrame) -> pd.DataFrame:
    # Build a simple team-season core from facts-only game logs.
    g = games_facts.copy()
    if "Played" not in g.columns:
        g["Played"] = False

    # Create long view: each game twice (home/away)
    home = g.copy()
    home["TeamKey"] = home["HomeKey"]
    home["Team"] = home["Home"]
    home["For"] = pd.to_numeric(home.get("HomeScore", np.nan), errors="coerce")
    home["Against"] = pd.to_numeric(home.get("AwayScore", np.nan), errors="coerce")
    home["IsHome"] = True

    away = g.copy()
    away["TeamKey"] = away["AwayKey"]
    away["Team"] = away["Away"]
    away["For"] = pd.to_numeric(away.get("AwayScore", np.nan), errors="coerce")
    away["Against"] = pd.to_numeric(away.get("HomeScore", np.nan), errors="coerce")
    away["IsHome"] = False

    long = pd.concat([home, away], ignore_index=True)

    # Attach class/region from each team's side
    long["Class"] = np.where(long["IsHome"], long.get("HomeClass", None), long.get("AwayClass", None))
    long["Region"] = np.where(long["IsHome"], long.get("HomeRegion", None), long.get("AwayRegion", None))

    # Only played games count toward stats
    longp = long[long["Played"].fillna(False)].copy()
    longp["Margin"] = pd.to_numeric(longp["For"], errors="coerce") - pd.to_numeric(longp["Against"], errors="coerce")

    def agg_team(sub: pd.DataFrame) -> pd.Series:
        games = int(len(sub))
        wins = int((sub["Margin"] > 0).sum())
        losses = int((sub["Margin"] < 0).sum())
        ties = int((sub["Margin"] == 0).sum())
        pts_for = float(pd.to_numeric(sub["For"], errors="coerce").fillna(0).sum())
        pts_against = float(pd.to_numeric(sub["Against"], errors="coerce").fillna(0).sum())
        ppg = float(pts_for / games) if games else np.nan
        oppg = float(pts_against / games) if games else np.nan
        marginpg = float((sub["Margin"]).mean()) if games else np.nan
        winpct = float(wins / games) if games else np.nan
        return pd.Series({
            "Games": games,
            "Wins": wins,
            "Losses": losses,
            "Ties": ties,
            "Record": f"{wins}-{losses}-{ties}",
            "WinPct": winpct,
            "PointsFor": pts_for,
            "PointsAgainst": pts_against,
            "PPG": ppg,
            "OPPG": oppg,
            "MarginPG": marginpg,
            "OffEff": ppg,
            "DefEff": oppg,
            "NetEff": (ppg - oppg) if (ppg == ppg and oppg == oppg) else np.nan,
        })

    group_cols = [c for c in ["TeamKey", "Team", "Season", "Gender", "Class", "Region"] if c in longp.columns]
    teams = longp.groupby(group_cols, dropna=False).apply(agg_team, include_groups=False).reset_index()

    # Ensure at least one row per team even if no played games yet:
    if teams.empty:
        # Fall back to a roster built from scheduled games (facts-only)
        long0 = long.copy()
        group_cols0 = [c for c in ["TeamKey", "Team", "Season", "Gender", "Class", "Region"] if c in long0.columns]
        base = long0.dropna(subset=["TeamKey"]).drop_duplicates(subset=group_cols0)[group_cols0].copy()
        for c in ["Games", "Wins", "Losses", "Ties", "WinPct", "PointsFor", "PointsAgainst", "PPG", "OPPG", "MarginPG", "OffEff", "DefEff", "NetEff"]:
            base[c] = np.nan
        base["Record"] = "0-0-0"
        teams = base

    teams["CoreVersion"] = CORE_VERSION_V40
    if "TeamKey" in teams.columns:
        teams["TeamKey"] = teams["TeamKey"].astype(str).str.strip()

        # TeamKey repeats across seasons/slices; enforce uniqueness on the real composite key
        dups = int(teams.duplicated(subset=["TeamKey", "Season", "Gender", "Class", "Region"]).sum())
        if dups:
            raise RuntimeError(f"teams_core_v40 has duplicate TeamKey+Season+Gender+Class+Region (count={dups})")

    return teams


# --------------------------------------------------------------------------------------
# Merge + grading (public bundle only)
# --------------------------------------------------------------------------------------


def merge_predictions(games_facts: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    g = games_facts.copy()
    p = pred.copy()

    g["GameID"] = clean_gameids(g["GameID"])
    p["GameID"] = clean_gameids(p["GameID"])

    keep = [c for c in PRED_ALL_COLS if c in p.columns]
    p2 = p[keep].drop_duplicates(subset="GameID", keep="first").copy()

    # Merge by GameID only (engine keys may differ from v40 keys)
    out = g.merge(p2, on=["GameID"], how="left", suffixes=("", "_pred"))

    # Guardrail: preds must exist for every game
    missing_pm = int(pd.to_numeric(out["PredMargin"], errors="coerce").isna().sum())
    missing_wp = int(pd.to_numeric(out["PredHomeWinProb"], errors="coerce").isna().sum())
    if missing_pm or missing_wp:
        raise RuntimeError(f"After merge missing PredMargin={missing_pm}, PredHomeWinProb={missing_wp}")

    # Non-fatal key mismatch note + remove pred-side keys to avoid confusion downstream
    if "HomeKey_pred" in out.columns and "AwayKey_pred" in out.columns:
        bad_home = (out["HomeKey"].astype(str).str.strip() != out["HomeKey_pred"].astype(str).str.strip()).sum()
        bad_away = (out["AwayKey"].astype(str).str.strip() != out["AwayKey_pred"].astype(str).str.strip()).sum()
        print(f"KEY MISMATCH NOTE (non-fatal): bad_home={int(bad_home)} bad_away={int(bad_away)}")
        out = out.drop(columns=[c for c in ["HomeKey_pred", "AwayKey_pred"] if c in out.columns])

    return out


def add_grading_fields(games_plus: pd.DataFrame) -> pd.DataFrame:
    out = games_plus.copy()

    # ActualMargin (facts-derived)
    hs = pd.to_numeric(out.get("HomeScore", np.nan), errors="coerce")
    aS = pd.to_numeric(out.get("AwayScore", np.nan), errors="coerce")
    played = out.get("Played", False)
    played = played.fillna(False) if isinstance(played, pd.Series) else pd.Series([False] * len(out))

    out["ActualMargin"] = np.where(played, hs - aS, np.nan)

    # FavoriteIsHome (prediction-derived; allowed ONLY in public bundle)
    phwp = pd.to_numeric(out["PredHomeWinProb"], errors="coerce")
    out["FavoriteIsHome"] = phwp >= 0.5

    # FavProb: favorite win probability
    out["FavProb"] = np.where(out["FavoriteIsHome"].fillna(False), phwp, 1.0 - phwp)

    # ModelCorrect: favorite won
    am = pd.to_numeric(out["ActualMargin"], errors="coerce")
    fav_is_home = out["FavoriteIsHome"].fillna(False)
    out["ModelCorrect"] = np.where(
        played,
        np.where(fav_is_home, am > 0, am < 0),
        np.nan,
    )

    return out


def build_public_bundle(games_plus: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "GameID", "Date", "Season", "Gender",
        "Home", "Away", "HomeKey", "AwayKey",
        "HomeClass", "AwayClass", "HomeRegion", "AwayRegion",
        "HomeScore", "AwayScore", "Played", "IsNeutral",
        "PredHomeWinProb", "PredMargin", "PredHomeScore", "PredAwayScore", "PredTotalPoints",
        "PredWinnerKey", "PredWinnerProbPct", "PredSpreadAbs",
        "ActualMargin", "FavoriteIsHome", "FavProb", "ModelCorrect",
        "CoreVersion", "PredBuildID",
    ]
    cols = [c for c in keep if c in games_plus.columns]
    out = games_plus[cols].copy()
    return out


# --------------------------------------------------------------------------------------
# Performance / calibration (v40)
# --------------------------------------------------------------------------------------


def build_performance_tables_v40(games_public: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Mirrors the essentials of v30 performance outputs but computed from public bundle.
    df = games_public.copy()

    # Only grade played games
    played = df[df.get("Played", False).fillna(False)].copy()
    if played.empty:
        summary = pd.DataFrame([{
            "TotalGames": 0,
            "CorrectGames": 0,
            "OverallAccuracy": 0.0,
            "UpsetRate": 0.0,
            "MAE": 0.0,
            "RMSE": 0.0,
            "Within5Pts": 0.0,
            "Within10Pts": 0.0,
            "BrierScore": 0.0,
        }])
        perfgames = pd.DataFrame(columns=["Date", "Home", "Away", "HomeScore", "AwayScore", "Favorite", "FavProbPct", "ModelCorrect", "PredMargin", "ActualMargin", "Gender"])
        calib = pd.DataFrame(columns=["ConfBucket", "Games", "Correct", "HitRate", "AvgProb"])
        spreadperf = pd.DataFrame(columns=["SpreadBucket", "Games", "Correct", "HitRate", "AvgSpread", "MAE"])
        return summary, perfgames, calib, spreadperf

    hs = pd.to_numeric(played["HomeScore"], errors="coerce")
    aS = pd.to_numeric(played["AwayScore"], errors="coerce")
    outcome_home = np.where(hs > aS, 1.0, np.where(hs < aS, 0.0, 0.5))

    phwp = pd.to_numeric(played["PredHomeWinProb"], errors="coerce")
    predmargin = pd.to_numeric(played["PredMargin"], errors="coerce")
    actualmargin = pd.to_numeric(played["ActualMargin"], errors="coerce")

    fav_is_home = played["FavoriteIsHome"].fillna(False)
    favorite = np.where(fav_is_home, played["Home"], played["Away"])
    favprob = np.where(fav_is_home, phwp, 1.0 - phwp)
    favprobpct = 100.0 * favprob

    model_correct = played["ModelCorrect"].fillna(False)

    perfgames = pd.DataFrame({
        "Date": played.get("Date"),
        "Home": played.get("Home"),
        "Away": played.get("Away"),
        "HomeScore": played.get("HomeScore"),
        "AwayScore": played.get("AwayScore"),
        "Favorite": favorite,
        "FavProbPct": favprobpct,
        "ModelCorrect": model_correct,
        "PredMargin": predmargin,
        "ActualMargin": actualmargin,
        "Gender": played.get("Gender", np.nan),
    })

    totalgames = int(len(perfgames))
    correctgames = int(pd.Series(perfgames["ModelCorrect"]).fillna(False).sum())
    overallacc = float(100.0 * correctgames / totalgames) if totalgames else 0.0
    upsetrate = float(100.0 - overallacc) if totalgames else 0.0

    err = (predmargin - actualmargin).abs()
    mae = float(err.mean()) if err.notna().any() else 0.0
    rmse = float(np.sqrt(((predmargin - actualmargin) ** 2).mean())) if predmargin.notna().any() and actualmargin.notna().any() else 0.0
    within5 = float(100.0 * (err <= 5.0).mean()) if err.notna().any() else 0.0
    within10 = float(100.0 * (err <= 10.0).mean()) if err.notna().any() else 0.0
    brier = float(((phwp - outcome_home) ** 2).mean()) if phwp.notna().any() else 0.0

    summary = pd.DataFrame([{
        "TotalGames": totalgames,
        "CorrectGames": correctgames,
        "OverallAccuracy": overallacc,
        "UpsetRate": upsetrate,
        "MAE": mae,
        "RMSE": rmse,
        "Within5Pts": within5,
        "Within10Pts": within10,
        "BrierScore": brier,
    }])

    # Calibration buckets
    bins = [50, 60, 70, 80, 90, 101]
    labels = ["50-59", "60-69", "70-79", "80-89", "90-100"]
    tmp = perfgames.copy()
    tmp["ConfBucket"] = pd.cut(tmp["FavProbPct"].clip(50, 100), bins=bins, labels=labels, right=False)
    calib = (
        tmp.dropna(subset=["ConfBucket"])
           .groupby("ConfBucket", dropna=True, observed=False)
           .agg(
               Games=("ModelCorrect", "size"),
               Correct=("ModelCorrect", lambda s: int(pd.Series(s).fillna(False).sum())),
               HitRate=("ModelCorrect", lambda s: float(100.0 * pd.Series(s).fillna(False).mean()) if len(s) else 0.0),
               AvgProb=("FavProbPct", "mean"),
           )
           .reset_index()
    )

    # Spread buckets
    spreaddf = perfgames.copy()
    spreaddf["AbsSpread"] = pd.to_numeric(spreaddf["PredMargin"], errors="coerce").abs()
    spreadbins = [0, 2, 5, 8, 12, 100]
    spreadlabels = ["0-2", "2-5", "5-8", "8-12", "12+"]
    spreaddf["SpreadBucket"] = pd.cut(spreaddf["AbsSpread"], bins=spreadbins, labels=spreadlabels, right=False)

    def mae_bucket(sub: pd.DataFrame) -> float:
        if sub.empty:
            return 0.0
        pm = pd.to_numeric(sub["PredMargin"], errors="coerce")
        am = pd.to_numeric(sub["ActualMargin"], errors="coerce")
        return float((pm - am).abs().mean())

    spreadperf = (
        spreaddf.dropna(subset=["SpreadBucket"])
                .groupby("SpreadBucket", dropna=True, observed=False)
                .apply(lambda sub: pd.Series({
                    "Games": int(len(sub)),
                    "Correct": int(pd.Series(sub["ModelCorrect"]).fillna(False).sum()),
                    "HitRate": float(100.0 * pd.Series(sub["ModelCorrect"]).fillna(False).mean()) if len(sub) else 0.0,
                    "AvgSpread": float(pd.to_numeric(sub["AbsSpread"], errors="coerce").mean()) if len(sub) else 0.0,
                    "MAE": mae_bucket(sub),
                }), include_groups=False)
                .reset_index()
    )

    return summary, perfgames, calib, spreadperf


# --------------------------------------------------------------------------------------
# Nightly report (quick stats artifact)
# --------------------------------------------------------------------------------------


def build_nightly_report(games_facts: pd.DataFrame, pred: pd.DataFrame, public: pd.DataFrame) -> pd.DataFrame:
    g = games_facts.copy()
    p = pred.copy()
    pub = public.copy()

    total_games = int(len(g))
    played = int(g["Played"].fillna(False).sum()) if "Played" in g.columns else 0

    wp = pd.to_numeric(p.get("PredHomeWinProb", np.nan), errors="coerce")
    pm = pd.to_numeric(p.get("PredMargin", np.nan), errors="coerce")

    pub_played = pub[pub["Played"].fillna(False)].copy() if "Played" in pub.columns else pd.DataFrame()
    mae = np.nan
    acc = np.nan
    if not pub_played.empty and {"PredMargin", "ActualMargin", "ModelCorrect"}.issubset(pub_played.columns):
        mae = float((pd.to_numeric(pub_played["PredMargin"], errors="coerce") - pd.to_numeric(pub_played["ActualMargin"], errors="coerce")).abs().mean())
        acc = float(100.0 * pd.Series(pub_played["ModelCorrect"]).fillna(False).mean())

    return pd.DataFrame([{
        "BuiltAtUTC": datetime.now(timezone.utc).isoformat(),
        "TotalGames": total_games,
        "PlayedGames": played,
        "UnplayedGames": total_games - played,
        "PredWinProbMin": float(wp.min()) if wp.notna().any() else np.nan,
        "PredWinProbMax": float(wp.max()) if wp.notna().any() else np.nan,
        "PredWinProbMean": float(wp.mean()) if wp.notna().any() else np.nan,
        "PredMarginAbsMean": float(pm.abs().mean()) if pm.notna().any() else np.nan,
        "PublicPlayedMAE": mae,
        "PublicPlayedAccuracyPct": acc,
    }])


# --------------------------------------------------------------------------------------
# Main orchestration
# --------------------------------------------------------------------------------------


def main() -> None:
    print("NIGHTLY V40 START (NO CORE_V30)")

    for d in [CORE_DIR, PRED_DIR, CAL_DIR, PUB_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    if not TRUTH_PATH.exists():
        raise FileNotFoundError(f"Missing truth.csv at {TRUTH_PATH}")

    # 1) Facts-only core build
    print("1) Build v40 facts cores from truth.csv (no predictions)")
    truth = load_truth_csv(TRUTH_PATH)
    games_facts = build_games_facts_v40(truth)
    teams = build_teams_facts_v40(games_facts)

    # Guardrails: facts must never contain preds
    assert_no_banned_facts_cols(games_facts, "games_facts_v40")
    assert_no_banned_facts_cols(teams, "teams_core_v40")  # teams shouldn't have Pred* either

    atomic_write_parquet(teams, TEAMS_V40)
    atomic_write_parquet(games_facts, GAMES_FACTS_V40)

    # 2) Run prediction engine (writes legacy preds file), then load + validate
    print("2) Run prediction engine to generate predictions_current")
    arch_dir = PRED_DIR / "archives"
    arch_dir.mkdir(parents=True, exist_ok=True)
    if COMPAT_PREDS.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        shutil.copy2(COMPAT_PREDS, arch_dir / f"games_predictions_current__before__{stamp}.parquet")

    run_pred_engine()

    pred = pd.read_parquet(COMPAT_PREDS).copy()
    pred["GameID"] = clean_gameids(pred["GameID"])

    validate_predictions(games_facts, pred)
    # TEMP: engine and v40 facts may compute keys differently; GameID is the join contract
    validate_key_match(games_facts, pred)

    # Write v40 preds (canonical location)
    atomic_write_parquet(pred, PRED_CURRENT_V40)

    # 3) Merge to public + add grading
    print("3) Build v40 public bundle (facts + preds + grading)")
    games_plus = merge_predictions(games_facts, pred)
    games_plus = add_grading_fields(games_plus)

    public = build_public_bundle(games_plus)
    atomic_write_parquet(public, PUBLIC_GAMES_V40)

    # 4) Performance/calibration from public bundle
    print("4) Build v40 performance/calibration outputs")
    perf_summary, perf_games, perf_calib, perf_spread = build_performance_tables_v40(public)

    atomic_write_parquet(perf_summary, PERF_SUMMARY_V40)
    atomic_write_parquet(perf_games, PERF_GAMES_V40)
    atomic_write_parquet(perf_calib, PERF_CALIB_V40)
    atomic_write_parquet(perf_spread, PERF_SPREAD_V40)

    # 5) Nightly report artifact
    report = build_nightly_report(games_facts, pred, public)
    atomic_write_parquet(report, NIGHTLY_REPORT_V40)

    # 6) Optional compat outputs (v40-built, not v30-built)
    if COMPAT_WRITE:
        print("5) Write compat filenames (v40-built artifacts)")
        atomic_write_parquet(teams, COMPAT_TEAMS)
        # IMPORTANT: legacy games file should be the merged public view (pages expect Pred* there)
        atomic_write_parquet(public, COMPAT_GAMES)
        atomic_write_parquet(pred, COMPAT_PREDS)
        atomic_write_parquet(perf_summary, COMPAT_PERF_SUMMARY)
        atomic_write_parquet(perf_games, COMPAT_PERF_GAMES)
        atomic_write_parquet(perf_calib, COMPAT_PERF_CALIB)
        atomic_write_parquet(perf_spread, COMPAT_PERF_SPREAD)

        # Also write the v30-style *core/* names you hardcoded earlier (so nothing breaks)
        (DATADIR / "core").mkdir(parents=True, exist_ok=True)
        compat_teams_v30 = build_compat_teams_v30_from_v40(teams_v40=teams, games_v40_public=public)
        compat_games_v30 = build_compat_games_v30_from_v40(games_v40_public=public)
        atomic_write_parquet(compat_teams_v30, DATADIR / "core" / "teamsteamseasoncorev30.parquet")
        atomic_write_parquet(compat_games_v30, DATADIR / "core" / "gamesgamecorev30.parquet")

    # Final audits: re-read and enforce separation
    print("6) Final separation audit")
    reread_games_facts = pd.read_parquet(GAMES_FACTS_V40)
    reread_pred = pd.read_parquet(PRED_CURRENT_V40)
    reread_public = pd.read_parquet(PUBLIC_GAMES_V40)

    assert_no_banned_facts_cols(reread_games_facts, "reread games_facts_v40")
    validate_predictions(reread_games_facts, reread_pred)

    # Hard guardrail: keyset must match exactly by GameID
    g_ids = set(clean_gameids(reread_games_facts["GameID"]).dropna().unique().tolist())
    p_ids = set(clean_gameids(reread_pred["GameID"]).dropna().unique().tolist())
    if g_ids != p_ids:
        raise RuntimeError(
            f"Final audit GameID mismatch: facts={len(g_ids)} preds={len(p_ids)} overlap={len(g_ids.intersection(p_ids))}"
        )

    # Public is allowed to contain preds, but must still have exact keyset
    assert_unique_key(reread_public, "GameID", "public_v40")
    ids_facts = set(clean_gameids(reread_games_facts["GameID"]).unique().tolist())
    ids_public = set(clean_gameids(reread_public["GameID"]).unique().tolist())
    if ids_facts != ids_public:
        raise RuntimeError(f"Public bundle GameID mismatch vs facts: facts={len(ids_facts)} public={len(ids_public)}")

    print(f"Wrote v40 facts:   {TEAMS_V40}, {GAMES_FACTS_V40}")
    print(f"Wrote v40 preds:   {PRED_CURRENT_V40}")
    print(f"Wrote v40 public:  {PUBLIC_GAMES_V40}")
    print(f"Wrote v40 calib:   {PERF_SUMMARY_V40}, {PERF_GAMES_V40}, {PERF_CALIB_V40}, {PERF_SPREAD_V40}")
    print(f"Wrote v40 report:  {NIGHTLY_REPORT_V40}")
    print("NIGHTLY V40 SUCCESS")


if __name__ == "__main__":
    main()
