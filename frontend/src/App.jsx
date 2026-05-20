import { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Polyline,
  Rectangle,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import BehavioralPanel from "./components/BehavioralPanel";
import BehavioralEventMarkers from "./components/BehavioralEventMarkers";
import FloatingReportsPanel from "./components/FloatingReportsPanel";
import PatternReplayPanel from "./components/PatternReplayPanel";


const coverageZones = [
  { name: "Western Fiji / Lautoka / Nadi", bounds: [[-18.8, 176.6], [-16.9, 178.0]], color: "green" },
  { name: "Central / Suva Watch Zone", bounds: [[-18.5, 177.3], [-17.4, 178.8]], color: "orange" },
  { name: "Vanua Levu Watch Zone", bounds: [[-17.0, 178.0], [-15.5, 180.0]], color: "orange" },
  { name: "Kadavu Southern Watch Zone", bounds: [[-19.6, 177.0], [-18.5, 179.4]], color: "orange" },
  { name: "French Polynesia / Tahiti Watch Zone", bounds: [[-22.0, -154.0], [-14.0, -146.0]], color: "orange" },
  { name: "Marquesas Northern Watch Zone", bounds: [[-11.0, -142.5], [-7.0, -137.0]], color: "orange" },
  { name: "Tuamotu Archipelago Watch Zone", bounds: [[-24.0, -149.0], [-13.0, -134.0]], color: "orange" },
];

const portZones = [
  { name: "Lautoka", bounds: [[-17.66, 177.40], [-17.56, 177.50]] },
  { name: "Suva", bounds: [[-18.18, 178.38], [-18.04, 178.55]] },
  { name: "Levuka", bounds: [[-17.73, 178.78], [-17.64, 178.88]] },
  { name: "Labasa / Vanua Levu", bounds: [[-16.48, 179.25], [-16.28, 179.48]] },
];

function MapOverlays() {
  return (
    <>
      {coverageZones.map((z) => (
        <Rectangle
          key={z.name}
          bounds={z.bounds}
          pathOptions={{ color: z.color, weight: 1, fillOpacity: 0.08 }}
        />
      ))}

      {portZones.map((p) => (
        <Rectangle
          key={p.name}
          bounds={p.bounds}
          pathOptions={{ color: "red", weight: 1, dashArray: "6 6", fillOpacity: 0.03 }}
        />
      ))}
    </>
  );
}

function MapLegend() {
  return (
    <div style={{
      position: "absolute",
      bottom: 18,
      left: 18,
      zIndex: 1000,
      background: "rgba(10,15,25,0.9)",
      color: "white",
      padding: "10px 12px",
      borderRadius: "10px",
      fontSize: "12px",
      lineHeight: "1.6",
      border: "1px solid #334155"
    }}>
      <div><b>Map Legend</b></div>
      <div>🟢 Vessel / low risk</div>
      <div>🟠 Medium risk / watch zone</div>
      <div>🔴 Dashed box = port monitoring</div>
      <div style={{ marginTop: 6, opacity: 0.8 }}>Source: AIS + Fiji-Pacific zones</div>
    </div>
  );
}

function LastUpdatedLabel() {
  return (
    <div style={{
      position: "absolute",
      top: 12,
      right: 330,
      zIndex: 1000,
      background: "rgba(10,15,25,0.85)",
      color: "white",
      padding: "8px 10px",
      borderRadius: "8px",
      fontSize: "12px",
      border: "1px solid #334155"
    }}>
      Last updated: {new Date().toLocaleTimeString()}
    </div>
  );
}


function FitToData({ vessels, alerts, shouldFit }) {
  const map = useMap();

  useEffect(() => {


    if (!shouldFit) return;

    const vesselPoints = (vessels || [])
      .map((v) => [Number(v.lat), Number(v.lon)])
      .filter(([lat, lon]) => !Number.isNaN(lat) && !Number.isNaN(lon));

    const alertPoints = (alerts || [])
      .map((a) => [Number(a.lat), Number(a.lon)])
      .filter(([lat, lon]) => !Number.isNaN(lat) && !Number.isNaN(lon));

    const allPoints = [...vesselPoints, ...alertPoints];

    if (allPoints.length === 1) {
      map.setView(allPoints[0], 9);
      return;
    }

    if (allPoints.length > 1) {
      map;
    }
  }, [vessels, alerts, shouldFit, map]);

  return null;
}

function FollowSelected({ selected, selectedType, followMode }) {
  const map = useMap();

  useEffect(() => {
    if (!followMode) return;
    if (!selected) return;
    if (selectedType !== "vessel") return;

    const lat = Number(selected.lat);
    const lon = Number(selected.lon);

    if (Number.isNaN(lat) || Number.isNaN(lon)) return;

    map.setView([lat, lon], Math.max(map.getZoom(), 9), { animate: true });
  }, [selected, selectedType, followMode, map]);

  return null;
}

function LocateSelectedVessel() {
  const map = useMap();

  useEffect(() => {
    const handler = (event) => {
      const lat = Number(event.detail?.lat);
      const lon = Number(event.detail?.lon);

      if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
        map.setView([lat, lon], Math.max(map.getZoom(), 10), {
          animate: true,
        });
      }
    };

    window.addEventListener("locate-selected-vessel", handler);
    return () => window.removeEventListener("locate-selected-vessel", handler);
  }, [map]);

  return null;
}

function isOnLand(lat, lon) {
  const nLat = Number(lat);
  const nLon = Number(lon);

  if (Number.isNaN(nLat) || Number.isNaN(nLon)) return false;

  return (
    nLat > -18.2 &&
    nLat < -17.5 &&
    nLon > 177.3 &&
    nLon < 178.2
  );
}

function projectPoint(lat, lon, courseDeg, distanceKm = 3) {
  const R = 6371;
  const bearing = (courseDeg * Math.PI) / 180;

  const lat1 = (lat * Math.PI) / 180;
  const lon1 = (lon * Math.PI) / 180;
  const angularDistance = distanceKm / R;

  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(angularDistance) +
      Math.cos(lat1) * Math.sin(angularDistance) * Math.cos(bearing)
  );

  const lon2 =
    lon1 +
    Math.atan2(
      Math.sin(bearing) * Math.sin(angularDistance) * Math.cos(lat1),
      Math.cos(angularDistance) - Math.sin(lat1) * Math.sin(lat2)
    );

  return [(lat2 * 180) / Math.PI, (lon2 * 180) / Math.PI];
}

function formatFlags(flags) {
  if (!flags) return "None";
  if (Array.isArray(flags)) {
    return flags.length ? flags.join(", ") : "None";
  }
  if (typeof flags === "object") {
    return Object.values(flags).flat().filter(Boolean).join(", ") || "None";
  }
  return String(flags);
}

function MiniStat({ label, value }) {
  return (
    <div style={{ marginBottom: "8px" }}>
      <strong>{label}:</strong> {value}
    </div>
  );
}

export default function App() {
  const [selectedVessel, setSelectedVessel] = useState(null);
  const [vesselProfile, setVesselProfile] = useState(null);
  const [validationStatus, setValidationStatus] = useState("Pending");
  const [analystNote, setAnalystNote] = useState("");
  const [validationSaved, setValidationSaved] = useState(false);
  const [isEditingNote, setIsEditingNote] = useState(false);
  const [caseNote, setCaseNote] = useState("");
  const [caseHistory, setCaseHistory] = useState([]);
  const [selected, setSelected] = useState(null);
  const [selectedType, setSelectedType] = useState(null);

  const [vessels, setVessels] = useState([]);
const [intelSummary, setIntelSummary] = useState(null);
  const [aisGaps, setAisGaps] = useState([]);
  const [priorityTargets, setPriorityTargets] = useState([])
const [selectedTarget, setSelectedTarget] = useState(null)
const [selectedTimeline, setSelectedTimeline] = useState([])
  const [alerts, setAlerts] = useState([]);
  const [routeIntel, setRouteIntel] = useState([]);
  const [loiterStatus, setLoiterStatus] = useState({ total_monitored: 0, loitering: [] });
  const [rendezvousStatus, setRendezvousStatus] = useState({ total_pairs_monitored: 0, rendezvous: [] });
const [timelineData, setTimelineData] = useState([]);
const [networkData, setNetworkData] = useState({ zones: [], connections: [], events: [] });
  const [darkActivity, setDarkActivity] = useState({ total_dark_activity: 0, dark_activity: [] });
  const [clusterIntel, setClusterIntel] = useState({ total_clusters: 0, clusters: [] });
  const [operationalReport, setOperationalReport] = useState(null);
  const [feedCoverage, setFeedCoverage] = useState({ total_vessels: 0, coverage: [] });
  const [cyberThreats, setCyberThreats] = useState({ total: 0, events: [] });
const [cyberForm, setCyberForm] = useState({
  title: "",
  type: "MANUAL_OSINT",
  target: "",
  zone: "Suva Port",
  risk: "LOW",
  indicator: "",
  summary: "",
  recommended_action: "",
  verification_status: "UNVERIFIED",
  confidence: "LOW",
  observed_date: "",
  source_url: "",
  evidence_file: "",
  analyst_name: "NAYADRA Analyst",
  analyst_note: ""
});
const [cyberSubmitting, setCyberSubmitting] = useState(false);
const [cyberFilter, setCyberFilter] = useState("ALL");
const [cyberSourceFilter, setCyberSourceFilter] = useState("ALL");
const [cyberFeedHealth, setCyberFeedHealth] = useState(null);



  const [fusionIntel, setFusionIntel] = useState(null);


  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/maritime-cyber-fusion")
      .then((res) => res.json())
      .then((data) => {
        setFusionIntel(data || { total: 0, fusion_alerts: [] });
      })
      .catch((err) => {
        console.error("Maritime-cyber fusion fetch error:", err);
        setFusionIntel({ total: 0, fusion_alerts: [] });
      });
  }, []);

  const [satMismatch, setSatMismatch] = useState({ total_mismatches: 0, mismatches: [] });
  const [briefing, setBriefing] = useState(null);
  const [escalationAlerts, setEscalationAlerts] = useState({ total_alerts: 0, alerts: [] });
  const [dbEvents, setDbEvents] = useState({ events: [] });
  const [cases, setCases] = useState({ cases: [] });
  const [predictiveIntel, setPredictiveIntel] = useState({ total_predictions: 0, predictions: [] });

  const [route, setRoute] = useState([]);
  const [prediction, setPrediction] = useState([]);
  const [shouldFit, setShouldFit] = useState(true);

  const [historyRange, setHistoryRange] = useState("1");
  const [followMode, setFollowMode] = useState(false);

  const [loadingVessels, setLoadingVessels] = useState(true);
  const [loadingAlerts, setLoadingAlerts] = useState(true);

  const [vesselError, setVesselError] = useState("");
  const [alertError, setAlertError] = useState("");

  const [showVessels, setShowVessels] = useState(true);
  const [showAlerts, setShowAlerts] = useState(true);
const [showSentinel, setShowSentinel] = useState(true);


  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/cyber-alerts")
      .then((res) => res.json())
      .then((data) => {
        const events = Array.isArray(data) ? data : [];
        setCyberThreats({
          total: events.length,
          events: events
        });
      })
      .catch((err) => {
        console.error("Cyber alerts fetch error:", err);
        setCyberThreats({ total: 0, events: [] });
      });
  }, []);

  useEffect(() => {
    const fetchHealth = () => {
      fetch("http://127.0.0.1:5000/api/cyber-feed-health")
        .then((res) => res.json())
        .then((data) => setCyberFeedHealth(data))
        .catch((err) => {
          console.error("Cyber feed health fetch error:", err);
          setCyberFeedHealth({
            status: "ERROR",
            last_error: "Could not reach cyber feed health endpoint."
          });
        });
    };

    fetchHealth();
    const timer = setInterval(fetchHealth, 60000);
    return () => clearInterval(timer);
      <BehavioralPanel />
  }, []);


const [opacity, setOpacity] = useState(0.6);
  const [highRiskOnly, setHighRiskOnly] = useState(false);



  const updateCyberAlertStatus = async (alertId, newStatus) => {
    try {
      const res = await fetch("http://127.0.0.1:5000/api/update-cyber-alert-status?token=gods_eye_pacific_admin_2026", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          id: alertId,
          verification_status: newStatus,
          analyst_note: `Updated from dashboard to ${newStatus}`
        })
      });

      const result = await res.json();

      if (!result.ok) {
        alert("Cyber alert status update failed.");
        return;
      }

      setCyberThreats((prev) => {
        const events = (prev?.events || []).map((item) =>
          item.id === alertId
            ? {
                ...item,
                status: newStatus,
                verification_status: newStatus,
                analyst_note: `Updated from dashboard to ${newStatus}`,
                last_reviewed_at: new Date().toISOString()
              }
            : item
        );

        return {
          ...prev,
          total: events.length,
          events
        };
      });

    } catch (err) {
      console.error("Cyber status update error:", err);
      alert("Cyber alert status update error.");
    }
  };

  const generateReport = () => {
    const elevatedVessels = vessels
      .filter((v) => String(v.risk_level || "").toLowerCase() !== "low")
      .slice(0, 20)
      .map((v) => ({
        id: v.id,
        mmsi: v.mmsi || "unknown",
        name: v.name || "unknown",
        lat: v.lat,
        lon: v.lon,
        speed: v.speed,
        course: v.course,
        risk_level: v.risk_level || "unknown",
        flags: v.anomaly_flags || v.flags || [],

        
        zone: (() => {
          const lat = v.lat;
          const lon = v.lon;

          if (lat > -20 && lat < -15 && lon > 175 && lon < 180) return "Fiji EEZ";
          if (lat > -23 && lat < -15 && lon > -175 && lon < -173) return "Tonga";
          if (lat > -20 && lat < -10 && lon > 165 && lon < 170) return "Vanuatu";
          if (lat > -15 && lat < -13 && lon > -173 && lon < -171) return "Samoa";
          if (lat > -10 && lat < -5 && lon > 175 && lon < 180) return "Tuvalu";
          if (lat > -12 && lat < -5 && lon > 155 && lon < 165) return "Solomon Islands";
          if (lat > -10 && lat < 0 && lon > 140 && lon < 155) return "Papua New Guinea";
          if (lat > -5 && lat < 5 && lon > 170 && lon < -150) return "Kiribati";
          if (lat > -10 && lat < -7 && lon > -172 && lon < -170) return "Tokelau";
          if (lat > 0 && lat < 10 && lon > 140 && lon < 160) return "Micronesia";
          if (lat > -13 && lat < -12 && lon > 177 && lon < 179) return "Rotuma";

          return "Open Ocean";
        })(),

        
        recommendation:
          (v.speed || 0) < 1
            ? "Monitor closely. Vessel is moving very slowly or stationary inside a monitored zone."
            : (v.speed || 0) < 2
            ? "Investigate pattern. Low-speed movement may indicate drifting, waiting, or unusual behaviour."
            : "Routine monitoring. No immediate action required based on speed behaviour."
,

        threat:
          (v.speed || 0) < 1
            ? "Port Loitering"
            : (v.speed || 0) < 2
            ? "Suspicious Drift"
            : "Normal Transit"
      }));

    const activeAlerts = alerts.slice(0, 20).map((a) => {
      let severity = "low";

      // Basic intelligence scoring
      if (a.type === "LOITERING") {
        severity = "high";
      } else if ((a.speed || 0) < 2) {
        severity = "medium";
      } else {
        severity = "low";
      }

      return {
        id: a.id,
        name: a.name || "Alert",
        severity,
        message: a.message || ""
      };
    });

    const analysis =
      elevatedVessels.length > 0 || activeAlerts.length > 0
        ? `${elevatedVessels.length} elevated vessel(s) and ${activeAlerts.length} active alert(s) require monitoring.`
        : "No elevated maritime threats detected at the time of report generation.";

    const report = {
      system: "GODS EYE - Operational Maritime Intelligence Report v1",
      region: "Fiji-Pacific EEZ",
      timestamp: new Date().toISOString(),
      summary: {
        total_vessels: vessels.length,
        total_alerts: alerts.length,
        elevated_vessels: elevatedVessels.length,
        satellite_enabled: showSentinel
      },
      analysis,
      vessels: elevatedVessels,
      alerts: activeAlerts
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "gods_eye_operational_intel_report_v1.json";
    a.click();
    URL.revokeObjectURL(url);
  };




  useEffect(() => {
    if (selected && selectedType === "vessel" && selected.mmsi) {

      fetch(`http://127.0.0.1:5000/api/timeline/${selected.mmsi}`)
        .then((res) => res.json())
        .then((data) => {
          setTimelineData(data.timeline || []);
        })
        .catch((err) => {
          console.error("Timeline error:", err);
          setTimelineData([]);
        });

      fetch(`http://127.0.0.1:5000/api/network/${selected.mmsi}`)
        .then((res) => res.json())
        .then((data) => {
          setNetworkData(data || { zones: [], connections: [], events: [] });
        })
        .catch((err) => {
          console.error("Network error:", err);
          setNetworkData({ zones: [], connections: [], events: [] });
        });

      fetch(`http://127.0.0.1:5000/api/vessel-profile?token=gods_eye_pacific_admin_2026&mmsi=${selected.mmsi || selected.MMSI || selected.id || selected.name}`)
        .then((res) => res.json())
        .then((data) => setVesselProfile(data))
        .catch((err) => {
          console.error("Vessel profile error:", err);
          setVesselProfile(null);
        });

    } else {
      setTimelineData([]);
      setNetworkData({ zones: [], connections: [], events: [] });
      setVesselProfile(null);
    }
  }, [selected, selectedType]);

  useEffect(() => {
    if (!vesselProfile || vesselProfile.error) {
      setCaseHistory([]);
      return;
    }

    fetch(`http://127.0.0.1:5000/api/case-notes?token=gods_eye_pacific_admin_2026&mmsi=${vesselProfile.mmsi}`)
      .then((res) => res.json())
      .then((data) => {
        setCaseHistory(data.case_notes || []);
      })
      .catch((err) => {
        console.error("Case history fetch error:", err);
        setCaseHistory([]);
      });
  }, [vesselProfile]);

  useEffect(() => {
    if (!vesselProfile || vesselProfile.error) return;

    const key = `nayadra_validation_${vesselProfile.mmsi || vesselProfile.name || "unknown"}`;

    try {
      const saved = JSON.parse(localStorage.getItem(key) || "{}");
      setValidationStatus(saved.status || "Pending");
      setAnalystNote(saved.note || "");
      setValidationSaved(false);
    } catch (e) {
      setValidationStatus("Pending");
      setAnalystNote("");
      setValidationSaved(false);
    }
  }, [vesselProfile]);



  useEffect(() => {

  fetch("http://127.0.0.1:5000/api/intel-summary")
    .then(res => res.json())
    .then(data => setIntelSummary(data))
    .catch(err => console.error("Intel summary error:", err));

    const loadVessels = () => {
      fetch("http://127.0.0.1:5000/api/vessels")
        .then((res) => {
          if (!res.ok) throw new Error(`Vessels HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          const parsed = Array.isArray(data) ? data : [];

          const memory = JSON.parse(localStorage.getItem("godsEyeVesselMemory") || "{}");

          const enrichedParsed = parsed.map((v) => {
            const vid = String(v.mmsi || v.id || "unknown");

            if (!memory[vid]) {
              memory[vid] = {
                sightings: 0,
                first_seen: new Date().toISOString(),
                last_seen: null,
                threat_hits: 0
              };
            }

            memory[vid].sightings += 1;
            memory[vid].last_seen = new Date().toISOString();

            if (
              String(v.threat_level || "").toUpperCase() === "HIGH" ||
              String(v.threat_level || "").toUpperCase() === "CRITICAL" ||
              Number(v.threat_score || v.risk || 0) >= 40
            ) {
              memory[vid].threat_hits += 1;
            }

            return {
              ...v,
              persistent_memory: memory[vid],
              repeat_offender: memory[vid].threat_hits >= 3 || memory[vid].sightings >= 10
            };
          });

          localStorage.setItem("godsEyeVesselMemory", JSON.stringify(memory));

          setVessels(enrichedParsed);
          setVesselError("");

          if (selected && selectedType === "vessel" && !isEditingNote) {
            const updated = parsed.find((v) => v.id === selected.id);
            if (updated) {
              setSelected(updated);
            }
          }
        })
        .catch((err) => {
          console.error("Vessels fetch error:", err);
          setVesselError(String(err));
          setVessels([]);
        })
        .finally(() => setLoadingVessels(false));
    };

    loadVessels();
    const interval = setInterval(loadVessels, 15000);
    return () => clearInterval(interval);
  }, [selected, selectedType]);


  useEffect(() => {
    if (selected && selectedType === "vessel" && selected.mmsi) {

      fetch(`http://127.0.0.1:5000/api/timeline/${selected.mmsi}`)
        .then((res) => res.json())
        .then((data) => {
          setTimelineData(data.timeline || []);
        })
        .catch((err) => {
          console.error("Timeline error:", err);
          setTimelineData([]);
        });

      fetch(`http://127.0.0.1:5000/api/network/${selected.mmsi}`)
        .then((res) => res.json())
        .then((data) => {
          setNetworkData(data || { zones: [], connections: [], events: [] });
        })
        .catch((err) => {
          console.error("Network error:", err);
          setNetworkData({ zones: [], connections: [], events: [] });
        });

      fetch(`http://127.0.0.1:5000/api/vessel-profile?token=gods_eye_pacific_admin_2026&mmsi=${selected.mmsi || selected.MMSI || selected.id || selected.name}`)
        .then((res) => res.json())
        .then((data) => setVesselProfile(data))
        .catch((err) => {
          console.error("Vessel profile error:", err);
          setVesselProfile(null);
        });

    } else {
      setTimelineData([]);
      setNetworkData({ zones: [], connections: [], events: [] });
      setVesselProfile(null);
    }
  }, [selected, selectedType]);

  useEffect(() => {

  fetch("http://127.0.0.1:5000/api/intel-summary")
    .then(res => res.json())
    .then(data => setIntelSummary(data))
    .catch(err => console.error("Intel summary error:", err));

    const loadAlerts = () => {
      fetch("http://127.0.0.1:5000/api/alerts")
        .then((res) => {
          if (!res.ok) throw new Error(`Alerts HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          setAlerts(Array.isArray(data) ? data : []);
          setAlertError("");
        })
        .catch((err) => {
          console.error("Alerts fetch error:", err);
          setAlertError(String(err));
          setAlerts([]);
        })
        .finally(() => setLoadingAlerts(false));
    };

    loadAlerts();
    const interval = setInterval(loadAlerts, 30000);
    return () => clearInterval(interval);
  }, []);


  useEffect(() => {
    if (selected && selectedType === "vessel" && selected.mmsi) {

      fetch(`http://127.0.0.1:5000/api/timeline/${selected.mmsi}`)
        .then((res) => res.json())
        .then((data) => {
          setTimelineData(data.timeline || []);
        })
        .catch((err) => {
          console.error("Timeline error:", err);
          setTimelineData([]);
        });

      fetch(`http://127.0.0.1:5000/api/network/${selected.mmsi}`)
        .then((res) => res.json())
        .then((data) => {
          setNetworkData(data || { zones: [], connections: [], events: [] });
        })
        .catch((err) => {
          console.error("Network error:", err);
          setNetworkData({ zones: [], connections: [], events: [] });
        });

      fetch(`http://127.0.0.1:5000/api/vessel-profile?token=gods_eye_pacific_admin_2026&mmsi=${selected.mmsi || selected.MMSI || selected.id || selected.name}`)
        .then((res) => res.json())
        .then((data) => setVesselProfile(data))
        .catch((err) => {
          console.error("Vessel profile error:", err);
          setVesselProfile(null);
        });

    } else {
      setTimelineData([]);
      setNetworkData({ zones: [], connections: [], events: [] });
      setVesselProfile(null);
    }
  }, [selected, selectedType]);

  useEffect(() => {

  fetch("http://127.0.0.1:5000/api/intel-summary")
    .then(res => res.json())
    .then(data => setIntelSummary(data))
    .catch(err => console.error("Intel summary error:", err));

    const timer = setTimeout(() => setShouldFit(false), 1500);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const loadIntelStatus = () => {
      fetch("http://127.0.0.1:5000/api/loiter-status")
        .then((res) => res.json())
        .then((data) => setLoiterStatus(data))
        .catch((err) => console.error("Loiter status error:", err));

      fetch("http://127.0.0.1:5000/api/rendezvous-status")
        .then((res) => res.json())
        .then((data) => setRendezvousStatus(data))
        .catch((err) => console.error("Rendezvous status error:", err));

      fetch("http://127.0.0.1:5000/api/dark-activity")
        .then((res) => res.json())
        .then((data) => setDarkActivity(data))
        .catch((err) => console.error("Dark activity error:", err));

      fetch("http://127.0.0.1:5000/api/cluster-intelligence")
        .then((res) => res.json())
        .then((data) => setClusterIntel(data))
        .catch((err) => console.error("Cluster intelligence error:", err));

      fetch("http://127.0.0.1:5000/api/operational-report")
        .then((res) => res.json())
        .then((data) => setOperationalReport(data))
        .catch((err) => console.error("Operational report error:", err));

      fetch("http://127.0.0.1:5000/api/feed-coverage")
        .then((res) => res.json())
        .then((data) => setFeedCoverage(data))
        .catch((err) => console.error("Feed coverage error:", err));

      fetch("http://127.0.0.1:5000/api/cyber-threats")
        .then((res) => res.json())
        .then((data) => setCyberThreats(data))
        .catch((err) => console.error("Cyber threat error:", err));

      fetch("http://127.0.0.1:5000/api/fusion-intelligence")
        .then((res) => res.json())
        .then((data) => setFusionIntel(data))
        .catch((err) => console.error("Fusion intelligence error:", err));

      fetch("http://127.0.0.1:5000/api/satellite-mismatch")
        .then((res) => res.json())
        .then((data) => setSatMismatch(data))
        .catch((err) => console.error("Satellite mismatch error:", err));

      fetch("http://127.0.0.1:5000/api/operational-briefing")
        .then((res) => res.json())
        .then((data) => setBriefing(data))
        .catch((err) => console.error("Operational briefing error:", err));

      fetch("http://127.0.0.1:5000/api/escalation-alerts")
        .then((res) => res.json())
        .then((data) => setEscalationAlerts(data))
        .catch((err) => console.error("Escalation alerts error:", err));

      fetch("http://127.0.0.1:5000/api/db/events?token=gods_eye_pacific_admin_2026")
        .then((res) => res.json())
        .then((data) => setDbEvents(data))
        .catch((err) => console.error("DB events error:", err));

      fetch("http://127.0.0.1:5000/api/cases?token=gods_eye_pacific_admin_2026")
        .then((res) => res.json())
        .then((data) => setCases(data))
        .catch((err) => console.error("Cases error:", err));

      fetch("http://127.0.0.1:5000/api/predictive-intelligence?test=1")
        .then((res) => res.json())
        .then((data) => setPredictiveIntel(data))
        .catch((err) => console.error("Predictive intelligence error:", err));
    };

    loadIntelStatus();
    const interval = setInterval(loadIntelStatus, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchRoute = async (id, vessel = null, rangeHours = historyRange) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:5000/api/vessels/${id}/history?limit=150&range_hours=${rangeHours}`
      );
      const data = await res.json();

      const points = (Array.isArray(data) ? data : [])
        .map((p) => ({
          lat: Number(p.lat),
          lon: Number(p.lon),
          course: Number(p.course),
        }))
        .filter((p) => !Number.isNaN(p.lat) && !Number.isNaN(p.lon));

      setRoute(points.map((p) => [p.lat, p.lon]));

      const recentCourses = points
        .slice(-3)
        .map((p) => p.course)
        .filter((c) => !Number.isNaN(c));

      let avgCourse = vessel ? Number(vessel.course) : NaN;
      if (recentCourses.length > 0) {
        avgCourse = recentCourses.reduce((sum, c) => sum + c, 0) / recentCourses.length;
      }

      const baseLat =
        points.length > 0 ? points[points.length - 1].lat : Number(vessel?.lat);
      const baseLon =
        points.length > 0 ? points[points.length - 1].lon : Number(vessel?.lon);
      const baseSpeed = Number(vessel?.speed);

      if (
        Number.isNaN(baseLat) ||
        Number.isNaN(baseLon) ||
        Number.isNaN(avgCourse) ||
        Number.isNaN(baseSpeed) ||
        baseSpeed < 1
      ) {
        setPrediction([]);
        return;
      }

      const distanceKm = (baseSpeed * 1.852) * (5 / 60);
      const predicted = projectPoint(baseLat, baseLon, avgCourse, distanceKm);

      if (isOnLand(predicted[0], predicted[1])) {
        setPrediction([]);
        return;
      }

      setPrediction([
        [baseLat, baseLon],
        predicted,
      ]);
    } catch (err) {
      console.error("Route fetch failed:", err);
      setRoute([]);
      setPrediction([]);
    }
  };


  useEffect(() => {
    if (selected && selectedType === "vessel" && selected.mmsi) {

      fetch(`http://127.0.0.1:5000/api/timeline/${selected.mmsi}`)
        .then((res) => res.json())
        .then((data) => {
          setTimelineData(data.timeline || []);
        })
        .catch((err) => {
          console.error("Timeline error:", err);
          setTimelineData([]);
        });

      fetch(`http://127.0.0.1:5000/api/network/${selected.mmsi}`)
        .then((res) => res.json())
        .then((data) => {
          setNetworkData(data || { zones: [], connections: [], events: [] });
        })
        .catch((err) => {
          console.error("Network error:", err);
          setNetworkData({ zones: [], connections: [], events: [] });
        });

      fetch(`http://127.0.0.1:5000/api/vessel-profile?token=gods_eye_pacific_admin_2026&mmsi=${selected.mmsi || selected.MMSI || selected.id || selected.name}`)
        .then((res) => res.json())
        .then((data) => setVesselProfile(data))
        .catch((err) => {
          console.error("Vessel profile error:", err);
          setVesselProfile(null);
        });

    } else {
      setTimelineData([]);
      setNetworkData({ zones: [], connections: [], events: [] });
      setVesselProfile(null);
    }
  }, [selected, selectedType]);

  useEffect(() => {

  fetch("http://127.0.0.1:5000/api/intel-summary")
    .then(res => res.json())
    .then(data => setIntelSummary(data))
    .catch(err => console.error("Intel summary error:", err));

    if (selected && selectedType === "vessel") {
      fetchRoute(selected.id, selected, historyRange);
    }
  }, [historyRange]);


  useEffect(() => {
    if (selected && selectedType === "vessel" && selected.mmsi) {

      fetch(`http://127.0.0.1:5000/api/timeline/${selected.mmsi}`)
        .then((res) => res.json())
        .then((data) => {
          setTimelineData(data.timeline || []);
        })
        .catch((err) => {
          console.error("Timeline error:", err);
          setTimelineData([]);
        });

      fetch(`http://127.0.0.1:5000/api/network/${selected.mmsi}`)
        .then((res) => res.json())
        .then((data) => {
          setNetworkData(data || { zones: [], connections: [], events: [] });
        })
        .catch((err) => {
          console.error("Network error:", err);
          setNetworkData({ zones: [], connections: [], events: [] });
        });

      fetch(`http://127.0.0.1:5000/api/vessel-profile?token=gods_eye_pacific_admin_2026&mmsi=${selected.mmsi || selected.MMSI || selected.id || selected.name}`)
        .then((res) => res.json())
        .then((data) => setVesselProfile(data))
        .catch((err) => {
          console.error("Vessel profile error:", err);
          setVesselProfile(null);
        });

    } else {
      setTimelineData([]);
      setNetworkData({ zones: [], connections: [], events: [] });
      setVesselProfile(null);
    }
  }, [selected, selectedType]);

  useEffect(() => {

  fetch("http://127.0.0.1:5000/api/intel-summary")
    .then(res => res.json())
    .then(data => setIntelSummary(data))
    .catch(err => console.error("Intel summary error:", err));

    if (followMode && selected && selectedType === "vessel") {
      fetchRoute(selected.id, selected, historyRange);
    }
  }, [selected, followMode]);

  const getRiskColor = (risk) => {
    if (risk === "Critical") return "purple";
    if (risk === "High") return "red";
    if (risk === "Elevated") return "orange";
    return "green";
  };

  const getAlertColor = (severity) => {
    const value = String(severity || "").toLowerCase();
    if (value === "high") return "red";
    if (value === "medium") return "orange";
    if (value === "low") return "yellow";
    return "deepskyblue";
  };

  const visibleVessels = useMemo(() => {
    let data = vessels
      .map((v) => ({
        ...v,
        lat: Number(v.lat),
        lon: Number(v.lon),
        speed: Number(v.speed) || 0,
        course: Number(v.course),
        heading: Number(v.heading),
        confidence: Number(v.confidence) || 0,
        correlation_score: Number(v.correlation_score) || 0,
      }))
      .filter((v) => Number.isFinite(v.lat) && Number.isFinite(v.lon) && v.lat >= -90 && v.lat <= 90 && v.lon >= -180 && v.lon <= 180);

    if (highRiskOnly) {
      data = data.filter((v) => ["High", "Critical"].includes(v.risk_level));
    }

    return data.slice(0, 100);
  }, [vessels, highRiskOnly]);

  const visibleAlerts = useMemo(() => {
    let data = alerts
      .map((a) => ({
        ...a,
        lat: Number(a.lat),
        lon: Number(a.lon),
      }))
      .filter((a) => Number.isFinite(a.lat) && Number.isFinite(a.lon) && a.lat >= -90 && a.lat <= 90 && a.lon >= -180 && a.lon <= 180);

    if (highRiskOnly) {
      data = data.filter((a) => String(a.severity || "").toLowerCase() === "high");
    }

    return data.slice(0, 100);
  }, [alerts, highRiskOnly]);

  const totalVisible =
    (showVessels ? visibleVessels.length : 0) +
    (showAlerts ? visibleAlerts.length : 0);

  const topThreats = [...visibleVessels]
    .filter((v) => ["High", "Critical"].includes(v.risk_level))
    .sort((a, b) => {
      const aScore = (a.anomaly_score || 0) + (a.correlation_score || 0);
      const bScore = (b.anomaly_score || 0) + (b.correlation_score || 0);
      return bScore - aScore;
    })
    .slice(0, 5);


  const submitCyberAlert = async () => {
    if (!cyberForm.title.trim()) {
      alert("Add a cyber alert title first.");
      return;
    }

    setCyberSubmitting(true);

    try {
      const res = await fetch("http://127.0.0.1:5000/api/add-cyber-alert?token=gods_eye_pacific_admin_2026", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: "UNVERIFIED",
          confidence: "LOW",
          type: cyberForm.type,
          title: cyberForm.title,
          target: cyberForm.target,
          zone: cyberForm.zone,
          risk: cyberForm.risk,
          indicator: cyberForm.indicator,
          summary: cyberForm.summary,
          recommended_action: cyberForm.recommended_action,
          verification_status: cyberForm.verification_status,
          confidence: cyberForm.confidence,
          observed_date: cyberForm.observed_date,
          source_url: cyberForm.source_url,
          evidence_file: cyberForm.evidence_file,
          analyst_name: cyberForm.analyst_name,
          analyst_note: cyberForm.analyst_note
        })
      });

      const data = await res.json();

      if (!data.ok) {
        alert("Failed to add cyber alert: " + (data.error || "Unknown error"));
        return;
      }

      setCyberThreats((prev) => ({
        total: (prev?.events?.length || 0) + 1,
        events: [data.added, ...(prev?.events || [])]
      }));

      setCyberForm({
        title: "",
        type: "MANUAL_OSINT",
        target: "",
        zone: "Suva Port",
        risk: "LOW",
        indicator: "",
        summary: "",
        recommended_action: "",
        verification_status: "UNVERIFIED",
        confidence: "LOW",
        observed_date: "",
        source_url: "",
        evidence_file: "",
        analyst_name: "NAYADRA Analyst",
        analyst_note: ""
      });

      alert("Cyber alert added.");
    } catch (err) {
      console.error("Cyber alert submit error:", err);
      alert("Cyber alert submit error.");
    } finally {
      setCyberSubmitting(false);
    }
  };



  const updateCyberStatus = async (alertId, newStatus) => {
    try {
      const res = await fetch("http://127.0.0.1:5000/api/update-cyber-alert-status?token=gods_eye_pacific_admin_2026", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: alertId,
          verification_status: newStatus,
          analyst_note: `Status changed to ${newStatus} from dashboard.`
        })
      });

      const data = await res.json();

      if (!data.ok) {
        alert("Status update failed: " + (data.error || "Unknown error"));
        return;
      }

      setCyberThreats((prev) => ({
        total: prev?.total || prev?.events?.length || 0,
        events: (prev?.events || []).map((item) =>
          item.id === alertId ? data.updated : item
        )
      }));
    } catch (err) {
      console.error("Cyber status update error:", err);
      alert("Cyber status update error.");
    }
  };


  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", width: "100%", background: "#0b1020" }}>
      <div style={{ flex: 3, position: "relative" }}>
        <div
          style={{
            position: "absolute",
            zIndex: 1000,
            top: 12,
            left: 12,
            background: "rgba(10,10,10,0.88)",
            color: "#fff",
            padding: "12px 14px",
            borderRadius: "12px",
            width: "180px",
            boxShadow: "0 4px 14px rgba(0,0,0,0.3)",
            fontSize: "14px",
          }}
        >
          <div style={{ fontWeight: "bold", marginBottom: "10px" }}>Phase 11 Controls</div>

          <label style={{ display: "block", marginBottom: "8px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={showVessels}
              onChange={() => setShowVessels((prev) => !prev)}
              style={{ marginRight: "8px" }}
            />
            Show vessels
          </label>

          <label style={{ display: "block", marginBottom: "8px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={showAlerts}
              onChange={() => setShowAlerts((prev) => !prev)}
              style={{ marginRight: "8px" }}
            />
            Show alerts
          </label>

          <label style={{ display: "block", marginBottom: "8px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={highRiskOnly}
              onChange={() => setHighRiskOnly((prev) => !prev)}
              style={{ marginRight: "8px" }}
            />
            High risk only
          </label>

          <label style={{ display: "block", marginBottom: "10px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={followMode}
              onChange={() => setFollowMode((prev) => !prev)}
              style={{ marginRight: "8px" }}
            />
            Follow selected vessel
          </label>

          <div style={{ marginBottom: "10px" }}>
            <div style={{ marginBottom: "4px" }}>History range</div>
            <select
              value={historyRange}
              onChange={(e) => setHistoryRange(e.target.value)}
              style={{
                width: "100%",
                padding: "6px 8px",
                borderRadius: "6px",
                border: "1px solid #333",
                background: "#111",
                color: "#fff",
              }}
            >
              <option value="1">Last 1 hour</option>
              <option value="6">Last 6 hours</option>
              <option value="24">Last 24 hours</option>
              <option value="48">Last 48 hours</option>
            </select>
          </div>

          <button
            onClick={() => {
              if (selected && selectedType === "vessel") {
                window.dispatchEvent(
                  new CustomEvent("locate-selected-vessel", {
                    detail: {
                      lat: Number(selected.lat),
                      lon: Number(selected.lon),
                    },
                  })
                );
              }
            }}
            style={{
              width: "100%",
              marginBottom: "10px",
              padding: "8px",
              borderRadius: "6px",
              border: "1px solid #333",
              background: "#111",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            Locate selected vessel
          </button>

          <div style={{ opacity: 0.9, marginBottom: "10px" }}>Visible items: {totalVisible}</div>

          <div style={{ marginTop: "10px", borderTop: "1px solid #333", paddingTop: "10px" }}>
            <div style={{ fontWeight: "bold", marginBottom: "6px" }}>Regional Jump</div>

            {[
              ["Fiji", -17.7134, 178.0650, 7],
              ["Samoa", -13.7590, -172.1046, 7],
              ["Tonga", -21.1790, -175.1982, 7],
              ["Vanuatu", -16.2902, 167.6924, 6],
              ["PNG", -6.3150, 143.9555, 5],
              ["Pacific", -15.0000, -170.0000, 4],
              ["French Polynesia", -17.6797, -149.4068, 5],
              ["Tahiti", -17.6509, -149.4260, 8],
              ["Marquesas", -9.0000, -140.0000, 6],
              ["Tuamotu", -18.0000, -142.0000, 5]
            ].map(([name, lat, lon, zoom]) => (
              <button
                key={name}
                onClick={() => {
                  setShouldFit(false);
                  window.dispatchEvent(new CustomEvent("locate-selected-vessel", {
                    detail: { lat, lon, zoom }
                  }));
                }}
                style={{
                  width: "100%",
                  margin: "2px",
                  padding: "6px",
                  borderRadius: "6px",
                  border: "1px solid #333",
                  background: "#111",
                  color: "#fff",
                  cursor: "pointer",
                  fontSize: "11px"
                }}
              >
                {name}
              </button>
            ))}
          </div>
        </div>

          <FloatingReportsPanel />
          <PatternReplayPanel />
        <MapContainer
          center={[-17.7134, 178.0650]}   // Fiji center
          zoom={7}
          scrollWheelZoom={true}
          style={{ height: "100vh", width: "100%" }}
         >

          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {showSentinel && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            opacity={0.95}
          />
        )}

          <BehavioralEventMarkers />
            <MapOverlays />
        <MapLegend />
        <LastUpdatedLabel />

        <FitToData
            vessels={showVessels ? visibleVessels : []}
            alerts={showAlerts ? visibleAlerts : []}
            shouldFit={shouldFit}
          />

          <FollowSelected
            selected={selected}
            selectedType={selectedType}
            followMode={followMode}
          />

          <LocateSelectedVessel />

          {showVessels &&
            visibleVessels.map((v) => {
              const movingLandAnomaly =
                isOnLand(v.lat, v.lon) && Number(v.speed) > 1;

                const vesselLat = Number(v.lat);
                const vesselLon = Number(v.lon);
                if (!Number.isFinite(vesselLat) || !Number.isFinite(vesselLon)) return null;
                const vesselPosition = [vesselLat, vesselLon];

              return (
                <CircleMarker
                    key={`vessel-${v.mmsi || v.id || String(v.lat) + "-" + String(v.lon)}`}
                    center={vesselPosition}
                  radius={
                    String(v.threat_level || "").toUpperCase() === "CRITICAL" ? 10 :
                    String(v.threat_level || "").toUpperCase() === "HIGH" ? 8 :
                    String(v.threat_level || "").toUpperCase() === "MEDIUM" ? 6 :
                    4
                  }
                  pathOptions={{
                    color: movingLandAnomaly ? "purple" :
                      String(v.threat_level || "").toUpperCase() === "CRITICAL" ? "#ff0000" :
                      String(v.threat_level || "").toUpperCase() === "HIGH" ? "#ff3333" :
                      String(v.threat_level || "").toUpperCase() === "MEDIUM" ? "#ffaa00" :
                      "#39ff14",
                    fillColor: movingLandAnomaly ? "purple" :
                      String(v.threat_level || "").toUpperCase() === "CRITICAL" ? "#ff0000" :
                      String(v.threat_level || "").toUpperCase() === "HIGH" ? "#ff3333" :
                      String(v.threat_level || "").toUpperCase() === "MEDIUM" ? "#ffaa00" :
                      "#39ff14",
                    fillOpacity: 1,
                    weight: String(v.threat_level || "").toUpperCase() === "CRITICAL" ? 4 : 2,
                  }}
                  eventHandlers={{
                    click: () => {
                      setSelected(v);
                      setSelectedType("vessel");
                      fetchRoute(v.id, v, historyRange);
                    },
                  }}
                >
                  <Popup>
                    <strong>{v.name || "Unknown Vessel"}</strong>
                    <br />
                    Type: {v.type || "Unknown"}
                    <br />
                    Speed: {v.speed ?? "N/A"} kn
                    <br />
                    Course: {Number.isNaN(v.course) ? "N/A" : v.course}
                    <br />
                    Heading: {Number.isNaN(v.heading) ? "N/A" : v.heading}
                    <br />
                    Last Seen: {v.lastSeen || "N/A"}
                    <br />
                    Confidence: {v.confidence}
                    <br />
                    Risk Level: {v.threat_level || v.risk_level}
                    <br />
                    Offender: {v.memory?.offender_status || "NEW"}
                    <br />
                    Repeat Score: {v.memory?.repeat_offender_score ?? 0}
                    <br />
                    Lat: {v.lat}
                    <br />
                    Lon: {v.lon}
                    <br />
                    Anomaly: {movingLandAnomaly ? "Yes" : "No"}
                  </Popup>
                </CircleMarker>
              );
            })}

          {showAlerts &&
            visibleAlerts.map((a) => (
              <CircleMarker
                key={`alert-${a.id}`}
                center={[-17.7134, 178.0650]}
                radius={4}
                pathOptions={{
                  color: getAlertColor(a.severity),
                  fillColor: getAlertColor(a.severity),
                  fillOpacity: 0.9,
                  weight: 1,
                }}
                eventHandlers={{
                  click: () => {
                    setSelected(a);
                    setSelectedType("alert");
                    setRoute([]);
                    setPrediction([]);
                  },
                }}
              >
                <Popup>
                  <strong>{a.name || "Alert"}</strong>
                  <br />
                  Type: {a.type || "Unknown"}
                  <br />
                  Severity: {a.severity || "N/A"}
                  <br />
                  Lat: {a.lat}
                  <br />
                  Lon: {a.lon}
                </Popup>
              </CircleMarker>
            ))}

          {route.length > 1 && (
            <Polyline positions={route} pathOptions={{ color: "blue", weight: 1 }} />
          )}

          {prediction.length > 1 && (
            <Polyline
              positions={prediction}
              pathOptions={{ color: "cyan", weight: 1, dashArray: "6, 6" }}
            />
          )}
        
{aisGaps.map((g, i) => (
  g.lat && g.lon && (
    <CircleMarker
      key={"gap-" + i}
      center={[-17.7134, 178.0650]}
      radius={4}
      pathOptions={{ color: "#ff0000", fillColor: "#ff0000", fillOpacity: 0.65 }}
    >
      <Tooltip permanent direction="top" offset={[0, -10]} className="dark-vessel-label">
        DARK AIS • {g.age_minutes} min
      </Tooltip>
    </CircleMarker>
  )
))}


{intelSummary && (
  <div style={{
    position: "absolute",
    top: "80px",
    right: "20px",
    background: "rgba(0,0,0,0.8)",
    padding: "10px",
    borderRadius: "8px",
    color: "white",
    width: "220px",
    zIndex: 1000
  }}>
    <h4>🧠 Intel Summary</h4>
    <div>Total: {intelSummary.total_vessels}</div>
    <div>High Risk: {intelSummary.high_risk}</div>
    <div>Medium: {intelSummary.medium_risk}</div>
    <div>Low: {intelSummary.low_risk}</div>
    <div>Stale: {intelSummary.stale_tracks}</div>
  </div>
)}

</MapContainer>
      </div>

      <div
        style={{
          flex: 1, width: "100%",
          background: "#0a0a0a",
          color: "#fff",
          
          overflowY: "auto",
          borderLeft: "1px solid #222",
        }}
      >
        <h2 style={{ marginTop: 0 }}>🧠 Intelligence Panel</h2>

        <div style={{
          border: "1px solid rgba(0, 255, 170, 0.35)",
          background: "rgba(0, 20, 30, 0.72)",
          borderRadius: "12px",
          padding: "12px",
          marginBottom: "14px",
          boxShadow: "0 0 14px rgba(0,255,170,0.12)"
        }}>
          <div style={{
            border: "1px solid rgba(0,255,170,0.35)",
            borderRadius: "10px",
            padding: "10px",
            marginBottom: "12px",
            background: "rgba(0,20,25,0.72)"
          }}>
            <div style={{ color: "#00ffaa", fontWeight: "bold", marginBottom: "6px" }}>
              Cyber Feed Health
            </div>
            <div style={{ fontSize: "12px", lineHeight: "1.45", color: "#d8f7ff" }}>
              <div><b>Status:</b> {cyberFeedHealth?.status || "UNKNOWN"}</div>
              <div><b>Source:</b> {cyberFeedHealth?.source || "OpenPhish scheduled feed"}</div>
              <div><b>Last Check:</b> {cyberFeedHealth?.last_check_at || "Not checked yet"}</div>
              <div><b>Last Added:</b> {cyberFeedHealth?.last_added ?? "N/A"}</div>
              <div><b>Last Skipped:</b> {cyberFeedHealth?.last_skipped ?? "N/A"}</div>
              <div><b>Total Alerts:</b> {cyberFeedHealth?.total_alerts ?? "N/A"}</div>
              <div><b>Log Exists:</b> {cyberFeedHealth?.log_exists ? "YES" : "NO"}</div>
              {cyberFeedHealth?.last_error && (
                <div style={{ color: "#ff6666", marginTop: "6px" }}>
                  <b>Error:</b> {cyberFeedHealth.last_error}
                </div>
              )}
            </div>
          </div>

          <h3 style={{ margin: "0 0 6px 0", color: "#00ffaa" }}>🛡️ Cyber Threat Feed</h3>
          <p style={{ margin: "0 0 10px 0", color: "#9fb7c2", fontSize: "12px" }}>
            Pacific cyber indicators linked to ports, agencies, scams and maritime activity.
          </p>


          <div style={{
            border: "1px solid rgba(0,255,170,0.2)",
            borderRadius: "10px",
            padding: "10px",
            margin: "10px 0",
            background: "rgba(0,0,0,0.22)"
          }}>
            <div style={{ color: "#00ffaa", fontWeight: "bold", marginBottom: "8px" }}>
              ➕ Add Manual Cyber Alert
            </div>

            <input
              placeholder="Title"
              value={cyberForm.title}
              onChange={(e) => setCyberForm({ ...cyberForm, title: e.target.value })}
              style={{ width: "100%", marginBottom: "6px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />

            <div style={{ display: "flex", gap: "6px", marginBottom: "6px" }}>
              <select
                value={cyberForm.type}
                onChange={(e) => setCyberForm({ ...cyberForm, type: e.target.value })}
                style={{ flex: 1, padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
              >
                <option value="MANUAL_OSINT">MANUAL_OSINT</option>
                <option value="PHISHING_URL">PHISHING_URL</option>
                <option value="FAKE_SOCIAL_PAGE">FAKE_SOCIAL_PAGE</option>
                <option value="BREACH_ALERT">BREACH_ALERT</option>
                <option value="SCAM_REPORT">SCAM_REPORT</option>
              </select>

              <select
                value={cyberForm.risk}
                onChange={(e) => setCyberForm({ ...cyberForm, risk: e.target.value })}
                style={{ width: "100px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
              </select>
            </div>

            <input
              placeholder="Target, e.g. Customs / port staff"
              value={cyberForm.target}
              onChange={(e) => setCyberForm({ ...cyberForm, target: e.target.value })}
              style={{ width: "100%", marginBottom: "6px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />

            <input
              placeholder="Zone, e.g. Suva Port"
              value={cyberForm.zone}
              onChange={(e) => setCyberForm({ ...cyberForm, zone: e.target.value })}
              style={{ width: "100%", marginBottom: "6px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />

            <input
              placeholder="Indicator, URL, domain, page name, email, etc."
              value={cyberForm.indicator}
              onChange={(e) => setCyberForm({ ...cyberForm, indicator: e.target.value })}
              style={{ width: "100%", marginBottom: "6px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />

            <textarea
              placeholder="Summary"
              value={cyberForm.summary}
              onChange={(e) => setCyberForm({ ...cyberForm, summary: e.target.value })}
              style={{ width: "100%", height: "55px", marginBottom: "6px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />


            <div style={{ display: "flex", gap: "6px", marginBottom: "6px" }}>
              <select
                value={cyberForm.verification_status}
                onChange={(e) => setCyberForm({ ...cyberForm, verification_status: e.target.value })}
                style={{ flex: 1, padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
              >
                <option value="UNVERIFIED">UNVERIFIED</option>
                <option value="UNDER_REVIEW">UNDER_REVIEW</option>
                <option value="VERIFIED">VERIFIED</option>
                <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
              </select>

              <select
                value={cyberForm.confidence}
                onChange={(e) => setCyberForm({ ...cyberForm, confidence: e.target.value })}
                style={{ width: "110px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
              </select>
            </div>

            <input
              type="date"
              value={cyberForm.observed_date}
              onChange={(e) => setCyberForm({ ...cyberForm, observed_date: e.target.value })}
              style={{ width: "100%", marginBottom: "6px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />

            <input
              placeholder="Source URL"
              value={cyberForm.source_url}
              onChange={(e) => setCyberForm({ ...cyberForm, source_url: e.target.value })}
              style={{ width: "100%", marginBottom: "6px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />

            <input
              placeholder="Evidence file name, e.g. screenshot_001.png"
              value={cyberForm.evidence_file}
              onChange={(e) => setCyberForm({ ...cyberForm, evidence_file: e.target.value })}
              style={{ width: "100%", marginBottom: "6px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />

            <input
              placeholder="Analyst name"
              value={cyberForm.analyst_name}
              onChange={(e) => setCyberForm({ ...cyberForm, analyst_name: e.target.value })}
              style={{ width: "100%", marginBottom: "6px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />

            <textarea
              placeholder="Analyst note"
              value={cyberForm.analyst_note}
              onChange={(e) => setCyberForm({ ...cyberForm, analyst_note: e.target.value })}
              style={{ width: "100%", height: "55px", marginBottom: "6px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />

            <textarea
              placeholder="Recommended action"
              value={cyberForm.recommended_action}
              onChange={(e) => setCyberForm({ ...cyberForm, recommended_action: e.target.value })}
              style={{ width: "100%", height: "55px", marginBottom: "8px", padding: "6px", background: "#061014", color: "#fff", border: "1px solid #135" }}
            />

            <button
              onClick={submitCyberAlert}
              disabled={cyberSubmitting}
              style={{
                width: "100%",
                padding: "8px",
                background: cyberSubmitting ? "#333" : "#003d2f",
                color: "#00ffaa",
                border: "1px solid #00ffaa",
                borderRadius: "8px",
                cursor: cyberSubmitting ? "not-allowed" : "pointer"
              }}
            >
              {cyberSubmitting ? "Adding..." : "Add Cyber Alert"}
            </button>
          </div>


          <div style={{ margin: "8px 0 10px 0" }}>
            <select
              value={cyberFilter}
              onChange={(e) => setCyberFilter(e.target.value)}
              style={{
                width: "100%",
                padding: "7px",
                background: "#061014",
                color: "#00ffaa",
                border: "1px solid rgba(0,255,170,0.5)",
                borderRadius: "8px"
              }}
            >
              <option value="ALL">ALL CYBER ALERTS</option>
              <option value="HIGH">HIGH RISK ONLY</option>
              <option value="VERIFIED">VERIFIED ONLY</option>
              <option value="UNVERIFIED">UNVERIFIED ONLY</option>
              <option value="UNDER_REVIEW">UNDER REVIEW ONLY</option>
              <option value="FALSE_POSITIVE">FALSE POSITIVE ONLY</option>
            </select>
          </div>

          <div style={{ margin: "8px 0 10px 0" }}>
            <select
              value={cyberSourceFilter}
              onChange={(e) => setCyberSourceFilter(e.target.value)}
              style={{
                width: "100%",
                padding: "7px",
                background: "#061014",
                color: "#00ffaa",
                border: "1px solid rgba(0,255,170,0.5)",
                borderRadius: "8px"
              }}
            >
              <option value="ALL">ALL SOURCES</option>
              <option value="OPENPHISH_FEED">OPENPHISH FEED</option>
              <option value="MANUAL">MANUAL OSINT / SCAM REPORTS</option>
              <option value="DEMO">DEMO / TEST DATA</option>
            </select>
          </div>

          <div style={{ marginBottom: "10px", color: "#ffffff", fontSize: "13px" }}>
            Total Cyber Alerts: <strong>{cyberThreats?.events?.length ?? cyberThreats?.total ?? 0}</strong><br/>
            Visible Cyber Alerts: <strong>{
              (cyberThreats?.events || []).filter((item) => {
                const statusMatch =
                  cyberFilter === "ALL" ||
                  (cyberFilter === "HIGH" && item.risk === "HIGH") ||
                  ((item.verification_status || item.status) === cyberFilter);

                const sourceMatch =
                  cyberSourceFilter === "ALL" ||
                  (cyberSourceFilter === "OPENPHISH_FEED" && item.type === "OPENPHISH_FEED") ||
                  (cyberSourceFilter === "MANUAL" && item.type !== "OPENPHISH_FEED" && item.status !== "DEMO") ||
                  (cyberSourceFilter === "DEMO" && (item.status === "DEMO" || item.confidence === "TEST DATA"));

                return statusMatch && sourceMatch;
              }).length
            }</strong>
          </div>

          {(cyberThreats?.events || []).length === 0 ? (
            <div style={{ color: "#9fb7c2", fontSize: "12px" }}>No cyber alerts loaded.</div>
          ) : (
            (cyberThreats?.events || [])
              .filter((item) => {
                const statusMatch =
                  cyberFilter === "ALL" ||
                  (cyberFilter === "HIGH" && item.risk === "HIGH") ||
                  ((item.verification_status || item.status) === cyberFilter);

                const sourceMatch =
                  cyberSourceFilter === "ALL" ||
                  (cyberSourceFilter === "OPENPHISH_FEED" && item.type === "OPENPHISH_FEED") ||
                  (cyberSourceFilter === "MANUAL" && item.type !== "OPENPHISH_FEED" && item.status !== "DEMO") ||
                  (cyberSourceFilter === "DEMO" && (item.status === "DEMO" || item.confidence === "TEST DATA"));

                return statusMatch && sourceMatch;
              })
              .slice(0, 8)
              .map((item, idx) => (
              <div key={item.id || idx} style={{
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: "10px",
                padding: "10px",
                marginBottom: "8px",
                background: "rgba(0,0,0,0.28)"
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
                  <strong style={{ color: "#ffffff", fontSize: "13px" }}>
                    {item.title || "Untitled cyber alert"}
                  </strong>
                  <span style={{
                    color: item.risk === "HIGH" ? "#ff4d4d" : item.risk === "MEDIUM" ? "#ffcc00" : "#66ff99",
                    border: "1px solid currentColor",
                    borderRadius: "999px",
                    padding: "2px 8px",
                    fontSize: "11px",
                    whiteSpace: "nowrap"
                  }}>
                    {item.risk || "UNKNOWN"}
                  </span>
                </div>

                <div style={{ color: "#9fb7c2", fontSize: "11px", marginTop: "4px" }}>
                  {item.status || "LIVE"} · {item.type || "CYBER_ALERT"} · Zone: {item.zone || "N/A"} · Target: {item.target || "N/A"}
                </div>

                <div style={{ color: "#dbeafe", fontSize: "12px", marginTop: "6px" }}>
                  {item.summary || "No summary available."}
                </div>

                <div style={{ color: "#ffffff", fontSize: "12px", marginTop: "6px" }}>
                  <strong>Action:</strong> {item.recommended_action || "Review and verify."}
                </div>

                <div style={{ marginTop: "8px" }}>
                  
                <details style={{
                  marginTop: "10px",
                  border: "1px solid rgba(0,255,170,0.35)",
                  borderRadius: "8px",
                  padding: "8px",
                  background: "rgba(0,20,25,0.65)"
                }}>
                  <summary style={{ color: "#00ffaa", cursor: "pointer", fontWeight: "bold" }}>
                    Evidence Pack
                  </summary>
                  <div style={{ marginTop: "8px", fontSize: "12px", lineHeight: "1.45", color: "#d8f7ff" }}>
                    <div><b>Alert ID:</b> {item.id || "N/A"}</div>
                    <div><b>Source:</b> {item.source || "N/A"}</div>
                    <div><b>Type:</b> {item.type || "N/A"}</div>
                    <div><b>Indicator:</b> {item.indicator || "N/A"}</div>
                    <div><b>Source URL:</b> {item.source_url || "N/A"}</div>
                    <div><b>Evidence File:</b> {item.evidence_file || "N/A"}</div>
                    <div><b>Observed Date:</b> {item.observed_date || "N/A"}</div>
                    <div><b>Analyst:</b> {item.analyst_name || "NAYADRA Analyst"}</div>
                    <div><b>Status:</b> {item.verification_status || item.status || "UNVERIFIED"}</div>
                    <div><b>Last Reviewed:</b> {item.last_reviewed_at || "Not reviewed"}</div>
                    <div><b>Analyst Note:</b> {item.analyst_note || "No analyst note recorded."}</div>
                    <div style={{ marginTop: "8px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.15)" }}>
                      <b>Safe Handling Checklist:</b>
                      <ul style={{ marginTop: "5px", paddingLeft: "18px" }}>
                        <li>Do not visit suspicious links directly.</li>
                        <li>Preserve URL, screenshots, timestamps and source context.</li>
                        <li>Verify before escalation.</li>
                        <li>Only mark VERIFIED after independent confirmation.</li>
                      </ul>
                    </div>
                  </div>
                </details>

                  <select
                    value={item.verification_status || item.status || "UNVERIFIED"}
                    onChange={(e) => updateCyberStatus(item.id, e.target.value)}
                    style={{
                      width: "100%",
                      padding: "6px",
                      background: "#061014",
                      color: "#00ffaa",
                      border: "1px solid rgba(0,255,170,0.5)",
                      borderRadius: "6px"
                    }}
                  >
                    <option value="UNVERIFIED">UNVERIFIED</option>
                    <option value="UNDER_REVIEW">UNDER_REVIEW</option>
                    <option value="VERIFIED">VERIFIED</option>
                    <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
                  </select>
                </div>
              </div>
            ))
          )}
        </div>


          {selected && selectedType === "vessel" && (
            <div style={{
              background: "#020617",
              border: "1px solid #38bdf8",
              borderRadius: "12px",
              padding: "12px",
              marginBottom: "14px",
              boxShadow: "0 0 18px rgba(56,189,248,0.18)",
              fontSize: "13px"
            }}>
              <h3 style={{ marginTop: 0, color: "#38bdf8" }}>🎯 Target Vessel Intelligence Profile</h3>

              {!vesselProfile && <div style={{ opacity: 0.8 }}>Loading vessel profile...</div>}

              {vesselProfile && vesselProfile.error && (
                <div style={{
                  background: "#451a03",
                  border: "1px solid #f97316",
                  borderRadius: "8px",
                  padding: "8px",
                  color: "#fed7aa"
                }}>
                  <b>Profile status:</b> {vesselProfile.message || vesselProfile.error}
                </div>
              )}

              {vesselProfile && !vesselProfile.error && (
                <>
                  <div><b>Name:</b> {vesselProfile.name || selected.name || selected.shipname || "Unknown"}</div>
                  <div><b>MMSI:</b> {vesselProfile.mmsi || selected.mmsi || "Unknown"}</div>
                  <div><b>Zone:</b> {vesselProfile.zone || selected.zone || "Unknown"}</div>
                  <div><b>Speed:</b> {vesselProfile.speed ?? selected.speed ?? 0} kn</div>
                  <div><b>Course:</b> {vesselProfile.course ?? selected.course ?? selected.heading ?? "Unknown"}</div>

                  <div style={{
                    marginTop: "10px",
                    padding: "10px",
                    borderRadius: "10px",
                    background:
                      String(vesselProfile.risk_level || "").toLowerCase() === "high" ? "#7f1d1d" :
                      String(vesselProfile.risk_level || "").toLowerCase() === "medium" ? "#78350f" :
                      "#064e3b",
                    border: "1px solid rgba(255,255,255,0.18)"
                  }}>
                    <div><b>Risk Level:</b> {vesselProfile.risk_level || "Unknown"}</div>
                    <div><b>Risk Score:</b> {vesselProfile.risk_score ?? 0}</div>
                    <div><b>Track Status:</b> {vesselProfile.track_status || "Unknown"}</div>
                  </div>

                  <div style={{ marginTop: "10px" }}>
                    <b>Recommendation:</b> {vesselProfile.recommendation || "Review vessel activity"}
                  </div>

                  <div><b>Flags:</b> {
                    Array.isArray(vesselProfile.flags) && vesselProfile.flags.length
                      ? vesselProfile.flags.join(", ")
                      : "None"
                  }</div>

                  <div style={{
                    marginTop: "12px",
                    padding: "10px",
                    borderRadius: "10px",
                    background: "#0f172a",
                    border: "1px solid #64748b"
                  }}>
                    <h4 style={{ margin: "0 0 8px 0", color: "#93c5fd" }}>
                      🌐 External Validation
                    </h4>

                    <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "8px" }}>
                      Use these sources to manually validate vessel identity, current position, and possible AIS mismatch.
                    </div>

                    <div style={{ display: "grid", gap: "6px" }}>
                      <a
                        href={`https://www.marinetraffic.com/en/ais/index/search/all?keyword=${encodeURIComponent(vesselProfile.mmsi || vesselProfile.name || "")}`}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: "#38bdf8" }}
                      >
                        Open MarineTraffic search
                      </a>

                      <a
                        href={`https://www.vesselfinder.com/vessels/details/${encodeURIComponent(vesselProfile.mmsi || "")}`}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: "#38bdf8" }}
                      >
                        Open VesselFinder MMSI search
                      </a>

                      <a
                        href={`https://www.myshiptracking.com/vessels?name=${encodeURIComponent(vesselProfile.name || vesselProfile.mmsi || "")}`}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: "#38bdf8" }}
                      >
                        Open MyShipTracking search
                      </a>

                      <a
                        href="https://globalfishingwatch.org/map/"
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: "#38bdf8" }}
                      >
                        Open Global Fishing Watch map
                      </a>
                    </div>

                    <div style={{
                      marginTop: "10px",
                      padding: "8px",
                      borderRadius: "8px",
                      background: "#020617",
                      border: "1px solid #334155"
                    }}>
                      <div style={{ fontWeight: "bold", color: "#facc15", marginBottom: "6px" }}>
                        Analyst Validation
                      </div>

                      <label style={{ display: "block", fontSize: "12px", marginBottom: "4px" }}>
                        Validation Status
                      </label>

                      <select
                        value={validationStatus}
                        onChange={(e) => {
                          setValidationStatus(e.target.value);
                          setValidationSaved(false);
                        }}
                        style={{
                          width: "100%",
                          background: "#0f172a",
                          color: "white",
                          border: "1px solid #475569",
                          borderRadius: "6px",
                          padding: "6px",
                          marginBottom: "8px"
                        }}
                      >
                        <option value="Pending">Pending</option>
                        <option value="Confirmed">Confirmed</option>
                        <option value="Mismatch">Mismatch</option>
                        <option value="Escalated">Escalated</option>
                      </select>

                      <label style={{ display: "block", fontSize: "12px", marginBottom: "4px" }}>
                        Analyst Note
                      </label>

                      <textarea
                        value={analystNote}
                        onFocus={() => setIsEditingNote(true)}
                        onBlur={() => setIsEditingNote(false)}
                        onClick={(e) => e.stopPropagation()}
                        onMouseDown={(e) => e.stopPropagation()}
                        onKeyDown={(e) => e.stopPropagation()}
                        onChange={(e) => {
                          setAnalystNote(e.target.value);
                          setValidationSaved(false);
                        }}
                        placeholder="Example: MarineTraffic shows vessel docked, but AISStream position appears stale/offshore."
                        rows={4}
                        style={{
                          width: "100%",
                          minHeight: "90px",
                          background: "#0f172a",
                          color: "white",
                          border: "1px solid #475569",
                          borderRadius: "6px",
                          padding: "8px",
                          resize: "vertical",
                          pointerEvents: "auto",
                          userSelect: "text",
                          boxSizing: "border-box"
                        }}
                      />

                      <button
                        onClick={() => {
                          const key = `nayadra_validation_${vesselProfile.mmsi || vesselProfile.name || "unknown"}`;
                          localStorage.setItem(key, JSON.stringify({
                            status: validationStatus,
                            note: analystNote,
                            saved_at: new Date().toISOString(),
                            vessel: vesselProfile.name || "Unknown",
                            mmsi: vesselProfile.mmsi || "Unknown"
                          }));

                          fetch("http://127.0.0.1:5000/api/case-notes", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                              token: "gods_eye_pacific_admin_2026",
                              name: vesselProfile.name || "Unknown",
                              mmsi: vesselProfile.mmsi || "Unknown",
                              zone: vesselProfile.zone || "Unknown",
                              risk_level: vesselProfile.risk_level || "Unknown",
                              risk_score: vesselProfile.risk_score ?? 0,
                              track_status: vesselProfile.track_status || "Unknown",
                              validation_status: validationStatus,
                              analyst_note: analystNote,
                              recommendation: vesselProfile.recommendation || "Review vessel activity",
                              source: vesselProfile.source || "NAYADRA pilot intelligence engine"
                            })
                          })
                            .then((r) => r.json())
                            .then((data) => {
                              console.log("Backend case note saved:", data);
                              setValidationSaved(true);
                            })
                            .catch((err) => {
                              console.error("Backend case note save failed:", err);
                              setValidationSaved(true);
                            });
                        }}
                        style={{
                          marginTop: "8px",
                          width: "100%",
                          background: "#0369a1",
                          color: "white",
                          border: "1px solid #38bdf8",
                          borderRadius: "6px",
                          padding: "7px",
                          cursor: "pointer",
                          fontWeight: "bold"
                        }}
                      >
                        Save Validation Note
                      </button>

                      <div style={{
                        marginTop: "8px",
                        fontSize: "12px",
                        color:
                          validationStatus === "Escalated" ? "#f87171" :
                          validationStatus === "Mismatch" ? "#fb923c" :
                          validationStatus === "Confirmed" ? "#4ade80" :
                          "#facc15"
                      }}>
                        Status: {validationStatus}
                        {validationSaved ? " — saved" : ""}
                      </div>

                      <button
                        onClick={() => {
                          const note = `NAYADRA Vessel Intelligence Case Note

Target: ${vesselProfile.name || "Unknown"}
MMSI: ${vesselProfile.mmsi || "Unknown"}
Zone: ${vesselProfile.zone || "Unknown"}
Position: ${vesselProfile.lat || "N/A"}, ${vesselProfile.lon || "N/A"}
Speed: ${vesselProfile.speed ?? "N/A"} kn
Course: ${vesselProfile.course ?? "N/A"}

Risk Level: ${vesselProfile.risk_level || "Unknown"}
Risk Score: ${vesselProfile.risk_score ?? 0}
Track Status: ${vesselProfile.track_status || "Unknown"}
Flags: ${(vesselProfile.flags || []).join(", ") || "None"}

External Validation Status: ${validationStatus}

Analyst Note:
${analystNote || "No analyst note entered."}

Recommended Action:
${vesselProfile.recommendation || "Review vessel activity."}

Source:
${vesselProfile.source || "NAYADRA local intelligence engine"}

Generated:
${new Date().toISOString()}`;

                          setCaseNote(note);
                          try {
                            navigator.clipboard.writeText(note);
                          } catch (e) {
                            console.error("Clipboard copy failed:", e);
                          }
                        }}
                        style={{
                          marginTop: "8px",
                          width: "100%",
                          background: "#14532d",
                          color: "white",
                          border: "1px solid #22c55e",
                          borderRadius: "6px",
                          padding: "7px",
                          cursor: "pointer",
                          fontWeight: "bold"
                        }}
                      >
                        Generate Case Note
                      </button>

                      {caseNote && (
                        <>
                          <button
                            onClick={async () => {
                              let logoDataUrl = "/nayadra-logo.png";

                              try {
                                const logoResponse = await fetch("/nayadra-logo.png");
                                const logoBlob = await logoResponse.blob();
                                logoDataUrl = await new Promise((resolve) => {
                                  const reader = new FileReader();
                                  reader.onloadend = () => resolve(reader.result);
                                  reader.readAsDataURL(logoBlob);
                                });
                              } catch (e) {
                                console.error("Logo embed failed:", e);
                              }

                              const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>NAYADRA Vessel Intelligence Case Note</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #ffffff;
      color: #111827;
      padding: 32px;
      line-height: 1.5;
    }
    .header {
      border-bottom: 3px solid #0f172a;
      padding-bottom: 12px;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    .header-text {
      flex: 1;
    }
    .report-logo {
      width: 105px;
      max-height: 105px;
      object-fit: contain;
    }
    .title {
      font-size: 24px;
      font-weight: bold;
      color: #0f172a;
    }
    .subtitle {
      color: #475569;
      margin-top: 4px;
    }
    .risk {
      border: 2px solid #92400e;
      background: #fffbeb;
      padding: 12px;
      border-radius: 8px;
      margin: 16px 0;
    }
    pre {
      white-space: pre-wrap;
      font-family: Arial, sans-serif;
      font-size: 14px;
    }
    .footer {
      margin-top: 24px;
      font-size: 12px;
      color: #64748b;
      border-top: 1px solid #cbd5e1;
      padding-top: 10px;
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="header-text">
      <div class="title">NAYADRA Vessel Intelligence Case Note</div>
      <div class="subtitle">Pacific Maritime Monitoring Pilot | Generated ${new Date().toISOString()}</div>
    </div>
    <img class="report-logo" src="${logoDataUrl}" alt="NAYADRA logo" />
  </div>

  <div class="risk">
    <b>Target:</b> ${vesselProfile.name || "Unknown"}<br/>
    <b>MMSI:</b> ${vesselProfile.mmsi || "Unknown"}<br/>
    <b>Risk:</b> ${vesselProfile.risk_level || "Unknown"} / ${vesselProfile.risk_score ?? 0}<br/>
    <b>Status:</b> ${vesselProfile.track_status || "Unknown"}<br/>
    <b>External Validation:</b> ${validationStatus}
  </div>

  <pre>${caseNote.replace(/[<>&]/g, c => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]))}</pre>

  <div class="footer">
    Generated by NAYADRA / God’s Eye pilot dashboard. Analyst validation required before operational action.
  </div>
</body>
</html>`;

                              const blob = new Blob([html], { type: "text/html" });
                              const url = URL.createObjectURL(blob);
                              const a = document.createElement("a");
                              a.href = url;
                              a.download = `NAYADRA_Case_Note_${vesselProfile.mmsi || vesselProfile.name || "vessel"}.html`;
                              document.body.appendChild(a);
                              a.click();
                              document.body.removeChild(a);
                              URL.revokeObjectURL(url);
                            }}
                            style={{
                              marginTop: "8px",
                              width: "100%",
                              background: "#7c2d12",
                              color: "white",
                              border: "1px solid #fb923c",
                              borderRadius: "6px",
                              padding: "7px",
                              cursor: "pointer",
                              fontWeight: "bold"
                            }}
                          >
                            Export Case Report
                          </button>

                          <textarea
                            value={caseNote}
                            readOnly
                            rows={10}
                            onClick={(e) => {
                              e.stopPropagation();
                              e.target.select();
                            }}
                            style={{
                              marginTop: "8px",
                              width: "100%",
                              background: "#020617",
                              color: "#e5e7eb",
                              border: "1px solid #22c55e",
                              borderRadius: "6px",
                              padding: "8px",
                              fontSize: "12px",
                              boxSizing: "border-box"
                            }}
                          />
                        </>
                      )}
                    </div>
                  </div>

                  <div style={{ opacity: 0.75, marginTop: "6px" }}>
                    Source: {vesselProfile.source || "Local intelligence engine"}
                  </div>

                  <div style={{
                    marginTop: "12px",
                    padding: "10px",
                    borderRadius: "10px",
                    background: "#111827",
                    border: "1px solid #818cf8"
                  }}>
                    <h4 style={{ margin: "0 0 8px 0", color: "#a5b4fc" }}>
                      📁 Case History
                    </h4>

                    {caseHistory.length === 0 && (
                      <div style={{ fontSize: "12px", opacity: 0.75 }}>
                        No saved case notes for this vessel yet.
                      </div>
                    )}

                    {caseHistory.slice().reverse().slice(0, 5).map((c, i) => (
                      <div
                        key={c.case_id || i}
                        style={{
                          background: "#020617",
                          border: "1px solid #475569",
                          borderRadius: "8px",
                          padding: "8px",
                          marginBottom: "8px",
                          fontSize: "12px"
                        }}
                      >
                        <b>{c.case_id || "CASE"}</b><br/>
                        <b>Status:</b> {c.validation_status || "Pending"}<br/>
                        <b>Risk:</b> {c.risk_level || "Unknown"} / {c.risk_score ?? 0}<br/>
                        <b>Track:</b> {c.track_status || "Unknown"}<br/>
                        <b>Saved:</b> {c.created_at || "Unknown"}<br/>
                        <div style={{ marginTop: "6px", opacity: 0.9 }}>
                          {c.analyst_note || "No analyst note."}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}


        <div style={{ marginBottom: "16px", fontSize: "14px", opacity: 0.9 }}>
          <div>Vessels: {loadingVessels ? "Loading..." : visibleVessels.length}</div>
          <div>
            Unique positions: {
              new Set(
                visibleVessels.map(v =>
                  `${Number(v.lat).toFixed(3)},${Number(v.lon).toFixed(3)}`
                )
              ).size
            }
          </div>
          <div>
            Overlapping/clustered: {
              Math.max(
                0,
                visibleVessels.length -
                new Set(
                  visibleVessels.map(v =>
                    `${Number(v.lat).toFixed(3)},${Number(v.lon).toFixed(3)}`
                  )
                ).size
              )
            }
          </div>
          <div>Alerts: {loadingAlerts ? "Loading..." : visibleAlerts.length}</div>
        </div>

        <hr style={{ borderColor: "#222", margin: "16px 0" }} />
          <h3 style={{ marginTop: 0 }}>🔥 Top Threats</h3>
          {visibleVessels
            .filter((v) => (Number(v.threat_score || v.risk || 0) > 0) || String(v.threat_level || "").toUpperCase() !== "LOW")
            .sort((a, b) => Number(b.threat_score || b.risk || 0) - Number(a.threat_score || a.risk || 0))
            .slice(0, 5)
            .map((v, i) => (
              <div
                key={v.id || v.mmsi || i}
                onClick={() => {
                  setSelected(v);
                  setSelectedType("vessel");
                  if (v.lat && v.lon) {
                    window.dispatchEvent(new CustomEvent("locate-selected-vessel", {
                      detail: { lat: v.lat, lon: v.lon }
                    }));
                  }
                }}
                style={{
                  background: "#1a0000",
                  border: "1px solid #ff4444",
                  padding: "8px",
                  marginBottom: "6px",
                  borderRadius: "6px",
                  fontSize: "11px",
                  cursor: "pointer"
                }}
              >
                <b>{i + 1}. {v.name || v.ship_name || v.mmsi || "Unknown Vessel"}</b><br/>
                Threat: {v.threat_score || v.risk || 0} / {v.threat_level || v.risk_level || "Unknown"}<br/>
                Offender: {v.memory?.offender_status || "NEW"} ({v.memory?.repeat_offender_score ?? 0})<br/>
                Speed: {v.speed ?? "?"} kn<br/>
                Flags: {formatFlags(v.threat_reasons || v.risk_flags || v.anomaly_flags)}
              </div>
            ))}

          {visibleVessels.filter((v) => (Number(v.threat_score || v.risk || 0) > 0) || String(v.threat_level || "").toUpperCase() !== "LOW").length === 0 && (
            <div style={{ fontSize: "12px", opacity: 0.7, marginBottom: "12px" }}>
              No active high-threat vessels detected.
            </div>
          )}

          <h4 style={{ color: "#ffaa00", marginTop: "12px" }}>🧭 Route Intelligence</h4>
          {routeIntel.length === 0 && (
            <div style={{ fontSize: "12px", opacity: 0.7 }}>No route activity</div>
          )}
          {routeIntel.slice(0,5).map((r, i) => (
            <div key={i} style={{
              background: "#1a1a00",
              border: "1px solid #ffaa00",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px",
              cursor: "pointer"
            }}>
              <b>{r.name}</b><br/>
              Score: {r.score} ({r.severity})<br/>
              {r.indicators?.[0]}
            </div>
          ))}

          <h4 style={{ color: "#00d4ff", marginTop: "14px" }}>🕒 Loitering Monitor</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Tracking: {loiterStatus?.total_monitored || 0}
          </div>
          {(loiterStatus?.loitering || []).slice(0,5).map((l, i) => (
            <div key={i} style={{
              background: "#001a22",
              border: "1px solid #00d4ff",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{l.status}</b><br/>
              MMSI: {l.mmsi}<br/>
              Time: {l.loiter_minutes} / {l.alert_threshold_minutes} min
            </div>
          ))}

          <h4 style={{ color: "#ff66cc", marginTop: "14px" }}>🤝 Rendezvous Monitor</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Pairs tracking: {rendezvousStatus?.total_pairs_monitored || 0}
          </div>
          {(rendezvousStatus?.rendezvous || []).slice(0,5).map((r, i) => (
            <div key={i} style={{
              background: "#220018",
              border: "1px solid #ff66cc",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{r.status}</b> — {r.severity || "MONITORING"}<br/>
              {r.vessel_a} ↔ {r.vessel_b}<br/>
              Score: {r.rendezvous_score ?? 0}<br/>
              Distance: {r.distance_km} km<br/>
              Time: {r.minutes_close} / {r.alert_threshold_minutes} min<br/>
              Zone: {r.zone || "Open Water"}<br/>
              Indicators: {formatFlags(r.indicators)}
            </div>
          ))}

          <h4 style={{ color: "#ffcc00", marginTop: "14px" }}>🔮 Predictive Intelligence</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Predicted sectors: {predictiveIntel?.total_predictions || 0}
          </div>
          {(predictiveIntel?.predictions || []).slice(0,5).map((p, i) => (
            <div key={i} style={{
              background: "#1f1800",
              border: "1px solid #ffcc00",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{p.severity}</b> — Score {p.prediction_score}<br/>
              Sector: {p.sector}<br/>
              Forecast: {p.forecast}<br/>
              Threat: {p.threat_activity} | Dark: {p.dark_activity} | Rendezvous: {p.rendezvous_activity}
            </div>
          ))}

          <h4 style={{ color: "#ffaa66", marginTop: "14px" }}>🗂 Investigation Cases</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Active cases: {(cases?.cases || []).length}
          </div>

          {(cases?.cases || []).slice(0,5).map((c, i) => (
            <div
              key={i}
              onClick={() => {
                fetch(`http://127.0.0.1:5000/api/cases/zone?token=gods_eye_pacific_admin_2026&zone=${encodeURIComponent(c.zone)}`)
                  .then((res) => res.json())
                  .then((z) => {
                    if (z.lat && z.lon) {
                      setShouldFit(false);
                      window.dispatchEvent(new CustomEvent("locate-selected-vessel", {
                        detail: { lat: z.lat, lon: z.lon, zoom: z.zoom || 10 }
                      }));
                    }
                  })
                  .catch((err) => console.error("Case zone jump error:", err));
              }}
              style={{
              background: "#1a1208",
              border: "1px solid #ffaa66",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{c.case_id}</b> — {c.priority}<br/>
              {c.title}<br/>
              Zone: {c.zone}<br/>
              Status: {c.status}<br/>
              Linked MMSI: {c.linked_mmsi || "None"}<br/>
              <span style={{ opacity: 0.75 }}>{c.notes}</span>
            </div>
          ))}

          <h4 style={{ color: "#bbbbff", marginTop: "14px" }}>🗄 Persistent Event Log</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Stored events: {(dbEvents?.events || []).length}
          </div>
          {(dbEvents?.events || []).slice(0,5).map((e, i) => (
            <div key={i} style={{
              background: "#0b0b22",
              border: "1px solid #8888ff",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{e.severity}</b> — {e.event_type}<br/>
              Zone: {e.zone}<br/>
              {e.message}<br/>
              <span style={{ opacity: 0.65 }}>{e.timestamp}</span>
            </div>
          ))}

          <h4 style={{ color: "#ff3333", marginTop: "14px" }}>🚨 Escalation Alerts</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Active escalations: {escalationAlerts?.total_alerts || 0}
          </div>
          {(escalationAlerts?.alerts || []).slice(0,5).map((a, i) => (
            <div key={i} style={{
              background: "#260606",
              border: "1px solid #ff3333",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{a.severity}</b> — {a.type}<br/>
              {a.message}<br/>
              <span style={{ opacity: 0.65 }}>{a.timestamp}</span>
            </div>
          ))}

          <h4 style={{ color: "#ffffff", marginTop: "14px" }}>📝 Operational Briefing</h4>
          {briefing && (
            <div style={{
              background: "#111827",
              border: "1px solid #ffffff",
              padding: "8px",
              marginBottom: "8px",
              borderRadius: "8px",
              fontSize: "12px"
            }}>
              <b>Threat Level: {briefing.threat_level}</b><br/>
              <br/>
              {briefing.summary}<br/>
              <br/>
              <b>Recommendation:</b><br/>
              {briefing.recommendation}
            </div>
          )}

          <h4 style={{ color: "#66ccff", marginTop: "14px" }}>🛰 Satellite/AIS Mismatch</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Mismatches: {satMismatch?.total_mismatches || 0}
          </div>
          {(satMismatch?.mismatches || []).slice(0,5).map((m, i) => (
            <div key={i} style={{
              background: "#06131f",
              border: "1px solid #66ccff",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{m.severity}</b> — {m.zone}<br/>
              Satellite visible: {m.satellite_visible}<br/>
              AIS contacts: {m.ais_contacts}<br/>
              {m.assessment}<br/>
              <span style={{ opacity: 0.75 }}>{m.recommendation}</span><br/>

              <button
                onClick={() => {
                  fetch("http://127.0.0.1:5000/api/cases/create-suva-mismatch?token=gods_eye_pacific_admin_2026")
                    .then((res) => res.json())
                    .then(() => {
                      return fetch("http://127.0.0.1:5000/api/cases?token=gods_eye_pacific_admin_2026");
                    })
                    .then((res) => res.json())
                    .then((data) => setCases(data))
                    .catch((err) => console.error("Create case error:", err));
                }}
                style={{
                  marginTop: "6px",
                  width: "100%",
                  padding: "6px",
                  borderRadius: "6px",
                  border: "1px solid #66ccff",
                  background: "#0b2233",
                  color: "white",
                  cursor: "pointer",
                  fontSize: "11px"
                }}
              >
                Create Investigation Case
              </button>
            </div>
          ))}

          <h4 style={{ color: "#ffaa00", marginTop: "14px" }}>🧠 Fusion Intelligence</h4>
          {fusionIntel && (
            <div style={{
              background: "#1f1400",
              border: fusionIntel.regional_threat_level === "LOW" ? "1px solid #00ffaa" : "1px solid #ffaa00",
              padding: "8px",
              marginBottom: "8px",
              borderRadius: "8px",
              fontSize: "12px"
            }}>
              <b>Regional Threat Level: {fusionIntel.regional_threat_level}</b><br/>
              Fusion Score: {fusionIntel.fusion_score}<br/>
              Maritime High Risk: {fusionIntel.maritime_high_risk}<br/>
              Dark Activity: {fusionIntel.dark_activity}<br/>
              Repeat Offenders: {fusionIntel.repeat_offenders}<br/>
              Cyber Events: {fusionIntel.cyber_events}<br/>
              <br/>
              {fusionIntel.recommendation}
            </div>
          )}

          <h4 style={{ color: "#00ffcc", marginTop: "14px" }}>🛡 Cyber Threat Intelligence</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Cyber events: {cyberThreats?.events?.length ?? cyberThreats?.total ?? 0}
          </div>
          {(cyberThreats?.events || []).slice(0,5).map((c, i) => (
            <div key={i} style={{
              background: "#061c1a",
              border: c.severity === "HIGH" ? "1px solid #ff4444" : "1px solid #00ffcc",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{c.severity}</b> — {c.type}<br/>
              Target: {c.target}<br/>
              Region: {c.region}<br/>
              Source: {c.source}<br/>
              {c.summary}
            </div>
          ))}

          <h4 style={{ color: "#66ccff", marginTop: "14px" }}>📡 Feed Coverage</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Total tracked vessels: {feedCoverage?.total_vessels || 0}
          </div>
          {(feedCoverage?.coverage || []).map((z, i) => (
            <div key={i} style={{
              background: z.status === "ACTIVE" ? "#061b10" : z.status === "LOW COVERAGE" ? "#1f1800" : "#1f0606",
              border: z.status === "ACTIVE" ? "1px solid #00ffaa" : z.status === "LOW COVERAGE" ? "1px solid #ffcc00" : "1px solid #ff4444",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{z.zone}</b><br/>
              Contacts: {z.contacts} — {z.status}
            </div>
          ))}

          <h4 style={{ color: "#00ffaa", marginTop: "14px" }}>📄 Operational Report</h4>
          {operationalReport && (
            <div style={{
              background: "#061b14",
              border: "1px solid #00ffaa",
              padding: "8px",
              marginBottom: "8px",
              borderRadius: "8px",
              fontSize: "12px"
            }}>
              <b>Threat Posture Summary</b><br/>
              Vessels: {operationalReport.summary?.tracked_vessels ?? 0}<br/>
              High Risk: {operationalReport.summary?.high_risk_vessels ?? 0}<br/>
              Dark Activity: {operationalReport.summary?.dark_activity ?? 0}<br/>
              Clusters: {operationalReport.summary?.clusters ?? 0}<br/>
              Repeat Offenders: {operationalReport.summary?.repeat_offenders ?? 0}<br/>
              <br/>
              <b>Assessment:</b><br/>
              {operationalReport.assessment || "No assessment available."}
            </div>
          )}

          <h4 style={{ color: "#ff8844", marginTop: "14px" }}>🧬 Cluster Intelligence</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Active clusters: {clusterIntel?.total_clusters || 0}
          </div>
          {(clusterIntel?.clusters || []).slice(0,5).map((c, i) => (
            <div key={i} style={{
              background: "#1f1006",
              border: "1px solid #ff8844",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{c.severity}</b> — Cluster Score {c.cluster_score}<br/>
              Vessels: {c.vessel_count}<br/>
              MMSIs: {formatFlags((c.vessels || []).slice(0,4))}<br/>
              Indicators: {formatFlags(c.indicators)}
            </div>
          ))}

          <h4 style={{ color: "#8888ff", marginTop: "14px" }}>🌑 Dark Activity Monitor</h4>
          <div style={{ fontSize: "12px", opacity: 0.85, marginBottom: "6px" }}>
            Dark events: {darkActivity?.total_dark_activity || 0}
          </div>
          {(darkActivity?.dark_activity || []).slice(0,5).map((d, i) => (
            <div key={i} style={{
              background: "#080822",
              border: "1px solid #8888ff",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px"
            }}>
              <b>{d.severity}</b> — {d.name || d.mmsi}<br/>
              Score: {d.dark_score ?? 0}<br/>
              AIS gap: {d.age_minutes} min<br/>
              Zone: {d.zone || "Unknown"}<br/>
              Flags: {formatFlags(d.flags)}
            </div>
          ))}

          <h4 style={{ color: "#ff4444", marginTop: "10px" }}>🚨 Active Alerts</h4>
          {alerts.length === 0 && (
            <div style={{ fontSize: "12px", opacity: 0.7 }}>No alerts</div>
          )}
          {alerts.map((a, idx) => (
            <div
              key={idx}
              onClick={() => {
                setSelected(a);
                setSelectedType("alert");
                if (a.lat && a.lon) {
                  window.dispatchEvent(new CustomEvent("locate-selected-vessel", {
                    detail: { lat: a.lat, lon: a.lon }
                  }));
                }
              }}
              style={{
              background: "#2a0000",
              padding: "6px",
              marginBottom: "4px",
              borderRadius: "6px",
              fontSize: "12px",
              cursor: "pointer"
            }}>
              <b>{a.type}</b><br/>
              <div className={`threat-badge threat-${(a.risk || a.severity || "medium").toLowerCase()}`}>
                {(a.risk || a.severity || "medium").toUpperCase()} RISK
              </div>
              {a.msg}<br/>

              {(a.type === "REMOTE_STOP_COORDINATE_CAPTURED" || a.type === "PORT_REMOTE_RETURN") && (
                <div style={{ marginTop: "6px", fontSize: "12px", lineHeight: "1.45" }}>
                  <b>Origin Port:</b> {a.origin_port || "Unknown"}<br/>
                  {a.returned_to_port && (
                    <>
                      <b>Returned To:</b> {a.returned_to_port}<br/>
                    </>
                  )}
                  <b>Stop Coordinates:</b> {a.stop_lat}, {a.stop_lon}<br/>
                  <b>Distance From Port:</b> {a.distance_from_origin_port_km || "Unknown"} km<br/>
                  {a.stopped_at && (
                    <>
                      <b>Stopped At:</b> {a.stopped_at}<br/>
                    </>
                  )}
                  <b>Assessment:</b> Requires analyst review
                </div>
              )}
              {a.zone && <span>Zone: {a.zone}</span>}
            </div>
          ))}

<div style={{marginTop:"16px",padding:"12px",background:"#111",borderRadius:"12px",border:"1px solid #222"}}>

<h3>🛰️ 
        {selectedVessel && (
          <div className="selected-intel-card">
            <h3>🎯 Selected Vessel</h3>
            <p><b>Name:</b> {selectedVessel.name || selectedVessel.shipname || "Unknown"}</p>
            <p><b>MMSI:</b> {selectedVessel.mmsi || selectedVessel.id || "Unknown"}</p>
            <p><b>Speed:</b> {selectedVessel.speed || selectedVessel.sog || 0} kn</p>
            <p><b>Heading:</b> {selectedVessel.heading || selectedVessel.cog || "Unknown"}</p>
            <p><b>Risk:</b> {selectedVessel.risk || selectedVessel.risk_level || "LOW"}</p>
            <p><b>Zone:</b> {selectedVessel.zone || selectedVessel.zone_name || "Unknown"}</p>
          </div>
        )}

          Sentinel Satellite</h3>

<label>

<input type="checkbox" checked={showSentinel} onChange={()=>setShowSentinel(!showSentinel)} /> Enable Satellite

</label>

<div style={{marginTop:"10px"}}>

Opacity: {opacity.toFixed(2)}

<input type="range" min="0" max="1" step="0.05" value={opacity} onChange={(e)=>setOpacity(parseFloat(e.target.value))} />

</div>

</div>

        {topThreats.length === 0 && (
          <div style={{ opacity: 0.8 }}>No active threats detected.</div>
        )}

        <hr style={{ borderColor: "#222", margin: "16px 0" }} />
        <h3 style={{ marginTop: 0 }}>🟡 Vessel Watchlist</h3>

<div style={{
  background: "#111827",
  border: "1px solid #facc15",
  borderRadius: "10px",
  padding: "10px",
  marginBottom: "12px"
}}>
  <h4 style={{ margin: "0 0 8px 0", color: "#facc15" }}>
    ⚠️ Ranked Elevated Vessels
  </h4>

  {vessels
    .filter(v => String(v.risk_level || "").toLowerCase() !== "low")
    .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
    .slice(0, 5)
    .map((v, idx) => (
      <div key={v.id || v.mmsi || idx} style={{
        fontSize: "12px",
        padding: "6px",
        borderBottom: "1px solid #374151"
      }}>
        <b>#{idx + 1}</b> {v.mmsi || v.id || "Unknown"}<br />
        Risk: <b>{v.risk_level || "Unknown"}</b><br />
        Confidence: {v.confidence || 0}%<br />
        Flags: {(v.anomaly_flags || v.flags || []).join(", ") || "None"}
      </div>
    ))}

  {vessels.filter(v => String(v.risk_level || "").toLowerCase() !== "low").length === 0 && (
    <div style={{ fontSize: "12px", color: "#9ca3af" }}>
      No elevated vessels currently detected.
    </div>
  )}
</div>


<button
  style={{
    marginTop: "10px",
    width: "100%",
    padding: "8px",
    background: "#1f6feb",
    color: "white",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer"
  }}

  onClick={() => {
  window.location.href = "http://127.0.0.1:5000/api/report/pdf";
}}>
  📄 Generate Report
</button>


        {visibleVessels
          .filter((v) => String(v.risk_level || "").toLowerCase() !== "low")
          .slice(0, 10)
          .map((v) => (
            <div
              key={v.id}
              onClick={() => {
                setSelected(v);
                setSelectedType("vessel");
              }}
              style={{
                marginBottom: "12px",
                padding: "12px",
                background: "#0f172a",
                border: "1px solid #facc15",
                borderRadius: "12px",
                cursor: "pointer",
              }}
            >
              <div style={{ fontWeight: "bold", fontSize: "15px" }}>
                {v.name || "Unknown"}
              </div>
              <div>MMSI: {v.mmsi || v.id || "N/A"}</div>
              <div>Risk: <b style={{ color: "#facc15" }}>{v.risk_level || "Medium"}</b></div>
              <div>Speed: {v.speed ?? "N/A"} kn</div>
              <div>Heading: {v.heading ?? v.course ?? "N/A"}°</div>
              <div>Confidence: {v.confidence ?? "N/A"}</div>
              <div style={{ marginTop: "8px", fontSize: "13px", opacity: 0.9 }}>
                <b>Reasons:</b><br />
                {(v.anomaly_flags || v.risk_flags || v.behavior_flags || ["inside Fiji-Pacific watch zone"])
                  .join(", ")}
              </div>
            </div>
          ))}

        {topThreats.map((v) => (
          <div
            key={v.id}
            style={{
              marginBottom: "12px",
              padding: "12px",
              background: "#111",
              borderRadius: "12px",
              border: "1px solid #222",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>{v.name || "Unknown"}</strong>
              <span
                style={{
                  background: "#2b0b0b",
                  color: "#ff5c5c",
                  padding: "4px 8px",
                  borderRadius: "999px",
                  fontSize: "11px",
                  fontWeight: "bold",
                }}
              >
                ● {String(v.risk_level || "").toUpperCase()}
              </span>
            </div>
            <MiniStat label="Confidence" value={v.confidence} />
            <MiniStat label="Last seen age" value={`${v.last_seen_age_hours ?? "N/A"} hrs`} />
            <MiniStat label="Flags" value={formatFlags(v.anomaly_flags)} />
          </div>
        ))}

        <hr style={{ borderColor: "#222", margin: "16px 0" }} />

        {!selected && <div style={{ opacity: 0.9 }}>Select a vessel or alert on the map.</div>}

        {selected && selectedType === "vessel" && (
          <>
            <h3>{selected.name || "Unknown"}</h3>
            <MiniStat label="Category" value="Vessel" />
            <MiniStat label="Type" value={selected.type || "Unknown"} />
            <MiniStat label="Speed" value={`${selected.speed ?? "N/A"} kn`} />
            <MiniStat label="Course" value={Number.isNaN(Number(selected.course)) ? "N/A" : selected.course} />
            <MiniStat label="Heading" value={Number.isNaN(Number(selected.heading)) ? "N/A" : selected.heading} />
            <MiniStat label="Last Seen" value={selected.lastSeen || "N/A"} />
            <MiniStat label="Confidence" value={selected.confidence ?? 0} />
            <MiniStat label="Risk Level" value={selected.threat_level || selected.risk_level || selected.risk_level || "Unknown"} />
            <MiniStat label="Offender Status" value={selected.memory?.offender_status || "NEW"} />
            <MiniStat label="Repeat Offender Score" value={selected.memory?.repeat_offender_score ?? 0} />
            <MiniStat label="Loitering History" value={selected.memory?.loitering_count ?? 0} />
            <MiniStat label="Dark Activity History" value={selected.memory?.dark_activity_count ?? 0} />
            <MiniStat label="Rendezvous History" value={selected.memory?.rendezvous_count ?? 0} />
            <MiniStat label="Latitude" value={selected.lat} />
            <MiniStat label="Longitude" value={selected.lon} />
            <MiniStat label="Correlation Score" value={selected.correlation_score ?? 0} />
            <MiniStat label="Risk Flags" value={formatFlags(selected.threat_level || selected.risk_level || selected.risk_flags)} />
            <MiniStat label="Anomaly Flags" value={formatFlags(selected.anomaly_flags)} />
            <MiniStat label="Behavior Flags" value={formatFlags(selected.behavior_flags)} />
            <MiniStat label="Last Seen Age" value={`${selected.last_seen_age_hours ?? "N/A"} hrs`} />
            <MiniStat label="Assessment" value={selected.assessment || "No assessment yet"} />

            <hr style={{ borderColor: "#222", margin: "16px 0" }} />

            <h4 style={{ color: "#ffaa66", marginBottom: "10px" }}>
              🧾 Vessel Intelligence Profile
            </h4>

            {vesselProfile && (
              <div style={{
                background: "#1a1208",
                border: "1px solid #ffaa66",
                borderRadius: "8px",
                padding: "8px",
                marginBottom: "8px",
                fontSize: "12px"
              }}>
                <b>MMSI:</b> {vesselProfile.mmsi}<br/>
                Linked Cases: {vesselProfile.risk_summary?.linked_case_count ?? 0}<br/>
                Timeline Events: {vesselProfile.risk_summary?.timeline_events ?? 0}<br/>

                {(vesselProfile.linked_cases || []).slice(0,3).map((c, i) => (
                  <div key={i} style={{
                    marginTop: "6px",
                    padding: "6px",
                    background: "#2a1908",
                    borderRadius: "6px"
                  }}>
                    <b>{c.case_id}</b> — {c.priority}<br/>
                    {c.title}<br/>
                    Status: {c.status}<br/>
                    Zone: {c.zone}
                  </div>
                ))}
              </div>
            )}

            <h4 style={{ color: "#ff66cc", marginBottom: "10px" }}>
              🕸 Vessel Network Intelligence
            </h4>

            <MiniStat label="Known Zones" value={formatFlags(networkData.zones)} />
            <MiniStat label="Network Links" value={(networkData.connections || []).length} />

            {(networkData.connections || []).slice(0,5).map((c, idx) => (
              <div
                key={idx}
                style={{
                  background: "#180718",
                  border: "1px solid #442244",
                  borderRadius: "8px",
                  padding: "8px",
                  marginBottom: "6px",
                  fontSize: "11px"
                }}
              >
                <div style={{ color: "#ff66cc", fontWeight: "bold" }}>
                  Linked Vessel: {c.target}
                </div>
                <div>Score: {c.score}</div>
                <div>Relationship: {formatFlags(c.types)}</div>
                <div style={{ opacity: 0.55, fontSize: "10px" }}>
                  Last Seen: {c.last_seen}
                </div>
              </div>
            ))}

            {(networkData.connections || []).length === 0 && (
              <div style={{ fontSize: "12px", opacity: 0.7, marginBottom: "10px" }}>
                No vessel network links yet.
              </div>
            )}

            <h4 style={{ color: "#00ffaa", marginBottom: "10px" }}>
              🕒 Vessel Timeline
            </h4>

            {timelineData.length === 0 && (
              <div style={{ fontSize: "12px", opacity: 0.7 }}>
                No timeline events yet.
              </div>
            )}

            {timelineData.slice().reverse().slice(0,10).map((e, idx) => (
              <div
                key={idx}
                style={{
                  background: "#071018",
                  border: "1px solid #123444",
                  borderRadius: "8px",
                  padding: "8px",
                  marginBottom: "6px",
                  fontSize: "11px"
                }}
              >
                <div style={{ color: "#00ffaa", fontWeight: "bold" }}>
                  {e.event_type}
                </div>

                <div style={{ opacity: 0.9 }}>
                  {e.details}
                </div>

                <div style={{ opacity: 0.5, fontSize: "10px" }}>
                  {e.timestamp}
                </div>
              </div>
            ))}

            {isOnLand(selected.lat, selected.lon) && Number(selected.speed) > 1 && (
              <p style={{ color: "orange", fontWeight: "bold" }}>
                ⚠️ Position anomaly detected
              </p>
            )}

            {selected.score_breakdown && (
              <>
                <hr style={{ borderColor: "#222", margin: "16px 0" }} />
                <p><strong>Score Breakdown:</strong></p>
                <MiniStat label="Base Confidence" value={selected.score_breakdown.base_confidence} />
                <MiniStat label="Correlation" value={selected.score_breakdown.correlation} />
                <MiniStat label="Anomaly" value={selected.score_breakdown.anomaly} />
                <MiniStat label="Stale Tracking" value={selected.score_breakdown.stale_tracking} />
                <MiniStat label="Type Weight" value={selected.score_breakdown.type_weight} />
                <MiniStat label="Multiple Alert Bonus" value={selected.score_breakdown.multiple_alert_bonus} />
              </>
            )}
          </>
        )}

        {selected && selectedType === "alert" && (
          <>
            <h3>{selected.name || "Alert"}</h3>
            <MiniStat label="Category" value="Alert" />
            <MiniStat label="Type" value={selected.type || "Unknown"} />
            <MiniStat label="Severity" value={selected.severity || "N/A"} />
            <MiniStat label="Latitude" value={selected.lat} />
            <MiniStat label="Longitude" value={selected.lon} />
          </>
        )}
      </div>
    </div>
  );
}