from flask import Flask, jsonify, request
from flask_cors import CORS

from services.db import init_db, list_alerts, list_vessels, get_vessel_history
from services.correlation import correlate_vessels_alerts
from services.intelligence import score_vessels
from services.alert_correlation import correlate_alerts_vessels

app = Flask(__name__)
CORS(app)

init_db()
live_vessels = []

def get_scored_vessels():
    vessels_data = list_vessels(100)
    alerts_data = list_alerts(100)
    correlated = correlate_vessels_alerts(vessels_data, alerts_data, radius_km=80)
    scored = score_vessels(correlated)
    return scored

@app.route("/api/alerts")
def alerts():
    alerts_data = list_alerts(100)
    scored_vessels = get_scored_vessels()
    enriched_alerts = correlate_alerts_vessels(alerts_data, scored_vessels, radius_km=80)
    return jsonify(enriched_alerts)

@app.route("/api/vessels", methods=["GET", "POST"])
def handle_vessels():
    global live_vessels

    if request.method == "POST":
        data = request.json
        live_vessels = [v for v in live_vessels if v["id"] != data["id"]]
        live_vessels.append(data)
        live_vessels = live_vessels[-500:]
        return {"status": "added"}

    return jsonify(get_scored_vessels())

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

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
