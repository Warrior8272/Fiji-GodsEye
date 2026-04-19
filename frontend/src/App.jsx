import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  ImageOverlay,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function SentinelOverlay({ enabled, opacity }) {
  const map = useMap();
  const [bounds, setBounds] = useState(null);
  const [url, setUrl] = useState("");

  useEffect(() => {
    const updateOverlay = () => {
      const b = map.getBounds();
      const sw = b.getSouthWest();
      const ne = b.getNorthEast();

      setBounds([
        [sw.lat, sw.lng],
        [ne.lat, ne.lng],
      ]);

      const overlayUrl =
        `/api/sentinel/tile?minLon=${sw.lng}&minLat=${sw.lat}` +
        `&maxLon=${ne.lng}&maxLat=${ne.lat}&t=${Date.now()}`;

      setUrl(overlayUrl);
    };

    updateOverlay();
    map.on("moveend", updateOverlay);
    map.on("zoomend", updateOverlay);

    return () => {
      map.off("moveend", updateOverlay);
      map.off("zoomend", updateOverlay);
    };
  }, [map]);

  if (!enabled || !bounds || !url) return null;

  return <ImageOverlay url={url} bounds={bounds} opacity={opacity} />;
}

export default function App() {
  const [alerts, setAlerts] = useState([]);
  const [vessels, setVessels] = useState([]);
  const [sentinelEnabled, setSentinelEnabled] = useState(false);
  const [sentinelOpacity, setSentinelOpacity] = useState(0.6);
  const [backendStatus, setBackendStatus] = useState("Checking...");
  const [sentinelStatus, setSentinelStatus] = useState("Checking...");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then(() => setBackendStatus("Backend online"))
      .catch(() => setBackendStatus("Backend offline"));

    fetch("/api/sentinel/health")
      .then((res) => res.json())
      .then((data) => {
        if (data.sentinel_configured) {
          setSentinelStatus("Sentinel configured");
        } else {
          setSentinelStatus("Sentinel not configured");
        }
      })
      .catch(() => setSentinelStatus("Sentinel check failed"));

    fetch("/api/alerts")
      .then((res) => res.json())
      .then((data) => setAlerts(data))
      .catch((err) => console.error("Alerts error:", err));

    fetch("/api/vessels")
      .then((res) => res.json())
      .then((data) => setVessels(data))
      .catch((err) => console.error("Vessels error:", err));
  }, []);

  return (
    <div
      style={{
        height: "100vh",
        width: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          padding: "10px 14px",
          background: "#111827",
          color: "white",
          display: "flex",
          gap: "20px",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <strong>God's Eye - Phase 9</strong>
        <span>{backendStatus}</span>
        <span>{sentinelStatus}</span>

        <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <input
            type="checkbox"
            checked={sentinelEnabled}
            onChange={(e) => setSentinelEnabled(e.target.checked)}
          />
          Sentinel Satellite
        </label>

        {sentinelEnabled && (
          <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            Opacity
            <input
              type="range"
              min="0.1"
              max="1"
              step="0.1"
              value={sentinelOpacity}
              onChange={(e) => setSentinelOpacity(Number(e.target.value))}
            />
            {sentinelOpacity}
          </label>
        )}
      </div>

      <MapContainer
        center={[-17.8, 178.0]}
        zoom={7}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <SentinelOverlay enabled={sentinelEnabled} opacity={sentinelOpacity} />

        {alerts.map((alert) => (
          <Marker key={alert.id} position={[alert.lat, alert.lon]}>
            <Popup>
              <div>
                <strong>{alert.title}</strong>
                <br />
                Type: {alert.type}
                <br />
                Severity: {alert.severity}
                <br />
                Source: {alert.source}
                <br />
                {alert.description}
              </div>
            </Popup>
          </Marker>
        ))}

        {vessels.map((vessel) => (
          <Marker key={vessel.id} position={[vessel.lat, vessel.lon]}>
            <Popup>
              <div>
                <strong>{vessel.name}</strong>
                <br />
                MMSI: {vessel.mmsi}
                <br />
                Speed: {vessel.speed} kn
                <br />
                Heading: {vessel.heading}
                <br />
                Confidence: {vessel.confidence}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
