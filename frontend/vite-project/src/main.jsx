import { useEffect, useState } from "react";

function App() {
  const [news, setNews] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  const totalNews = news.length;
  const totalAlerts = alerts.length;

  useEffect(() => {
    const loadData = () => {
      fetch("http://localhost:5000/news")
        .then((res) => res.json())
        .then((data) => {
          setNews(data);
          setLastUpdated(new Date().toLocaleTimeString());
        })
        .catch((err) => setError(err.message));

      fetch("http://localhost:5000/alerts")
        .then((res) => res.json())
        .then((data) => setAlerts(data))
        .catch((err) => setError(err.message));
    };

    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const filteredNews = news.filter((item) =>
    item.title?.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div
      style={{
        padding: "20px",
        color: "white",
        background: "#050505",
        minHeight: "100vh",
        fontFamily: "Arial",
      }}
    >
      <div style={{ marginBottom: "20px" }}>
        <h1>🌍 Fiji Gods Eye v1</h1>
        <p style={{ color: "#bbb" }}>OSINT-style monitoring dashboard</p>
        <p style={{ color: "#888", fontSize: "14px" }}>
          Last updated: {lastUpdated || "Loading..."}
        </p>
      </div>

      <div
        style={{
          display: "flex",
          gap: "20px",
          marginBottom: "20px",
        }}
      >
        <div style={{ background: "#111", padding: "10px", borderRadius: "8px" }}>
          📰 News: <strong>{totalNews}</strong>
        </div>

        <div style={{ background: "#111", padding: "10px", borderRadius: "8px" }}>
          🚨 Alerts: <strong>{totalAlerts}</strong>
        </div>

        <div style={{ background: "#111", padding: "10px", borderRadius: "8px" }}>
          ⚙️ Status:{" "}
          <strong style={{ color: error ? "red" : "lightgreen" }}>
            {error ? "ERROR" : "OK"}
          </strong>
        </div>
      </div>

      <input
        type="text"
        placeholder="Filter headlines..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{
          padding: "10px",
          width: "300px",
          marginBottom: "20px",
          borderRadius: "6px",
        }}
      />

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "20px" }}>
        <div style={{ background: "#111", padding: "15px", borderRadius: "8px" }}>
          <h2>📰 Latest News</h2>
          <ul>
            {filteredNews.map((item, i) => (
              <li key={i}>
                <a href={item.url} target="_blank" rel="noreferrer">
                  {item.title}
                </a>
              </li>
            ))}
          </ul>
        </div>

        <div style={{ background: "#111", padding: "15px", borderRadius: "8px" }}>
          <h2>🚨 Alerts</h2>
          {alerts.length === 0 ? (
            <p>No alerts</p>
          ) : (
            alerts.map((a, i) => (
              <div key={i} style={{ color: "red", marginBottom: "10px" }}>
                ⚠️ [{a.risk}] {a.title}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
