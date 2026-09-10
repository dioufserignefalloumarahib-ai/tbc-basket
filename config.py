from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database" / "tbc.db"
SECRET_KEY = os.environ.get("SECRET_KEY", "tbc-development-key-change-me")
NBA_API_KEY = os.environ.get("NBA_API_KEY", "")
NBA_API_BASE_URL = os.environ.get("NBA_API_BASE_URL", "")
