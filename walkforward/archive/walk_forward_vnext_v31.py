from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional

import math
import pandas as pd


DATA_DIR = Path("data")
GAMES_PATH = DATA_DIR / "games_game_core_v30.parquet"
OUT_EVAL_PATH = DATA_DIR / "model_eval_walkforward_v31.parquet"


@dataclass
class EloConfig:
    base_rating: float = 1500.0
    k_early: float = 46.0
    k_late: float = 18.0
    early_games: int = 10
    mov_cap: float = 20.0
    elo_scale: float = 400.0
    home_adv_elo: float = 55.0
    rating_per_point: float = 25.0


@dataclass
class PointsConfig:
    base_points: float = 52.0
    home_pts_adv: float = 2.0
    pace_init: float = 0.0
    lr_base: float = 0.030
    l2_off: float = 0.020
    l2_def: float = 0.020
    l2_pace: float = 0.010
    max_step: float = 0.35


@dataclass
class BlendConfig:
    min_w_points: float = 0.15
    max_w_points: float = 0.90
    games_for_full_weight: int = 10


@dataclass
class ShrinkConfig:
    shrink_strength: float = 0.75


@dataclass
class GateConfig:
    gate_games_min: int = 6
    gate_margin_abs: float = 6.0


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


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


class EloState:
    def __init__(self, cfg: EloConfig):
        self.cfg = cfg
        self.ratings: Dict[Tuple[str, str, str], float] = {}
        self.games_played: Dict[Tuple[str, str, str], int] = {}

    def _key(self, season: str, gender: str, team: str) -> Tuple[str, str, str]:
        return (str(season), str(gender), str(team))

    def get_rating(self, season: str, gender: str, team: str) -> float:
        return self.ratings.get(self._key(season, gender, team), self.cfg.base_rating)

    def get_games(self, season: str, gender: str, team: str) -> int:
        return self.games_played.get(self._key(season, gender, team), 0)

    def predict(self, season: str, gender: str, home: str, away: str) -> Tuple[float, float]:
        rh = self.get_rating(season, gender, home)
        ra = self.get_rating(season, gender, away)
        diff = (rh - ra) + self.cfg.home_adv_elo
        p_home = _win_prob_from_elo(diff, self.cfg.elo_scale)
        margin_pts = diff / self.cfg.rating_per_point
        return float(p_home), float(margin_pts)

    def update(self, season: str, gender: str, home: str, away: str, home_score: float, away_score: float) -> None:
        rh = self.get_rating(season, gender, home)
        ra = self.get_rating(season, gender, away)

        diff = (rh - ra) + self.cfg.home_adv_elo
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

        self.ratings[kh] = float(rh_new)
        self.ratings[ka] = float(ra_new)
        self.games_played[kh] = gh + 1
        self.games_played[ka] = ga + 1


class PointsState:
    def __init__(self, cfg: PointsConfig):
        self.cfg = cfg
        self.off: Dict[Tuple[str, str, str], float] = {}
        self.defn: Dict[Tuple[str, str, str], float] = {}
        self.pace: Dict[Tuple[str, str, str], float] = {}
        self.games_played: Dict[Tuple[str, str, str], int] = {}

    def _key(self, season: str, gender: str, team: str) -> Tuple[str, str, str]:
        return (str(season), str(gender), str(team))

    def _get(self, d: Dict[Tuple[str, str, str], float], k: Tuple[str, str, str]) -> float:
        return float(d.get(k, 0.0))

    def get_games(self, season: str, gender: str, team: str) -> int:
        return int(self.games_played.get(self._key(season, gender, team), 0))

    def predict_means(self, season: str, gender: str, home: str, away: str) -> Tuple[float, float, float]:
        kh = self._key(season, gender, home)
        ka = self._key(season, gender, away)

        off_h = self._get(self.off, kh)
        def_h = self._get(self.defn, kh)
        pace_h = self._get(self.pace, kh)

        off_a = self._get(self.off, ka)
        def_a = self._get(self.defn, ka)
        pace_a = self._get(self.pace, ka)

        pace_term = (pace_h + pace_a) / 2.0

        mu_home = self.cfg.base_points + pace_term + off_h - def_a + self.cfg.home_pts_adv
        mu_away = self.cfg.base_points + pace_term + off_a - def_h

        mu_home = float(_clip(mu_home, 25.0, 95.0))
        mu_away = float(_clip(mu_away, 25.0, 95.0))

        total = float(mu_home + mu_away)
        return mu_home, mu_away, total

    def update(self, season: str, gender: str, home: str, away: str, home_score: float, away_score: float) -> None:
        kh = self._key(season, gender, home)
        ka = self._key(season, gender, away)

        mu_home, mu_away, _ = self.predict_means(season, gender, home, away)

        err_h = float(home_score) - mu_home
        err_a = float(away_score) - mu_away

        pace_obs = (float(home_score) + float(away_score)) / 2.0 - self.cfg.base_points
        pace_h = self._get(self.pace, kh)
        pace_a = self._get(self.pace, ka)

        gh = self.get_games(season, gender, home)
        ga = self.get_games(season, gender, away)
        gmin = min(gh, ga)

        lr = self.cfg.lr_base * (1.0 + 0.7 * math.exp(-gmin / 4.0))
        lr = float(_clip(lr, 0.010, 0.060))

        def step(x: float) -> float:
            return float(_clip(x, -self.cfg.max_step, self.cfg.max_step))

        off_h = self._get(self.off, kh)
        def_h = self._get(self.defn, kh)
        off_a = self._get(self.off, ka)
        def_a = self._get(self.defn, ka)

        grad_off_h = err_h - self.cfg.l2_off * off_h
        grad_def_a = -err_h - self.cfg.l2_def * def_a

        grad_off_a = err_a - self.cfg.l2_off * off_a
        grad_def_h = -err_a - self.cfg.l2_def * def_h

        pace_target_h = pace_obs - self.cfg.l2_pace * pace_h
        pace_target_a = pace_obs - self.cfg.l2_pace * pace_a

        self.off[kh] = off_h + step(lr * grad_off_h)
        self.defn[ka] = def_a + step(lr * grad_def_a)

        self.off[ka] = off_a + step(lr * grad_off_a)
        self.defn[kh] = def_h + step(lr * grad_def_h)

        self.pace[kh] = pace_h + step(lr * 0.50 * pace_target_h)
        self.pace[ka] = pace_a + step(lr * 0.50 * pace_target_a)

        self.games_played[kh] = gh + 1
        self.games_played[ka] = ga + 1


def _blend_weight(games_home: int, games_away: int, cfg: BlendConfig) -> float:
    g = min(games_home, games_away)
    t = _clip(g / float(cfg.games_for_full_weight), 0.0, 1.0)
    return float(cfg.min_w_points + (cfg.max_w_points - cfg.min_w_points) * t)


def _confidence_score(p_home: float, margin_points: float, games_home: int, games_away: int) -> float:
    g = min(games_home, games_away)
    g_term = _clip(g / 12.0, 0.0, 1.0)
    p_term = abs(p_home - 0.5) * 2.0
    m_term = _clip(abs(margin_points) / 15.0, 0.0, 1.0)
    conf = 0.45 * g_term + 0.35 * p_term + 0.20 * m_term
    return float(_clip(conf, 0.0, 1.0))


def _close_game_shrink(margin: float, conf: float, cfg: ShrinkConfig) -> float:
    shrink = cfg.shrink_strength * (1.0 - conf)
    return float(margin * (1.0 - shrink))


def _brier(p: float, y: float) -> float:
    return float((p - y) ** 2)


def _logloss(p: float, y: float) -> float:
    p = float(_clip(p, 1e-6, 1.0 - 1e-6))
    return float(-(y * math.log(p) + (1.0 - y) * math.log(1.0 - p)))


def main() -> None:
    if not GAMES_PATH.exists():
        raise SystemExit(f"Missing {GAMES_PATH}")

    df = pd.read_parquet(GAMES_PATH).copy()

    date_col = _safe_col(df, "Date", "date", "GameDate")
    gameid_col = _safe_col(df, "GameID", "GameId", "game_id")
    season_col = _safe_col(df, "Season", "season")
    gender_col = _safe_col(df, "Gender", "gender")
    home_col = _safe_col(df, "Home", "HomeTeam")
    away_col = _safe_col(df, "Away", "AwayTeam")
    hs_col = _safe_col(df, "HomeScore", "HomePts", "HomePoints")
    as_col = _safe_col(df, "AwayScore", "AwayPts", "AwayPoints")

    required = {
        "Date": date_col,
        "GameID": gameid_col,
        "Season": season_col,
        "Gender": gender_col,
        "Home": home_col,
        "Away": away_col,
        "HomeScore": hs_col,
        "AwayScore": as_col,
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values([date_col, gameid_col]).reset_index(drop=True)

    elo_cfg = EloConfig()
    pts_cfg = PointsConfig()
    blend_cfg = BlendConfig()
    shrink_cfg = ShrinkConfig()
    gate_cfg = GateConfig()

    elo = EloState(elo_cfg)
    pts = PointsState(pts_cfg)

    rows = []

    for _, r in df.iterrows():
        season = str(r[season_col]).strip()
        gender = str(r[gender_col]).strip()
        home = str(r[home_col]).strip()
        away = str(r[away_col]).strip()

        hs = r[hs_col]
        ars = r[as_col]
        if pd.isna(hs) or pd.isna(ars):
            continue

        hs = float(hs)
        ars = float(ars)

        p_home_elo, margin_elo = elo.predict(season, gender, home, away)

        mu_h, mu_a, total_pts = pts.predict_means(season, gender, home, away)
        margin_points = float(mu_h - mu_a)

        gh = pts.get_games(season, gender, home)
        ga = pts.get_games(season, gender, away)

        w_points = _blend_weight(gh, ga, blend_cfg)
        margin_blend = float(w_points * margin_points + (1.0 - w_points) * margin_elo)

        conf = _confidence_score(p_home_elo, margin_points, gh, ga)

        gmin = min(gh, ga)
        if gmin < gate_cfg.gate_games_min and abs(margin_blend) < gate_cfg.gate_margin_abs:
            margin_final = 0.0
        else:
            margin_final = _close_game_shrink(margin_blend, conf, shrink_cfg)

        pred_home = float((total_pts + margin_final) / 2.0)
        pred_away = float(total_pts - pred_home)

        pred_home = float(_clip(pred_home, 25.0, 95.0))
        pred_away = float(_clip(pred_away, 25.0, 95.0))
        pred_total = float(pred_home + pred_away)

        p_home = float(p_home_elo)

        margin_actual = hs - ars
        total_actual = hs + ars
        y_home = 1.0 if margin_actual > 0 else 0.0

        rows.append(
            dict(
                Date=r[date_col],
                GameID=int(r[gameid_col]),
                Season=season,
                Gender=gender,
                Home=home,
                Away=away,
                HomeScore=hs,
                AwayScore=ars,
                PredWinProbHome=float(p_home),
                PredMarginHome=float(margin_final),
                PredHomeScore=float(pred_home),
                PredAwayScore=float(pred_away),
                PredTotal=float(pred_total),
                Conf=float(conf),
                WeightPoints=float(w_points),
                PredMarginPoints=float(margin_points),
                PredMarginElo=float(margin_elo),
                PredWinProbElo=float(p_home_elo),
                ActualMarginHome=float(margin_actual),
                ActualTotal=float(total_actual),
                ErrorMargin=float(margin_final - margin_actual),
                ErrorTotal=float(pred_total - total_actual),
                ErrorHomeScore=float(pred_home - hs),
                ErrorAwayScore=float(pred_away - ars),
                Brier=float(_brier(p_home, y_home)),
                LogLoss=float(_logloss(p_home, y_home)),
            )
        )

        pts.update(season, gender, home, away, hs, ars)
        elo.update(season, gender, home, away, hs, ars)

    out = pd.DataFrame(rows)
    out.to_parquet(OUT_EVAL_PATH, index=False)
    print("wrote", OUT_EVAL_PATH, "rows", len(out))


if __name__ == "__main__":
    main()
