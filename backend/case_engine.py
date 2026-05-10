import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("godseye_intel.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_case_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS investigation_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT,
        created TEXT,
        title TEXT,
        status TEXT,
        priority TEXT,
        zone TEXT,
        notes TEXT,
        linked_mmsi TEXT
    )
    """)

    conn.commit()
    conn.close()

def create_case(title, priority, zone, notes, linked_mmsi=""):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM investigation_cases")
    count = cur.fetchone()[0] + 1

    case_id = f"CASE-{count:04d}"

    cur.execute("""
    INSERT INTO investigation_cases
    (case_id, created, title, status, priority, zone, notes, linked_mmsi)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        case_id,
        datetime.utcnow().isoformat(),
        title,
        "ACTIVE",
        priority,
        zone,
        notes,
        linked_mmsi
    ))

    conn.commit()
    conn.close()

    return {
        "case_id": case_id,
        "status": "ACTIVE"
    }

def get_cases():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT case_id, created, title, status, priority, zone, notes, linked_mmsi
    FROM investigation_cases
    ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "case_id": r[0],
            "created": r[1],
            "title": r[2],
            "status": r[3],
            "priority": r[4],
            "zone": r[5],
            "notes": r[6],
            "linked_mmsi": r[7]
        }
        for r in rows
    ]
