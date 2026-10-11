class CurrencyNotFoundError(ValueError):
    """Ошибка неизвестной валюты."""

    def __init__(self, code: str) -> None:
        super().__init__(f"Неизвестная валюта '{code}'")


class InsufficientFundsError(ValueError):
    """Ошибка недостатка средств в кошельке."""

    def __init__(self, available: float, required: float, code: str) -> None:
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )


class ApiRequestError(Exception):
    """Ошибка обращения к внешнему API."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
