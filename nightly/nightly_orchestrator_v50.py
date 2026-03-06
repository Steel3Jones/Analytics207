from __future__ import annotations

# ======================================================================================
# NIGHTLY ORCHESTRATOR V50 — with Supabase logging
# ======================================================================================

import sys
import subprocess
import shutil
import time
from datetime import datetime
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent  # up from nightly\ to C:\ANALYTICS207
DATADIR     = ROOT / "data"
BACKUPDIR   = ROOT / "backup"
LOGSDIR     = ROOT / "logs"
SCRAPERSDIR = ROOT / "scrapers"
NIGHTLYDIR  = ROOT / "nightly"
TRUTHPATH   = DATADIR / "truth.csv"

# Add scrapers and root to path so we can import log_to_supabase and nightly modules
for p in [str(SCRAPERSDIR), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from log_to_supabase import log_scraper_run, log_orchestrator_run


# ======================================================================================
# HELPERS
# ======================================================================================

def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd or ROOT))
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


def run_and_log(scraper_name: str, cmd: list[str], cwd: Path | None = None) -> None:
    """Run a command and log the result to Supabase automatically."""
    start = time.time()
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd or ROOT))
    duration = int(time.time() - start)
    if result.returncode != 0:
        error = f"Exit code {result.returncode}"
        log_scraper_run(scraper_name, "failed", error_message=error, duration_seconds=duration)
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")
    else:
        log_scraper_run(scraper_name, "success", duration_seconds=duration)


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


# ======================================================================================
# MAIN
# ======================================================================================

def main() -> None:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    LOGSDIR.mkdir(exist_ok=True)
    BACKUPDIR.mkdir(exist_ok=True)

    logfile    = LOGSDIR / f"nightly_v50_{ts}.log"
    sys.stdout = open(logfile, "w", buffering=1, encoding="utf-8")
    sys.stderr = sys.stdout

    print("NIGHTLY ORCHESTRATOR V50 START", ts)
    orchestrator_start = time.time()

    try:
        backup_pre_run(ts)

        print("1) Running scrapers pipeline to build data/truth.csv")
        run_and_log("MPA_SCRAPER_V50",          [sys.executable, "MPA_SCRAPER_V50.py"],          cwd=SCRAPERSDIR)
        run_and_log("MPA_SCORES_SCRAPER_V50",   [sys.executable, "MPA_SCORES_SCRAPER_V50.py"],   cwd=SCRAPERSDIR)
        run_and_log("JOIN_SCORES_V50",          [sys.executable, "JOIN_SCORES_V50.py"],          cwd=SCRAPERSDIR)
        run_and_log("FIX_HOME_AWAY_TEAM_NAMES", [sys.executable, "FIX_HOME_AWAY_TEAM_NAMES.py"], cwd=SCRAPERSDIR)

        backup_post_scrape(ts)

        if not TRUTHPATH.exists():
            raise FileNotFoundError(f"Expected truth file not found at {TRUTHPATH}")

        print("2) Running nightly_v50 build")
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))

        build_start = time.time()
        from nightly.nightly_v50 import main as run_build  # type: ignore
        run_build()
        log_scraper_run("NIGHTLY_BUILD_V50", "success", duration_seconds=int(time.time() - build_start))

        print("3) Running postseason bracket scrape")
        run_and_log("SCRAPE_POSTSEASON", [sys.executable, "scrape_postseason.py"], cwd=SCRAPERSDIR)

        print("4) Pushing updated parquets to GitHub")
        run_cmd(["git", "add",    "data/"],                                        cwd=ROOT)
        run_cmd(["git", "commit", "--allow-empty", "-m", f"nightly update {ts}"], cwd=ROOT)
        run_cmd(["git", "push",   "origin", "main"],                               cwd=ROOT)
        log_scraper_run("GIT_PUSH", "success")

        print("5) Scoring stump picks")
        run_and_log("SCORE_STUMP_PICKS",    [sys.executable, "score_stump_picks.py"],    cwd=ROOT / "tools")

        print("6) Scoring survivor picks")
        run_and_log("SCORE_SURVIVOR_PICKS", [sys.executable, "score_survivor_picks.py"], cwd=ROOT / "tools")

        total_duration = int(time.time() - orchestrator_start)
        log_orchestrator_run("success", duration_seconds=total_duration)

        print("NIGHTLY ORCHESTRATOR V50 SUCCESS")
        sys.exit(0)

    except Exception as e:
        total_duration = int(time.time() - orchestrator_start)
        log_orchestrator_run("failed", error_message=str(e), duration_seconds=total_duration)
        print("NIGHTLY ORCHESTRATOR V50 FAILED")
        print("ERROR:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
