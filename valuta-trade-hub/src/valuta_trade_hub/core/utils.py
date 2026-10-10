import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    """Читает данные из JSON-файла."""
    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Файл не найден: {path}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Некорректный JSON в файле {path}") from e


def save_json(path: Path, data: list) -> None:
    """Записывает данные в JSON-файл."""
    with path.open(mode="w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
