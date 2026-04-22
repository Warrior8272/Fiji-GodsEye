from datetime import datetime, timezone

def is_on_land_box(lat, lon):
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return False

    return lat > -18.1 and lat < -17.5 and lon > 177.5 and lon < 178.3

def hours_since(iso_ts):
    if not iso_ts:
        return None
    try:
        ts = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - ts.astimezone(timezone.utc)
        return delta.total_seconds() / 3600
    except Exception:
        return None

def vessel_type_weight(vessel_type):
    value = str(vessel_type or "").lower()
    if value == "unknown":
        return 15
    if value == "fishing":
        return 10
    if value == "cargo":
        return 5
    return 0

def risk_level(score):
    if score >= 85:
        return "High"
    if score >= 60:
        return "Elevated"
    if score >= 30:
        return "Moderate"
    return "Low"

def build_assessment(score, flags):
    if "position_anomaly" in flags and "near_alert_activity" in flags:
        return "Strong indicators of suspicious behaviour: anomaly plus nearby alert activity."
    if "multiple_nearby_alerts" in flags:
        return "Multiple nearby alerts increase the likelihood this contact needs analyst review."
    if "stale_tracking" in flags:
        return "Tracking appears stale and should be reviewed for visibility gaps."
    if score >= 85:
        return "High-priority contact requiring analyst review."
    if score >= 60:
        return "Elevated-risk contact with notable indicators."
    if score >= 30:
        return "Moderate-risk contact. Continue monitoring."
    return "Low-risk contact based on current signals."

def score_vessel_record(vessel):
    base_confidence = int(vessel.get("confidence", 0) or 0)
    correlation_score = int(vessel.get("correlation_score", 0) or 0)
    nearby_alerts = vessel.get("nearby_alerts", []) or []

    score = base_confidence
    flags = list(vessel.get("risk_flags", []) or [])
    breakdown = {
        "base_confidence": base_confidence,
        "correlation": correlation_score,
        "anomaly": 0,
        "stale_tracking": 0,
        "type_weight": 0,
        "multiple_alert_bonus": 0,
    }

    # Correlation
    score += correlation_score

    # Position anomaly
    if is_on_land_box(vessel.get("lat"), vessel.get("lon")):
        breakdown["anomaly"] = 20
        score += 20
        if "position_anomaly" not in flags:
            flags.append("position_anomaly")

    # Stale tracking
    age_hours = hours_since(vessel.get("lastSeen"))
    if age_hours is not None and age_hours >= 8:
        breakdown["stale_tracking"] = 15
        score += 15
        if "stale_tracking" not in flags:
            flags.append("stale_tracking")

    # Vessel type weighting
    type_bonus = vessel_type_weight(vessel.get("type"))
    breakdown["type_weight"] = type_bonus
    score += type_bonus

    # Extra bonus for multiple nearby alerts
    if len(nearby_alerts) >= 2:
        breakdown["multiple_alert_bonus"] = 10
        score += 10
        if "multiple_nearby_alerts" not in flags:
            flags.append("multiple_nearby_alerts")

    final_score = min(score, 100)
    level = risk_level(final_score)
    assessment = build_assessment(final_score, flags)

    enriched = dict(vessel)
    enriched["confidence"] = final_score
    enriched["risk_level"] = level
    enriched["risk_flags"] = flags
    enriched["score_breakdown"] = breakdown
    enriched["assessment"] = assessment
    enriched["last_seen_age_hours"] = round(age_hours, 2) if age_hours is not None else None

    return enriched

def score_vessels(vessels):
    return [score_vessel_record(v) for v in vessels]
