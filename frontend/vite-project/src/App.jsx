import React, { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

const API_BASE = "http://127.0.0.1:5000";
const FIJI_CENTER = [-18.1248, 178.4501];
const MAX_MAP_SHIPS = 100;

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return "Unknown";
  return Number(value).toFixed(digits);
}

function formatHours(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "Unknown";
  return `${Number(value).toFixed(1)} hrs`;
}

function markerColor(ship) {
  if (ship?.ais_timeout) return "gray";
  if (ship?.suspicious) return "red";
  if ((ship?.confidence_score ?? 0) >= 75) return "green";
  if ((ship?.confidence_score ?? 0) >= 45) return "orange";
  return "yellow";
}

function markerRadius(ship) {
  const score = ship?.confidence_score ?? 0;
  if (score >= 80) return 7;
  if (score >= 60) return 9;
  if (score >= 40) return 11;
  return 13;
}

export default function App() {
  const [ships, setShips] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");
  
const [showSuspiciousOnly, setShowSuspiciousOnly] = useState(true);
  const [searchText, setSearchText] = useState("");
  const [basemap, setBasemap] = useState("osm");

  const fetchAllData = async () => {
    try {
      setLoading(true);
      setError("");

      const res = await fetch(`${API_BASE}/api/vessels?include_stale=true`);
      const data = await res.json();
      const vesselList = safeArray(data?.vessels);

      setShips(vesselList);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error(err);
      setError("Could not load live AIS data from backend.");
      setShips([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const filteredShips = useMemo(() => {
    let data = safeArray(ships);

    if (showSuspiciousOnly) {
      data = data.filter((ship) => ship?.suspicious);
    }

    if (searchText.trim()) {
      const q = searchText.trim().toLowerCase();
      data = data.filter((ship) =>
        [
          ship?.name,
          ship?.mmsi,
          ship?.imo,
          ship?.callsign,
          ship?.destination,
          ship?.ship_type,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(q)
      );
    }

    return data;
  }, [ships, showSuspiciousOnly, searchText]);

  const mapShips = useMemo(() => filteredShips.slice(0, MAX_MAP_SHIPS), [filteredShips]);

  const currentTile = useMemo(() => {
    if (basemap === "esri") {
      return {
        url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attribution: "Tiles © Esri",
      };
    }

    return {
      url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      attribution: "&copy; OpenStreetMap contributors",
    };
  }, [basemap]);

  return (
    <div
      style={{
        height: "100vh",
        width: "100%",
        display: "grid",
        gridTemplateColumns: "320px 1fr",
        background: "#081225",
        color: "#f8fafc",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <div
        style={{
          padding: "16px",
          borderRight: "1px solid #1e293b",
          background: "#0b1730",
          overflowY: "auto",
        }}
      >
        <h1 style={{ marginTop: 0, marginBottom: 8 }}>Fiji God&apos;s Eye</h1>
        <div style={{ color: "#94a3b8", marginBottom: 18 }}>Live AIS Dashboard</div>

        <button onClick={fetchAllData} style={{ marginBottom: 14 }}>
          Refresh
        </button>

        <div style={{ marginBottom: 14 }}>
          <strong>Total ships:</strong> {ships.length}
          <br />
          <strong>On map:</strong> {mapShips.length}
          <br />
          <strong>Last updated:</strong> {lastUpdated || "Waiting..."}
        </div>

        <div style={{ marginBottom: 14 }}>
          <label>
            <input
              type="checkbox"
              checked={showSuspiciousOnly}
              onChange={(e) => setShowSuspiciousOnly(e.target.checked)}
              style={{ marginRight: 8 }}
            />
            Suspicious only
          </label>
        </div>

        <div style={{ marginBottom: 14 }}>
          <div style={{ marginBottom: 6 }}>Search</div>
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="name, MMSI, IMO..."
            style={{
              width: "100%",
              padding: "8px",
              background: "#020617",
              color: "white",
              border: "1px solid #334155",
              borderRadius: "6px",
              boxSizing: "border-box",
            }}
          />
        </div>

        <div style={{ marginBottom: 14 }}>
          <div style={{ marginBottom: 6 }}>Basemap</div>
          <select
            value={basemap}
            onChange={(e) => setBasemap(e.target.value)}
            style={{
              width: "100%",
              padding: "8px",
              background: "#020617",
              color: "white",
              border: "1px solid #334155",
              borderRadius: "6px",
            }}
          >
            <option value="osm">OpenStreetMap</option>
            <option value="esri">Esri Satellite</option>
          </select>
        </div>

        {loading && <div style={{ marginBottom: 12 }}>Loading...</div>}

        {error && (
          <div
            style={{
              background: "#7f1d1d",
              color: "white",
              padding: "10px",
              borderRadius: "8px",
              marginBottom: 12,
            }}
          >
            {error}
          </div>
        )}

        {ships.length > MAX_MAP_SHIPS && (
          <div
            style={{
              background: "#78350f",
              color: "#fef3c7",
              padding: "10px",
              borderRadius: "8px",
              marginBottom: 12,
            }}
          >
            Feed is very large. Showing first {MAX_MAP_SHIPS} ships on the map to keep the dashboard stable.
          </div>
        )}

        <div style={{ fontSize: 14, color: "#cbd5e1" }}>
          <div><span style={{ color: "red" }}>●</span> Suspicious</div>
          <div><span style={{ color: "gray" }}>●</span> AIS timeout</div>
          <div><span style={{ color: "green" }}>●</span> High confidence</div>
          <div><span style={{ color: "orange" }}>●</span> Medium confidence</div>
          <div><span style={{ color: "yellow" }}>●</span> Low confidence</div>
        </div>
      </div>

      <div style={{ position: "relative" }}>
        <MapContainer
          center={FIJI_CENTER}
          zoom={5}
          style={{ height: "100%", width: "100%" }}
          worldCopyJump={false}
          preferCanvas={true}
        >
          <TileLayer
            attribution={currentTile.attribution}
            url={currentTile.url}
          />

          {mapShips.map((ship, index) => {
            const lat = Number(ship?.lat);
            const lon = Number(ship?.lon);

            if (Number.isNaN(lat) || Number.isNaN(lon)) return null;

            return (
              <CircleMarker
                key={`${ship?.mmsi || ship?.name || "ship"}-${index}`}
                center={[lat, lon]}
                radius={markerRadius(ship)}
                pathOptions={{
                  color: markerColor(ship),
                  fillColor: markerColor(ship),
                  fillOpacity: 0.75,
                  weight: 2,
                }}
              >
                <Popup>
                  <div style={{ minWidth: 250, color: "#111827" }}>
                    <h3 style={{ marginTop: 0, marginBottom: 8 }}>
                      {ship?.name || "Unknown Vessel"}
                    </h3>

                    <div><strong>MMSI:</strong> {ship?.mmsi || "Unknown"}</div>
                    <div><strong>IMO:</strong> {ship?.imo || "Unknown"}</div>
                    <div><strong>Callsign:</strong> {ship?.callsign || "Unknown"}</div>
                    <div><strong>Type:</strong> {ship?.ship_type || "Unknown"}</div>
                    <div><strong>Status:</strong> {ship?.status || "Unknown"}</div>
                    <div><strong>Destination:</strong> {ship?.destination || "Unknown"}</div>

                    <hr />

                    <div><strong>Speed:</strong> {formatNumber(ship?.speed_knots, 1)} knots</div>
                    <div><strong>Course:</strong> {ship?.course ?? "Unknown"}°</div>
                    <div><strong>Heading:</strong> {ship?.heading ?? "Unknown"}°</div>
                    <div><strong>Distance to Fiji:</strong> {formatNumber(ship?.distance_to_fiji_nm, 1)} NM</div>
                    <div><strong>Hours since seen:</strong> {formatHours(ship?.hours_since_seen)}</div>
                    <div><strong>Confidence:</strong> {ship?.confidence_score ?? 0}%</div>

                    <hr />

                    <div><strong>Suspicious:</strong> {ship?.suspicious ? "Yes" : "No"}</div>
                    <div><strong>AIS timeout:</strong> {ship?.ais_timeout ? "Yes" : "No"}</div>
                    <div><strong>Unknown vessel:</strong> {ship?.unknown_vessel ? "Yes" : "No"}</div>
                    <div><strong>Source:</strong> {ship?.source || "Unknown"}</div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
