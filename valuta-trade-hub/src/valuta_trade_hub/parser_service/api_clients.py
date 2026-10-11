import json
from abc import ABC, abstractmethod

import requests

from ..core.exceptions import ApiRequestError
from ..core.utils import now_iso
from .config import ParserConfig


class BaseApiClient(ABC):
    """Базовый клиент внешнего API курсов валют."""

    source: str

    def __init__(self, config: ParserConfig) -> None:
        self._config = config

    def fetch_rates(self) -> dict:
        """Возвращает курсы в формате {"pairs": {"BTC_USD": {...}, ...}}."""
        try:
            rates = self._fetch_pair_rates()
        except requests.exceptions.RequestException as e:
            raise self._network_error() from e
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise self._invalid_response_error() from e

        updated_at = now_iso()
        return {
            "pairs": {
                pair: {
                    "rate": rate,
                    "source": self.source,
                    "updated_at": updated_at,
                }
                for pair, rate in rates.items()
            }
        }

    @abstractmethod
    def _fetch_pair_rates(self) -> dict[str, float]:
        """Запрашивает курсы у API."""

    def _assert_rate_value(self, value: object) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value <= 0
        ):
            raise ApiRequestError(
                f"{self.source}: некорректное значение курса '{value}'"
            )

    def _status_error(
        self, status_code: int, reason: str | None = None
    ) -> ApiRequestError:
        """Создает ошибку по коду ответа API."""
        if status_code in (401, 403):
            message = "неверный API-ключ"
        elif status_code == 429:
            message = "превышен лимит запросов, повторите попытку позже"
        else:
            message = f"код ответа {status_code}"
        if reason:
            message += f" ({reason})"
        return ApiRequestError(f"{self.source}: {message}")

    def _network_error(self) -> ApiRequestError:
        return ApiRequestError(f"{self.source}: сетевая ошибка")

    def _invalid_response_error(self) -> ApiRequestError:
        return ApiRequestError(f"{self.source}: некорректный формат ответа")


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko для курсов криптовалют."""

    source: str = "CoinGecko"

    def _fetch_pair_rates(self) -> dict[str, float]:
        base = self._config.BASE_CURRENCY
        vs_currency = base.lower()
        ids = ",".join(
            self._config.CRYPTO_ID_MAP[code]
            for code in self._config.CRYPTO_CURRENCIES
        )
        resp = requests.get(
            self._config.COINGECKO_URL,
            params={"ids": ids, "vs_currencies": vs_currency},
            timeout=self._config.REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            raise self._status_error(resp.status_code)

        rates = {}
        for raw_id, value in json.loads(resp.content).items():
            code = self._config.ID_CRYPTO_MAP.get(raw_id)
            if code is None:
                continue
            self._assert_rate_value(value[vs_currency])
            rates[f"{code}_{base}"] = value[vs_currency]
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API для курсов фиатных валют."""

    source: str = "ExchangeRate-API"

    @staticmethod
    def _error_type(resp: requests.Response) -> str | None:
        """Возвращает тип ошибки из тела ответа, если его удается прочитать."""
        try:
            return json.loads(resp.content).get("error-type")
        except (ValueError, AttributeError):
            return None

    def _fetch_pair_rates(self) -> dict[str, float]:
        base = self._config.BASE_CURRENCY
        url = (
            f"{self._config.EXCHANGERATE_API_URL}/"
            f"{self._config.EXCHANGERATE_API_KEY}/latest/{base}"
        )
        resp = requests.get(url, timeout=self._config.REQUEST_TIMEOUT)
        if resp.status_code != 200:
            raise self._status_error(resp.status_code, self._error_type(resp))

        response_body = json.loads(resp.content)
        if response_body["result"] != "success":
            raise self._status_error(
                resp.status_code, response_body.get("error-type")
            )

        rates = {}
        for code, value in response_body["conversion_rates"].items():
            if code not in self._config.FIAT_CURRENCIES or code == base:
                continue
            self._assert_rate_value(value)
            rates[f"{code}_{base}"] = 1 / value
        return rates
