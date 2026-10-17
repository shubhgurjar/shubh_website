import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"

# Ensure essential directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "career_hub.db"
SEED_PATH = DATA_DIR / "seed_data.json"

# Auth configuration
SECRET_KEY = os.getenv("CAREER_HUB_SECRET", "career-hub-super-secret-key-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
COOKIE_NAME = "career_hub_token"
DEFAULT_MASTER_PASSWORD = os.getenv("CAREER_HUB_PASSWORD", "admin123")
