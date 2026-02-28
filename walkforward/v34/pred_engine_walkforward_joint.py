from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timezone
import math

import numpy as np
import pandas as pd

try:
    from sklearn.linear_model import Ridge
    SKLEARN_OK = True
except Exception:
    Ridge = None
    SKLEARN_OK = False

ENGINEVERSION = "JOINT_RIDGE_20260216_03_MARGINCAL_V1"

ROOT = Path(r"C:\ANALYTICS207")
GAMESPATH   = ROOT / "data" / "core"        / "games_game_core_v50.parquet"
OUTPATH     = ROOT / "data" / "predictions" / "games_predictions_current.parquet"
PIR_OUTPATH = ROOT / "data" / "core"        / "teams_power_index_v50.parquet"
SIM_OUTPATH = ROOT / "data" / "core"        / "tournament_sim_v50.parquet"

GENDER_COL       = "Gender"
GIRLSTOTALBIAS   = 26.278252430827177

MARGIN_CAL_A     = -8.404158261785373
MARGIN_CAL_B     =  3.110015243682007
MARGIN_CAL_CLAMP = 40.0

TIER_COUNTS = {"lo": 0, "mid": 0, "hi": 0}


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def clean_str(x: object) -> str:
    return str(x).strip()


def norm_cdf(z: float) -> float:
    z = float(z)
    return float(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))))


def build_team_index(teams: List[str]) -> Dict[str, int]:
    uniq = sorted({clean_str(t) for t in teams if clean_str(t) != ""})
    return {t: i for i, t in enumerate(uniq)}


def fit_joint_ridge(gdf: pd.DataFrame, alpha: float = 15.0) -> dict:
    if not SKLEARN_OK or Ridge is None:
        raise RuntimeError("sklearn is required for joint ridge engine")

    teams = pd.unique(pd.concat([gdf["HomeKey"], gdf["AwayKey"]], ignore_index=True)).tolist()
    tidx  = build_team_index(teams)
    n     = len(tidx)

    played     = gdf["Played"].to_numpy(dtype=bool)
    home       = gdf.loc[played, "HomeKey"].tolist()
    away       = gdf.loc[played, "AwayKey"].tolist()
    is_neutral = gdf.loc[played, "IsNeutral"].to_numpy(dtype=bool)
    y_home     = gdf.loc[played, "HomeScore"].to_numpy(dtype=float)
    y_away     = gdf.loc[played, "AwayScore"].to_numpy(dtype=float)

    p  = 2 * n + 1
    Xh = np.zeros((len(home), p), dtype=float)
    Xa = np.zeros((len(home), p), dtype=float)

    for i, (ht, at, neu) in enumerate(zip(home, away, is_neutral)):
        hi = tidx[ht]; ai = tidx[at]
        Xh[i, hi]      = 1.0
        Xh[i, n + ai]  = 1.0
        Xh[i, 2 * n]   = 0.0 if neu else 1.0
        Xa[i, ai]      = 1.0
        Xa[i, n + hi]  = 1.0
        Xa[i, 2 * n]   = 0.0

    reg_h = Ridge(alpha=float(alpha), fit_intercept=True, random_state=7)
    reg_a = Ridge(alpha=float(alpha), fit_intercept=True, random_state=7)
    reg_h.fit(Xh, y_home)
    reg_a.fit(Xa, y_away)

    pred_home    = reg_h.predict(Xh)
    pred_away    = reg_a.predict(Xa)
    resid_margin = (y_home - y_away) - (pred_home - pred_away)
    sigma_m      = float(np.std(resid_margin, ddof=1)) if len(resid_margin) >= 20 else 12.0
    sigma_m      = max(6.0, sigma_m)
    print("FIT sigma_m", sigma_m, "n_resid", len(resid_margin))

    return {"tidx": tidx, "n": n, "reg_h": reg_h, "reg_a": reg_a, "sigma_m": sigma_m}


def predict_game(model: dict, home: str, away: str, is_neutral: bool) -> Tuple[float, float, float, float, float]:
    tidx: Dict[str, int] = model["tidx"]
    n:    int             = model["n"]
    reg_h                 = model["reg_h"]
    reg_a                 = model["reg_a"]
    sigma_m: float        = float(model["sigma_m"])

    p  = 2 * n + 1
    Xh = np.zeros((1, p), dtype=float)
    Xa = np.zeros((1, p), dtype=float)

    ht = clean_str(home); at = clean_str(away)
    hi = tidx.get(ht, None)
    ai = tidx.get(at, None)

    if hi is not None:
        Xh[0, hi]     = 1.0
        Xa[0, n + hi] = 1.0
    if ai is not None:
        Xh[0, n + ai] = 1.0
        Xa[0, ai]     = 1.0

    Xh[0, 2 * n] = 0.0 if bool(is_neutral) else 1.0

    ph = float(reg_h.predict(Xh)[0])
    pa = float(reg_a.predict(Xa)[0])
    ph = clamp(ph, 35.0, 95.0)
    pa = clamp(pa, 30.0, 95.0)

    pm_raw = float(ph) - float(pa)
    pt     = float(ph + pa)

    Z1 = 0.50; Z2 = 0.90
    SIGMA_MULT_LO  = 0.70
    SIGMA_MULT_MID = 0.54
    SIGMA_MULT_HI  = 0.35

    z = pm_raw / max(1e-6, sigma_m)
    if abs(z) >= Z2:
        sigma_mult = SIGMA_MULT_HI;  TIER_COUNTS["hi"]  += 1
    elif abs(z) >= Z1:
        sigma_mult = SIGMA_MULT_MID; TIER_COUNTS["mid"] += 1
    else:
        sigma_mult = SIGMA_MULT_LO;  TIER_COUNTS["lo"]  += 1

    p_home = norm_cdf(pm_raw / max(1e-6, sigma_m * sigma_mult))
    p_home = clamp(p_home, 1e-6, 1.0 - 1e-6)

    pm = MARGIN_CAL_A + MARGIN_CAL_B * pm_raw
    pm = clamp(pm, -MARGIN_CAL_CLAMP, MARGIN_CAL_CLAMP)
    ph = 0.5 * (pt + pm)
    pa = 0.5 * (pt - pm)

    return float(ph), float(pa), float(pm), float(pt), float(p_home)


def build_power_index_from_model(
    games: pd.DataFrame,
    model: dict | None,
    gender: str,
) -> pd.DataFrame:
    if model is None:
        return pd.DataFrame(columns=[
            "TeamKey", "Gender", "OffRating_Ridge",
            "DefRating_Ridge", "PowerIndex_Ridge", "PowerIndex_Display",
        ])

    tidx: Dict[str, int] = model["tidx"]
    n:    int             = model["n"]
    reg_h                 = model["reg_h"]
    reg_a                 = model["reg_a"]
    coef_h = reg_h.coef_.reshape(-1)
    coef_a = reg_a.coef_.reshape(-1)

    off = {}; deff = {}
    for team, idx in tidx.items():
        off[team]  = float(0.5 * (coef_h[idx]     + coef_a[idx]))
        deff[team] = float(0.5 * (coef_h[n + idx] + coef_a[n + idx]))

    gdf = games.loc[games[GENDER_COL].astype(str).str.strip().str.title() == gender].copy()
    if "HomeKey" not in gdf.columns or "AwayKey" not in gdf.columns:
        return pd.DataFrame(columns=[
            "TeamKey", "Gender", "OffRating_Ridge",
            "DefRating_Ridge", "PowerIndex_Ridge", "PowerIndex_Display",
        ])

    team_keys = pd.unique(
        pd.concat([gdf["HomeKey"].astype(str), gdf["AwayKey"].astype(str)], ignore_index=True)
    )
    base = pd.DataFrame({"TeamKey": team_keys})
    base["TeamKey"]          = base["TeamKey"].astype(str).str.strip()
    base["Gender"]           = gender
    base["OffRating_Ridge"]  = base["TeamKey"].map(off).astype(float)
    base["DefRating_Ridge"]  = base["TeamKey"].map(deff).astype(float)
    base["PowerIndex_Ridge"] = base["OffRating_Ridge"] - base["DefRating_Ridge"]

    mu    = base["PowerIndex_Ridge"].mean()
    sigma = base["PowerIndex_Ridge"].std(ddof=0)
    if sigma == 0 or np.isnan(sigma):
        base["PowerIndex_Display"] = 50.0
    else:
        z = (base["PowerIndex_Ridge"] - mu) / sigma
        base["PowerIndex_Display"] = 50.0 + 12.0 * z

    return base[[
        "TeamKey", "Gender", "OffRating_Ridge",
        "DefRating_Ridge", "PowerIndex_Ridge", "PowerIndex_Display",
    ]]


def build_bracket_sim(games: pd.DataFrame, n_sims: int = 10_000) -> pd.DataFrame:

    def h2h_prob(pi_a: float, pi_b: float) -> float:
        return 1.0 / (1.0 + np.exp(-0.07 * (pi_a - pi_b)))

    def simulate_bracket(seeds_keys: list, pi_map: dict, n: int) -> dict:
        champ_counts = {k: 0 for k in seeds_keys}
        for _ in range(n):
            alive = list(seeds_keys)
            while len(alive) > 1:
                next_round = []
                if len(alive) % 2 == 1:
                    next_round.append(alive[0])
                    alive = alive[1:]
                for i in range(0, len(alive) - 1, 2):
                    a, b   = alive[i], alive[i + 1]
                    p_a    = h2h_prob(pi_map[a], pi_map[b])
                    winner = a if np.random.random() < p_a else b
                    next_round.append(winner)
                alive = next_round
            if alive:
                champ_counts[alive[0]] += 1
        return champ_counts

    # ── Build team PI / Rank lookup ──────────────────
    home_pi = games[["HomeKey", "HomeClass", "HomeRegion", GENDER_COL, "HomePI"]].rename(
        columns={"HomeKey": "TeamKey", "HomeClass": "Class", "HomeRegion": "Region",
                 GENDER_COL: "Gender", "HomePI": "PI"})
    away_pi = games[["AwayKey", "AwayClass", "AwayRegion", GENDER_COL, "AwayPI"]].rename(
        columns={"AwayKey": "TeamKey", "AwayClass": "Class", "AwayRegion": "Region",
                 GENDER_COL: "Gender", "AwayPI": "PI"})
    team_pi = pd.concat([home_pi, away_pi], ignore_index=True)
    team_pi["PI"] = pd.to_numeric(team_pi["PI"], errors="coerce")

    home_rank = games[["HomeKey", GENDER_COL, "HomeRank"]].rename(
        columns={"HomeKey": "TeamKey", GENDER_COL: "Gender", "HomeRank": "Rank"})
    away_rank = games[["AwayKey", GENDER_COL, "AwayRank"]].rename(
        columns={"AwayKey": "TeamKey", GENDER_COL: "Gender", "AwayRank": "Rank"})
    team_rank = pd.concat([home_rank, away_rank], ignore_index=True)
    team_rank["Rank"] = pd.to_numeric(team_rank["Rank"], errors="coerce")

    team_pi_agg = (
        team_pi.dropna(subset=["PI"])
        .sort_values("PI")
        .groupby(["TeamKey", "Gender", "Class", "Region"], dropna=True)
        .agg(PI=("PI", "last"))
        .reset_index()
    )
    team_rank_agg = (
        team_rank.dropna(subset=["Rank"])
        .groupby(["TeamKey", "Gender"], dropna=True)
        .agg(Rank=("Rank", "last"))
        .reset_index()
    )

    ta        = team_pi_agg.merge(team_rank_agg, on=["TeamKey", "Gender"], how="left")
    qualified = ta[ta["Rank"].notna() & (ta["Rank"] <= 16) & ta["PI"].notna()].copy()

    if qualified.empty:
        print("   BracketSim: no qualified teams found, skipping.")
        return pd.DataFrame()

    # ── Stage 1: Regional championship odds ──────────
    all_rows = []
    for (gender, cls, region), grp in qualified.groupby(["Gender", "Class", "Region"], dropna=True):
        grp = grp.copy()
        grp["Seed"] = grp["Rank"].apply(lambda r: int(round(r)))
        grp = grp.sort_values("Seed").reset_index(drop=True)
        if len(grp) < 2:
            continue

        pi_map       = dict(zip(grp["TeamKey"], grp["PI"]))
        seeds_keys   = grp["TeamKey"].tolist()
        champ_counts = simulate_bracket(seeds_keys, pi_map, n_sims)

        for _, row in grp.iterrows():
            tk   = row["TeamKey"]
            wins = champ_counts.get(tk, 0)
            all_rows.append({
                "TeamKey":         tk,
                "Gender":          gender,
                "Class":           cls,
                "Region":          region,
                "ProjectedSeed":   int(row["Seed"]),
                "PI":              float(row["PI"]),
                "SimChampWins":    wins,
                "NSims":           n_sims,
                "RegionalChampPct": round(100.0 * wins / n_sims, 2),
                "BuiltAtUTC":      datetime.now(timezone.utc).isoformat(),
            })

    df = pd.DataFrame(all_rows)
    if df.empty:
        print("   BracketSim: no rows produced.")
        return df

    # ── Stage 2: State (Gold Ball) championship odds ──
    # For each team: StateChampPct = sum over all opponents in other region of
    #   P(team wins regional) × P(opponent wins their regional) × P(team beats opponent)
    state_rows = []
    for (gender, cls), grp in df.groupby(["Gender", "Class"]):
        north = grp[grp["Region"] == "North"].copy()
        south = grp[grp["Region"] == "South"].copy()
        if north.empty or south.empty:
            # Only one region — state prob = regional prob
            for _, row in grp.iterrows():
                state_rows.append({
                    "TeamKey":       row["TeamKey"],
                    "Gender":        gender,
                    "Class":         cls,
                    "StateChampPct": round(row["RegionalChampPct"], 2),
                })
            continue

        for _, nr in north.iterrows():
            p_n_regional = nr["RegionalChampPct"] / 100.0
            state_prob   = 0.0
            for _, sr in south.iterrows():
                p_s_regional = sr["RegionalChampPct"] / 100.0
                p_n_beats_s  = h2h_prob(float(nr["PI"]), float(sr["PI"]))
                state_prob  += p_n_regional * p_s_regional * p_n_beats_s
            state_rows.append({
                "TeamKey":       nr["TeamKey"],
                "Gender":        gender,
                "Class":         cls,
                "StateChampPct": round(state_prob * 100.0, 2),
            })

        for _, sr in south.iterrows():
            p_s_regional = sr["RegionalChampPct"] / 100.0
            state_prob   = 0.0
            for _, nr in north.iterrows():
                p_n_regional = nr["RegionalChampPct"] / 100.0
                p_s_beats_n  = 1.0 - h2h_prob(float(nr["PI"]), float(sr["PI"]))
                state_prob  += p_s_regional * p_n_regional * p_s_beats_n
            state_rows.append({
                "TeamKey":       sr["TeamKey"],
                "Gender":        gender,
                "Class":         cls,
                "StateChampPct": round(state_prob * 100.0, 2),
            })

    state_df = pd.DataFrame(state_rows)
    df = df.merge(state_df, on=["TeamKey", "Gender", "Class"], how="left")
    df["StateChampPct"] = df["StateChampPct"].fillna(0.0)

    df = df.sort_values(
        ["Gender", "Class", "Region", "ProjectedSeed"]
    ).reset_index(drop=True)

    SIM_OUTPATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SIM_OUTPATH, index=False)
    print(f"   BracketSim: {len(df)} team-rows  →  {SIM_OUTPATH}")
    print(f"   Columns: {df.columns.tolist()}")
    return df


def main() -> None:
    if not GAMESPATH.exists():
        raise FileNotFoundError(f"Missing GAMESPATH: {GAMESPATH}")

    games = pd.read_parquet(GAMESPATH).copy()

    if "Date" in games.columns:
        games["Date"] = pd.to_datetime(games["Date"], errors="coerce")
        games = games.sort_values("Date").reset_index(drop=True)

    required = ["GameID", "HomeKey", "AwayKey", "IsNeutral", GENDER_COL, "HomeScore", "AwayScore", "Played"]
    for c in required:
        if c not in games.columns:
            raise RuntimeError(f"games file missing required column: {c}")

    games["GameID"]      = games["GameID"].astype(str).str.strip()
    games["HomeKey"]     = games["HomeKey"].astype(str).str.strip()
    games["AwayKey"]     = games["AwayKey"].astype(str).str.strip()
    games[GENDER_COL]    = games[GENDER_COL].astype(str).str.strip().str.title()
    games["HomeScore"]   = pd.to_numeric(games["HomeScore"], errors="coerce")
    games["AwayScore"]   = pd.to_numeric(games["AwayScore"], errors="coerce")
    games["Played"]      = games["Played"].fillna(False).astype(bool)

    build_id  = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    boys_df   = games.loc[games[GENDER_COL] == "Boys"].copy()
    girls_df  = games.loc[games[GENDER_COL] == "Girls"].copy()

    boys_model  = fit_joint_ridge(boys_df,  alpha=15.0) if len(boys_df)  else None
    girls_model = fit_joint_ridge(girls_df, alpha=15.0) if len(girls_df) else None

    try:
        pir_boys  = build_power_index_from_model(games, boys_model,  gender="Boys")
        pir_girls = build_power_index_from_model(games, girls_model, gender="Girls")
        pir_all   = pd.concat([pir_boys, pir_girls], ignore_index=True)
        pir_all["EngineVersion"] = ENGINEVERSION
        pir_all["BuiltAtUTC"]    = datetime.now(timezone.utc).isoformat()
        PIR_OUTPATH.parent.mkdir(parents=True, exist_ok=True)
        pir_all.to_parquet(PIR_OUTPATH, index=False)
        print(f"Wrote PIR table with {len(pir_all)} teams to {PIR_OUTPATH}")
    except Exception as e:
        print(f"[WARN] PIR build failed: {e}")

    CLASS_ORDER = {"S": 1, "D": 2, "C": 3, "B": 4, "A": 5}
    rows: List[dict] = []

    for _, g in games.iterrows():
        gid        = clean_str(g["GameID"])
        home       = clean_str(g["HomeKey"])
        away       = clean_str(g["AwayKey"])
        is_neutral = bool(g.get("IsNeutral", False))
        gender     = clean_str(g.get(GENDER_COL, "")).title()

        model = girls_model if gender == "Girls" else boys_model

        if model is None:
            ph, pa, pm, pt, p_home = 48.0, 45.0, 3.0, 93.0, 0.55
        else:
            ph, pa, pm, pt, p_home = predict_game(model, home, away, is_neutral)

        try:
            home_cls  = CLASS_ORDER.get(str(g.get("HomeClass", "")).strip().upper(), 3)
            away_cls  = CLASS_ORDER.get(str(g.get("AwayClass", "")).strip().upper(), 3)
            class_gap = home_cls - away_cls
            if abs(class_gap) >= 2 and abs(pm) >= 15:
                boost = min(0.06 * abs(class_gap), 0.18)
                if class_gap > 0 and p_home > 0.5:
                    p_home = clamp(p_home + boost, 0.0001, 0.9999)
                elif class_gap < 0 and p_home < 0.5:
                    p_home = clamp(p_home - boost, 0.0001, 0.9999)
        except Exception:
            pass

        home_ti = pd.to_numeric(g.get("HomeTI", pd.NA), errors="coerce")
        away_ti = pd.to_numeric(g.get("AwayTI", pd.NA), errors="coerce")
        home_pi = pd.to_numeric(g.get("HomePI", pd.NA), errors="coerce")
        away_pi = pd.to_numeric(g.get("AwayPI", pd.NA), errors="coerce")

        if pd.notna(home_ti) and pd.notna(away_ti):
            strength_gap = float(home_ti - away_ti)
        elif pd.notna(home_pi) and pd.notna(away_pi):
            strength_gap = float(home_pi - away_pi)
        else:
            strength_gap = 0.0

        if gender == "Girls":
            pt = float(pt) - float(GIRLSTOTALBIAS)
            ph = 0.5 * (pt + pm)
            pa = 0.5 * (pt - pm)
            ph = clamp(ph, 35.0, 95.0)
            pa = clamp(pa, 30.0, 95.0)
            pt = float(ph + pa)
            pm = float(ph - pa)

        pred_home_wins   = bool(p_home >= 0.5)
        pred_winner_key  = home if pred_home_wins else away
        pred_loser_key   = away if pred_home_wins else home
        pred_winner_prob = float(p_home) if pred_home_wins else float(1.0 - p_home)

        if bool(g["Played"]):
            y_home = 1 if float(g["HomeScore"] - g["AwayScore"]) > 0 else 0
            result_home_win = int(y_home)
        else:
            result_home_win = pd.NA

        rows.append({
            "GameID":                  gid,
            "HomeKey":                 home,
            "AwayKey":                 away,
            "PredHomeWinProb":         float(p_home),
            "PredHomeScore":           float(ph),
            "PredAwayScore":           float(pa),
            "PredMargin":              float(pm),
            "PredTotalPoints":         float(pt),
            "PredWinnerKey":           pred_winner_key,
            "PredLoserKey":            pred_loser_key,
            "PredWinnerProb":          float(pred_winner_prob),
            "PredWinnerProbPct":       float(100.0 * pred_winner_prob),
            "PredSpreadAbs":           float(abs(pm)),
            "CoreVersion":             ENGINEVERSION,
            "PredBuildID":             build_id,
            "EloDiff":                 0.0,
            "StrengthGap":             float(strength_gap),
            "BlowoutMode":             False,
            "SecondMeeting":           False,
            "FirstMeetingWasBlowout":  False,
            "ResultHomeWin":           result_home_win,
        })

    out = pd.DataFrame(rows)

    for c in [
        "PredHomeWinProb", "PredHomeScore", "PredAwayScore",
        "PredMargin", "PredTotalPoints", "PredWinnerProb",
        "PredWinnerProbPct", "PredSpreadAbs", "EloDiff", "StrengthGap",
    ]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out.drop_duplicates(subset="GameID", keep="first").reset_index(drop=True)
    if len(out) != len(games):
        raise RuntimeError(f"Joint engine wrote {len(out)} rows but games has {len(games)} rows")

    OUTPATH.parent.mkdir(parents=True, exist_ok=True)
    print("TIER_COUNTS", TIER_COUNTS)
    out.to_parquet(OUTPATH, index=False)
    print(f"Wrote {len(out)} rows to {OUTPATH}")

    try:
        build_bracket_sim(games, n_sims=10_000)
    except Exception as e:
        print(f"[WARN] BracketSim failed: {e}")


if __name__ == "__main__":
    main()
