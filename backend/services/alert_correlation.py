from services.correlation import distance_km

def correlate_alerts_vessels(alerts, vessels, radius_km=80):
    enriched = []

    for alert in alerts:
        alert_lat = alert.get("lat")
        alert_lon = alert.get("lon")

        nearby_vessels = []
        nearest_vessel_distance = None
        nearest_vessel_id = None

        if alert_lat is None or alert_lon is None:
            enriched_alert = dict(alert)
            enriched_alert["nearby_vessels"] = []
            enriched_alert["vessel_count"] = 0
            enriched_alert["nearest_vessel_distance"] = None
            enriched_alert["nearest_vessel_id"] = None
            enriched.append(enriched_alert)
            continue

        for vessel in vessels:
            vessel_lat = vessel.get("lat")
            vessel_lon = vessel.get("lon")

            if vessel_lat is None or vessel_lon is None:
                continue

            dist = distance_km(alert_lat, alert_lon, vessel_lat, vessel_lon)

            if nearest_vessel_distance is None or dist < nearest_vessel_distance:
                nearest_vessel_distance = dist
                nearest_vessel_id = vessel.get("id")

            if dist <= radius_km:
                nearby_vessels.append({
                    "id": vessel.get("id"),
                    "name": vessel.get("name"),
                    "type": vessel.get("type"),
                    "risk_level": vessel.get("risk_level"),
                    "confidence": vessel.get("confidence"),
                    "distance_km": round(dist, 2),
                })

        enriched_alert = dict(alert)
        enriched_alert["nearby_vessels"] = nearby_vessels
        enriched_alert["vessel_count"] = len(nearby_vessels)
        enriched_alert["nearest_vessel_distance"] = (
            round(nearest_vessel_distance, 2)
            if nearest_vessel_distance is not None else None
        )
        enriched_alert["nearest_vessel_id"] = nearest_vessel_id

        enriched.append(enriched_alert)

    return enriched
