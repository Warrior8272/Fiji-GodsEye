from datetime import datetime

def generate_operational_report(
    vessels,
    alerts,
    dark_activity,
    clusters,
    corridors
):
    now = datetime.utcnow().isoformat()

    high_risk = [
        v for v in vessels
        if str(v.get("threat_level", "")).upper() in ["HIGH", "CRITICAL"]
    ]

    repeat_offenders = [
        v for v in vessels
        if v.get("memory", {}).get("offender_status") == "PERSISTENT OFFENDER"
    ]

    report = {
        "generated_at": now,
        "summary": {
            "tracked_vessels": len(vessels),
            "high_risk_vessels": len(high_risk),
            "alerts": len(alerts),
            "dark_activity": len(dark_activity),
            "clusters": len(clusters),
            "repeat_offenders": len(repeat_offenders)
        },
        "top_threats": [],
        "dark_activity": dark_activity[:10],
        "clusters": clusters[:10],
        "corridors": corridors[:10],
        "repeat_offenders": [],
        "assessment": ""
    }

    sorted_threats = sorted(
        high_risk,
        key=lambda x: float(x.get("threat_score", x.get("risk", 0)) or 0),
        reverse=True
    )

    for v in sorted_threats[:10]:
        report["top_threats"].append({
            "mmsi": v.get("mmsi"),
            "name": v.get("name"),
            "threat_level": v.get("threat_level"),
            "threat_score": v.get("threat_score", v.get("risk")),
            "zone": v.get("zone_name"),
            "flags": v.get("risk_flags", [])
        })

    for v in repeat_offenders[:10]:
        report["repeat_offenders"].append({
            "mmsi": v.get("mmsi"),
            "name": v.get("name"),
            "score": v.get("memory", {}).get("repeat_offender_score", 0),
            "zone": v.get("zone_name")
        })

    assessment_lines = []

    if len(clusters) >= 3:
        assessment_lines.append(
            "Elevated coordinated maritime activity detected across monitored sectors."
        )

    if len(dark_activity) >= 5:
        assessment_lines.append(
            "Multiple AIS dark activity events detected requiring continued monitoring."
        )

    if len(repeat_offenders) >= 5:
        assessment_lines.append(
            "Persistent repeat-offender maritime behaviour observed."
        )

    if not assessment_lines:
        assessment_lines.append(
            "No major coordinated maritime threat patterns currently detected."
        )

    report["assessment"] = " ".join(assessment_lines)

    return report
