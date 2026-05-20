import { useEffect, useState } from "react";

export default function BehavioralPanel() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch("http://127.0.0.1:5000/api/behavioral-events");
        const data = await res.json();
        setEvents(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Behavioral events fetch failed:", err);
      }
    };

    fetchEvents();
    const timer = setInterval(fetchEvents, 15000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div style={{
      position: "absolute",
      top: "90px",
      right: "20px",
      zIndex: 1000,
      width: "360px",
      maxHeight: "420px",
      overflowY: "auto",
      background: "rgba(5, 10, 20, 0.92)",
      color: "#fff",
      border: "1px solid rgba(0, 255, 255, 0.35)",
      borderRadius: "12px",
      padding: "12px",
      fontSize: "13px",
      boxShadow: "0 0 18px rgba(0,255,255,0.25)"
    }}>
      <h3 style={{ margin: "0 0 10px 0", color: "#66fcf1" }}>
        Behavioral Intelligence
      </h3>

      <div style={{ marginBottom: "8px", color: "#ccc" }}>
        Events detected: {events.length}
      </div>

      {events.length === 0 ? (
        <div style={{ color: "#999" }}>No offshore behavioral events detected.</div>
      ) : (
        events.slice(0, 6).map((event, index) => (
          <div key={index} style={{
            marginBottom: "10px",
            padding: "8px",
            borderRadius: "8px",
            background: "rgba(255,255,255,0.06)",
            borderLeft: event.risk === "HIGH" ? "4px solid red" :
                        event.risk === "MEDIUM" ? "4px solid orange" :
                        "4px solid #66fcf1"
          }}>
            <strong>{event.vessel_name || "UNKNOWN VESSEL"}</strong>
            <div>MMSI: {event.mmsi || "N/A"}</div>
            <div>Risk: {event.risk} | Score: {event.behavior_score}</div>
            <div>Behaviors: {(event.detected_behaviors || []).join(", ")}</div>
            <div>Lat: {event.latitude}</div>
            <div>Lon: {event.longitude}</div>
            <div>Nearest Port: {event.nearest_port || "N/A"}</div>
            <div>Distance: {event.distance_from_nearest_port_nm || "N/A"} nm</div>
          </div>
        ))
      )}

      <div style={{ marginTop: "12px", borderTop: "1px solid rgba(255,255,255,0.2)", paddingTop: "10px" }}>
        <h4 style={{ margin: "0 0 8px 0", color: "#66fcf1" }}>PDF Reports</h4>

        <button onClick={() => window.open("http://127.0.0.1:5000/api/night-stop/report/pdf", "_blank")} style={{ width: "100%", marginBottom: "6px", padding: "7px", borderRadius: "8px" }}>
          Possible Night Stop PDF
        </button>

        <button onClick={() => window.open("http://127.0.0.1:5000/api/night-stop/anthas/report/pdf", "_blank")} style={{ width: "100%", marginBottom: "6px", padding: "7px", borderRadius: "8px" }}>
          ANTHAS Night Stop PDF
        </button>

        <button onClick={() => window.open("http://127.0.0.1:5000/api/night-movement/arrow/report/pdf", "_blank")} style={{ width: "100%", padding: "7px", borderRadius: "8px" }}>
          ARROW Night Movement PDF
        </button>
      </div>

    </div>
  );
}
