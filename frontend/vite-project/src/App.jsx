import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

function App() {
  const [ships, setShips] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/live-ships")
      .then((res) => res.json())
      .then((data) => setShips(data))
      .catch((err) => console.error(err));

    fetch("http://127.0.0.1:8000/api/alerts")
      .then((res) => res.json())
      .then((data) => setAlerts(data))
      .catch((err) => console.error(err));
  }, []);

  const filteredShips =
    filter === "all"
      ? ships
      : ships.filter((ship) => ship.type === filter);

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

  return (
    <div style={{ padding: "20px" }}>
      <h1>Fiji God’s Eye</h1>

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
              <small>Severity: {alert.severity}</small>
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

      <div style={{ height: "500px", marginBottom: "20px" }}>
        <MapContainer
          center={[-17.8, 178.1]}
          zoom={7}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

          {filteredShips.map((ship, index) => (
            <Marker key={index} position={[ship.lat, ship.lon]}>
              <Popup>
                <strong>{ship.name}</strong>
                <br />
                Type: {ship.type}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      {filteredShips.map((ship, index) => (
        <div key={index}>
          <h3>{ship.name}</h3>
          <p>Lat: {ship.lat}</p>
          <p>Lon: {ship.lon}</p>
          <p>Type: {ship.type}</p>
        </div>
      ))}
    </div>
  );
}

export default App;
