from flask import Blueprint, jsonify

from config import Config
from utils.geo import dt_to_iso, utc_now

health_bp = Blueprint("health", __name__)


@health_bp.get("/")
def index():
    return jsonify({
        "name": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "status": "ok",
        "endpoints": [
            "/api/health",
            "/api/vessels",
            "/api/alerts",
            "/api/summary",
            "/api/vessel/<mmsi>",
        ],
    })

@health_bp.get("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "utc_time": dt_to_iso(utc_now()),
        "ais_timeout_hours": Config.AIS_TIMEOUT_HOURS,
        "feed_source": Config.AIS_API_URL if Config.AIS_API_URL else "no_live_feed_configured",
    })
