from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timezone
import os

import numpy as np
import pandas as pd

# Optional: online logistic win-prob model (walk-forward).
# If sklearn isn't installed, engine falls back to current Elo-prob method.
try:
    from sklearn.linear_model import SGDClassifier
    from sklearn.preprocessing import StandardScaler

    SKLEARN_OK = True
except Exception:
    SGDClassifier = None
    StandardScaler = None
    SKLEARN_OK = False



ENGINEVERSION = "v41_walkforward_prod_20260216_winprob_sgd1_girls_totalcal1"
ROOT = Path(r"C:\ANALYTICS207")

GAMESPATH = ROOT / "data" / "core" / "games_game_core_v40.parquet"
OUTPATH = ROOT / "data" / "predictions" / "games_predictions_current.parquet"


def getenv_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "")
    if raw is None or str(raw).strip() == "":
        return float(default)
    try:
        return float(str(raw).strip())
    except Exception:
        return float(default)


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

def _blend(a: float, b: float, w: float) -> float:
    w = float(clamp(float(w), 0.0, 1.0))
    return (1.0 - w) * float(a) + w * float(b)



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
    # ----------------- Rolling points (walk-forward) -----------------
    # Weight: how much to trust "team points for" vs opponent "points against"
    PTS_W_FOR_VS_AG = getenv_float("PTS_W_FOR_VS_AG", 0.00)
    PTS_W_FOR_VS_AG = clamp(PTS_W_FOR_VS_AG, 0.0, 1.0)

    # Per-team rolling histories
    team_pts_for: Dict[str, List[float]] = {}
    team_pts_against: Dict[str, List[float]] = {}

    # League rolling totals (for league average)
    league_pts_for: float = 0.0
    league_n: int = 0

    def _league_avg() -> float:
        # Fallback to score_cfg.base_total/2 until we have played games
        if league_n <= 0:
            return float(score_cfg.base_total) / 2.0
        return float(league_pts_for) / float(league_n)

    def _team_for(team: str) -> float:
        xs = team_pts_for.get(team, [])
        if not xs:
            return _league_avg()
        return float(np.mean(xs))

    def _team_against(team: str) -> float:
        xs = team_pts_against.get(team, [])
        if not xs:
            return _league_avg()
        return float(np.mean(xs))

    def _shrunk(x: float, n: int, league_avg: float, k: float = 6.0) -> float:
        # Shrink toward league average when sample size is small
        n = int(n)
        if n <= 0:
            return float(league_avg)
        w = float(n) / float(n + float(k))
        return (1.0 - w) * float(league_avg) + w * float(x)
    # -----------------------------------------------------------------

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

    # WP blend alpha: default in code, override via env var
    alpha = getenv_float("WPBLENDALPHA", getenv_float("WP_BLEND_ALPHA", 0.20))
    alpha = clamp(alpha, 0.0, 0.60)


    # Rolling calibration store (favorite prob, favorite outcome), walk-forward
    N_WINDOW = 1500
    MIN_FIT = 300
    calib_p: List[float] = []
    calib_y: List[float] = []
    platt_a, platt_b = 0.0, 1.0

    # ----------------- W/L-first win-prob model (walk-forward) -----------------
    WP_MIN_FIT = 250  # don't trust model until it has some data
    wp_ready = False

    if SKLEARN_OK:
        wp_scaler = StandardScaler(with_mean=True, with_std=True)
        wp_model = SGDClassifier(
            loss="log_loss",
            penalty="l2",
            alpha=1e-3,
            learning_rate="optimal",
            fit_intercept=True,
            max_iter=1,
            tol=None,
            random_state=7,
        )
        wp_classes = np.array([0, 1], dtype=int)
    else:
        wp_scaler = None
        wp_model = None
        wp_classes = None
    # --------------------------------------------------------------------------

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
            is_neutral=is_neutral,
            cfg=score_cfg,
        )

        # --------- Upgrade TOTAL/POINTS using rolling For/Against (walk-forward) ---------
        league_avg = _league_avg()

        hf_hist = team_pts_for.get(home, [])
        ha_hist = team_pts_against.get(home, [])
        af_hist = team_pts_for.get(away, [])
        aa_hist = team_pts_against.get(away, [])

        home_for = _shrunk(_team_for(home), len(hf_hist), league_avg)
        home_ag  = _shrunk(_team_against(home), len(ha_hist), league_avg)
        away_for = _shrunk(_team_for(away), len(af_hist), league_avg)
        away_ag  = _shrunk(_team_against(away), len(aa_hist), league_avg)

        # Predict team points (simple symmetric blend)
        pred_home_pts = _blend(home_for, away_ag, PTS_W_FOR_VS_AG)
        pred_away_pts = _blend(away_for, home_ag, PTS_W_FOR_VS_AG)

        # Home-court: split across the two teams to keep totals stable
        if not bool(is_neutral):
            pred_home_pts = float(pred_home_pts) + float(score_cfg.home_adv) / 2.0
            pred_away_pts = float(pred_away_pts) - float(score_cfg.home_adv) / 2.0

        pt_new = float(pred_home_pts) + float(pred_away_pts)

        # Clamp total similar to prior logic
        total_cap = float(score_cfg.blowout_total_max if blowout else score_cfg.clamp_total_max)
        pt_new = float(clamp(pt_new, 80.0, total_cap))

        # Recompute scores from (new total, SAME margin pm)
        ph = float(pt_new) / 2.0 + float(pm) / 2.0
        pa = float(pt_new) / 2.0 - float(pm) / 2.0

        team_cap = float(score_cfg.blowout_team_max if blowout else score_cfg.clamp_team_max)
        ph = float(clamp(ph, 40.0, team_cap))
        pa = float(clamp(pa, 35.0, team_cap))
        pt = float(ph) + float(pa)
        pm = float(ph) - float(pa)  # keep internal consistency after clamps
        # -------------------------------------------------------------------------------

# -------------------------------------------------------------------------------




        # ----------------- Girls score/total calibration -----------------
        # Fix systematic Girls total bias by shifting total downward, then
        # recompute component scores so total stays consistent with margin.
        if gender == "Girls":
            pt = float(pt) - float(GIRLS_TOTAL_BIAS)

            

            ph = float(pt) / 2.0 + float(pm) / 2.0
            pa = float(pt) / 2.0 - float(pm) / 2.0

            teamcap = float(score_cfg.blowout_team_max) if blowout else score_cfg.clamp_team_max
            totalcap = float(score_cfg.blowout_total_max) if blowout else score_cfg.clamp_total_max

            pt = clamp(float(pt), 80.0, totalcap)
            ph = clamp(float(ph), 40.0, teamcap)
            pa = clamp(float(pa), 35.0, teamcap)

            pm = float(ph) - float(pa)
            pt = float(ph) + float(pa)

        # ---------------------------------------------------------------

        home_score = pd.to_numeric(g.get("HomeScore", pd.NA), errors="coerce")
        away_score = pd.to_numeric(g.get("AwayScore", pd.NA), errors="coerce")
        played = pd.notna(home_score) and pd.notna(away_score)

        

        # ----------------- Win probability (W/L-first) -----------------
        # Baseline (your current Elo mapping)
        ELO_PROB_MULT = 4.9
        baseline = float(elo_expected(ELO_PROB_MULT * elo_diff))
        baseline = float(clamp(baseline, 1e-6, 1.0 - 1e-6))

        # Feature vector (no leakage; all known pre-game)
        x = np.array(
            [
                [
                    float(elo_diff),
                    0.0 if bool(is_neutral) else 1.0,  # home indicator
                    float(strength_gap),
                ]
            ],
            dtype=float,
        )

        
        # Use learned model after warmup; otherwise baseline (blend when available)
        if SKLEARN_OK and wp_ready and (len(calib_y) >= WP_MIN_FIT):
            xs = wp_scaler.transform(x)
            p_sgd = float(wp_model.predict_proba(xs)[0, 1])
            p_elo = baseline
            winprob_home_raw = (1.0 - alpha) * p_elo + alpha * p_sgd
        else:
            winprob_home_raw = baseline

        winprob_home_raw = float(clamp(winprob_home_raw, 1e-6, 1.0 - 1e-6))

        # Keep Platt layer for now (we can A/B removing it later)
        if len(calib_p) >= MIN_FIT:
            winprob_home = _platt_apply(winprob_home_raw, platt_a, platt_b)
        else:
            winprob_home = winprob_home_raw
        # --------------------------------------------------------------

        # W/L-first: predicted winner comes from win probability
        pred_home_wins = bool(winprob_home >= 0.5)
        pred_winner_key = home if pred_home_wins else away
        pred_loser_key = away if pred_home_wins else home
        pred_winner_prob = float(winprob_home) if pred_home_wins else float(1.0 - winprob_home)

        if played:
            actual_margin = float(home_score - away_score)
            result_home_win = 1 if actual_margin > 0 else 0

            # Update rolling points model (walk-forward; only after game is played)
            hs = float(home_score)
            as_ = float(away_score)

            team_pts_for.setdefault(home, []).append(hs)
            team_pts_against.setdefault(home, []).append(as_)
            team_pts_for.setdefault(away, []).append(as_)
            team_pts_against.setdefault(away, []).append(hs)

            league_pts_for += hs + as_
            league_n += 2

            hist.append({"IsBlowout": abs(actual_margin) >= 30})
            matchup_history[key] = hist

            # -------- walk-forward train/update of win-prob model --------
            if SKLEARN_OK:
                y = np.array([int(result_home_win)], dtype=int)

                if not wp_ready:
                    wp_scaler.partial_fit(x)
                    xs = wp_scaler.transform(x)
                    wp_model.partial_fit(xs, y, classes=wp_classes)
                    wp_ready = True
                    print("WP READY FLIPPED TRUE at GameID:", gid)  # TEMP DEBUG
                else:
                    wp_scaler.partial_fit(x)
                    xs = wp_scaler.transform(x)
                    wp_model.partial_fit(xs, y)
            # -------------------------------------------------------------

            update_elo(home, away, result_home_win)
            team_games[home] += 1
            team_games[away] += 1

            # Add calibration sample (favorite-based, using RAW prob as the uncalibrated score)
            fav_is_home = winprob_home_raw >= 0.5
            fav_prob = winprob_home_raw if fav_is_home else (1.0 - winprob_home_raw)
            fav_won = (
                1.0
                if ((fav_is_home and actual_margin > 0) or ((not fav_is_home) and actual_margin < 0))
                else 0.0
            )

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
        raise RuntimeError(f"v41 engine wrote {len(out)} rows but games has {len(games)} rows")

    OUTPATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUTPATH, index=False)
    print(f"Wrote {len(out)} rows to {OUTPATH}")


if __name__ == "__main__":
    main()

