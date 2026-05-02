from datetime import datetime, timezone
from services.db import init_db, upsert_vessel

def main():
    print("🚀 Starting vessel ingestion...")

    # Seeded realistic vessel records for Phase 10C DB pipeline
    # Replace this source block next with GFW / real provider data.
    vessel_data = [
        {
            "id": "vessel::cargo-alpha",
            "source": "seed_pipeline",
            "name": "Cargo Alpha",
            "type": "Cargo",
            "lat": -18.20,
            "lon": 177.20,
            "speed": 10.0,
            "lastSeen": datetime.now(timezone.utc).isoformat(),
            "confidence": 70,
            "raw_json": '{"seed": true, "label": "cargo-alpha"}'
        },
        {
            "id": "vessel::unknown-1",
            "source": "seed_pipeline",
            "name": "Unknown Vessel",
            "type": "Unknown",
            "lat": -18.50,
            "lon": 176.80,
            "speed": 12.0,
            "lastSeen": datetime.now(timezone.utc).isoformat(),
            "confidence": 80,
            "raw_json": '{"seed": true, "label": "unknown-1"}'
        },
        {
            "id": "vessel::fishing-1",
            "source": "seed_pipeline",
            "name": "Fishing Vessel",
            "type": "Fishing",
            "lat": -17.95,
            "lon": 178.30,
            "speed": 6.0,
            "lastSeen": datetime.now(timezone.utc).isoformat(),
            "confidence": 45,
            "raw_json": '{"seed": true, "label": "fishing-1"}'
        }
    ]

    init_db()

    count = 0
    for record in vessel_data:
        upsert_vessel(record)
        count += 1

    print(f"✅ Vessels ingested: {count}")

if __name__ == "__main__":
    main()
