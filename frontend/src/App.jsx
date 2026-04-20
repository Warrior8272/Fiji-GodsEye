import { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

function FitToData({ vessels, alerts }) {
  const map = useMap();

  useEffect(() => {
    const vesselPoints = (vessels || [])
      .map((v) => [Number(v.lat), Number(v.lon)])
      .filter(([lat, lon]) => !Number.isNaN(lat) && !Number.isNaN(lon));

    const alertPoints = (alerts || [])
      .map((a) => [Number(a.lat), Number(a.lon)])
      .filter(([lat, lon]) => !Number.isNaN(lat) && !Number.isNaN(lon));

    const allPoints = [...vesselPoints, ...alertPoints];

    if (allPoints.length === 1) {
      map.setView(allPoints[0], 8);
      return;
    }

    if (allPoints.length > 1) {
      map.fitBounds(allPoints, { padding: [40, 40] });
    }
  }, [vessels, alerts, map]);

  return null;
}

function isOnLand(lat, lon) {
  const nLat = Number(lat);
  const nLon = Number(lon);

  if (Number.isNaN(nLat) || Number.isNaN(nLon)) return false;

  return nLat > -18.1 && nLat < -17.5 && nLon > 177.5 && nLon < 178.3;
}

export default function App() {
  const [selected, setSelected] = useState(null);
  const [selectedType, setSelectedType] = useState(null);

  const [vessels, setVessels] = useState([]);
  const [alerts, setAlerts] = useState([]);

  const [loadingVessels, setLoadingVessels] = useState(true);
  const [loadingAlerts, setLoadingAlerts] = useState(true);

  const [vesselError, setVesselError] = useState("");
  const [alertError, setAlertError] = useState("");

  const [showVessels, setShowVessels] = useState(true);
  const [showAlerts, setShowAlerts] = useState(true);
  const [highRiskOnly, setHighRiskOnly] = useState(false);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/vessels")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Vessels HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setVessels(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        console.error("Vessels fetch error:", err);
        setVesselError(String(err));
        setVessels([]);
      })
      .finally(() => {
        setLoadingVessels(false);
      });
  }, []);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/alerts")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Alerts HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setAlerts(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        console.error("Alerts fetch error:", err);
        setAlertError(String(err));
        setAlerts([]);
      })
      .finally(() => {
        setLoadingAlerts(false);
      });
  }, []);

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

  const getRiskLabel = (confidence) => {
    const score = Number(confidence) || 0;
    if (score > 75) return "High";
    if (score > 50) return "Elevated";
    if (score > 25) return "Moderate";
    return "Low";
  };

  const visibleVessels = useMemo(() => {
    let data = vessels
      .map((v) => ({
        ...v,
        lat: Number(v.lat),
        lon: Number(v.lon),
        confidence: Number(v.confidence) || 0,
      }))
      .filter((v) => !Number.isNaN(v.lat) && !Number.isNaN(v.lon));

    if (highRiskOnly) {
      data = data.filter((v) => v.confidence > 50);
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
          <div
            style={{
              background: "#331111",
              color: "#ffb3b3",
              padding: "10px",
              borderRadius: "8px",
              marginBottom: "12px",
              fontSize: "13px",
            }}
          >
            Vessel fetch error: {vesselError}
          </div>
        )}

        {alertError && (
          <div
            style={{
              background: "#332211",
              color: "#ffd59a",
              padding: "10px",
              borderRadius: "8px",
              marginBottom: "12px",
              fontSize: "13px",
            }}
          >
            Alert fetch error: {alertError}
          </div>
        )}

        {!selected && (
          <div style={{ opacity: 0.9 }}>
            Select a vessel or alert on the map.
          </div>
        )}

        {selected && selectedType === "vessel" && (
          <>
            <h3 style={{ marginBottom: "12px" }}>{selected.name || "Unknown Vessel"}</h3>
            <p><strong>Category:</strong> Vessel</p>
            <p><strong>Type:</strong> {selected.type || "Unknown"}</p>
            <p><strong>Speed:</strong> {selected.speed ?? "N/A"}</p>
            <p><strong>Last Seen:</strong> {selected.lastSeen || "N/A"}</p>
            <p><strong>Confidence:</strong> {selected.confidence ?? 0}</p>
            <p><strong>Risk Level:</strong> {getRiskLabel(selected.confidence)}</p>
            <p><strong>Latitude:</strong> {selected.lat}</p>
            <p><strong>Longitude:</strong> {selected.lon}</p>

            {isOnLand(selected.lat, selected.lon) && (
              <p style={{ color: "orange", fontWeight: "bold" }}>
                ⚠️ Position anomaly detected
              </p>
            )}

            <hr style={{ borderColor: "#222", margin: "16px 0" }} />

            <p><strong>Assessment:</strong></p>
            <p style={{ lineHeight: 1.5 }}>
              {Number(selected.confidence) > 75
                ? "High-priority maritime contact requiring analyst review."
                : Number(selected.confidence) > 50
                ? "Elevated contact with moderate indicators of concern."
                : Number(selected.confidence) > 25
                ? "Moderate contact. Continue monitoring."
                : "Low concern contact based on current scoring."}
            </p>
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

            <hr style={{ borderColor: "#222", margin: "16px 0" }} />

            <p><strong>Assessment:</strong></p>
            <p style={{ lineHeight: 1.5 }}>
              This alert is plotted as part of the Phase 10B dashboard and can later be correlated
              with vessel activity, suspicious routes, or regional cyber reporting.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
