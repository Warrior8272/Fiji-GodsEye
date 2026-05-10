from collections import defaultdict

CORRIDORS = [
    ("Fiji Test Zone", "Tonga Watch Zone"),
    ("Tonga Watch Zone", "Samoa Watch Zone"),
    ("Samoa Watch Zone", "Fiji Test Zone"),
    ("Fiji Test Zone", "French Polynesia Corridor"),
]

corridor_memory = defaultdict(lambda: {
    "transits": 0,
    "dark_events": 0,
    "rendezvous_events": 0,
    "repeat_vessels": set(),
})

def process_corridor_activity(vessel):
    history = vessel.get("zone_history", [])
    mmsi = str(vessel.get("mmsi") or vessel.get("id") or "UNKNOWN")

    results = []

    for start, end in CORRIDORS:
        if start in history and end in history:
            key = f"{start} ↔ {end}"

            entry = corridor_memory[key]

            entry["transits"] += 1
            entry["repeat_vessels"].add(mmsi)

            flags = vessel.get("risk_flags", [])

            if not isinstance(flags, list):
                flags = [str(flags)]

            flags_lower = " ".join([str(f).lower() for f in flags])

            if "dark" in flags_lower or "ais blackout" in flags_lower:
                entry["dark_events"] += 1

            if "rendezvous" in flags_lower:
                entry["rendezvous_events"] += 1

            threat_score = (
                entry["transits"] * 2 +
                entry["dark_events"] * 15 +
                entry["rendezvous_events"] * 20 +
                len(entry["repeat_vessels"]) * 5
            )

            if threat_score >= 100:
                threat = "CRITICAL"
            elif threat_score >= 60:
                threat = "HIGH"
            elif threat_score >= 30:
                threat = "MEDIUM"
            else:
                threat = "LOW"

            results.append({
                "corridor": key,
                "threat": threat,
                "threat_score": threat_score,
                "transits": entry["transits"],
                "dark_events": entry["dark_events"],
                "rendezvous_events": entry["rendezvous_events"],
                "repeat_vessels": len(entry["repeat_vessels"])
            })

    return results

def get_corridor_summary():
    results = []

    for key, entry in corridor_memory.items():

        threat_score = (
            entry["transits"] * 2 +
            entry["dark_events"] * 15 +
            entry["rendezvous_events"] * 20 +
            len(entry["repeat_vessels"]) * 5
        )

        if threat_score >= 100:
            threat = "CRITICAL"
        elif threat_score >= 60:
            threat = "HIGH"
        elif threat_score >= 30:
            threat = "MEDIUM"
        else:
            threat = "LOW"

        results.append({
            "corridor": key,
            "threat": threat,
            "threat_score": threat_score,
            "transits": entry["transits"],
            "dark_events": entry["dark_events"],
            "rendezvous_events": entry["rendezvous_events"],
            "repeat_vessels": len(entry["repeat_vessels"])
        })

    results.sort(key=lambda x: x["threat_score"], reverse=True)

    return results
