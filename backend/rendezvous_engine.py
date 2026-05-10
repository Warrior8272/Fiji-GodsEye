import math
from datetime import datetime, timezone

def _num(x, default=None):
    try:
        return float(x)
    except Exception:
        return default

def _get(v, *keys):
    for k in keys:
        if k in v and v.get(k) not in [None, ""]:
            return v.get(k)
    return None

def distance_nm(lat1, lon1, lat2, lon2):
    R_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dp/2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return (R_km * c) * 0.539957

def detect_rendezvous(vessels, max_distance_nm=1.5, max_speed_knots=3.0):
    alerts = []

    clean = []
    for v in vessels:
        lat = _num(_get(v, "lat", "Latitude"))
        lon = _num(_get(v, "lon", "Longitude"))
        speed = _num(_get(v, "speed", "SOG"), 0)
        mmsi = str(_get(v, "mmsi", "MMSI") or "UNKNOWN")
        name = str(_get(v, "name", "ShipName") or "UNKNOWN")
        zone = str(_get(v, "zone_name", "zone", "zone_current") or "Unknown Zone")
        ztype = str(_get(v, "zone_type") or "").lower()

        if lat is None or lon is None:
            continue

        clean.append({
            "mmsi": mmsi,
            "name": name,
            "lat": lat,
            "lon": lon,
            "speed": speed,
            "zone_name": zone,
            "zone_type": ztype,
            "raw": v
        })

    for i in range(len(clean)):
        for j in range(i + 1, len(clean)):
            a = clean[i]
            b = clean[j]

            if a["mmsi"] == b["mmsi"]:
                continue

            d = distance_nm(a["lat"], a["lon"], b["lat"], b["lon"])

            slow_a = a["speed"] <= max_speed_knots
            slow_b = b["speed"] <= max_speed_knots
            close = d <= max_distance_nm

            if close and slow_a and slow_b:
                score = 70

                if a["zone_type"] != "port" and b["zone_type"] != "port":
                    score += 15

                if a["speed"] == 0 and b["speed"] == 0:
                    score += 10

                score = min(score, 100)

                alerts.append({
                    "type": "RENDEZVOUS",
                    "threat_level": "HIGH" if score >= 80 else "MEDIUM",
                    "threat_score": score,
                    "distance_nm": round(d, 2),
                    "zone": a["zone_name"],
                    "assessment": "Possible vessel rendezvous / transfer behaviour detected",
                    "vessel_a": {
                        "mmsi": a["mmsi"],
                        "name": a["name"],
                        "speed": a["speed"],
                        "lat": a["lat"],
                        "lon": a["lon"]
                    },
                    "vessel_b": {
                        "mmsi": b["mmsi"],
                        "name": b["name"],
                        "speed": b["speed"],
                        "lat": b["lat"],
                        "lon": b["lon"]
                    },
                    "reasons": [
                        "Two vessels within close range",
                        "Both vessels slow or stationary",
                        "Possible at-sea meeting pattern"
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

    return alerts
