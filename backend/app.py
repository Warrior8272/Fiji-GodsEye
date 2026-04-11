from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
import math

app = Flask(__name__)
CORS(app)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_lower(value):
    return str(value).lower() if value is not None else ""


def severity_rank(severity: str) -> int:
    ranking = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }
    return ranking.get((severity or "").lower(), 0)


def distance_km(lat1, lng1, lat2, lng2):
    r = 6371.0

    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c

# ROUTE HELPERS

def km_per_degree_lat():
    return 111.0 

def km_per_degree_lng(lat):
    return 111.0 * math.cos(math.radians(lat))

def project_position(lat, lng, course_deg, speed_knots, hours):

    if None in (lat, lng, course_deg, speed_knots):
        return None

    distance_km_total = speed_knots * 1.852 * hours

    course_rad = math.radians(course_deg)
 
    north_km = math.cos(course_rad) * distance_km_total
    east_km = math.sin(course_rad) * distance_km_total

    new_lat = + (north_km / 111.0)

    new_lng = lng + (east_km / (111.0 * math.radians(lat)))

    return {"lat": round(new_lat,4), "lng": round(new_lng,4)}

def infer_origin_zone(lat, lng):

    if lat is None or lng is None:
        return "unknown"

    if lat < -25:
        return "deep south pacific"

    if lat < -21:
        return "south pacific corridor"

    if lat < -19:
        return "southern approach"

    return "near fiji waters"

def score_alert(alert):
    score = 0

    severity = safe_lower(alert.get("severity"))
    category = safe_lower(alert.get("category"))
    title = safe_lower(alert.get("title"))
    description = safe_lower(alert.get("description"))
    region = safe_lower(alert.get("region"))

    score += {
        "critical": 100,
        "high": 75,
        "medium": 50,
        "low": 25,
    }.get(severity, 0)

    if category == "phishing":
        score += 15
    elif category == "cyber":
        score += 12
    elif category == "crime":
        score += 14
    elif category == "maritime":
        score += 10
    elif category == "osint":
        score += 8

    high_risk_terms = [
        "bank",
        "narcotics",
        "drug",
        "malware",
        "credential",
        "phishing",
        "smuggling",
        "fraud",
        "scam",
        "ransomware",
    ]

    for term in high_risk_terms:
        if term in title or term in description:
            score += 8

    if "fiji" in region or "suva" in region:
        score += 10

    return score


def sort_alerts(alerts):
    return sorted(
        alerts,
        key=lambda a: (
            a.get("priority_score", 0),
            severity_rank(a.get("severity", "")),
            a.get("timestamp", ""),
        ),
        reverse=True,
    )


# --------------------------------------------------
# SAMPLE DATA
# --------------------------------------------------

def generate_alerts():
    alerts = [
        {
            "id": "ALT-001",
            "title": "Phishing Campaign Targeting Fiji Banks",
            "description": "Fake banking login pages detected targeting Fijian users.",
            "type": "phishing",
            "category": "phishing",
            "severity": "high",
            "source": "OpenPhish",
            "region": "Fiji",
            "timestamp": utc_now(),
            "lat": -18.1416,
            "lng": 178.4419,
        },
        {
            "id": "ALT-002",
            "title": "Malware Alert - Suspicious File Detected",
            "description": "Possible malware spreading via email attachments.",
            "type": "cyber",
            "category": "cyber",
            "severity": "medium",
            "source": "ThreatFeed",
            "region": "Suva",
            "timestamp": utc_now(),
            "lat": -18.1248,
            "lng": 178.4501,
        },
        {
            "id": "ALT-003",
            "title": "Maritime Suspicion Near Southern Route",
            "description": "Vessel movement pattern appears unusual along a known trafficking corridor.",
            "type": "maritime",
            "category": "maritime",
            "severity": "high",
            "source": "AIS Analysis",
            "region": "South of Fiji",
            "timestamp": utc_now(),
            "lat": -19.0,
            "lng": 176.0,
        },
        {
            "id": "ALT-004",
            "title": "Credential Harvesting Scam Reported",
            "description": "Users reported fake password reset pages harvesting credentials.",
            "type": "cyber",
            "category": "cyber",
            "severity": "high",
            "source": "Community Reports",
            "region": "Fiji",
            "timestamp": utc_now(),
            "lat": -18.13,
            "lng": 178.42,
        },
    ]

    for alert in alerts:
        alert["priority_score"] = score_alert(alert)

    return sort_alerts(alerts)


def generate_events():
    return [
        {
            "id": "EVT-001",
            "title": "Public Gathering - Suva",
            "description": "Large gathering reported in Suva.",
            "lat": -18.1416,
            "lng": 178.4419,
            "region": "Suva",
            "timestamp": utc_now(),
            "category": "public_event",
            "severity": "low",
            "source": "Event Feed",
        }
    ]


def generate_crime():
    return [
        {
            "id": "CRM-001",
            "title": "Drug Trafficking Alert",
            "description": "Suspicious maritime route linked to narcotics trade.",
            "lat": -19.0,
            "lng": 176.0,
            "region": "South Pacific Corridor",
            "timestamp": utc_now(),
            "category": "crime",
            "severity": "high",
            "source": "Crime Feed",
        }
    ]


# --------------------------------------------------
# VESSEL INTELLIGENCE
# --------------------------------------------------

def heading_to_text(course_deg):
    if course_deg is None:
        return "unknown"

    directions = [
        "north", "north-east", "east", "south-east",
        "south", "south-west", "west", "north-west"
    ]
    index = round(course_deg / 45) % 8
    return directions[index]


def vessel_suspicion_label(score):
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def analyze_vessel(vessel, alerts, crime_items):
    score = 0
    reasons = []

    name = vessel.get("name")
    lat = vessel.get("lat")
    lng = vessel.get("lng")
    speed = vessel.get("speed_knots")
    course = vessel.get("course_deg")
    identity_known = vessel.get("identity_known", True)
    ais_gap_hours = vessel.get("ais_gap_hours", 0)
    last_port = safe_lower(vessel.get("last_port"))
    destination = safe_lower(vessel.get("destination"))
    region = safe_lower(vessel.get("region"))

    if not identity_known or safe_lower(name) in ["unknown vessel", "unknown", ""]:
        score += 30
        reasons.append("Vessel identity is missing or unresolved.")

    if ais_gap_hours >= 6:
        score += 25
        reasons.append(f"AIS tracking gap detected ({ais_gap_hours} hours).")

    if "south pacific corridor" in region or "south of fiji" in region:
        score += 20
        reasons.append("Vessel is operating in a high-risk southern Pacific corridor.")

    if speed is not None and speed < 3:
        score += 10
        reasons.append("Very low speed may indicate loitering or waiting activity.")

    if destination in ["unknown", "", "n/a"]:
        score += 10
        reasons.append("Destination data is missing or unclear.")

    if last_port in ["unknown", "", "n/a"]:
        score += 8
        reasons.append("Last known port is missing.")

    nearest_crime = None
    nearest_crime_distance = None

    for crime in crime_items:
        if None not in (lat, lng, crime.get("lat"), crime.get("lng")):
            dist = distance_km(lat, lng, crime["lat"], crime["lng"])
            if nearest_crime_distance is None or dist < nearest_crime_distance:
                nearest_crime_distance = dist
                nearest_crime = crime

    if nearest_crime_distance is not None and nearest_crime_distance <= 250:
        score += 20
        reasons.append(
            f"Vessel is within {nearest_crime_distance:.1f} km of a crime-related maritime alert."
        )

    nearby_maritime_alerts = []
    for alert in alerts:
        if safe_lower(alert.get("category")) == "maritime":
            if None not in (lat, lng, alert.get("lat"), alert.get("lng")):
                dist = distance_km(lat, lng, alert["lat"], alert["lng"])
                if dist <= 300:
                    nearby_maritime_alerts.append({
                        "id": alert["id"],
                        "title": alert["title"],
                        "distance_km": round(dist, 1),
                    })

    if nearby_maritime_alerts:
        score += 15
        reasons.append("Vessel is close to one or more maritime anomaly alerts.")

    inferred_heading = heading_to_text(course)
    if inferred_heading in ["north", "north-east", "north-west"]:
        score += 8
        reasons.append(
            f"Current course suggests movement {inferred_heading} toward Fiji-facing waters."
        )

    summary = (
        f"{name} is assessed as {vessel_suspicion_label(score).upper()} risk. "
        f"Primary concerns include identity status, operating area, tracking continuity, "
        f"and proximity to maritime/crime indicators."
    )

    return {
        **vessel,
        "risk_score": score,
        "risk_level": vessel_suspicion_label(score),
        "inferred_heading": inferred_heading,
        "analysis_summary": summary,
        "risk_reasons": reasons,
        "nearest_crime_distance_km": round(nearest_crime_distance, 1) if nearest_crime_distance is not None else None,
        "nearest_crime_title": nearest_crime.get("title") if nearest_crime else None,
        "nearby_maritime_alerts": nearby_maritime_alerts,
    }


def generate_ships():
    base_ships = [
        {
            "id": "SHP-001",
            "name": "Cargo Vessel A",
            "lat": -18.1248,
            "lng": 178.4501,
            "region": "Suva Waters",
            "timestamp": utc_now(),
            "source": "AIS Feed",
            "identity_known": True,
            "speed_knots": 11.4,
            "course_deg": 35,
            "destination": "Suva",
            "last_port": "Lautoka",
            "ais_gap_hours": 0,
        },
        {
            "id": "SHP-002",
            "name": "Unknown Vessel",
            "lat": -20.5,
            "lng": 175.2,
            "region": "South Pacific Corridor",
            "timestamp": utc_now(),
            "source": "AIS Feed",
            "identity_known": False,
            "speed_knots": 2.1,
            "course_deg": 28,
            "destination": "Unknown",
            "last_port": "Unknown",
            "ais_gap_hours": 8,
        },
    ]

    alerts = generate_alerts()
    crime_items = generate_crime()

    analyzed = [analyze_vessel(vessel, alerts, crime_items) for vessel in base_ships]
    analyzed.sort(key=lambda v: v.get("risk_score", 0), reverse=True)
    return analyzed


# --------------------------------------------------
# CORRELATION ENGINE
# --------------------------------------------------

def build_correlations(alerts, ships, events, crime_items):
    correlations = []

    for alert in alerts:
        alert_title = safe_lower(alert.get("title"))
        alert_desc = safe_lower(alert.get("description"))
        alert_category = safe_lower(alert.get("category"))
        alert_lat = alert.get("lat")
        alert_lng = alert.get("lng")

        for crime in crime_items:
            crime_title = safe_lower(crime.get("title"))
            crime_desc = safe_lower(crime.get("description"))

            keyword_match = any(
                term in alert_title or term in alert_desc
                for term in ["drug", "narcotics", "smuggling", "fraud", "scam", "phishing"]
            ) and any(
                term in crime_title or term in crime_desc
                for term in ["drug", "narcotics", "smuggling", "fraud", "scam", "phishing"]
            )

            geo_match = False
            if None not in (alert_lat, alert_lng, crime.get("lat"), crime.get("lng")):
                geo_match = distance_km(alert_lat, alert_lng, crime["lat"], crime["lng"]) <= 250

            if keyword_match or geo_match:
                correlations.append({
                    "type": "alert_crime",
                    "severity": "high" if geo_match else "medium",
                    "summary": f"{alert['title']} correlated with crime item: {crime['title']}",
                    "alert_id": alert["id"],
                    "crime_id": crime["id"],
                    "region": crime.get("region", "Unknown"),
                    "timestamp": utc_now(),
                    "confidence": "high" if keyword_match and geo_match else "medium",
                })

        for ship in ships:
            ship_lat = ship.get("lat")
            ship_lng = ship.get("lng")
            ship_risk = safe_lower(ship.get("risk_level"))

            geo_match = False
            if None not in (alert_lat, alert_lng, ship_lat, ship_lng):
                geo_match = distance_km(alert_lat, alert_lng, ship_lat, ship_lng) <= 300

            suspicious_alert = alert_category in ["maritime", "crime"] or any(
                term in alert_title or term in alert_desc
                for term in ["vessel", "route", "smuggling", "narcotics", "maritime"]
            )

            if geo_match and (suspicious_alert or ship_risk in ["high", "critical"]):
                correlations.append({
                    "type": "alert_ship",
                    "severity": "high" if ship_risk in ["high", "critical"] else "medium",
                    "summary": f"{alert['title']} geographically linked to vessel: {ship['name']}",
                    "alert_id": alert["id"],
                    "ship_id": ship["id"],
                    "region": ship.get("region", "Unknown"),
                    "timestamp": utc_now(),
                    "confidence": "high" if ship_risk in ["high", "critical"] else "medium",
                })

        for event in events:
            event_lat = event.get("lat")
            event_lng = event.get("lng")

            geo_match = False
            if None not in (alert_lat, alert_lng, event_lat, event_lng):
                geo_match = distance_km(alert_lat, alert_lng, event_lat, event_lng) <= 80

            if geo_match and alert_category in ["cyber", "phishing", "crime"]:
                correlations.append({
                    "type": "alert_event",
                    "severity": "medium",
                    "summary": f"{alert['title']} is near event location: {event['title']}",
                    "alert_id": alert["id"],
                    "event_id": event["id"],
                    "region": event.get("region", "Unknown"),
                    "timestamp": utc_now(),
                    "confidence": "low",
                })

    correlations.sort(
        key=lambda c: (severity_rank(c.get("severity", "")), c.get("timestamp", "")),
        reverse=True,
    )
    return correlations


# --------------------------------------------------
# API ROUTES
# --------------------------------------------------

@app.route("/")
def index():
    return jsonify({
        "message": "God's Eye Pacific Phase 11 Backend Running",
        "version": "phase-11",
        "endpoints": [
            "/api/alerts",
            "/api/ships",
            "/api/events",
            "/api/crime",
            "/api/correlations",
            "/api/summary",
            "/api/vessel-intel",
        ],
    })


@app.route("/api/alerts")
def alerts():
    return jsonify(generate_alerts())


@app.route("/api/ships")
def ships():
    return jsonify(generate_ships())


@app.route("/api/events")
def events():
    return jsonify(generate_events())


@app.route("/api/crime")
def crime():
    return jsonify(generate_crime())


@app.route("/api/correlations")
def correlations():
    alerts_data = generate_alerts()
    ships_data = generate_ships()
    events_data = generate_events()
    crime_data = generate_crime()
    return jsonify(build_correlations(alerts_data, ships_data, events_data, crime_data))


@app.route("/api/vessel-intel")
def vessel_intel():
    ships_data = generate_ships()
    return jsonify({
        "generated_at": utc_now(),
        "high_risk_vessels": [s for s in ships_data if s.get("risk_level") in ["high", "critical"]],
        "all_vessels": ships_data,
        "top_vessel": ships_data[0] if ships_data else None,
    })


@app.route("/api/summary")
def summary():
    alerts_data = generate_alerts()
    ships_data = generate_ships()
    events_data = generate_events()
    crime_data = generate_crime()
    correlation_data = build_correlations(alerts_data, ships_data, events_data, crime_data)

    high_priority_alerts = [a for a in alerts_data if a.get("priority_score", 0) >= 80]
    high_risk_ships = [s for s in ships_data if s.get("risk_level") in ["high", "critical"]]

    return jsonify({
        "generated_at": utc_now(),
        "totals": {
            "alerts": len(alerts_data),
            "ships": len(ships_data),
            "events": len(events_data),
            "crime": len(crime_data),
            "correlations": len(correlation_data),
        },
        "high_priority_alerts": len(high_priority_alerts),
        "high_risk_ships": len(high_risk_ships),
        "top_alert": alerts_data[0] if alerts_data else None,
        "top_correlation": correlation_data[0] if correlation_data else None,
        "top_vessel": ships_data[0] if ships_data else None,
    })


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
