import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

# =========================
# ENV LOADING
# =========================
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

app = Flask(__name__)
CORS(app)

# =========================
# ENV VARS
# =========================
SENTINEL_CLIENT_ID = os.getenv("396602bd-35db-48ff-9802-1a252bf4f210 ")
SENTINEL_CLIENT_SECRET = os.getenv("TKHHipBzwZawZQwWx5XQeObsUpkoj6hi")

# =========================
# DEMO DATA
# Replace later with real feeds
# =========================
DEMO_ALERTS = [
    {
        "id": 1,
        "title": "OpenPhish Alert",
        "type": "cyber",
        "lat": -18.1248,
        "lon": 178.4501,
        "severity": "medium",
        "source": "OpenPhish",
        "description": "Suspicious phishing domain reported."
    },
    {
        "id": 2,
        "title": "Suspicious Maritime Activity",
        "type": "maritime",
        "lat": -17.7134,
        "lon": 177.0650,
        "severity": "high",
        "source": "AIS Fusion",
        "description": "Unusual vessel behaviour detected."
    }
]

DEMO_VESSELS = [
    {
        "id": "v001",
        "name": "Unknown Vessel",
        "mmsi": "000000001",
        "lat": -17.85,
        "lon": 177.42,
        "speed": 11.2,
        "heading": 136,
        "confidence": 62
    },
    {
        "id": "v002",
        "name": "Cargo Alpha",
        "mmsi": "000000002",
        "lat": -18.02,
        "lon": 178.10,
        "speed": 8.4,
        "heading": 94,
        "confidence": 78
    }
]

# =========================
# TOKEN CACHE
# =========================
sentinel_token_cache = {
    "access_token": None,
    "expires_at": 0
}


# =========================
# HELPERS
# =========================
def normalize_lon(lon: float) -> float:
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon


def get_sentinel_token() -> str:
    now = time.time()

    if (
        sentinel_token_cache["access_token"]
        and sentinel_token_cache["expires_at"] > now + 60
    ):
        return sentinel_token_cache["access_token"]

    if not SENTINEL_CLIENT_ID or not SENTINEL_CLIENT_SECRET:
        raise RuntimeError("Missing SENTINEL_CLIENT_ID or SENTINEL_CLIENT_SECRET in backend/.env")

    token_url = "https://services.sentinel-hub.com/oauth/token"

    response = requests.post(
        token_url,
        data={"grant_type": "client_credentials"},
        auth=(SENTINEL_CLIENT_ID, SENTINEL_CLIENT_SECRET),
        timeout=30
    )
    response.raise_for_status()

    token_data = response.json()
    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600)

    sentinel_token_cache["access_token"] = access_token
    sentinel_token_cache["expires_at"] = now + expires_in

    return access_token


def build_true_color_evalscript() -> str:
    return """
    //VERSION=3
    function setup() {
      return {
        input: ["B04", "B03", "B02"],
        output: { bands: 3 }
      };
    }

    function evaluatePixel(sample) {
      return [sample.B04, sample.B03, sample.B02];
    }
    """


# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "God's Eye backend running",
        "routes": [
            "/api/health",
            "/api/alerts",
            "/api/vessels",
            "/api/sentinel/health",
            "/api/sentinel/tile",
            "/api/sentinel/snapshot"
        ]
    })


@app.route("/api/health")
def api_health():
    return jsonify({
        "status": "ok",
        "backend": "running"
    })


@app.route("/api/alerts")
def get_alerts():
    return jsonify(DEMO_ALERTS)


@app.route("/api/vessels")
def get_vessels():
    return jsonify(DEMO_VESSELS)


@app.route("/api/sentinel/health")
def sentinel_health():
    client_id = os.getenv("SENTINEL_CLIENT_ID")
    client_secret = os.getenv("SENTINEL_CLIENT_SECRET")

    return jsonify({
        "client_id_present": bool(client_id),
        "client_secret_present": bool(client_secret),
        "sentinel_configured": bool(client_id and client_secret)
    })


@app.route("/api/sentinel/tile")
def sentinel_tile():
    try:
        min_lon = float(request.args.get("minLon"))
        min_lat = float(request.args.get("minLat"))
        max_lon = float(request.args.get("maxLon"))
        max_lat = float(request.args.get("maxLat"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid or missing bbox parameters"}), 400

    # Normalize longitudes and clamp latitudes
    min_lon = normalize_lon(min_lon)
    max_lon = normalize_lon(max_lon)
    min_lat = max(min_lat, -90)
    max_lat = min(max_lat, 90)

    if min_lat >= max_lat:
        return jsonify({"error": "Invalid latitude bounds"}), 400

    # Handle dateline crossing simply for now
    if max_lon < min_lon:
        center = normalize_lon((min_lon + max_lon) / 2)
        span = 2.0
        min_lon = max(-180, center - span)
        max_lon = min(180, center + span)

    if min_lon == max_lon or min_lat == max_lat:
        return jsonify({"error": "Degenerate bbox"}), 400

    try:
        access_token = get_sentinel_token()

        process_url = "https://services.sentinel-hub.com/api/v1/process"

        payload = {
            "input": {
                "bounds": {
                    "bbox": [min_lon, min_lat, max_lon, max_lat]
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {
                                "from": "2024-01-01T00:00:00Z",
                                "to": "2024-12-31T23:59:59Z"
                            },
                            "maxCloudCoverage": 40
                        }
                    }
                ]
            },
            "output": {
                "width": 512,
                "height": 512,
                "responses": [
                    {
                        "identifier": "default",
                        "format": {"type": "image/png"}
                    }
                ]
            },
            "evalscript": build_true_color_evalscript()
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "image/png"
        }

        response = requests.post(
            process_url,
            json=payload,
            headers=headers,
            timeout=60
        )

        if response.status_code != 200:
            return jsonify({
                "error": "Sentinel request failed",
                "status_code": response.status_code,
                "details": response.text
            }), 502

        return Response(response.content, mimetype="image/png")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sentinel/snapshot")
def sentinel_snapshot():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Missing or invalid lat/lon"}), 400

    delta = 0.08
    min_lon = lon - delta
    max_lon = lon + delta
    min_lat = lat - delta
    max_lat = lat + delta

    with app.test_request_context(
        f"/api/sentinel/tile?minLon={min_lon}&minLat={min_lat}&maxLon={max_lon}&maxLat={max_lat}"
    ):
        return sentinel_tile()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
