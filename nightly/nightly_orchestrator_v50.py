from __future__ import annotations

# ======================================================================================
#-----------------HEADER: Imports & Constants
# ======================================================================================

import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\ANALYTICS207")
DATADIR = ROOT / "data"
BACKUPDIR = ROOT / "backup"
LOGSDIR = ROOT / "logs"
SCRAPERSDIR = ROOT / "scrapers"
TRUTHPATH = DATADIR / "truth.csv"

#-----------------FOOTER: Imports & Constants
# ======================================================================================


# ======================================================================================
#-----------------HEADER: Helpers
# ======================================================================================

def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd or ROOT))
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


def backup_pre_run(timestamp: str) -> Path:
    dest = BACKUPDIR / f"{timestamp}__pre"
    dest.mkdir(parents=True, exist_ok=True)
    for src in [DATADIR / "truth.csv", DATADIR / "games_predictions_current.parquet"]:
        if src.exists():
            shutil.copy2(src, dest / src.name)
    print(f"Pre-run backup at: {dest}")
    return dest


def backup_post_scrape(timestamp: str) -> Path:
    dest = BACKUPDIR / f"{timestamp}__post_scrape"
    dest.mkdir(parents=True, exist_ok=True)
    for src in [DATADIR / "truth.csv"]:
        if src.exists():
            shutil.copy2(src, dest / src.name)
    print(f"Post-scrape backup at: {dest}")
    return dest

#-----------------FOOTER: Helpers
# ======================================================================================


# ======================================================================================
#-----------------HEADER: Main
# ======================================================================================

def main() -> None:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    LOGSDIR.mkdir(exist_ok=True)
    BACKUPDIR.mkdir(exist_ok=True)

    logfile = LOGSDIR / f"nightly_v50_{ts}.log"
    sys.stdout = open(logfile, "w", buffering=1, encoding="utf-8")
    sys.stderr = sys.stdout

    print("NIGHTLY ORCHESTRATOR V50 START", ts)

    try:
        backup_pre_run(ts)

        print("1) Running scrapers pipeline to build data/truth.csv")
        run_cmd([sys.executable, "MPA_SCRAPER_V50.py"],        cwd=SCRAPERSDIR)
        run_cmd([sys.executable, "MPA_SCORES_SCRAPER_V50.py"], cwd=SCRAPERSDIR)
        run_cmd([sys.executable, "JOIN_SCORES_V50.py"],        cwd=SCRAPERSDIR)
        run_cmd([sys.executable, "FIX_HOME_AWAY_TEAM_NAMES.py"], cwd=SCRAPERSDIR)

        backup_post_scrape(ts)

        if not TRUTHPATH.exists():
            raise FileNotFoundError(f"Expected truth file not found at {TRUTHPATH}")

        print("2) Running nightly_v50 build")
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))

        from nightly.nightly_v50 import main as run_build  # type: ignore
        run_build()

        print("3) Running postseason bracket scrape")
        run_cmd([sys.executable, "scrape_postseason.py"], cwd=SCRAPERSDIR)

        print("NIGHTLY ORCHESTRATOR V50 SUCCESS")
        sys.exit(0)

    except Exception as e:
        print("NIGHTLY ORCHESTRATOR V50 FAILED")
        print("ERROR:", e)
        sys.exit(1)

#-----------------FOOTER: Main
# ======================================================================================

if __name__ == "__main__":
    main()
