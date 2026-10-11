import logging
import sys

from .infra.settings import SettingsLoader

PARSER_LOGGER_NAME = "valutatrade.parser"


def setup_parser_logging() -> None:
    """Настраивает вывод журнала сервиса парсинга в консоль."""
    logger = logging.getLogger(PARSER_LOGGER_NAME)
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(SettingsLoader().get_log_level())
    logger.propagate = False
