import json
from pathlib import Path
from datetime import datetime

MEMORY_FILE = Path("vessel_memory.json")

def load_memory():
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text())
        except:
            return {}
    return {}

def save_memory(memory):
    MEMORY_FILE.write_text(json.dumps(memory, indent=2))

def update_vessel_memory(vessel):
    memory = load_memory()

    mmsi = str(
        vessel.get("mmsi")
        or vessel.get("MMSI")
        or vessel.get("id")
        or "UNKNOWN"
    )

    if mmsi not in memory:
        memory[mmsi] = {
            "mmsi": mmsi,
            "first_seen": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
            "event_count": 0,
            "dark_activity_count": 0,
            "loitering_count": 0,
            "rendezvous_count": 0,
            "watch_zone_entries": 0,
            "historical_flags": []
        }

    entry = memory[mmsi]

    entry["last_seen"] = datetime.utcnow().isoformat()
    entry["event_count"] += 1

    flags = vessel.get("risk_flags", [])

    if not isinstance(flags, list):
        flags = [str(flags)]

    for flag in flags:
        if flag not in entry["historical_flags"]:
            entry["historical_flags"].append(flag)

        fl = str(flag).lower()

        if "loiter" in fl:
            entry["loitering_count"] += 1

        if "watch zone" in fl:
            entry["watch_zone_entries"] += 1

        if "rendezvous" in fl:
            entry["rendezvous_count"] += 1

        if "dark" in fl or "ais blackout" in fl:
            entry["dark_activity_count"] += 1

    repeat_score = 0
    repeat_score += entry.get("loitering_count", 0) * 10
    repeat_score += entry.get("dark_activity_count", 0) * 20
    repeat_score += entry.get("rendezvous_count", 0) * 25
    repeat_score += entry.get("watch_zone_entries", 0) * 8
    repeat_score += min(entry.get("event_count", 0), 50)

    entry["repeat_offender_score"] = repeat_score

    if repeat_score >= 100:
        entry["offender_status"] = "PERSISTENT OFFENDER"
    elif repeat_score >= 60:
        entry["offender_status"] = "REPEAT ACTIVITY"
    elif repeat_score >= 25:
        entry["offender_status"] = "MONITORED"
    else:
        entry["offender_status"] = "NEW"

    save_memory(memory)

    return entry
