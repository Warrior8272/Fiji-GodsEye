from datetime import datetime

SATELLITE_VISUAL_ZONES = [
    {
        "zone": "Suva Port",
        "satellite_visible_vessels": True,
        "estimated_visible_count": 8,
        "notes": "Multiple docked and anchored vessels visually confirmed via satellite imagery."
    }
]

def generate_satellite_mismatch(feed_coverage):

    mismatches = []

    for zone in SATELLITE_VISUAL_ZONES:

        name = zone["zone"]

        matching = next(
            (z for z in feed_coverage if z.get("zone") == name),
            None
        )

        if not matching:
            continue

        contacts = matching.get("contacts", 0)

        if zone["satellite_visible_vessels"] and contacts == 0:

            mismatches.append({
                "zone": name,
                "severity": "HIGH",
                "type": "SATELLITE_AIS_MISMATCH",
                "satellite_visible": zone["estimated_visible_count"],
                "ais_contacts": contacts,
                "timestamp": datetime.utcnow().isoformat(),
                "assessment": "Satellite imagery indicates vessel presence while AIS feed reports zero contacts.",
                "recommendation": "Verify AIS coverage, satellite freshness, and possible non-reporting vessel activity."
            })

    return {
        "total_mismatches": len(mismatches),
        "mismatches": mismatches
    }
