import { useEffect, useMemo, useRef, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  useMap,
} from "react-leaflet";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import "leaflet/dist/leaflet.css";

const investigationLocations = [
  {
    id: "suva",
    name: "Suva Port",
    lat: -18.1416,
    lon: 178.4419,
    zoom: 11,
    radius: 8000,
  },
  {
    id: "nadi",
    name: "Nadi Coast",
    lat: -17.7765,
    lon: 177.4357,
    zoom: 10,
    radius: 10000,
  },
  {
    id: "labasa",
    name: "Labasa Area",
    lat: -16.4332,
    lon: 179.3645,
    zoom: 10,
    radius: 10000,
  },
];

function FocusLocation({ location }) {
  const map = useMap();

  useEffect(() => {
    if (location) {
      map.setView([location.lat, location.lon], location.zoom);
    }
  }, [location, map]);

  return null;
}

function App() {
  const [ships, setShips] = useState([]);
  const [cyberAlerts, setCyberAlerts] = useState([]);
  const [basemap, setBasemap] = useState("esri");
  const [correlations, setCorrelations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(
    investigationLocations[0]
  );
  const [caseTitle, setCaseTitle] = useState("Port Monitoring Case");
  const [caseNotes, setCaseNotes] = useState(
    "Monitor vessels and unusual activity around this area."
  );
  const [investigationStatus, setInvestigationStatus] = useState("Open");
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [cyberFilter, setCyberFilter] = useState("all");

  const reportRef = useRef(null);
  const lastAlertKeyRef = useRef("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const shipRes = await fetch("http://127.0.0.1:8000/api/live-ships");
        const shipData = await shipRes.json();
        setShips(Array.isArray(shipData) ? shipData : []);
      } catch {
        setShips([]);
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
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const renderBasemap = () => {
    if (basemap === "osm") {
      return (
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />
      );
    }

    return (
      <TileLayer
        url="https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        attribution="Source: Esri"
      />
    );
  };

  const getStatusStyle = (status) => {
    if (status === "Escalated") {
      return { backgroundColor: "#ff4d4f", color: "white" };
    }
    if (status === "Monitoring") {
      return { backgroundColor: "#faad14", color: "black" };
    }
    if (status === "Closed") {
      return { backgroundColor: "#52c41a", color: "white" };
    }
    return { backgroundColor: "#1677ff", color: "white" };
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

  const getVerificationBadgeStyle = (verification) => {
    if (verification === "verified") {
      return { backgroundColor: "#52c41a", color: "white" };
    }
    if (verification === "osint") {
      return { backgroundColor: "#fa8c16", color: "white" };
    }
    return { backgroundColor: "#d9d9d9", color: "black" };
  };

  const distanceKm = (lat1, lon1, lat2, lon2) => {
    const toRad = (deg) => (deg * Math.PI) / 180;
    const R = 6371;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);

    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) *
        Math.cos(toRad(lat2)) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  };

  const shipsInZone = useMemo(() => {
    return ships.filter((ship) => {
      const d = distanceKm(
        selectedLocation.lat,
        selectedLocation.lon,
        ship.lat,
        ship.lon
      );
      return d <= selectedLocation.radius / 1000;
    });
  }, [ships, selectedLocation]);

  const highRiskShipsInZone = useMemo(() => {
    return shipsInZone.filter(
      (ship) => ship.threat_level === "HIGH" || (ship.threat_score || 0) >= 6
    );
  }, [shipsInZone]);

  const cyberAlertsInZone = useMemo(() => {
    return cyberAlerts.filter((alert) => {
      const d = distanceKm(
        selectedLocation.lat,
        selectedLocation.lon,
        alert.lat,
        alert.lon
      );
      return d <= selectedLocation.radius / 1000 + 15;
    });
  }, [cyberAlerts, selectedLocation]);

  const openPhishAlertsInZone = useMemo(() => {
    return cyberAlertsInZone.filter((alert) => alert.source === "openphish");
  }, [cyberAlertsInZone]);

  const visibleCyberAlerts = useMemo(() => {
    if (cyberFilter === "all") return cyberAlertsInZone;
    if (cyberFilter === "openphish") {
      return cyberAlertsInZone.filter((alert) => alert.source === "openphish");
    }
    if (cyberFilter === "simulation") {
      return cyberAlertsInZone.filter((alert) => alert.source === "simulation");
    }
    return cyberAlertsInZone;
  }, [cyberAlertsInZone, cyberFilter]);

  const overallZoneRisk = useMemo(() => {
    const shipRisk = shipsInZone.reduce(
      (sum, ship) => sum + (ship.threat_score || 0),
      0
    );
    const cyberRisk = cyberAlertsInZone.reduce((sum, alert) => {
      if (alert.severity === "high") return sum + 4;
      if (alert.severity === "medium") return sum + 2;
      return sum + 1;
    }, 0);

    const total = shipRisk + cyberRisk;

    if (total >= 15) return "HIGH";
    if (total >= 7) return "MEDIUM";
    return "LOW";
  }, [shipsInZone, cyberAlertsInZone]);

  const generatedSummary = useMemo(() => {
    return `Investigation target ${selectedLocation.name} currently has ${shipsInZone.length} vessel(s) in area, ${highRiskShipsInZone.length} high-risk vessel(s), ${cyberAlertsInZone.length} cyber alert(s) nearby, and ${openPhishAlertsInZone.length} OpenPhish indicator(s). Current zone risk is assessed as ${overallZoneRisk}.`;
  }, [
    selectedLocation,
    shipsInZone.length,
    highRiskShipsInZone.length,
    cyberAlertsInZone.length,
    openPhishAlertsInZone.length,
    overallZoneRisk,
  ]);

  const exportPdfReport = async () => {
    if (!reportRef.current) return;

    const canvas = await html2canvas(reportRef.current, {
      scale: 2,
      useCORS: true,
      backgroundColor: "#ffffff",
    });

    const imgData = canvas.toDataURL("image/png");
    const pdf = new jsPDF("p", "mm", "a4");
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();

    const imgWidth = pageWidth - 20;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    let heightLeft = imgHeight;
    let position = 10;

    pdf.addImage(imgData, "PNG", 10, position, imgWidth, imgHeight);
    heightLeft -= pageHeight - 20;

    while (heightLeft > 0) {
      pdf.addPage();
      position = 10 - (imgHeight - heightLeft);
      pdf.addImage(imgData, "PNG", 10, position, imgWidth, imgHeight);
      heightLeft -= pageHeight - 20;
    }

    pdf.save(`${caseTitle.replace(/\s+/g, "_")}_report.pdf`);
  };

  const requestAlertsPermission = async () => {
    if (!("Notification" in window)) {
      alert("This browser does not support desktop notifications.");
      return;
    }

    const permission = await Notification.requestPermission();
    setNotificationsEnabled(permission === "granted");
  };

  const playAlertSound = async () => {
    try {
      const audio = new Audio(
        "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
      );
      await audio.play();
    } catch {
      // ignore autoplay issues
    }
  };

  useEffect(() => {
    if (!notificationsEnabled) return;

    const key = `${overallZoneRisk}-${highRiskShipsInZone.length}-${cyberAlertsInZone.length}-${openPhishAlertsInZone.length}`;
    if (lastAlertKeyRef.current === key) return;

    const shouldTrigger =
      overallZoneRisk === "HIGH" ||
      highRiskShipsInZone.length > 0 ||
      cyberAlertsInZone.some((a) => a.severity === "high") ||
      openPhishAlertsInZone.length > 0;

    if (!shouldTrigger) return;

    lastAlertKeyRef.current = key;

    if ("Notification" in window && Notification.permission === "granted") {
      new Notification("Fiji God’s Eye Alert", {
        body: `${selectedLocation.name}: ${overallZoneRisk} risk | ${highRiskShipsInZone.length} high-risk ship(s) | ${cyberAlertsInZone.length} cyber alert(s) | ${openPhishAlertsInZone.length} OpenPhish indicator(s)`,
      });
    }

    playAlertSound();
  }, [
    notificationsEnabled,
    overallZoneRisk,
    highRiskShipsInZone.length,
    cyberAlertsInZone,
    openPhishAlertsInZone.length,
    selectedLocation.name,
  ]);

  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h1>Fiji God’s Eye</h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "15px",
          marginBottom: "20px",
        }}
      >
        <div style={{ border: "1px solid #ccc", padding: "10px", borderRadius: "8px" }}>
          <h2>Investigation Setup</h2>

          <label>Case Title</label>
          <input
            value={caseTitle}
            onChange={(e) => setCaseTitle(e.target.value)}
            style={{ width: "100%", marginBottom: "10px", padding: "6px" }}
          />

          <label>Location</label>
          <select
            value={selectedLocation.id}
            onChange={(e) =>
              setSelectedLocation(
                investigationLocations.find((l) => l.id === e.target.value)
              )
            }
            style={{ width: "100%", marginBottom: "10px", padding: "6px" }}
          >
            {investigationLocations.map((loc) => (
              <option key={loc.id} value={loc.id}>
                {loc.name}
              </option>
            ))}
          </select>

          <label>Status</label>
          <select
            value={investigationStatus}
            onChange={(e) => setInvestigationStatus(e.target.value)}
            style={{ width: "100%", marginBottom: "10px", padding: "6px" }}
          >
            <option>Open</option>
            <option>Monitoring</option>
            <option>Escalated</option>
            <option>Closed</option>
          </select>

          <div
            style={{
              ...getStatusStyle(investigationStatus),
              padding: "8px 12px",
              borderRadius: "6px",
              display: "inline-block",
              marginTop: "5px",
            }}
          >
            {investigationStatus}
          </div>
        </div>

        <div style={{ border: "1px solid #ccc", padding: "10px", borderRadius: "8px" }}>
          <h2>Case Notes</h2>
          <textarea
            value={caseNotes}
            onChange={(e) => setCaseNotes(e.target.value)}
            rows={8}
            style={{ width: "100%", padding: "8px" }}
          />
        </div>
      </div>

      <div
        ref={reportRef}
        style={{
          border: "1px solid #ccc",
          borderRadius: "10px",
          padding: "16px",
          backgroundColor: "#fffdf2",
          marginBottom: "20px",
        }}
      >
        <h2 style={{ marginTop: 0 }}>Investigation Report Snapshot</h2>
        <p><strong>Case:</strong> {caseTitle}</p>
        <p><strong>Location:</strong> {selectedLocation.name}</p>
        <p><strong>Status:</strong> {investigationStatus}</p>
        <p><strong>Zone Risk:</strong> {overallZoneRisk}</p>
        <p><strong>Ships in Zone:</strong> {shipsInZone.length}</p>
        <p><strong>High-Risk Ships:</strong> {highRiskShipsInZone.length}</p>
        <p><strong>Cyber Alerts Nearby:</strong> {cyberAlertsInZone.length}</p>
        <p><strong>OpenPhish Alerts Nearby:</strong> {openPhishAlertsInZone.length}</p>
        <p><strong>Notes:</strong> {caseNotes}</p>
        <p><strong>Auto Summary:</strong> {generatedSummary}</p>
      </div>

      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "20px" }}>
        <button
          onClick={exportPdfReport}
          style={{
            padding: "10px 15px",
            backgroundColor: "#1677ff",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
          }}
        >
          📄 Export PDF Report
        </button>

        <button
          onClick={requestAlertsPermission}
          style={{
            padding: "10px 15px",
            backgroundColor: notificationsEnabled ? "#52c41a" : "#722ed1",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
          }}
        >
          {notificationsEnabled ? "✅ Alerts Enabled" : "🔔 Enable Alert Triggers"}
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, minmax(160px, 1fr))",
          gap: "12px",
          marginBottom: "20px",
        }}
      >
        <div style={{ border: "1px solid #ccc", padding: "12px", borderRadius: "8px" }}>
          <strong>Ships in Zone</strong>
          <p style={{ fontSize: "24px", margin: "8px 0" }}>{shipsInZone.length}</p>
        </div>

        <div style={{ border: "1px solid #ccc", padding: "12px", borderRadius: "8px" }}>
          <strong>High-Risk Ships</strong>
          <p style={{ fontSize: "24px", margin: "8px 0" }}>{highRiskShipsInZone.length}</p>
        </div>

        <div style={{ border: "1px solid #ccc", padding: "12px", borderRadius: "8px" }}>
          <strong>Cyber Alerts Nearby</strong>
          <p style={{ fontSize: "24px", margin: "8px 0" }}>{visibleCyberAlerts.length}</p>
        </div>

        <div style={{ border: "1px solid #ccc", padding: "12px", borderRadius: "8px" }}>
          <strong>OpenPhish Nearby</strong>
          <p style={{ fontSize: "24px", margin: "8px 0" }}>{openPhishAlertsInZone.length}</p>
        </div>

        <div style={{ border: "1px solid #ccc", padding: "12px", borderRadius: "8px" }}>
          <strong>Zone Risk</strong>
          <p style={{ fontSize: "24px", margin: "8px 0" }}>{overallZoneRisk}</p>
        </div>
      </div>

      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "10px" }}>
        <div>
          <label>Basemap: </label>
          <select value={basemap} onChange={(e) => setBasemap(e.target.value)}>
            <option value="esri">Esri Satellite</option>
            <option value="osm">OpenStreetMap</option>
          </select>
        </div>

        <div>
          <label>Cyber Alerts: </label>
          <select
            value={cyberFilter}
            onChange={(e) => setCyberFilter(e.target.value)}
          >
            <option value="all">All Cyber Alerts</option>
            <option value="openphish">OpenPhish Only</option>
            <option value="simulation">Simulation Only</option>
          </select>
        </div>
      </div>

      <MapContainer
        center={[-17.8, 178]}
        zoom={6}
        style={{ height: "500px" }}
      >
        <FocusLocation location={selectedLocation} />

        {basemap === "osm" ? (
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="&copy; OpenStreetMap contributors"
          />
        ) : (
          <TileLayer
            url="https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Source: Esri"
          />
        )}

        <Circle
          center={[selectedLocation.lat, selectedLocation.lon]}
          radius={selectedLocation.radius}
          pathOptions={{
            color: "#111",
            fillColor: "#999",
            fillOpacity: 0.08,
          }}
        >
          <Popup>
            <strong>{selectedLocation.name}</strong>
            <br />
            Investigation target area
          </Popup>
        </Circle>

        {visibleCyberAlerts.map((alert, i) => (
          <Circle
            key={`cyber-${i}`}
            center={[alert.lat, alert.lon]}
            radius={alert.source === "openphish" ? 6500 : 5000}
            pathOptions={{
              color: alert.severity === "high" ? "red" : "orange",
              fillColor: alert.severity === "high" ? "red" : "orange",
              fillOpacity: alert.source === "openphish" ? 0.28 : 0.2,
            }}
          >
            <Popup>
              <strong>{alert.title}</strong>
              <br />
              Severity: {alert.severity}
              <br />
              Category: {alert.category}
              <br />
              Location: {alert.location}
              <br />
              Source: {alert.source || "unknown"}
              <br />
              Confidence: {alert.confidence || "unknown"}
              <br />
              Verification: {alert.verification || "unknown"}
              <br />
              {alert.ioc && (
                <>
                  IOC:
                  <br />
                  <a href={alert.ioc} target="_blank" rel="noreferrer">
                    {alert.ioc}
                  </a>
                  <br />
                </>
              )}
              {alert.message}
            </Popup>
          </Circle>
        ))}

        {ships.map((ship, i) => (
          <Marker key={i} position={[ship.lat, ship.lon]}>
            <Popup>
              <strong>{ship.name}</strong>
              <br />
              Type: {ship.type}
              <br />
              Status: {ship.status}
              <br />
              Threat: {ship.threat_level} ({ship.threat_score})
              <br />
              Source: {ship.source}
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "15px",
          marginTop: "20px",
        }}
      >
        <div style={{ border: "1px solid #ccc", padding: "12px", borderRadius: "8px" }}>
          <h2>Ships Inside Investigation Zone</h2>
          {shipsInZone.length === 0 ? (
            <p>No ships currently inside this investigation area.</p>
          ) : (
            shipsInZone.map((ship, i) => (
              <div key={i} style={{ marginBottom: "10px" }}>
                <strong>{ship.name}</strong>
                <div>Threat: {ship.threat_level}</div>
                <div>Source: {ship.source}</div>
              </div>
            ))
          )}
        </div>

        <div style={{ border: "1px solid #ccc", padding: "12px", borderRadius: "8px" }}>
          <h2>Cyber Alerts Near Investigation Zone</h2>
          {visibleCyberAlerts.length === 0 ? (
            <p>No cyber alerts near this investigation area.</p>
          ) : (
            visibleCyberAlerts.map((alert, i) => (
              <div
                key={i}
                style={{
                  ...getSeverityStyle(alert.severity),
                  marginBottom: "10px",
                  padding: "10px",
                  borderRadius: "8px",
                }}
              >
                <strong>{alert.title}</strong>
                <div>Severity: {alert.severity}</div>
                <div>Location: {alert.location}</div>
                <div>Source: {alert.source || "unknown"}</div>
                <div>Confidence: {alert.confidence || "unknown"}</div>
                <div>
                  Verification:{" "}
                  <span
                    style={{
                      ...getVerificationBadgeStyle(alert.verification),
                      padding: "2px 8px",
                      borderRadius: "12px",
                      display: "inline-block",
                      marginTop: "4px",
                    }}
                  >
                    {alert.verification || "unknown"}
                  </span>
                </div>
                {alert.ioc && (
                  <div style={{ marginTop: "6px", wordBreak: "break-all" }}>
                    IOC:{" "}
                    <a href={alert.ioc} target="_blank" rel="noreferrer">
                      {alert.ioc}
                    </a>
                  </div>
                )}
              </div>
            ))
          )}
        </div
        
        <div
  style={{
    border: "1px solid #ccc",
    padding: "12px",
    borderRadius: "8px",
    marginTop: "20px",
  }}
>
  <h2>Correlated Threat Intelligence</h2>

  {correlations.length === 0 ? (
    <p>No correlations detected.</p>
  ) : (
    correlations.map((c, i) => (
      <div
        key={i}
        style={{
          marginBottom: "10px",
          padding: "10px",
          borderRadius: "8px",
          backgroundColor:
            c.correlation_confidence === "HIGH"
              ? "#ffcccc"
              : c.correlation_confidence === "MEDIUM"
              ? "#fff3cd"
              : "#f6ffed",
          border: "1px solid #ccc",
        }}
      >
        <strong>{c.title}</strong>

        <div>{c.message}</div>

        <div>
          <strong>Confidence:</strong> {c.correlation_confidence}
        </div>

        <div>
          <strong>Priority Score:</strong> {c.priority}
        </div>

        <div>
          <strong>Distance:</strong> {c.distance_km} km
        </div>

        <div>
          <strong>Ship:</strong> {c.ship_name} ({c.ship_type})
        </div>

        <div>
          <strong>Ship Risk Score:</strong> {c.ship_risk_score}
        </div>

        <div>
          <strong>Alert Source:</strong> {c.alert_source}
        </div>

        <div>
          <strong>Verification:</strong> {c.alert_verification}
        </div>
      </div>
    );
  }  

export default App;
