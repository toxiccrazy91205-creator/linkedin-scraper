import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "linkedin-scraper-dev-key-change-me")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", 45))  # Enforced max 45 seconds timeout per user request
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))           # Max 3 retries
