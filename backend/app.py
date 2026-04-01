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

WATCH_ZONE = {
    "minLat": -18.5,
    "maxLat": -17.5,
    "minLon": 177.5,
    "maxLon": 178.5,
}

MAX_HISTORY = 10

ship_positions = [
    {
        "name": "Cargo Vessel Alpha",
        "type": "cargo",
        "routeSegments": [
            [
                [-23.5, -75.0],
                [-23.0, -90.0],
                [-22.0, -110.0],
                [-21.0, -130.0],
                [-20.0, -150.0],
                [-19.0, -170.0],
                [-18.5, -179.0],
            ],
            [
                [-18.5, 179.0],
                [-18.3, 178.8],
                [-18.1, 178.5],
                [-17.9, 178.2],
            ],
        ],
        "index": 0,
        "history": [],
    },
    {
        "name": "Fishing Vessel Beta",
        "type": "fishing",
        "routeSegments": [
            [
                [-19.2, 175.0],
                [-18.9, 175.8],
                [-18.6, 176.5],
                [-18.4, 177.1],
                [-18.3, 177.5],
                [-18.2, 177.8],
            ]
        ],
        "index": 0,
        "history": [],
    },
    {
        "name": "Tanker Pacific",
        "type": "tanker",
        "routeSegments": [
            [
                [-28.0, -78.0],
                [-27.0, -95.0],
                [-25.5, -115.0],
                [-24.0, -135.0],
                [-22.5, -155.0],
                [-21.0, -172.0],
                [-20.0, -179.0],
            ],
            [
                [-20.0, 179.0],
                [-19.2, 178.9],
                [-18.5, 178.7],
                [-17.9, 178.5],
                [-17.5, 178.4],
            ],
        ],
        "index": 0,
        "history": [],
    },
]


def flatten_route_segments(route_segments):
    all_points = []
    for segment in route_segments:
        for point in segment:
            all_points.append(point)
    return all_points


def is_inside_watch_zone(lat, lon):
    return (
        WATCH_ZONE["minLat"] <= lat <= WATCH_ZONE["maxLat"]
        and WATCH_ZONE["minLon"] <= lon <= WATCH_ZONE["maxLon"]
    )


@app.get("/")
def home():
    return {"status": "Backend running"}


@app.get("/api/live-ships")
def get_live_ships():
    output = []

    for ship in ship_positions:
        all_points = flatten_route_segments(ship["routeSegments"])

        ship["index"] = (ship["index"] + 1) % len(all_points)
        lat, lon = all_points[ship["index"]]

        ship["history"].append([lat, lon])
        if len(ship["history"]) > MAX_HISTORY:
            ship["history"] = ship["history"][-MAX_HISTORY:]

        output.append({
            "name": ship["name"],
            "type": ship["type"],
            "lat": lat,
            "lon": lon,
            "routeSegments": ship["routeSegments"],
            "history": ship["history"],
        })

    return output


@app.get("/api/alerts")
def get_alerts():
    ships = get_live_ships()
    alerts = []
    ships_in_zone = 0

    for ship in ships:
        lat = ship["lat"]
        lon = ship["lon"]
        ship_type = ship.get("type", "unknown")
        name = ship["name"]
        history = ship.get("history", [])

        in_zone = is_inside_watch_zone(lat, lon)

        if in_zone:
            ships_in_zone += 1

        risk_score = 0

        if in_zone:
            risk_score += 2
            alerts.append({
                "title": f"Zone entry detected: {name}",
                "message": f"{name} has entered the Fiji monitoring zone.",
                "severity": "medium",
                "ship": name,
                "type": ship_type,
                "risk_score": risk_score,
            })

        if ship_type == "tanker" and in_zone:
            risk_score += 3
            alerts.append({
                "title": f"HIGH RISK: Tanker in Fiji zone",
                "message": f"{name} is a tanker operating inside the monitored zone.",
                "severity": "high",
                "ship": name,
                "type": ship_type,
                "risk_score": risk_score,
            })

        if ship_type == "unknown":
            risk_score += 2
            alerts.append({
                "title": f"Unknown vessel detected: {name}",
                "message": f"{name} has no recognised vessel type classification.",
                "severity": "medium",
                "ship": name,
                "type": ship_type,
                "risk_score": risk_score,
            })

        if ship.get("routeSegments"):
            first_segment = ship["routeSegments"][0]
            if first_segment:
                start = first_segment[0]
                start_lon = start[1]

                if start_lon < -60:
                    risk_score += 3
                    alerts.append({
                        "title": f"High-risk origin: {name}",
                        "message": "Route appears to originate from South America region.",
                        "severity": "high",
                        "ship": name,
                        "type": ship_type,
                        "risk_score": risk_score,
                    })

        if ship_type == "cargo" and in_zone:
            risk_score += 1
            alerts.append({
                "title": f"Cargo vessel in zone: {name}",
                "message": f"{name} is a cargo vessel inside the monitored zone.",
                "severity": "medium",
                "ship": name,
                "type": ship_type,
                "risk_score": risk_score,
            })

        if len(history) >= 3:
            unique_points = {tuple(p) for p in history[-3:]}
            if len(unique_points) <= 2:
                alerts.append({
                    "title": f"Possible loitering: {name}",
                    "message": f"{name} has shown limited movement in recent tracking history.",
                    "severity": "medium",
                    "ship": name,
                    "type": ship_type,
                    "risk_score": risk_score + 2,
                })

    if ships_in_zone >= 2:
        alerts.append({
            "title": "Cluster alert",
            "message": f"{ships_in_zone} vessels are currently inside the Fiji monitoring zone.",
            "severity": "high" if ships_in_zone >= 3 else "medium",
            "ship": "multiple",
            "type": "cluster",
            "risk_score": ships_in_zone,
        })

    return alerts
