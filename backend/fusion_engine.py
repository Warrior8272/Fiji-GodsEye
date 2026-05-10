from datetime import datetime
from cyber_feed import get_cyber_events

def generate_fusion_intelligence(vessels):

    cyber = get_cyber_events()

    maritime_high = 0
    dark_activity = 0
    repeat_offenders = 0

    for v in vessels:
        try:
            score = float(v.get("threat_score", v.get("risk", 0)))

            if score >= 40:
                maritime_high += 1

            if float(v.get("dark_activity_count", 0)) > 0:
                dark_activity += 1

            if float(v.get("repeat_offender_score", 0)) > 0:
                repeat_offenders += 1

        except:
            pass

    cyber_events = cyber.get("total", 0)

    fusion_score = (
        (maritime_high * 8) +
        (dark_activity * 6) +
        (repeat_offenders * 5) +
        (cyber_events * 7)
    )

    if fusion_score >= 80:
        level = "CRITICAL"
    elif fusion_score >= 50:
        level = "HIGH"
    elif fusion_score >= 25:
        level = "ELEVATED"
    else:
        level = "LOW"

    recommendation = {
        "LOW": "Routine monitoring recommended.",
        "ELEVATED": "Increase regional monitoring posture.",
        "HIGH": "Elevated intelligence activity detected. Review maritime and cyber sectors.",
        "CRITICAL": "Critical multi-domain intelligence escalation detected."
    }[level]

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "regional_threat_level": level,
        "fusion_score": fusion_score,
        "maritime_high_risk": maritime_high,
        "dark_activity": dark_activity,
        "repeat_offenders": repeat_offenders,
        "cyber_events": cyber_events,
        "recommendation": recommendation
    }
