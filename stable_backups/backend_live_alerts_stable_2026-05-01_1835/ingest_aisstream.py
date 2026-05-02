import os
import json
import time
import requests
import websocket

AISSTREAM_API_KEY = os.getenv("AISSTREAM_API_KEY")
BACKEND_URL = "http://127.0.0.1:5000/api/vessels"

# Fiji / nearby Pacific bounding boxes
BOUNDING_BOXES = [
    [[-18.5, 177.0], [-17.0, 178.8]],   # Western Viti Levu / Lautoka / Nadi
    [[-18.6, 178.0], [-17.5, 179.5]],   # Suva / Eastern Viti Levu
    [[-17.0, 178.0], [-15.5, 180.0]],   # Vanua Levu
    [[-19.6, 177.0], [-18.5, 179.4]],   # Kadavu / South
    [[-21.0, -179.9], [-15.0, -175.0]], # Lau / Eastern Fiji
]

def post_vessel(v):
    try:
        requests.post(BACKEND_URL, json=v, timeout=3)
    except Exception as e:
        print("Backend post failed:", e)

def main():
    if not AISSTREAM_API_KEY:
        print("Missing AISSTREAM_API_KEY")
        print("Run: export AISSTREAM_API_KEY='your_key_here'")
        return

    print("Starting AISStream ingest...")

    ws = websocket.create_connection("wss://stream.aisstream.io/v0/stream")

    subscribe = {
        "APIKey": AISSTREAM_API_KEY,
        "BoundingBoxes": BOUNDING_BOXES,
        "FilterMessageTypes": ["PositionReport"]
    }

    ws.send(json.dumps(subscribe))
    print("AISStream connected and subscribed.")

    while True:
        try:
            msg = json.loads(ws.recv())

            meta = msg.get("MetaData", {})
            position = msg.get("Message", {}).get("PositionReport", {})

            if not position:
                continue

            vessel = {
                "id": f"ais:{meta.get('MMSI') or position.get('UserID')}",
                "mmsi": meta.get("MMSI") or position.get("UserID"),
                "name": meta.get("ShipName") or "Unknown",
                "lat": position.get("Latitude"),
                "lon": position.get("Longitude"),
                "speed": position.get("Sog"),
                "course": position.get("Cog"),
                "heading": position.get("TrueHeading"),
                "source": "aisstream",
                "type": "AIS",
                "lastSeen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

            print("AIS:", vessel["id"], vessel["lat"], vessel["lon"], vessel["speed"])
            post_vessel(vessel)

        except KeyboardInterrupt:
            print("Stopping AIS ingest.")
            break
        except Exception as e:
            print("AIS ingest error:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
