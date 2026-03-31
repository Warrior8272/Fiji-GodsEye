from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Backend running"}

@app.get("/api/ships")
def get_ships():
    return [
        {"name": "Test Ship 1", "lat": -17.7, "lon": 178.0},
        {"name": "Test Ship 2", "lat": -18.1, "lon": 178.4},
    ]

@app.get("/api/live-ships")
def get_live_ships():
    return [
        {"name": "Cargo Vessel Alpha", "lat": -17.9, "lon": 178.2, "type": "cargo"},
        {"name": "Fishing Vessel Beta", "lat": -18.2, "lon": 177.8, "type": "fishing"},
        {"name": "Tanker Pacific", "lat": -17.5, "lon": 178.4, "type": "tanker"},
    ]

@app.get("/api/alerts")
def get_alerts():
    ships = get_live_ships()
    alerts = []

    for ship in ships:
        ship_type = str(ship.get("type", "")).lower()
        name = str(ship.get("name", "Unknown Vessel"))

        if ship_type == "tanker":
            alerts.append({
                "title": f"Tanker detected: {name}",
                "severity": "high",
                "message": f"{name} is operating inside the monitored Fiji area.",
            })
        elif ship_type == "cargo":
            alerts.append({
                "title": f"Cargo vessel detected: {name}",
                "severity": "medium",
                "message": f"{name} is present in the monitored area.",
            })
        elif ship_type == "fishing":
            alerts.append({
                "title": f"Fishing vessel detected: {name}",
                "severity": "low",
                "message": f"{name} is active in the monitored area.",
            })

    return alerts
