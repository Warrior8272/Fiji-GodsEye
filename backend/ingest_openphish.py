#!/usr/bin/env python3
import json
import re
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

# Phase 17M — tighter NAYADRA relevance filtering
HIGH_RELEVANCE_TERMS = [
    "fiji", "fijian", "suva", "lautoka", "nadi",
    "customs", "border", "immigration", "biosecurity",
    "navy", "police", "government", "gov", "ministry"
]

MEDIUM_RELEVANCE_TERMS = [
    "shipping", "maritime", "vessel", "cargo", "freight",
    "logistics", "seaport", "harbour", "harbor", "portauthority",
    "port-authority", "port_authority"
]

WEAK_RELEVANCE_TERMS = [
    "port"
]


def classify_nayadra_relevance(url_text):
    """
    Returns:
      relevance_label, matched_terms, should_add
    """
    t = str(url_text or "").lower()

    high = [x for x in HIGH_RELEVANCE_TERMS if x in t]
    medium = [x for x in MEDIUM_RELEVANCE_TERMS if x in t]
    weak = [x for x in WEAK_RELEVANCE_TERMS if re.search(r'(^|[^a-z])' + re.escape(x) + r'([^a-z]|$)', t)]

    matched = high + medium + weak

    if high:
        return "HIGH_RELEVANCE", matched, True

    if medium:
        return "MARITIME_REVIEW", matched, True

    # Important: port alone is too weak. Do not add unless combined with stronger context.
    if weak:
        return "WEAK_PORT_ONLY", matched, False

    return "NOT_RELEVANT", [], False



FEED_URL = "https://www.openphish.com/feed.txt"
CYBER_FILE = Path(__file__).with_name("cyber_alerts.json")

# Strong relevance terms: these are specific enough for NAYADRA.
FIJI_TERMS = [
    "fiji", "suva", "lautoka", "nadi", "viti", "vanua", "yasawa", "kadavu", "rotuma"
]

PACIFIC_TERMS = [
    "pacific", "samoa", "tonga", "tuvalu", "vanuatu", "kiribati", "solomon", "png",
    "papua", "micronesia", "marshall", "cookislands", "cook-islands"
]

MARITIME_TERMS = [
    "maritime", "shipping", "ship", "vessel", "seafarer", "seaman", "crew",
    "port", "cargo", "freight", "customs", "border", "navy", "coastguard"
]

# Weak generic terms should not create alerts alone.
WEAK_TERMS = [
    "support", "agency", "manager", "login", "mail", "account", "verify"
]

def load_existing():
    if CYBER_FILE.exists():
        try:
            data = json.loads(CYBER_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_alerts(alerts):
    CYBER_FILE.write_text(json.dumps(alerts, indent=2), encoding="utf-8")

def next_id(alerts):
    nums = []
    for a in alerts:
        aid = str(a.get("id", ""))
        if aid.startswith("CYBER-"):
            try:
                nums.append(int(aid.split("-")[1]))
            except Exception:
                pass
    return f"CYBER-{(max(nums) + 1) if nums else 1:04d}"

def classify_relevance(url):
    u = url.lower()

    fiji_hits = [k for k in FIJI_TERMS if k in u]
    pacific_hits = [k for k in PACIFIC_TERMS if k in u]
    maritime_hits = [k for k in MARITIME_TERMS if k in u]
    weak_hits = [k for k in WEAK_TERMS if k in u]

    if fiji_hits:
        return "FIJI_RELEVANT", fiji_hits, "HIGH"

    if pacific_hits and maritime_hits:
        return "PACIFIC_MARITIME_RELEVANT", pacific_hits + maritime_hits, "HIGH"

    if maritime_hits:
        return "MARITIME_REVIEW", maritime_hits, "MEDIUM"

    # Do not add weak generic matches automatically.
    return "NOT_RELEVANT", weak_hits, "LOW"

def main():
    print("[17I-2] Fetching OpenPhish feed...")
    with urllib.request.urlopen(FEED_URL, timeout=20) as response:
        raw = response.read().decode("utf-8", errors="ignore")

    urls = [line.strip() for line in raw.splitlines() if line.strip().startswith("http")]
    print(f"[17I-2] Feed URLs received: {len(urls)}")

    alerts = load_existing()
    existing_indicators = {a.get("indicator") for a in alerts}

    added = 0
    skipped = 0

    for url in urls:
        relevance, hits, should_add = classify_nayadra_relevance(url)

        if not should_add:
            skipped += 1
            continue

        if relevance == "HIGH_RELEVANCE":
            risk = "HIGH"
        elif relevance == "MARITIME_REVIEW":
            risk = "MEDIUM"
        else:
            risk = "LOW"

        if url in existing_indicators:
            skipped += 1
            continue

        domain = urlparse(url).netloc

        alert = {
            "id": next_id(alerts),
            "status": "UNVERIFIED",
            "verification_status": "UNVERIFIED",
            "confidence": "LOW",
            "type": "OPENPHISH_FEED",
            "title": f"OpenPhish {relevance}: {domain}",
            "target": "Fiji/Pacific maritime or government-related keyword match",
            "zone": "Cyber / OSINT",
            "risk": risk,
            "source": "OpenPhish public feed",
            "indicator": url,
            "source_url": FEED_URL,
            "evidence_file": "",
            "observed_date": datetime.now(timezone.utc).date().isoformat(),
            "analyst_name": "NAYADRA Cyber Feed",
            "analyst_note": f"Automatically ingested OpenPhish match. Relevance={relevance}; matched_terms={hits}. Requires manual verification before escalation.",
            "summary": f"OpenPhish feed URL matched NAYADRA relevance filter: {relevance}. Matched terms: {', '.join(hits)}. This does not confirm targeting and requires analyst review.",
            "recommended_action": "Do not visit directly. Use safe analysis tools, capture evidence, verify domain context, and classify before reporting.",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        alerts.insert(0, alert)
        existing_indicators.add(url)
        added += 1

    save_alerts(alerts)

    print(f"[17I-2] Added alerts: {added}")
    print(f"[17I-2] Skipped/not relevant or duplicate: {skipped}")
    print(f"[17I-2] Total cyber alerts now: {len(alerts)}")

if __name__ == "__main__":
    main()
