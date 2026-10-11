import logging
import threading

from ..logging_config import PARSER_LOGGER_NAME
from .updater import RatesUpdater

logger = logging.getLogger(PARSER_LOGGER_NAME)


class RatesScheduler:
    """Планировщик периодического обновления курсов."""

    def __init__(self, updater: RatesUpdater, interval_seconds: int) -> None:
        self._updater = updater
        self._interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Запускает периодическое обновление курсов."""
        if self.is_running:
            raise ValueError("Планировщик обновления курсов уже запущен")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Останавливает периодическое обновление курсов."""
        if not self.is_running:
            raise ValueError("Планировщик обновления курсов не запущен")
        self._stop_event.set()
        self._thread.join()
        self._thread = None

    def _run(self) -> None:
        """Выполняет обновление курсов с заданным интервалом до остановки."""
        while not self._stop_event.is_set():
            try:
                self._updater.run_update()
            except Exception:
                logger.exception("Scheduled rates update failed")
            self._stop_event.wait(self._interval_seconds)
