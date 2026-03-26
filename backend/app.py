from flask import Flask, jsonify
from flask_cors import CORS
from modules.news import get_news
from modules.alerts import get_alerts

app = Flask(__name__)
CORS(app)

@app.route("/news")
def news():
    return jsonify(get_news())

@app.route("/alerts")
def alerts():
    return jsonify(get_alerts())

if __name__ == "__main__":
    app.run(debug=True)
