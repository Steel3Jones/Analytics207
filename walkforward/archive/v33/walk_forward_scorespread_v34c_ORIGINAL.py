from __future__ import annotations

from math import log
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

ENGINE_VERSION = "v34c_prod_20260208"

ROOT = Path(r"C:\ANALYTICS207")
GAMES_PATH = ROOT / "data" / "games_game_core_v30.parquet"
OUT_PATH = ROOT / "data" / "games_predictions_current.parquet"


# ----------------------------
# Config (no dataclasses)
# ----------------------------
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
        base_total: float = 118.0,
        home_adv: float = 3.0,
        total_shrink: float = 0.65,
        margin_keep: float = 0.55,
        margin_divisor_normal: float = 25.0,
        blowout_margin_keep: float = 0.85,
        margin_divisor_blowout: float = 13.0,
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


# ----------------------------
# Helpers
# ----------------------------
def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def log_loss(y: int, p: float) -> float:
    eps = 1e-9
    p = clamp(p, eps, 1 - eps)
    return -(y * log(p) + (1 - y) * log(1 - p))


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
    cfg: ScoreConfig,
) -> Tuple[float, float, float, float]:
    divisor = cfg.margin_divisor_blowout if blowout else cfg.margin_divisor_normal
    divisor = max(1e-6, float(divisor))

    margin_raw = elo_diff / divisor
    keep = cfg.blowout_margin_keep if blowout else cfg.margin_keep
    keep = clamp(float(keep), 0.0, 1.0)
    margin = margin_raw * keep

    if blowout:
        sign = 1.0 if margin >= 0 else -1.0
        excess = max(0.0, abs(elo_diff) - float(cfg.boost_start_elo))
        boost = clamp(float(cfg.boost_per_elo) * excess, 0.0, float(cfg.boost_cap))
        margin = margin + sign * boost

        floor = 0.08 * abs(elo_diff) - 5.0
        floor = clamp(floor, 0.0, 22.0)
        if abs(margin) < floor:
            margin = sign * floor

        if second_meeting and first_meeting_blowout:
            rematch_floor = 30.0
            if abs(margin) < rematch_floor:
                margin = sign * rematch_floor

    total = cfg.total_shrink * cfg.base_total + (1 - cfg.total_shrink) * (cfg.base_total + abs(margin))

    team_cap = cfg.blowout_team_max if blowout else cfg.clamp_team_max
    total_cap = cfg.blowout_total_max if blowout else cfg.clamp_total_max
    total = clamp(float(total), 80.0, float(total_cap))

    home_score = total / 2 + margin / 2 + cfg.home_adv
    away_score = total / 2 - margin / 2

    home_score = clamp(float(home_score), 40.0, float(team_cap))
    away_score = clamp(float(away_score), 35.0, float(team_cap))

    return home_score, away_score, home_score - away_score, home_score + away_score


def main() -> None:
    if not GAMES_PATH.exists():
        raise FileNotFoundError(f"Missing {GAMES_PATH}")

    games = pd.read_parquet(GAMES_PATH).copy()
    if "Date" in games.columns:
        games["Date"] = pd.to_datetime(games["Date"], errors="coerce")
        games = games.sort_values("Date").reset_index(drop=True)

    for c in ["GameID", "Home", "Away", "HomeKey", "AwayKey"]:

        if c not in games.columns:
            raise RuntimeError(f"games file missing required column: {c}")

    games["GameID"] = games["GameID"].astype(str).str.strip()
    games["Home"] = games["Home"].astype(str).str.strip()
    games["Away"] = games["Away"].astype(str).str.strip()

    blowout_cfg = BlowoutConfig()
    score_cfg = ScoreConfig()

    team_games: Dict[str, int] = {}
    elo: Dict[str, float] = {}
    matchup_history: Dict[Tuple[str, str], List[dict]] = {}

    def get_elo(team: str) -> float:
        return float(elo.get(team, 1500.0))

    def update_elo(home: str, away: str, result: int) -> None:
        k = 18.0
        rh = get_elo(home)
        ra = get_elo(away)
        p = sigmoid((rh - ra) / 400.0)
        elo[home] = rh + k * (float(result) - p)
        elo[away] = ra - k * (float(result) - p)

    rows: List[dict] = []

    for _, g in games.iterrows():
        home = str(g["HomeKey"]).strip()
        away = str(g["AwayKey"]).strip()

        gid = str(g["GameID"])

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


        key = tuple(sorted([home, away]))
        hist = matchup_history.get(key, [])
        second_meeting = len(hist) >= 1
        first_meeting_blowout = bool(hist[0].get("IsBlowout", False)) if second_meeting else False

        blowout = compute_blowout_mode(
            blowout_cfg,
            home,
            away,
            team_games,
            elo_diff,
            strength_gap,
            second_meeting,
            first_meeting_blowout,
        )

        ph, pa, pm, pt = score_engine(
            elo_diff=elo_diff,
            blowout=blowout,
            second_meeting=second_meeting,
            first_meeting_blowout=first_meeting_blowout,
            cfg=score_cfg,
        )

        home_score = pd.to_numeric(g.get("HomeScore", pd.NA), errors="coerce")
        away_score = pd.to_numeric(g.get("AwayScore", pd.NA), errors="coerce")
        played = pd.notna(home_score) and pd.notna(away_score)
        win_prob = sigmoid(elo_diff / 400.0)

        # Update Elo only when played (keeps walk-forward semantics)
        if played:
            actual_margin = float(home_score - away_score)
            result = 1 if actual_margin > 0 else 0
            hist.append({"IsBlowout": abs(actual_margin) >= 30})
            matchup_history[key] = hist
            update_elo(home, away, result)
            team_games[home] += 1
            team_games[away] += 1
        else:
            result = pd.NA

        rows.append(
            {
                "GameID": gid,
                "PredHomeWinProb": win_prob,
                "PredHomeScore": ph,
                "PredAwayScore": pa,
                "PredMargin": pm,            # home - away
                "PredTotalPoints": pt,
                "CoreVersion": ENGINE_VERSION,
                # Optional debug columns you can drop later:
                "EloDiff": elo_diff,
                "StrengthGap": strength_gap,
                "BlowoutMode": blowout,
                "SecondMeeting": second_meeting,
                "FirstMeetingWasBlowout": first_meeting_blowout,
                "ResultHomeWin": result,
            }
        )

    out = pd.DataFrame(rows)

    # enforce numeric
    for c in ["PredHomeWinProb", "PredHomeScore", "PredAwayScore", "PredMargin", "PredTotalPoints"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # hard guardrail: one row per GameID and same set as games
    out = out.drop_duplicates(subset=["GameID"], keep="first").reset_index(drop=True)
    if len(out) != len(games):
        raise RuntimeError(f"v34c wrote {len(out)} rows but games has {len(games)} rows")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(out)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
