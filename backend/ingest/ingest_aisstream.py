import asyncio
import websockets
import json
import requests
from datetime import datetime, timezone

from services.db import init_db, upsert_vessel, insert_vessel_history

AISSTREAM_URL = "wss://stream.aisstream.io/v0/stream"
API_KEY = "7ca09eeb84e85ab922ac5ed801b51bfd70e9ecb8"

async def connect_ais():
    print("Starting AIS script...")
    init_db()

    while True:
        try:
            print("Connecting to AISStream...")

            async with websockets.connect(AISSTREAM_URL) as websocket:
                subscription_message = {
                    "APIKey": API_KEY,
                    "BoundingBoxes": [[[-30, 160], [-5, 190]]]
                }

                await websocket.send(json.dumps(subscription_message))
                print("Subscription sent")

                while True:
                    raw = await websocket.recv()
                    data = json.loads(raw)
                    msg = data.get("Message", {})

                    if "PositionReport" not in msg:
                        continue

                    meta = msg.get("MetaData", {})
                    report = msg.get("PositionReport", {})

                    lat = report.get("Latitude")
                    lon = report.get("Longitude")
                    mmsi = meta.get("MMSI") or report.get("UserID")

                    if lat is None or lon is None or mmsi is None:
                        continue

                    vessel = {
                        "id": f"ais:{mmsi}",
                        "name": meta.get("ShipName", "Unknown"),
                        "lat": lat,
                        "lon": lon,
                        "speed": report.get("Sog", 0),
                        "course": report.get("Cog"),
                        "heading": report.get("TrueHeading"),
                        "type": "AIS",
                        "source": "aisstream",
                        "confidence": 85,
                        "lastSeen": meta.get("time_utc") or datetime.now(timezone.utc).isoformat(),
                        "raw_json": json.dumps(data)
                    }

                    upsert_vessel(vessel)
                    insert_vessel_history(vessel)

                    try:
                        requests.post("http://127.0.0.1:5000/api/vessels", json=vessel, timeout=2)
                    except Exception:
                        pass

                    print("LIVE VESSEL:", vessel)

        except Exception as e:
            print("AIS reconnecting after error:", e)
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(connect_ais())
    except KeyboardInterrupt:
        print("Stopped by user")
