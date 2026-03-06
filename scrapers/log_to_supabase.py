#!/usr/bin/env python3
"""
log_to_supabase.py
------------------
Drop this file into your C:\\ANALYTICS207\\scrapers\\ folder.

Usage in nightly_orchestrator_v50.py:
    from log_to_supabase import log_scraper_run, log_orchestrator_run

Call it after each scraper step completes or fails.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional
from supabase import create_client

# ── Same credentials as your auth.py ──────────────────────────────────────────
SUPABASE_URL = "https://lofxbafahfogptdkjhhv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxvZnhiYWZhaGZvZ3B0ZGtqaGh2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIzMDAwMjAsImV4cCI6MjA4Nzg3NjAyMH0.KaC9gKZWG9fvjzuH8exf4_5rp28JGLHYY-6QCUOScuc"

def _get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def log_scraper_run(
    scraper_name: str,
    status: str,                        # "success" | "failed" | "partial"
    records_processed: int = 0,
    error_message: Optional[str] = None,
    duration_seconds: int = 0,
    log_output: Optional[str] = None,
) -> None:
    """
    Write one row to scraper_logs in Supabase.
    Silently swallows errors so a logging failure never kills your pipeline.
    """
    try:
        sb = _get_client()
        sb.table("scraper_logs").insert({
            "scraper_name":      scraper_name,
            "status":            status,
            "records_processed": records_processed,
            "error_message":     error_message,
            "duration_seconds":  duration_seconds,
            "ran_at":            datetime.now(timezone.utc).isoformat(),
        }).execute()
        print(f"  [log_to_supabase] ✓ Logged {scraper_name} → {status}")
    except Exception as e:
        print(f"  [log_to_supabase] ⚠ Could not log to Supabase: {e}")


def timed_step(scraper_name: str, fn, *args, **kwargs):
    """
    Helper: run fn(*args, **kwargs), time it, log result automatically.

    Example:
        timed_step("MPA_SCRAPER_V50", run_cmd,
                   [sys.executable, "MPA_SCRAPER_V50.py"], cwd=SCRAPERSDIR)
    """
    start = time.time()
    try:
        result = fn(*args, **kwargs)
        duration = int(time.time() - start)
        log_scraper_run(scraper_name, "success", duration_seconds=duration)
        return result
    except Exception as e:
        duration = int(time.time() - start)
        log_scraper_run(
            scraper_name,
            "failed",
            error_message=str(e),
            duration_seconds=duration,
        )
        raise  # re-raise so orchestrator still catches it


# ── Convenience: log the whole orchestrator run ────────────────────────────────
def log_orchestrator_run(status: str, error_message: Optional[str] = None, duration_seconds: int = 0) -> None:
    log_scraper_run(
        scraper_name="NIGHTLY_ORCHESTRATOR",
        status=status,
        error_message=error_message,
        duration_seconds=duration_seconds,
    )


if __name__ == "__main__":
    print("Testing Supabase connection...")
    log_scraper_run("TEST", "success", records_processed=42, duration_seconds=5)
    print("Done! Check your scraper_logs table in Supabase.")

