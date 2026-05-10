import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("godseye_intel.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS intelligence_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        event_type TEXT,
        severity TEXT,
        zone TEXT,
        message TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        action TEXT,
        details TEXT
    )
    """)

    conn.commit()
    conn.close()

def log_event(event_type, severity, zone, message):
    conn = get_conn()
    cur = conn.cursor()

    # Prevent repeated duplicate logs for the same event/zone/message
    cur.execute("""
    SELECT id FROM intelligence_events
    WHERE event_type = ?
      AND zone = ?
      AND message = ?
    ORDER BY id DESC
    LIMIT 1
    """, (event_type, zone, message))

    existing = cur.fetchone()

    if existing:
        conn.close()
        return False

    cur.execute("""
    INSERT INTO intelligence_events
    (timestamp, event_type, severity, zone, message)
    VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        event_type,
        severity,
        zone,
        message
    ))

    conn.commit()
    conn.close()
    return True

def log_audit(action, details):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO audit_log
    (timestamp, action, details)
    VALUES (?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        action,
        details
    ))

    conn.commit()
    conn.close()

def recent_events(limit=20):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT timestamp, event_type, severity, zone, message
    FROM intelligence_events
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "timestamp": r[0],
            "event_type": r[1],
            "severity": r[2],
            "zone": r[3],
            "message": r[4]
        }
        for r in rows
    ]
