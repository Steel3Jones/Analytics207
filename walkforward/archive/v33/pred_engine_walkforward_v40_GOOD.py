from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timezone

import numpy as np
import pandas as pd


ENGINEVERSION = "v40_walkforward_prod_20260216_girls_totalcal1"
ROOT = Path(r"C:\ANALYTICS207")

GAMESPATH = ROOT / "data" / "core" / "games_game_core_v40.parquet"
OUTPATH = ROOT / "data" / "predictions" / "games_predictions_current.parquet"

# Girls totals were systematically high; subtract this from PredTotalPoints for Girls
GIRLS_TOTAL_BIAS = 26.278252430827177
GENDER_COL = "Gender"


class BlowoutConfig:
    def __init__(
        self,
        enabled: bool = True,
        min_games_each: int = 8,
        elo_diff_threshold: float = 180.0,
        strength_gap_threshold: float = 20.0,
        first_blowout_second_meeting_relief: float = 25.0,
    ) -> None:
        self.enabled = enabled
        self.min_games_each = min_games_each
        self.elo_diff_threshold = elo_diff_threshold
        self.strength_gap_threshold = strength_gap_threshold
        self.first_blowout_second_meeting_relief = first_blowout_second_meeting_relief


class ScoreConfig:
    def __init__(
        self,
        base_total: float = 95.0,
        home_adv: float = 2.5,
        total_shrink: float = 0.65,
        margin_scale: float = 0.304,
        margin_keep: float = 1.00,
        margin_divisor_normal: float = 1.0,
        blowout_margin_keep: float = 1.00,
        margin_divisor_blowout: float = 1.0,
        boost_start_elo: float = 190.0,
        boost_per_elo: float = 0.07,
        boost_cap: float = 18.0,
        clamp_team_max: float = 82.0,
        clamp_total_max: float = 155.0,
        blowout_team_max: float = 112.0,
        blowout_total_max: float = 190.0,
    ) -> None:
        self.base_total = base_total
        self.home_adv = home_adv
        self.total_shrink = total_shrink
        self.margin_scale = margin_scale
        self.margin_keep = margin_keep
        self.margin_divisor_normal = margin_divisor_normal
        self.blowout_margin_keep = blowout_margin_keep
        self.margin_divisor_blowout = margin_divisor_blowout
        self.boost_start_elo = boost_start_elo
        self.boost_per_elo = boost_per_elo
        self.boost_cap = boost_cap
        self.clamp_team_max = clamp_team_max
        self.clamp_total_max = clamp_total_max
        self.blowout_team_max = blowout_team_max
        self.blowout_total_max = blowout_total_max


def elo_expected(diff: float) -> float:
    return 1.0 / (1.0 + (10.0 ** (-float(diff) / 400.0)))


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_blowout_mode(
    cfg: BlowoutConfig,
    home: str,
    away: str,
    team_games: Dict[str, int],
    elo_diff: float,
    strength_gap: float,
    second_meeting: bool,
    first_meeting_blowout: bool,
) -> bool:
    if not cfg.enabled:
        return False
    if team_games.get(home, 0) < cfg.min_games_each:
        return False
    if team_games.get(away, 0) < cfg.min_games_each:
        return False
    if abs(elo_diff) >= cfg.elo_diff_threshold:
        return True
    if abs(strength_gap) >= cfg.strength_gap_threshold:
        return True
    if (
        second_meeting
        and first_meeting_blowout
        and abs(elo_diff) >= (cfg.elo_diff_threshold - cfg.first_blowout_second_meeting_relief)
    ):
        return True
    return False


def score_engine(
    elo_diff: float,
    blowout: bool,
    second_meeting: bool,
    first_meeting_blowout: bool,
    is_neutral: bool,
    cfg: ScoreConfig,
) -> Tuple[float, float, float, float]:
    divisor = float(cfg.margin_divisor_blowout if blowout else cfg.margin_divisor_normal)
    divisor = max(1e-6, divisor)

    margin_raw = float(cfg.margin_scale) * (float(elo_diff) / divisor)

    keep = float(cfg.blowout_margin_keep if blowout else cfg.margin_keep)
    keep = clamp(keep, 0.0, 1.0)
    margin = margin_raw * keep

    if blowout:
        sign = 1.0 if margin >= 0 else -1.0

        excess = max(0.0, abs(float(elo_diff)) - float(cfg.boost_start_elo))
        boost = clamp(float(cfg.boost_per_elo) * excess, 0.0, float(cfg.boost_cap))
        margin = margin + sign * boost

        floor = 0.04 * abs(float(elo_diff)) - 3.0
        floor = clamp(floor, 0.0, 14.0)
        if abs(margin) < floor:
            margin = sign * floor

        if second_meeting and first_meeting_blowout:
            rematch_floor = 12.0
            if abs(margin) < rematch_floor:
                margin = sign * rematch_floor

    total = float(cfg.base_total) + abs(margin)

    team_cap = float(cfg.blowout_team_max if blowout else cfg.clamp_team_max)
    total_cap = float(cfg.blowout_total_max if blowout else cfg.clamp_total_max)

    total = clamp(total, 80.0, total_cap)

    home_score = total / 2.0 + margin / 2.0
    away_score = total / 2.0 - margin / 2.0

    if not bool(is_neutral):
        home_score = float(home_score) + float(cfg.home_adv)
        margin = float(margin) + float(cfg.home_adv)
        total = float(home_score) + float(away_score)

    home_score = clamp(home_score, 40.0, team_cap)
    away_score = clamp(away_score, 35.0, team_cap)

    return home_score, away_score, (home_score - away_score), (home_score + away_score)


# ----------------- Platt calibration helpers -----------------


def _logit(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 1e-12, 1 - 1e-12)
    return np.log(x / (1 - x))


def _platt_fit(p: np.ndarray, y: np.ndarray, iters: int = 2000, lr: float = 0.02) -> tuple[float, float]:
    x = _logit(p)
    a, b = 0.0, 1.0
    for _ in range(iters):
        z = a + b * x
        q = 1.0 / (1.0 + np.exp(-z))
        a -= lr * float(np.mean(q - y))
        b -= lr * float(np.mean((q - y) * x))
    return a, b


def _platt_apply(prob: float, a: float, b: float) -> float:
    p = float(clamp(prob, 1e-6, 1.0 - 1e-6))
    z = a + b * float(_logit(np.array([p], dtype=float))[0])
    q = 1.0 / (1.0 + np.exp(-z))
    return float(clamp(float(q), 1e-6, 1.0 - 1e-6))


def main() -> None:
    if not GAMESPATH.exists():
        raise FileNotFoundError(f"Missing GAMESPATH: {GAMESPATH}")

    games = pd.read_parquet(GAMESPATH).copy()
    if "Date" in games.columns:
        games["Date"] = pd.to_datetime(games["Date"], errors="coerce")
        games = games.sort_values("Date").reset_index(drop=True)

    required = ["GameID", "HomeKey", "AwayKey", "IsNeutral", GENDER_COL]
    for c in required:
        if c not in games.columns:
            raise RuntimeError(f"games file missing required column: {c}")

    games["GameID"] = games["GameID"].astype(str).str.strip()
    games["HomeKey"] = games["HomeKey"].astype(str).str.strip()
    games["AwayKey"] = games["AwayKey"].astype(str).str.strip()

    blowout_cfg = BlowoutConfig()
    score_cfg = ScoreConfig()

    team_games: Dict[str, int] = {}
    elo: Dict[str, float] = {}
    matchup_history: Dict[Tuple[str, str], List[dict]] = {}

    def get_elo(team: str) -> float:
        return float(elo.get(team, 1500.0))

    def update_elo(home: str, away: str, result_home_win: int) -> None:
        # Adaptive K: higher early season, lower later (stabilizes + improves rematch learning)
        gh = int(team_games.get(home, 0))
        ga = int(team_games.get(away, 0))
        gmin = min(gh, ga)

        # Tune these 3 numbers first
        K_MAX = 28.0
        K_MIN = 12.0
        G_FULL = 12  # after ~12 games, mostly stabilized

        frac = min(1.0, gmin / float(G_FULL))
        k = K_MAX - (K_MAX - K_MIN) * frac

        rh = get_elo(home)
        ra = get_elo(away)
        p = elo_expected(rh - ra)

        elo[home] = rh + k * (float(result_home_win) - p)
        elo[away] = ra - k * (float(result_home_win) - p)


    build_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")

    # Rolling calibration store (favorite prob, favorite outcome), walk-forward
    N_WINDOW = 1500
    MIN_FIT = 300
    calib_p: List[float] = []
    calib_y: List[float] = []
    platt_a, platt_b = 0.0, 1.0

    rows: List[dict] = []
    for _, g in games.iterrows():
        home = str(g["HomeKey"]).strip()
        away = str(g["AwayKey"]).strip()
        gid = str(g["GameID"]).strip()
        is_neutral = bool(g.get("IsNeutral", False))
        gender = str(g.get(GENDER_COL, "")).strip().title()

        team_games.setdefault(home, 0)
        team_games.setdefault(away, 0)

        elo_diff = get_elo(home) - get_elo(away)

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

        key = tuple(sorted((home, away)))
        hist = matchup_history.get(key, [])
        second_meeting = len(hist) >= 1
        first_meeting_blowout = bool(hist[0].get("IsBlowout", False)) if second_meeting else False

        blowout = compute_blowout_mode(
            blowout_cfg, home, away, team_games, elo_diff, strength_gap, second_meeting, first_meeting_blowout
        )

        ph, pa, pm, pt = score_engine(
            elo_diff=elo_diff,
            blowout=blowout,
            second_meeting=second_meeting,
            first_meeting_blowout=first_meeting_blowout,
            is_neutral=is_neutral,
            cfg=score_cfg,
        )

        # ----------------- Girls score/total calibration -----------------
        # Fix systematic Girls total bias by shifting total downward, then
        # recompute component scores so total stays consistent with margin.
        if gender == "Girls":
            pt = float(pt) - float(GIRLS_TOTAL_BIAS)

            ph = float(pt) / 2.0 + float(pm) / 2.0
            pa = float(pt) / 2.0 - float(pm) / 2.0

            team_cap = float(score_cfg.blowout_team_max if blowout else score_cfg.clamp_team_max)
            total_cap = float(score_cfg.blowout_total_max if blowout else score_cfg.clamp_total_max)

            pt = clamp(float(pt), 80.0, total_cap)
            ph = clamp(float(ph), 40.0, team_cap)
            pa = clamp(float(pa), 35.0, team_cap)

            pm = float(ph) - float(pa)
            pt = float(ph) + float(pa)
        # ---------------------------------------------------------------

        home_score = pd.to_numeric(g.get("HomeScore", pd.NA), errors="coerce")
        away_score = pd.to_numeric(g.get("AwayScore", pd.NA), errors="coerce")
        played = pd.notna(home_score) and pd.notna(away_score)

        # Raw Elo-based win probability
        ELO_PROB_MULT = 4.9
        winprob_home_raw = float(elo_expected(ELO_PROB_MULT * elo_diff))
        winprob_home_raw = float(clamp(winprob_home_raw, 1e-6, 1.0 - 1e-6))

        # Calibrated (when enough history), otherwise raw
        if len(calib_p) >= MIN_FIT:
            winprob_home = _platt_apply(winprob_home_raw, platt_a, platt_b)
        else:
            winprob_home = winprob_home_raw

        # W/L-first: predicted winner comes from win probability
        pred_home_wins = bool(winprob_home >= 0.5)
        pred_winner_key = home if pred_home_wins else away
        pred_loser_key = away if pred_home_wins else home
        pred_winner_prob = float(winprob_home) if pred_home_wins else float(1.0 - winprob_home)

        if played:
            actual_margin = float(home_score - away_score)
            result_home_win = 1 if actual_margin > 0 else 0

            hist.append({"IsBlowout": abs(actual_margin) >= 30})
            matchup_history[key] = hist

            update_elo(home, away, result_home_win)
            team_games[home] += 1
            team_games[away] += 1

            # Add calibration sample (favorite-based, using RAW prob as the uncalibrated score)
            fav_is_home = winprob_home_raw >= 0.5
            fav_prob = winprob_home_raw if fav_is_home else (1.0 - winprob_home_raw)
            fav_won = 1.0 if ((fav_is_home and actual_margin > 0) or ((not fav_is_home) and actual_margin < 0)) else 0.0

            calib_p.append(float(clamp(fav_prob, 1e-6, 1.0 - 1e-6)))
            calib_y.append(float(fav_won))

            if len(calib_p) > N_WINDOW:
                calib_p = calib_p[-N_WINDOW:]
                calib_y = calib_y[-N_WINDOW:]

            # Refit occasionally for stability
            if len(calib_p) >= MIN_FIT and (len(calib_p) % 25 == 0):
                p_arr = np.array(calib_p, dtype=float)
                y_arr = np.array(calib_y, dtype=float)
                platt_a, platt_b = _platt_fit(p_arr, y_arr, iters=2000, lr=0.02)
        else:
            result_home_win = pd.NA

        rows.append(
            {
                "GameID": gid,
                "HomeKey": home,
                "AwayKey": away,
                "PredHomeWinProb": winprob_home,
                "PredHomeScore": ph,
                "PredAwayScore": pa,
                "PredMargin": pm,
                "PredTotalPoints": pt,
                "PredWinnerKey": pred_winner_key,
                "PredLoserKey": pred_loser_key,
                "PredWinnerProb": pred_winner_prob,
                "PredWinnerProbPct": 100.0 * pred_winner_prob,
                "PredSpreadAbs": abs(float(pm)),
                "CoreVersion": ENGINEVERSION,
                "PredBuildID": build_id,
                "EloDiff": elo_diff,
                "StrengthGap": strength_gap,
                "BlowoutMode": blowout,
                "SecondMeeting": second_meeting,
                "FirstMeetingWasBlowout": first_meeting_blowout,
                "ResultHomeWin": result_home_win,
            }
        )

    out = pd.DataFrame(rows)

    for c in [
        "PredHomeWinProb",
        "PredHomeScore",
        "PredAwayScore",
        "PredMargin",
        "PredTotalPoints",
        "PredWinnerProb",
        "PredWinnerProbPct",
        "PredSpreadAbs",
        "EloDiff",
        "StrengthGap",
    ]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out.drop_duplicates(subset="GameID", keep="first").reset_index(drop=True)

    if len(out) != len(games):
        raise RuntimeError(f"v40 engine wrote {len(out)} rows but games has {len(games)} rows")

    OUTPATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUTPATH, index=False)
    print(f"Wrote {len(out)} rows to {OUTPATH}")


if __name__ == "__main__":
    main()
