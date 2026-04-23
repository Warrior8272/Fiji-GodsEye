from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timezone

def clamp(value, low=0, high=100):
    return max(low, min(high, value))

def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

def hours_since(timestamp):
    dt = parse_dt(timestamp)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, (now - dt).total_seconds() / 3600)

def is_on_land(lat, lon):
    return (
        lat > -18.2 and
        lat < -17.5 and
        lon > 177.3 and
        lon < 178.2
    )

def classify_type_weight(vessel_type):
    value = str(vessel_type or "").lower()
    if value == "unknown":
        return 15
    if value == "fishing":
        return 10
    return 0

def score_vessels(vessels):
    scored = []

    for v in vessels:
        lat = float(v.get("lat", 0) or 0)
        lon = float(v.get("lon", 0) or 0)
        speed = float(v.get("speed", 0) or 0)
        course = v.get("course")
        heading = v.get("heading")
        confidence = int(float(v.get("confidence", 0) or 0))
        correlation_score = int(float(v.get("correlation_score", 0) or 0))
        nearby_alerts = v.get("nearby_alerts", []) or []

        last_seen_age_hours = hours_since(v.get("lastSeen"))

        anomaly_flags = []
        behavior_flags = []

        if is_on_land(lat, lon) and speed > 1:
            anomaly_flags.append("land_movement")

        if speed > 45:
            anomaly_flags.append("extreme_speed")

        if speed < 0.2:
            behavior_flags.append("stationary")
        elif speed < 2:
            behavior_flags.append("slow_movement")

        stale_tracking = 0
        if last_seen_age_hours is not None:
            if last_seen_age_hours > 12:
                behavior_flags.append("stale_tracking")
                stale_tracking = -10  # reduce score instead of increasing
            elif last_seen_age_hours > 6:
                stale_tracking = -5


        multiple_alert_bonus = 10 if len(nearby_alerts) > 1 else 0

        anomaly_score = 0
        if "land_movement" in anomaly_flags:
            anomaly_score += 35
        if "extreme_speed" in anomaly_flags:
            anomaly_score += 25
        if "stale_tracking" in anomaly_flags:
            anomaly_score += 10

        type_weight = classify_type_weight(v.get("type"))

        base_confidence_weighted = round(confidence * 0.25)

        total_score = clamp(
            base_confidence_weighted +
            correlation_score +
            anomaly_score +
            stale_tracking +
            type_weight +
            multiple_alert_bonus
        )

        if total_score >= 80:
            risk_level = "Critical"
        elif total_score >= 55:
            risk_level = "High"
        elif total_score >= 30:
            risk_level = "Elevated"
        else:
            risk_level = "Low"

        assessment = "No immediate anomaly detected."
        if anomaly_flags:
            assessment = "Anomaly detected: " + ", ".join(anomaly_flags)

        scored.append({
            **v,
            "risk_level": risk_level,
            "anomaly_flags": anomaly_flags,
            "behavior_flags": behavior_flags,
            "anomaly_score": anomaly_score,
            "last_seen_age_hours": round(last_seen_age_hours, 2) if last_seen_age_hours else None,
            "assessment": assessment,
            "score_breakdown": {
                "base_confidence": base_confidence_weighted,
                "correlation": correlation_score,
                "anomaly": anomaly_score,
                "stale_tracking": stale_tracking,
                "type_weight": type_weight,
                "multiple_alert_bonus": multiple_alert_bonus,
            }
        })

    return scored
