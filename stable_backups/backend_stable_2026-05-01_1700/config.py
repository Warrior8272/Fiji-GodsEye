import os


class Config:
    APP_NAME = "Fiji God's Eye Backend"
    APP_VERSION = "phase9-professional"

    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    AIS_TIMEOUT_HOURS = float(os.getenv("AIS_TIMEOUT_HOURS", "8"))
    VESSEL_STALE_HOURS = float(os.getenv("VESSEL_STALE_HOURS", "24"))
    SUSPICIOUS_PROXIMITY_NM = float(os.getenv("SUSPICIOUS_PROXIMITY_NM", "250"))
    LOITERING_SPEED_KNOTS = float(os.getenv("LOITERING_SPEED_KNOTS", "2.0"))
    HIGH_SPEED_KNOTS = float(os.getenv("HIGH_SPEED_KNOTS", "35.0"))

    AIS_API_URL = os.getenv("AIS_API_URL", "").strip()
    AIS_API_KEY = os.getenv("AIS_API_KEY", "").strip()

    FIJI_CENTER = {"lat": -18.1248, "lon": 178.4501}
    SOUTH_AMERICA_GATE = {"lat": -12.0464, "lon": -77.0428, "name": "Lima corridor"}
    PACIFIC_MID_GATE = {"lat": -15.0, "lon": -140.0, "name": "Pacific mid-route"}
    FIJI_GATE = {"lat": -18.1248, "lon": 178.4501, "name": "Fiji approach"}
