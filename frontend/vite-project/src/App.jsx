import React, { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Popup,
  CircleMarker,
  LayersControl,
  Polyline,
  Circle,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

function riskColor(level) {
  switch ((level || "").toLowerCase()) {
    case "critical":
      return "#dc2626";
    case "high":
      return "#f97316";
    case "medium":
      return "#eab308";
    default:
      return "#22c55e";
  }
}

function severityColor(level) {
  switch ((level || "").toLowerCase()) {
    case "critical":
      return "#dc2626";
    case "high":
      return "#f97316";
    case "medium":
      return "#eab308";
    default:
      return "#22c55e";
  }
}

function darkActivityColor(level) {
  switch ((level || "").toLowerCase()) {
    case "critical":
      return "#7c3aed";
    case "high":
      return "#8b5cf6";
    case "medium":
      return "#a78bfa";
    default:
      return "#c4b5fd";
  }
}

function Badge({ text, color }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "4px 8px",
        borderRadius: "999px",
        fontSize: "12px",
        fontWeight: 700,
        background: color,
        color: "white",
        textTransform: "uppercase",
      }}
    >
      {text}
    </span>
  );
}

function SectionToggle({ title, onClick }) {
  return (
    <button onClick={onClick} style={buttonStyle}>
      {title}
    </button>
  );
}

export default function App() {
  const apiBase = "http://127.0.0.1:5000";

  const [alerts, setAlerts] = useState([]);
  const [ships, setShips] = useState([]);
  const [events, setEvents] = useState([]);
  const [crime, setCrime] = useState([]);
  const [correlations, setCorrelations] = useState([]);
  const [summary, setSummary] = useState(null);

  const [selectedType, setSelectedType] = useState("all");

  const [showTopVessel, setShowTopVessel] = useState(true);
  const [showAlerts, setShowAlerts] = useState(true);
  const [showShips, setShowShips] = useState(true);
  const [showDarkActivity, setShowDarkActivity] = useState(true);
  const [showCorrelations, setShowCorrelations] = useState(true);
  const [showEvents, setShowEvents] = useState(true);
  const [showCrime, setShowCrime] = useState(true);

  useEffect(() => {
    fetch(`${apiBase}/api/alerts`)
      .then((res) => res.json())
      .then(setAlerts)
      .catch((err) => console.error("alerts error", err));

    fetch(`${apiBase}/api/ships`)
      .then((res) => res.json())
      .then(setShips)
      .catch((err) => console.error("ships error", err));

    fetch(`${apiBase}/api/events`)
      .then((res) => res.json())
      .then(setEvents)
      .catch((err) => console.error("events error", err));

    fetch(`${apiBase}/api/crime`)
      .then((res) => res.json())
      .then(setCrime)
      .catch((err) => console.error("crime error", err));

    fetch(`${apiBase}/api/correlations`)
      .then((res) => res.json())
      .then(setCorrelations)
      .catch((err) => console.error("correlations error", err));

    fetch(`${apiBase}/api/summary`)
      .then((res) => res.json())
      .then(setSummary)
      .catch((err) => console.error("summary error", err));
  }, []);

  const filteredAlerts = useMemo(() => {
    if (selectedType === "all") return alerts;
    return alerts.filter(
      (a) =>
        (a.type || "").toLowerCase() === selectedType ||
        (a.category || "").toLowerCase() === selectedType
    );
  }, [alerts, selectedType]);

  const topVessel = summary?.top_vessel || ships[0] || null;
  const flaggedDarkActivityShips = ships.filter((s) => s.surface_event_flag);

  return (
    <div style={{ display: "flex", height: "100vh", width: "100%" }}>
      <div
        style={{
          width: "32%",
          minWidth: "370px",
          background: "#0f172a",
          color: "white",
          overflowY: "auto",
          padding: "12px",
          borderRight: "1px solid #1e293b",
        }}
      >
        <h1 style={{ marginTop: 0, marginBottom: "8px" }}>God&apos;s Eye Pacific</h1>
        <p style={{ color: "#94a3b8", marginTop: 0 }}>
          Operational Intelligence Dashboard
        </p>

        {summary && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Summary</h3>
            <div style={summaryGrid}>
              <div style={miniCard}>
                <strong>{summary.totals?.alerts ?? 0}</strong>
                <div style={miniLabel}>Alerts</div>
              </div>
              <div style={miniCard}>
                <strong>{summary.totals?.ships ?? 0}</strong>
                <div style={miniLabel}>Ships</div>
              </div>
              <div style={miniCard}>
                <strong>{summary.totals?.correlations ?? 0}</strong>
                <div style={miniLabel}>Correlations</div>
              </div>
              <div style={miniCard}>
                <strong>{summary.high_risk_ships ?? 0}</strong>
                <div style={miniLabel}>High Risk Ships</div>
              </div>
            </div>
          </div>
        )}

        <div style={{ marginBottom: "14px" }}>
          <label style={{ marginRight: "8px" }}>Filter Alerts:</label>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            style={selectStyle}
          >
            <option value="all">All</option>
            <option value="cyber">Cyber</option>
            <option value="phishing">Phishing</option>
            <option value="crime">Crime</option>
            <option value="maritime">Maritime</option>
          </select>
        </div>

        <SectionToggle
          title={showTopVessel ? "Hide Top Vessel" : "Show Top Vessel"}
          onClick={() => setShowTopVessel(!showTopVessel)}
        />
        {showTopVessel && topVessel && (
          <div style={cardStyle}>
            <div style={rowBetween}>
              <h3 style={{ marginTop: 0, marginBottom: 0 }}>Top Suspicious Vessel</h3>
              <Badge
                text={topVessel.risk_level || "low"}
                color={riskColor(topVessel.risk_level)}
              />
            </div>

            <div style={{ marginTop: "10px" }}>
              <strong>{topVessel.name}</strong>
            </div>
            <p style={{ margin: "8px 0" }}>
              {topVessel.analysis_summary || "No vessel analysis available."}
            </p>

            <div style={metaLine}>
              Score: {topVessel.risk_score ?? 0} | Heading:{" "}
              {topVessel.inferred_heading || "unknown"}
            </div>
            <div style={metaLine}>
              Region: {topVessel.region || "unknown"} | Destination:{" "}
              {topVessel.destination || "unknown"}
            </div>
            <div style={metaLine}>
              Estimated Origin: {topVessel.estimated_origin_zone || "unknown"}
            </div>

            {Array.isArray(topVessel.risk_reasons) &&
              topVessel.risk_reasons.length > 0 && (
                <div style={{ marginTop: "10px" }}>
                  <strong>Reasons</strong>
                  <ul style={listStyle}>
                    {topVessel.risk_reasons.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}
          </div>
        )}

        <SectionToggle
          title={showDarkActivity ? "Hide Dark Activity" : "Show Dark Activity"}
          onClick={() => setShowDarkActivity(!showDarkActivity)}
        />
        {showDarkActivity && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Dark Activity Watch</h3>
            {flaggedDarkActivityShips.length === 0 ? (
              <p>No dark activity flags.</p>
            ) : (
              flaggedDarkActivityShips.map((ship) => (
                <div key={`dark-${ship.id}`} style={itemStyle}>
                  <div style={rowBetween}>
                    <strong>{ship.name}</strong>
                    <Badge
                      text={ship.dark_activity_level || "low"}
                      color={darkActivityColor(ship.dark_activity_level)}
                    />
                  </div>
                  <p style={{ margin: "6px 0" }}>
                    {ship.surface_event_summary || "No dark activity summary."}
                  </p>
                  <small style={{ color: "#cbd5e1" }}>
                    score {ship.dark_activity_score ?? 0} | surface event{" "}
                    {ship.surface_event_flag ? "true" : "false"}
                  </small>

                  {Array.isArray(ship.dark_activity_reasons) &&
                    ship.dark_activity_reasons.length > 0 && (
                      <ul style={listStyle}>
                        {ship.dark_activity_reasons.map((reason, idx) => (
                          <li key={idx}>{reason}</li>
                        ))}
                      </ul>
                    )}
                </div>
              ))
            )}
          </div>
        )}

        <SectionToggle
          title={showAlerts ? "Hide Alerts" : "Show Alerts"}
          onClick={() => setShowAlerts(!showAlerts)}
        />
        {showAlerts && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Alerts</h3>
            {filteredAlerts.length === 0 ? (
              <p>No alerts available.</p>
            ) : (
              filteredAlerts.map((alert) => (
                <div key={alert.id} style={itemStyle}>
                  <div style={rowBetween}>
                    <strong>{alert.title}</strong>
                    <Badge
                      text={alert.severity || "low"}
                      color={severityColor(alert.severity)}
                    />
                  </div>
                  <p style={{ margin: "6px 0" }}>{alert.description}</p>
                  <small style={{ color: "#cbd5e1" }}>
                    {(alert.category || alert.type || "unknown").toLowerCase()} |{" "}
                    {alert.source || "unknown"} | score {alert.priority_score ?? 0}
                  </small>
                </div>
              ))
            )}
          </div>
        )}

        <SectionToggle
          title={showShips ? "Hide Ships" : "Show Ships"}
          onClick={() => setShowShips(!showShips)}
        />
        {showShips && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Ships</h3>
            {ships.length === 0 ? (
              <p>No ship data available.</p>
            ) : (
              ships.map((ship) => (
                <details key={ship.id} style={detailsStyle}>
                  <summary style={summaryStyle}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <strong>{ship.name}</strong>
                      <Badge
                        text={ship.risk_level || "low"}
                        color={riskColor(ship.risk_level)}
                      />
                    </div>
                  </summary>

                  <div style={{ marginTop: "10px" }}>
                    <div style={metaLine}>
                      Lat: {ship.lat}, Lng: {ship.lng}
                    </div>
                    <div style={metaLine}>
                      Score: {ship.risk_score ?? 0} | Heading:{" "}
                      {ship.inferred_heading || "unknown"}
                    </div>
                    <div style={metaLine}>
                      Region: {ship.region || "unknown"}
                    </div>
                    <div style={metaLine}>
                      Destination: {ship.destination || "unknown"} | Last Port:{" "}
                      {ship.last_port || "unknown"}
                    </div>
                    <div style={metaLine}>
                      AIS Gap: {ship.ais_gap_hours ?? 0}h | Speed:{" "}
                      {ship.speed_knots ?? "n/a"} kn
                    </div>
                    <div style={metaLine}>
                      Estimated Origin: {ship.estimated_origin_zone || "unknown"}
                    </div>
                    <div style={metaLine}>
                      Dark Activity: {ship.dark_activity_level || "low"} | Surface
                      Event: {ship.surface_event_flag ? "true" : "false"}
                    </div>

                    {ship.analysis_summary && (
                      <p style={{ marginTop: "8px" }}>{ship.analysis_summary}</p>
                    )}

                    {Array.isArray(ship.risk_reasons) && ship.risk_reasons.length > 0 && (
                      <>
                        <strong>Reasons</strong>
                        <ul style={listStyle}>
                          {ship.risk_reasons.map((reason, idx) => (
                            <li key={idx}>{reason}</li>
                          ))}
                        </ul>
                      </>
                    )}

                    {Array.isArray(ship.dark_activity_reasons) &&
                      ship.dark_activity_reasons.length > 0 && (
                        <>
                          <strong>Dark Activity Reasons</strong>
                          <ul style={listStyle}>
                            {ship.dark_activity_reasons.map((reason, idx) => (
                              <li key={idx}>{reason}</li>
                            ))}
                          </ul>
                        </>
                      )}
                  </div>
                </details>
              ))
            )}
          </div>
        )}

        <SectionToggle
          title={showCorrelations ? "Hide Correlations" : "Show Correlations"}
          onClick={() => setShowCorrelations(!showCorrelations)}
        />
        {showCorrelations && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Correlations</h3>
            {correlations.length === 0 ? (
              <p>No correlation data available.</p>
            ) : (
              correlations.slice(0, 8).map((item, idx) => (
                <div key={`${item.type}-${idx}`} style={itemStyle}>
                  <div style={rowBetween}>
                    <strong>{item.type}</strong>
                    <Badge
                      text={item.severity || "low"}
                      color={severityColor(item.severity)}
                    />
                  </div>
                  <p style={{ margin: "6px 0" }}>{item.summary}</p>
                  <small style={{ color: "#cbd5e1" }}>
                    {item.region || "unknown"} | confidence {item.confidence || "unknown"}
                  </small>
                </div>
              ))
            )}
          </div>
        )}

        <SectionToggle
          title={showEvents ? "Hide Events" : "Show Events"}
          onClick={() => setShowEvents(!showEvents)}
        />
        {showEvents && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Events</h3>
            {events.length === 0 ? (
              <p>No event data available.</p>
            ) : (
              events.map((event) => (
                <div key={event.id} style={itemStyle}>
                  <strong>{event.title}</strong>
                  <p style={{ margin: "6px 0" }}>{event.description}</p>
                  <small style={{ color: "#cbd5e1" }}>
                    {event.region || "unknown"} | {event.source || "unknown"}
                  </small>
                </div>
              ))
            )}
          </div>
        )}

        <SectionToggle
          title={showCrime ? "Hide Crime" : "Show Crime"}
          onClick={() => setShowCrime(!showCrime)}
        />
        {showCrime && (
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Crime</h3>
            {crime.length === 0 ? (
              <p>No crime data available.</p>
            ) : (
              crime.map((entry) => (
                <div key={entry.id} style={itemStyle}>
                  <div style={rowBetween}>
                    <strong>{entry.title}</strong>
                    <Badge
                      text={entry.severity || "low"}
                      color={severityColor(entry.severity)}
                    />
                  </div>
                  <p style={{ margin: "6px 0" }}>{entry.description}</p>
                  <small style={{ color: "#cbd5e1" }}>
                    {entry.region || "unknown"} | {entry.source || "unknown"}
                  </small>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <div style={{ flex: 1 }}>
        <MapContainer
          center={[-18.2, 178.1]}
          zoom={6}
          style={{ height: "100%", width: "100%" }}
        >
          <LayersControl position="topright">
            <LayersControl.BaseLayer checked name="Esri Satellite">
              <TileLayer
                attribution="Tiles &copy; Esri"
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              />
            </LayersControl.BaseLayer>

            <LayersControl.BaseLayer name="OpenStreetMap">
              <TileLayer
                attribution="&copy; OpenStreetMap contributors"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            </LayersControl.BaseLayer>
          </LayersControl>

          {ships.map((ship) =>
  ship.lat && ship.lng ? (
    <React.Fragment key={`ship-${ship.id}`}>
      {ship.surface_event_flag && (
        <Circle
          center={[ship.lat, ship.lng]}
          radius={6}
          pathOptions={{
            color: darkActivityColor(ship.dark_activity_level),
            fillColor: darkActivityColor(ship.dark_activity_level),
            fillOpacity: 0.12,
          }}
        />
      )}

      <CircleMarker
        center={[ship.lat, ship.lng]}
        radius={12}
        pathOptions={{
          color: riskColor(ship.risk_level),
          fillColor: riskColor(ship.risk_level),
          fillOpacity: 0.85,
          weight: 2,
        }}
      >
        <Popup>
          <strong>{ship.name}</strong>
          <br />
          Risk: {ship.risk_level}
          <br />
          Score: {ship.risk_score}
          <br />

          {ship.surface_event_flag && (
            <div style={{ color: "#a78bfa", fontWeight: "bold", marginTop: "6px" }}>
              ⚠ Dark Activity Detected
            </div>
          )}

          Dark Activity: {ship.dark_activity_level}
          <br />
          AIS Gap: {ship.ais_gap_hours ?? 0}h
        </Popup>
      </CircleMarker>
    </React.Fragment>
  ) : null
)}
         
                  

          {ships.map((ship) => {
            const back = ship.projected_12h_back;
            const current = ship.lat && ship.lng ? [ship.lat, ship.lng] : null;
            const forward = ship.projected_12h_forward;

            if (!back || !current || !forward) return null;

            return (
              <React.Fragment key={`route-${ship.id}`}>
                <Polyline
                  positions={[
                    [back.lat, back.lng],
                    current,
                  ]}
                  pathOptions={{
                    color: "#38bdf8",
                    weight: 3,
                    opacity: 0.8,
                    dashArray: "6, 6",
                  }}
                />
                <Polyline
                  positions={[
                    current,
                    [forward.lat, forward.lng],
                  ]}
                  pathOptions={{
                    color: riskColor(ship.risk_level),
                    weight: 4,
                    opacity: 0.9,
                  }}
                />
              </React.Fragment>
            );
          })}

          {alerts.map((alert) =>
            alert.lat && alert.lng ? (
              <CircleMarker
                key={alert.id}
                center={[alert.lat, alert.lng]}
                radius={6}
                pathOptions={{
                  color: severityColor(alert.severity),
                  fillColor: severityColor(alert.severity),
                  fillOpacity: 0.55,
                }}
              >
                <Popup>
                  <strong>{alert.title}</strong>
                  <br />
                  {alert.description}
                  <br />
                  Score: {alert.priority_score ?? 0}
                </Popup>
              </CircleMarker>
            ) : null
          )}

          {crime.map((entry) =>
            entry.lat && entry.lng ? (
              <CircleMarker
                key={entry.id}
                center={[entry.lat, entry.lng]}
                radius={10}
                pathOptions={{
                  color: severityColor(entry.severity),
                  fillColor: severityColor(entry.severity),
                  fillOpacity: 0.7,
                }}
              >
                <Popup>
                  <strong>{entry.title}</strong>
                  <br />
                  {entry.description}
                </Popup>
              </CircleMarker>
            ) : null
          )}

          {events.map((event) =>
            event.lat && event.lng ? (
              <CircleMarker
                key={event.id}
                center={[event.lat, event.lng]}
                radius={8}
                pathOptions={{
                  color: "#38bdf8",
                  fillColor: "#38bdf8",
                  fillOpacity: 0.7,
                }}
              >
                <Popup>
                  <strong>{event.title}</strong>
                  <br />
                  {event.description}
                </Popup>
              </CircleMarker>
            ) : null
          )}
        </MapContainer>
      </div>
    </div>
  );
}

const selectStyle = {
  padding: "7px 10px",
  borderRadius: "8px",
  background: "#1e293b",
  color: "white",
  border: "1px solid #334155",
};

const buttonStyle = {
  width: "100%",
  padding: "10px",
  marginBottom: "8px",
  background: "#2563eb",
  color: "white",
  border: "none",
  borderRadius: "8px",
  cursor: "pointer",
};

const cardStyle = {
  background: "#1e293b",
  padding: "12px",
  borderRadius: "10px",
  marginBottom: "12px",
};

const itemStyle = {
  padding: "10px 0",
  borderBottom: "1px solid #334155",
};

const rowBetween = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "8px",
};

const listStyle = {
  marginTop: "8px",
  marginBottom: 0,
  paddingLeft: "18px",
};

const metaLine = {
  color: "#cbd5e1",
  fontSize: "13px",
  marginTop: "4px",
};

const detailsStyle = {
  padding: "10px 0",
  borderBottom: "1px solid #334155",
};

const summaryStyle = {
  cursor: "pointer",
  listStyle: "none",
};

const summaryGrid = {
  display: "grid",
  gridTemplateColumns: "repeat(2, 1fr)",
  gap: "8px",
};

const miniCard = {
  background: "#0f172a",
  borderRadius: "10px",
  padding: "10px",
  textAlign: "center",
};

const miniLabel = {
  fontSize: "12px",
  color: "#94a3b8",
  marginTop: "4px",
};
