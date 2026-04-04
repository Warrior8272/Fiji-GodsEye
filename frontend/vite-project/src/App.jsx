import { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Rectangle,
  Circle,
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

function App() {
  const [ships, setShips] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [cyberAlerts, setCyberAlerts] = useState([]);
  const [correlations, setCorrelations] = useState([]);
  const [filter, setFilter] = useState("all");
  const [replayStep, setReplayStep] = useState(0);

  const WATCH_ZONE = [
    [-18.5, 177.5],
    [-17.5, 178.5],
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

  const filteredShips =
    filter === "all" ? ships : ships.filter((s) => s.type === filter);

  const highestRiskShip = useMemo(() => {
    if (!ships.length) return null;
    return [...ships].sort(
      (a, b) => (b.threat_score || 0) - (a.threat_score || 0)
    )[0];
  }, [ships]);

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

  const threatRadarStyle = useMemo(() => {
    if (overallThreatLevel === "HIGH") {
      return {
        backgroundColor: "#990000",
        color: "white",
        border: "2px solid #ff4d4d",
      };
    }
    if (overallThreatLevel === "MEDIUM") {
      return {
        backgroundColor: "#996300",
        color: "white",
        border: "2px solid #ffcc66",
      };
    }
    return {
      backgroundColor: "#1f5c1f",
      color: "white",
      border: "2px solid #66cc66",
    };
  }, [overallThreatLevel]);

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

  const maxReplayStep = useMemo(() => {
    let max = 0;
    ships.forEach((ship) => {
      if (Array.isArray(ship.history) && ship.history.length - 1 > max) {
        max = ship.history.length - 1;
      }
    });
    return max;
  }, [ships]);

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

  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
      <h1>Fiji God’s Eye</h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(280px, 1fr))",
          gap: "14px",
          marginBottom: "20px",
        }}
      >
        <div
          style={{
            ...threatRadarStyle,
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
            border: "1px solid #ccc",
            borderRadius: "10px",
            padding: "16px",
            backgroundColor: "#f8f8f8",
          }}
        >
          <h2 style={{ marginTop: 0 }}>Highest-Risk Vessel</h2>
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
            </>
          ) : (
            <p>No vessel data available.</p>
          )}
        </div>
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
        </div>
      ))}

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
          style={{ width: "100%" }}
        />
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

      <select
        onChange={(e) => setFilter(e.target.value)}
        value={filter}
        style={{ marginBottom: "20px" }}
      >
        <option value="all">All</option>
        <option value="cargo">Cargo</option>
        <option value="tanker">Tanker</option>
        <option value="fishing">Fishing</option>
      </select>

      <MapContainer
        center={[-17.8, 178]}
        zoom={6}
        style={{ height: "520px", marginTop: "20px" }}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

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

        {replayShips.map((ship, index) => (
          <div key={`ship-${index}`}>
            <Marker
              position={[ship.lat, ship.lon]}
              icon={isInsideZone(ship) ? redIcon : blueIcon}
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
              </Popup>
            </Marker>

            {Array.isArray(ship.routeSegments) &&
              ship.routeSegments.map((segment, i) => (
                <Polyline
                  key={`route-${index}-${i}`}
                  positions={segment}
                  pathOptions={{
                    color: ship.type === "tanker" ? "red" : "blue",
                    weight: 3,
                  }}
                />
              ))}

            {Array.isArray(ship.replayHistory) && ship.replayHistory.length > 1 && (
              <Polyline
                positions={ship.replayHistory}
                pathOptions={{ color: "orange", dashArray: "6,6", weight: 4 }}
              />
            )}
          </div>
        ))}

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
      {replayShips.map((ship, i) => (
        <div
          key={`ship-card-${i}`}
          style={{
            border: "1px solid #ccc",
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
          <p>{isInsideZone(ship) ? "Inside Watch Zone" : "Outside Watch Zone"}</p>
        </div>
      ))}
    </div>
  );
}

export default App;
