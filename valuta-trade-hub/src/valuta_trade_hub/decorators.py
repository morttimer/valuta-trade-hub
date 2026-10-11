import inspect
import json
from functools import wraps
from pathlib import Path

from .core.constants import LOG_JSON_FILE, LOG_STRING_FILE
from .core.utils import now_iso
from .infra.settings import SettingsLoader


def log_action(action_name, level=None):
    """Логирует вызов доменной операции и ее результат."""

    def outer(func):
        settings = SettingsLoader()
        log_level = level if level else settings.get_log_level()
        log_file_dir = settings.get_log_file_dir()
        log_format = settings.get_log_format()
        signature = inspect.signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            params = bound.arguments
            exception = False
            try:
                return func(*args, **kwargs)
            except Exception:
                exception = True
                raise
            finally:
                user = params.get("user")
                log_line_dict = {
                    "log_level": log_level,
                    "current_datetime": now_iso(),
                    "action_name": action_name.upper(),
                    "username": user.username if user else None,
                    "currency": params.get("currency"),
                    "amount": params.get("amount"),
                    "result": "ERROR" if exception else "OK",
                }
                _write_log(log_line_dict, log_file_dir, log_format)

        return wrapper

    return outer


def _write_log(
    log_line_dict: dict, log_file_dir: Path, log_format: str
) -> None:
    """Записывает запись лога в файл заданного формата."""
    log_file_dir.mkdir(parents=True, exist_ok=True)
    if log_format.upper() == "JSON":
        _write_json_log(log_line_dict, log_file_dir / LOG_JSON_FILE)
    else:
        _write_txt_log(log_line_dict, log_file_dir / LOG_STRING_FILE)


def _write_json_log(log_line_dict: dict, file_path: Path) -> None:
    """Дописывает запись лога в файл в формате JSON Lines."""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_line_dict, ensure_ascii=False))
        f.write("\n")


def _write_txt_log(log_line_dict: dict, file_path: Path) -> None:
    """Дописывает запись лога в файл в строковом формате."""
    log_line = (
        f"{log_line_dict['log_level']} "
        f"{log_line_dict['current_datetime']} "
        f"{log_line_dict['action_name']} "
        f"user='{log_line_dict['username']}' "
        f"currency='{log_line_dict['currency']}' "
        f"amount='{log_line_dict['amount']}' "
        f"result='{log_line_dict['result']}'"
    )
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(log_line)
        f.write("\n")
