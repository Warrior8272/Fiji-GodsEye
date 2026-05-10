from datetime import datetime
from db_engine import log_event

def evaluate_escalation(fusion, mismatches):

    alerts = []

    score = fusion.get("fusion_score", 0)
    level = fusion.get("regional_threat_level", "LOW")

    if score >= 50:
        alerts.append({
            "severity": level,
            "type": "FUSION_ESCALATION",
            "message": f"Regional fusion score elevated to {score}.",
            "timestamp": datetime.utcnow().isoformat()
        })

    for m in mismatches:
        event_msg = f"{m.get('zone')} mismatch detected."

        log_event(
            "SATELLITE_AIS_MISMATCH",
            m.get("severity", "MEDIUM"),
            m.get("zone"),
            event_msg
        )

        alerts.append({
            "severity": m.get("severity", "MEDIUM"),
            "type": "SATELLITE_AIS_MISMATCH",
            "message": event_msg,
            "timestamp": datetime.utcnow().isoformat()
        })

    return {
        "total_alerts": len(alerts),
        "alerts": alerts
    }
