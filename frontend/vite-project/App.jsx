import { useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

function App() {
  const [basemap, setBasemap] = useState("osm");

  // ✅ PUT YOUR SENTINEL INSTANCE HERE
  const SENTINEL_INSTANCE = "PLAKfb35bc95238a4d45bac71029cb2e9ab5";

  const ships = [
    {
      name: "Tanker Pacific",
      lat: -18.1248,
      lon: 178.4501,
      type: "tanker",
      status: "inside zone",
      threat_level: "HIGH",
      threat_score: 10,
      eta_hours: 5
    },
    {
      name: "Cargo Alpha",
      lat: -18.1416,
      lon: 178.4419,
      type: "cargo",
      status: "moving",
      threat_level: "MEDIUM",
      threat_score: 7,
      eta_hours: 12
    }
  ];

  // ✅ BASEMAP SWITCHER (CLEAN)
  const renderBasemap = () => {
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
      url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
      attribution="Tiles &copy; Esri"
    />
  );
}

    if (basemap === "sentinel") {
      return (
        <TileLayer
          url={`https://services.sentinel-hub.com/ogc/wms/${SENTINEL_INSTANCE}?service=WMS&request=GetMap&layers=TRUE_COLOR&styles=&format=image/png&transparent=true&version=1.1.1&width=256&height=256&srs=EPSG:3857&bbox={bbox-epsg-3857}`}
          attribution="Sentinel-2 © ESA"
        />
      );
    }
  };

  return (
    <div style={{ padding: "10px" }}>
      <h1>Fiji God’s Eye</h1>

      {/* ✅ Basemap Selector */}
      <div style={{ marginBottom: "10px" }}>
        <label style={{ marginRight: "10px" }}>
          Basemap:
        </label>
        <select
          value={basemap}
          onChange={(e) => setBasemap(e.target.value)}
        >
          <option value="osm">OpenStreetMap</option>
          <option value="esri">Esri Satellite</option>
          <option value="sentinel">Sentinel-2 (Latest)</option>
        </select>
      </div>

      {/* ✅ Map */}
      <MapContainer
        center={[-18.1248, 178.4501]}
        zoom={7}
        style={{ height: "600px", width: "100%" }}
      >
        {renderBasemap()}

        {/* ✅ Ships */}
        {ships.map((ship, index) => (
          <Marker key={index} position={[ship.lat, ship.lon]}>
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
        ))}
      </MapContainer>
    </div>
  );
}

export default App;
