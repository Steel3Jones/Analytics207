from __future__ import annotations


# ======================================================================================
# NIGHTLY V40 (NO CORE_V30)
# - Single truth: facts cores are facts-only
# - Predictions are separate: predictions parquet is preds-only
# - Public bundle is the ONLY merged artifact (facts + preds + grading)
# - Heavy guardrails: schema contract, separation audits, keyset checks, stats report
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
import os

# ----------------- Imports & Constants ------------------------------------------------


ROOT = Path(r"C:\ANALYTICS207")
DATADIR = ROOT / "data"

# Make project imports work when running as: py nightly\nightly_v40.py
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
GAMES_ANALYTICS_V40 = CORE_DIR / "games_analytics_v40.parquet"
TEAMS_ANALYTICS_V40 = CORE_DIR / "teams_team_season_analytics_v40.parquet"

def season_from_date(dt: pd.Timestamp) -> str | None:
    if pd.isna(dt):
        return None
    y = dt.year
    if dt.month >= 7:
        return f"{y}-{str(y + 1)[-2:]}"
    else:
        return f"{y - 1}-{str(y)[-2:]}"


# Prediction engine script (should write  OR we copy into it)
PRED_ENGINE_SCRIPT = ROOT / "walkforward" / "v34" / "pred_engine_walkforward_joint.py"


# Version strings
CORE_VERSION_V40 = "v40"

PRED_COLS = ["PredHomeWinProb", "PredMargin", "PredHomeScore", "PredAwayScore", "PredTotalPoints"]
PRED_DERIVED_COLS = ["PredWinnerKey", "PredWinnerProb", "PredWinnerProbPct", "PredSpreadAbs"]
PRED_META_COLS = ["CoreVersion", "PredBuildID"]

PRED_ALL_COLS = ["GameID", "HomeKey", "AwayKey"] + PRED_META_COLS + PRED_COLS + PRED_DERIVED_COLS

# Facts-only: must not contain any of these
BANNED_FACTS_COLS = set(
    PRED_COLS
    + PRED_DERIVED_COLS
    + ["FavProb", "FavProbPct", "FavoriteIsHome", "FavoriteTeamKey", "ModelCorrect"]
)

# Schema contract file
SCHEMA_CONTRACT_PATH = CAL_DIR / "v40_schema_contract.json"

#---------------------------HELPER-----------------------------------------






#---------------------------End HELPER---------------------
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
# Schema contract helpers (STRICT mode)
# --------------------------------------------------------------------------------------


def load_schema_contract(path: Path) -> dict[str, list[str]] | None:
    if not path.exists():
        return None
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"Schema contract at {path} is not a JSON object")
    out: dict[str, list[str]] = {}
    for k, v in obj.items():
        if not isinstance(k, str) or not isinstance(v, list):
            raise RuntimeError(f"Schema contract malformed at key {k}")
        out[k] = [str(x) for x in v]
    return out


def save_schema_contract(path: Path, schemas: dict[str, list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: [str(c) for c in cols] for k, cols in schemas.items()}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def enforce_schema_contract_strict(df: pd.DataFrame, expected_cols: list[str], name: str) -> pd.DataFrame:
    actual_cols = [str(c) for c in df.columns.tolist()]
    expected_set = set(expected_cols)
    actual_set = set(actual_cols)

    missing = [c for c in expected_cols if c not in actual_set]
    extra = [c for c in actual_cols if c not in expected_set]

    if missing or extra:
        msg = [f"SCHEMA CONTRACT VIOLATION: {name}"]
        if missing:
            msg.append(f"  Missing columns ({len(missing)}): {missing}")
        if extra:
            msg.append(f"  Extra columns ({len(extra)}): {extra}")
        msg.append("  Fix: run with --freeze-schema (intentional change) or remove the offending columns.")
        raise RuntimeError("\n".join(msg))

    # Strict: exact columns, exact order
    return df.reindex(columns=expected_cols)


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


def require_non_null(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing_cols = [c for c in cols if c not in df.columns]
    if missing_cols:
        raise RuntimeError(f"{name} missing required columns: {missing_cols}")
    bad = [c for c in cols if df[c].isna().any()]
    if bad:
        raise RuntimeError(f"{name} has nulls in required columns: {bad}")


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

# Engine is expected to write to PRED_CURRENT_V40 (v40 canonical path).
    if not PRED_CURRENT_V40.exists():
        raise RuntimeError(f"Engine did not write expected preds file: {PRED_CURRENT_V40}")



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

    if "Date" in g.columns:
        g["Date"] = pd.to_datetime(g["Date"], errors="coerce")
        g["Season"] = g["Date"].apply(season_from_date)
    else:
        g["Season"] = pd.Series([None] * len(g), dtype=object)


    if "HomeTeam" not in g.columns or "AwayTeam" not in g.columns:
        raise RuntimeError("truth.csv must include HomeTeam and AwayTeam columns")
    g["Home"] = g["HomeTeam"].astype(str).str.strip()
    g["Away"] = g["AwayTeam"].astype(str).str.strip()

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

    if "Gender" not in g.columns:
        g["Gender"] = None

    g["HomeKey"] = g.apply(lambda r: build_team_key(r["Home"], r.get("Gender", ""), r["HomeClass"], r["HomeRegion"]), axis=1)
    g["AwayKey"] = g.apply(lambda r: build_team_key(r["Away"], r.get("Gender", ""), r["AwayClass"], r["AwayRegion"]), axis=1)

    g["HomeScore"] = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
    g["AwayScore"] = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
    g["Played"] = g["HomeScore"].notna() & g["AwayScore"].notna()
    g["Margin"] = np.where(g["Played"], g["HomeScore"] - g["AwayScore"], np.nan)

    g["WinnerTeam"] = np.where(
        g["Played"] & (g["HomeScore"] > g["AwayScore"]),
        g["Home"],
        np.where(g["Played"] & (g["AwayScore"] > g["HomeScore"]), g["Away"], None),
    )

    neutral = coalesce_bool_series(g, ["NeutralSite", "Neutral", "IsNeutral", "NeutralFlag"])
    if neutral is None:
        if "Site" in g.columns:
            neutral = g["Site"].astype(str).str.lower().str.contains("neutral", na=False)
        elif "LocationType" in g.columns:
            neutral = g["LocationType"].astype(str).str.lower().eq("neutral")
        else:
            neutral = pd.Series([False] * len(g), dtype=bool)
    g["IsNeutral"] = neutral

    if "GameID" not in g.columns:
        raise RuntimeError("truth.csv must include GameID column")

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
    out["GameID"] = clean_gameids(out["GameID"])

    assert_unique_key(out, "GameID", "games_facts_v40")
    assert_no_banned_facts_cols(out, "games_facts_v40")
    require_non_null(out, ["GameID", "Home", "Away", "HomeKey", "AwayKey", "Season", "CoreVersion"], "games_facts_v40")

    return out


def build_teams_facts_v40(games_facts: pd.DataFrame) -> pd.DataFrame:
    g = games_facts.copy()
    if "Played" not in g.columns:
        g["Played"] = False

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

    long["Class"] = np.where(
        long["IsHome"],
        long.get("HomeClass", None),
        long.get("AwayClass", None),
    )
    long["Region"] = np.where(
        long["IsHome"],
        long.get("HomeRegion", None),
        long.get("AwayRegion", None),
    )

    # Map existing game-level TI/PI onto each team row
    long["TeamTI"] = np.where(
        long["IsHome"],
        pd.to_numeric(long.get("HomeTI"), errors="coerce"),
        pd.to_numeric(long.get("AwayTI"), errors="coerce"),
    )
    long["TeamPI"] = np.where(
        long["IsHome"],
        pd.to_numeric(long.get("HomePI"), errors="coerce"),
        pd.to_numeric(long.get("AwayPI"), errors="coerce"),
    )

    longp = long[long["Played"].fillna(False)].copy()
    longp["Margin"] = (
        pd.to_numeric(longp["For"], errors="coerce")
        - pd.to_numeric(longp["Against"], errors="coerce")
    )

    def agg_team(sub: pd.DataFrame) -> pd.Series:
        games = int(len(sub))
        wins = int((sub["Margin"] > 0).sum())
        losses = int((sub["Margin"] < 0).sum())
        ties = int((sub["Margin"] == 0).sum())
        pts_for = float(pd.to_numeric(sub["For"], errors="coerce").fillna(0).sum())
        pts_against = float(pd.to_numeric(sub["Against"], errors="coerce").fillna(0).sum())
        ppg = float(pts_for / games) if games else np.nan
        oppg = float(pts_against / games) if games else np.nan
        marginpg = float(sub["Margin"].mean()) if games else np.nan
        winpct = float(wins / games) if games else np.nan

        # Canonical Class/Region: most frequent non-null values in this team
        cls = (
            sub["Class"].dropna().mode().iloc[0]
            if "Class" in sub.columns and sub["Class"].notna().any()
            else np.nan
        )
        reg = (
            sub["Region"].dropna().mode().iloc[0]
            if "Region" in sub.columns and sub["Region"].notna().any()
            else np.nan
        )

        # Carry through existing TI/PI from MPA (no recompute)
        ti = pd.to_numeric(sub.get("TeamTI"), errors="coerce")
        pi = pd.to_numeric(sub.get("TeamPI"), errors="coerce")
        team_ti = ti.dropna().iloc[-1] if ti.notna().any() else np.nan
        team_pi = pi.dropna().iloc[-1] if pi.notna().any() else np.nan

        return pd.Series(
            {
                "Class": cls,
                "Region": reg,
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
                "TI": team_ti,
                "PI": team_pi,
            }
        )

    # ONE row per TeamKey/Season/Gender (Class/Region are derived inside agg_team)
    group_cols = [c for c in ["TeamKey", "Team", "Season", "Gender"] if c in longp.columns]
    teams = (
        longp.groupby(group_cols, dropna=False)
        .apply(agg_team, include_groups=False)
        .reset_index()
    )

    if teams.empty:
        long0 = long.copy()
        group_cols0 = [c for c in ["TeamKey", "Team", "Season", "Gender"] if c in long0.columns]
        base = (
            long0.dropna(subset=["TeamKey"])
            .drop_duplicates(subset=group_cols0)[group_cols0]
            .copy()
        )
        for c in [
            "Class",
            "Region",
            "Games",
            "Wins",
            "Losses",
            "Ties",
            "WinPct",
            "PointsFor",
            "PointsAgainst",
            "PPG",
            "OPPG",
            "MarginPG",
            "OffEff",
            "DefEff",
            "NetEff",
            "TI",
            "PI",
        ]:
            base[c] = np.nan
        base["Record"] = "0-0-0"
        teams = base

    teams["CoreVersion"] = CORE_VERSION_V40
    if "TeamKey" in teams.columns:
        teams["TeamKey"] = teams["TeamKey"].astype(str).str.strip()
        dups = int(teams.duplicated(subset=["TeamKey", "Season", "Gender"]).sum())
        if dups:
            raise RuntimeError(
                f"teams_core_v40 has duplicate TeamKey+Season+Gender (count={dups})"
            )

    assert_no_banned_facts_cols(teams, "teams_core_v40")
    require_non_null(
        teams,
        ["TeamKey", "Team", "Season", "Gender", "CoreVersion"],
        "teams_core_v40",
    )
    return teams


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
        mae = float(
            (pd.to_numeric(pub_played["PredMargin"], errors="coerce")
             - pd.to_numeric(pub_played["ActualMargin"], errors="coerce")).abs().mean()
        )
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
# Merge + grading (public bundle only)
# --------------------------------------------------------------------------------------


def merge_predictions(games_facts: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    g = games_facts.copy()
    p = pred.copy()

    g["GameID"] = clean_gameids(g["GameID"])
    p["GameID"] = clean_gameids(p["GameID"])

    keep = [c for c in PRED_ALL_COLS if c in p.columns]
    p2 = p[keep].drop_duplicates(subset="GameID", keep="first").copy()

    out = g.merge(p2, on=["GameID"], how="left", suffixes=("", "_pred"))

    missing_pm = int(pd.to_numeric(out["PredMargin"], errors="coerce").isna().sum())
    missing_wp = int(pd.to_numeric(out["PredHomeWinProb"], errors="coerce").isna().sum())
    if missing_pm or missing_wp:
        raise RuntimeError(f"After merge missing PredMargin={missing_pm}, PredHomeWinProb={missing_wp}")

    if "HomeKey_pred" in out.columns and "AwayKey_pred" in out.columns:
        bad_home = (out["HomeKey"].astype(str).str.strip() != out["HomeKey_pred"].astype(str).str.strip()).sum()
        bad_away = (out["AwayKey"].astype(str).str.strip() != out["AwayKey_pred"].astype(str).str.strip()).sum()
        print(f"KEY MISMATCH NOTE (non-fatal): bad_home={int(bad_home)} bad_away={int(bad_away)}")
        out = out.drop(columns=[c for c in ["HomeKey_pred", "AwayKey_pred"] if c in out.columns])

    return out


def add_grading_fields(games_plus: pd.DataFrame) -> pd.DataFrame:
    out = games_plus.copy()

    hs = pd.to_numeric(out.get("HomeScore", np.nan), errors="coerce")
    aS = pd.to_numeric(out.get("AwayScore", np.nan), errors="coerce")
    played = out.get("Played", False)
    played = played.fillna(False) if isinstance(played, pd.Series) else pd.Series([False] * len(out))

    out["ActualMargin"] = np.where(played, hs - aS, np.nan)

    phwp = pd.to_numeric(out["PredHomeWinProb"], errors="coerce")
    out["FavoriteIsHome"] = phwp >= 0.5

    out["FavProb"] = np.where(out["FavoriteIsHome"].fillna(False), phwp, 1.0 - phwp)

    pm = pd.to_numeric(out.get("PredMargin", np.nan), errors="coerce")
    am = pd.to_numeric(out.get("ActualMargin", np.nan), errors="coerce")

    out["ModelCorrect"] = np.where(
    played,
    (pm > 0) == (am > 0),
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
    assert_unique_key(out, "GameID", "public_v40")
    require_non_null(out, ["GameID", "Home", "Away", "HomeKey", "AwayKey", "Season", "CoreVersion"], "public_v40")
    return out


# --------------------------------------------------------------------------------------
# Performance / calibration (v40)
# --------------------------------------------------------------------------------------


def build_performance_tables_v40(games_public: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = games_public.copy()

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


def main() -> None:
    args = parse_args()

    print("NIGHTLY V40 START (NO CORE_V30)")

    for d in [CORE_DIR, PRED_DIR, CAL_DIR, PUB_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    if not TRUTH_PATH.exists():
        raise FileNotFoundError(f"Missing truth.csv at {TRUTH_PATH}")

    # 1) Build v40 facts cores (no predictions)
    print("1) Build v40 facts cores from truth.csv (no predictions)")
    truth = load_truth_csv(TRUTH_PATH)
    games_facts = build_games_facts_v40(truth)
    teams = build_teams_facts_v40(games_facts)

    assert_no_banned_facts_cols(games_facts, "games_facts_v40")
    assert_no_banned_facts_cols(teams, "teams_core_v40")

    atomic_write_parquet(teams, TEAMS_V40)
    atomic_write_parquet(games_facts, GAMES_FACTS_V40)

    # 1b) Build v40 game analytics (descriptive only)
    print("1b) Build v40 game analytics (descriptive only)")
    games_analytics = build_games_analytics_v40()
    atomic_write_parquet(games_analytics, GAMES_ANALYTICS_V40)

    # 2) Run prediction engine to generate predictions_current
    print("2) Run prediction engine to generate predictions_current")
    arch_dir = PRED_DIR / "archives"
    arch_dir.mkdir(parents=True, exist_ok=True)
    if PRED_CURRENT_V40.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        shutil.copy2(
            PRED_CURRENT_V40,
            arch_dir / f"games_predictions_current__before__{stamp}.parquet",
        )

    run_pred_engine()

    pred = pd.read_parquet(PRED_CURRENT_V40).copy()
    pred["GameID"] = clean_gameids(pred["GameID"])

    validate_predictions(games_facts, pred)
    validate_key_match(games_facts, pred)

    # 3) Build v40 public bundle (facts + preds + grading)
    print("3) Build v40 public bundle (facts + preds + grading)")
    games_plus = merge_predictions(games_facts, pred)
    games_plus = add_grading_fields(games_plus)
    public = build_public_bundle(games_plus)

    # 4) Build v40 performance/calibration outputs
    print("4) Build v40 performance/calibration outputs")
    perf_summary, perf_games, perf_calib, perf_spread = build_performance_tables_v40(public)
    report = build_nightly_report(games_facts, pred, public)

    # ---------------- Contract: create/enforce column sets ----------------
    outputs: dict[str, pd.DataFrame] = {
        "teams_v40": teams,
        "games_facts_v40": games_facts,
        "pred_current_v40": pred,
        "public_games_v40": public,
        "perf_summary_v40": perf_summary,
        "perf_games_v40": perf_games,
        "perf_calib_v40": perf_calib,
        "perf_spread_v40": perf_spread,
        "nightly_report_v40": report,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(
        "--freeze-schema",
        action="store_true",
        help="Overwrite v40_schema_contract.json using the schemas produced by this run.",
    )
    ap.add_argument(
        "--no-contract",
        action="store_true",
        help="Disable schema contract enforcement for this run (debug only).",
    )
    return ap.parse_args()




    if not args.no_contract:
        contract = load_schema_contract(SCHEMA_CONTRACT_PATH)
        if contract is None or args.freeze_schema:
            schemas = {k: list(df.columns) for k, df in outputs.items()}
            save_schema_contract(SCHEMA_CONTRACT_PATH, schemas)
            contract = schemas
            print(f"Schema contract saved: {SCHEMA_CONTRACT_PATH}")

        # Strict enforce: missing OR extra columns => fail; exact order enforced
        teams = enforce_schema_contract_strict(outputs["teams_v40"], contract["teams_v40"], "teams_v40")
        games_facts = enforce_schema_contract_strict(outputs["games_facts_v40"], contract["games_facts_v40"], "games_facts_v40")
        pred = enforce_schema_contract_strict(outputs["pred_current_v40"], contract["pred_current_v40"], "pred_current_v40")
        public = enforce_schema_contract_strict(outputs["public_games_v40"], contract["public_games_v40"], "public_games_v40")
        perf_summary = enforce_schema_contract_strict(outputs["perf_summary_v40"], contract["perf_summary_v40"], "perf_summary_v40")
        perf_games = enforce_schema_contract_strict(outputs["perf_games_v40"], contract["perf_games_v40"], "perf_games_v40")
        perf_calib = enforce_schema_contract_strict(outputs["perf_calib_v40"], contract["perf_calib_v40"], "perf_calib_v40")
        perf_spread = enforce_schema_contract_strict(outputs["perf_spread_v40"], contract["perf_spread_v40"], "perf_spread_v40")
        report = enforce_schema_contract_strict(outputs["nightly_report_v40"], contract["nightly_report_v40"], "nightly_report_v40")

    # ---------------- Writes (after enforcement) ----------------
    atomic_write_parquet(teams, TEAMS_V40)
    atomic_write_parquet(games_facts, GAMES_FACTS_V40)
    atomic_write_parquet(pred, PRED_CURRENT_V40)
    atomic_write_parquet(public, PUBLIC_GAMES_V40)

    atomic_write_parquet(perf_summary, PERF_SUMMARY_V40)
    atomic_write_parquet(perf_games, PERF_GAMES_V40)
    atomic_write_parquet(perf_calib, PERF_CALIB_V40)
    atomic_write_parquet(perf_spread, PERF_SPREAD_V40)
    atomic_write_parquet(report, NIGHTLY_REPORT_V40)

    print("6) Final separation audit")
    reread_games_facts = pd.read_parquet(GAMES_FACTS_V40)
    reread_pred = pd.read_parquet(PRED_CURRENT_V40)
    reread_public = pd.read_parquet(PUBLIC_GAMES_V40)

    assert_no_banned_facts_cols(reread_games_facts, "reread games_facts_v40")
    validate_predictions(reread_games_facts, reread_pred)

    g_ids = set(clean_gameids(reread_games_facts["GameID"]).dropna().unique().tolist())
    p_ids = set(clean_gameids(reread_pred["GameID"]).dropna().unique().tolist())
    if g_ids != p_ids:
        raise RuntimeError(
            f"Final audit GameID mismatch: facts={len(g_ids)} preds={len(p_ids)} overlap={len(g_ids.intersection(p_ids))}"
        )

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

