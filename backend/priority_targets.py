def build_priority_targets(fusion_scores, limit=10):

    targets = []

    for item in fusion_scores:

        score = item.get("fusion_score", 0)

        if score < 35:
            continue

        if score >= 80:
            priority = "IMMEDIATE"
        elif score >= 60:
            priority = "HIGH"
        else:
            priority = "WATCH"

        targets.append({
            "priority": priority,
            "mmsi": item.get("mmsi"),
            "shipname": item.get("shipname", "UNKNOWN"),
            "fusion_score": score,
            "threat_level": item.get("threat_level"),
            "reasons": item.get("reasons", []),
            "recommended_action": recommended_action(priority)
        })

    return targets[:limit]


def recommended_action(priority):

    if priority == "IMMEDIATE":
        return "Escalate for operational review and continuous monitoring"

    if priority == "HIGH":
        return "Monitor closely and review vessel history"

    return "Maintain watchlist observation"
