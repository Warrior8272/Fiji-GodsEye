from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/api/vessels")
def vessels():
    return jsonify([
        {
            "id": 1,
            "name": "Cargo Alpha",
            "lat": -18.2,
            "lon": 177.2,
            "speed": 10,
            "lastSeen": "5m ago",
            "confidence": 70,
            "type": "Cargo"
        },
        {
            "id": 2,
            "name": "Unknown Vessel",
            "lat": -18.5,
            "lon": 176.8,
            "speed": 12,
            "lastSeen": "1h ago",
            "confidence": 80,
            "type": "Unknown"
        }
    ])

@app.route("/api/alerts")
def alerts():
    return jsonify([
        {
            "id": 1,
            "name": "Phishing Campaign",
            "lat": -17.75,
            "lon": 178.45,
            "severity": "high",
            "type": "cyber"
        },
        {
            "id": 2,
            "name": "Suspicious Maritime Activity",
            "lat": -18.05,
            "lon": 177.65,
            "severity": "medium",
            "type": "maritime"
        }
    ])

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
