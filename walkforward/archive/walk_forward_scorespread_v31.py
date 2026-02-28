from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional

import math
import pandas as pd


DATA_DIR = Path("data")
GAMES_PATH = DATA_DIR / "games_game_core_v30.parquet"
OUT_EVAL_PATH = DATA_DIR / "model_eval_walkforward_v33.parquet"


def _safe_col(df: pd.DataFrame, *cands: str) -> Optional[str]:
    for c in cands:
        if c in df.columns:
            return c
    return None


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _win_prob_from_elo(diff: float, scale: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-diff / scale))


def _mov_multiplier(margin: float, cap: float) -> float:
    m = min(abs(float(margin)), cap)
    return math.log1p(m)


def _brier(p: float, y: float) -> float:
    return float((p - y) ** 2)


def _logloss(p: float, y: float) -> float:
    p = float(_clip(p, 1e-6, 1.0 - 1e-6))
    return float(-(y * math.log(p) + (1.0 - y) * math.log(1.0 - p)))


@dataclass
class EloConfig:
    base_rating: float = 1500.0
    k_early: float = 46.0
    k_late: float = 18.0
    early_games: int = 10
    mov_cap: float = 20.0
    elo_scale: float = 400.0
    home_adv_elo: float = 55.0
    rating_per_point: float = 18.0


@dataclass
class ScoreConfig:
    home_adv_points: float = 2.5

    init_points_for: float = 52.0
    init_points_against: float = 52.0
    init_total: float = 104.0

    alpha_min: float = 0.08
    alpha_max: float = 0.35

    mix_offense: float = 0.55
    mix_defense: float = 0.45

    total_blend: float = 0.55

    clamp_team_min: float = 24.0
    clamp_team_max: float = 98.0
    clamp_total_min: float = 70.0
    clamp_total_max: float = 160.0


@dataclass
class BlowoutConfig:
    enabled: bool = True

    min_games_each: int = 6
    elo_diff_threshold: float = 220.0

    strength_gap_threshold: float = 18.0

    total_blend_when_blowout: float = 0.10

    clamp_team_max_when_blowout: float = 112.0
    clamp_total_max_when_blowout: float = 190.0


@dataclass
class BlendConfig:
    min_w_score: float = 0.25
    max_w_score: float = 0.92
    games_for_full_weight: int = 10


@dataclass
class ShrinkConfig:
    shrink_strength: float = 0.65


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

    def predict(self, season: str, gender: str, home: str, away: str) -> Tuple[float, float, float]:
        rh = self.get_rating(season, gender, home)
        ra = self.get_rating(season, gender, away)
        diff = (rh - ra) + self.cfg.home_adv_elo
        p_home = _win_prob_from_elo(diff, self.cfg.elo_scale)
        margin_pts = diff / self.cfg.rating_per_point
        return float(p_home), float(margin_pts), float(diff)

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


class ScoreState:
    def __init__(self, cfg: ScoreConfig):
        self.cfg = cfg

        self.pf: Dict[Tuple[str, str, str], float] = {}
        self.pa: Dict[Tuple[str, str, str], float] = {}
        self.tot: Dict[Tuple[str, str, str], float] = {}
        self.g: Dict[Tuple[str, str, str], int] = {}

        self.league_tot: Dict[Tuple[str, str], float] = {}
        self.league_g: Dict[Tuple[str, str], int] = {}

    def _tkey(self, season: str, gender: str, team: str) -> Tuple[str, str, str]:
        return (str(season), str(gender), str(team))

    def _lkey(self, season: str, gender: str) -> Tuple[str, str]:
        return (str(season), str(gender))

    def get_games(self, season: str, gender: str, team: str) -> int:
        return int(self.g.get(self._tkey(season, gender, team), 0))

    def _get_pf(self, season: str, gender: str, team: str) -> float:
        return float(self.pf.get(self._tkey(season, gender, team), self.cfg.init_points_for))

    def _get_pa(self, season: str, gender: str, team: str) -> float:
        return float(self.pa.get(self._tkey(season, gender, team), self.cfg.init_points_against))

    def _get_tot(self, season: str, gender: str, team: str) -> float:
        return float(self.tot.get(self._tkey(season, gender, team), self.cfg.init_total))

    def _get_league_tot(self, season: str, gender: str) -> float:
        return float(self.league_tot.get(self._lkey(season, gender), self.cfg.init_total))

    def team_strength(self, season: str, gender: str, team: str) -> float:
        return float(self._get_pf(season, gender, team) - self._get_pa(season, gender, team))

    def _alpha(self, games_played: int) -> float:
        a = 2.0 / float(games_played + 6)
        return float(_clip(a, self.cfg.alpha_min, self.cfg.alpha_max))

    def predict_scores(
        self,
        season: str,
        gender: str,
        home: str,
        away: str,
        total_blend_override: Optional[float] = None,
        clamp_team_max_override: Optional[float] = None,
        clamp_total_max_override: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        pf_h = self._get_pf(season, gender, home)
        pa_h = self._get_pa(season, gender, home)
        tot_h = self._get_tot(season, gender, home)

        pf_a = self._get_pf(season, gender, away)
        pa_a = self._get_pa(season, gender, away)
        tot_a = self._get_tot(season, gender, away)

        base_home = self.cfg.mix_offense * pf_h + self.cfg.mix_defense * pa_a + self.cfg.home_adv_points
        base_away = self.cfg.mix_offense * pf_a + self.cfg.mix_defense * pa_h

        team_total = base_home + base_away

        league_total = self._get_league_tot(season, gender)

        tb = self.cfg.total_blend if total_blend_override is None else float(total_blend_override)
        expected_total = tb * ((tot_h + tot_a) / 2.0) + (1.0 - tb) * league_total

        total_max = self.cfg.clamp_total_max if clamp_total_max_override is None else float(clamp_total_max_override)
        team_max = self.cfg.clamp_team_max if clamp_team_max_override is None else float(clamp_team_max_override)

        expected_total = float(_clip(expected_total, self.cfg.clamp_total_min, total_max))

        scale = expected_total / team_total if team_total > 1e-6 else 1.0

        mu_home = float(_clip(base_home * scale, self.cfg.clamp_team_min, team_max))
        mu_away = float(_clip(base_away * scale, self.cfg.clamp_team_min, team_max))
        total = float(mu_home + mu_away)

        return mu_home, mu_away, total

    def update(self, season: str, gender: str, home: str, away: str, home_score: float, away_score: float) -> None:
        hk = self._tkey(season, gender, home)
        ak = self._tkey(season, gender, away)
        lk = self._lkey(season, gender)

        gh = self.get_games(season, gender, home)
        ga = self.get_games(season, gender, away)

        ah = self._alpha(gh)
        aa = self._alpha(ga)

        pf_h = self._get_pf(season, gender, home)
        pa_h = self._get_pa(season, gender, home)
        tot_h = self._get_tot(season, gender, home)

        pf_a = self._get_pf(season, gender, away)
        pa_a = self._get_pa(season, gender, away)
        tot_a = self._get_tot(season, gender, away)

        hs = float(home_score)
        ars = float(away_score)
        tot_obs = hs + ars

        self.pf[hk] = (1.0 - ah) * pf_h + ah * hs
        self.pa[hk] = (1.0 - ah) * pa_h + ah * ars
        self.tot[hk] = (1.0 - ah) * tot_h + ah * tot_obs

        self.pf[ak] = (1.0 - aa) * pf_a + aa * ars
        self.pa[ak] = (1.0 - aa) * pa_a + aa * hs
        self.tot[ak] = (1.0 - aa) * tot_a + aa * tot_obs

        lg = int(self.league_g.get(lk, 0))
        al = self._alpha(lg)
        lt = self._get_league_tot(season, gender)
        self.league_tot[lk] = (1.0 - al) * lt + al * tot_obs
        self.league_g[lk] = lg + 1

        self.g[hk] = gh + 1
        self.g[ak] = ga + 1


def _blend_weight(games_home: int, games_away: int, cfg: BlendConfig) -> float:
    g = min(games_home, games_away)
    t = _clip(g / float(cfg.games_for_full_weight), 0.0, 1.0)
    return float(cfg.min_w_score + (cfg.max_w_score - cfg.min_w_score) * t)


def _confidence_score(p_home: float, margin_pts: float, games_home: int, games_away: int) -> float:
    g = min(games_home, games_away)
    g_term = _clip(g / 12.0, 0.0, 1.0)
    p_term = abs(p_home - 0.5) * 2.0
    m_term = _clip(abs(margin_pts) / 18.0, 0.0, 1.0)
    conf = 0.45 * g_term + 0.35 * p_term + 0.20 * m_term
    return float(_clip(conf, 0.0, 1.0))


def _close_game_shrink(margin: float, conf: float, cfg: ShrinkConfig, enabled: bool) -> float:
    if not enabled:
        return float(margin)
    shrink = cfg.shrink_strength * (1.0 - conf)
    return float(margin * (1.0 - shrink))


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

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.sort_values([date_col, gameid_col]).reset_index(drop=True)

    elo = EloState(EloConfig())
    score = ScoreState(ScoreConfig())

    blow_cfg = BlowoutConfig()
    blend_cfg = BlendConfig()
    shrink_cfg = ShrinkConfig()

    rows = []

    for _, r in df.iterrows():
        season = str(r[season_col]).strip()
        gender = str(r[gender_col]).strip().title()
        home = str(r[home_col]).strip()
        away = str(r[away_col]).strip()

        hs = r[hs_col]
        ars = r[as_col]
        if pd.isna(hs) or pd.isna(ars):
            continue

        hs = float(hs)
        ars = float(ars)

        p_home_elo, margin_elo_pts, elo_diff = elo.predict(season, gender, home, away)

        gh = score.get_games(season, gender, home)
        ga = score.get_games(season, gender, away)

        strength_gap = score.team_strength(season, gender, home) - score.team_strength(season, gender, away)

        is_blowout = False
        if blow_cfg.enabled:
            if gh >= blow_cfg.min_games_each and ga >= blow_cfg.min_games_each:
                if abs(elo_diff) >= blow_cfg.elo_diff_threshold and abs(strength_gap) >= blow_cfg.strength_gap_threshold:
                    is_blowout = True

        total_blend_override = blow_cfg.total_blend_when_blowout if is_blowout else None
        clamp_team_max_override = blow_cfg.clamp_team_max_when_blowout if is_blowout else None
        clamp_total_max_override = blow_cfg.clamp_total_max_when_blowout if is_blowout else None

        mu_h, mu_a, total_pred = score.predict_scores(
            season,
            gender,
            home,
            away,
            total_blend_override=total_blend_override,
            clamp_team_max_override=clamp_team_max_override,
            clamp_total_max_override=clamp_total_max_override,
        )
        margin_score = float(mu_h - mu_a)

        w_score = _blend_weight(gh, ga, blend_cfg)
        margin_blend = float(w_score * margin_score + (1.0 - w_score) * margin_elo_pts)

        conf = _confidence_score(p_home_elo, margin_blend, gh, ga)

        shrink_enabled = not is_blowout
        margin_final = _close_game_shrink(margin_blend, conf, shrink_cfg, enabled=shrink_enabled)

        pred_total = float(_clip(total_pred, 70.0, (blow_cfg.clamp_total_max_when_blowout if is_blowout else 160.0)))
        pred_home = float((pred_total + margin_final) / 2.0)
        pred_away = float(pred_total - pred_home)

        team_max = blow_cfg.clamp_team_max_when_blowout if is_blowout else 98.0
        pred_home = float(_clip(pred_home, 24.0, team_max))
        pred_away = float(_clip(pred_away, 24.0, team_max))
        pred_total = float(pred_home + pred_away)

        p_from_margin = float(_sigmoid(margin_final / 7.5))
        p_home = float(0.70 * p_home_elo + 0.30 * p_from_margin)

        margin_actual = float(hs - ars)
        total_actual = float(hs + ars)
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
                PredWinProbElo=float(p_home_elo),
                PredMarginHome=float(margin_final),
                PredMarginScore=float(margin_score),
                PredMarginElo=float(margin_elo_pts),
                PredHomeScore=float(pred_home),
                PredAwayScore=float(pred_away),
                PredTotal=float(pred_total),
                Conf=float(conf),
                WeightScore=float(w_score),
                EloDiff=float(elo_diff),
                StrengthGap=float(strength_gap),
                BlowoutMode=bool(is_blowout),
                ActualMarginHome=float(margin_actual),
                ActualTotal=float(total_actual),
                ErrorMargin=float(margin_final - margin_actual),
                ErrorTotal=float(pred_total - total_actual),
                ErrorHomeScore=float(pred_home - hs),
                ErrorAwayScore=float(pred_away - ars),
                AbsErrMargin=float(abs(margin_final - margin_actual)),
                AbsErrTotal=float(abs(pred_total - total_actual)),
                AbsErrHome=float(abs(pred_home - hs)),
                AbsErrAway=float(abs(pred_away - ars)),
                Brier=float(_brier(p_home, y_home)),
                LogLoss=float(_logloss(p_home, y_home)),
            )
        )

        score.update(season, gender, home, away, hs, ars)
        elo.update(season, gender, home, away, hs, ars)

    out = pd.DataFrame(rows)
    out.to_parquet(OUT_EVAL_PATH, index=False)
    print("wrote", OUT_EVAL_PATH, "rows", len(out))


if __name__ == "__main__":
    main()
