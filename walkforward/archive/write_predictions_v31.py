from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional

import math
import shutil
import numpy as np
import pandas as pd


DATA_DIR = Path("data")

GAMES_PATH = DATA_DIR / "games_game_core_v30.parquet"
CAL_TABLE_PATH = DATA_DIR / "calibration_winprob_table_v31.parquet"

OUT_V31 = DATA_DIR / "games_predictions_v31.parquet"
OUT_CURRENT = DATA_DIR / "games_predictions_current.parquet"


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
    lr_base: float = 0.030
    l2_off: float = 0.020
    l2_def: float = 0.020
    l2_pace: float = 0.010
    max_step: float = 0.35
    # how many games before we trust learned off/def more than fallbacks
    min_games_for_state: int = 4


@dataclass
class BlendConfig:
    min_w_points: float = 0.15
    max_w_points: float = 0.90
    games_for_full_weight: int = 10


@dataclass
class ShrinkConfig:
    shrink_strength: float = 0.75


def _safe_col(df: pd.DataFrame, *cands: str) -> Optional[str]:
    for c in cands:
        if c in df.columns:
            return c
    return None


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _win_prob_from_elo(diff: float, scale: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-diff / scale))


def _mov_multiplier(margin: float, cap: float) -> float:
    m = min(abs(float(margin)), cap)
    return math.log1p(m)


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

    def predict_from_state(self, season: str, gender: str, home: str, away: str) -> Tuple[float, float]:
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
        return mu_home, mu_away

    def update(self, season: str, gender: str, home: str, away: str, home_score: float, away_score: float) -> None:
        kh = self._key(season, gender, home)
        ka = self._key(season, gender, away)

        mu_home, mu_away = self.predict_from_state(season, gender, home, away)

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


def _apply_cal_table(p: np.ndarray, table: pd.DataFrame) -> np.ndarray:
    p_out = np.empty_like(p, dtype=float)
    p_lo = table["p_lo"].to_numpy(dtype=float)
    p_hi = table["p_hi"].to_numpy(dtype=float)
    p_cal = table["p_cal"].to_numpy(dtype=float)

    for i, x in enumerate(p):
        j = np.searchsorted(p_hi, x, side="left")
        if j >= len(p_hi):
            j = len(p_hi) - 1
        if x < p_lo[j]:
            j = max(j - 1, 0)
        p_out[i] = p_cal[j]

    return p_out


def _fallback_mu_from_row(r: pd.Series) -> Tuple[Optional[float], Optional[float]]:
    hp = r.get("HomePPG")
    ho = r.get("HomeOPPG")
    ap = r.get("AwayPPG")
    ao = r.get("AwayOPPG")

    vals = [hp, ho, ap, ao]
    if any(pd.isna(v) for v in vals):
        return None, None

    hp = float(hp)
    ho = float(ho)
    ap = float(ap)
    ao = float(ao)

    # simple offense-defense interaction baseline:
    # home expected points ~ avg(home scoring, away conceding) + small home bump already handled in state model,
    # so here include modest +1 to represent court.
    mu_home = 0.5 * hp + 0.5 * ao + 1.0
    mu_away = 0.5 * ap + 0.5 * ho

    return float(_clip(mu_home, 25.0, 95.0)), float(_clip(mu_away, 25.0, 95.0))


def main() -> None:
    if not GAMES_PATH.exists():
        raise SystemExit(f"Missing {GAMES_PATH}")
    if not CAL_TABLE_PATH.exists():
        raise SystemExit(f"Missing {CAL_TABLE_PATH}")

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
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.sort_values([date_col, gameid_col]).reset_index(drop=True)

    cal = pd.read_parquet(CAL_TABLE_PATH).copy()

    elo_cfg = EloConfig()
    pts_cfg = PointsConfig()
    blend_cfg = BlendConfig()
    shrink_cfg = ShrinkConfig()

    elo = EloState(elo_cfg)
    pts = PointsState(pts_cfg)

    out_rows = []

    for _, r in df.iterrows():
        season = str(r[season_col]).strip()
        gender = str(r[gender_col]).strip()
        home = str(r[home_col]).strip()
        away = str(r[away_col]).strip()

        game_id = int(r[gameid_col])
        dt = r[date_col]

        p_raw_elo, margin_elo = elo.predict(season, gender, home, away)

        gh = pts.get_games(season, gender, home)
        ga = pts.get_games(season, gender, away)
        gmin = min(gh, ga)

        # Score prediction: trust state when it has some history, else use row-based fallback if available
        mu_state_h, mu_state_a = pts.predict_from_state(season, gender, home, away)
        mu_f_h, mu_f_a = _fallback_mu_from_row(r)

        if gmin >= pts_cfg.min_games_for_state or (mu_f_h is None or mu_f_a is None):
            mu_h = mu_state_h
            mu_a = mu_state_a
        else:
            # blend into state gradually so it doesn't jump
            w = _clip(gmin / float(pts_cfg.min_games_for_state), 0.0, 1.0)
            mu_h = float(w * mu_state_h + (1.0 - w) * mu_f_h)
            mu_a = float(w * mu_state_a + (1.0 - w) * mu_f_a)

        mu_h = float(_clip(mu_h, 25.0, 95.0))
        mu_a = float(_clip(mu_a, 25.0, 95.0))
        total_pts = float(mu_h + mu_a)

        margin_points = float(mu_h - mu_a)

        w_points = _blend_weight(gh, ga, blend_cfg)
        margin_blend = float(w_points * margin_points + (1.0 - w_points) * margin_elo)

        conf = _confidence_score(p_raw_elo, margin_points, gh, ga)

        # No snapping to 0. Shrink only.
        margin_final = _close_game_shrink(margin_blend, conf, shrink_cfg)

        # Final projected scores anchored on mu_h/mu_a, then adjusted so spread is consistent but totals stay realistic
        # small adjustment, not full algebra, to avoid collapsing scores
        adj = float(_clip(margin_final - margin_points, -6.0, 6.0))
        pred_home = float(_clip(mu_h + 0.5 * adj, 25.0, 95.0))
        pred_away = float(_clip(mu_a - 0.5 * adj, 25.0, 95.0))
        pred_total = float(pred_home + pred_away)

        out_rows.append(
            dict(
                GameID=game_id,
                Date=dt,
                Season=season,
                Gender=gender,
                Home=home,
                Away=away,
                PredWinProbRaw=float(p_raw_elo),   # raw, before calibration
                PredWinProbCal=0.0,                # filled after loop
                PredMarginHome=float(margin_final),
                PredHomeScore=float(pred_home),
                PredAwayScore=float(pred_away),
                PredTotal=float(pred_total),
                Conf=float(conf),
                WeightPoints=float(w_points),
                CoreVersion="v31",
            )
        )

        played = (hs_col is not None and as_col is not None and (not pd.isna(r.get(hs_col))) and (not pd.isna(r.get(as_col))))
        if played:
            hs = float(r[hs_col])
            ars = float(r[as_col])
            pts.update(season, gender, home, away, hs, ars)
            elo.update(season, gender, home, away, hs, ars)

    out = pd.DataFrame(out_rows)

    p = out["PredWinProbRaw"].to_numpy(dtype=float)
    p = np.clip(p, 1e-6, 1.0 - 1e-6)

    p_cal = _apply_cal_table(p, cal)
    p_cal = np.clip(p_cal, 1e-6, 1.0 - 1e-6)

    out["PredWinProbCal"] = p_cal

    out.to_parquet(OUT_V31, index=False)
    shutil.copyfile(OUT_V31, OUT_CURRENT)

    print("wrote", OUT_V31, "rows", len(out))
    print("wrote", OUT_CURRENT, "rows", len(out))


if __name__ == "__main__":
    main()
