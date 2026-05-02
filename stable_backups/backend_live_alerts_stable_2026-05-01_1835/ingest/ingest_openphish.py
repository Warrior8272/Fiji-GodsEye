import os
from datetime import datetime, timezone
from services.db import init_db, upsert_alert

def main():
    print("🚀 Starting OpenPhish ingestion...")

    # Demo data (replace later with real feed)
    demo_data = [
        "http://phish-example1.com",
        "http://phish-example2.com"
    ]

    init_db()

    count = 0

    for url in demo_data:
        record = {
            "id": f"openphish::{url}",
            "source": "openphish",
            "name": "Phishing Campaign",
            "type": "cyber",
            "severity": "high",
            "indicator": url,
            "target_region": "Fiji",
            "lat": -17.7134,
            "lon": 178.065,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "confidence": 80,
            "raw_json": url
        }

        upsert_alert(record)
        count += 1

    print(f"✅ Alerts ingested: {count}")

if __name__ == "__main__":
    main()
