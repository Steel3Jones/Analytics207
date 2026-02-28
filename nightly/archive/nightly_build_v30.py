# C:\ANALYTICS207\nightly\nightly_build_v30.py

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(r"C:\ANALYTICS207")
DATA_DIR = ROOT / "data"

TRUTH_PATH = DATA_DIR / "truth.csv"

# Core v30 outputs
TEAMS_OUT = DATA_DIR / "teams_team_season_core_v30.parquet"
GAMES_OUT = DATA_DIR / "games_game_core_v30.parquet"

# Performance outputs
PERF_SUMMARY_OUT = DATA_DIR / "performance_summary_v30.parquet"
PERF_GAMES_OUT = DATA_DIR / "performance_games_v30.parquet"
PERF_CALIB_OUT = DATA_DIR / "performance_calibration_v30.parquet"
PERF_SPREAD_OUT = DATA_DIR / "performance_by_spread_v30.parquet"

# New prediction outputs (walk forward)
PRED_GAMES_OUT = DATA_DIR / "games_predictions_v30.parquet"
PRED_EVAL_OUT = DATA_DIR / "model_eval_v30.parquet"

# Make imports stable: allow "from core.core_v30 import ..."
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.core_v30 import build_core_v30, build_performance_tables_v30  # type: ignore
from core.predict_v30 import build_predictions_walkforward_v30  # type: ignore


def _atomic_write_parquet(df, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet", dir=str(out_path.parent)) as tmp:
        tmp_path = Path(tmp.name)
    df.to_parquet(tmp_path, index=False)
    tmp_path.replace(out_path)


def main() -> None:
    if not TRUTH_PATH.exists():
        raise FileNotFoundError(
            f"Missing truth file: {TRUTH_PATH}\n"
            f"Fix: put your ONE truth CSV at {TRUTH_PATH} (exact name)."
        )

    # Core v30 build: teams (team season) and games (rich game table)
    teams, games = build_core_v30(TRUTH_PATH)

    # Ensure ProjectedSeed exists for bracketology (TI based seeding)
    if "ProjectedSeed" not in teams.columns:
        import numpy as np
        import pandas as pd

        teams["TI"] = pd.to_numeric(teams.get("TI"), errors="coerce")
        teams["WinPct"] = pd.to_numeric(teams.get("WinPct"), errors="coerce")

        group_cols = [c for c in ["Gender", "Class", "Region", "Season"] if c in teams.columns]

        def _seed_group(g: pd.DataFrame) -> pd.DataFrame:
            g = g.copy()
            g = g.sort_values(["TI", "WinPct"], ascending=[False, False]).reset_index(drop=True)
            g["ProjectedSeed"] = np.arange(1, len(g) + 1)
            return g

        if group_cols:
            teams = (
                teams.groupby(group_cols, dropna=False, group_keys=False)
                .apply(_seed_group)
                .reset_index(drop=True)
            )
        else:
            teams = _seed_group(teams)

    # Write core v30 parquets
    _atomic_write_parquet(teams, TEAMS_OUT)
    _atomic_write_parquet(games, GAMES_OUT)

    # Build walk forward prediction tables
    pred_games, pred_eval = build_predictions_walkforward_v30(games, teams)

    _atomic_write_parquet(pred_games, PRED_GAMES_OUT)
    _atomic_write_parquet(pred_eval, PRED_EVAL_OUT)

    # Build performance tables from games
    perf_summary, perf_games, perf_calib, perf_spread = build_performance_tables_v30(games)

    # Write performance v30 parquets
    _atomic_write_parquet(perf_summary, PERF_SUMMARY_OUT)
    _atomic_write_parquet(perf_games, PERF_GAMES_OUT)
    _atomic_write_parquet(perf_calib, PERF_CALIB_OUT)
    _atomic_write_parquet(perf_spread, PERF_SPREAD_OUT)

    print(f"Wrote {len(teams)} teams to {TEAMS_OUT}")
    print(f"Wrote {len(games)} games to {GAMES_OUT}")
    print(f"Wrote {len(pred_games)} predicted game rows to {PRED_GAMES_OUT}")
    print(f"Wrote {len(pred_eval)} eval rows to {PRED_EVAL_OUT}")
    print(f"Wrote v30 performance summary to {PERF_SUMMARY_OUT}")
    print(f"Wrote v30 performance games to {PERF_GAMES_OUT}")
    print(f"Wrote v30 calibration to {PERF_CALIB_OUT}")
    print(f"Wrote v30 performance by spread to {PERF_SPREAD_OUT}")


if __name__ == "__main__":
    main()
