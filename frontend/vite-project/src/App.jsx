import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Rectangle,
  Polyline,
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
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    const fetchData = () => {
      fetch("http://127.0.0.1:8000/api/live-ships")
        .then((res) => res.json())
        .then((data) => {
          setShips(Array.isArray(data) ? data : []);
        })
        .catch((err) => {
          console.error("Ships fetch error:", err);
          setShips([]);
        });

      fetch("http://127.0.0.1:8000/api/alerts")
        .then((res) => res.json())
        .then((data) => {
          setAlerts(Array.isArray(data) ? data : []);
        })
        .catch((err) => {
          console.error("Alerts fetch error:", err);
          setAlerts([]);
        });
    };

    fetchData();
    const interval = setInterval(fetchData, 3000);

    return () => clearInterval(interval);
  }, []);

  const filteredShips =
    filter === "all"
      ? ships
      : ships.filter((ship) => ship.type === filter);

  const watchZoneBounds = [
    [-18.5, 177.5],
    [-17.5, 178.5],
  ];

  const isInsideZone = (ship) => {
    return (
      ship.lat >= -18.5 &&
      ship.lat <= -17.5 &&
      ship.lon >= 177.5 &&
      ship.lon <= 178.5
    );
  };

  const getSeverityStyle = (severity) => {
    if (severity === "high") {
      return {
        background: "#ffe5e5",
        border: "1px solid #cc0000",
        color: "#990000",
      };
    }
    if (severity === "medium") {
      return {
        background: "#fff4e5",
        border: "1px solid #cc7a00",
        color: "#995200",
      };
    }
    return {
      background: "#eaf7ea",
      border: "1px solid #2d862d",
      color: "#1f5c1f",
    };
  };

  const totalShips = ships.length;
  const shipsInZone = ships.filter((ship) => isInsideZone(ship)).length;
  const tankerCount = ships.filter((ship) => ship.type === "tanker").length;
  const cargoCount = ships.filter((ship) => ship.type === "cargo").length;
  const fishingCount = ships.filter((ship) => ship.type === "fishing").length;

  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
      <h1>Fiji God’s Eye</h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: "10px",
          marginBottom: "20px",
        }}
      >
        <div style={{ padding: "10px", border: "1px solid #ccc", borderRadius: "8px" }}>
          <strong>Total Ships</strong>
          <p>{totalShips}</p>
        </div>
        <div style={{ padding: "10px", border: "1px solid #ccc", borderRadius: "8px" }}>
          <strong>Ships in Zone</strong>
          <p>{shipsInZone}</p>
        </div>
        <div style={{ padding: "10px", border: "1px solid #ccc", borderRadius: "8px" }}>
          <strong>Tankers</strong>
          <p>{tankerCount}</p>
        </div>
        <div style={{ padding: "10px", border: "1px solid #ccc", borderRadius: "8px" }}>
          <strong>Cargo</strong>
          <p>{cargoCount}</p>
        </div>
        <div style={{ padding: "10px", border: "1px solid #ccc", borderRadius: "8px" }}>
          <strong>Fishing</strong>
          <p>{fishingCount}</p>
        </div>
      </div>

      <h2>Alerts</h2>
      <div style={{ marginBottom: "20px" }}>
        {alerts.length === 0 ? (
          <p>No alerts detected.</p>
        ) : (
          alerts.map((alert, index) => (
            <div
              key={index}
              style={{
                ...getSeverityStyle(alert.severity),
                padding: "12px",
                marginBottom: "10px",
                borderRadius: "8px",
              }}
            >
              <strong>{alert.title}</strong>
              <p style={{ margin: "6px 0 0 0" }}>{alert.message}</p>
              <small>
                Severity: {alert.severity} | Type: {alert.type} | Risk score:{" "}
                {alert.risk_score}
              </small>
            </div>
          ))
        )}
      </div>

      <select
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        style={{ marginBottom: "15px", padding: "6px" }}
      >
        <option value="all">All</option>
        <option value="cargo">Cargo</option>
        <option value="fishing">Fishing</option>
        <option value="tanker">Tanker</option>
      </select>

      <div style={{ height: "600px", marginBottom: "20px" }}>
        <MapContainer
          center={[-20, 180]}
          zoom={3}
          style={{ height: "100%", width: "100%" }}
          worldCopyJump={true}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

          <Rectangle
            bounds={watchZoneBounds}
            pathOptions={{ color: "red", weight: 2 }}
          >
            <Popup>Monitored Fiji Watch Zone</Popup>
          </Rectangle>

          {filteredShips.map((ship, index) => {
            const insideZone = isInsideZone(ship);

            return (
              <div key={index}>
                <Marker
                  position={[ship.lat, ship.lon]}
                  icon={insideZone ? redIcon : blueIcon}
                >
                  <Popup>
                    <strong>{ship.name}</strong>
                    <br />
                    Type: {ship.type}
                    <br />
                    Status: {ship.status}
                    <br />
                    Lat: {ship.lat}
                    <br />
                    Lon: {ship.lon}
                    <br />
                    {insideZone && (
                      <span style={{ color: "red" }}>⚠ Inside Watch Zone</span>
                    )}
                  </Popup>
                </Marker>

                {ship.routeSegments &&
                  Array.isArray(ship.routeSegments) &&
                  ship.routeSegments.map((segment, segIndex) => (
                    <Polyline
                      key={`route-${index}-${segIndex}`}
                      positions={segment}
                      pathOptions={{
                        color: ship.type === "tanker" ? "red" : "blue",
                        weight: 3,
                      }}
                    />
                  ))}

                {ship.history &&
                  Array.isArray(ship.history) &&
                  ship.history.length > 1 && (
                    <Polyline
                      positions={ship.history}
                      pathOptions={{
                        color: "orange",
                        weight: 4,
                        dashArray: "6, 6",
                      }}
                    />
                  )}
              </div>
            );
          })}
        </MapContainer>
      </div>

      <h2>Tracked Ships</h2>
      {filteredShips.map((ship, index) => (
        <div
          key={index}
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
          <p>Lat: {ship.lat}</p>
          <p>Lon: {ship.lon}</p>
          <p>{isInsideZone(ship) ? "Inside Watch Zone" : "Outside Watch Zone"}</p>
        </div>
      ))}
    </div>
  );
}

export default App;
