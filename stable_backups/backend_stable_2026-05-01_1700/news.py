import requests

def get_news():
    url = "https://newsapi.org/v2/everything?q=fiji&apiKey=YOUR_API_KEY"
    
    response = requests.get(url)
    data = response.json()

    articles = []

    for article in data.get("articles", [])[:5]:
        articles.append({
            "title": article["title"],
            "url": article["url"]
        })

    return articles
