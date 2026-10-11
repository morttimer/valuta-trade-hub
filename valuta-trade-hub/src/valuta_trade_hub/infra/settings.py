from pathlib import Path
from typing import Any, Self

from ..core.constants import DB_DIR, DB_SETTINGS
from ..core.utils import load_json

_MISSING = object()

DEFAULT_SETTINGS = {
    "rates_ttl_seconds": 300,
    "db_users_path": "users.json",
    "db_rates_path": "rates.json",
    "db_ports_path": "portfolios.json",
    "db_history_path": "exchange_rates.json",
    "pivot_currency": "USD",
    "default_base_currency": "USD",
    "log_level": "INFO",
    "log_max_file_size_mb": 512,
    "log_format": "str",
    "log_dir": "logs",
}


# Singleton через __new__: проще и читабельнее, чем метакласс.
class SettingsLoader:
    """Загрузчик конфигурации проекта."""

    __instance = None

    def __new__(cls) -> Self:
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance._settings = SettingsLoader._load_settings()

        return cls.__instance

    def get(self, key: str, default: Any = _MISSING) -> Any:
        """Возвращает значение параметра конфигурации."""
        if key in self._settings:
            return self._settings[key]
        if default is _MISSING:
            raise KeyError(f"В конфигурации отсутствует ключ '{key}'")
        return default

    def get_rates_ttl_seconds(self) -> int:
        """Возвращает срок актуальности кеша курсов в секундах."""
        return self.get("rates_ttl_seconds")

    def get_log_file_dir(self) -> Path:
        """Возвращает каталог журналов."""
        return DB_DIR / self.get("log_dir")

    def get_log_level(self) -> str:
        """Возвращает уровень логирования."""
        return self.get("log_level")

    def get_log_max_file_size_mb(self) -> int:
        """Возвращает максимальный размер файла журнала в мегабайтах."""
        return self.get("log_max_file_size_mb")

    def get_log_format(self) -> str:
        """Возвращает формат журнала."""
        return self.get("log_format")

    def get_db_users_path(self) -> Path:
        """Возвращает путь к файлу пользователей."""
        return DB_DIR / self.get("db_users_path")

    def get_db_rates_path(self) -> Path:
        """Возвращает путь к кешу курсов."""
        return DB_DIR / self.get("db_rates_path")

    def get_db_ports_path(self) -> Path:
        """Возвращает путь к файлу портфелей."""
        return DB_DIR / self.get("db_ports_path")

    def get_db_history_path(self) -> Path:
        """Возвращает путь к истории курсов."""
        return DB_DIR / self.get("db_history_path")

    def get_pivot_currency(self) -> str:
        """Возвращает опорную валюту."""
        return self.get("pivot_currency")

    def get_default_base_currency(self) -> str:
        """Возвращает базовую валюту по умолчанию."""
        return self.get("default_base_currency")

    @staticmethod
    def _load_settings() -> dict:
        return load_json(DB_SETTINGS, DEFAULT_SETTINGS)
