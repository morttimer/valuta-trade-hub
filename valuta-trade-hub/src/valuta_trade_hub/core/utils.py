import copy
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    """Возвращает текущее время в формате ISO с точностью до секунд."""
    return to_iso(datetime.now())


def to_iso(value: datetime) -> str:
    """Форматирует время в ISO с точностью до секунд."""
    return value.isoformat(timespec="seconds")


_MISSING = object()


def load_json(path: Path, default: Any = _MISSING) -> Any:
    """Читает данные из JSON-файла, создавая его со значением по умолчанию."""
    if default is not _MISSING and not path.exists():
        save_json(path, default)
        return copy.deepcopy(default)
    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Файл не найден: {path}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Некорректный JSON в файле {path}") from e


def save_json(path: Path, data: dict | list) -> None:
    """Атомарно записывает данные в JSON-файл через временный файл."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, mode="w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
    except BaseException:
        os.unlink(tmp_name)
        raise
