export default function FloatingReportsPanel() {
  const btn = {
    width: "100%",
    marginBottom: "7px",
    padding: "8px",
    borderRadius: "8px",
    border: "1px solid #66fcf1",
    background: "rgba(0,255,255,0.08)",
    color: "#fff",
    cursor: "pointer",
    fontSize: "12px",
    fontWeight: "bold"
  };

  return (
    <div style={{
      position: "fixed",
      right: "18px",
      bottom: "18px",
      zIndex: 99999,
      width: "270px",
      background: "rgba(3, 8, 20, 0.96)",
      border: "1px solid rgba(102,252,241,0.6)",
      borderRadius: "14px",
      padding: "12px",
      color: "#fff",
      boxShadow: "0 0 22px rgba(0,255,255,0.35)"
    }}>
      <div style={{ color: "#66fcf1", fontWeight: "bold", marginBottom: "10px" }}>
        NA.YADRA PDF Reports
      </div>

      <button style={btn} onClick={() => window.open("http://127.0.0.1:5000/api/night-stop/report/pdf", "_blank")}>
        Possible Night Stop PDF
      </button>

      <button style={btn} onClick={() => window.open("http://127.0.0.1:5000/api/night-stop/anthas/report/pdf", "_blank")}>
        ANTHAS Night Stop PDF
      </button>

      <button style={btn} onClick={() => window.open("http://127.0.0.1:5000/api/night-movement/arrow/report/pdf", "_blank")}>
        ARROW Night Movement PDF
      </button>
    </div>
  );
}
