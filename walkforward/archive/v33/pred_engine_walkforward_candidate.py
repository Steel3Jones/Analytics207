from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# Optional: for online Bradley–Terry via logistic regression
try:
    from sklearn.linear_model import SGDClassifier
    SKLEARN_OK = True
except Exception:
    SGDClassifier = None
    SKLEARN_OK = False


# ======================================================================================
# CANDIDATE ENGINE: Bradley–Terry winprob (Boys/Girls separate)
# - Stable output schema for pages/nightly
# - WinProb: Bradley–Terry (online logistic, team parameters)
# - Scores/Margin/Total: simple baseline score engine (placeholder)
# ======================================================================================

ENGINEVERSION = "CAND_BT_20260216_01_FIXDIM"
ROOT = Path(r"C:\ANALYTICS207")

GAMESPATH = ROOT / "data" / "core" / "games_game_core_v40.parquet"
OUTPATH = ROOT / "data" / "predictions" / "games_predictions_current.parquet"

GENDER_COL = "Gender"
GIRLS_TOTAL_BIAS = 26.278252430827177  # keep your known correction


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def clean_str(x: object) -> str:
    return str(x).strip()


def score_engine_simple(
    strength_diff: float,
    is_neutral: bool,
    base_total: float = 95.0,
    home_adv: float = 2.5,
    margin_scale: float = 0.30,
    clamp_team_max: float = 82.0,
    clamp_total_max: float = 155.0,
) -> Tuple[float, float, float, float]:
    """
    Simple, stable score engine: (margin from strength_diff) + (total baseline).
    This is NOT Bradley–Terry; it's just to keep required output columns stable.
    """
    pm = float(margin_scale) * float(strength_diff)
    pt = float(base_total) + abs(pm)

    if not bool(is_neutral):
        pm = float(pm) + float(home_adv)

    pt = clamp(pt, 80.0, clamp_total_max)

    ph = pt / 2.0 + pm / 2.0
    pa = pt / 2.0 - pm / 2.0

    ph = clamp(ph, 40.0, clamp_team_max)
    pa = clamp(pa, 35.0, clamp_team_max)

    pt = float(ph) + float(pa)
    pm = float(ph) - float(pa)
    return ph, pa, pm, pt


class BTOnline:
    """
    Bradley–Terry as an online logistic regression with one parameter per team,
    implemented via SGDClassifier over a FIXED feature map.

    Feature design:
      x[home_team] = +1
      x[away_team] = -1
      x["__HOME_ADV__"] = +1  (0 on neutral)
    """
    HOME_ADV_KEY = "__HOME_ADV__"

    def __init__(self, teams: List[str], l2_alpha: float = 5e-4, random_state: int = 7) -> None:
        self.l2_alpha = float(l2_alpha)
        self.random_state = int(random_state)

        uniq = sorted({clean_str(t) for t in teams if clean_str(t) != ""})
        self.idx: Dict[str, int] = {t: i for i, t in enumerate(uniq)}
        self.idx[self.HOME_ADV_KEY] = len(self.idx)

        self.model = None
        self.ready = False
        self._classes = np.array([0, 1], dtype=int)

        if SKLEARN_OK:
            self.model = SGDClassifier(
                loss="log_loss",
                penalty="l2",
                alpha=self.l2_alpha,
                learning_rate="optimal",
                fit_intercept=False,  # explicit home-adv feature
                max_iter=1,
                tol=None,
                random_state=self.random_state,
            )

    def _vectorize(self, feats: Dict[str, float]) -> np.ndarray:
        x = np.zeros((1, len(self.idx)), dtype=float)
        for k, v in feats.items():
            j = self.idx.get(str(k), None)
            if j is None:
                continue
            x[0, j] = float(v)
        return x

    def predict_proba_home(self, home: str, away: str, is_neutral: bool) -> float:
        if not SKLEARN_OK or self.model is None or (not self.ready):
            return 0.5

        feats = {
            clean_str(home): 1.0,
            clean_str(away): -1.0,
            self.HOME_ADV_KEY: 0.0 if bool(is_neutral) else 1.0,
        }
        x = self._vectorize(feats)
        p = float(self.model.predict_proba(x)[0, 1])
        return float(clamp(p, 1e-6, 1.0 - 1e-6))

    def update(self, home: str, away: str, is_neutral: bool, y_home_win: int) -> None:
        if not SKLEARN_OK or self.model is None:
            return

        feats = {
            clean_str(home): 1.0,
            clean_str(away): -1.0,
            self.HOME_ADV_KEY: 0.0 if bool(is_neutral) else 1.0,
        }
        x = self._vectorize(feats)
        y = np.array([int(y_home_win)], dtype=int)

        if not self.ready:
            self.model.partial_fit(x, y, classes=self._classes)
            self.ready = True
        else:
            self.model.partial_fit(x, y)

    def get_team_strengths(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        if not SKLEARN_OK or self.model is None or (not self.ready):
            return out

        coef = self.model.coef_.ravel()
        for team, j in self.idx.items():
            if team == self.HOME_ADV_KEY:
                continue
            out[team] = float(coef[j])
        return out

    def get_home_adv(self) -> float:
        if not SKLEARN_OK or self.model is None or (not self.ready):
            return 0.0
        coef = self.model.coef_.ravel()
        j = self.idx.get(self.HOME_ADV_KEY, None)
        return float(coef[j]) if j is not None else 0.0


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

    # Clean string keys
    games["GameID"] = games["GameID"].astype(str).str.strip()
    games["HomeKey"] = games["HomeKey"].astype(str).str.strip()
    games["AwayKey"] = games["AwayKey"].astype(str).str.strip()
    games[GENDER_COL] = games[GENDER_COL].astype(str).str.strip().str.title()

    build_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")

    # Prebuild fixed feature spaces per gender (prevents sklearn feature-count crash)
    boys = games.loc[games[GENDER_COL] == "Boys", ["HomeKey", "AwayKey"]]
    girls = games.loc[games[GENDER_COL] == "Girls", ["HomeKey", "AwayKey"]]

    boys_teams = pd.unique(pd.concat([boys["HomeKey"], boys["AwayKey"]], ignore_index=True)).tolist()
    girls_teams = pd.unique(pd.concat([girls["HomeKey"], girls["AwayKey"]], ignore_index=True)).tolist()

    bt_boys = BTOnline(teams=boys_teams, l2_alpha=5e-4, random_state=7)
    bt_girls = BTOnline(teams=girls_teams, l2_alpha=5e-4, random_state=11)

    rows: List[dict] = []

    for _, g in games.iterrows():
        gid = clean_str(g["GameID"])
        home = clean_str(g["HomeKey"])
        away = clean_str(g["AwayKey"])
        is_neutral = bool(g.get("IsNeutral", False))
        gender = clean_str(g.get(GENDER_COL, "")).title()

        bt = bt_girls if gender == "Girls" else bt_boys

        # Predict winprob from BT
        p_home = bt.predict_proba_home(home, away, is_neutral)

        # Strength diff proxy for score engine
        strengths = bt.get_team_strengths()
        s_home = float(strengths.get(home, 0.0))
        s_away = float(strengths.get(away, 0.0))
        strength_diff = s_home - s_away

        # Predict scores/margin/total
        ph, pa, pm, pt = score_engine_simple(
            strength_diff=strength_diff,
            is_neutral=is_neutral,
            base_total=95.0,
            home_adv=2.5,
            margin_scale=25.0,  # BT weights are small; scale to points-ish
            clamp_team_max=82.0,
            clamp_total_max=155.0,
        )

        # Girls total correction
        if gender == "Girls":
            pt = float(pt) - float(GIRLS_TOTAL_BIAS)
            ph = float(pt) / 2.0 + float(pm) / 2.0
            pa = float(pt) / 2.0 - float(pm) / 2.0
            ph = clamp(ph, 40.0, 82.0)
            pa = clamp(pa, 35.0, 82.0)
            pt = float(ph) + float(pa)
            pm = float(ph) - float(pa)

        pred_home_wins = bool(p_home >= 0.5)
        pred_winner_key = home if pred_home_wins else away
        pred_loser_key = away if pred_home_wins else home
        pred_winner_prob = float(p_home) if pred_home_wins else float(1.0 - p_home)

        # Walk-forward update on played games only
        home_score = pd.to_numeric(g.get("HomeScore", pd.NA), errors="coerce")
        away_score = pd.to_numeric(g.get("AwayScore", pd.NA), errors="coerce")
        played = pd.notna(home_score) and pd.notna(away_score)

        if played:
            y_home = 1 if float(home_score - away_score) > 0 else 0
            bt.update(home, away, is_neutral, y_home)
            result_home_win = y_home
        else:
            result_home_win = pd.NA

        rows.append(
            {
                "GameID": gid,
                "HomeKey": home,
                "AwayKey": away,
                "PredHomeWinProb": float(p_home),
                "PredHomeScore": float(ph),
                "PredAwayScore": float(pa),
                "PredMargin": float(pm),
                "PredTotalPoints": float(pt),
                "PredWinnerKey": pred_winner_key,
                "PredLoserKey": pred_loser_key,
                "PredWinnerProb": float(pred_winner_prob),
                "PredWinnerProbPct": float(100.0 * pred_winner_prob),
                "PredSpreadAbs": float(abs(pm)),
                "CoreVersion": ENGINEVERSION,
                "PredBuildID": build_id,

                # --- v40 schema contract placeholders (required by nightly) ---
                "EloDiff": 0.0,
                "StrengthGap": 0.0,
                "BlowoutMode": False,
                "SecondMeeting": False,
                "FirstMeetingWasBlowout": False,

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
    ]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out.drop_duplicates(subset="GameID", keep="first").reset_index(drop=True)

    if len(out) != len(games):
        raise RuntimeError(f"Candidate BT engine wrote {len(out)} rows but games has {len(games)} rows")

    OUTPATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUTPATH, index=False)
    print(f"Wrote {len(out)} rows to {OUTPATH}")


if __name__ == "__main__":
    main()
