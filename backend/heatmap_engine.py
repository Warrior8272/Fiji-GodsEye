from collections import defaultdict

heatmap_cells = defaultdict(lambda: {
    "dark_activity": 0,
    "loitering": 0,
    "rendezvous": 0,
    "repeat_offenders": 0,
    "total_score": 0
})

def grid_key(lat, lon, precision=1):
    try:
        lat = round(float(lat), precision)
        lon = round(float(lon), precision)
        return f"{lat},{lon}"
    except:
        return None

def process_heatmap(vessel):
    lat = vessel.get("lat")
    lon = vessel.get("lon")

    key = grid_key(lat, lon)

    if not key:
        return

    cell = heatmap_cells[key]

    flags = vessel.get("risk_flags", [])
    if not isinstance(flags, list):
        flags = [str(flags)]

    flags_lower = " ".join([str(f).lower() for f in flags])

    if "dark" in flags_lower or "ais blackout" in flags_lower:
        cell["dark_activity"] += 1
        cell["total_score"] += 25

    if "loiter" in flags_lower:
        cell["loitering"] += 1
        cell["total_score"] += 10

    if "rendezvous" in flags_lower:
        cell["rendezvous"] += 1
        cell["total_score"] += 20

    memory = vessel.get("memory", {})

    if memory.get("offender_status") == "PERSISTENT OFFENDER":
        cell["repeat_offenders"] += 1
        cell["total_score"] += 15

def get_heatmap():
    results = []

    for key, cell in heatmap_cells.items():
        try:
            lat, lon = key.split(",")
            lat = float(lat)
            lon = float(lon)
        except:
            continue

        score = cell["total_score"]

        if score >= 100:
            severity = "CRITICAL"
        elif score >= 60:
            severity = "HIGH"
        elif score >= 30:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        results.append({
            "lat": lat,
            "lon": lon,
            "severity": severity,
            "score": score,
            "dark_activity": cell["dark_activity"],
            "loitering": cell["loitering"],
            "rendezvous": cell["rendezvous"],
            "repeat_offenders": cell["repeat_offenders"]
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results
