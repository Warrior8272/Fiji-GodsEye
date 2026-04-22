from datetime import datetime, timezone
from math import sqrt


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, int(round(value))))


def to_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def parse_time(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def last_seen_hours(ts):
    dt = parse_time(ts)
    if not dt:
        return None
    delta = datetime.now(timezone.utc) - dt
    return round(delta.total_seconds() / 3600, 2)


def classify_risk(confidence):
    if confidence >= 75:
        return "High"
    if confidence >= 60:
        return "Medium"
    return "Low"


def offshore_distance_hint(lat, lon):
    lat = to_float(lat)
    lon = to_float(lon)
    if lat is None or lon is None:
        return None

    ref_lat = -17.75
    ref_lon = 177.38
    return sqrt((lat - ref_lat) ** 2 + (lon - ref_lon) ** 2)


def repeated_position_score(vessel):
    history = vessel.get("history") or []
    if not isinstance(history, list) or len(history) < 3:
        return 0

    coords = []
    for point in history[-6:]:
        lat = to_float(point.get("lat"))
        lon = to_float(point.get("lon"))
        if lat is None or lon is None:
            continue
        coords.append((round(lat, 5), round(lon, 5)))

    if len(coords) < 3:
        return 0

    unique_count = len(set(coords))
    if unique_count == 1:
        return 14
    if unique_count <= 2:
        return 8
    return 0


def score_single_vessel(vessel):
    speed = to_float(vessel.get("speed"), 0)
    course = to_float(vessel.get("course"))
    heading = to_float(vessel.get("heading"))
    lat = to_float(vessel.get("lat"))
    lon = to_float(vessel.get("lon"))
    last_seen = vessel.get("lastSeen")
    vessel_type = str(vessel.get("type") or "").strip().upper()
    nearby_alerts = vessel.get("nearby_alerts") or []

    age = last_seen_hours(last_seen)
    flags = []

    base_confidence = 20
    movement_score = 0
    stale_tracking = 0
    navigation_score = 0
    type_weight = 0
    loitering_score = 0
    ghost_signal = 0
    repeated_position = repeated_position_score(vessel)
    correlation = min(len(nearby_alerts) * 12, 30)
    multiple_alert_bonus = 10 if len(nearby_alerts) >= 2 else 0

    # Movement
    if speed is None:
        movement_score = 6
    elif speed == 0:
        movement_score = 20
        flags.append("stationary")
    elif speed < 0.3:
        movement_score = 16
        flags.append("drifting")
    elif speed < 1:
        movement_score = 10
        flags.append("drifting")
    elif speed < 2:
        movement_score = 6
        flags.append("slow_movement")
    elif speed < 5:
        movement_score = 2
    elif speed > 40:
        movement_score = 8
        flags.append("extreme_speed")

    # Staleness
    if age is None:
        stale_tracking = 6
    elif age >= 12:
        stale_tracking = 40
        flags.append("ais_silence")
    elif age >= 6:
        stale_tracking = 28
        flags.append("ais_silence")
    elif age >= 2:
        stale_tracking = 18
        flags.append("stale_tracking")
    elif age >= 1:
        stale_tracking = 10
        flags.append("stale_tracking")

    # Stationary long only when really barely moving and stale enough
    if speed is not None and speed < 0.5 and age is not None and age > 0.5:
        if "stationary" in flags:
            flags.append("stationary_long")

    # Navigation anomalies
    if heading is not None and (heading < 0 or heading > 360):
        navigation_score += 10
        flags.append("odd_navigation")

    if course is not None and (course < 0 or course > 360):
        navigation_score += 10
        if "odd_navigation" not in flags:
            flags.append("odd_navigation")

    if course is not None and heading is not None:
        delta = abs(course - heading)
        delta = min(delta, 360 - delta)
        if delta > 120:
            navigation_score += 12
            flags.append("course_heading_mismatch")
        elif delta > 60:
            navigation_score += 6
            flags.append("course_heading_mismatch")

    # Identity
    if vessel_type in {"", "UNKNOWN"}:
        type_weight = 8
        flags.append("weak_identity")
    elif vessel_type == "AIS":
        type_weight = 3
        flags.append("weak_identity")
    elif vessel_type in {"FISHING", "TANKER", "CARGO"}:
        type_weight = 2

    # Offshore loitering / slow offshore behavior
    proxy = offshore_distance_hint(lat, lon)

    if proxy is not None and age is not None:
        if proxy > 0.28 and speed is not None and speed <= 0.8 and 0.2 < age < 1.5:
            loitering_score = 16
            flags.append("offshore_loitering")
        elif proxy > 0.20 and speed is not None and speed <= 0.3 and 0.2 < age < 1.0:
            loitering_score = 10
            flags.append("slow_offshore_behavior")

    # Ghost / silent AIS
    if age is not None:
        if age >= 6 and speed is not None and speed <= 1:
            ghost_signal += 18
            flags.append("ghost_signal")
        elif age >= 2 and speed is not None and speed <= 1:
            ghost_signal += 10
            flags.append("silent_ais_pattern")

        if nearby_alerts and age >= 1:
            ghost_signal += 8
            if "nearby_alert_link" not in flags:
                flags.append("nearby_alert_link")

    # Repeated coordinates
    if repeated_position > 0:
        flags.append("repeated_coordinates")

    # Alert linkage
    if nearby_alerts and "nearby_alert_link" not in flags:
        flags.append("nearby_alert_link")

    confidence = clamp(
        base_confidence
        + movement_score
        + stale_tracking
        + navigation_score
        + type_weight
        + loitering_score
        + ghost_signal
        + repeated_position
        + correlation
        + multiple_alert_bonus
    )

    # Existing escalation rules
    if ghost_signal >= 18 and navigation_score >= 10:
        confidence = clamp(confidence + 10)

    if loitering_score >= 16 and navigation_score >= 10:
        confidence = clamp(confidence + 8)

    if repeated_position >= 14 and stale_tracking >= 18:
        confidence = clamp(confidence + 8)

    unique_flags = list(dict.fromkeys(flags))

    # Reduce noise from identity-only cases
    if unique_flags == ["weak_identity"]:
        confidence = clamp(confidence - 10)

    # Tuned escalation engine
    serious_flags = [
        f for f in unique_flags
        if f not in ["weak_identity", "slow_movement"]
    ]

    if len(serious_flags) >= 3:
        confidence = clamp(confidence + 8)

    if "stationary" in unique_flags and "course_heading_mismatch" in unique_flags:
        confidence = clamp(confidence + 6)

    if (
        "offshore_loitering" in unique_flags
        and speed is not None
        and speed < 2
        and (
            "course_heading_mismatch" in unique_flags
            or "stale_tracking" in unique_flags
            or "ais_silence" in unique_flags
        )
    ):
        confidence = clamp(confidence + 8)

    if "weak_identity" in unique_flags and len(serious_flags) >= 2:
        confidence = clamp(confidence + 4)

    if "drifting" in unique_flags and "offshore_loitering" in unique_flags:
        confidence = clamp(confidence + 6)

    # ===== PORT / COASTAL NORMALIZATION =====
    if lat is not None and lon is not None:
        if -18.2 < lat < -16.5 and 176.8 < lon < 178.6:
            if "stationary" in unique_flags and "course_heading_mismatch" in unique_flags:
                confidence = clamp(confidence - 10)

            if "slow_offshore_behavior" in unique_flags:
                confidence = clamp(confidence - 6)

            if "weak_identity" in unique_flags:
                confidence = clamp(confidence - 3)

    # ===== OFFSHORE VALIDATION FILTER =====
    if lat is not None and lon is not None:
        if -18.2 < lat < -16.5 and 176.8 < lon < 178.6:
            if "offshore_loitering" in unique_flags:
                if not (
                    proxy is not None
                    and proxy > 0.25
                    and speed is not None
                    and speed < 1
                    and age is not None
                    and age > 0.2
                ):
                    unique_flags.remove("offshore_loitering")
                    confidence = clamp(confidence - 12)

            if "slow_offshore_behavior" in unique_flags:
                if proxy is not None and proxy < 0.15:
                    unique_flags.remove("slow_offshore_behavior")
                    confidence = clamp(confidence - 8)

    # reduce confidence if only weak + stationary combo
    if set(unique_flags).issubset({"stationary", "weak_identity"}):
        confidence = clamp(confidence - 8)

    # ===== COASTAL / PORT NORMALIZATION (FINAL GUARD) =====
    if (
        "stationary" in unique_flags
        and "weak_identity" in unique_flags
        and "offshore_loitering" not in unique_flags
        and "ghost_signal" not in unique_flags
    ):
        confidence = clamp(confidence - 12)

    if set(unique_flags).issubset({"stationary", "stationary_long", "weak_identity"}):
        confidence = clamp(confidence - 15)

    if (
        "course_heading_mismatch" in unique_flags
        and speed is not None
        and speed < 0.5
    ):
        confidence = clamp(confidence - 6)

    # ===== CONFIDENCE FLOOR (CRITICAL FIX) =====
    if confidence < 10:
       confidence = 10 
   
    risk_level = classify_risk(confidence)

    # Assessment
    reasons = []
    if "ghost_signal" in unique_flags:
        reasons.append("possible ghost AIS behavior")
    if "silent_ais_pattern" in unique_flags:
        reasons.append("silent AIS pattern")
    if "offshore_loitering" in unique_flags:
        reasons.append("offshore loitering")
    if "slow_offshore_behavior" in unique_flags:
        reasons.append("slow offshore behavior")
    if "stationary_long" in unique_flags:
        reasons.append("extended stationary behavior")
    if "stationary" in unique_flags and "stationary_long" not in unique_flags:
        reasons.append("stationary behavior")
    if "drifting" in unique_flags:
        reasons.append("drifting pattern")
    if "course_heading_mismatch" in unique_flags:
        reasons.append("course-heading mismatch")
    if "odd_navigation" in unique_flags:
        reasons.append("odd navigation values")
    if "repeated_coordinates" in unique_flags:
        reasons.append("repeated coordinates")
    if "nearby_alert_link" in unique_flags:
        reasons.append("nearby alert linkage")
    if "weak_identity" in unique_flags and not reasons:
        reasons.append("weak identity signal")

    if reasons:
        joined = ", ".join(reasons)
        if risk_level == "High":
            assessment = f"High-priority vessel requiring analyst review due to {joined}."
        elif risk_level == "Medium":
            assessment = f"Moderate-risk vessel flagged due to {joined}."
        else:
            assessment = f"Low-risk vessel noted due to {joined}."
    else:
        if risk_level == "High":
            assessment = "High-priority vessel requiring analyst review."
        elif risk_level == "Medium":
            assessment = "Moderate-risk vessel requiring monitoring."
        else:
            assessment = "Low-risk vessel with no immediate indicators."

    vessel["confidence"] = round(confidence)
    vessel["risk_level"] = risk_level
    vessel["risk_flags"] = unique_flags
    vessel["assessment"] = assessment
    vessel["last_seen_age_hours"] = age
    vessel["correlation_score"] = correlation
    vessel["score_breakdown"] = {
        "base_confidence": base_confidence,
        "movement_score": movement_score,
        "stale_tracking": stale_tracking,
        "navigation_score": navigation_score,
        "type_weight": type_weight,
        "loitering": loitering_score,
        "ghost_signal": ghost_signal,
        "repeated_position": repeated_position,
        "correlation": correlation,
        "multiple_alert_bonus": multiple_alert_bonus,
    }

    return vessel


def score_vessels(vessels):
    return [score_single_vessel(v) for v in vessels]

