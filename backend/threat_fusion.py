def threat_score(v):
    score = int(v.get("risk", 0) or 0)
    reasons = []

    if v.get("loiter_time", 0) > 300:
        score += 25
        reasons.append("loitering")

    if v.get("zone_type") in ["watch", "port", "restricted"]:
        score += 20
        reasons.append(f"{v.get('zone_type')} zone")

    if "AIS_GAP" in str(v.get("nearby_alerts", [])):
        score += 30
        reasons.append("AIS gap")

    if v.get("speed", 0) == 0 and v.get("loiter_time", 0) > 600:
        score += 15
        reasons.append("stationary long duration")

    score = min(score, 100)

    if score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "threat_score": score,
        "threat_level": level,
        "threat_reasons": reasons
    }

def apply_threat_scores(vessels):
    for v in vessels:
        v.update(threat_score(v))
    return vessels
