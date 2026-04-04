from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WATCH_ZONE = {
    "minLat": -18.5,
    "maxLat": -17.5,
    "minLon": 177.5,
    "maxLon": 178.5,
}

MAX_HISTORY = 5

ship_positions = [
    {
        "name": "Cargo Alpha",
        "type": "cargo",
        "routeSegments": [
            [[-15.0, -120.0], [-16.0, -100.0], [-17.0, -80.0], [-18.0, 178.0]]
        ],
        "index": 0,
        "history": [],
    },
    {
        "name": "Tanker Pacific",
        "type": "tanker",
        "routeSegments": [
            [[-20.0, -130.0], [-19.0, -110.0], [-18.0, -90.0], [-17.0, 178.0]]
        ],
        "index": 0,
        "history": [],
    },
    {
        "name": "Fishing Vessel Fiji",
        "type": "fishing",
        "routeSegments": [
            [[-17.7, 177.9], [-17.8, 178.1], [-17.9, 178.3]]
        ],
        "index": 0,
        "history": [],
    },
]


def flatten_route_segments(route_segments):
    points = []
    for segment in route_segments:
        points.extend(segment)
    return points


def is_inside_watch_zone(lat, lon):
    return (
        WATCH_ZONE["minLat"] <= lat <= WATCH_ZONE["maxLat"]
        and WATCH_ZONE["minLon"] <= lon <= WATCH_ZONE["maxLon"]
    )


def zone_center():
    return (
        (WATCH_ZONE["minLat"] + WATCH_ZONE["maxLat"]) / 2,
        (WATCH_ZONE["minLon"] + WATCH_ZONE["maxLon"]) / 2,
    )


def distance_to_zone_center(lat, lon):
    center_lat, center_lon = zone_center()
    return math.sqrt((lat - center_lat) ** 2 + (lon - center_lon) ** 2)


def detect_suspicious_behavior(ship_data):
    history = ship_data.get("history", [])
    if len(history) < 3:
        return False

    last = history[-1]
    prev = history[-2]
    dx = last[1] - prev[1]
    dy = last[0] - prev[0]

    return abs(dx) > 1 or abs(dy) > 1


def calculate_eta(ship, target_lat=-17.8, target_lon=178.0):
    dx = target_lon - ship["lon"]
    dy = target_lat - ship["lat"]
    distance = math.sqrt(dx**2 + dy**2)
    speed = ship.get("speed", 0.5)

    if speed == 0:
        return "Unknown"

    return round(distance / speed, 2)


def calculate_threat_score(ship):
    score = 0

    if ship.get("type") == "tanker":
        score += 3
    elif ship.get("type") == "cargo":
        score += 2
    elif ship.get("type") == "fishing":
        score += 1

    if ship.get("inside_zone"):
        score += 2

    if ship.get("origin") == "south_america":
        score += 3

    if ship.get("suspicious"):
        score += 2

    return score


def get_behavior_status(ship):
    history = ship.get("history", [])
    lat = ship["lat"]
    lon = ship["lon"]

    if is_inside_watch_zone(lat, lon):
        return "inside zone"

    if len(history) < 2:
        return "outside zone"

    prev_lat, prev_lon = history[-2]
    current_distance = distance_to_zone_center(lat, lon)
    previous_distance = distance_to_zone_center(prev_lat, prev_lon)

    movement = math.sqrt((lat - prev_lat) ** 2 + (lon - prev_lon) ** 2)

    if movement < 0.05:
        return "loitering"

    if current_distance < previous_distance:
        return "approaching zone"

    if current_distance > previous_distance:
        return "leaving zone"

    return "outside zone"


@app.get("/")
def home():
    return {"status": "Backend running"}


@app.get("/api/live-ships")
def get_live_ships():
    output = []

    for ship_data in ship_positions:
        all_points = flatten_route_segments(ship_data["routeSegments"])

        ship_data["index"] = (ship_data["index"] + 1) % len(all_points)
        lat, lon = all_points[ship_data["index"]]

        ship_data["history"].append([lat, lon])
        if len(ship_data["history"]) > MAX_HISTORY:
            ship_data["history"] = ship_data["history"][-MAX_HISTORY:]

        origin = "south_america"
        suspicious = detect_suspicious_behavior(ship_data)
        inside_zone = is_inside_watch_zone(lat, lon)

        ship = {
            "name": ship_data["name"],
            "lat": lat,
            "lon": lon,
            "type": ship_data["type"],
            "status": "moving",
            "history": ship_data["history"],
            "routeSegments": ship_data["routeSegments"],
            "origin": origin,
            "suspicious": suspicious,
            "inside_zone": inside_zone,
            "speed": 0.5,
        }

        ship["threat_score"] = calculate_threat_score(ship)

        if ship["threat_score"] >= 6:
            ship["threat_level"] = "HIGH"
        elif ship["threat_score"] >= 3:
            ship["threat_level"] = "MEDIUM"
        else:
            ship["threat_level"] = "LOW"

        ship["eta_hours"] = calculate_eta(ship)
        ship["status"] = get_behavior_status(ship)

        output.append(ship)

    return output


@app.get("/api/alerts")
def get_alerts():
    ships = get_live_ships()
    alerts = []

    for ship in ships:
        lat = ship["lat"]
        lon = ship["lon"]
        ship_type = ship.get("type", "unknown")
        name = ship["name"]
        status = ship.get("status", "outside zone")
        in_zone = is_inside_watch_zone(lat, lon)

        if in_zone:
            alerts.append({
                "title": f"Zone entry detected: {name}",
                "message": f"{name} has entered the Fiji monitoring zone.",
                "severity": "medium",
                "ship": name,
                "type": ship_type,
                "risk_score": ship["threat_score"],
            })

        if ship_type == "tanker" and in_zone:
            alerts.append({
                "title": f"HIGH RISK: Tanker in Fiji zone",
                "message": f"{name} is a tanker operating inside the monitored zone.",
                "severity": "high",
                "ship": name,
                "type": ship_type,
                "risk_score": ship["threat_score"],
            })

        if ship.get("origin") == "south_america":
            alerts.append({
                "title": f"High-risk origin: {name}",
                "message": "Route appears to originate from South America region.",
                "severity": "high",
                "ship": name,
                "type": ship_type,
                "risk_score": ship["threat_score"],
            })

        if status == "approaching zone":
            alerts.append({
                "title": f"Approaching zone: {name}",
                "message": f"{name} is moving toward the Fiji watch zone.",
                "severity": "medium",
                "ship": name,
                "type": ship_type,
                "risk_score": ship["threat_score"],
            })

        if ship["threat_level"] == "HIGH":
            alerts.append({
                "title": f"High Threat Vessel: {name}",
                "message": f"Threat score {ship['threat_score']} - ETA {ship['eta_hours']} hrs",
                "severity": "high",
                "ship": name,
                "type": ship_type,
                "risk_score": ship["threat_score"],
            })

    return alerts


@app.get("/api/cyber-alerts")
def get_cyber_alerts():
    return [
        {
            "title": "Phishing campaign targeting Fiji banking users",
            "message": "Multiple reports of fake banking login pages targeting users in Suva.",
            "severity": "high",
            "category": "phishing",
            "location": "Suva",
            "lat": -18.1416,
            "lon": 178.4419,
            "heat": 9,
        },
        {
            "title": "Suspicious login attempts against government portal",
            "message": "Repeated login attempts detected against a public-facing portal.",
            "severity": "medium",
            "category": "intrusion",
            "location": "Nadi",
            "lat": -17.7765,
            "lon": 177.4357,
            "heat": 6,
        },
        {
            "title": "Scam investment pages shared on social media",
            "message": "Fraudulent investment links circulating across public social channels.",
            "severity": "medium",
            "category": "scam",
            "location": "Labasa",
            "lat": -16.4332,
            "lon": 179.3645,
            "heat": 5,
        },
    ]


def detect_correlation(ships, cyber_alerts):
    correlations = []

    for ship in ships:
        for alert in cyber_alerts:
            location_match = alert["location"].lower() in ["suva", "nadi", "labasa"]
            high_risk_ship = ship.get("threat_score", 0) >= 3
            inside_zone = ship.get("inside_zone")

            if location_match and (high_risk_ship or inside_zone):
                correlations.append({
                    "title": "Correlated Threat Detected",
                    "message": f"{ship['name']} ({ship['type']}) near {alert['location']} during {alert['category']} activity",
                    "severity": "high",
                    "priority": ship.get("threat_score", 0) + (2 if alert["severity"] == "high" else 1),
                })

    return correlations


@app.get("/api/correlations")
def get_correlations():
    ships = get_live_ships()
    cyber = get_cyber_alerts()
    return detect_correlation(ships, cyber)
