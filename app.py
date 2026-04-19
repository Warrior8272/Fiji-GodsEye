from flask import Flask, jsonify
from modules.news import get_news

app = Flask(__name__)

@app.route("/news")
def news():
    return jsonify(get_news())

if __name__ == "__main__":
    app.run(debug=True)
