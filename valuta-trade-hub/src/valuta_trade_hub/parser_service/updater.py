import logging

from ..core.exceptions import ApiRequestError
from ..logging_config import PARSER_LOGGER_NAME
from .api_clients import BaseApiClient
from .storage import RatesStorage

logger = logging.getLogger(PARSER_LOGGER_NAME)


class UpdateResult:
    """Результат обновления курсов."""

    def __init__(
        self, updated_count: int, last_refresh: str | None, errors: list
    ) -> None:
        self.updated_count = updated_count
        self.last_refresh = last_refresh
        self.errors = errors


class RatesUpdater:
    """Координатор обновления курсов из внешних API."""

    def __init__(
        self, clients: list[BaseApiClient], storage: RatesStorage
    ) -> None:
        self._clients = clients
        self._storage = storage

    def run_update(self) -> UpdateResult:
        """Опрашивает всех клиентов и сохраняет полученные курсы."""
        logger.info("Starting rates update...")
        all_rates = {"pairs": {}}
        errors = []
        for client in self._clients:
            try:
                pairs = client.fetch_rates()["pairs"]
            except ApiRequestError as e:
                logger.error("Failed to fetch from %s: %s", client.source, e)
                errors.append(str(e))
                continue
            logger.info(
                "Fetching from %s... OK (%d rates)", client.source, len(pairs)
            )
            all_rates["pairs"] |= pairs

        updated_count = len(all_rates["pairs"])
        if updated_count == 0:
            return UpdateResult(0, None, errors)

        logger.info(
            "Writing %d rates to %s...",
            updated_count,
            self._storage.rates_path.name,
        )
        last_refresh = self._storage.save_rates(all_rates)
        return UpdateResult(updated_count, last_refresh, errors)
