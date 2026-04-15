from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from routes import health_bp, vessels_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(vessels_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Internal server error", "details": str(error)}), 500

    return app


app = create_app()

if __name__ == "__main__":
    print(f"Starting {Config.APP_NAME} on port {Config.PORT}")
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
