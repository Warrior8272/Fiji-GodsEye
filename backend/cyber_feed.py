from datetime import datetime

CYBER_EVENTS = [
    {
        "type": "PHISHING",
        "severity": "HIGH",
        "source": "Demo Feed",
        "target": "Government / Finance",
        "url": "https://example-phishing-site.test/login",
        "region": "Pacific",
        "timestamp": datetime.utcnow().isoformat(),
        "summary": "Suspected phishing page targeting login credentials."
    },
    {
        "type": "MALICIOUS_DOMAIN",
        "severity": "MEDIUM",
        "source": "Demo Feed",
        "target": "Public Users",
        "url": "malicious-domain.test",
        "region": "Fiji / Pacific",
        "timestamp": datetime.utcnow().isoformat(),
        "summary": "Potential malicious domain requiring review."
    }
]

def get_cyber_events():
    return {
        "total": len(CYBER_EVENTS),
        "events": CYBER_EVENTS
    }
