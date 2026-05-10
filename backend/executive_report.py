from datetime import datetime

def generate_executive_report(
    fusion,
    briefing,
    escalation,
    mismatch
):

    report = {
        "title": "God's Eye Executive Intelligence Report",
        "generated": datetime.utcnow().isoformat(),
        "regional_threat_level": fusion.get("regional_threat_level"),
        "fusion_score": fusion.get("fusion_score"),
        "summary": briefing.get("summary"),
        "recommendation": briefing.get("recommendation"),
        "active_escalations": escalation.get("total_alerts", 0),
        "satellite_mismatches": mismatch.get("total_mismatches", 0),
        "sections": {
            "fusion_intelligence": fusion,
            "operational_briefing": briefing,
            "escalation_alerts": escalation,
            "satellite_mismatch": mismatch
        }
    }

    return report
