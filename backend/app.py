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
        "threat_score": 4,
        "threat_level": "MEDIUM",
        "eta_hours": 12,
        "history": [[-17.5, 178.0], [-17.7, 178.2], [-17.9, 178.3]],
        "routeSegments": [[[-15.0, -120.0], [-18.0, 178.0]]],
        "inside_zone": True,
        "origin": "south_america",
        "suspicious": False,
        "source": "simulation",
    },
    {
        "name": "Tanker Pacific",
        "lat": -17.8,
        "lon": 178.1,
        "type": "tanker",
        "status": "inside zone",
        "threat_score": 6,
        "threat_level": "HIGH",
        "eta_hours": 5,
        "history": [[-18.2, 178.0], [-18.0, 178.1], [-17.8, 178.1]],
        "routeSegments": [[[-20.0, -130.0], [-17.0, 178.0]]],
        "inside_zone": True,
        "origin": "south_america",
        "suspicious": True,
        "source": "simulation",
    },
    {
        "name": "Fishing Vessel Fiji",
        "lat": -17.7,
        "lon": 177.9,
        "type": "fishing",
        "status": "moving",
        "threat_score": 2,
        "threat_level": "LOW",
        "eta_hours": 2,
        "history": [[-17.6, 177.8], [-17.7, 177.85], [-17.7, 177.9]],
        "routeSegments": [[[-17.6, 177.8], [-17.7, 177.9]]],
        "inside_zone": True,
        "origin": "local",
        "suspicious": False,
        "source": "simulation",
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
    if score >= 6:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"


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

    return score


def get_cyber_alerts_data():
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


def build_threat_labels(ship: dict, cyber_alerts: list) -> list[str]:
    labels = []

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
    ship_copy["threat_score"] = calculate_threat_score(ship_copy)
    ship_copy["threat_level"] = score_to_level(ship_copy["threat_score"])
    ship_copy["eta_hours"] = calculate_eta_hours(ship_copy["lat"], ship_copy["lon"])
    ship_copy["threat_labels"] = build_threat_labels(ship_copy, cyber_alerts)
    return ship_copy


def classify_ship_type(ship_name: str) -> str:
    name = ship_name.lower()

    if "tanker" in name:
        return "tanker"
    if "cargo" in name:
        return "cargo"
    if "fish" in name:
        return "fishing"
    return "unknown"


def normalize_live_ship(msg: dict) -> dict | None:
    lat = msg.get("Latitude")
    lon = msg.get("Longitude")
    mmsi = msg.get("UserID")

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
                    "BoundingBoxes": [[[ -25.0, 160.0 ], [ -10.0, 190.0 ]]]
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
                            ship["history"] = old_history[-10:]
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
    ships = get_live_ships_data()
    cyber = get_cyber_alerts_data()
    return detect_correlation(ships, cyber)

