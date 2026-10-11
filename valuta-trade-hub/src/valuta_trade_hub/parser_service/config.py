import os
from pathlib import Path

from ..infra.settings import SettingsLoader


class ParserConfig:
    """Конфигурация сервиса парсинга курсов."""

    EXCHANGERATE_API_KEY: str | None = os.getenv("EXCHANGERATE_API_KEY")

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = SettingsLoader().get_pivot_currency()
    FIAT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict[str, str] = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    }
    ID_CRYPTO_MAP: dict[str, str] = {
        raw_id: code for code, raw_id in CRYPTO_ID_MAP.items()
    }

    RATES_FILE_PATH: Path = SettingsLoader().get_db_rates_path()
    HISTORY_FILE_PATH: Path = SettingsLoader().get_db_history_path()
    REQUEST_TIMEOUT: int = 10
