import sqlite3
import os

DB_PATH = "data/gods_eye.db"

def get_conn():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        source TEXT,
        name TEXT,
        type TEXT,
        severity TEXT,
        indicator TEXT,
        target_region TEXT,
        lat REAL,
        lon REAL,
        first_seen TEXT,
        confidence INTEGER,
        raw_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vessels (
        id TEXT PRIMARY KEY,
        source TEXT,
        name TEXT,
        type TEXT,
        lat REAL,
        lon REAL,
        speed REAL,
        course REAL,
        heading REAL,
        lastSeen TEXT,
        confidence INTEGER,
        raw_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vessel_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vessel_id TEXT,
        name TEXT,
        lat REAL,
        lon REAL,
        speed REAL,
        course REAL,
        heading REAL,
        recorded_at TEXT,
        source TEXT
    )
    """)

    conn.commit()
    conn.close()

def upsert_alert(record):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO alerts (
        id, source, name, type, severity, indicator, target_region,
        lat, lon, first_seen, confidence, raw_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record["id"],
        record["source"],
        record["name"],
        record["type"],
        record["severity"],
        record["indicator"],
        record["target_region"],
        record["lat"],
        record["lon"],
        record["first_seen"],
        record["confidence"],
        record["raw_json"]
    ))

    conn.commit()
    conn.close()

def upsert_vessel(record):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO vessels (
        id, source, name, type, lat, lon, speed, course, heading,
        lastSeen, confidence, raw_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record["id"],
        record["source"],
        record["name"],
        record["type"],
        record["lat"],
        record["lon"],
        record["speed"],
        record.get("course"),
        record.get("heading"),
        record["lastSeen"],
        record["confidence"],
        record["raw_json"]
    ))

    conn.commit()
    conn.close()

def insert_vessel_history(record):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO vessel_history (
        vessel_id, name, lat, lon, speed, course, heading, recorded_at, source
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record["id"],
        record.get("name"),
        record.get("lat"),
        record.get("lon"),
        record.get("speed"),
        record.get("course"),
        record.get("heading"),
        record.get("lastSeen"),
        record.get("source")
    ))

    conn.commit()
    conn.close()

def list_alerts(limit=100):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT id, source, name, type, severity, indicator, target_region,
           lat, lon, first_seen, confidence
    FROM alerts
    ORDER BY first_seen DESC
    LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "source": r[1],
            "name": r[2],
            "type": r[3],
            "severity": r[4],
            "indicator": r[5],
            "target_region": r[6],
            "lat": r[7],
            "lon": r[8],
            "first_seen": r[9],
            "confidence": r[10],
        }
        for r in rows
    ]

def list_vessels(limit=100):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT id, source, name, type, lat, lon, speed, course, heading, lastSeen, confidence
    FROM vessels
    ORDER BY lastSeen DESC
    LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "source": r[1],
            "name": r[2],
            "type": r[3],
            "lat": r[4],
            "lon": r[5],
            "speed": r[6],
            "course": r[7],
            "heading": r[8],
            "lastSeen": r[9],
            "confidence": r[10],
        }
        for r in rows
    ]

def get_vessel_history(vessel_id, limit=50):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT vessel_id, name, lat, lon, speed, course, heading, recorded_at, source
    FROM vessel_history
    WHERE vessel_id = ?
    ORDER BY recorded_at ASC
    LIMIT ?
    """, (vessel_id, limit))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "name": r[1],
            "lat": r[2],
            "lon": r[3],
            "speed": r[4],
            "course": r[5],
            "heading": r[6],
            "recorded_at": r[7],
            "source": r[8],
        }
        for r in rows
    ]
