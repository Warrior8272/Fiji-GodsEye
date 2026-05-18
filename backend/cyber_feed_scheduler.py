#!/usr/bin/env python3

import time
import subprocess
import sys
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INGEST_SCRIPT = os.path.join(BASE_DIR, "ingest_openphish.py")
LOG_FILE = os.path.join(BASE_DIR, "cyber_feed_scheduler.log")

# 30 minutes
INTERVAL_SECONDS = 30 * 60


def log(msg):
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run_ingest():
    log("Starting OpenPhish ingestion run...")

    try:
        result = subprocess.run(
            [sys.executable, INGEST_SCRIPT],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                log("STDOUT: " + line)

        if result.stderr.strip():
            for line in result.stderr.strip().splitlines():
                log("STDERR: " + line)

        log(f"OpenPhish ingestion finished with exit code {result.returncode}")

    except subprocess.TimeoutExpired:
        log("ERROR: OpenPhish ingestion timed out after 120 seconds.")
    except Exception as e:
        log(f"ERROR: Scheduler failed to run ingestion: {e}")


def main():
    log("NAYADRA Phase 17N Cyber Feed Scheduler started.")
    log(f"Interval: {INTERVAL_SECONDS} seconds")
    log(f"Ingest script: {INGEST_SCRIPT}")

    # Run immediately on startup
    run_ingest()

    while True:
        log(f"Sleeping for {INTERVAL_SECONDS} seconds...")
        time.sleep(INTERVAL_SECONDS)
        run_ingest()


if __name__ == "__main__":
    main()
