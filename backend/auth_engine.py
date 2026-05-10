import os
import secrets
from functools import wraps
from flask import request, jsonify

ADMIN_TOKEN = os.getenv("GODSEYE_ADMIN_TOKEN") or secrets.token_hex(24)

def get_admin_token():
    return ADMIN_TOKEN

def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-GODSEYE-TOKEN") or request.args.get("token")

        if token != ADMIN_TOKEN:
            return jsonify({
                "error": "Unauthorized",
                "message": "Valid God’s Eye admin token required."
            }), 401

        return fn(*args, **kwargs)

    return wrapper
