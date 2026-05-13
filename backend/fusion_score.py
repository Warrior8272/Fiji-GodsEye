def calculate_fusion_score(vessel, alerts):

    score = 0
    reasons = []
    counted_types = set()

    mmsi = str(vessel.get("mmsi", ""))

    base_risk = vessel.get("risk", 0) or 0
    score += int(base_risk)

    if base_risk:
        reasons.append(f"Base vessel risk: {base_risk}")

    for alert in alerts:

        alert_mmsi = str(alert.get("mmsi", ""))

        if alert_mmsi and alert_mmsi != mmsi:
            continue

        alert_type = alert.get("type", "")

        if alert_type in counted_types:
            continue

        counted_types.add(alert_type)

        if alert_type == "DARK_ACTIVITY":
            score += 30
            reasons.append("AIS silence / dark activity")

        elif alert_type == "REPEAT_OFFENDER":
            score += 25
            reasons.append("Repeat suspicious activity")

        elif alert_type == "ROUTE_ANOMALY":
            score += 15
            reasons.append("Route anomaly")

        elif alert_type == "SPEED_ANOMALY":
            score += 10
            reasons.append("Speed anomaly")

        elif alert_type == "LOITERING":
            score += 20
            reasons.append("Loitering behaviour")

        elif alert_type == "SPOOFING":
            score += 35
            reasons.append("Possible GPS spoofing")

    if score >= 80:
        level = "CRITICAL"
    elif score >= 60:
        level = "HIGH"
    elif score >= 35:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "mmsi": mmsi,
        "shipname": vessel.get("shipname", "UNKNOWN"),
        "fusion_score": min(score, 100),
        "threat_level": level,
        "reasons": reasons
    }


def process_fusion_scores(vessels, alerts):

    results = []

    for vessel in vessels:
        results.append(calculate_fusion_score(vessel, alerts))

    return sorted(
        results,
        key=lambda x: x.get("fusion_score", 0),
        reverse=True
    )
