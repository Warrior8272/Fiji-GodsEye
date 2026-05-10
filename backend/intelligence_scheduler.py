import threading
import time

SCHEDULER_STATE = {
    "running": False,
    "last_run": None,
    "runs": 0,
    "error": None
}

def start_intelligence_scheduler(task, interval=60):
    if SCHEDULER_STATE["running"]:
        return

    SCHEDULER_STATE["running"] = True

    def loop():
        while True:
            try:
                task()
                SCHEDULER_STATE["last_run"] = time.time()
                SCHEDULER_STATE["runs"] += 1
                SCHEDULER_STATE["error"] = None
            except Exception as e:
                SCHEDULER_STATE["error"] = str(e)

            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()

def get_scheduler_state():
    return SCHEDULER_STATE
