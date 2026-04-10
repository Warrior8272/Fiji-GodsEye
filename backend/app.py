from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import math
import asyncio
import threading
import requests
import websockets

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

AISSTREAM_API_KEY = os.getenv("AISSTREAM_API_KEY", "").strip()

live_ais_ships = []
live_ais_lock = threading.Lock()

SIM_SHIPS = [
    {
        "name": "Cargo Alpha",
        "lat": -17.9,
        "lon": 178.3,
        "type": "cargo",
        "status": "moving",
        "history": [[-17.5, 178.0], [-17.7, 178.2], [-17.9, 178.3]],
        "routeSegments": [[[-15.0, -120.0], [-18.0, 178.0]]],
        "inside_zone": True,
        "origin": "south_america",
        "suspicious": False,
        "source": "simulation",
        "speed": 12.0,
        "entry_count": 2,
    },
    {
        "name": "Tanker Pacific",
        "lat": -17.8,
        "lon": 178.1,
        "type": "tanker",
        "status": "inside zone",
        "history": [[-18.2, 178.0], [-18.0, 178.1], [-17.8, 178.1]],
        "routeSegments": [[[-20.0, -130.0], [-17.0, 178.0]]],
        "inside_zone": True,
        "origin": "south_america",
        "suspicious": True,
        "source": "simulation",
        "speed": 8.0,
        "entry_count": 3,
    },
    {
        "name": "Fishing Vessel Fiji",
        "lat": -17.7,
        "lon": 177.9,
        "type": "fishing",
        "status": "moving",
        "history": [[-17.6, 177.8], [-17.7, 177.85], [-17.7, 177.9]],
        "routeSegments": [[[-17.6, 177.8], [-17.7, 177.9]]],
        "inside_zone": True,
        "origin": "local",
        "suspicious": False,
        "source": "simulation",
        "speed": 5.0,
        "entry_count": 1,
    },
]


def is_inside_watch_zone(lat: float, lon: float) -> bool:
    return (
        WATCH_ZONE["minLat"] <= lat <= WATCH_ZONE["maxLat"]
        and WATCH_ZONE["minLon"] <= lon <= WATCH_ZONE["maxLon"]
    )


def calculate_eta_hours(lat: float, lon: float, target_lat=-17.8, target_lon=178.0):
    dx = target_lon - lon
    dy = target_lat - lat
    distance = math.sqrt(dx**2 + dy**2)
    speed = 0.5
    if speed == 0:
        return "Unknown"
    return round(distance / speed, 2)


def score_to_level(score: int) -> str:
    if score >= 8:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


def classify_ship_type(ship_name: str) -> str:
    name = ship_name.lower()
    if "tanker" in name:
        return "tanker"
    if "cargo" in name:
        return "cargo"
    if "fish" in name:
        return "fishing"
    return "unknown"


def detect_loitering(history):
    if not history or len(history) < 3:
        return False

    lats = [p[0] for p in history[-5:]]
    lons = [p[1] for p in history[-5:]]
    lat_spread = max(lats) - min(lats)
    lon_spread = max(lons) - min(lons)

    return lat_spread < 0.03 and lon_spread < 0.03


def unusual_speed(speed, ship_type):
    if speed is None:
        return False

    if ship_type == "fishing" and speed > 18:
        return True
    if ship_type in ["cargo", "tanker"] and speed > 25:
        return True
    if speed < 0.5:
        return True
    return False


def calculate_threat_score(ship: dict) -> int:
    score = 0

    if ship["type"] == "tanker":
        score += 3
    elif ship["type"] == "cargo":
        score += 2
    elif ship["type"] == "fishing":
        score += 1

    if ship.get("inside_zone"):
        score += 2

    if ship.get("origin") == "south_america":
        score += 3

    if ship.get("suspicious"):
        score += 2

    if ship.get("loitering"):
        score += 2

    if ship.get("unusual_speed"):
        score += 2

    if ship.get("entry_count", 0) >= 2:
        score += 1

    if ship.get("source") == "aisstream":
        score += 1

    return score


def fetch_openphish_feed(limit=25):
    url = "https://openphish.com/feed.txt"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        lines = [line.strip() for line in resp.text.splitlines() if line.strip()]
    except Exception as exc:
        print(f"OpenPhish fetch failed: {exc}")
        return []

    alerts = []
    fiji_targets = [
        ("fiji", -18.1416, 178.4419, "Suva"),
        ("suva", -18.1416, 178.4419, "Suva"),
        ("nadi", -17.7765, 177.4357, "Nadi"),
        ("labasa", -16.4332, 179.3645, "Labasa"),
        ("westpac", -18.1416, 178.4419, "Suva"),
        ("anz", -18.1416, 178.4419, "Suva"),
        ("bsp", -18.1416, 178.4419, "Suva"),
        ("vodafone", -18.1416, 178.4419, "Suva"),
        ("mytsp", -18.1416, 178.4419, "Suva"),
        ("gov", -18.1416, 178.4419, "Suva"),
        (".fj", -18.1416, 178.4419, "Suva"),
    ]

    for phish_url in lines[:limit]:
        matched = None
        lower_url = phish_url.lower()
        for keyword, lat, lon, location in fiji_targets:
            if keyword in lower_url:
                matched = (lat, lon, location)
                break

        # If no Fiji keyword match, still surface a few as generic regional OSINT.
        if matched:
            lat, lon, location = matched
            severity = "high"
            confidence = "medium"
            message = f"OpenPhish feed matched Fiji-related keyword in URL: {phish_url}"
        else:
            lat, lon, location = -18.1416, 178.4419, "Suva"
            severity = "medium"
            confidence = "low"
            message = f"OpenPhish active phishing URL observed; geotagged as regional OSINT lead: {phish_url}"

        alerts.append({
            "title": "OpenPhish phishing alert",
            "message": message,
            "severity": severity,
            "category": "phishing",
            "location": location,
            "lat": lat,
            "lon": lon,
            "heat": 8 if severity == "high" else 5,
            "source": "openphish",
            "confidence": confidence,
            "ioc": phish_url,
            "verification": "osint",
        })

    return alerts


def get_cyber_alerts_data():
    static_alerts = [
        {
            "title": "Phishing campaign targeting Fiji banking users",
            "message": "Multiple reports of fake banking login pages targeting users in Suva.",
            "severity": "high",
            "category": "phishing",
            "location": "Suva",
            "lat": -18.1416,
            "lon": 178.4419,
            "heat": 9,
            "source": "simulation",
            "confidence": "training",
            "verification": "simulation",
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
            "source": "simulation",
            "confidence": "training",
            "verification": "simulation",
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
            "source": "simulation",
            "confidence": "training",
            "verification": "simulation",
        },
    ]

    openphish_alerts = fetch_openphish_feed(limit=20)
    return static_alerts + openphish_alerts


def build_threat_labels(ship: dict, cyber_alerts: list) -> list[str]:
    labels = []

    if ship.get("source") == "aisstream":
        labels.append("Live AIS")

    if ship.get("origin") == "south_america":
        labels.append("Drug trafficking risk")

    if ship.get("suspicious"):
        labels.append("Suspicious route")

    if ship.get("inside_zone"):
        labels.append("Inside watch zone")

    if ship.get("type") == "tanker":
        labels.append("High-value tanker")

    if ship.get("type") == "cargo":
        labels.append("Cargo monitoring priority")

    if ship.get("loitering"):
        labels.append("Loitering behaviour")

    if ship.get("unusual_speed"):
        labels.append("Unusual speed")

    if ship.get("entry_count", 0) >= 2:
        labels.append("Repeated zone entry")

    matched_locations = {"suva", "nadi", "labasa"}
    if ship.get("inside_zone") and any(
        alert.get("location", "").lower() in matched_locations for alert in cyber_alerts
    ):
        labels.append("Cyber-linked area")

    if ship.get("threat_level") == "HIGH":
        labels.append("Priority target")

    return labels


def enrich_ship(ship: dict) -> dict:
    cyber_alerts = get_cyber_alerts_data()
    ship_copy = dict(ship)

    ship_copy["inside_zone"] = is_inside_watch_zone(ship_copy["lat"], ship_copy["lon"])
    ship_copy["loitering"] = detect_loitering(ship_copy.get("history", []))
    ship_copy["unusual_speed"] = unusual_speed(ship_copy.get("speed"), ship_copy.get("type"))
    ship_copy["threat_score"] = calculate_threat_score(ship_copy)
    ship_copy["threat_level"] = score_to_level(ship_copy["threat_score"])
    ship_copy["eta_hours"] = calculate_eta_hours(ship_copy["lat"], ship_copy["lon"])
    ship_copy["threat_labels"] = build_threat_labels(ship_copy, cyber_alerts)

    return ship_copy


def normalize_live_ship(msg: dict):
    lat = msg.get("Latitude")
    lon = msg.get("Longitude")
    mmsi = msg.get("UserID")
    speed = msg.get("Sog")

    if lat is None or lon is None or mmsi is None:
        return None

    name = f"Live-{mmsi}"
    ship_type = classify_ship_type(name)

    ship = {
        "name": name,
        "lat": float(lat),
        "lon": float(lon),
        "type": ship_type,
        "status": "live",
        "history": [[float(lat), float(lon)]],
        "routeSegments": [],
        "origin": "live",
        "suspicious": False,
        "source": "aisstream",
        "speed": float(speed or 0),
        "entry_count": 1,
    }

    return enrich_ship(ship)


async def aisstream_listener():
    if not AISSTREAM_API_KEY:
        print("AISSTREAM_API_KEY not set, using simulation only.")
        return

    uri = "wss://stream.aisstream.io/v0/stream"

    while True:
        try:
            async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as websocket:
                subscribe_message = {
                    "APIKey": AISSTREAM_API_KEY,
                    "BoundingBoxes": [[[-25.0, 160.0], [-10.0, 190.0]]]
                }

                await websocket.send(json.dumps(subscribe_message))
                print("Connected to AISStream.")

                while True:
                    raw_message = await websocket.recv()
                    data = json.loads(raw_message)

                    message = data.get("Message", {})
                    position_report = message.get("PositionReport")
                    if not position_report:
                        continue

                    ship = normalize_live_ship(position_report)
                    if not ship:
                        continue

                    with live_ais_lock:
                        existing_index = next(
                            (i for i, s in enumerate(live_ais_ships) if s["name"] == ship["name"]),
                            None,
                        )

                        if existing_index is not None:
                            old_ship = live_ais_ships[existing_index]
                            old_history = old_ship.get("history", [])
                            old_history.append([ship["lat"], ship["lon"]])

                            old_entry_count = old_ship.get("entry_count", 1)
                            previously_inside = old_ship.get("inside_zone", False)
                            now_inside = is_inside_watch_zone(ship["lat"], ship["lon"])

                            if now_inside and not previously_inside:
                                old_entry_count += 1

                            ship["history"] = old_history[-10:]
                            ship["entry_count"] = old_entry_count
                            ship = enrich_ship(ship)
                            live_ais_ships[existing_index] = ship
                        else:
                            live_ais_ships.append(ship)

                        if len(live_ais_ships) > 50:
                            del live_ais_ships[:-50]

        except Exception as exc:
            print(f"AISStream connection error: {exc}")
            await asyncio.sleep(5)


def start_aisstream_background():
    def runner():
        asyncio.run(aisstream_listener())

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()


start_aisstream_background()


def get_live_ships_data():
    with live_ais_lock:
      live_copy = [dict(ship) for ship in live_ais_ships]

    if live_copy:
        return live_copy + [enrich_ship(ship) for ship in SIM_SHIPS]

    return [enrich_ship(ship) for ship in SIM_SHIPS]


@app.get("/")
def home():
    return {"status": "Backend running"}


@app.get("/api/live-ships")
def get_live_ships():
    return get_live_ships_data()


@app.get("/api/alerts")
def get_alerts():
    ships = get_live_ships_data()
    alerts = []

    for ship in ships:
        if ship["inside_zone"]:
            alerts.append({
                "title": f"Zone entry detected: {ship['name']}",
                "message": f"{ship['name']} is operating inside the Fiji watch zone.",
                "severity": "medium",
                "type": ship["type"],
                "risk_score": ship["threat_score"],
            })

        if ship["threat_level"] == "HIGH":
            alerts.append({
                "title": f"High Threat Vessel: {ship['name']}",
                "message": f"Threat score {ship['threat_score']} - ETA {ship['eta_hours']} hrs",
                "severity": "high",
                "type": ship["type"],
                "risk_score": ship["threat_score"],
            })

    return alerts


@app.get("/api/cyber-alerts")
def get_cyber_alerts():
    return get_cyber_alerts_data()


def severity_score(severity: str) -> int:
    sev = (severity or "").lower()
    if sev == "high":
        return 4
    if sev == "medium":
        return 2
    return 1


def source_score(source: str) -> int:
    src = (source or "").lower()
    if src == "openphish":
        return 3
    if src == "simulation":
        return 1
    return 2


def location_match_score(ship: dict, alert: dict) -> int:
    ship_lat = ship.get("lat")
    ship_lon = ship.get("lon")
    alert_lat = alert.get("lat")
    alert_lon = alert.get("lon")

    if None in [ship_lat, ship_lon, alert_lat, alert_lon]:
        return 0

    distance = distance_km(ship_lat, ship_lon, alert_lat, alert_lon)

    if distance <= 10:
        return 4
    if distance <= 25:
        return 3
    if distance <= 50:
        return 2
    if distance <= 100:
        return 1
    return 0


def time_proximity_score(ship: dict, alert: dict) -> int:
    # Placeholder for now until you add timestamps to all feeds.
    # Gives live AIS and live OSINT feeds more weight than simulation.
    ship_source = (ship.get("source") or "").lower()
    alert_verification = (alert.get("verification") or "").lower()
    alert_source = (alert.get("source") or "").lower()

    score = 0

    if ship_source == "aisstream":
        score += 2
    elif ship_source == "simulation":
        score += 1

    if alert_source == "openphish":
        score += 2
    elif alert_verification == "simulation":
        score += 1

    return score


def correlation_level(score: int) -> str:
    if score >= 12:
        return "HIGH"
    if score >= 8:
        return "MEDIUM"
    return "LOW"

def severity_score(severity: str) -> int:
    sev = (severity or "").lower()
    if sev == "high":
        return 4
    if sev == "medium":
        return 2
    return 1


def source_score(source: str) -> int:
    src = (source or "").lower()
    if src == "openphish":
        return 3
    if src == "simulation":
        return 1
    return 2


def location_match_score(ship: dict, alert: dict) -> int:
    ship_lat = ship.get("lat")
    ship_lon = ship.get("lon")
    alert_lat = alert.get("lat")
    alert_lon = alert.get("lon")

    if None in [ship_lat, ship_lon, alert_lat, alert_lon]:
        return 0

    distance = distance_km(ship_lat, ship_lon, alert_lat, alert_lon)

    if distance <= 10:
        return 4
    if distance <= 25:
        return 3
    if distance <= 50:
        return 2
    if distance <= 100:
        return 1
    return 0


def time_proximity_score(ship: dict, alert: dict) -> int:
    # Placeholder for now until you add timestamps to all feeds.
    # Gives live AIS and live OSINT feeds more weight than simulation.
    ship_source = (ship.get("source") or "").lower()
    alert_verification = (alert.get("verification") or "").lower()
    alert_source = (alert.get("source") or "").lower()

    score = 0

    if ship_source == "aisstream":
        score += 2
    elif ship_source == "simulation":
        score += 1

    if alert_source == "openphish":
        score += 2
    elif alert_verification == "simulation":
        score += 1

    return score


def correlation_level(score: int) -> str:
    if score >= 12:
        return "HIGH"
    if score >= 8:
        return "MEDIUM"
    return "LOW"


def distance_km(lat1, lon1, lat2, lon2):
    def to_rad(deg):
        return deg * math.pi / 180

    r = 6371
    dlat = to_rad(lat2 - lat1)
    dlon = to_rad(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(to_rad(lat1))
        * math.cos(to_rad(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def detect_correlation(ships, cyber_alerts):
    correlations = []

    for ship in ships:
        for alert in cyber_alerts:
            loc_score = location_match_score(ship, alert)
            if loc_score == 0:
                continue

            ship_score = ship.get("threat_score", 0)
            cyber_score = severity_score(alert.get("severity"))
            credibility = source_score(alert.get("source"))
            time_score = time_proximity_score(ship, alert)

            total_score = ship_score + cyber_score + credibility + time_score + loc_score
            level = correlation_level(total_score)

            correlations.append({
                "title": "Correlated Threat Detected",
                "message": f"{ship['name']} ({ship['type']}) near {alert['location']} during {alert['category']} activity",
                "severity": level.lower(),
                "priority": total_score,
                "correlation_confidence": level,
                "distance_km": round(
                    distance_km(ship["lat"], ship["lon"], alert["lat"], alert["lon"]), 2
                ),
                "ship_name": ship["name"],
                "ship_type": ship["type"],
                "ship_source": ship.get("source"),
                "ship_risk_score": ship_score,
                "alert_title": alert.get("title"),
                "alert_source": alert.get("source"),
                "alert_verification": alert.get("verification"),
                "alert_severity": alert.get("severity"),
            })

    correlations.sort(key=lambda x: x["priority"], reverse=True)
    return correlations[:20]
