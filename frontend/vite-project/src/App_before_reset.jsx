import { useEffect, useMemo, useState } from "react";
  const SENTINEL_INSTANCE = "PLAKfb35bc95238a4d45bac71029cb2e9ab5";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Rectangle,
  Circle,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const blueIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const redIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const dangerIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-violet.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [35, 55],
  iconAnchor: [17, 55],
  popupAnchor: [1, -40],
  shadowSize: [50, 50],
});

const liveIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [30, 48],
  iconAnchor: [15, 48],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function FocusHighestRisk({ ship }) {
  const map = useMap();

  useEffect(() => {
    if (ship && ship.lat !== undefined && ship.lon !== undefined) {
      map.setView([ship.lat, ship.lon], 7, { animate: true });
    }
  }, [ship, map]);

  return null;
}

function getLabelStyle(label) {
  const l = String(label || "").toLowerCase();

  if (l.includes("live ais")) {
    return { backgroundColor: "#1677ff", color: "white" };
  }

  if (l.includes("drug") || l.includes("priority")) {
    return { backgroundColor: "#ff4d4f", color: "white" };
  }

  if (l.includes("suspicious") || l.includes("cyber")) {
    return { backgroundColor: "#fa8c16", color: "white" };
  }

  if (l.includes("tanker")) {
    return { backgroundColor: "#722ed1", color: "white" };
  }

  if (l.includes("zone") || l.includes("cargo")) {
    return { backgroundColor: "#52c41a", color: "white" };
  }

  if (l.includes("loitering") || l.includes("unusual speed") || l.includes("repeated")) {
    return { backgroundColor: "#13c2c2", color: "white" };
  }

  return { backgroundColor: "#d9d9d9", color: "black" };
}

function App() {
  const [ships, setShips] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [cyberAlerts, setCyberAlerts] = useState([]);
  const [correlations, setCorrelations] = useState([]);
  const [filter, setFilter] = useState("all");
  const [replayStep, setReplayStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [autoFocusDanger, setAutoFocusDanger] = useState(true);
  const [basemap, setBasemap] = useState("osm");
  const [historicalMode, setHistoricalMode] = useState("current");
  const [waybackVersion, setWaybackVersion] = useState("2024");

  const WATCH_ZONE = [
    [-18.5, 177.5],
    [-17.5, 178.5],
  ];

  const WAYBACK_APP_URL = "https://livingatlas.arcgis.com/wayback/";

  // Placeholder labels for analyst workflow.
  // Later we can replace these with exact verified dated Wayback layer URLs.
  const waybackOptions = [
    { value: "2025", label: "Wayback 2025" },
    { value: "2024", label: "Wayback 2024" },
    { value: "2023", label: "Wayback 2023" },
    { value: "2022", label: "Wayback 2022" },
    { value: "2020", label: "Wayback 2020" },
  ];

  const isInsideZone = (ship) => {
    return (
      ship.lat >= WATCH_ZONE[0][0] &&
      ship.lat <= WATCH_ZONE[1][0] &&
      ship.lon >= WATCH_ZONE[0][1] &&
      ship.lon <= WATCH_ZONE[1][1]
    );
  };

  const getSeverityStyle = (severity) => {
    if (severity === "high") {
      return {
        backgroundColor: "#ffcccc",
        border: "1px solid #cc0000",
      };
    }
    if (severity === "medium") {
      return {
        backgroundColor: "#fff3cd",
        border: "1px solid #cc7a00",
      };
    }
    return {
      backgroundColor: "#d4edda",
      border: "1px solid #2d862d",
    };
  };

  const getCyberCircleStyle = (alert) => {
    const heat = alert.heat || 3;

    if (heat >= 8) {
      return {
        color: "#cc0000",
        fillColor: "#ff1a1a",
        fillOpacity: 0.3,
        radius: 18000,
      };
    }

    if (heat >= 5) {
      return {
        color: "#cc7a00",
        fillColor: "#ffb84d",
        fillOpacity: 0.24,
        radius: 13000,
      };
    }

    return {
      color: "#2d862d",
      fillColor: "#66cc66",
      fillOpacity: 0.18,
      radius: 9000,
    };
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const shipsRes = await fetch("http://127.0.0.1:8000/api/live-ships");
        const shipsData = await shipsRes.json();
        setShips(Array.isArray(shipsData) ? shipsData : []);
      } catch (err) {
        console.error("Ships fetch error:", err);
        setShips([]);
      }

      try {
        const alertsRes = await fetch("http://127.0.0.1:8000/api/alerts");
        const alertsData = await alertsRes.json();
        setAlerts(Array.isArray(alertsData) ? alertsData : []);
      } catch (err) {
        console.error("Alerts fetch error:", err);
        setAlerts([]);
      }

      try {
        const cyberRes = await fetch("http://127.0.0.1:8000/api/cyber-alerts");
        const cyberData = await cyberRes.json();
        setCyberAlerts(Array.isArray(cyberData) ? cyberData : []);
      } catch (err) {
        console.error("Cyber alerts fetch error:", err);
        setCyberAlerts([]);
      }

      try {
        const corrRes = await fetch("http://127.0.0.1:8000/api/correlations");
        const corrData = await corrRes.json();
        setCorrelations(Array.isArray(corrData) ? corrData : []);
      } catch (err) {
        console.error("Correlations fetch error:", err);
        setCorrelations([]);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const filteredShips = useMemo(() => {
    return filter === "all" ? ships : ships.filter((s) => s.type === filter);
  }, [ships, filter]);

  const maxReplayStep = useMemo(() => {
    let max = 0;
    ships.forEach((ship) => {
      if (Array.isArray(ship.history) && ship.history.length - 1 > max) {
        max = ship.history.length - 1;
      }
    });
    return max;
  }, [ships]);

  useEffect(() => {
    if (!isPlaying || maxReplayStep <= 0) return;

    const timer = setInterval(() => {
      setReplayStep((prev) => (prev >= maxReplayStep ? 0 : prev + 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [isPlaying, maxReplayStep]);

  const replayShips = useMemo(() => {
    return filteredShips.map((ship) => {
      if (!Array.isArray(ship.history) || ship.history.length === 0) {
        return ship;
      }

      const safeIndex = Math.min(replayStep, ship.history.length - 1);
      const [lat, lon] = ship.history[safeIndex];

      return {
        ...ship,
        lat,
        lon,
        replayHistory: ship.history.slice(0, safeIndex + 1),
      };
    });
  }, [filteredShips, replayStep]);

  const highestRiskShip = useMemo(() => {
    if (!replayShips.length) return null;
    return [...replayShips].sort(
      (a, b) => (b.threat_score || 0) - (a.threat_score || 0)
    )[0];
  }, [replayShips]);

  const totalThreatScore = useMemo(() => {
    const shipScore = ships.reduce((sum, ship) => sum + (ship.threat_score || 0), 0);
    const cyberScore = cyberAlerts.reduce((sum, alert) => {
      if (alert.severity === "high") return sum + 3;
      if (alert.severity === "medium") return sum + 2;
      return sum + 1;
    }, 0);
    const correlationScore = correlations.length * 4;
    return shipScore + cyberScore + correlationScore;
  }, [ships, cyberAlerts, correlations]);

  const overallThreatLevel = useMemo(() => {
    if (totalThreatScore >= 20) return "HIGH";
    if (totalThreatScore >= 10) return "MEDIUM";
    return "LOW";
  }, [totalThreatScore]);

  const nationalThreatIndex = useMemo(() => {
    return Math.min(100, totalThreatScore * 3);
  }, [totalThreatScore]);

  const timelineEvents = useMemo(() => {
    const events = [];

    ships.forEach((ship) => {
      events.push({
        type: "ship",
        priority: ship.threat_score || 0,
        text: `${ship.name} (${ship.type}) - ${ship.status} - Threat ${ship.threat_level}`,
      });
    });

    cyberAlerts.forEach((alert) => {
      events.push({
        type: "cyber",
        priority: alert.heat || 0,
        text: `${alert.location} - ${alert.category} - ${alert.title}`,
      });
    });

    correlations.forEach((corr) => {
      events.push({
        type: "correlation",
        priority: corr.priority || 10,
        text: corr.message,
      });
    });

    return events.sort((a, b) => b.priority - a.priority);
  }, [ships, cyberAlerts, correlations]);

  const indexBarColor =
    nationalThreatIndex >= 70
      ? "#cc0000"
      : nationalThreatIndex >= 40
      ? "#cc7a00"
      : "#2d862d";

  const renderBasemap = () => {
    // Current mode uses your active basemaps.
    if (historicalMode === "current") {
      return basemap === "osm" ? (

const renderBasemap = () => {
  if (historicalMode === "current") {
    if (basemap === "osm") {
      return (
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />
      );
    }

    if (basemap === "esri") {
      return (
        <TileLayer
          url="https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution="Source: Esri"
        />
      );
    }

    if (basemap === "sentinel") {
      return (
        <TileLayer

    // Advanced historical mode:
    // Keep Esri World Imagery on-map, while the selected Wayback version is managed as analyst context.
    // This gives you the UI and workflow now without guessing a dated WMTS tile endpoint.
    return (
      <TileLayer
        url="https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        attribution="Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community"
      />
    );
  };

  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
      <h1>Fiji God’s Eye</h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(260px, 1fr))",
          gap: "14px",
          marginBottom: "20px",
        }}
      >
        <div
          style={{
            backgroundColor:
              overallThreatLevel === "HIGH"
                ? "#990000"
                : overallThreatLevel === "MEDIUM"
                ? "#996300"
                : "#1f5c1f",
            color: "white",
            border:
              overallThreatLevel === "HIGH"
                ? "2px solid #ff4d4d"
                : overallThreatLevel === "MEDIUM"
                ? "2px solid #ffcc66"
                : "2px solid #66cc66",
            padding: "16px",
            borderRadius: "10px",
          }}
        >
          <h2 style={{ marginTop: 0 }}>Threat Radar</h2>
          <p style={{ fontSize: "22px", fontWeight: "bold", margin: "8px 0" }}>
            {overallThreatLevel}
          </p>
          <p style={{ margin: 0 }}>Total Threat Score: {totalThreatScore}</p>
          <p style={{ margin: "8px 0 0 0" }}>
            Ships: {ships.length} | Cyber Alerts: {cyberAlerts.length} | Correlations:{" "}
            {correlations.length}
          </p>
        </div>

        <div
          style={{
            border: "2px solid #cc0000",
            borderRadius: "10px",
            padding: "16px",
            backgroundColor: "#fff5f5",
          }}
        >
          <h2 style={{ marginTop: 0, color: "#990000" }}>Most Dangerous Ship</h2>
          {highestRiskShip ? (
            <>
              <p style={{ fontSize: "18px", fontWeight: "bold", margin: "8px 0" }}>
                {highestRiskShip.name}
              </p>
              <p style={{ margin: "4px 0" }}>Type: {highestRiskShip.type}</p>
              <p style={{ margin: "4px 0" }}>Status: {highestRiskShip.status}</p>
              <p style={{ margin: "4px 0" }}>
                Threat: {highestRiskShip.threat_level} ({highestRiskShip.threat_score})
              </p>
              <p style={{ margin: "4px 0" }}>ETA: {highestRiskShip.eta_hours} hrs</p>
              <p style={{ margin: "4px 0" }}>Source: {highestRiskShip.source}</p>

              {Array.isArray(highestRiskShip.threat_labels) &&
                highestRiskShip.threat_labels.length > 0 && (
                  <div style={{ marginTop: "8px" }}>
                    {highestRiskShip.threat_labels.map((label, i) => (
                      <span
                        key={`danger-label-${i}`}
                        style={{
                          ...getLabelStyle(label),
                          padding: "4px 8px",
                          borderRadius: "6px",
                          marginRight: "6px",
                          marginBottom: "6px",
                          fontSize: "12px",
                          display: "inline-block",
                        }}
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                )}

              <label style={{ display: "block", marginTop: "10px" }}>
                <input
                  type="checkbox"
                  checked={autoFocusDanger}
                  onChange={(e) => setAutoFocusDanger(e.target.checked)}
                />{" "}
                Auto-focus on danger ship
              </label>
            </>
          ) : (
            <p>No vessel data available.</p>
          )}
        </div>

        <div
          style={{
            border: "1px solid #ccc",
            borderRadius: "10px",
            padding: "16px",
            backgroundColor: "#f8f8f8",
          }}
        >
          <h2 style={{ marginTop: 0 }}>National Threat Index</h2>
          <p style={{ fontSize: "22px", fontWeight: "bold", margin: "8px 0" }}>
            {nationalThreatIndex}/100
          </p>
          <div
            style={{
              height: "18px",
              backgroundColor: "#ddd",
              borderRadius: "999px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${nationalThreatIndex}%`,
                height: "100%",
                backgroundColor: indexBarColor,
              }}
            />
          </div>
          <p style={{ marginTop: "10px" }}>
            Fiji-wide indicator based on vessel risk, cyber incidents, and correlations.
          </p>
        </div>
      </div>

      <h2>Timeline Replay</h2>
      <div
        style={{
          border: "1px solid #ccc",
          borderRadius: "8px",
          padding: "12px",
          marginBottom: "12px",
          backgroundColor: "#f8f8f8",
        }}
      >
        <label htmlFor="replay-slider" style={{ display: "block", marginBottom: "8px" }}>
          Replay Step: {replayStep} / {maxReplayStep}
        </label>
        <input
          id="replay-slider"
          type="range"
          min="0"
          max={maxReplayStep}
          value={replayStep}
          onChange={(e) => setReplayStep(Number(e.target.value))}
          style={{ width: "100%", marginBottom: "12px" }}
        />

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button onClick={() => setIsPlaying((prev) => !prev)}>
            {isPlaying ? "Pause Replay" : "Play Replay"}
          </button>
          <button onClick={() => setReplayStep((prev) => Math.max(0, prev - 1))}>
            Step Back
          </button>
          <button
            onClick={() => setReplayStep((prev) => Math.min(maxReplayStep, prev + 1))}
          >
            Step Forward
          </button>
          <button
            onClick={() => {
              setReplayStep(0);
              setIsPlaying(false);
            }}
          >
            Reset
          </button>
        </div>
      </div>

      <div
        style={{
          border: "1px solid #ccc",
          borderRadius: "8px",
          padding: "12px",
          marginBottom: "20px",
          backgroundColor: "#f8f8f8",
          maxHeight: "220px",
          overflowY: "auto",
        }}
      >
        {timelineEvents.length === 0 ? (
          <p>No timeline events available.</p>
        ) : (
          timelineEvents.map((event, i) => (
            <div
              key={`timeline-${i}`}
              style={{
                padding: "8px 0",
                borderBottom: "1px solid #ddd",
              }}
            >
              <strong>{event.type.toUpperCase()}</strong>
              <div>{event.text}</div>
              <small>Priority: {event.priority}</small>
            </div>
          ))
        )}
      </div>

      <h2>Alerts</h2>
      {(Array.isArray(alerts) ? alerts : []).map((alert, i) => (
        <div
          key={`alert-${i}`}
          style={{
            ...getSeverityStyle(alert.severity),
            padding: 10,
            marginBottom: 10,
            borderRadius: 8,
          }}
        >
          <strong>{alert.title}</strong>
          <p>{alert.message}</p>
          <small>
            Severity: {alert.severity} | Type: {alert.type} | Risk score:{" "}
            {alert.risk_score}
          </small>
        </div>
      ))}

      <h2>Cyber Alerts</h2>
      {(Array.isArray(cyberAlerts) ? cyberAlerts : []).map((alert, i) => (
        <div
          key={`cyber-card-${i}`}
          style={{
            ...getSeverityStyle(alert.severity),
            padding: 10,
            marginBottom: 10,
            borderRadius: 8,
          }}
        >
          <strong>{alert.title}</strong>
          <p>{alert.message}</p>
          <small>
            Severity: {alert.severity} | Category: {alert.category} | Location:{" "}
            {alert.location}
          </small>
        </div>
      ))}

      <h2>Correlated Threats</h2>
      {(Array.isArray(correlations) ? correlations : []).map((c, i) => (
        <div
          key={`corr-${i}`}
          style={{
            backgroundColor: "#ff4d4d",
            color: "white",
            padding: 10,
            marginBottom: 10,
            borderRadius: 8,
          }}
        >
          <strong>{c.title}</strong>
          <p>{c.message}</p>
          {c.priority !== undefined && <small>Priority: {c.priority}</small>}
        </div>
      ))}

      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "20px" }}>
        <div>
          <label style={{ marginRight: "10px", fontWeight: "bold" }}>Ships:</label>
          <select onChange={(e) => setFilter(e.target.value)} value={filter}>
            <option value="all">All ships</option>
            <option value="cargo">Cargo</option>
            <option value="tanker">Tanker</option>
            <option value="fishing">Fishing</option>
          </select>
        </div>

        <div>
          <label style={{ marginRight: "10px", fontWeight: "bold" }}>Basemap:</label>
          <select value={basemap} onChange={(e) => setBasemap(e.target.value)}>
            <option value="osm">OpenStreetMap</option>
            <option value="esri">Esri Satellite</option>
            <option value="sentinel">Sentinel-2 (Latest)</option>
          </select>
            <option value="osm">OpenStreetMap</option>
            <option value="esri">Esri Satellite</option>
          </select>
        </div>

        <div>
          <label style={{ marginRight: "10px", fontWeight: "bold" }}>Imagery Mode:</label>
          <select value={historicalMode} onChange={(e) => setHistoricalMode(e.target.value)}>
            <option value="current">Current imagery</option>
            <option value="wayback">Historical imagery mode</option>
          </select>
        </div>

        {historicalMode === "wayback" && (
          <>
            <div>
              <label style={{ marginRight: "10px", fontWeight: "bold" }}>Wayback version:</label>
              <select value={waybackVersion} onChange={(e) => setWaybackVersion(e.target.value)}>
                {waybackOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <a
                href={WAYBACK_APP_URL}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: "inline-block",
                  padding: "6px 10px",
                  border: "1px solid #ccc",
                  borderRadius: "6px",
                  textDecoration: "none",
                  color: "black",
                  background: "#f8f8f8",
                }}
              >
                Open Wayback App
              </a>
            </div>
          </>
        )}
      </div>

      {historicalMode === "wayback" && (
        <div
          style={{
            border: "1px solid #ccc",
            borderRadius: "8px",
            padding: "12px",
            marginBottom: "20px",
            backgroundColor: "#fffdf2",
          }}
        >
          <strong>Historical Imagery Mode:</strong>
          <p style={{ marginBottom: 0 }}>
            You’re in analyst mode for <strong>{waybackVersion}</strong>. Use the Wayback app to
            inspect and verify archived imagery for this period, then we can wire exact dated layers
            into this selector next.
          </p>
        </div>
      )}

      <MapContainer
        center={[-17.8, 178]}
        zoom={6}
        style={{ height: "520px", marginTop: "20px" }}
      >
        {autoFocusDanger && highestRiskShip && <FocusHighestRisk ship={highestRiskShip} />}

        {renderBasemap()}

        <Rectangle bounds={WATCH_ZONE} pathOptions={{ color: "red" }} />

        {(Array.isArray(cyberAlerts) ? cyberAlerts : []).map((alert, i) => {
          const style = getCyberCircleStyle(alert);
          return (
            <Circle
              key={`cyber-circle-${i}`}
              center={[alert.lat, alert.lon]}
              radius={style.radius}
              pathOptions={{
                color: style.color,
                fillColor: style.fillColor,
                fillOpacity: style.fillOpacity,
              }}
            >
              <Popup>
                <strong>{alert.title}</strong>
                <br />
                Heat: {alert.heat}
                <br />
                Cyber hotspot around {alert.location}
              </Popup>
            </Circle>
          );
        })}

        {replayShips.map((ship, index) => {
          const isDanger = highestRiskShip && ship.name === highestRiskShip.name;

          return (
            <div key={`ship-${index}`}>
              <Marker
                position={[ship.lat, ship.lon]}
                icon={
                  isDanger
                    ? dangerIcon
                    : ship.source === "aisstream"
                    ? liveIcon
                    : isInsideZone(ship)
                    ? redIcon
                    : blueIcon
                }
              >
                <Popup>
                  <strong>{ship.name}</strong>
                  <br />
                  Type: {ship.type}
                  <br />
                  Status: {ship.status}
                  <br />
                  Threat: {ship.threat_level} ({ship.threat_score})
                  <br />
                  ETA: {ship.eta_hours} hrs
                  <br />
                  Source: {ship.source}

                  {Array.isArray(ship.threat_labels) && ship.threat_labels.length > 0 && (
                    <>
                      <br />
                      <div style={{ marginTop: "6px" }}>
                        {ship.threat_labels.map((label, i) => (
                          <span
                            key={i}
                            style={{
                              ...getLabelStyle(label),
                              padding: "4px 8px",
                              borderRadius: "6px",
                              marginRight: "6px",
                              marginBottom: "6px",
                              fontSize: "12px",
                              display: "inline-block",
                            }}
                          >
                            {label}
                          </span>
                        ))}
                      </div>
                    </>
                  )}

                  {isDanger && (
                    <>
                      <br />
                      <span style={{ color: "#990000", fontWeight: "bold" }}>
                        ⚠️ Highest-Risk Vessel
                      </span>
                    </>
                  )}
                </Popup>
              </Marker>

              {Array.isArray(ship.routeSegments) &&
                ship.routeSegments.map((segment, i) => (
                  <Polyline
                    key={`route-${index}-${i}`}
                    positions={segment}
                    pathOptions={{
                      color: ship.type === "tanker" ? "red" : "blue",
                      weight: isDanger ? 5 : 3,
                    }}
                  />
                ))}

              {Array.isArray(ship.replayHistory) && ship.replayHistory.length > 1 && (
                <Polyline
                  positions={ship.replayHistory}
                  pathOptions={{
                    color: isDanger ? "#990000" : "orange",
                    dashArray: "6,6",
                    weight: isDanger ? 6 : 4,
                  }}
                />
              )}
            </div>
          );
        })}

        {(Array.isArray(cyberAlerts) ? cyberAlerts : []).map((alert, i) => (
          <Marker
            key={`cyber-marker-${i}`}
            position={[alert.lat, alert.lon]}
            icon={redIcon}
          >
            <Popup>
              <strong>{alert.title}</strong>
              <br />
              Category: {alert.category}
              <br />
              Severity: {alert.severity}
              <br />
              Heat: {alert.heat}
              <br />
              Location: {alert.location}
              <br />
              {alert.message}
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      <h2 style={{ marginTop: "20px" }}>Tracked Ships</h2>
      {replayShips.map((ship, i) => {
        const isDanger = highestRiskShip && ship.name === highestRiskShip.name;

        return (
          <div
            key={`ship-card-${i}`}
            style={{
              border: isDanger ? "2px solid #cc0000" : "1px solid #ccc",
              backgroundColor: isDanger ? "#fff5f5" : "white",
              padding: "12px",
              marginBottom: "10px",
              borderRadius: "8px",
            }}
          >
            <h3>{ship.name}</h3>
            <p>Type: {ship.type}</p>
            <p>Status: {ship.status}</p>
            <p>Threat: {ship.threat_level}</p>
            <p>ETA: {ship.eta_hours} hrs</p>
            <p>Source: {ship.source}</p>
            <p>{isInsideZone(ship) ? "Inside Watch Zone" : "Outside Watch Zone"}</p>

            {Array.isArray(ship.threat_labels) && ship.threat_labels.length > 0 && (
              <div style={{ marginTop: "6px" }}>
                {ship.threat_labels.map((label, idx) => (
                  <span
                    key={`card-label-${idx}`}
                    style={{
                      ...getLabelStyle(label),
                      padding: "4px 8px",
                      borderRadius: "6px",
                      marginRight: "6px",
                      marginBottom: "6px",
                      fontSize: "12px",
                      display: "inline-block",
                    }}
                  >
                    {label}
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default App;
