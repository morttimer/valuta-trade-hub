from pathlib import Path

DB_DIR = Path(__file__).resolve().parents[3] / "data/"
DB_PORTFOLIOS = DB_DIR / "portfolios.json"
DB_RATES = DB_DIR / "rates.json"
DB_USERS = DB_DIR / "users.json"

PIVOT_CURRENCY = "USD"
