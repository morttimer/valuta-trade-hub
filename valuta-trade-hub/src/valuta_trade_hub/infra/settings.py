from pathlib import Path
from typing import Any, Self

from ..core.constants import DB_DIR, DB_SETTINGS
from ..core.utils import load_json

_MISSING = object()


# Singleton через __new__: проще и читабельнее, чем метакласс.
class SettingsLoader:
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
        return self.get("rates_ttl_seconds")

    def get_log_file_dir(self) -> Path:
        return DB_DIR / self.get("log_dir")

    def get_log_level(self) -> str:
        return self.get("log_level")

    def get_log_max_file_size_mb(self) -> int:
        return self.get("log_max_file_size_mb")

    def get_log_format(self) -> str:
        return self.get("log_format")

    def get_db_users_path(self) -> Path:
        return DB_DIR / self.get("db_users_path")

    def get_db_rates_path(self) -> Path:
        return DB_DIR / self.get("db_rates_path")

    def get_db_ports_path(self) -> Path:
        return DB_DIR / self.get("db_ports_path")

    def get_pivot_currency(self) -> str:
        return self.get("pivot_currency")

    def get_default_base_currency(self) -> str:
        return self.get("default_base_currency")

    @staticmethod
    def _load_settings() -> dict:
        return load_json(DB_SETTINGS)
