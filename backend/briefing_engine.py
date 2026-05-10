from datetime import datetime

def generate_operational_briefing(
    fusion,
    cyber,
    coverage,
    mismatches
):

    level = fusion.get("regional_threat_level", "UNKNOWN")

    summary = []

    summary.append(
        f"Regional threat posture currently assessed as {level}."
    )

    if fusion.get("cyber_events", 0) > 0:
        summary.append(
            f"{fusion.get('cyber_events')} cyber threat events are currently active across monitored sectors."
        )

    gaps = [
        z["zone"]
        for z in coverage
        if z.get("status") == "COVERAGE GAP"
    ]

    if gaps:
        summary.append(
            "AIS coverage gaps detected in: " + ", ".join(gaps) + "."
        )

    if mismatches:
        summary.append(
            f"{len(mismatches)} satellite/AIS correlation mismatches require operational review."
        )

    recommendation = fusion.get(
        "recommendation",
        "Continue monitoring."
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "threat_level": level,
        "summary": " ".join(summary),
        "recommendation": recommendation
    }
