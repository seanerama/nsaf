#!/usr/bin/env python3
"""NSAF Flask App — Idea selection, QA review, and Webex bot."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from flask import Flask

from shared.db import get_db

app = Flask(__name__)


def init_app():
    """Initialize database connection and register routes."""
    get_db()

    from routes.select import select_bp
    from routes.review import review_bp
    from routes.webex import webex_bp

    app.register_blueprint(select_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(webex_bp)


init_app()


@app.errorhandler(404)
def not_found(e):
    return {"error": "Not found"}, 404


@app.errorhandler(500)
def server_error(e):
    return {"error": "Internal server error"}, 500


if __name__ == "__main__":
    host = os.environ.get("NSAF_FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("NSAF_FLASK_PORT", "5000"))
    app.run(host=host, port=port, debug=True)
