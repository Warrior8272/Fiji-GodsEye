import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const shipIcon = new L.Icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/68/68472.png",
  iconSize: [25, 25],
});

function App() {
  const [news, setNews] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  useEffect(() => {
    const loadData = () => {
      Promise.all([
        fetch("http://127.0.0.1:5000/news").then((res) => res.json()),
        fetch("http://127.0.0.1:5000/alerts").then((res) => res.json()),
      ])
        .then(([newsData, alertsData]) => {
          setNews(newsData);
          setAlerts(alertsData);
          setError("");
          setLastUpdated(new Date().toLocaleTimeString());
        })
        .catch((err) => {
          setError(err.message);
        });
    };

    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const filteredNews = useMemo(() => {
    return news.filter((item) =>
      item.title?.toLowerCase().includes(query.toLowerCase())
    );
  }, [news, query]);

  const highCount = alerts.filter((a) => a.risk === "HIGH").length;
  const mediumCount = alerts.filter((a) => a.risk === "MEDIUM").length;
  const lowCount = alerts.filter((a) => a.risk === "LOW").length;

  const riskColor = (risk) => {
    if (risk === "HIGH") return "#ff4d4f";
    if (risk === "MEDIUM") return "#faad14";
    return "#52c41a";
  };

  const cardStyle = {
    background: "#111827",
    border: "1px solid #1f2937",
    borderRadius: "14px",
    padding: "16px",
    boxShadow: "0 10px 25px rgba(0,0,0,0.25)",
  };

  const alertMarkers = alerts
    .map((a) => {
      const text = a.title.toLowerCase();

      if (text.includes("suva")) {
        return {
          name: "Suva",
          position: [-18.1416, 178.4419],
          risk: a.risk,
          title: a.title,
        };
      }

      if (text.includes("nadi")) {
        return {
          name: "Nadi",
          position: [-17.7765, 177.4358],
          risk: a.risk,
          title: a.title,
        };
      }

      if (text.includes("lautoka")) {
        return {
          name: "Lautoka",
          position: [-17.6169, 177.4505],
          risk: a.risk,
          title: a.title,
        };
      }

      if (text.includes("labasa")) {
        return {
          name: "Labasa",
          position: [-16.4332, 179.3645],
          risk: a.risk,
          title: a.title,
        };
      }

      if (text.includes("fiji")) {
        const locations = [
          [-18.1416, 178.4419],
          [-17.7765, 177.4358],
          [-17.6169, 177.4505],
          [-16.4332, 179.3645],
        ];
        const randomLocation =
          locations[Math.floor(Math.random() * locations.length)];

        return {
          name: "Fiji",
          position: randomLocation,
          risk: a.risk,
          title: a.title,
        };
      }

      return null;
    })
    .filter(Boolean);

  const ships = [
    { name: "Cargo Vessel", position: [-18.2, 178.3], type: "Cargo" },
    { name: "Fishing Vessel", position: [-17.9, 177.8], type: "Fishing" },
    { name: "Unknown Vessel", position: [-18.0, 178.0], type: "Unknown" },
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#030712",
        color: "#f9fafb",
        fontFamily: "Arial, sans-serif",
        padding: "24px",
      }}
    >
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: 0, fontSize: "42px" }}>Fiji Gods Eye v1</h1>
        <p style={{ color: "#9ca3af", marginTop: "8px" }}>
          Fiji-focused OSINT monitoring dashboard
        </p>
        <p style={{ color: "#6b7280", fontSize: "14px" }}>
          Last updated: {lastUpdated || "Loading..."}
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        <div style={cardStyle}>
          <div style={{ color: "#9ca3af", fontSize: "14px" }}>News Items</div>
          <div style={{ fontSize: "30px", fontWeight: "bold", marginTop: "6px" }}>
            {news.length}
          </div>
        </div>

        <div style={cardStyle}>
          <div style={{ color: "#9ca3af", fontSize: "14px" }}>High Alerts</div>
          <div style={{ fontSize: "30px", fontWeight: "bold", marginTop: "6px", color: "#ff4d4f" }}>
            {highCount}
          </div>
        </div>

        <div style={cardStyle}>
          <div style={{ color: "#9ca3af", fontSize: "14px" }}>Medium Alerts</div>
          <div style={{ fontSize: "30px", fontWeight: "bold", marginTop: "6px", color: "#faad14" }}>
            {mediumCount}
          </div>
        </div>

        <div style={cardStyle}>
          <div style={{ color: "#9ca3af", fontSize: "14px" }}>Low Alerts</div>
          <div style={{ fontSize: "30px", fontWeight: "bold", marginTop: "6px", color: "#52c41a" }}>
            {lowCount}
          </div>
        </div>

        <div style={cardStyle}>
          <div style={{ color: "#9ca3af", fontSize: "14px" }}>System Status</div>
          <div
            style={{
              fontSize: "20px",
              fontWeight: "bold",
              marginTop: "10px",
              color: error ? "#ff4d4f" : "#52c41a",
            }}
          >
            {error ? "ERROR" : "ONLINE"}
          </div>
        </div>
      </div>

      <div style={{ ...cardStyle, marginBottom: "24px" }}>
        <input
          type="text"
          placeholder="Filter headlines..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{
            width: "100%",
            padding: "12px 14px",
            borderRadius: "10px",
            border: "1px solid #374151",
            background: "#0b1220",
            color: "#f9fafb",
            outline: "none",
            fontSize: "15px",
            boxSizing: "border-box",
          }}
        />
      </div>

      <div style={{ ...cardStyle, marginBottom: "24px" }}>
        <h2 style={{ marginTop: 0 }}>Fiji Monitoring Map</h2>
        <div
          style={{
            position: "relative",
            height: "420px",
            borderRadius: "12px",
            overflow: "hidden",
          }}
        >
          <MapContainer
            center={[-17.8, 178.1]}
            zoom={7}
            scrollWheelZoom={true}
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {alertMarkers.map((marker, index) => (
              <Marker key={`alert-${index}`} position={marker.position}>
                <Popup>
                  <strong>{marker.name}</strong>
                  <br />
                  <span style={{ color: marker.risk === "HIGH" ? "red" : "orange" }}>
                    {marker.risk}
                  </span>
                  <br />
                  {marker.title}
                </Popup>
              </Marker>
            ))}

            {ships.map((ship, i) => (
              <Marker key={`ship-${i}`} position={ship.position} icon={shipIcon}>
                <Popup>
                  🚢 <strong>{ship.name}</strong>
                  <br />
                  Type: {ship.type}
                </Popup>
              </Marker>
            ))}
          </MapContainer>

          <div
            style={{
              position: "absolute",
              bottom: "20px",
              right: "20px",
              background: "#0b1220",
              padding: "12px 16px",
              borderRadius: "10px",
              border: "1px solid #1f2937",
              fontSize: "13px",
              color: "#f9fafb",
              zIndex: 1000,
            }}
          >
            <div style={{ fontWeight: "bold", marginBottom: "6px" }}>Legend</div>

            <div style={{ display: "flex", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ width: "10px", height: "10px", background: "#ff4d4f", marginRight: "8px" }}></span>
              High Alert
            </div>

            <div style={{ display: "flex", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ width: "10px", height: "10px", background: "#faad14", marginRight: "8px" }}></span>
              Medium Alert
            </div>

            <div style={{ display: "flex", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ width: "10px", height: "10px", background: "#52c41a", marginRight: "8px" }}></span>
              Low Alert
            </div>

            <div style={{ display: "flex", alignItems: "center" }}>
              🚢 Ships
            </div>
          </div>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: "20px",
        }}
      >
        <div style={cardStyle}>
          <h2 style={{ marginTop: 0 }}>News Feed</h2>
          {filteredNews.length === 0 ? (
            <p style={{ color: "#9ca3af" }}>No matching headlines.</p>
          ) : (
            <ul style={{ paddingLeft: "18px", marginBottom: 0 }}>
              {filteredNews.map((item, i) => (
                <li key={i} style={{ marginBottom: "12px" }}>
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "#93c5fd", textDecoration: "none" }}
                  >
                    {item.title}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div style={cardStyle}>
          <h2 style={{ marginTop: 0 }}>Alerts</h2>
          {alerts.length === 0 ? (
            <p style={{ color: "#9ca3af" }}>No alerts detected.</p>
          ) : (
            <div>
              {alerts.map((item, i) => (
                <div
                  key={i}
                  style={{
                    marginBottom: "12px",
                    padding: "12px",
                    borderRadius: "10px",
                    background: "#0b1220",
                    borderLeft: `5px solid ${riskColor(item.risk)}`,
                  }}
                >
                  <div
                    style={{
                      fontSize: "12px",
                      fontWeight: "bold",
                      color: riskColor(item.risk),
                      marginBottom: "6px",
                    }}
                  >
                    {item.risk}
                  </div>
                  <div style={{ fontSize: "14px", lineHeight: 1.4 }}>{item.title}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
