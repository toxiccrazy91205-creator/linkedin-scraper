"""
LinkedIn Scraper — Flask Web Application

A production-ready web interface for the LinkedIn Scraper.
"""

import os
import atexit
from flask import Flask, render_template
from flask_cors import CORS

from config import Config
from logger import app_logger
from routes import api_bp
from services import shutdown_scraper

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
CORS(app)

# Register API Blueprint
app.register_blueprint(api_bp)

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the single-page application."""
    return render_template("index.html")

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

atexit.register(shutdown_scraper)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app_logger.info(f"Starting LinkedIn Scraper Web App on port {Config.PORT}")
    app_logger.info(f"Open http://localhost:{Config.PORT} in your browser")
    
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG, threaded=True)
