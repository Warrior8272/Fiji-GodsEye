import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

SENTINEL_CLIENT_ID = os.getenv("SENTINEL_CLIENT_ID")
SENTINEL_CLIENT_SECRET = os.getenv("SENTINEL_CLIENT_SECRET")

print("ENV PATH:", env_path)
print("CLIENT ID RAW:", repr(SENTINEL_CLIENT_ID))
print("CLIENT SECRET PRESENT:", bool(SENTINEL_CLIENT_SECRET))


import os
import time
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

# =========================
# ENVIRONMENT VARIABLES
# =========================
SENTINEL_CLIENT_ID = os.getenv("c5ea91ec-87ec-42e9-b818-aae6d7a3418f")
SENTINEL_CLIENT_SECRET = os.getenv("JpRqBGgu8kxTW4b4eRuisflueldCCjyp")

# =========================
# SIMPLE TOKEN CACHE
# =========================
sentinel_token_cache = {
    "access_token": None,
    "expires_at": 0
}

# =========================
# BASIC DEMO DATA
# Replace these later with your real feeds
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
# SENTINEL AUTH
# =========================
def get_sentinel_token():
    now = time.time()

    # Reuse token if still valid
    if (
        sentinel_token_cache["access_token"]
        and sentinel_token_cache["expires_at"] > now + 60
    ):
        return sentinel_token_cache["access_token"]

    if not SENTINEL_CLIENT_ID or not SENTINEL_CLIENT_SECRET:
        raise RuntimeError(
            "Missing SENTINEL_CLIENT_ID or SENTINEL_CLIENT_SECRET in backend/.env"
        )

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

# ========================
# ROUTES
# =========================
@app.route("/api/sentinel/health")
def sentinel_health():
    client_id = os.getenv("SENTINEL_CLIENT_ID")
    client_secret = os.getenv("SENTINEL_CLIENT_SECRET")

    return jsonify({
        "client_id_present": bool(client_id),
        "client_secret_present": bool(client_secret),
        "sentinel_configured": bool(client_id and client_secret)
    })

@app.route("/api/alerts")
def get_alerts():
    return jsonify(DEMO_ALERTS)

@app.route("/api/vessels")
def get_vessels():
    return jsonify(DEMO_VESSELS)


    return jsonify({
        "sentinel_configured": configured,
        "client_id_present": bool(SENTINEL_CLIENT_ID),
        "client_secret_present": bool(SENTINEL_CLIENT_SECRET)
    })

@app.route("/api/sentinel/tile")
def sentinel_tile():
    """
    Example:
    /api/sentinel/tile?minLon=177.0&minLat=-18.4&maxLon=178.2&maxLat=-17.4
    """

    try:
        min_lon = float(request.args.get("minLon"))
        min_lat = float(request.args.get("minLat"))
        max_lon = float(request.args.get("maxLon"))
        max_lat = float(request.args.get("maxLat"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid or missing bbox parameters"}), 400

    try:
        access_token = get_sentinel_token()

        process_url = "https://services.sentinel-hub.com/api/v1/process"

        evalscript = """
        //VERSION=3
        function setup() {
          return {
            input: ["B04", "B03", "B02"],
            output: { bands: 3 }
          };
        }

        function evaluatePixel(sample) {
          return [
            sample.B04 * 2.5,
            sample.B03 * 2.5,
            sample.B02 * 2.5
          ];
        }
        """

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
                                "from": "2026-01-01T00:00:00Z",
                                "to": "2026-12-31T23:59:59Z"
                            },
                            "maxCloudCoverage": 30
                        }
                    }
                ]
            },
            "output": {
                "width": 1024,
                "height": 1024,
                "responses": [
                    {
                        "identifier": "default",
                        "format": {
                            "type": "image/png"
                        }
                    }
                ]
            },
            "evalscript": evalscript
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
    """
    Build a small bbox around a point.
    Example:
    /api/sentinel/snapshot?lat=-17.85&lon=177.42
    """

    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Missing or invalid lat/lon"}), 400

    # Approx small area around clicked point
    delta = 0.08

    min_lon = lon - delta
    max_lon = lon + delta
    min_lat = lat - delta
    max_lat = lat + delta

    try:
        access_token = get_sentinel_token()

        process_url = "https://services.sentinel-hub.com/api/v1/process"

        evalscript = """
        //VERSION=3
        function setup() {
          return {
            input: ["B04", "B03", "B02"],
            output: { bands: 3 }
          };
        }

        function evaluatePixel(sample) {
          return [
            sample.B04 * 2.5,
            sample.B03 * 2.5,
            sample.B02 * 2.5
          ];
        }
        """

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
                                "from": "2026-01-01T00:00:00Z",
                                "to": "2026-12-31T23:59:59Z"
                            },
                            "maxCloudCoverage": 30
                        }
                    }
                ]
            },
            "output": {
                "width": 768,
                "height": 768,
                "responses": [
                    {
                        "identifier": "default",
                        "format": {
                            "type": "image/png"
                        }
                    }
                ]
            },
            "evalscript": evalscript
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
                "error": "Snapshot request failed",
                "status_code": response.status_code,
                "details": response.text
            }), 502

        return Response(response.content, mimetype="image/png")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
