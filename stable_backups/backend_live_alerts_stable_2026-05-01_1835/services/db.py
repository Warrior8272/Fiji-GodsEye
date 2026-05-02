import sqlite3
import os

DB_PATH = "data/vessels.db"

def get_conn():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vessels (
        id TEXT PRIMARY KEY,
        mmsi TEXT,
        name TEXT,
        lat REAL,
        lon REAL,
        speed REAL,
        course REAL,
        heading REAL,
        lastSeen TEXT,
        source TEXT,
        type TEXT
    )
    """)

    conn.commit()
    conn.close()

def list_vessels(limit=100):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM vessels ORDER BY lastSeen DESC LIMIT ?", (limit,))
    rows = cur.fetchall()

    cols = [c[0] for c in cur.description]
    result = [dict(zip(cols, r)) for r in rows]

    conn.close()
    return result

def list_alerts(limit=100):
    return []

def get_vessel_history(vessel_id, limit=100):
    return []


def upsert_vessel(v):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO vessels
    (id, mmsi, name, lat, lon, speed, course, heading, lastSeen, source, type)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        v.get("id"),
        v.get("mmsi"),
        v.get("name"),
        v.get("lat"),
        v.get("lon"),
        v.get("speed"),
        v.get("course"),
        v.get("heading"),
        v.get("lastSeen"),
        v.get("source"),
        v.get("type")
    ))

    conn.commit()
    conn.close()
