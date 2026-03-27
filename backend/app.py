from flask import Flask, jsonify
from flask_cors import CORS
import feedparser

app = Flask(__name__)
CORS(app)

RSS_FEEDS = [
    "https://www.rnz.co.nz/rss/pacific.xml",
    "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
]

KEYWORDS = {
    "fiji": "HIGH",
    "suva": "HIGH",
    "pacific": "MEDIUM",
    "scam": "HIGH",
    "fraud": "HIGH",
    "cyber": "HIGH",
    "attack": "HIGH",
    "crime": "MEDIUM",
    "arrest": "MEDIUM",
    "drug": "HIGH",
    "drugs": "HIGH",
    "seizure": "HIGH",
    "trafficking": "HIGH",
    "port": "MEDIUM",
    "airport": "MEDIUM",
    "shipment": "MEDIUM",
    "police": "LOW",
    "court": "LOW",
}

from flask import Flask, jsonify
from flask_cors import CORS
import feedparser

app = Flask(__name__)
CORS(app)

# 🌍 RSS feeds (Pacific + Asia)
RSS_FEEDS = [
    "https://www.rnz.co.nz/rss/pacific.xml",
    "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
]

# 🚨 Keyword risk levels
KEYWORDS = {
    "fiji": "HIGH",
    "suva": "HIGH",
    "pacific": "MEDIUM",
    "scam": "HIGH",
    "fraud": "HIGH",
    "cyber": "HIGH",
    "attack": "HIGH",
    "crime": "MEDIUM",
    "arrest": "MEDIUM",
    "drug": "HIGH",
    "drugs": "HIGH",
    "seizure": "HIGH",
    "trafficking": "HIGH",
    "port": "MEDIUM",
    "airport": "MEDIUM",
    "shipment": "MEDIUM",
    "police": "LOW",
    "court": "LOW",
}

# 📰 Get live news
def get_live_news():
    items = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:15]:
            items.append({
                "title": entry.get("title", "No title"),
                "url": entry.get("link", "#"),
                "summary": entry.get("summary", "")
            })

    # 🔍 Fiji-focused filter
    filtered = []
    for item in items:
        text = f"{item['title']} {item['summary']}".lower()

        if any(word in text for word in ["fiji", "suva"]):
            filtered.append(item)

    return filtered[:20]

# 🚨 Build alerts
def build_alerts(news_items):
    alerts = []

    for item in news_items:
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()

        for keyword, risk in KEYWORDS.items():
            if keyword in text:
                alerts.append({
                    "keyword": keyword,
                    "risk": risk,
                    "title": item["title"],
                    "url": item["url"]
                })

    return alerts

# 🏠 Home route
@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "God's Eye backend is running"
    })

# 📰 News route
@app.route("/news")
def news():
    return jsonify(get_live_news())

# 🚨 Alerts route
@app.route("/alerts")
def alerts():
    news_items = get_live_news()
    return jsonify(build_alerts(news_items))

# ▶️ Run server
if __name__ == "__main__":
    app.run(debug=True, port=5000)
