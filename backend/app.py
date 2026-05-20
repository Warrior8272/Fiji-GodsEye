
# --- Global vessel memory ---
import io
from flask import send_file
from datetime import datetime
from reportlab.lib.styles import getSampleStyleSheet
from services.alert_correlation import correlate_alerts_vessels
from services.intelligence import score_vessels
from services.correlation import correlate_vessels_alerts
from services.db import init_db, list_alerts, list_vessels, get_vessel_history, upsert_vessel
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from flask_cors import CORS
from dark_activity import process_dark_activity
from repeat_offender import process_repeat_offenders
from vessel_timeline import update_vessel_timeline, get_vessel_timeline
from route_anomaly import process_route_anomalies
from fusion_score import process_fusion_scores
from priority_targets import build_priority_targets
from flask import Flask, jsonify, jsonify, request
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Image, Image, Image, Image, Table, TableStyle
import time
from ais_gap import detect_gaps
from threat_fusion import apply_threat_scores

ZONES = ZONES if 'ZONES' in globals() else []

# --- TEST FIJI ZONE ---
ZONES.append({
    "name": "Fiji Test Zone",
    "type": "watch",
    "country": "Fiji",
    "bbox": [176.5, -18.5, 178.5, -16.5],
    "color": "orange"
})


app = Flask(__name__)

# Global vessel state store
VESSEL_STATE = {}
CORS(app)

init_db()
live_vessels = []


def get_scored_vessels():
    vessels_data = list_vessels(500)
    alerts_data = []
    correlated = correlate_vessels_alerts(
        vessels_data, alerts_data, radius_km=80)
    scored = score_vessels(correlated)
    return scored


def generate_alerts(vessels):
    alerts = []
    for v in vessels:
        confidence = v.get("confidence", 0)
        flags = v.get("anomaly_flags", [])

        if confidence >= 85:
            alerts.append({
                "id": v.get("id"),
                "type": "HIGH_THREAT",
                "message": "High confidence threat detected",
                "vessel": v
            })
        elif confidence >= 70:
            alerts.append({
                "id": v.get("id"),
                "type": "ELEVATED_THREAT",
                "message": "Elevated risk vessel",
                "vessel": v
            })

        if "land_movement" in flags:
            alerts.append({
                "id": v.get("id"),
                "type": "SPOOFING",
                "message": "Possible GPS spoofing detected",
                "vessel": v
            })

        if v.get("speed", 0) == 0:
            alerts.append({
                "id": v.get("id"),
                "type": "LOITERING",
                "message": "Vessel stationary in monitored zone",
                "vessel": v
            })

    return alerts


def safe_generate_alerts(vessels):
    alerts = []

    for v in vessels:
        confidence = v.get("confidence", 0)
        flags = v.get("anomaly_flags", [])
        speed = v.get("speed", 0)

        if confidence >= 85:
            alerts.append({"type": "HIGH",
                           "msg": "High confidence vessel",
                           "id": v.get("id")})
        elif confidence >= 70:
            alerts.append(
                {"type": "ELEVATED", "msg": "Elevated vessel", "id": v.get("id")})

        if "land_movement" in flags:
            alerts.append({"type": "SPOOFING",
                           "msg": "Possible GPS spoofing",
                           "id": v.get("id")})

        if speed == 0:
            alerts.append(
                {
                    "type": "LOITERING",
                    "severity": "HIGH" if v.get(
                        "risk",
                        0) >= 20 else "MEDIUM",
                    f"msg": f"Stationary vessel | Risk: {
                        v.get('risk')} | Zone: {
                        v.get('zone_name')} | Flags: {
                        ', '.join(
                            v.get(
                                'risk_flags',
                                []))}",
                    "id": v.get("id")})

    return alerts


# --- Zone helper ---
def is_in_bbox(vessel, bbox):
    lon = vessel.get("lon") or vessel.get("lng") or vessel.get("longitude")
    lat = vessel.get("lat") or vessel.get("latitude")

    if lon is None or lat is None:
        return False

    lon = float(lon)
    lat = float(lat)

    min_lon, min_lat, max_lon, max_lat = bbox

    if min_lon <= max_lon:
        return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat

    return (lon >= min_lon or lon <= max_lon) and min_lat <= lat <= max_lat


def detect_zone(vessel, zones):
    for zone in zones:
        bbox = zone.get("bbox")
        if bbox and is_in_bbox(vessel, bbox):
            return zone
    return None


@app.route("/api/alerts", methods=["GET"])
def alerts():
    import json
    from pathlib import Path

    alert_list = []

    try:
        ais_path = Path(__file__).resolve().parent / "ais_live.json"
        vessels = []

        if ais_path.exists():
            with open(ais_path, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    vessels = data

        # Basic vessel alerts
        for v in vessels:
            mmsi = v.get("mmsi", "UNKNOWN")
            lat = v.get("lat")
            lon = v.get("lon")
            speed = v.get("speed", v.get("sog", 0)) or 0

            try:
                speed = float(speed)
            except Exception:
                speed = 0

            if speed < 1:
                alert_list.append({
                    "type": "LOW_SPEED_OR_STATIONARY",
                    "risk": "LOW",
                    "mmsi": mmsi,
                    "lat": lat,
                    "lon": lon,
                    "msg": f"Vessel {mmsi} is slow/stationary"
                })

        # Coverage gap intelligence alert
        if len(vessels) < 20:
            alert_list.append({
                "type": "AIS_COVERAGE_GAP",
                "risk": "MEDIUM",
                "zone": "Fiji / Wider Pacific",
                "vessel_count": len(vessels),
                "msg": f"Only {len(vessels)} AIS contacts visible. Possible feed limitation or satellite AIS gap."
            })

        return jsonify(alert_list)

    except Exception as e:
        return jsonify([{
            "type": "ALERT_ENGINE_ERROR",
            "risk": "HIGH",
            "msg": str(e)
        }]), 200


@app.route("/api/vessels", methods=["GET", "POST"])
def handle_vessels():
    global live_vessels

    if request.method == "POST":
        data = request.json
        upsert_vessel(data)
        return {"status": "added"}

    vessels = get_scored_vessels()

    # --- Zone Detection for /api/vessels ---
    for vessel in vessels:
        zone = detect_zone(vessel, ZONES) if 'ZONES' in globals() else None

        if zone:
            vessel["zone_name"] = zone.get("name")
            vessel["zone_type"] = zone.get("type")
            vessel["zone_country"] = zone.get("country")
        else:
            vessel["zone_name"] = None
            vessel["zone_type"] = None
            vessel["zone_country"] = None

        # --- Zone Risk Scoring ---

        # --- Loitering Detection ---

        # --- Cross-Zone Tracking ---
        vid = vessel.get("mmsi") or vessel.get("id")
        state = VESSEL_STATE.setdefault(vid, {"zones": []})

        current_zone = vessel.get("zone_name")

        if current_zone:
            if not state["zones"] or state["zones"][-1] != current_zone:
                state["zones"].append(current_zone)

        vessel["zone_history"] = state["zones"][-5:]

        # Detect suspicious route pattern
        history = vessel["zone_history"]

        if "Tonga Watch Zone" in history and "Samoa Watch Zone" in history:
            vessel["risk"] = vessel.get("risk", 0) + 15
            vessel.setdefault("risk_flags", []).append("Tonga → Samoa route")

        if "Samoa Watch Zone" in history and "Fiji Test Zone" in history:
            vessel["risk"] = vessel.get("risk", 0) + 15
            vessel.setdefault("risk_flags", []).append("Samoa → Fiji route")

        speed = vessel.get("speed", 0) or 0
        vid = vessel.get("mmsi") or vessel.get("id")

        state = VESSEL_STATE.setdefault(vid, {"loiter": 0})

        if speed < 2:
            state["loiter"] = state.get("loiter", 0) + 1
        else:
            state["loiter"] = 0

        vessel["loiter_time"] = state["loiter"]

        if vessel["loiter_time"] > 5:
            vessel["risk"] = vessel.get("risk", 0) + 10
            if "Loitering Detected" not in vessel.get("risk_flags", []):
                vessel.setdefault(
                    "risk_flags", []).append("Loitering Detected")

        if vessel.get("loiter_time", 0) > 5:
            vessel["risk"] = vessel.get("risk", 0) + 10
            if "Loitering Detected" not in vessel.get("risk_flags", []):
                vessel.setdefault(
                    "risk_flags", []).append("Loitering Detected")

        if zone:
            if zone.get("type") == "watch":
                vessel["risk"] = vessel.get("risk", 0) + 5
                vessel.setdefault(
                    "risk_flags", []).append("Entered Watch Zone")

            if zone.get("type") == "port":
                vessel["risk"] = vessel.get("risk", 0) + 2
                vessel.setdefault("risk_flags", []).append("In Port Zone")

    vessels = apply_threat_scores(vessels)

    # SAFE FALLBACK RETURN FOR handle_vessels
    return jsonify(vessels)

@app.route("/api/vessels/<path:vessel_id>/history")
def vessel_history(vessel_id):
    limit = request.args.get("limit", default=150, type=int)
    range_hours = request.args.get("range_hours", default=None, type=int)

    if limit < 10:
        limit = 10
    if limit > 500:
        limit = 500

    if range_hours is not None and range_hours < 1:
        range_hours = 1

    return jsonify(get_vessel_history(vessel_id, limit, range_hours))


# ===== PDF REPORT ROUTE =====


@app.route("/api/ais-gaps")
def api_ais_gaps():
    import json
    import time
    from pathlib import Path

    ais_file = Path(__file__).with_name("ais_live.json")
    now = time.time()
    gap_threshold_seconds = 60 * 30  # 30 minutes

    gaps = []

    try:
        data = json.loads(ais_file.read_text())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "gaps": []
        })

    if isinstance(data, dict):
        vessels = list(data.values())
    elif isinstance(data, list):
        vessels = data
    else:
        vessels = []

    for v in vessels:
        if not isinstance(v, dict):
            continue

        mmsi = v.get("mmsi") or v.get("MMSI") or v.get("id") or "unknown"

        ts = (
            v.get("timestamp")
            or v.get("last_seen")
            or v.get("lastSeen")
            or v.get("time")
            or v.get("received_at")
        )

        last_seen_epoch = None

        if isinstance(ts, (int, float)):
            last_seen_epoch = float(ts)
        elif isinstance(ts, str):
            try:
                last_seen_epoch = datetime.fromisoformat(
                    ts.replace("Z", "+00:00")).timestamp()
            except Exception:
                last_seen_epoch = now

        if last_seen_epoch is None:
            continue

        age_seconds = now - last_seen_epoch

        if age_seconds >= gap_threshold_seconds:
            gaps.append(
                {
                    "type": "AIS_GAP",
                    "severity": (
                        "high" if age_seconds >= 1800 else "medium" if age_seconds >= 600 else "low"),
                    "mmsi": mmsi,
                    "name": v.get("name") or v.get("shipname") or v.get("ShipName") or "Unknown vessel",
                    "age_minutes": round(
                        age_seconds / 60,
                        1),
                    "message": f"AIS signal gap detected for {mmsi}: last update {round(age_seconds / 60, 1)} minutes ago",
                    "lat": v.get("lat"),
                    "lon": v.get("lon")})

    return jsonify({
        "status": "ok",
        "threshold_minutes": gap_threshold_seconds / 60,
        "total_gaps": len(gaps),
        "gaps": gaps
    })


# ===== ROUTE INTELLIGENCE =====
@app.route("/api/route-intelligence")
def api_route_intelligence():
    import json
    from pathlib import Path

    ais_file = Path(__file__).with_name("ais_live.json")

    try:
        data = json.loads(ais_file.read_text())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "routes": []})

    vessels = []

    # Column-style JSON: {"id": "...", "lat": -17, "lon": 177}
    if isinstance(data, dict) and "lat" in data and "lon" in data:
        vessels = [data]

    # Normal dict of vessels
    elif isinstance(data, dict):
        vessels = list(data.values())

    # Normal list of vessels
    elif isinstance(data, list):
        vessels = data

    route_hits = []

    for v in vessels:
        if not isinstance(v, dict):
            continue

        lat = v.get("lat") or v.get("latitude")
        lon = v.get("lon") or v.get("lng") or v.get("longitude")

        if lat is None or lon is None:
            continue

        lat = float(lat)
        lon = float(lon)

        name = v.get("name") or v.get("shipname") or "Unknown vessel"
        mmsi = v.get("mmsi") or v.get("id") or "unknown"
        speed = float(v.get("speed") or 0)
        course = float(v.get("course") or v.get("heading") or 0)

        indicators = ["Baseline vessel detected"]
        score = 10

        if -30 <= lat <= 5 and 140 <= lon <= 180:
            indicators.append("Inside Fiji-Pacific monitoring corridor")
            score += 20

        if speed <= 2:
            indicators.append("Slow movement / possible loitering")
            score += 20

        severity = "high" if score >= 40 else "medium" if score >= 20 else "low"

        route_hits.append({
            "type": "ROUTE_INTEL",
            "severity": severity,
            "score": score,
            "mmsi": mmsi,
            "name": name,
            "lat": lat,
            "lon": lon,
            "speed": speed,
            "course": course,
            "indicators": indicators,
            "message": f"{name} / {mmsi}: route indicators detected ({score})"
        })

    return jsonify({
        "status": "ok",
        "total": len(route_hits),
        "routes": route_hits[:20]
    })


# ===== FUSION THREAT SCORING =====
@app.route("/api/fusion-score")
def api_fusion_score():
    import json
    import time
    from pathlib import Path

    ais_file = Path(__file__).with_name("ais_live.json")
    now = time.time()

    try:
        data = json.loads(ais_file.read_text())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "fusion": []
        })

    vessels = []

    if isinstance(data, dict) and "lat" in data and "lon" in data:
        vessels = [data]
    elif isinstance(data, dict):
        vessels = [v for v in data.values() if isinstance(v, dict)]
    elif isinstance(data, list):
        vessels = data

    fusion = []

    for v in vessels:
        if not isinstance(v, dict):
            continue

        lat = v.get("lat") or v.get("latitude")
        lon = v.get("lon") or v.get("longitude") or v.get("lng")

        if lat is None or lon is None:
            continue

        name = v.get("name") or v.get("shipname") or "Unknown vessel"
        mmsi = v.get("mmsi") or v.get("id") or "unknown"
        speed = float(v.get("speed") or v.get("sog") or 0)
        course = float(v.get("course") or v.get(
            "heading") or v.get("cog") or 0)

        score = 0
        signals = []

        # 1. Stationary / loitering
        if speed <= 1:
            score += 30
            signals.append("Stationary / possible loitering")
        elif speed <= 2:
            score += 20
            signals.append("Slow movement")

        # 2. Fiji-Pacific monitoring corridor
        lat_f = float(lat)
        lon_f = float(lon)

        if -30 <= lat_f <= 5 and 140 <= lon_f <= 180:
            score += 20
            signals.append("Inside Fiji-Pacific monitoring corridor")

        # 3. Route direction indicator
        if 210 <= course <= 300:
            score += 15
            signals.append("Westbound or southwest movement")

        # 4. Existing anomaly flags
        flags = v.get("anomaly_flags") or v.get("behavior_flags") or []
        if isinstance(flags, list) and flags:
            score += 15
            signals.append("Existing anomaly flags detected")

        # 5. Stale AIS / possible gap
        age_hours = float(v.get("last_seen_age_hours") or 0)
        if age_hours >= 0.5:
            score += 30
            signals.append("AIS stale over 30 minutes")
        elif age_hours >= 0.1:
            score += 15
            signals.append("AIS update delay")

        if score >= 70:
            severity = "critical"
        elif score >= 45:
            severity = "high"
        elif score >= 25:
            severity = "medium"
        else:
            severity = "low"

        fusion.append({
            "type": "FUSION_SCORE",
            "name": name,
            "mmsi": mmsi,
            "lat": lat_f,
            "lon": lon_f,
            "speed": speed,
            "course": course,
            "score": score,
            "severity": severity,
            "signals": signals,
            "message": f"{name} / {mmsi}: fusion score {score} ({severity})"
        })

    fusion = sorted(fusion, key=lambda x: x["score"], reverse=True)

    return jsonify({
        "status": "ok",
        "total": len(fusion),
        "fusion": fusion[:20]
    })


@app.route("/api/intel-summary")
def intel_summary():
    import json
    import time
    import os
    from flask import jsonify

    ais_path = os.path.join(os.path.dirname(__file__), "ais_live.json")

    if not os.path.exists(ais_path):
        return jsonify({
            "status": "no_data",
            "total_vessels": 0,
            "fresh_tracks": 0,
            "aging_tracks": 0,
            "dark_tracks": 0,
            "top_threats": []
        })

    with open(ais_path, "r") as f:
        vessels = json.load(f)

    now = time.time()

    summary = {
        "status": "active",
        "generated_at": now,
        "total_vessels": len(vessels),
        "fresh_tracks": 0,
        "aging_tracks": 0,
        "dark_tracks": 0,
        "high_risk": 0,
        "medium_risk": 0,
        "low_risk": 0,
        "top_threats": []
    }

    enriched = []

    for v in vessels:
        age_hours = round((now - float(v.get("timestamp", now))) / 3600, 2)
        speed = float(v.get("speed") or 0)

        risk_score = 0
        flags = []

        if age_hours < 1:
            track_status = "Fresh track"
            summary["fresh_tracks"] += 1
        elif age_hours < 6:
            track_status = "Aging track"
            summary["aging_tracks"] += 1
            risk_score += 15
            flags.append("aging_ais_track")
        else:
            track_status = "DARK / AIS LOST"
            summary["dark_tracks"] += 1
            risk_score += 45
            flags.append("dark_vessel_timer_triggered")

        if speed < 1:
            risk_score += 10
            flags.append("stationary_or_loitering")

        if v.get("name", "Unknown") == "Unknown":
            risk_score += 10
            flags.append("unknown_identity")

        if risk_score >= 40:
            risk_level = "High"
            summary["high_risk"] += 1
        elif risk_score >= 20:
            risk_level = "Medium"
            summary["medium_risk"] += 1
        else:
            risk_level = "Low"
            summary["low_risk"] += 1

        enriched.append({
            "mmsi": v.get("mmsi"),
            "name": v.get("name", "Unknown"),
            "zone": v.get("zone", "Unknown area"),
            "lat": v.get("lat"),
            "lon": v.get("lon"),
            "speed": speed,
            "course": v.get("course"),
            "age_hours": age_hours,
            "track_status": track_status,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "flags": flags,
            "recommendation": "Investigate AIS loss / possible dark activity" if track_status == "DARK / AIS LOST" else "Continue observation"
        })

    summary["top_threats"] = sorted(
        enriched,
        key=lambda x: x["risk_score"],
        reverse=True
    )[:5]

    return jsonify(summary)


@app.route("/api/report")
def generate_report():
    import json
    import time
    import os
    from flask import send_file
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Image, Image, Image, Image
    from reportlab.lib.styles import getSampleStyleSheet

    ais_path = os.path.join(os.path.dirname(__file__), "ais_live.json")
    if not os.path.exists(ais_path):
        return {"error": "No AIS data"}

    with open(ais_path, "r") as f:
        vessels = json.load(f)

    now = time.time()
    fresh = aging = dark = 0
    enriched = []

    for v in vessels:
        age_hours = (now - float(v.get("timestamp", now))) / 3600
        speed = float(v.get("speed") or 0)

        if age_hours < 1:
            status = "Fresh track"
            fresh += 1
        elif age_hours < 6:
            status = "Aging track"
            aging += 1
        else:
            status = "DARK / AIS LOST"
            dark += 1

        reasons = []

        if status == "DARK / AIS LOST":
            reasons.append("AIS signal loss — possible dark vessel activity")

        if status == "Aging track":
            reasons.append("Delayed AIS updates — possible signal degradation")

        zone = v.get("zone", "Unknown area")

        if status == "DARK / AIS LOST":
            reasons.append(
                f"AIS signal lost near {zone} — potential dark activity")

        elif speed < 0.3 and age_hours > 1:
            reasons.append(
                f"Prolonged low-speed movement near {zone} — possible loitering")

        elif speed < 0.3:
            reasons.append(f"Stationary vessel detected near {zone}")

        elif age_hours > 0.5:
            reasons.append(
                f"Recent AIS delay near {zone} — monitoring required")

        else:
            reasons.append(f"Normal transit activity through {zone}")

        if v.get("name", "Unknown") == "Unknown":
            reasons.append("Unidentified vessel — no name data available")

        if not reasons:
            reasons.append("Normal maritime activity — no immediate concern")

        enriched.append({
            "name": v.get("name", "Unknown"),
            "mmsi": v.get("mmsi"),
            "speed": speed,
            "course": v.get("course"),
            "status": status,
            "age": round(age_hours, 2),
            "reason": "; ".join(reasons)
        })

    enriched = sorted(enriched, key=lambda x: x["age"], reverse=True)

    if dark > 0:
        threat_level = "HIGH"
    elif aging > 0:
        threat_level = "MEDIUM"
    elif any(v["speed"] < 0.5 for v in enriched):
        threat_level = "LOW-MODERATE"
    else:
        threat_level = "LOW"

    if dark > 0:
        threat_level = "HIGH"
    elif aging > 0:
        threat_level = "MEDIUM"
    elif any(v["speed"] < 0.5 for v in enriched):
        threat_level = "LOW-MODERATE"
    else:
        threat_level = "LOW"

    report_path = os.path.join(os.path.dirname(__file__), "intel_report.pdf")
    doc = SimpleDocTemplate(report_path)
    styles = getSampleStyleSheet()
    content = []

    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "branding", "nayadra_insignia.png"))
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=110, height=110)
        content.append(logo)
        content.append(Spacer(1, 8))

    content.append(
        Paragraph(
            "NAYADRA Maritime-Cyber Intelligence Report",
            styles["Title"]))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"Generated: {time.ctime()}", styles["Normal"]))
    content.append(Paragraph(
        "<b>UNVERIFIED INTELLIGENCE PRODUCT — FOR REVIEW ONLY</b><br/>"
        "Contains AIS-derived maritime indicators and manually entered cyber OSINT. "
        "Not for public attribution without independent verification.",
        styles["Normal"]
    ))
    content.append(Spacer(1, 10))


    content.append(Spacer(1, 10))
    content.append(
        Paragraph(
            f"Threat Level: {threat_level}",
            styles["Heading2"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Executive Summary", styles["Heading2"]))
    content.append(Paragraph(
        f"This report provides a real-time overview of maritime activity within the Fiji monitoring zone. "
        f"A total of {len(vessels)} vessels are currently tracked. "
        f"{dark} vessels are classified as dark AIS-loss tracks, "
        f"{aging} vessels show degraded tracking, and "
        f"{fresh} vessels are actively transmitting.",
        styles["Normal"]
    ))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Track Status Overview", styles["Heading2"]))
    content.append(Paragraph(f"Fresh Tracks: {fresh}", styles["Normal"]))
    content.append(Paragraph(f"Aging Tracks: {aging}", styles["Normal"]))
    content.append(Paragraph(f"Dark Tracks: {dark}", styles["Normal"]))
    content.append(Spacer(1, 12))

    # Priority Targets Section
    priority = [v for v in enriched if v["status"] !=
                "Fresh track" or v["age"] > 1.5 or v["speed"] < 0.3]

    content.append(Paragraph("Priority Targets", styles["Heading2"]))

    if priority:
        for v in priority[:5]:
            content.append(
                Paragraph(
                    f"{
                        v['name']} | MMSI: {
                        v['mmsi']} | Status: {
                        v['status']} | " f"Speed: {
                        v['speed']} kn | Course: {
                            v['course']} | Age: {
                                v['age']}h | " f"Reason: {
                                    v.get(
                                        'reason',
                                        'Routine monitoring')}",
                    styles["Normal"]))
            content.append(Spacer(1, 6))
    else:
        content.append(
            Paragraph(
                "No priority targets detected at this time.",
                styles["Normal"]))

    content.append(Spacer(1, 12))

    content.append(Paragraph("Top Maritime Activity", styles["Heading2"]))
    for v in enriched[:8]:
        content.append(
            Paragraph(
                f"{
                    v['name']} | MMSI: {
                    v['mmsi']} | Status: {
                    v['status']} | " f"Speed: {
                        v['speed']} kn | Course: {
                            v['course']} | Age: {
                                v['age']}h",
                styles["Normal"]))
        content.append(Spacer(1, 6))

    content.append(Spacer(1, 12))
    content.append(Spacer(1, 12))

    # Phase 17G - Cyber Threat Intelligence Section
    cyber_path = os.path.join(os.path.dirname(__file__), "cyber_alerts.json")
    cyber_alerts = []

    try:
        if os.path.exists(cyber_path):
            with open(cyber_path, "r", encoding="utf-8") as cf:
                cyber_data = json.load(cf)
                if isinstance(cyber_data, list):
                    cyber_alerts = cyber_data
    except Exception:
        cyber_alerts = []

    content.append(Paragraph("Cyber Threat Intelligence", styles["Heading2"]))

    if cyber_alerts:
        verified_count = len([
            c for c in cyber_alerts
            if c.get("verification_status") == "VERIFIED" or c.get("status") == "VERIFIED"
        ])
        under_review_count = len([
            c for c in cyber_alerts
            if c.get("verification_status") == "UNDER_REVIEW" or c.get("status") == "UNDER_REVIEW"
        ])
        high_risk_cyber = len([
            c for c in cyber_alerts
            if str(c.get("risk", "")).upper() == "HIGH"
        ])

        content.append(Paragraph(
            f"Total Cyber Alerts: {len(cyber_alerts)}<br/>"
            f"Verified: {verified_count}<br/>"
            f"Under Review: {under_review_count}<br/>"
            f"High Risk Cyber Indicators: {high_risk_cyber}",
            styles["Normal"]
        ))
        content.append(Spacer(1, 8))

        for c in cyber_alerts[:5]:
            content.append(Paragraph(
                f"<b>{c.get('title', 'Untitled cyber alert')}</b><br/>"
                f"Type: {c.get('type', 'N/A')} | Risk: {c.get('risk', 'N/A')} | "
                f"Status: {c.get('verification_status', c.get('status', 'UNVERIFIED'))} | "
                f"Confidence: {c.get('confidence', 'N/A')}<br/>"
                f"Target: {c.get('target', 'N/A')} | Zone: {c.get('zone', 'N/A')}<br/>"
                f"Indicator: {c.get('indicator', 'N/A')}<br/>"
                f"Observed: {c.get('observed_date', 'N/A')} | Evidence: {c.get('evidence_file', 'N/A')}<br/>"
                f"Summary: {c.get('summary', 'No summary available.')}<br/>"
                f"Recommended Action: {c.get('recommended_action', 'Review and verify.')}<br/>"
                f"<b>Evidence Pack:</b><br/>"
                f"Alert ID: {c.get('id', 'N/A')}<br/>"
                f"Source URL: {c.get('source_url', 'N/A')}<br/>"
                f"Evidence File: {c.get('evidence_file', 'N/A')}<br/>"
                f"Observed Date: {c.get('observed_date', 'N/A')}<br/>"
                f"Analyst: {c.get('analyst_name', 'NAYADRA Analyst')}<br/>"
                f"Last Reviewed: {c.get('last_reviewed_at', 'Not reviewed')}<br/>"
                f"Analyst Note: {c.get('analyst_note', 'No analyst note recorded.')}<br/>"
                f"Safe Handling: Do not visit suspicious links directly. Preserve URL, screenshot, timestamps, and source context before escalation.",
                styles["Normal"]
            ))
            content.append(Spacer(1, 8))
    else:
        content.append(Paragraph(
            "No cyber threat intelligence entries were available at the time of report generation.",
            styles["Normal"]
        ))

    content.append(Spacer(1, 12))
    content.append(Paragraph("Maritime-Cyber Fusion Assessment", styles["Heading2"]))

    fusion_items = []
    try:
        for c in cyber_alerts:
            cyber_risk = str(c.get("risk", "LOW")).upper()
            cyber_target = str(c.get("target", "")).lower()
            cyber_zone = str(c.get("zone", "")).lower()

            if (
                cyber_risk in ["HIGH", "MEDIUM"]
                and len(vessels) > 0
                and (
                    "port" in cyber_zone
                    or "customs" in cyber_target
                    or "maritime" in cyber_target
                    or "border" in cyber_target
                )
            ):
                fusion_items.append(c)
    except Exception:
        fusion_items = []

    if fusion_items:
        content.append(Paragraph(
            f"{len(fusion_items)} cyber indicators are linked to maritime, port, customs, border, or agency-related targets while AIS vessel activity is active in the operational picture. "
            f"This does not confirm coordination, but it increases the need for cross-domain monitoring, evidence preservation, and verification before escalation.",
            styles["Normal"]
        ))
    else:
        content.append(Paragraph(
            "No maritime-cyber fusion indicators were detected at the time of report generation.",
            styles["Normal"]
        ))

    content.append(Spacer(1, 12))

    content.append(
        Paragraph(
            "Operational Recommendations",
            styles["Heading2"]))
    content.append(Paragraph(
        "Monitor vessels exhibiting AIS loss behaviour.<br/>"
        "Investigate stationary vessels in high-risk zones.<br/>"
        "Correlate maritime activity with intelligence sources.<br/>"
        "Maintain continuous situational awareness across Fiji waters.",
        styles["Normal"]
    ))

    doc.build(content)
    return send_file(report_path, as_attachment=True)






@app.route("/api/cyber-alert-report/<alert_id>")
def cyber_alert_report(alert_id):
    import os
    import json
    import time
    from flask import send_file, jsonify
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4

    cyber_path = os.path.join(os.path.dirname(__file__), "cyber_alerts.json")
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "branding", "nayadra_insignia.png"))

    if not os.path.exists(cyber_path):
        return jsonify({"status": "error", "message": "cyber_alerts.json not found"}), 404

    try:
        with open(cyber_path, "r", encoding="utf-8") as f:
            alerts = json.load(f)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    if not isinstance(alerts, list):
        return jsonify({"status": "error", "message": "cyber_alerts.json is not a list"}), 500

    alert = None
    for item in alerts:
        if str(item.get("id", "")).strip() == str(alert_id).strip():
            alert = item
            break

    if not alert:
        return jsonify({"status": "not_found", "message": f"No cyber alert found for {alert_id}"}), 404

    safe_alert_id = "".join(ch for ch in str(alert_id) if ch.isalnum() or ch in "-_")
    report_path = os.path.join(os.path.dirname(__file__), f"cyber_alert_report_{safe_alert_id}.pdf")

    doc = SimpleDocTemplate(report_path, pagesize=A4)
    styles = getSampleStyleSheet()
    content = []

    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=95, height=95)
            content.append(logo)
            content.append(Spacer(1, 8))
        except Exception:
            pass

    content.append(Paragraph("NAYADRA Cyber Alert Escalation Pack", styles["Title"]))
    content.append(Spacer(1, 8))
    content.append(Paragraph(f"Generated: {time.ctime()}", styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Intelligence Handling Disclaimer", styles["Heading2"]))
    content.append(Paragraph(
        "This report is an intelligence support document generated by the NAYADRA pilot system. "
        "It does not confirm criminal activity, compromise, attribution, or targeting. "
        "All indicators must be independently verified before operational escalation, public attribution, or enforcement action.",
        styles["Normal"]
    ))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Cyber Alert Summary", styles["Heading2"]))
    content.append(Paragraph(
        f"<b>Alert ID:</b> {alert.get('id', 'N/A')}<br/>"
        f"<b>Title:</b> {alert.get('title', 'N/A')}<br/>"
        f"<b>Type:</b> {alert.get('type', 'N/A')}<br/>"
        f"<b>Risk:</b> {alert.get('risk', 'N/A')}<br/>"
        f"<b>Confidence:</b> {alert.get('confidence', 'N/A')}<br/>"
        f"<b>Status:</b> {alert.get('verification_status', alert.get('status', 'UNVERIFIED'))}<br/>"
        f"<b>Target:</b> {alert.get('target', 'N/A')}<br/>"
        f"<b>Zone:</b> {alert.get('zone', 'N/A')}<br/>"
        f"<b>Indicator:</b> {alert.get('indicator', 'N/A')}<br/>"
        f"<b>Observed Date:</b> {alert.get('observed_date', 'N/A')}",
        styles["Normal"]
    ))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Evidence Pack", styles["Heading2"]))
    content.append(Paragraph(
        f"<b>Source:</b> {alert.get('source', 'N/A')}<br/>"
        f"<b>Source URL:</b> {alert.get('source_url', 'N/A')}<br/>"
        f"<b>Evidence File:</b> {alert.get('evidence_file', 'N/A')}<br/>"
        f"<b>Analyst:</b> {alert.get('analyst_name', 'NAYADRA Analyst')}<br/>"
        f"<b>Last Reviewed:</b> {alert.get('last_reviewed_at', 'Not reviewed')}<br/>"
        f"<b>Analyst Note:</b> {alert.get('analyst_note', 'No analyst note recorded.')}",
        styles["Normal"]
    ))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Summary and Recommended Action", styles["Heading2"]))
    content.append(Paragraph(
        f"<b>Summary:</b> {alert.get('summary', 'No summary available.')}<br/>"
        f"<b>Recommended Action:</b> {alert.get('recommended_action', 'Review and verify.')}",
        styles["Normal"]
    ))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Safe Handling Checklist", styles["Heading2"]))
    content.append(Paragraph(
        "1. Do not visit suspicious links directly.<br/>"
        "2. Preserve URL, screenshots, timestamps, and source context.<br/>"
        "3. Verify domain ownership, page history, and affected organisation context.<br/>"
        "4. Mark as VERIFIED only after independent confirmation.<br/>"
        "5. Mark as FALSE_POSITIVE if unrelated to Fiji, Pacific, maritime, port, customs, or government risk.<br/>"
        "6. Do not publicly attribute or accuse without confirmation.",
        styles["Normal"]
    ))

    doc.build(content)

    return send_file(report_path, as_attachment=True)


@app.route("/api/cyber-feed-health")
def cyber_feed_health():
    import os
    import json
    from datetime import datetime, timezone

    health_path = os.path.join(os.path.dirname(__file__), "cyber_feed_health.json")
    log_path = os.path.join(os.path.dirname(__file__), "cyber_feed_scheduler.log")

    payload = {
        "status": "UNKNOWN",
        "last_check_at": None,
        "last_added": None,
        "last_skipped": None,
        "total_alerts": None,
        "last_error": None,
        "log_exists": os.path.exists(log_path),
        "source": "OpenPhish scheduled feed"
    }

    try:
        if os.path.exists(health_path):
            with open(health_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    payload.update(data)
        else:
            payload["status"] = "NO_HEALTH_FILE"
            payload["last_error"] = "Scheduler has not written health file yet."
    except Exception as e:
        payload["status"] = "ERROR"
        payload["last_error"] = str(e)

    return jsonify(payload)


@app.route("/api/send-alerts")
def send_alerts():
    import json
    import time
    import os
    import smtplib
    from email.mime.text import MIMEText
    from flask import jsonify

    ais_path = os.path.join(os.path.dirname(__file__), "ais_live.json")

    if not os.path.exists(ais_path):
        return jsonify({"status": "no_data", "sent": 0})

    with open(ais_path, "r") as f:
        vessels = json.load(f)

    now = time.time()
    alerts = []

    for v in vessels:
        age_hours = round((now - float(v.get("timestamp", now))) / 3600, 2)
        speed = float(v.get("speed") or 0)
        zone = v.get("zone", "Unknown area")

        reasons = []

        if age_hours > 6:
            reasons.append("AIS signal lost / possible dark activity")

        if speed < 0.3:
            reasons.append(f"Stationary or loitering behaviour near {zone}")

        # Only alert on meaningful conditions
        if (
            age_hours > 2 or
            (speed < 0.3 and age_hours > 1) or
            "dark" in " ".join(reasons).lower()
        ):
            alerts.append({
                "name": v.get("name", "Unknown"),
                "mmsi": v.get("mmsi"),
                "zone": zone,
                "speed": speed,
                "age_hours": age_hours,
                "reasons": reasons
            })

    if not alerts:
        return jsonify({
            "status": "no_alerts",
            "message": "No alert-worthy vessels detected",
            "sent": 0
        })

    subject = "Gods Eye Maritime Alert"
    body = "Gods Eye Maritime Alert\n\n"

    for a in alerts[:5]:
        body += f"Vessel: {a['name']}\n"
        body += f"MMSI: {a['mmsi']}\n"
        body += f"Zone: {a['zone']}\n"
        body += f"Speed: {a['speed']} kn\n"
        body += f"Track age: {a['age_hours']} hours\n"
        body += f"Reason: {'; '.join(a['reasons'])}\n"
        body += "---\n"

    # Dry run by default unless email settings are provided
    smtp_user = os.getenv("ALERT_EMAIL_USER")
    smtp_pass = os.getenv("ALERT_EMAIL_PASS")
    alert_to = os.getenv("ALERT_EMAIL_TO")

    if not smtp_user or not smtp_pass or not alert_to:
        return jsonify({
            "status": "dry_run",
            "message": "Alert generated but not sent. Set ALERT_EMAIL_USER, ALERT_EMAIL_PASS and ALERT_EMAIL_TO to enable email.",
            "alerts": alerts[:5],
            "sent": 0
        })

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = alert_to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [alert_to], msg.as_string())

    return jsonify({
        "status": "sent",
        "sent": 1,
        "alerts": alerts[:5]
    })


@app.route("/api/zones")
def get_zones():
    import json
    import os
    from flask import jsonify

    zones_path = os.path.join(
        os.path.dirname(__file__),
        "config",
        "zones.json")

    if not os.path.exists(zones_path):
        return jsonify([])

    with open(zones_path, "r") as f:
        zones = json.load(f)

    return jsonify(zones)


@app.route("/api/test-cross-zone")
def test_cross_zone():
    test_vessel = {
        "id": "TEST-ROUTE-001",
        "mmsi": "999000111",
        "name": "TEST ROUTE VESSEL",
        "lat": -17.60,
        "lon": 177.44,
        "speed": 1,
        "risk": 0,
        "risk_flags": [],
        "zone_name": "Fiji Test Zone"
    }

    state = VESSEL_STATE.setdefault("999000111", {"loiter": 0, "zones": []})
    state.setdefault("zones", [])

    for z in ["Tonga Watch Zone", "Samoa Watch Zone", "Fiji Test Zone"]:
        if not state["zones"] or state["zones"][-1] != z:
            state["zones"].append(z)

    test_vessel["zone_history"] = state["zones"][-5:]

    if "Tonga Watch Zone" in test_vessel["zone_history"] and "Samoa Watch Zone" in test_vessel["zone_history"]:
        test_vessel["risk"] += 15
        test_vessel["risk_flags"].append("Tonga → Samoa route")

    if "Samoa Watch Zone" in test_vessel["zone_history"] and "Fiji Test Zone" in test_vessel["zone_history"]:
        test_vessel["risk"] += 15
        test_vessel["risk_flags"].append("Samoa → Fiji route")

    return jsonify(test_vessel)


@app.route("/api/vessel-timeline/<mmsi>")
def vessel_timeline_api(mmsi):
    return jsonify(get_vessel_timeline(mmsi))


@app.route("/api/priority-targets")
def priority_targets_api():

    try:

        vessels = list_vessels()

        alerts = generate_alerts(vessels)

        fusion_scores = process_fusion_scores(vessels, alerts)

        return jsonify(build_priority_targets(fusion_scores))

    except Exception as e:

        return jsonify({
            "error": "Priority target generation failed",
            "details": str(e)
        }), 500



@app.route("/api/vessel-profile")
def vessel_profile():
    token = request.args.get("token", "")
    mmsi = request.args.get("mmsi", "")

    if token != "gods_eye_pacific_admin_2026":
        return jsonify({
            "error": "unauthorized",
            "message": "Invalid or missing token"
        }), 401

    if not mmsi:
        return jsonify({
            "error": "missing_mmsi",
            "message": "Provide mmsi parameter"
        }), 400

    import json
    import os
    from datetime import datetime

    vessels = []

    possible_files = [
        "ais_live.json",
        "data/ais_live.json",
        "./ais_live.json",
        "./data/ais_live.json"
    ]

    for f in possible_files:
        try:
            if os.path.exists(f):
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)

                if isinstance(data, list):
                    vessels = data
                elif isinstance(data, dict):
                    vessels = data.get("vessels", data.get("contacts", data.get("data", [])))

                if vessels:
                    break
        except Exception:
            pass

    target = None

    # First search local/raw vessel list
    for v in vessels:
        if (
            str(v.get("mmsi", "")) == str(mmsi)
            or str(v.get("id", "")) == str(mmsi)
            or str(v.get("id", "")).replace("ais:", "") == str(mmsi).replace("ais:", "")
            or str(v.get("name", "")).strip().lower() == str(mmsi).strip().lower()
        ):
            target = v
            break

    # Fallback: search the same enriched source used by /api/vessels
    if not target:
        try:
            with app.test_client() as client:
                resp = client.get("/api/vessels")
                enriched = resp.get_json() or []
            for v in enriched:
                if (
                    str(v.get("mmsi", "")) == str(mmsi)
                    or str(v.get("id", "")) == str(mmsi)
                    or str(v.get("id", "")).replace("ais:", "") == str(mmsi).replace("ais:", "")
                    or str(v.get("name", "")).strip().lower() == str(mmsi).strip().lower()
                ):
                    target = v
                    break
            vessels = enriched
        except Exception:
            pass

    if not target:
        return jsonify({
            "error": "not_found",
            "mmsi": mmsi,
            "message": "Vessel not found in current AIS feed",
            "total_vessels_checked": len(vessels)
        }), 404

    flags = target.get("flags", [])
    if not isinstance(flags, list):
        flags = [str(flags)]

    # -----------------------------
    # Enriched vessel risk profiling
    # -----------------------------
    try:
        speed_val = float(target.get("speed", target.get("sog", 0)) or 0)
    except Exception:
        speed_val = 0

    try:
        age_val = target.get("age_hours", target.get("last_seen_age_hours", None))
        age_val = float(age_val) if age_val is not None else None
    except Exception:
        age_val = None

    risk_score_calc = int(target.get("risk_score", target.get("threat_score", target.get("risk", 0))) or 0)
    risk_level_calc = target.get("risk_level", target.get("risk", "Unknown"))
    track_status_calc = target.get("track_status", "STALE TRACK" if target.get("last_seen_age_hours") else "Unknown")
    recommendation_calc = target.get("recommendation", target.get("assessment", "Review vessel activity"))

    if speed_val <= 1:
        if "low_speed_or_stationary" not in flags:
            flags.append("low_speed_or_stationary")
        risk_score_calc += 15
        if track_status_calc == "Unknown":
            track_status_calc = "SLOW / STATIONARY"
        recommendation_calc = "Review vessel activity / possible loitering"

    if age_val is not None and age_val >= 6:
        if "dark_vessel_timer_triggered" not in flags:
            flags.append("dark_vessel_timer_triggered")
        risk_score_calc += 40
        track_status_calc = "DARK / AIS LOST"
        recommendation_calc = "Investigate AIS loss / possible dark activity"

    if risk_score_calc >= 70:
        risk_level_calc = "High"
    elif risk_score_calc >= 40:
        risk_level_calc = "Medium"
    elif risk_score_calc > 0:
        risk_level_calc = "Low"
    elif risk_level_calc == "Unknown":
        risk_level_calc = "Low"

    profile = {
        "mmsi": target.get("mmsi"),
        "name": target.get("name", target.get("shipname", target.get("ship_name", "UNKNOWN"))),
        "lat": target.get("lat"),
        "lon": target.get("lon"),
        "speed": speed_val,
        "course": target.get("course", target.get("cog")),
        "zone": target.get("zone", target.get("zone_name", target.get("zone_country", "Unknown"))),
        "risk_level": risk_level_calc,
        "risk_score": risk_score_calc,
        "track_status": track_status_calc,
        "recommendation": recommendation_calc,
        "flags": flags,
        "age_hours": age_val,
        "source": "AIS live feed / NAYADRA pilot intelligence engine",
        "linked_cases": [],
        "timeline_events": [
            {
                "event_type": "VESSEL_PROFILE_CREATED",
                "details": "Profile generated from current AIS feed",
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "risk_summary": {
            "linked_case_count": 0,
            "flags_count": len(flags),
            "current_status": track_status_calc
        }
    }

    return jsonify(profile)




CASE_NOTES_FILE = "case_notes.json"

def load_case_notes():
    import json, os
    if not os.path.exists(CASE_NOTES_FILE):
        return []
    try:
        with open(CASE_NOTES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_case_notes(notes):
    import json
    with open(CASE_NOTES_FILE, "w") as f:
        json.dump(notes, f, indent=2)

@app.route("/api/case-notes", methods=["GET"])
def get_case_notes():
    token = request.args.get("token", "")
    if token != "gods_eye_pacific_admin_2026":
        return jsonify({"error": "unauthorized"}), 401

    mmsi = request.args.get("mmsi", "")
    notes = load_case_notes()

    if mmsi:
        notes = [n for n in notes if str(n.get("mmsi", "")) == str(mmsi)]

    return jsonify({
        "count": len(notes),
        "case_notes": notes
    })

@app.route("/api/case-notes", methods=["POST"])
def create_case_note():
    from datetime import datetime, timezone

    data = request.get_json(silent=True) or {}
    token = data.get("token", "")

    if token != "gods_eye_pacific_admin_2026":
        return jsonify({"error": "unauthorized"}), 401

    notes = load_case_notes()

    note = {
        "case_id": f"CASE-{len(notes)+1:04d}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": data.get("name", "Unknown"),
        "mmsi": data.get("mmsi", "Unknown"),
        "zone": data.get("zone", "Unknown"),
        "risk_level": data.get("risk_level", "Unknown"),
        "risk_score": data.get("risk_score", 0),
        "track_status": data.get("track_status", "Unknown"),
        "validation_status": data.get("validation_status", "Pending"),
        "analyst_note": data.get("analyst_note", ""),
        "recommendation": data.get("recommendation", "Review vessel activity"),
        "source": data.get("source", "NAYADRA pilot intelligence engine")
    }

    notes.append(note)
    save_case_notes(notes)

    return jsonify({
        "saved": True,
        "case_note": note
    })




@app.route("/api/cyber-alerts")
def api_cyber_alerts():
    import json
    from pathlib import Path

    cyber_file = Path(__file__).with_name("cyber_alerts.json")

    try:
        if not cyber_file.exists():
            return jsonify([])

        with cyber_file.open("r", encoding="utf-8") as f:
            alerts = json.load(f)

        if not isinstance(alerts, list):
            return jsonify([])

        risk_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        alerts = sorted(
            alerts,
            key=lambda x: risk_order.get(str(x.get("risk", "")).upper(), 0),
            reverse=True
        )

        return jsonify(alerts)

    except Exception as e:
        return jsonify([
            {
                "type": "CYBER_ALERTS_ERROR",
                "risk": "HIGH",
                "msg": str(e)
            }
        ]), 500




@app.route("/api/maritime-cyber-fusion")
def api_maritime_cyber_fusion():
    import json
    from pathlib import Path
    from datetime import datetime, timezone

    base = Path(__file__).parent
    cyber_file = base / "cyber_alerts.json"
    ais_file = base / "ais_live.json"

    fusion_alerts = []

    try:
        cyber_alerts = []
        vessels = []

        if cyber_file.exists():
            with cyber_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    cyber_alerts = data

        if ais_file.exists():
            with ais_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    vessels = data
                elif isinstance(data, dict):
                    vessels = data.get("vessels", [])

        active_vessel_count = len(vessels)

        for c in cyber_alerts:
            cyber_risk = str(c.get("risk", "LOW")).upper()
            zone = c.get("zone", "Unknown Zone")

            if cyber_risk in ["HIGH", "MEDIUM"] and active_vessel_count > 0:
                fusion_risk = "HIGH" if cyber_risk == "HIGH" else "MEDIUM"

                fusion_alerts.append({
                    "id": f"FUSION-{c.get('id', 'UNKNOWN')}",
                    "type": "MARITIME_CYBER_FUSION",
                    "risk": fusion_risk,
                    "zone": zone,
                    "cyber_title": c.get("title", "Cyber alert"),
                    "cyber_type": c.get("type", "CYBER_ALERT"),
                    "cyber_target": c.get("target", "Unknown target"),
                    "maritime_context": f"{active_vessel_count} AIS contacts currently visible in the operational picture.",
                    "assessment": "Cyber activity is linked to a maritime or port-related zone while vessel activity is active. This may indicate opportunistic targeting, reconnaissance, fraud, or wider maritime-domain risk.",
                    "recommended_action": "Correlate cyber indicator with port activity, preserve evidence, verify affected organisations, and monitor vessels/alerts in the same zone.",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })

        return jsonify({
            "total": len(fusion_alerts),
            "fusion_alerts": fusion_alerts
        })

    except Exception as e:
        return jsonify({
            "total": 0,
            "fusion_alerts": [],
            "error": str(e)
        }), 500




@app.route("/api/add-cyber-alert", methods=["POST"])
def api_add_cyber_alert():
    import json
    from pathlib import Path
    from datetime import datetime, timezone
    from flask import request

    token = request.args.get("token", "")
    if token != "gods_eye_pacific_admin_2026":
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    cyber_file = Path(__file__).with_name("cyber_alerts.json")

    try:
        payload = request.get_json(force=True) or {}

        existing = []
        if cyber_file.exists():
            with cyber_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    existing = data

        new_id = f"CYBER-{len(existing) + 1:04d}"

        alert = {
            "id": new_id,
            "status": payload.get("status", "UNVERIFIED"),
            "confidence": payload.get("confidence", "LOW"),
            "verification_status": payload.get("verification_status", payload.get("status", "UNVERIFIED")),
            "observed_date": payload.get("observed_date", ""),
            "source_url": payload.get("source_url", ""),
            "evidence_file": payload.get("evidence_file", ""),
            "analyst_name": payload.get("analyst_name", "NAYADRA Analyst"),
            "analyst_note": payload.get("analyst_note", ""),
            "type": payload.get("type", "MANUAL_OSINT"),
            "title": payload.get("title", "Untitled cyber alert"),
            "target": payload.get("target", "Unknown target"),
            "zone": payload.get("zone", "Unknown zone"),
            "risk": payload.get("risk", "LOW"),
            "source": payload.get("source", "Manual OSINT"),
            "indicator": payload.get("indicator", "N/A"),
            "summary": payload.get("summary", "No summary provided."),
            "recommended_action": payload.get("recommended_action", "Review and verify."),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        existing.insert(0, alert)
        cyber_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")

        return jsonify({"ok": True, "added": alert, "total": len(existing)})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500




@app.route("/api/update-cyber-alert-status", methods=["POST"])
def api_update_cyber_alert_status():
    import json
    from pathlib import Path
    from datetime import datetime, timezone
    from flask import request

    token = request.args.get("token", "")
    if token != "gods_eye_pacific_admin_2026":
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    cyber_file = Path(__file__).with_name("cyber_alerts.json")

    try:
        payload = request.get_json(force=True) or {}
        alert_id = payload.get("id")
        new_status = payload.get("verification_status", "UNDER_REVIEW")
        note = payload.get("analyst_note", "")

        allowed = ["UNVERIFIED", "UNDER_REVIEW", "VERIFIED", "FALSE_POSITIVE"]
        if new_status not in allowed:
            return jsonify({"ok": False, "error": "Invalid status"}), 400

        if not alert_id:
            return jsonify({"ok": False, "error": "Missing alert id"}), 400

        alerts = []
        if cyber_file.exists():
            with cyber_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    alerts = data

        updated = None

        for item in alerts:
            if item.get("id") == alert_id:
                item["verification_status"] = new_status
                item["status"] = new_status
                item["last_reviewed_at"] = datetime.now(timezone.utc).isoformat()

                if note:
                    item["analyst_note"] = note

                updated = item
                break

        if not updated:
            return jsonify({"ok": False, "error": "Alert not found"}), 404

        cyber_file.write_text(json.dumps(alerts, indent=2), encoding="utf-8")

        return jsonify({"ok": True, "updated": updated})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500



# --- NAYADRA Behavioral Maritime Intelligence Engine ---
@app.route("/api/behavioral-events", methods=["GET"])
def behavioral_events_api():
    import json, os
    from flask import jsonify
    from behavioral_engine import generate_behavioral_events

    data_file = os.path.join(os.path.dirname(__file__), "ais_live.json")

    if not os.path.exists(data_file):
        return jsonify([])

    with open(data_file, "r") as f:
        vessels = json.load(f)

    if isinstance(vessels, dict):
        vessels = list(vessels.values())

    events = generate_behavioral_events(vessels)
    return jsonify(events)


# --- NAYADRA 24-Hour Night Movement Recall ---
@app.route("/api/night-movement/24h", methods=["GET"])
def night_movement_24h_api():
    import json, os
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo
    from flask import jsonify

    history_file = os.path.join(os.path.dirname(__file__), "intelligence", "behavioral_history.json")

    if not os.path.exists(history_file):
        return jsonify([])

    with open(history_file, "r") as f:
        history = json.load(f)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    results = []

    for event in history:
        if "NIGHT_MOVEMENT" not in event.get("detected_behaviors", []):
            continue

        raw_ts = event.get("timestamp")
        if not raw_ts:
            continue

        try:
            ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if ts < cutoff:
            continue

        results.append({
            "event_type": "NIGHT_MOVEMENT_24H",
            "vessel_name": event.get("vessel_name"),
            "mmsi": event.get("mmsi"),
            "timestamp_utc": ts.isoformat(),
            "fiji_time": ts.astimezone(ZoneInfo("Pacific/Fiji")).isoformat(),
            "latitude": event.get("latitude"),
            "longitude": event.get("longitude"),
            "risk": event.get("risk"),
            "behavior_score": event.get("behavior_score"),
            "detected_behaviors": event.get("detected_behaviors", [])
        })

    results.sort(key=lambda x: x["fiji_time"], reverse=True)
    return jsonify(results)


# --- NAYADRA Night Movement Text Report ---
@app.route("/api/night-movement/report", methods=["GET"])
def night_movement_report():
    from flask import Response
    import json, os
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo

    history_file = os.path.join(os.path.dirname(__file__), "intelligence", "behavioral_history.json")

    if not os.path.exists(history_file):
        data = []
    else:
        with open(history_file, "r") as f:
            history = json.load(f)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        data = []

        for event in history:
            if "NIGHT_MOVEMENT" not in event.get("detected_behaviors", []):
                continue

            raw_ts = event.get("timestamp")
            if not raw_ts:
                continue

            try:
                ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if ts < cutoff:
                continue

            data.append({
                "vessel_name": event.get("vessel_name"),
                "mmsi": event.get("mmsi"),
                "risk": event.get("risk"),
                "behavior_score": event.get("behavior_score"),
                "fiji_time": ts.astimezone(ZoneInfo("Pacific/Fiji")).isoformat(),
                "latitude": event.get("latitude"),
                "longitude": event.get("longitude"),
                "detected_behaviors": event.get("detected_behaviors", [])
            })

    lines = []
    lines.append("NAYADRA NIGHT MOVEMENT REPORT")
    lines.append("Pacific Maritime Intelligence Platform")
    lines.append("=" * 45)
    lines.append("")

    if not data:
        lines.append("No valid Fiji-time night movement events detected in the last 24 hours.")
    else:
        for i, e in enumerate(data, 1):
            lines.append(f"{i}. Vessel: {e.get('vessel_name')}")
            lines.append(f"   MMSI: {e.get('mmsi')}")
            lines.append(f"   Risk: {e.get('risk')}")
            lines.append(f"   Score: {e.get('behavior_score')}")
            lines.append(f"   Fiji Time: {e.get('fiji_time')}")
            lines.append(f"   Latitude: {e.get('latitude')}")
            lines.append(f"   Longitude: {e.get('longitude')}")
            lines.append(f"   Behaviors: {', '.join(e.get('detected_behaviors', []))}")
            lines.append("")

    return Response(
        "\n".join(lines),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=nayadra_night_movement_report.txt"}
    )


# --- NAYADRA Possible Night Stop Report ---
@app.route("/api/night-stop/report", methods=["GET"])
def possible_night_stop_report():
    from flask import Response
    import json, os
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo

    history_file = os.path.join(os.path.dirname(__file__), "intelligence", "behavioral_history.json")

    if not os.path.exists(history_file):
        history = []
    else:
        with open(history_file, "r") as f:
            history = json.load(f)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    events = []

    for event in history:
        behaviors = event.get("detected_behaviors", [])

        if "POSSIBLE_NIGHT_STOP_LOCATION" not in behaviors:
            continue

        raw_ts = event.get("timestamp")
        if not raw_ts:
            continue

        try:
            ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if ts < cutoff:
            continue

        events.append({
            "vessel_name": event.get("vessel_name"),
            "mmsi": event.get("mmsi"),
            "risk": event.get("risk"),
            "behavior_score": event.get("behavior_score"),
            "fiji_time": ts.astimezone(ZoneInfo("Pacific/Fiji")).isoformat(),
            "latitude": event.get("latitude"),
            "longitude": event.get("longitude"),
            "detected_behaviors": behaviors
        })

    # Deduplicate repeated same-vessel/same-location events
    deduped = {}
    for e in events:
        key = (
            e.get("mmsi"),
            round(float(e.get("latitude") or 0), 4),
            round(float(e.get("longitude") or 0), 4),
        )
        existing = deduped.get(key)
        if existing is None or e.get("behavior_score", 0) > existing.get("behavior_score", 0):
            deduped[key] = e

    events = list(deduped.values())
    events.sort(key=lambda x: x["fiji_time"], reverse=True)

    lines = []
    lines.append("NAYADRA POSSIBLE NIGHT STOP REPORT")
    lines.append("Pacific Maritime Intelligence Platform")
    lines.append("=" * 55)
    lines.append("")
    lines.append("Purpose:")
    lines.append("This report lists vessels detected as possible night-time offshore stop or loitering events within the last 24 hours using Fiji local time.")
    lines.append("")
    lines.append("Important Note:")
    lines.append("These are intelligence leads for analyst review only. A detection does not confirm criminal activity.")
    lines.append("")

    if not events:
        lines.append("No possible night-time offshore stop events detected in the last 24 hours.")
    else:
        for i, e in enumerate(events, 1):
            lines.append(f"{i}. Vessel: {e.get('vessel_name')}")
            lines.append(f"   MMSI: {e.get('mmsi')}")
            lines.append(f"   Risk: {e.get('risk')}")
            lines.append(f"   Behaviour Score: {e.get('behavior_score')}")
            lines.append(f"   Fiji Time: {e.get('fiji_time')}")
            lines.append(f"   Latitude: {e.get('latitude')}")
            lines.append(f"   Longitude: {e.get('longitude')}")
            lines.append(f"   Behaviours: {', '.join(e.get('detected_behaviors', []))}")
            lines.append("")
            lines.append("   Analyst Explanation:")
            lines.append("   This coordinate may represent a possible night-time offshore stop or loitering location because the vessel was detected slow/stationary outside a recognised port zone during Fiji night hours.")
            lines.append("")

    return Response(
        "\n".join(lines),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=nayadra_possible_night_stop_report.txt"}
    )


# --- NAYADRA Possible Night Stop PDF Report ---
@app.route("/api/night-stop/report/pdf", methods=["GET"])
def possible_night_stop_pdf_report():
    from flask import send_file
    import json, os
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch

    base_dir = os.path.dirname(__file__)
    history_file = os.path.join(base_dir, "intelligence", "behavioral_history.json")
    logo_file = os.path.join(base_dir, "reports", "nayadra_logo.png")
    output_file = os.path.join(base_dir, "reports", "nayadra_possible_night_stop_report.pdf")

    history = []
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            history = json.load(f)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    events = []

    for event in history:
        behaviors = event.get("detected_behaviors", [])
        if "POSSIBLE_NIGHT_STOP_LOCATION" not in behaviors:
            continue

        raw_ts = event.get("timestamp")
        if not raw_ts:
            continue

        try:
            ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if ts < cutoff:
            continue

        events.append({
            "vessel_name": event.get("vessel_name"),
            "mmsi": event.get("mmsi"),
            "risk": event.get("risk"),
            "behavior_score": event.get("behavior_score"),
            "fiji_time": ts.astimezone(ZoneInfo("Pacific/Fiji")).strftime("%Y-%m-%d %H:%M:%S %Z"),
            "latitude": event.get("latitude"),
            "longitude": event.get("longitude"),
            "detected_behaviors": ", ".join(behaviors),
        })

    deduped = {}
    for e in events:
        key = (e.get("mmsi"), round(float(e.get("latitude") or 0), 4), round(float(e.get("longitude") or 0), 4))
        old = deduped.get(key)
        if old is None or e.get("behavior_score", 0) > old.get("behavior_score", 0):
            deduped[key] = e
    events = list(deduped.values())

    doc = SimpleDocTemplate(output_file, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=40)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title", parent=styles["Title"], fontSize=18, leading=22, alignment=1)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10, leading=13)

    story = []

    if os.path.exists(logo_file):
        story.append(Image(logo_file, width=2.4*inch, height=2.4*inch))
        story.append(Spacer(1, 8))

    story.append(Paragraph("NA.YADRA Possible Night Stop Report", title))
    story.append(Paragraph("Pacific Maritime Intelligence Platform", styles["Heading3"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("This report lists possible night-time offshore stop or loitering events within the last 24 hours using Fiji local time.", body))
    story.append(Paragraph("Important: These are intelligence leads for analyst review only. A detection does not confirm criminal activity.", body))
    story.append(Spacer(1, 12))

    if not events:
        story.append(Paragraph("No possible night-time offshore stop events detected in the last 24 hours.", body))
    else:
        for i, e in enumerate(events, 1):
            data = [
                ["Field", "Details"],
                ["Vessel", str(e.get("vessel_name"))],
                ["MMSI", str(e.get("mmsi"))],
                ["Risk", str(e.get("risk"))],
                ["Behaviour Score", str(e.get("behavior_score"))],
                ["Fiji Time", str(e.get("fiji_time"))],
                ["Latitude", str(e.get("latitude"))],
                ["Longitude", str(e.get("longitude"))],
                ["Behaviours", str(e.get("detected_behaviors"))],
            ]
            table = Table(data, colWidths=[1.6*inch, 4.7*inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#8B0000")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
                ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#F7F7F7")),
                ("FONTSIZE", (0,0), (-1,-1), 8.5),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
            ]))
            story.append(Paragraph(f"Event {i}", styles["Heading2"]))
            story.append(table)
            story.append(Spacer(1, 8))
            story.append(Paragraph("Analyst Explanation: This coordinate may represent a possible night-time offshore stop or loitering location because the vessel was detected slow/stationary outside a recognised port zone during Fiji night hours.", body))
            story.append(Spacer(1, 12))

    story.append(Paragraph("© 2026 NA.YADRA Prototype - All Rights Reserved", styles["BodyText"]))
    doc.build(story)

    return send_file(output_file, as_attachment=True, download_name="nayadra_possible_night_stop_report.pdf")



# --- NA.YADRA ARROW Night Movement PDF Report ---
@app.route("/api/night-movement/arrow/report/pdf", methods=["GET"])
def arrow_night_movement_pdf_report():
    from flask import send_file
    import os
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch

    base_dir = os.path.dirname(__file__)
    logo_file = os.path.join(base_dir, "reports", "nayadra_logo.png")
    output_file = os.path.join(base_dir, "reports", "nayadra_arrow_night_movement_report.pdf")

    doc = SimpleDocTemplate(output_file, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=40)
    styles = getSampleStyleSheet()

    title = ParagraphStyle("Title", parent=styles["Title"], fontSize=18, leading=22, alignment=1)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=10)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10, leading=14)

    story = []

    if os.path.exists(logo_file):
        story.append(Image(logo_file, width=1.8*inch, height=1.8*inch))
        story.append(Spacer(1, 8))

    story.append(Paragraph("NA.YADRA Night Movement Intelligence Report", title))
    story.append(Paragraph("Pacific Maritime Intelligence Platform", styles["Heading3"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        "This report records a night movement detection for vessel ARROW near the Lautoka Port / Vuda Area. "
        "The event is generated from the NA.YADRA behavioural maritime monitoring engine.",
        body
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Event Summary", h2))

    data = [
        ["Field", "Details"],
        ["Vessel", "ARROW"],
        ["MMSI", "319245300"],
        ["Risk", "LOW"],
        ["Behaviour Score", "20"],
        ["Detected Behaviour", "NIGHT_MOVEMENT"],
        ["Fiji Time", "2026-05-21 01:51:54 FJT"],
        ["UTC Time", "2026-05-20 13:51:54 UTC"],
        ["Nearest Port", "Lautoka Port / Vuda Area"],
        ["Distance from Port", "6.75 nautical miles"],
        ["Latitude", "-17.64604166666667"],
        ["Longitude", "177.32996"],
    ]

    table = Table(data, colWidths=[1.8*inch, 4.6*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#8B0000")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#F7F7F7")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))

    story.append(table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Analyst Explanation", h2))
    story.append(Paragraph(
        "This event shows vessel ARROW detected during Fiji night-time movement outside the immediate Lautoka Port / Vuda Area. "
        "The LOW risk rating means the system has identified movement during night hours, but there is not enough supporting behaviour "
        "to classify it as suspicious by itself.",
        body
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "The coordinate listed above marks the vessel position at the time of detection. If the vessel later slows, stops, repeats this route, "
        "or operates near isolated areas or foreign vessels, the system can escalate the event into a higher-risk behavioural alert.",
        body
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Important Note: This report is an intelligence lead for analyst review only. A detection does not confirm criminal activity.",
        body
    ))

    story.append(Spacer(1, 14))
    story.append(Paragraph("© 2026 NA.YADRA Prototype - All Rights Reserved", styles["BodyText"]))

    doc.build(story)

    return send_file(output_file, as_attachment=True, download_name="nayadra_arrow_night_movement_report.pdf")



# --- NA.YADRA ANTHAS Night Stop PDF Report ---
@app.route("/api/night-stop/anthas/report/pdf", methods=["GET"])
def anthas_night_stop_pdf_report():
    from flask import send_file
    import os
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch

    base_dir = os.path.dirname(__file__)
    logo_file = os.path.join(base_dir, "reports", "nayadra_logo.png")
    output_file = os.path.join(base_dir, "reports", "nayadra_anthas_night_stop_report.pdf")

    doc = SimpleDocTemplate(output_file, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=40)
    styles = getSampleStyleSheet()

    title = ParagraphStyle("Title", parent=styles["Title"], fontSize=18, leading=22, alignment=1)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=10)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10, leading=14)

    story = []

    if os.path.exists(logo_file):
        story.append(Image(logo_file, width=1.8*inch, height=1.8*inch))
        story.append(Spacer(1, 8))

    story.append(Paragraph("NA.YADRA Possible Night Stop Intelligence Report", title))
    story.append(Paragraph("Pacific Maritime Intelligence Platform", styles["Heading3"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        "This report records a possible night-time offshore stop event for vessel ANTHAS near Denarau / Nadi Waters. "
        "The event is generated from the NA.YADRA behavioural maritime monitoring engine.",
        body
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Event Summary", h2))

    data = [
        ["Field", "Details"],
        ["Vessel", "ANTHAS"],
        ["MMSI", "253000026"],
        ["Risk", "HIGH"],
        ["Behaviour Score", "90"],
        ["Detected Behaviours", "OFFSHORE_LOW_SPEED_OR_STOPPED, NIGHT_OFFSHORE_STOP_INDICATOR, POSSIBLE_NIGHT_STOP_LOCATION, STOPPED_OUTSIDE_PORT_ZONE"],
        ["Fiji Time", "2026-05-21 01:51:54 FJT"],
        ["UTC Time", "2026-05-20 13:51:54 UTC"],
        ["Nearest Port", "Denarau / Nadi Waters"],
        ["Distance from Port", "3.08 nautical miles"],
        ["Speed", "0.0 knots"],
        ["Latitude", "-17.722289999999997"],
        ["Longitude", "177.37288666666666"],
    ]

    table = Table(data, colWidths=[1.8*inch, 4.6*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#8B0000")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#F7F7F7")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
    ]))

    story.append(table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Analyst Explanation", h2))
    story.append(Paragraph(
        "This event shows ANTHAS detected slow or stationary outside a recognised port zone during Fiji night hours. "
        "Because the vessel was recorded at 0.0 knots and outside the Denarau / Nadi port radius, the system escalated the behaviour "
        "as a possible night-time offshore stop location.",
        body
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "The HIGH risk rating is based on multiple combined behaviours: low speed or stopped offshore, night-time stop indicator, "
        "possible night stop location, and stopped outside port zone. This should be reviewed by an analyst against vessel history, "
        "route pattern, ownership, port call information, and any supporting intelligence.",
        body
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Important Note: This report is an intelligence lead for analyst review only. A detection does not confirm criminal activity.",
        body
    ))

    story.append(Spacer(1, 14))
    story.append(Paragraph("© 2026 NA.YADRA Prototype - All Rights Reserved", styles["BodyText"]))

    doc.build(story)

    return send_file(output_file, as_attachment=True, download_name="nayadra_anthas_night_stop_report.pdf")



# --- NA.YADRA Behavioural History 24h ---
@app.route("/api/behavioral-history/24h", methods=["GET"])
def behavioral_history_24h_api():
    from flask import jsonify
    import json, os
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo

    history_file = os.path.join(
        os.path.dirname(__file__),
        "intelligence",
        "behavioral_history.json"
    )

    if not os.path.exists(history_file):
        return jsonify([])

    with open(history_file, "r") as f:
        history = json.load(f)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    results = []

    for event in history:
        raw_ts = event.get("timestamp")
        if not raw_ts:
            continue

        try:
            ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if ts < cutoff:
            continue

        fiji_time = ts.astimezone(ZoneInfo("Pacific/Fiji"))

        results.append({
            "event_type": "BEHAVIOURAL_HISTORY_24H",
            "vessel_name": event.get("vessel_name"),
            "mmsi": event.get("mmsi"),
            "risk": event.get("risk"),
            "behavior_score": event.get("behavior_score"),
            "timestamp_utc": ts.isoformat(),
            "fiji_time": fiji_time.isoformat(),
            "latitude": event.get("latitude"),
            "longitude": event.get("longitude"),
            "detected_behaviors": event.get("detected_behaviors", []),
        })

    results.sort(key=lambda x: x["fiji_time"], reverse=True)
    return jsonify(results)



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)


# --- Zone detection helper ---
def is_in_bbox(vessel, bbox):
    """
    bbox format: [minLon, minLat, maxLon, maxLat]
    vessel needs lon/lng and lat.
    """
    lon = vessel.get("lon") or vessel.get("lng") or vessel.get("longitude")
    lat = vessel.get("lat") or vessel.get("latitude")

    if lon is None or lat is None:
        return False

    lon = float(lon)
    lat = float(lat)

    min_lon, min_lat, max_lon, max_lat = bbox

    # Normal bbox
    if min_lon <= max_lon:
        return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat

    # Dateline-crossing bbox
    return (lon >= min_lon or lon <= max_lon) and min_lat <= lat <= max_lat


def detect_zone(vessel, zones):
    """
    Returns the zone the vessel is currently inside, or None.
    """
    for zone in zones:
        bbox = zone.get("bbox")
        if bbox and is_in_bbox(vessel, bbox):
            return zone
    return None

# ===== AIS STATUS PATCH =====
from datetime import datetime, timezone

def get_status(ts):
    try:
        if isinstance(ts, str):
            ts = ts.replace("Z", "+00:00")
            t = datetime.fromisoformat(ts)
        else:
            return "UNKNOWN"

        now = datetime.now(timezone.utc)
        diff = (now - t).total_seconds()

        if diff < 300:
            return "LIVE"
        elif diff < 1800:
            return "DELAYED"
        else:
            return "STALE"
    except:
        return "UNKNOWN"
# ===== END PATCH =====


# ===== RENDEZVOUS DETECTION API =====
@app.route("/api/rendezvous")
def api_rendezvous():
    import json
    from flask import jsonify
    from rendezvous_engine import detect_rendezvous

    try:
        with open("ais_live.json") as f:
            vessels = json.load(f)

        alerts = detect_rendezvous(vessels)
        return jsonify(alerts)
    except Exception as e:
        return jsonify({"error": str(e), "alerts": []}), 500
# ===== END RENDEZVOUS DETECTION API =====



@app.route("/api/vessels/raw")
def get_raw_vessels():
    import json
    import os
    from flask import jsonify

    try:
        with open("ais_live.json", "r") as f:
            data = json.load(f)
    except Exception:
        return jsonify([])

    if isinstance(data, dict):
        data = list(data.values())

    if not isinstance(data, list):
        data = []

    return jsonify(data)


# ============================================================
# NAYADRA / GOD'S EYE - Vessel Profile Endpoint
# Safe endpoint for selected vessel intelligence profile
# ============================================================




