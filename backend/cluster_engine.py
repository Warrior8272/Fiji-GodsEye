from collections import defaultdict
from datetime import datetime
import math

CLUSTER_MEMORY = defaultdict(lambda: {
    "events": [],
    "vessels": set(),
    "score": 0
})

def haversine_km(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    except:
        return None

    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def detect_clusters(vessels):
    clusters = []
    used = set()

    clean = []
    for v in vessels:
        try:
            if v.get("lat") is not None and v.get("lon") is not None:
                clean.append(v)
        except:
            pass

    for i, a in enumerate(clean):
        if i in used:
            continue

        group = [a]
        used.add(i)

        for j, b in enumerate(clean):
            if j in used:
                continue

            dist = haversine_km(a.get("lat"), a.get("lon"), b.get("lat"), b.get("lon"))
            if dist is None:
                continue

            try:
                a_speed = float(a.get("speed", 0) or 0)
                b_speed = float(b.get("speed", 0) or 0)
            except:
                a_speed = b_speed = 0

            if dist <= 5 and a_speed < 5 and b_speed < 5:
                group.append(b)
                used.add(j)

        if len(group) >= 3:
            vessel_ids = [
                str(v.get("mmsi") or v.get("id") or "UNKNOWN")
                for v in group
            ]

            score = len(group) * 10

            if any(float(v.get("speed", 0) or 0) < 1 for v in group):
                score += 20

            if any(str(v.get("threat_level", "")).upper() in ["HIGH", "CRITICAL"] for v in group):
                score += 30

            if any(v.get("memory", {}).get("offender_status") == "PERSISTENT OFFENDER" for v in group):
                score += 25

            if score >= 90:
                severity = "CRITICAL"
            elif score >= 60:
                severity = "HIGH"
            elif score >= 35:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            key = "::".join(sorted(vessel_ids))[:120]
            entry = CLUSTER_MEMORY[key]
            entry["vessels"].update(vessel_ids)
            entry["score"] += score
            entry["events"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "score": score,
                "severity": severity
            })
            entry["events"] = entry["events"][-25:]

            clusters.append({
                "cluster_id": key,
                "severity": severity,
                "cluster_score": score,
                "vessel_count": len(group),
                "vessels": vessel_ids,
                "lat": group[0].get("lat"),
                "lon": group[0].get("lon"),
                "indicators": [
                    "multi-vessel close proximity",
                    "slow group movement",
                    "possible coordinated maritime activity"
                ]
            })

    clusters.sort(key=lambda x: x["cluster_score"], reverse=True)
    return clusters[:20]
