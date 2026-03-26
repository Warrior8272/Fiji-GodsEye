<div
  style={{
    display: "flex",
    gap: "20px",
    marginBottom: "20px",
    marginTop: "10px",
  }}
>
  <div style={{ background: "#111", padding: "10px 15px", borderRadius: "8px" }}>
    📰 News: <strong>{totalNews}</strong>
  </div>

  <div style={{ background: "#111", padding: "10px 15px", borderRadius: "8px" }}>
    🚨 Alerts: <strong>{totalAlerts}</strong>
  </div>

  <div style={{ background: "#111", padding: "10px 15px", borderRadius: "8px" }}>
    ⚙️ Status:{" "}
    <strong style={{ color: error ? "red" : "lightgreen" }}>
      {error ? "ERROR" : "OK"}
    </strong>
  </div>
</div>
export default App;

