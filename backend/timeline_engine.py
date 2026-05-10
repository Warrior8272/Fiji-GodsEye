from collections import defaultdict
from datetime import datetime
from db_engine import recent_events

TIMELINE_MEMORY = defaultdict(list)

def add_timeline_event(vessel, event_type, details):
    mmsi = str(vessel.get("mmsi") or vessel.get("id") or "UNKNOWN")

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "details": details
    }

    TIMELINE_MEMORY[mmsi].append(event)
    TIMELINE_MEMORY[mmsi] = TIMELINE_MEMORY[mmsi][-100:]

def process_timeline(vessel):
    flags = vessel.get("risk_flags", [])

    if not isinstance(flags, list):
        flags = [str(flags)]

    threat_level = str(vessel.get("threat_level") or "").upper()
    if threat_level in ["MEDIUM", "HIGH", "CRITICAL"]:
        add_timeline_event(
            vessel,
            "THREAT_LEVEL",
            f"Threat level {threat_level}"
        )

    memory = vessel.get("memory", {})
    offender_status = str(memory.get("offender_status") or "")
    if offender_status and offender_status != "NEW":
        add_timeline_event(
            vessel,
            "OFFENDER_STATUS",
            f"{offender_status} score {memory.get('repeat_offender_score', 0)}"
        )

    for flag in flags:
        fl = str(flag).lower()

        if "loiter" in fl:
            add_timeline_event(vessel, "LOITERING", flag)

        if "watch zone" in fl:
            add_timeline_event(vessel, "WATCH_ZONE_ENTRY", flag)

        if "rendezvous" in fl:
            add_timeline_event(vessel, "RENDEZVOUS", flag)

        if "dark" in fl or "ais blackout" in fl:
            add_timeline_event(vessel, "DARK_ACTIVITY", flag)

def get_timeline(mmsi):
    return TIMELINE_MEMORY.get(str(mmsi), [])

def build_timeline(limit=100):
    events = recent_events(limit)

    timeline = []
    for e in events:
        timeline.append({
            "timestamp": e.get("timestamp"),
            "title": e.get("event_type"),
            "severity": e.get("severity"),
            "zone": e.get("zone"),
            "details": e.get("message")
        })

    timeline = sorted(
        timeline,
        key=lambda x: x["timestamp"],
        reverse=True
    )

    return {
        "total_events": len(timeline),
        "timeline": timeline
    }
