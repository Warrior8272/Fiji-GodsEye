from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    text = str(value).strip()

    try:
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    ]:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def age_hours(dt: Optional[datetime]) -> Optional[float]:
    if not dt:
        return None
    return round((utc_now() - dt).total_seconds() / 3600.0, 2)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def percent(value: float) -> int:
    return int(round(clamp(value, 0, 100)))


def is_known_position(lat: Optional[float], lon: Optional[float]) -> bool:
    return lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_km = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    km = r_km * c
    nm = km * 0.539957
    return round(nm, 2)


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)

    x = math.sin(dlambda) * math.cos(phi2)
    y = (
        math.cos(phi1) * math.sin(phi2)
        - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    )
    brng = math.degrees(math.atan2(x, y))
    return round((brng + 360) % 360, 2)


def heading_to_cardinal(heading: Optional[float]) -> str:
    if heading is None:
        return "Unknown"

    directions = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW",
    ]
    index = round(heading / 22.5) % 16
    return directions[index]
