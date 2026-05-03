from datetime import datetime, timezone

def parse_time(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None

def detect_gaps(vessels):
    alerts = []
    now = datetime.now(timezone.utc)

    for v in vessels:
        mmsi = v.get("mmsi")
        last_seen_raw = v.get("lastSeen")

        if not mmsi or not last_seen_raw:
            continue

        last_seen = parse_time(last_seen_raw)
        if not last_seen:
            continue

        age_seconds = (now - last_seen).total_seconds()

        if age_seconds > 600:  # testing threshold
            alerts.append({
                "id": f"gap:{mmsi}",
                "type": "AIS_GAP",
                "severity": "HIGH",
                "message": f"Dark vessel alert: AIS silent for {int(age_seconds // 60)}m {int(age_seconds % 60)}s",
                "silent_for_seconds": int(age_seconds),
                "silent_for_display": f"{int(age_seconds // 60)}m {int(age_seconds % 60)}s",
                "mmsi": mmsi,
                "lastSeen": last_seen_raw,
                "vessel": v
            })

    return alerts
