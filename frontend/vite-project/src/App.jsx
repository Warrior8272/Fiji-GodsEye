import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Rectangle,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

/* ICONS */
const blueIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const redIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

function App() {
  const [ships, setShips] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [cyberAlerts, setCyberAlerts] = useState([]);
  const [correlations, setCorrelations] = useState([]);
  const [filter, setFilter] = useState("all");

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
    if (severity === "high")
      return { backgroundColor: "#ffcccc", border: "1px solid red" };
    if (severity === "medium")
      return { backgroundColor: "#fff3cd", border: "1px solid orange" };
    return { backgroundColor: "#d4edda", border: "1px solid green" };
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const shipsRes = await fetch("http://127.0.0.1:8000/api/live-ships");
        const shipsData = await shipsRes.json();
        setShips(Array.isArray(shipsData) ? shipsData : []);
      } catch {
        setShips([]);
      }

      try {
        const alertsRes = await fetch("http://127.0.0.1:8000/api/alerts");
        const alertsData = await alertsRes.json();
        setAlerts(Array.isArray(alertsData) ? alertsData : []);
      } catch {
        setAlerts([]);
      }

      try {
        const cyberRes = await fetch("http://127.0.0.1:8000/api/cyber-alerts");
        const cyberData = await cyberRes.json();
        setCyberAlerts(Array.isArray(cyberData) ? cyberData : []);
      } catch {
        setCyberAlerts([]);
      }

      try {
        const corrRes = await fetch("http://127.0.0.1:8000/api/correlations");
        const corrData = await corrRes.json();
        setCorrelations(Array.isArray(corrData) ? corrData : []);
      } catch {
        setCorrelations([]);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const filteredShips =
    filter === "all" ? ships : ships.filter((s) => s.type === filter);

  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h1>Fiji God’s Eye</h1>

      {/* ALERTS */}
      <h2>Alerts</h2>
      {alerts.map((a, i) => (
        <div key={i} style={{ ...getSeverityStyle(a.severity), padding: 10 }}>
          <strong>{a.title}</strong>
          <p>{a.message}</p>
        </div>
      ))}

      {/* CYBER ALERTS */}
      <h2>Cyber Alerts</h2>
      {cyberAlerts.map((a, i) => (
        <div key={i} style={{ ...getSeverityStyle(a.severity), padding: 10 }}>
          <strong>{a.title}</strong>
          <p>{a.message}</p>
        </div>
      ))}

      {/* CORRELATIONS */}
      <h2>Correlated Threats</h2>
      {correlations.map((c, i) => (
        <div
          key={i}
          style={{
            backgroundColor: "#ff4d4d",
            color: "white",
            padding: 10,
            marginBottom: 10,
          }}
        >
          <strong>{c.title}</strong>
          <p>{c.message}</p>
        </div>
      ))}

      {/* FILTER */}
      <select onChange={(e) => setFilter(e.target.value)}>
        <option value="all">All</option>
        <option value="cargo">Cargo</option>
        <option value="tanker">Tanker</option>
        <option value="fishing">Fishing</option>
      </select>

      {/* MAP */}
      <MapContainer
        center={[-17.8, 178]}
        zoom={6}
        style={{ height: "500px", marginTop: "20px" }}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Rectangle bounds={WATCH_ZONE} pathOptions={{ color: "red" }} />

        {filteredShips.map((ship, i) => (
          <div key={i}>
            <Marker
              position={[ship.lat, ship.lon]}
              icon={isInsideZone(ship) ? redIcon : blueIcon}
            >
              <Popup>
                <strong>{ship.name}</strong>
                <br />
                {ship.type}
              </Popup>
            </Marker>

            {ship.history && ship.history.length > 1 && (
              <Polyline
                positions={ship.history}
                pathOptions={{ color: "orange", dashArray: "6,6" }}
              />
            )}
          </div>
        ))}

        {cyberAlerts.map((a, i) => (
          <Marker key={i} position={[a.lat, a.lon]} icon={redIcon}>
            <Popup>
              <strong>{a.title}</strong>
              <br />
              {a.message}
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* SHIP LIST */}
      <h2>Tracked Ships</h2>
      {filteredShips.map((s, i) => (
        <div key={i}>
          <h3>{s.name}</h3>
          <p>{s.type}</p>
        </div>
      ))}
    </div>
  );
}

export default App;
