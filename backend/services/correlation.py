import math

def distance_km(lat1, lon1, lat2, lon2):
    # Haversine formula
    r = 6371.0

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r * c

def correlate_vessels_alerts(vessels, alerts, radius_km=80):
    enriched = []

    for vessel in vessels:
        vessel_lat = vessel.get("lat")
        vessel_lon = vessel.get("lon")

        nearby_alerts = []
        correlation_score = 0
        risk_flags = []

        if vessel_lat is None or vessel_lon is None:
            vessel["nearby_alerts"] = []
            vessel["correlation_score"] = 0
            vessel["risk_flags"] = ["missing_position"]
            enriched.append(vessel)
            continue

        for alert in alerts:
            alert_lat = alert.get("lat")
            alert_lon = alert.get("lon")

            if alert_lat is None or alert_lon is None:
                continue

            dist = distance_km(vessel_lat, vessel_lon, alert_lat, alert_lon)

            if dist <= radius_km:
                nearby_alerts.append({
                    "id": alert.get("id"),
                    "name": alert.get("name"),
                    "type": alert.get("type"),
                    "severity": alert.get("severity"),
                    "distance_km": round(dist, 2),
                })

                correlation_score += 20

                severity = str(alert.get("severity", "")).lower()
                if severity == "high":
                    correlation_score += 20
                elif severity == "medium":
                    correlation_score += 10

        if nearby_alerts:
            risk_flags.append("near_alert_activity")

        if len(nearby_alerts) >= 2:
            risk_flags.append("multiple_nearby_alerts")
            correlation_score += 15

        base_confidence = int(vessel.get("confidence", 0) or 0)
        final_score = min(base_confidence + correlation_score, 100)

        enriched_vessel = dict(vessel)
        enriched_vessel["nearby_alerts"] = nearby_alerts
        enriched_vessel["correlation_score"] = correlation_score
        enriched_vessel["confidence"] = final_score
        enriched_vessel["risk_flags"] = risk_flags

        enriched.append(enriched_vessel)

    return enriched
