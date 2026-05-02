from modules.news import get_news

HIGH_KEYWORDS = ["scam", "fraud", "breach", "attack"]
MEDIUM_KEYWORDS = ["cyber", "police", "crime", "incident"]

def get_alerts():
    news = get_news()
    alerts = []

    for item in news:
        title = item["title"].lower()
        risk = None
        matched_keyword = None

        for keyword in HIGH_KEYWORDS:
            if keyword in title:
                risk = "HIGH"
                matched_keyword = keyword
                break

        if not risk:
            for keyword in MEDIUM_KEYWORDS:
                if keyword in title:
                    risk = "MEDIUM"
                    matched_keyword = keyword
                    break

        if risk:
            alerts.append({
                "title": item["title"],
                "url": item["url"],
                "risk": risk,
                "keyword": matched_keyword
            })

    return alerts
