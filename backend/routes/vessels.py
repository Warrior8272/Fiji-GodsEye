from flask import Blueprint, jsonify, request

from services.analytics_service import get_vessels, get_alerts, get_summary

vessels_bp = Blueprint("vessels", __name__)


def apply_filters(vessels):
    include_stale = request.args.get("include_stale", "false").lower() == "true"
    suspicious_only = request.args.get("suspicious_only", "false").lower() == "true"
    unknown_only = request.args.get("unknown_only", "false").lower() == "true"
    fiji_only = request.args.get("fiji_only", "false").lower() == "true"

    filtered = vessels

    if not include_stale:
        filtered = [v for v in filtered if not v.get("stale", False)]
    if suspicious_only:
        filtered = [v for v in filtered if v.get("suspicious", False)]
    if unknown_only:
        filtered = [v for v in filtered if v.get("unknown_vessel", False)]
    if fiji_only:
        filtered = [v for v in filtered if v.get("distance_to_fiji_nm", 999999) <= 600]

    return filtered


def detect_mode(vessels):
    if not vessels:
        return "empty"

    sources = {str(v.get("source", "")).lower() for v in vessels}

    if "aisstream_live" in sources:
        return "live"
    if "cache" in sources or "cached" in sources:
        return "cached"
    if any("test" in str(v.get("name", "")).lower() for v in vessels):
        return "fallback"

    return "unknown"


@vessels_bp.route("/api/vessels")
def api_vessels():
    vessels = apply_filters(get_vessels())[:300]

    return jsonify({
        "count": len(vessels),
        "mode": detect_mode(vessels),
        "vessels": vessels
    })


@vessels_bp.route("/api/alerts")
def api_alerts():
    vessels = apply_filters(get_vessels())[:300]
    alerts = get_alerts(vessels)

    return jsonify({
        "count": len(alerts),
        "alerts": alerts
    })


@vessels_bp.route("/api/summary")
def api_summary():
    vessels = apply_filters(get_vessels())[:300]
    summary = get_summary(vessels)

    return jsonify(summary)
