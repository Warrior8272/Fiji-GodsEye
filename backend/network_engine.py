from collections import defaultdict
from datetime import datetime

VESSEL_NETWORK = defaultdict(lambda: {
    "connections": {},
    "zones": set(),
    "events": []
})

def register_connection(a, b, relation_type, score=1):
    a = str(a)
    b = str(b)

    if a == b:
        return

    now = datetime.utcnow().isoformat()

    # forward
    if b not in VESSEL_NETWORK[a]["connections"]:
        VESSEL_NETWORK[a]["connections"][b] = {
            "score": 0,
            "types": set(),
            "last_seen": now
        }

    VESSEL_NETWORK[a]["connections"][b]["score"] += score
    VESSEL_NETWORK[a]["connections"][b]["types"].add(relation_type)
    VESSEL_NETWORK[a]["connections"][b]["last_seen"] = now

    # reverse
    if a not in VESSEL_NETWORK[b]["connections"]:
        VESSEL_NETWORK[b]["connections"][a] = {
            "score": 0,
            "types": set(),
            "last_seen": now
        }

    VESSEL_NETWORK[b]["connections"][a]["score"] += score
    VESSEL_NETWORK[b]["connections"][a]["types"].add(relation_type)
    VESSEL_NETWORK[b]["connections"][a]["last_seen"] = now

def register_zone(vessel, zone_name):
    vid = str(vessel.get("mmsi") or vessel.get("id") or "UNKNOWN")

    if zone_name:
        VESSEL_NETWORK[vid]["zones"].add(zone_name)

def register_event(vessel, event_type, details):
    vid = str(vessel.get("mmsi") or vessel.get("id") or "UNKNOWN")

    VESSEL_NETWORK[vid]["events"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "details": details
    })

    VESSEL_NETWORK[vid]["events"] = VESSEL_NETWORK[vid]["events"][-50:]

def get_network(vessel_id):
    vessel_id = str(vessel_id)

    data = VESSEL_NETWORK.get(vessel_id, {})

    connections = []

    for target, info in data.get("connections", {}).items():
        connections.append({
            "target": target,
            "score": info["score"],
            "types": list(info["types"]),
            "last_seen": info["last_seen"]
        })

    connections.sort(key=lambda x: x["score"], reverse=True)

    return {
        "vessel": vessel_id,
        "zones": list(data.get("zones", [])),
        "connections": connections[:25],
        "events": data.get("events", [])[-25:]
    }
