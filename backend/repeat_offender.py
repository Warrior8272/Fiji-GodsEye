import json
import os
from datetime import datetime

DB_FILE = "repeat_offenders.json"

THRESHOLD = 3


def load_db():

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    return {}


def save_db(data):

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)


def process_repeat_offenders(vessels):

    db = load_db()

    alerts = []

    for vessel in vessels:

        mmsi = str(vessel.get("mmsi", ""))

        if not mmsi:
            continue

        flags = vessel.get("risk_flags", [])

        suspicious = (
            vessel.get("risk", 0) >= 20 or
            "watch_zone" in flags or
            "loitering" in flags
        )

        if not suspicious:
            continue

        if mmsi not in db:

            db[mmsi] = {
                "count": 0,
                "shipname": vessel.get("shipname", "UNKNOWN"),
                "first_seen": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat()
            }

        db[mmsi]["count"] += 1

        db[mmsi]["last_seen"] = datetime.utcnow().isoformat()

        if db[mmsi]["count"] >= THRESHOLD:

            alerts.append({
                "type": "REPEAT_OFFENDER",
                "risk": "HIGH",
                "mmsi": mmsi,
                "vessel": vessel.get("shipname"),
                "offender_count": db[mmsi]["count"],
                "msg": f"Repeat suspicious activity detected ({db[mmsi]['count']} events)"
            })

    save_db(db)

    return alerts
