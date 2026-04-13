from typing import Any

from kvk_data_service_experiment.client import KVKClient


class KVKDataService:
    def __init__(self, client: KVKClient):
        self._client = client

    def get_branch(
        self,
        *,
        branch_number: str | None = None,
        kvk_number: str | None = None,
        rsin: str | None = None,
    ) -> dict[str, Any]:
        return self._client.get_branch(branch_number=branch_number, kvk_number=kvk_number, rsin=rsin)

    def get_extract(self, *, kvk_number: str | None = None, rsin: str | None = None) -> dict[str, Any]:
        return self._client.get_extract(kvk_number=kvk_number, rsin=rsin)

    def get_financial_years(self, *, kvk_number: str) -> dict[str, Any]:
        return self._client.get_available_financial_years(kvk_number=kvk_number)

    def get_financial_statement(self, *, depot_id: str) -> dict[str, Any]:
        return self._client.get_financial_statement(depot_id=depot_id)

    def get_registration(self, *, kvk_number: str | None = None, rsin: str | None = None) -> dict[str, Any]:
        return self._client.get_registration(kvk_number=kvk_number, rsin=rsin)

    def get_ubo(self, *, kvk_number: str) -> dict[str, Any]:
        return self._client.get_ubo_register(kvk_number=kvk_number)
