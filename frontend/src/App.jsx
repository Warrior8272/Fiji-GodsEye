import { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

function FitToData({ vessels, alerts, route, prediction, shouldFit }) {
  const map = useMap();

  useEffect(() => {
    if (!shouldFit) return;

    const vesselPoints = (vessels || [])
      .map((v) => [Number(v.lat), Number(v.lon)])
      .filter(([lat, lon]) => !Number.isNaN(lat) && !Number.isNaN(lon));

    const alertPoints = (alerts || [])
      .map((a) => [Number(a.lat), Number(a.lon)])
      .filter(([lat, lon]) => !Number.isNaN(lat) && !Number.isNaN(lon));

    const routePoints = (route || [])
      .map((p) => [Number(p[0]), Number(p[1])])
      .filter(([lat, lon]) => !Number.isNaN(lat) && !Number.isNaN(lon));

    const predictionPoints = (prediction || [])
      .map((p) => [Number(p[0]), Number(p[1])])
      .filter(([lat, lon]) => !Number.isNaN(lat) && !Number.isNaN(lon));

    const allPoints = [
      ...vesselPoints,
      ...alertPoints,
      ...routePoints,
      ...predictionPoints,
    ];

    if (allPoints.length === 1) {
      map.setView(allPoints[0], 9);
      return;
    }

    if (allPoints.length > 1) {
      map.fitBounds(allPoints, { padding: [40, 40] });
    }
  }, [vessels, alerts, route, prediction, shouldFit, map]);

  return null;
}

function isOnLand(lat, lon) {
  if (Number.isNaN(lat) || Number.isNaN(lon)) return false;

  return (
    lat > -18.2 &&
    lat < -17.6 &&
    lon > 177.3 &&
    lon < 178.2
  );
}

function projectPoint(lat, lon, courseDeg, distanceKm = 3) {
  const R = 6371;
  const bearing = (courseDeg * Math.PI) / 180;

  const lat1 = (lat * Math.PI) / 180;
  const lon1 = (lon * Math.PI) / 180;

  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(distanceKm / R) +
    Math.cos(lat1) * Math.sin(distanceKm / R) * Math.cos(bearing)
  );

  const lon2 =
    lon1 +
    Math.atan2(
      Math.sin(bearing) * Math.sin(distanceKm / R) * Math.cos(lat1),
      Math.cos(distanceKm / R) - Math.sin(lat1) * Math.sin(lat2)
    );

  return [
    (lat2 * 180) / Math.PI,
    (lon2 * 180) / Math.PI,
  ];
}

export default function App() {
  const [selected, setSelected] = useState(null);
  const [selectedType, setSelectedType] = useState(null);

  const [vessels, setVessels] = useState([]);
  const [alerts, setAlerts] = useState([]);

  const [route, setRoute] = useState([]);
  const [prediction, setPrediction] = useState([]);
  const [shouldFit, setShouldFit] = useState(true);

  const [loadingVessels, setLoadingVessels] = useState(true);
  const [loadingAlerts, setLoadingAlerts] = useState(true);

  const [vesselError, setVesselError] = useState("");
  const [alertError, setAlertError] = useState("");

  const [showVessels, setShowVessels] = useState(true);
  const [showAlerts, setShowAlerts] = useState(true);
  const [highRiskOnly, setHighRiskOnly] = useState(false);

  useEffect(() => {
    const loadVessels = () => {
      fetch("http://127.0.0.1:5000/api/vessels")
        .then((res) => {
          if (!res.ok) throw new Error(`Vessels HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          setVessels(Array.isArray(data) ? data : []);
          setVesselError("");
        })
        .catch((err) => {
          console.error("Vessels fetch error:", err);
          setVesselError(String(err));
          setVessels([]);
        })
        .finally(() => setLoadingVessels(false));
    };

    loadVessels();
    const interval = setInterval(loadVessels, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const loadAlerts = () => {
      fetch("http://127.0.0.1:5000/api/alerts")
        .then((res) => {
          if (!res.ok) throw new Error(`Alerts HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          setAlerts(Array.isArray(data) ? data : []);
          setAlertError("");
        })
        .catch((err) => {
          console.error("Alerts fetch error:", err);
          setAlertError(String(err));
          setAlerts([]);
        })
        .finally(() => setLoadingAlerts(false));
    };

    loadAlerts();
    const interval = setInterval(loadAlerts, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!shouldFit) return;
    const timer = setTimeout(() => setShouldFit(false), 1000);
    return () => clearTimeout(timer);
  }, [shouldFit]);

  const fetchRoute = async (id, vessel = null) => {
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/vessels/${id}/history`);
      const data = await res.json();

      const points = (Array.isArray(data) ? data : [])
        .slice(-15)
        .map((p) => ({
          lat: Number(p.lat),
          lon: Number(p.lon),
          course: Number(p.course),
        }))
        .filter((p) => !Number.isNaN(p.lat) && !Number.isNaN(p.lon));

      const smoothed = points
        .slice(-10)
        .map((p) => [p.lat, p.lon]);

      setRoute(smoothed);

      const recentCourses = points
        .slice(-3)
        .map((p) => p.course)
        .filter((c) => !Number.isNaN(c));

      let avgCourse = vessel ? Number(vessel.course) : NaN;
      if (recentCourses.length > 0) {
        avgCourse =
          recentCourses.reduce((sum, c) => sum + c, 0) / recentCourses.length;
      }

      const baseLat =
        points.length > 0 ? points[points.length - 1].lat : Number(vessel?.lat);
      const baseLon =
        points.length > 0 ? points[points.length - 1].lon : Number(vessel?.lon);
      const baseSpeed = Number(vessel?.speed);

      if (
        Number.isNaN(baseLat) ||
        Number.isNaN(baseLon) ||
        Number.isNaN(avgCourse) ||
        Number.isNaN(baseSpeed) ||
        baseSpeed < 1
      ) {
        setPrediction([]);
        return;
      }

      const predicted = projectPoint(baseLat, baseLon, avgCourse, 3);

      if (isOnLand(predicted[0], predicted[1])) {
        setPrediction([]);
        return;
      }

      setPrediction([
        [baseLat, baseLon],
        predicted,
      ]);
    } catch (err) {
      console.error("Route fetch failed:", err);
      setRoute([]);
      setPrediction([]);
    }
  };

  const calculatePrediction = (v) => {
    if (!v) {
      setPrediction([]);
      return;
    }

    const lat = Number(v.lat);
    const lon = Number(v.lon);
    const course = Number(v.course);
    const speed = Number(v.speed);

    if (
      Number.isNaN(lat) ||
      Number.isNaN(lon) ||
      Number.isNaN(course) ||
      Number.isNaN(speed) ||
      speed < 1
    ) {
      setPrediction([]);
      return;
    }

    const predicted = projectPoint(lat, lon, course, 3);

    if (isOnLand(predicted[0], predicted[1])) {
      setPrediction([]);
      return;
    }

    setPrediction([
      [lat, lon],
      predicted,
    ]);
  };

  const getConfidenceColor = (confidence) => {
    const score = Number(confidence) || 0;
    if (score > 75) return "red";
    if (score > 50) return "orange";
    if (score > 25) return "yellow";
    return "green";
  };

  const getAlertColor = (severity) => {
    const value = String(severity || "").toLowerCase();
    if (value === "high") return "red";
    if (value === "medium") return "orange";
    if (value === "low") return "yellow";
    return "deepskyblue";
  };

  const visibleVessels = useMemo(() => {
    let data = vessels
      .map((v) => ({
        ...v,
        lat: Number(v.lat),
        lon: Number(v.lon),
        speed: Number(v.speed) || 0,
        course: Number(v.course),
        heading: Number(v.heading),
        confidence: Number(v.confidence) || 0,
        correlation_score: Number(v.correlation_score) || 0,
      }))
      .filter((v) => !Number.isNaN(v.lat) && !Number.isNaN(v.lon));

    if (highRiskOnly) {
      data = data.filter((v) => Number(v.confidence) > 50);
    }

    return data.slice(0, 100);
  }, [vessels, highRiskOnly]);

  const visibleAlerts = useMemo(() => {
    let data = alerts
      .map((a) => ({
        ...a,
        lat: Number(a.lat),
        lon: Number(a.lon),
      }))
      .filter((a) => !Number.isNaN(a.lat) && !Number.isNaN(a.lon));

    if (highRiskOnly) {
      data = data.filter(
        (a) => String(a.severity || "").toLowerCase() === "high"
      );
    }

    return data.slice(0, 100);
  }, [alerts, highRiskOnly]);

  const totalVisible =
    (showVessels ? visibleVessels.length : 0) +
    (showAlerts ? visibleAlerts.length : 0);

  return (
    <div style={{ display: "flex", height: "100vh", width: "100%", background: "#0b1020" }}>
      <div style={{ flex: 3, position: "relative" }}>
        <div
          style={{
            position: "absolute",
            zIndex: 1000,
            top: 12,
            left: 12,
            background: "rgba(10,10,10,0.88)",
            color: "#fff",
            padding: "10px 12px",
            borderRadius: "10px",
            minWidth: "220px",
            boxShadow: "0 4px 14px rgba(0,0,0,0.3)",
            fontSize: "14px",
          }}
        >
          <div style={{ fontWeight: "bold", marginBottom: "8px" }}>Phase 10B Controls</div>

          <label style={{ display: "block", marginBottom: "6px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={showVessels}
              onChange={() => setShowVessels((prev) => !prev)}
              style={{ marginRight: "8px" }}
            />
            Show vessels
          </label>

          <label style={{ display: "block", marginBottom: "6px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={showAlerts}
              onChange={() => setShowAlerts((prev) => !prev)}
              style={{ marginRight: "8px" }}
            />
            Show alerts
          </label>

          <label style={{ display: "block", marginBottom: "8px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={highRiskOnly}
              onChange={() => setHighRiskOnly((prev) => !prev)}
              style={{ marginRight: "8px" }}
            />
            High risk only
          </label>

          <div style={{ opacity: 0.9 }}>Visible items: {totalVisible}</div>
        </div>

        <MapContainer
          center={[-18.2, 177.2]}
          zoom={7}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

          <FitToData
            vessels={showVessels ? visibleVessels : []}
            alerts={showAlerts ? visibleAlerts : []}
            route={route}
            prediction={prediction}
            shouldFit={shouldFit}
          />

          {showVessels &&
            visibleVessels.map((v) => {
              const anomaly = isOnLand(v.lat, v.lon);

              return (
                <CircleMarker
                  key={`vessel-${v.id}`}
                  center={[v.lat, v.lon]}
                  radius={10}
                  pathOptions={{
                    color: anomaly ? "purple" : getConfidenceColor(v.confidence),
                    fillColor: anomaly ? "purple" : getConfidenceColor(v.confidence),
                    fillOpacity: 0.85,
                    weight: 3,
                  }}
                  eventHandlers={{
                    click: () => {
                      setSelected(v);
                      setSelectedType("vessel");
                      fetchRoute(v.id, v);
                      calculatePrediction(v);
                      setShouldFit(true);
                    },
                  }}
                >
                  <Popup>
                    <strong>{v.name || "Unknown Vessel"}</strong>
                    <br />
                    Type: {v.type || "Unknown"}
                    <br />
                    Speed: {v.speed ?? "N/A"}
                    <br />
                    Course: {Number.isNaN(v.course) ? "N/A" : v.course}
                    <br />
                    Heading: {Number.isNaN(v.heading) ? "N/A" : v.heading}
                    <br />
                    Last Seen: {v.lastSeen || "N/A"}
                    <br />
                    Confidence: {v.confidence}
                    <br />
                    Lat: {v.lat}
                    <br />
                    Lon: {v.lon}
                    <br />
                    Anomaly: {anomaly ? "Yes" : "No"}
                  </Popup>
                </CircleMarker>
              );
            })}

          {showAlerts &&
            visibleAlerts.map((a) => (
              <CircleMarker
                key={`alert-${a.id}`}
                center={[a.lat, a.lon]}
                radius={8}
                pathOptions={{
                  color: getAlertColor(a.severity),
                  fillColor: getAlertColor(a.severity),
                  fillOpacity: 0.9,
                  weight: 2,
                }}
                eventHandlers={{
                  click: () => {
                    setSelected(a);
                    setSelectedType("alert");
                    setRoute([]);
                    setPrediction([]);
                    setShouldFit(true);
                  },
                }}
              >
                <Popup>
                  <strong>{a.name || "Alert"}</strong>
                  <br />
                  Type: {a.type || "Unknown"}
                  <br />
                  Severity: {a.severity || "N/A"}
                  <br />
                  Lat: {a.lat}
                  <br />
                  Lon: {a.lon}
                </Popup>
              </CircleMarker>
            ))}

          {route.length > 1 && (
            <Polyline positions={route} pathOptions={{ color: "blue", weight: 4 }} />
          )}

          {prediction.length > 1 && (
            <Polyline
              positions={prediction}
              pathOptions={{ color: "cyan", weight: 3, dashArray: "6, 6" }}
            />
          )}
        </MapContainer>
      </div>

      <div
        style={{
          flex: 1,
          background: "#0a0a0a",
          color: "#fff",
          padding: "18px",
          overflowY: "auto",
          borderLeft: "1px solid #222",
        }}
      >
        <h2 style={{ marginTop: 0 }}>🧠 Intelligence Panel</h2>

        <div style={{ marginBottom: "16px", fontSize: "14px", opacity: 0.9 }}>
          <div>Vessels: {loadingVessels ? "Loading..." : visibleVessels.length}</div>
          <div>Alerts: {loadingAlerts ? "Loading..." : visibleAlerts.length}</div>
        </div>

        {vesselError && (
          <div style={{ background: "#331111", color: "#ffb3b3", padding: "10px", borderRadius: "8px", marginBottom: "12px", fontSize: "13px" }}>
            Vessel fetch error: {vesselError}
          </div>
        )}

        {alertError && (
          <div style={{ background: "#332211", color: "#ffd59a", padding: "10px", borderRadius: "8px", marginBottom: "12px", fontSize: "13px" }}>
            Alert fetch error: {alertError}
          </div>
        )}

        {!selected && <div style={{ opacity: 0.9 }}>Select a vessel or alert on the map.</div>}

        {selected && selectedType === "vessel" && (
          <>
            <h3 style={{ marginBottom: "12px" }}>{selected.name || "Unknown Vessel"}</h3>
            <p><strong>Category:</strong> Vessel</p>
            <p><strong>Type:</strong> {selected.type || "Unknown"}</p>
            <p><strong>Speed:</strong> {selected.speed ?? "N/A"}</p>
            <p><strong>Course:</strong> {Number.isNaN(Number(selected.course)) ? "N/A" : selected.course}</p>
            <p><strong>Heading:</strong> {Number.isNaN(Number(selected.heading)) ? "N/A" : selected.heading}</p>
            <p><strong>Last Seen:</strong> {selected.lastSeen || "N/A"}</p>
            <p><strong>Confidence:</strong> {selected.confidence ?? 0}</p>
            <p><strong>Risk Level:</strong> {selected.risk_level || "Unknown"}</p>
            <p><strong>Latitude:</strong> {selected.lat}</p>
            <p><strong>Longitude:</strong> {selected.lon}</p>
            <p><strong>Correlation Score:</strong> {selected.correlation_score ?? 0}</p>
            <p><strong>Risk Flags:</strong> {(selected.risk_flags || []).join(", ") || "None"}</p>
            <p><strong>Last Seen Age (hrs):</strong> {selected.last_seen_age_hours ?? "N/A"}</p>
            <p><strong>Assessment:</strong> {selected.assessment || "No assessment yet"}</p>

            {isOnLand(selected.lat, selected.lon) && (
              <p style={{ color: "orange", fontWeight: "bold" }}>⚠️ Position anomaly detected</p>
            )}

            {selected.score_breakdown && (
              <>
                <hr style={{ borderColor: "#222", margin: "16px 0" }} />
                <p><strong>Score Breakdown:</strong></p>
                <p>Base Confidence: {selected.score_breakdown.base_confidence}</p>
                <p>Correlation: {selected.score_breakdown.correlation}</p>
                <p>Anomaly: {selected.score_breakdown.anomaly}</p>
                <p>Stale Tracking: {selected.score_breakdown.stale_tracking}</p>
                <p>Type Weight: {selected.score_breakdown.type_weight}</p>
                <p>Multiple Alert Bonus: {selected.score_breakdown.multiple_alert_bonus}</p>
              </>
            )}

            {selected.nearby_alerts && selected.nearby_alerts.length > 0 && (
              <>
                <hr style={{ borderColor: "#222", margin: "16px 0" }} />
                <p><strong>Nearby Alerts:</strong></p>
                {selected.nearby_alerts.map((alert, idx) => (
                  <div key={idx} style={{ marginBottom: "10px", padding: "8px", background: "#111", borderRadius: "8px" }}>
                    <div><strong>{alert.name}</strong></div>
                    <div>Type: {alert.type}</div>
                    <div>Severity: {alert.severity}</div>
                    <div>Distance: {alert.distance_km} km</div>
                  </div>
                ))}
              </>
            )}
          </>
        )}

        {selected && selectedType === "alert" && (
          <>
            <h3 style={{ marginBottom: "12px" }}>{selected.name || "Alert"}</h3>
            <p><strong>Category:</strong> Alert</p>
            <p><strong>Type:</strong> {selected.type || "Unknown"}</p>
            <p><strong>Severity:</strong> {selected.severity || "N/A"}</p>
            <p><strong>Latitude:</strong> {selected.lat}</p>
            <p><strong>Longitude:</strong> {selected.lon}</p>
            <p><strong>Nearby Vessel Count:</strong> {selected.vessel_count ?? 0}</p>
            <p><strong>Nearest Vessel Distance:</strong> {selected.nearest_vessel_distance ?? "N/A"} km</p>

            <hr style={{ borderColor: "#222", margin: "16px 0" }} />

            <p><strong>Assessment:</strong></p>
            <p style={{ lineHeight: 1.5 }}>
              {selected.vessel_count > 0
                ? `This alert is geographically linked to ${selected.vessel_count} nearby vessel(s), with the nearest vessel at ${selected.nearest_vessel_distance} km.`
                : "No nearby vessels are currently linked to this alert."}
            </p>

            {selected.nearby_vessels && selected.nearby_vessels.length > 0 && (
              <>
                <hr style={{ borderColor: "#222", margin: "16px 0" }} />
                <p><strong>Nearby Vessels:</strong></p>
                {selected.nearby_vessels.map((vessel, idx) => (
                  <div key={idx} style={{ marginBottom: "10px", padding: "8px", background: "#111", borderRadius: "8px" }}>
                    <div><strong>{vessel.name}</strong></div>
                    <div>Type: {vessel.type}</div>
                    <div>Risk: {vessel.risk_level || "Unknown"}</div>
                    <div>Confidence: {vessel.confidence}</div>
                    <div>Distance: {vessel.distance_km} km</div>
                  </div>
                ))}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
