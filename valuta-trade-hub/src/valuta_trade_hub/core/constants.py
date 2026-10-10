from pathlib import Path

DB_DIR = Path(__file__).resolve().parents[3] / "data/"
DB_SETTINGS = DB_DIR / "config.json"
LOG_JSON_FILE = "log.json"
LOG_STRING_FILE = "log.txt"
