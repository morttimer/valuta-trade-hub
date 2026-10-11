from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Базовый класс валюты."""

    def __init__(self, curr_name: str, curr_code: str) -> None:
        self.name = curr_name
        self.code = curr_code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает строковое представление валюты для UI и логов."""
        pass

    @staticmethod
    def _is_code_valid(value: str) -> bool:
        return (
            isinstance(value, str)
            and 2 <= len(value) <= 5
            and value.find(" ") == -1
            and value.isupper()
        )

    @staticmethod
    def _is_name_valid(value: str) -> bool:
        return isinstance(value, str) and value.strip() != ""

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @code.setter
    def code(self, value: str) -> None:
        if not Currency._is_code_valid(value):
            raise ValueError(
                "Код валюты должен быть в верхнем регистре, 2-5 символов, "
                f"без пробелов: '{value}'"
            )

        self._code = value

    @name.setter
    def name(self, value: str) -> None:
        if not Currency._is_name_valid(value):
            raise ValueError("Название валюты не может быть пустым")

        self._name = value


class CurrencyRegistry:
    """Реестр поддерживаемых валют."""

    def __init__(self):
        self._currencies = []
        self.add_currency(FiatCurrency("US Dollar", "USD", "United States"))
        self.add_currency(FiatCurrency("Euro", "EUR", "Eurozone"))
        self.add_currency(FiatCurrency("Russian Ruble", "RUB", "Russia"))
        self.add_currency(CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12))
        self.add_currency(CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11))
        self.add_currency(
            FiatCurrency("British Pound", "GBP", "United Kingdom")
        )
        self.add_currency(
            CryptoCurrency("Solana", "SOL", "Proof of History", 6.0e10)
        )

    def add_currency(self, currency: Currency) -> None:
        """Добавляет валюту в реестр."""
        if any(c.code == currency.code for c in self._currencies):
            raise ValueError(f"Валюта '{currency.code}' уже есть в реестре")
        else:
            self._currencies.append(currency)

    def get_currency(self, code: str) -> Currency:
        """Возвращает валюту по коду."""
        target = next((c for c in self._currencies if c.code == code), None)
        if target is None:
            raise CurrencyNotFoundError(code)
        return target


class FiatCurrency(Currency):
    """Фиатная валюта."""

    def __init__(
        self, curr_name: str, curr_code: str, curr_issuer: str
    ) -> None:
        super().__init__(curr_name, curr_code)
        self.issuing_country = curr_issuer

    @staticmethod
    def _is_issuer_valid(value):
        return isinstance(value, str) and value.strip() != ""

    @property
    def issuing_country(self) -> str:
        return self._issuing_country

    @issuing_country.setter
    def issuing_country(self, value: str) -> None:
        if not FiatCurrency._is_issuer_valid(value):
            raise ValueError("Страна эмиссии не может быть пустой")

        self._issuing_country = value

    def get_display_info(self) -> str:
        """Возвращает строковое представление фиатной валюты."""
        return (
            f"[FIAT] {self.code} — {self.name} "
            f"(Issuing: {self.issuing_country})"
        )


class CryptoCurrency(Currency):
    """Криптовалюта."""

    def __init__(
        self, curr_name: str, curr_code: str, crypto_algo: str, last_cap: float
    ) -> None:
        super().__init__(curr_name, curr_code)
        self.algorithm = crypto_algo
        self.market_cap = last_cap

    @staticmethod
    def _is_market_cap_valid(value):
        return not isinstance(value, bool) and isinstance(value, (float, int))

    @staticmethod
    def _is_algo_valid(value):
        return isinstance(value, str) and value.strip() != ""

    @property
    def market_cap(self) -> float:
        return self._market_cap

    @market_cap.setter
    def market_cap(self, value) -> None:
        if not CryptoCurrency._is_market_cap_valid(value):
            raise TypeError("Капитализация должна быть числом")
        self._market_cap = float(value)

    @property
    def algorithm(self) -> str:
        return self._algorithm

    @algorithm.setter
    def algorithm(self, value: str) -> None:
        if not CryptoCurrency._is_algo_valid(value):
            raise ValueError("Алгоритм криптовалюты не может быть пустым")

        self._algorithm = value

    def get_display_info(self) -> str:
        """Возвращает строковое представление криптовалюты."""
        market_cap = f"{self.market_cap:.2e}".replace("e+", "e")
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {market_cap})"
        )
