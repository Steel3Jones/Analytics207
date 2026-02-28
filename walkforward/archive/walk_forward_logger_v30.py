from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional

import math
import pandas as pd


DATA_DIR = Path("data")
GAMES_PATH = DATA_DIR / "games_game_core_v30.parquet"
OUT_PATH = DATA_DIR / "model_eval_walkforward_v31.parquet"


@dataclass
class EloConfig:
    base_rating: float = 1500.0
    k_early: float = 42.0
    k_late: float = 18.0
    early_games: int = 10
    home_adv_points: float = 55.0
    mov_cap: float = 20.0
    elo_scale: float = 400.0


def _safe_col(df: pd.DataFrame, *cands: str) -> Optional[str]:
    for c in cands:
        if c in df.columns:
            return c
    return None


def _win_prob_from_elo(diff: float, scale: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-diff / scale))


def _mov_multiplier(margin: float, cap: float) -> float:
    m = min(abs(float(margin)), cap)
    return math.log1p(m)


class EloState:
    def __init__(self, cfg: EloConfig):
        self.cfg = cfg
        self.ratings: Dict[Tuple[str, str, str], float] = {}
        self.games_played: Dict[Tuple[str, str, str], int] = {}

    def _key(self, season: str, gender: str, team: str) -> Tuple[str, str, str]:
        return (str(season), str(gender), str(team))

    def get_rating(self, season: str, gender: str, team: str) -> float:
        k = self._key(season, gender, team)
        return self.ratings.get(k, self.cfg.base_rating)

    def get_games(self, season: str, gender: str, team: str) -> int:
        k = self._key(season, gender, team)
        return self.games_played.get(k, 0)

    def predict(self, season: str, gender: str, home: str, away: str) -> Tuple[float, float]:
        rh = self.get_rating(season, gender, home)
        ra = self.get_rating(season, gender, away)

        diff = (rh - ra) + self.cfg.home_adv_points
        p_home = _win_prob_from_elo(diff, self.cfg.elo_scale)

        margin_pts = diff / 25.0

        return p_home, margin_pts

    def update(self, season: str, gender: str, home: str, away: str, home_score: float, away_score: float) -> None:
        rh = self.get_rating(season, gender, home)
        ra = self.get_rating(season, gender, away)

        diff = (rh - ra) + self.cfg.home_adv_points
        p_home = _win_prob_from_elo(diff, self.cfg.elo_scale)

        margin = float(home_score) - float(away_score)
        actual_home = 1.0 if margin > 0 else 0.0

        gh = self.get_games(season, gender, home)
        ga = self.get_games(season, gender, away)
        k_home = self.cfg.k_early if gh < self.cfg.early_games else self.cfg.k_late
        k_away = self.cfg.k_early if ga < self.cfg.early_games else self.cfg.k_late

        mult = _mov_multiplier(margin, self.cfg.mov_cap)

        rh_new = rh + (k_home * mult) * (actual_home - p_home)
        ra_new = ra + (k_away * mult) * ((1.0 - actual_home) - (1.0 - p_home))

        kh = self._key(season, gender, home)
        ka = self._key(season, gender, away)
        self.ratings[kh] = rh_new
        self.ratings[ka] = ra_new
        self.games_played[kh] = gh + 1
        self.games_played[ka] = ga + 1


def main() -> None:
    if not GAMES_PATH.exists():
        raise SystemExit(f"Missing {GAMES_PATH}")

    df = pd.read_parquet(GAMES_PATH).copy()

    date_col = _safe_col(df, "Date", "date", "GameDate")
    if date_col is None:
        raise SystemExit("Could not find a Date column")

    gameid_col = _safe_col(df, "GameID", "GameId", "game_id")
    if gameid_col is None:
        raise SystemExit("Could not find a GameID column")

    season_col = _safe_col(df, "Season", "season")
    gender_col = _safe_col(df, "Gender", "gender")
    home_col = _safe_col(df, "Home", "HomeTeam")
    away_col = _safe_col(df, "Away", "AwayTeam")
    hs_col = _safe_col(df, "HomeScore", "HomePts", "HomePoints")
    as_col = _safe_col(df, "AwayScore", "AwayPts", "AwayPoints")

    missing = [n for n, c in [
        ("Season", season_col),
        ("Gender", gender_col),
        ("Home", home_col),
        ("Away", away_col),
        ("HomeScore", hs_col),
        ("AwayScore", as_col),
    ] if c is None]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values([date_col, gameid_col]).reset_index(drop=True)

    cfg = EloConfig()
    state = EloState(cfg)

    rows = []

    for _, r in df.iterrows():
        season = str(r[season_col])
        gender = str(r[gender_col])
        home = str(r[home_col])
        away = str(r[away_col])

        home_score = r[hs_col]
        away_score = r[as_col]

        if pd.isna(home_score) or pd.isna(away_score):
            continue

        p_home, margin_pred = state.predict(season, gender, home, away)

        total_pred = None
        if "HomeAvgTotal" in df.columns and "AwayAvgTotal" in df.columns:
            try:
                total_pred = float(r["HomeAvgTotal"] + r["AwayAvgTotal"]) / 2.0
            except Exception:
                total_pred = None

        pred_home = None
        pred_away = None
        if total_pred is not None:
            pred_home = (total_pred + margin_pred) / 2.0
            pred_away = total_pred - pred_home

        margin_actual = float(home_score) - float(away_score)
        total_actual = float(home_score) + float(away_score)
        win_home = 1.0 if margin_actual > 0 else 0.0
        brier = (p_home - win_home) ** 2
        err_margin = margin_pred - margin_actual

        rows.append(
            dict(
                Date=r[date_col],
                GameID=r[gameid_col],
                Season=season,
                Gender=gender,
                Home=home,
                Away=away,
                HomeScore=float(home_score),
                AwayScore=float(away_score),
                PredWinProbHome=float(p_home),
                PredMarginHome=float(margin_pred),
                PredTotal=float(total_pred) if total_pred is not None else None,
                PredHomeScore=float(pred_home) if pred_home is not None else None,
                PredAwayScore=float(pred_away) if pred_away is not None else None,
                ActualMarginHome=float(margin_actual),
                ActualTotal=float(total_actual),
                Brier=float(brier),
                ErrorMargin=float(err_margin),
            )
        )

        state.update(season, gender, home, away, float(home_score), float(away_score))

    out = pd.DataFrame(rows)
    out.to_parquet(OUT_PATH, index=False)
    print("wrote", OUT_PATH, "rows", len(out))


if __name__ == "__main__":
    main()
