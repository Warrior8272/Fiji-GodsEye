from datetime import datetime, timedelta
import json
import os

AIS_FILE = "ais_live.json"

CACHE_FILE = "dark_activity_cache.json"

DARK_THRESHOLD_MINUTES = 30

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def process_dark_activity():

    vessels = load_json(AIS_FILE, [])

    cache = load_json(CACHE_FILE, {})

    now = datetime.utcnow()

    alerts = []

    active_mmsi = set()

    for vessel in vessels:

        mmsi = str(vessel.get("mmsi"))

        if not mmsi:
            continue

        active_mmsi.add(mmsi)

        cache[mmsi] = {
            "last_seen": now.isoformat(),
            "name": vessel.get("shipname", "UNKNOWN"),
            "lat": vessel.get("lat"),
            "lon": vessel.get("lon")
        }

    for mmsi, info in cache.items():

        try:
            last_seen = datetime.fromisoformat(info["last_seen"])

            delta = now - last_seen

            if delta > timedelta(minutes=DARK_THRESHOLD_MINUTES):

                alerts.append({
                    "type": "DARK_ACTIVITY",
                    "risk": "HIGH",
                    "mmsi": mmsi,
                    "vessel": info.get("name"),
                    "minutes_dark": int(delta.total_seconds() / 60),
                    "last_position": {
                        "lat": info.get("lat"),
                        "lon": info.get("lon")
                    },
                    "msg": f"Vessel AIS silence detected for {int(delta.total_seconds()/60)} minutes"
                })

        except:
            pass

    save_json(CACHE_FILE, cache)

    return alerts
