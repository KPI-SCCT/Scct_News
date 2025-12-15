# config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

LOG_DIR = BASE_DIR / "logs"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"

for d in (LOG_DIR, STATIC_DIR, TEMPLATES_DIR, DATA_DIR):
    d.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "news.db"

APP_LOG_FILE = LOG_DIR / "app.log"
SCRAPER_LOG_FILE = LOG_DIR / "scraper.log"
