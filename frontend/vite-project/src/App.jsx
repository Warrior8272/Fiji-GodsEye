import { useEffect, useMemo, useState } from "react";

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
          gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
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
