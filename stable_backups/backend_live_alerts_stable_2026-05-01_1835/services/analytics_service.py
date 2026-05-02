from __future__ import annotations

from typing import Any, Dict, List

from config import Config
from services.ais_service import load_raw_vessels, normalize_vessel
from utils.geo import age_hours, bearing_degrees, haversine_nm, heading_to_cardinal, percent


def distance_to_fiji_nm(lat: float, lon: float) -> float:
    return haversine_nm(lat, lon, Config.FIJI_CENTER["lat"], Config.FIJI_CENTER["lon"])


def corridor_match_score(lat: float, lon: float) -> float:
    d1 = haversine_nm(lat, lon, Config.SOUTH_AMERICA_GATE["lat"], Config.SOUTH_AMERICA_GATE["lon"])
    d2 = haversine_nm(lat, lon, Config.PACIFIC_MID_GATE["lat"], Config.PACIFIC_MID_GATE["lon"])
    d3 = haversine_nm(lat, lon, Config.FIJI_GATE["lat"], Config.FIJI_GATE["lon"])

    closest = min(d1, d2, d3)

    if closest <= 150:
        return 1.0
    if closest <= 350:
        return 0.8
    if closest <= 700:
        return 0.55
    if closest <= 1200:
        return 0.3
    return 0.0


def likely_fiji_bound(lat: float, lon: float, course: float | None) -> bool:
    if course is None:
        return False

    target_bearing = bearing_degrees(lat, lon, Config.FIJI_CENTER["lat"], Config.FIJI_CENTER["lon"])
    diff = abs((course - target_bearing + 180) % 360 - 180)
    return diff <= 55


def route_risk_label(lat: float, lon: float, course: float | None) -> str:
    score = corridor_match_score(lat, lon)
    inbound = likely_fiji_bound(lat, lon, course)

    if score >= 0.8 and inbound:
        return "High corridor relevance"
    if score >= 0.55 and inbound:
        return "Moderate corridor relevance"
    if score >= 0.3:
        return "Low corridor relevance"
    return "No corridor match"


def is_ais_timeout(last_seen) -> bool:
    hrs = age_hours(last_seen)
    return hrs is None or hrs >= Config.AIS_TIMEOUT_HOURS


def is_stale(last_seen) -> bool:
    hrs = age_hours(last_seen)
    return hrs is None or hrs >= Config.VESSEL_STALE_HOURS


def is_unknown_vessel(vessel: Dict[str, Any]) -> bool:
    no_identity = not vessel.get("mmsi") and not vessel.get("imo") and not vessel.get("callsign")
    vague_name = vessel.get("name", "").strip().lower() in {"unknown", "unknown vessel", "unknown contact"}
    unknown_type = vessel.get("ship_type", "").strip().lower() in {"unknown", "", "n/a"}
    return no_identity or vague_name or unknown_type


def is_loitering(vessel: Dict[str, Any]) -> bool:
    return vessel["speed_knots"] <= Config.LOITERING_SPEED_KNOTS


def speed_anomaly(vessel: Dict[str, Any]) -> bool:
    return vessel["speed_knots"] >= Config.HIGH_SPEED_KNOTS


def compute_confidence_score(vessel: Dict[str, Any]) -> int:
    score = 0.0
    hrs = age_hours(vessel.get("last_seen"))

    if hrs is None:
        score += 0
    elif hrs <= 1:
        score += 35
    elif hrs <= 3:
        score += 28
    elif hrs <= Config.AIS_TIMEOUT_HOURS:
        score += 18
    elif hrs <= 12:
        score += 8

    score += 15

    if vessel.get("mmsi"):
        score += 15
    if vessel.get("imo"):
        score += 8
    if vessel.get("callsign"):
        score += 5
    if vessel.get("name") and vessel["name"].lower() not in {"unknown", "unknown vessel", "unknown contact"}:
        score += 5
    if vessel.get("course") is not None:
        score += 5
    if vessel.get("heading") is not None:
        score += 4
    if vessel.get("destination"):
        score += 5

    if is_unknown_vessel(vessel):
        score -= 18
    if is_ais_timeout(vessel.get("last_seen")):
        score -= 20
    if speed_anomaly(vessel):
        score -= 8

    return percent(score)


def marker_color(vessel: Dict[str, Any]) -> str:
    if vessel["ais_timeout"]:
        return "gray"
    if vessel["suspicious"]:
        return "red"
    if vessel["confidence_score"] >= 75:
        return "green"
    if vessel["confidence_score"] >= 45:
        return "orange"
    return "yellow"


def marker_radius(vessel: Dict[str, Any]) -> int:
    score = vessel["confidence_score"]
    if score >= 80:
        return 7
    if score >= 60:
        return 10
    if score >= 40:
        return 13
    return 16


def build_alerts(vessel: Dict[str, Any]) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []

    if vessel["ais_timeout"]:
        alerts.append({
            "type": "ais_timeout",
            "severity": "high",
            "title": "AIS timeout",
            "message": f"No fresh AIS update for {vessel['hours_since_seen']} hours.",
        })

    if vessel["unknown_vessel"]:
        alerts.append({
            "type": "unknown_identity",
            "severity": "medium",
            "title": "Unknown vessel identity",
            "message": "Vessel has weak or missing identity fields.",
        })

    if vessel["distance_to_fiji_nm"] <= Config.SUSPICIOUS_PROXIMITY_NM and vessel["unknown_vessel"]:
        alerts.append({
            "type": "unknown_near_fiji",
            "severity": "high",
            "title": "Unknown vessel near Fiji",
            "message": f"Unknown vessel detected within {Config.SUSPICIOUS_PROXIMITY_NM} NM of Fiji.",
        })

    if vessel["corridor_score"] >= 0.8 and vessel["fiji_bound"]:
        alerts.append({
            "type": "corridor_match",
            "severity": "medium",
            "title": "South Pacific corridor match",
            "message": "Track aligns strongly with monitored Pacific route toward Fiji.",
        })

    if vessel["loitering"]:
        alerts.append({
            "type": "loitering",
            "severity": "medium",
            "title": "Loitering behaviour",
            "message": f"Speed is very low at {vessel['speed_knots']} knots.",
        })

    if vessel["speed_anomaly"]:
        alerts.append({
            "type": "speed_anomaly",
            "severity": "medium",
            "title": "Unusual speed",
            "message": f"Speed appears unusually high at {vessel['speed_knots']} knots.",
        })

    return alerts


def enrich_vessel(vessel: Dict[str, Any]) -> Dict[str, Any]:
    dist_fiji = distance_to_fiji_nm(vessel["lat"], vessel["lon"])
    corridor = corridor_match_score(vessel["lat"], vessel["lon"])
    fiji_bound = likely_fiji_bound(vessel["lat"], vessel["lon"], vessel.get("course"))
    hrs_seen = age_hours(vessel.get("last_seen"))

    vessel["hours_since_seen"] = hrs_seen
    vessel["ais_timeout"] = is_ais_timeout(vessel.get("last_seen"))
    vessel["stale"] = is_stale(vessel.get("last_seen"))
    vessel["unknown_vessel"] = is_unknown_vessel(vessel)
    vessel["loitering"] = is_loitering(vessel)
    vessel["speed_anomaly"] = speed_anomaly(vessel)
    vessel["distance_to_fiji_nm"] = dist_fiji
    vessel["bearing_to_fiji"] = bearing_degrees(
        vessel["lat"], vessel["lon"], Config.FIJI_CENTER["lat"], Config.FIJI_CENTER["lon"]
    )
    vessel["corridor_score"] = round(corridor, 2)
    vessel["fiji_bound"] = fiji_bound
    vessel["route_risk_label"] = route_risk_label(vessel["lat"], vessel["lon"], vessel.get("course"))
    vessel["heading_cardinal"] = heading_to_cardinal(vessel.get("heading"))
    vessel["course_cardinal"] = heading_to_cardinal(vessel.get("course"))
    vessel["confidence_score"] = compute_confidence_score(vessel)

    vessel["suspicious"] = any([
        vessel["ais_timeout"],
        vessel["unknown_vessel"] and vessel["distance_to_fiji_nm"] <= Config.SUSPICIOUS_PROXIMITY_NM,
        vessel["corridor_score"] >= 0.8 and vessel["fiji_bound"],
        vessel["loitering"] and vessel["distance_to_fiji_nm"] <= Config.SUSPICIOUS_PROXIMITY_NM,
        vessel["speed_anomaly"],
    ])

    vessel["marker_color"] = marker_color(vessel)
    vessel["marker_radius"] = marker_radius(vessel)
    vessel["alerts"] = build_alerts(vessel)

    return vessel


def get_vessels():
    vessels = load_raw_vessels()

    # 🚨 FALLBACK if empty
    if not vessels:
        print("⚠️ No live AIS → using fallback vessels")

        vessels = [
            {
                "mmsi": 123456789,
                "name": "PACIFIC TEST 1",
                "lat": -17.8,
                "lon": 178.5,
                "speed": 12.3,
                "course": 90,
                "confidence": 80,
                "suspicious": False
            },
            {
                "mmsi": 987654321,
                "name": "PACIFIC TEST 2",
                "lat": -18.2,
                "lon": 177.9,
                "speed": 5.2,
                "course": 220,
                "confidence": 60,
                "suspicious": True
            }
        ]

    return vessels


def get_summary(vessels: List[Dict[str, Any]]) -> Dict[str, int]:
    return {
        "total_vessels": len(vessels),
        "suspicious_vessels": sum(1 for v in vessels if v["suspicious"]),
        "unknown_vessels": sum(1 for v in vessels if v["unknown_vessel"]),
        "ais_timeouts": sum(1 for v in vessels if v["ais_timeout"]),
        "near_fiji_250nm": sum(1 for v in vessels if v["distance_to_fiji_nm"] <= 250),
        "high_corridor_matches": sum(1 for v in vessels if v["corridor_score"] >= 0.8 and v["fiji_bound"]),
    }


def get_alerts(vessels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    for vessel in vessels:
        for alert in vessel["alerts"]:
            alerts.append({
                "mmsi": vessel.get("mmsi"),
                "name": vessel.get("name"),
                "ship_type": vessel.get("ship_type"),
                "lat": vessel.get("lat"),
                "lon": vessel.get("lon"),
                "speed_knots": vessel.get("speed_knots"),
                "distance_to_fiji_nm": vessel.get("distance_to_fiji_nm"),
                "confidence_score": vessel.get("confidence_score"),
                "last_seen_iso": vessel.get("last_seen_iso"),
                "marker_color": vessel.get("marker_color"),
                **alert,
            })

    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: (severity_order.get(a["severity"], 9), a["distance_to_fiji_nm"]))
    return alerts
