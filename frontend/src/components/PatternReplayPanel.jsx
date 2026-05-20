import { useEffect, useState } from "react";

export default function PatternReplayPanel() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch("http://127.0.0.1:5000/api/behavioral-history/24h");
        const data = await res.json();
        setEvents(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Pattern replay fetch failed:", err);
      }
    };

    fetchHistory();
    const timer = setInterval(fetchHistory, 30000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div style={{
      position: "fixed",
      left: "18px",
      bottom: "18px",
      zIndex: 99999,
      width: "360px",
      maxHeight: "430px",
      overflowY: "auto",
      background: "rgba(3, 8, 20, 0.96)",
      border: "1px solid rgba(255,165,0,0.65)",
      borderRadius: "14px",
      padding: "12px",
      color: "#fff",
      boxShadow: "0 0 22px rgba(255,165,0,0.3)",
      fontSize: "12px"
    }}>
      <div style={{ color: "orange", fontWeight: "bold", marginBottom: "8px", fontSize: "15px" }}>
        Pattern-of-Life Replay
      </div>

      <div style={{ color: "#ccc", marginBottom: "10px" }}>
        Last 24h behavioural events: {events.length}
      </div>

      {events.length === 0 ? (
        <div style={{ color: "#aaa" }}>No behavioural history in the last 24 hours.</div>
      ) : (
        events.slice(0, 8).map((event, index) => (
          <div key={index} style={{
            padding: "8px",
            marginBottom: "8px",
            borderRadius: "8px",
            background: "rgba(255,255,255,0.06)",
            borderLeft: event.risk === "HIGH" ? "4px solid red" :
                        event.risk === "MEDIUM" ? "4px solid orange" :
                        "4px solid #66fcf1"
          }}>
            <strong>{event.vessel_name || "UNKNOWN"}</strong>
            <div>MMSI: {event.mmsi || "N/A"}</div>
            <div>Risk: {event.risk} | Score: {event.behavior_score}</div>
            <div>Fiji Time: {event.fiji_time}</div>
            <div>Behaviours: {(event.detected_behaviors || []).join(", ")}</div>
            <div>Lat: {event.latitude}</div>
            <div>Lon: {event.longitude}</div>
          </div>
        ))
      )}
    </div>
  );
}
