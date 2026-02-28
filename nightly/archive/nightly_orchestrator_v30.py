from __future__ import annotations

import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path


# Root and key dirs
ROOT = Path(r"C:\ANALYTICS207")
DATA_DIR = ROOT / "data"
BACKUP_DIR = ROOT / "backup"
LOGS_DIR = ROOT / "logs"
SCRAPERS_DIR = ROOT / "scrapers"

TRUTH_PATH = DATA_DIR / "truth.csv"

# Make imports stable so we can call nightly_build_v34c_prod.main()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nightly.nightly_build_v34c_prod import main as run_v34c_build  # type: ignore


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"\n>>> Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or ROOT)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {' '.join(cmd)}"
        )


def backup_pre_run(timestamp: str) -> Path:
    """
    Backup what's already present BEFORE scraping/building (minimal, not data/).
    """
    dest = BACKUP_DIR / timestamp / "pre"
    dest.mkdir(parents=True, exist_ok=True)

    files_to_backup = [
        DATA_DIR / "truth.csv",
        DATA_DIR / "games_predictions_current.parquet",  # optional rollback artifact
    ]

    backed_up = 0
    for src in files_to_backup:
        if src.exists():
            shutil.copy2(src, dest / src.name)
            backed_up += 1

    print(f"✓ Pre-run backup completed at {dest} ({backed_up} files)")
    return dest


def backup_post_scrape(timestamp: str) -> Path:
    """
    Backup the scraper outputs AFTER scraping/joining/fixing.
    This guarantees you have the exact inputs that powered the build.
    """
    dest = BACKUP_DIR / timestamp / "post_scrape"
    dest.mkdir(parents=True, exist_ok=True)

    files_to_backup = [
        DATA_DIR / "games_raw_v30.csv",
        DATA_DIR / "games_scores_v30.csv",
        DATA_DIR / "truth.csv",
    ]

    backed_up = 0
    for src in files_to_backup:
        if src.exists():
            shutil.copy2(src, dest / src.name)
            backed_up += 1

    print(f"✓ Post-scrape backup completed at {dest} ({backed_up} files)")
    return dest


def main() -> None:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    LOGS_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)

    log_file = LOGS_DIR / f"nightly_v34c_{ts}.log"
    sys.stdout = open(log_file, "w", buffering=1, encoding="utf-8")
    sys.stderr = sys.stdout

    print(f"=== NIGHTLY ORCHESTRATOR V34C START {ts} ===")

    try:
        # (A) Pre-run minimal backup
        backup_pre_run(ts)

        print("\n[1] Running scrapers pipeline to build data/truth.csv")
        run([sys.executable, "MPA_SCRAPER_V25.py"], cwd=SCRAPERS_DIR)
        run([sys.executable, "MPA_SCORE_SCRAPER_V25.py"], cwd=SCRAPERS_DIR)
        run([sys.executable, "join_scores_V25.py"], cwd=SCRAPERS_DIR)

        print("\n[1b] Fixing home/away names in data/truth.csv")
        run([sys.executable, "FIX_HOME_AWAY_TEAM_NAMES.py"], cwd=SCRAPERS_DIR)

        # (A) Post-scrape backup of the generated inputs
        backup_post_scrape(ts)

        if not TRUTH_PATH.exists():
            raise FileNotFoundError(
                f"Expected truth file not found at {TRUTH_PATH}. "
                f"Scrapers/joiner/fixer must create this before build."
            )
        print(f"✓ Found truth file at {TRUTH_PATH}")

        try:
            import pandas as pd

            df_truth = pd.read_csv(TRUTH_PATH)
            total_games = len(df_truth)
            scored_games = (
                df_truth["HomeScore"].notna().sum()
                if "HomeScore" in df_truth.columns
                else 0
            )
            print(
                f"✓ Truth coverage: {scored_games} of {total_games} games "
                f"have non-null HomeScore"
            )
        except Exception as e:
            print(f"Warning: could not run scored-games coverage check: {e}")

        print("\n[2] Running nightly_build_v34c_prod")
        run_v34c_build()
        print("✓ nightly_build_v34c_prod completed")

        print("\n[3] Health checks on data/")

        key_files = [
            DATA_DIR / "teams_team_season_core_v30.parquet",
            DATA_DIR / "games_game_core_v30.parquet",
            DATA_DIR / "games_predictions_current.parquet",
        ]
        for f in key_files:
            if not f.exists():
                raise RuntimeError(f"Missing expected output: {f}")

        try:
            import pandas as pd

            df_pred = pd.read_parquet(DATA_DIR / "games_predictions_current.parquet")
            if "CoreVersion" not in df_pred.columns:
                raise RuntimeError(
                    "games_predictions_current.parquet missing CoreVersion column"
                )

            counts = df_pred["CoreVersion"].astype(str).value_counts()
            print("✓ Current predictions CoreVersion counts:")
            print(counts)

            if len(counts) != 1:
                raise RuntimeError("Current predictions have multiple CoreVersion values")

            only_version = str(counts.index[0])
            if not only_version.startswith("v34c"):
                raise RuntimeError(f"Unexpected CoreVersion: {only_version}")

        except Exception as e:
            raise RuntimeError(
                f"Failed validation of games_predictions_current.parquet: {e}"
            )

        print("✓ Health checks passed")
        print("\n=== NIGHTLY ORCHESTRATOR V34C SUCCESS ===")
        sys.exit(0)

    except Exception as e:
        print("\n=== NIGHTLY ORCHESTRATOR V34C FAILED ===")
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
