from kvk_data_service_experiment.service import KVKDataService

from .conftest import FakeKVKClient


class TestKVKDataService:
    def test_get_registration_delegates_to_client(self, service: KVKDataService, fake_client: FakeKVKClient) -> None:
        # Act
        service.get_registration(kvk_number="90000013", rsin="992177315")

        # Assert
        assert fake_client.calls == [("get_registration", {"kvk_number": "90000013", "rsin": "992177315"})]

    def test_get_branch_delegates_to_client(self, service: KVKDataService, fake_client: FakeKVKClient) -> None:
        # Act
        service.get_branch(branch_number="990000764192", kvk_number="90000250")

        # Assert
        assert fake_client.calls == [
            ("get_branch", {"branch_number": "990000764192", "kvk_number": "90000250", "rsin": None})
        ]

    def test_get_financial_years_delegates_to_get_available_financial_years(
        self, service: KVKDataService, fake_client: FakeKVKClient
    ) -> None:
        # Act
        service.get_financial_years(kvk_number="99000148")

        # Assert
        assert fake_client.calls == [("get_available_financial_years", {"kvk_number": "99000148"})]

    def test_get_financial_statement_delegates_to_client(
        self, service: KVKDataService, fake_client: FakeKVKClient
    ) -> None:
        # Act
        service.get_financial_statement(depot_id="-386e3edc:17fda168cb1:d75")

        # Assert
        assert fake_client.calls == [("get_financial_statement", {"depot_id": "-386e3edc:17fda168cb1:d75"})]

    def test_get_ubo_delegates_to_get_ubo_register(self, service: KVKDataService, fake_client: FakeKVKClient) -> None:
        # Act
        service.get_ubo(kvk_number="81408269")

        # Assert
        assert fake_client.calls == [("get_ubo_register", {"kvk_number": "81408269"})]

    def test_get_extract_delegates_to_client(self, service: KVKDataService, fake_client: FakeKVKClient) -> None:
        # Act
        service.get_extract(kvk_number="90006208", rsin="867240465")

        # Assert
        assert fake_client.calls == [("get_extract", {"kvk_number": "90006208", "rsin": "867240465"})]

    def test_returns_client_result(self, service: KVKDataService) -> None:
        # Act
        result = service.get_registration(kvk_number="90000013")

        # Assert
        assert result["method"] == "get_registration"
        assert result["kvk_number"] == "90000013"
