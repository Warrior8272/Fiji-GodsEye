from collections import defaultdict
from datetime import datetime
import math

PREDICTION_MEMORY = defaultdict(lambda: {
    "activity": 0,
    "threat": 0,
    "dark": 0,
    "clusters": 0,
    "rendezvous": 0
})

def sector_key(lat, lon):
    try:
        lat = round(float(lat), 1)
        lon = round(float(lon), 1)
        return f"{lat}:{lon}"
    except:
        return None

def process_prediction(vessel):
    lat = vessel.get("lat")
    lon = vessel.get("lon")

    key = sector_key(lat, lon)
    if not key:
        return

    mem = PREDICTION_MEMORY[key]

    mem["activity"] += 1

    level = str(vessel.get("threat_level", "")).upper()

    if level in ["HIGH", "CRITICAL"]:
        mem["threat"] += 1

    if vessel.get("memory", {}).get("dark_activity_count", 0) > 0:
        mem["dark"] += 1

    if vessel.get("memory", {}).get("rendezvous_count", 0) > 0:
        mem["rendezvous"] += 1

    if vessel.get("memory", {}).get("repeat_offender_score", 0) >= 50:
        mem["clusters"] += 1

def generate_predictions():
    predictions = []

    for sector, data in PREDICTION_MEMORY.items():

        score = (
            data["activity"] * 1 +
            data["threat"] * 5 +
            data["dark"] * 8 +
            data["rendezvous"] * 10 +
            data["clusters"] * 12
        )

        if score < 5:
            continue

        lat, lon = sector.split(":")
        lat = float(lat)
        lon = float(lon)

        if score >= 120:
            severity = "CRITICAL"
        elif score >= 70:
            severity = "HIGH"
        elif score >= 35:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        predictions.append({
            "sector": sector,
            "lat": lat,
            "lon": lon,
            "prediction_score": score,
            "severity": severity,
            "activity": data["activity"],
            "threat_activity": data["threat"],
            "dark_activity": data["dark"],
            "rendezvous_activity": data["rendezvous"],
            "repeat_offender_activity": data["clusters"],
            "forecast": "Likely future high-risk maritime activity sector"
        })

    predictions.sort(
        key=lambda x: x["prediction_score"],
        reverse=True
    )

    return predictions[:25]


def generate_test_predictions():
    return [{
        "sector": "-18.1:177.4",
        "lat": -18.1,
        "lon": 177.4,
        "prediction_score": 145,
        "severity": "CRITICAL",
        "activity": 40,
        "threat_activity": 18,
        "dark_activity": 6,
        "rendezvous_activity": 4,
        "repeat_offender_activity": 5,
        "forecast": "Predicted narcotics trafficking corridor escalation"
    }]
