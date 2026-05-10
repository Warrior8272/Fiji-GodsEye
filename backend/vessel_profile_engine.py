import sqlite3
from timeline_engine import get_timeline

DB = "godseye_intel.db"

def build_vessel_profile(mmsi):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    SELECT case_id, title, priority, status, zone
    FROM investigation_cases
    WHERE linked_mmsi = ?
    """, (str(mmsi),))

    linked_cases = [
        {
            "case_id": r[0],
            "title": r[1],
            "priority": r[2],
            "status": r[3],
            "zone": r[4]
        }
        for r in cur.fetchall()
    ]

    conn.close()

    timeline = get_timeline(mmsi)

    profile = {
        "mmsi": str(mmsi),
        "linked_cases": linked_cases,
        "timeline_events": timeline,
        "risk_summary": {
            "linked_case_count": len(linked_cases),
            "timeline_events": len(timeline)
        }
    }

    return profile
