import pandas as pd
import numpy as np
from dataclasses import dataclass
from math import exp, log

# -------------------------------------------------
# Paths
# -------------------------------------------------

GAMES_PATH = "data/games_game_core_v30.parquet"
OUT_PATH = "data/model_eval_walkforward_v34b.parquet"

# -------------------------------------------------
# Config
# -------------------------------------------------

@dataclass
class BlowoutConfig:
    enabled: bool = True
    min_games_each: int = 8
    elo_diff_threshold: float = 180.0
    strength_gap_threshold: float = 20.0
    second_meeting_elo_relaxed: float = 140.0


@dataclass
class ScoreConfig:
    base_total: float = 118.0
    home_adv: float = 3.0

    margin_shrink: float = 0.55
    total_shrink: float = 0.65

    clamp_team_max: float = 82.0
    clamp_total_max: float = 155.0

    blowout_team_max: float = 112.0
    blowout_total_max: float = 190.0

    # v34.b amplification (bounded)
    second_meeting_margin_boost: float = 1.15
    second_meeting_total_boost: float = 1.07


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def log_loss(y, p):
    eps = 1e-9
    p = clamp(p, eps, 1 - eps)
    return -(y * log(p) + (1 - y) * log(1 - p))


# -------------------------------------------------
# Blowout gate (same as v34.a)
# -------------------------------------------------

def compute_blowout_mode(
    config: BlowoutConfig,
    home,
    away,
    team_games,
    elo_diff,
    strength_gap,
    has_played_before,
):
    if not config.enabled:
        return False

    if team_games.get(home, 0) < config.min_games_each:
        return False

    if team_games.get(away, 0) < config.min_games_each:
        return False

    if abs(elo_diff) >= config.elo_diff_threshold:
        return True

    if abs(strength_gap) >= config.strength_gap_threshold:
        return True

    if has_played_before and abs(elo_diff) >= config.second_meeting_elo_relaxed:
        return True

    return False


# -------------------------------------------------
# Score engine (v33 base + v34.b lift)
# -------------------------------------------------

def score_engine(
    elo_diff,
    blowout,
    second_meeting,
    score_cfg: ScoreConfig,
):
    margin_raw = elo_diff / 25.0
    margin = margin_raw * (1 - score_cfg.margin_shrink)

    total = (
        score_cfg.total_shrink * score_cfg.base_total
        + (1 - score_cfg.total_shrink)
        * (score_cfg.base_total + abs(margin_raw))
    )

    # v34.b: bounded amplification
    if blowout and second_meeting:
        margin *= score_cfg.second_meeting_margin_boost
        total = (
            score_cfg.base_total
            + (total - score_cfg.base_total)
            * score_cfg.second_meeting_total_boost
        )

    team_cap = score_cfg.blowout_team_max if blowout else score_cfg.clamp_team_max
    total_cap = score_cfg.blowout_total_max if blowout else score_cfg.clamp_total_max

    total = clamp(total, 80.0, total_cap)

    home_score = total / 2 + margin / 2 + score_cfg.home_adv
    away_score = total / 2 - margin / 2

    home_score = clamp(home_score, 40.0, team_cap)
    away_score = clamp(away_score, 35.0, team_cap)

    return home_score, away_score, home_score - away_score, home_score + away_score


# -------------------------------------------------
# Main walk-forward
# -------------------------------------------------

def main():
    games = pd.read_parquet(GAMES_PATH).sort_values("Date").reset_index(drop=True)

    blowout_cfg = BlowoutConfig()
    score_cfg = ScoreConfig()

    team_games = {}
    elo = {}
    matchup_history = set()

    def get_elo(team):
        return elo.get(team, 1500.0)

    def update_elo(home, away, result):
        k = 18
        rh = get_elo(home)
        ra = get_elo(away)
        p = sigmoid((rh - ra) / 400.0)
        elo[home] = rh + k * (result - p)
        elo[away] = ra - k * (result - p)

    rows = []

    for _, g in games.iterrows():
        home = g.Home
        away = g.Away

        team_games.setdefault(home, 0)
        team_games.setdefault(away, 0)

        elo_diff = get_elo(home) - get_elo(away)
        strength_gap = g.StrengthGap if "StrengthGap" in g else 0.0

        matchup_key = tuple(sorted([home, away]))
        second_meeting = matchup_key in matchup_history

        blowout = compute_blowout_mode(
            blowout_cfg,
            home,
            away,
            team_games,
            elo_diff,
            strength_gap,
            second_meeting,
        )

        ph, pa, pm, pt = score_engine(
            elo_diff,
            blowout,
            second_meeting,
            score_cfg,
        )

        actual_margin = g.HomeScore - g.AwayScore
        result = 1 if actual_margin > 0 else 0

        win_prob = sigmoid(elo_diff / 400.0)

        rows.append(
            {
                "GameID": g.GameID,
                "Home": home,
                "Away": away,
                "SecondMeeting": second_meeting,
                "PredHomeScore": ph,
                "PredAwayScore": pa,
                "PredMarginHome": pm,
                "PredTotal": pt,
                "HomeScore": g.HomeScore,
                "AwayScore": g.AwayScore,
                "AbsErrMargin": abs(pm - actual_margin),
                "AbsErrTotal": abs(pt - (g.HomeScore + g.AwayScore)),
                "AbsErrHome": abs(ph - g.HomeScore),
                "AbsErrAway": abs(pa - g.AwayScore),
                "Brier": (win_prob - result) ** 2,
                "LogLoss": log_loss(result, win_prob),
                "EloDiff": elo_diff,
                "StrengthGap": strength_gap,
                "BlowoutMode": blowout,
            }
        )

        update_elo(home, away, result)
        team_games[home] += 1
        team_games[away] += 1
        matchup_history.add(matchup_key)

    pd.DataFrame(rows).to_parquet(OUT_PATH, index=False)


if __name__ == "__main__":
    main()
