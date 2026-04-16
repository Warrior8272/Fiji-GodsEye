from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from websocket import create_connection

from config import Config
from utils.geo import dt_to_iso, is_known_position, parse_dt, safe_float

AISSTREAM_WS_URL = "wss://stream.aisstream.io/v0/stream"
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
CACHE_FILE = CACHE_DIR / "last_vessels.json"
CACHE_MAX_AGE_MINUTES = 15


def parse_aisstream_time(value: str | None):
    if not value:
        return None

    text = str(value).strip().replace(" UTC", "")

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(\.\d+)? ([+-]\d{4})$",
        text,
    )
    if not match:
        return None

    base = match.group(1)
    frac = match.group(2) or ""
    offset = match.group(3)

    if frac:
        frac_digits = frac[1:][:6]
        frac = "." + frac_digits

    cleaned = f"{base}{frac} {offset}"

    try:
        return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S.%f %z")
    except ValueError:
        try:
            return datetime.strptime(f"{base} {offset}", "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            return None


def _fiji_bounding_box():
    return [
        [[-40.0, 140.0], [0.0, 180.0]],   # BIG Pacific region
        [[-40.0, -180.0], [0.0, -140.0]], # Dateline wrap
    ]


def _aisstream_subscription() -> Dict[str, Any]:
    api_key = Config.AIS_API_KEY or os.getenv("7ca09eeb84e85ab922ac5ed801b51bfd70e9ecb8", "").strip()

    return {
        "APIKey": api_key,
        "BoundingBoxes": _fiji_bounding_box(),
        "FilterMessageTypes": [
            "PositionReport",
            "ShipStaticData",
            "StandardClassBPositionReport",
            "ExtendedClassBPositionReport",
            "StaticDataReport",
        ],
    }


def _extract_from_message(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    message_type = msg.get("MessageType")
    metadata = msg.get("MetaData") or msg.get("Metadata") or {}
    message = msg.get("Message") or {}

    if not isinstance(metadata, dict):
        metadata = {}

    lat = safe_float(
        metadata.get("latitude")
        or metadata.get("Latitude")
        or msg.get("lat")
        or msg.get("Latitude")
    )
    lon = safe_float(
        metadata.get("longitude")
        or metadata.get("Longitude")
        or msg.get("lon")
        or msg.get("Longitude")
    )

    if lat is None or lon is None:
        return None

    if not is_known_position(lat, lon):
        return None

    mmsi = metadata.get("MMSI") or metadata.get("UserID")
    ship_name = metadata.get("ShipName")

    speed_knots = None
    course = None
    heading = None
    status = None
    destination = None
    callsign = None
    imo = None
    ship_type = None

    payload = {}
    if isinstance(message, dict):
        payload = message.get(message_type, {}) or {}

    if isinstance(payload, dict):
        speed_knots = safe_float(
            payload.get("Sog") or payload.get("Speed") or payload.get("SpeedOverGround"),
            0.0,
        )
        course = safe_float(
            payload.get("Cog") or payload.get("Course") or payload.get("CourseOverGround")
        )
        heading = safe_float(payload.get("TrueHeading") or payload.get("Heading"))
        status = payload.get("NavigationalStatus") or payload.get("Status")
        destination = payload.get("Destination")
        callsign = payload.get("CallSign") or payload.get("Callsign")
        imo = payload.get("ImoNumber") or payload.get("IMO")
        ship_type = payload.get("Type") or payload.get("ShipType")

    last_seen = parse_aisstream_time(metadata.get("time_utc") or metadata.get("TimeUTC"))
    if last_seen is None:
        last_seen = datetime.now(timezone.utc)

    return {
        "mmsi": str(mmsi).strip() if mmsi is not None else None,
        "imo": str(imo).strip() if imo is not None else None,
        "name": str(ship_name or "Unknown Vessel").strip(),
        "callsign": str(callsign).strip() if callsign else None,
        "ship_type": str(ship_type or "Unknown").strip(),
        "flag": None,
        "destination": destination,
        "status": status or "Unknown",
        "lat": lat,
        "lon": lon,
        "speed_knots": round(speed_knots or 0.0, 2),
        "course": round(course, 2) if course is not None else None,
        "heading": round(heading, 2) if heading is not None else None,
        "last_seen": last_seen,
        "last_seen_iso": dt_to_iso(last_seen),
        "source": "aisstream_live",
    }


def _json_safe_vessel(vessel: Dict[str, Any]) -> Dict[str, Any]:
    safe = dict(vessel)
    if isinstance(safe.get("last_seen"), datetime):
        safe["last_seen"] = dt_to_iso(safe["last_seen"])
    return safe


def save_cache(vessels: List[Dict[str, Any]]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "cached_at": dt_to_iso(datetime.now(timezone.utc)),
            "count": len(vessels),
            "vessels": [_json_safe_vessel(v) for v in vessels],
        }
        with CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(payload, f)
        print(f"Saved {len(vessels)} vessels to cache")
    except Exception as exc:
        print(f"Cache save failed: {exc}")


def load_cache() -> List[Dict[str, Any]]:
    if not CACHE_FILE.exists():
        print("No cache file found")
        return []

    try:
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        cached_at = parse_dt(payload.get("cached_at"))
        if cached_at is None:
            print("Cache timestamp invalid")
            return []

        age = datetime.now(timezone.utc) - cached_at
        if age > timedelta(minutes=CACHE_MAX_AGE_MINUTES):
            print("Cache is too old")
            return []

        vessels = payload.get("vessels", [])
        if not isinstance(vessels, list):
            return []

        print(f"Loaded {len(vessels)} vessels from cache")
        return vessels
    except Exception as exc:
        print(f"Cache load failed: {exc}")
        return []


def fetch_external_ais_feed() -> List[Dict[str, Any]]:
    if (Config.AIS_API_URL or "").strip().lower() != "aisstream":
        print("AISStream mode not enabled. Using cache if available.")
        return load_cache()

    api_key = Config.AIS_API_KEY or os.getenv("AIS_API_KEY", "").strip()
    if not api_key:
        print("AISStream API key missing. Using cache if available.")
        return load_cache()

    subscription = _aisstream_subscription()
    vessels_by_mmsi: Dict[str, Dict[str, Any]] = {}

    ws = None
    try:
        print("AISStream mode enabled")
        print(f"Using WS URL: {AISSTREAM_WS_URL}")
        print(f"API key present: {'yes' if api_key else 'no'}")
        print(f"Subscription: {subscription}")

        ws = create_connection(AISSTREAM_WS_URL, timeout=10)
        print("WebSocket connected")

        ws.send(json.dumps(subscription))
        print("Subscription sent")

        end_time = time.time() + 30

        while time.time() < end_time:
            try:
                raw = ws.recv()
            except Exception as exc:
                print(f"WebSocket receive failed: {exc}")
                break

            if not raw:
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if isinstance(msg, dict) and msg.get("error"):
                print(f"AISStream error: {msg['error']}")
                continue

            vessel = _extract_from_message(msg)
            if not vessel:
                continue

            mmsi = vessel.get("mmsi")
            if not mmsi:
                continue

            existing = vessels_by_mmsi.get(mmsi)
            if existing is None:
                vessels_by_mmsi[mmsi] = vessel
            else:
                if vessel.get("name") and existing.get("name") == "Unknown Vessel":
                    existing["name"] = vessel["name"]
                if vessel.get("callsign") and not existing.get("callsign"):
                    existing["callsign"] = vessel["callsign"]
                if vessel.get("imo") and not existing.get("imo"):
                    existing["imo"] = vessel["imo"]
                if vessel.get("ship_type") and existing.get("ship_type") == "Unknown":
                    existing["ship_type"] = vessel["ship_type"]
                if vessel.get("destination") and not existing.get("destination"):
                    existing["destination"] = vessel["destination"]
                if vessel.get("status") and existing.get("status") == "Unknown":
                    existing["status"] = vessel["status"]

                existing["lat"] = vessel["lat"]
                existing["lon"] = vessel["lon"]
                existing["speed_knots"] = vessel["speed_knots"]
                existing["course"] = vessel["course"]
                existing["heading"] = vessel["heading"]
                existing["last_seen"] = vessel["last_seen"]
                existing["last_seen_iso"] = vessel["last_seen_iso"]

        live_vessels = list(vessels_by_mmsi.values())

        if live_vessels:
            print(f"Returning {len(live_vessels)} live vessels")
            save_cache(live_vessels)
            return live_vessels

        print("No live vessels received. Falling back to cache.")
        return load_cache()

    except Exception as exc:
        print(f"AISStream fetch failed: {exc}")
        print("Falling back to cache.")
        return load_cache()

    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass


def normalize_vessel(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lat = safe_float(raw.get("lat"))
    lon = safe_float(raw.get("lon"))

    if not is_known_position(lat, lon):
        return None

    speed = safe_float(raw.get("speed_knots", raw.get("speed", raw.get("sog"))), 0.0)
    course = safe_float(raw.get("course", raw.get("cog")))
    heading = safe_float(raw.get("heading"))
    last_seen = parse_dt(raw.get("last_seen") or raw.get("timestamp") or raw.get("seen_at"))

    return {
        "mmsi": str(raw.get("mmsi") or "").strip() or None,
        "imo": str(raw.get("imo") or "").strip() or None,
        "name": str(raw.get("name") or "Unknown Vessel").strip(),
        "callsign": str(raw.get("callsign") or "").strip() or None,
        "ship_type": str(raw.get("ship_type") or raw.get("type") or "Unknown").strip(),
        "flag": raw.get("flag"),
        "destination": raw.get("destination"),
        "status": raw.get("status") or "Unknown",
        "lat": lat,
        "lon": lon,
        "speed_knots": round(speed or 0.0, 2),
        "course": round(course, 2) if course is not None else None,
        "heading": round(heading, 2) if heading is not None else None,
        "last_seen": last_seen,
        "last_seen_iso": dt_to_iso(last_seen),
        "source": raw.get("source", "live_feed"),
    }


def load_raw_vessels() -> List[Dict[str, Any]]:
    return fetch_external_ais_feed()
