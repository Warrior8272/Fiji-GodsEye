import json
import os
from datetime import datetime

DB_FILE = "vessel_timeline.json"


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


def update_vessel_timeline(vessels):
    db = load_db()
    now = datetime.utcnow().isoformat()

    for vessel in vessels:
        mmsi = str(vessel.get("mmsi", ""))

        if not mmsi:
            continue

        event = {
            "timestamp": now,
            "shipname": vessel.get("shipname", "UNKNOWN"),
            "lat": vessel.get("lat"),
            "lon": vessel.get("lon"),
            "speed": vessel.get("speed"),
            "course": vessel.get("course"),
            "zone": vessel.get("zone_name"),
            "risk": vessel.get("risk", 0),
            "risk_flags": vessel.get("risk_flags", [])
        }

        if mmsi not in db:
            db[mmsi] = []

        db[mmsi].append(event)

        # Keep only latest 100 timeline events per vessel
        db[mmsi] = db[mmsi][-100:]

    save_db(db)

    return db


def get_vessel_timeline(mmsi):
    db = load_db()
    return db.get(str(mmsi), [])
