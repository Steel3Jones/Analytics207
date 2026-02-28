from pathlib import Path
from core.core_v30 import build_core_v30

ROOT = Path(r"C:\ANALYTICS207")
DATA_DIR = ROOT / "data"

TRUTH_PATH = DATA_DIR / "truth.csv"
TEAMS_OUT = DATA_DIR / "teams_team_season_core_v30.parquet"
GAMES_OUT = DATA_DIR / "games_game_core_v30.parquet"

def main() -> None:
    teams_core, games_core = build_core_v30(TRUTH_PATH)

    print("run_core_v30_once: Has Gender?", "Gender" in teams_core.columns)
    print("run_core_v30_once: Has Class?", "Class" in teams_core.columns)
    print("run_core_v30_once: Has Region?", "Region" in teams_core.columns)
    print("run_core_v30_once: Has Season?", "Season" in teams_core.columns)

    teams_core.to_parquet(TEAMS_OUT, index=False)
    games_core.to_parquet(GAMES_OUT, index=False)

    print(f"run_core_v30_once: Wrote {len(teams_core)} teams to {TEAMS_OUT}")
    print(f"run_core_v30_once: Wrote {len(games_core)} games to {GAMES_OUT}")

if __name__ == "__main__":
    main()
