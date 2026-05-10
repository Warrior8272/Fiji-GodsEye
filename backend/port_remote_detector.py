import json
import os
from datetime import datetime, timezone
from math import radians, sin, cos, sqrt, atan2

HISTORY_FILE = "port_remote_history.json"

PORTS = {
    "Suva Port": (-18.1248, 178.4501),
    "Lautoka Port": (-17.6040, 177.4380),
}

PORT_RADIUS_KM = 8
STOP_SPEED_KN = 1.0
MIN_DISTANCE_FROM_PORT_KM = 10

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def distance_km(lat1, lon1, lat2, lon2):
    r = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return r * 2 * atan2(sqrt(a), sqrt(1-a))

def nearest_port(lat, lon):
    nearest = None
    nearest_dist = 999999

    for name, (plat, plon) in PORTS.items():
        d = distance_km(lat, lon, plat, plon)
        if d < nearest_dist:
            nearest = name
            nearest_dist = d

    if nearest_dist <= PORT_RADIUS_KM:
        return nearest, nearest_dist

    return None, nearest_dist

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def detect_port_remote_patterns(vessels):
    history = load_history()
    alerts = []

    for v in vessels:
        try:
            lat = float(v.get("lat") or v.get("latitude"))
            lon = float(v.get("lon") or v.get("longitude"))
            speed = float(v.get("speed") or v.get("sog") or 0)
        except Exception:
            continue

        mmsi = str(v.get("mmsi") or "UNKNOWN")
        name = v.get("shipname") or v.get("name") or "UNKNOWN"

        port, distance_to_nearest_port = nearest_port(lat, lon)

        record = history.get(mmsi, {
            "mmsi": mmsi,
            "name": name,
            "origin_port": None,
            "departed_port_at": None,
            "last_port_seen": None,
            "last_seen": None,
            "remote_stops": []
        })

        record["name"] = name
        record["last_seen"] = now_iso()

        # Vessel is docked or inside port area — this is normal, not a threat
        if port:
            record["last_port_seen"] = port

            if record.get("origin_port") and record.get("remote_stops"):
                last_stop = record["remote_stops"][-1]

                alerts.append({
                    "type": "PORT_REMOTE_RETURN",
                    "risk": "HIGH",
                    "score": 85,
                    "mmsi": mmsi,
                    "name": name,
                    "origin_port": record.get("origin_port"),
                    "returned_to_port": port,
                    "departed_port_at": record.get("departed_port_at"),
                    "stop_lat": last_stop.get("lat"),
                    "stop_lon": last_stop.get("lon"),
                    "stopped_at": last_stop.get("stopped_at"),
                    "distance_from_origin_port_km": last_stop.get("distance_from_origin_port_km"),
                    "summary": "Vessel departed port, stopped outside harbour limits, then returned to port.",
                    "reason": "Port-to-remote-stop-return pattern requires analyst review."
                })

                record["origin_port"] = None
                record["departed_port_at"] = None
                record["remote_stops"] = []

            history[mmsi] = record
            continue

        # Vessel is outside port
        if not port and record.get("last_port_seen") and not record.get("origin_port"):
            record["origin_port"] = record.get("last_port_seen")
            record["departed_port_at"] = now_iso()

        # Capture stop coordinates outside harbour area
        if record.get("origin_port") and speed <= STOP_SPEED_KN:
            origin_name = record["origin_port"]
            origin_lat, origin_lon = PORTS[origin_name]
            distance_from_origin = round(distance_km(lat, lon, origin_lat, origin_lon), 2)

            if distance_from_origin >= MIN_DISTANCE_FROM_PORT_KM:
                stop = {
                    "lat": lat,
                    "lon": lon,
                    "stopped_at": now_iso(),
                    "speed": speed,
                    "distance_from_origin_port_km": distance_from_origin
                }

                existing_stops = record.get("remote_stops", [])
                duplicate = False

                if existing_stops:
                    last = existing_stops[-1]
                    if distance_km(lat, lon, last["lat"], last["lon"]) < 1:
                        duplicate = True

                if not duplicate:
                    record.setdefault("remote_stops", []).append(stop)

                    alerts.append({
                        "type": "REMOTE_STOP_COORDINATE_CAPTURED",
                        "risk": "MEDIUM",
                        "score": 60,
                        "mmsi": mmsi,
                        "name": name,
                        "origin_port": origin_name,
                        "stop_lat": lat,
                        "stop_lon": lon,
                        "stopped_at": stop["stopped_at"],
                        "distance_from_origin_port_km": distance_from_origin,
                        "summary": "Vessel stopped outside harbour limits after leaving port.",
                        "reason": "Remote stop coordinates captured for analyst review."
                    })

        history[mmsi] = record

    save_history(history)
    return alerts
