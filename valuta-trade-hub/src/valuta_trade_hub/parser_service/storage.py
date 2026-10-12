import datetime
import threading
from pathlib import Path

from ..core.models import RateInfo
from ..core.utils import load_json, now_iso, save_json
from .config import ParserConfig


class RatesStorage:
    """Хранилище кеша и истории курсов."""

    _lock = threading.RLock()

    def __init__(self, config: ParserConfig) -> None:
        self._config = config

    @property
    def rates_path(self) -> Path:
        return self._config.RATES_FILE_PATH

    def load_rates(self) -> dict:
        """Читает текущий снимок курсов из rates.json."""
        return RateInfo.load_rate_info().to_dict()

    def save_rates(self, rates: dict) -> str:
        """Сохраняет снимок текущих курсов в rates.json."""
        with RatesStorage._lock:
            existed_rates = self.load_rates()

            current_time = now_iso()
            result = dict()
            old_pairs = existed_rates["pairs"]
            new_pairs = rates["pairs"]

            merged = dict(old_pairs)
            for key, new_pair in new_pairs.items():
                old_pair = merged.get(key)
                if old_pair is None or (
                    datetime.datetime.fromisoformat(new_pair["updated_at"])
                    > datetime.datetime.fromisoformat(old_pair["updated_at"])
                ):
                    merged[key] = new_pair

            result["pairs"] = merged

            result["last_refresh"] = current_time
            RateInfo.save_rates(result)
            self.append_history(result)
            return current_time

    @staticmethod
    def _create_history_id(curr_from: str, curr_to: str, time) -> str:
        return f"{curr_from}_{curr_to}_{time}"

    def append_history(self, rates: dict) -> None:
        """Добавляет записи измерений в exchange_rates.json без дубликатов."""
        with RatesStorage._lock:
            history_path = self._config.HISTORY_FILE_PATH
            history = load_json(history_path, [])
            positions = {record["id"]: i for i, record in enumerate(history)}

            for key, pair in rates["pairs"].items():
                curr_from, _, curr_to = key.partition("_")
                record_id = RatesStorage._create_history_id(
                    curr_from, curr_to, pair["updated_at"]
                )
                record = {
                    "id": record_id,
                    "from_currency": curr_from,
                    "to_currency": curr_to,
                    "rate": pair["rate"],
                    "timestamp": pair["updated_at"],
                    "source": pair["source"],
                }

                if record_id in positions:
                    history[positions[record_id]] = record
                else:
                    positions[record_id] = len(history)
                    history.append(record)

            save_json(history_path, history)
