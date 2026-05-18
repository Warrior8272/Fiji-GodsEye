#!/usr/bin/env python3

import time
import json
import subprocess
import sys
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INGEST_SCRIPT = os.path.join(BASE_DIR, "ingest_openphish.py")
LOG_FILE = os.path.join(BASE_DIR, "cyber_feed_scheduler.log")
HEALTH_FILE = os.path.join(BASE_DIR, "cyber_feed_health.json")

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



def write_health(status="UNKNOWN", added=None, skipped=None, total=None, error=None):
    payload = {
        "status": status,
        "last_check_at": datetime.now(timezone.utc).isoformat(),
        "last_added": added,
        "last_skipped": skipped,
        "total_alerts": total,
        "last_error": error
    }

    try:
        with open(HEALTH_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        log(f"ERROR: Could not write health file: {e}")


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

        added = None
        skipped = None
        total = None

        combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

        for line in combined_output.splitlines():
            if "Added alerts:" in line:
                try:
                    added = int(line.split("Added alerts:")[-1].strip())
                except Exception:
                    pass
            if "Skipped/not relevant or duplicate:" in line:
                try:
                    skipped = int(line.split("Skipped/not relevant or duplicate:")[-1].strip())
                except Exception:
                    pass
            if "Total cyber alerts now:" in line:
                try:
                    total = int(line.split("Total cyber alerts now:")[-1].strip())
                except Exception:
                    pass

        if result.stderr.strip():
            for line in result.stderr.strip().splitlines():
                log("STDERR: " + line)

        if result.returncode == 0:
            write_health(status="OK", added=added, skipped=skipped, total=total, error=None)
        else:
            write_health(status="ERROR", added=added, skipped=skipped, total=total, error=f"Exit code {result.returncode}")

        log(f"OpenPhish ingestion finished with exit code {result.returncode}")

    except subprocess.TimeoutExpired:
        write_health(status="ERROR", error="OpenPhish ingestion timed out after 120 seconds.")
        log("ERROR: OpenPhish ingestion timed out after 120 seconds.")
    except Exception as e:
        write_health(status="ERROR", error=str(e))
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
