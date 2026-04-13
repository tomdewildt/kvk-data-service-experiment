import pytest

from kvk_data_service_experiment.client import create_kvk_client
from kvk_data_service_experiment.config import config
from kvk_data_service_experiment.service import KVKDataService


@pytest.mark.integration()
class TestKVKDataServiceIntegration:
    @pytest.fixture()
    def service(self) -> KVKDataService:
        client = create_kvk_client(config)
        return KVKDataService(client)

    @pytest.mark.parametrize(
        ("kvk_number", "rsin"),
        [
            ("90000013", "992177315"),
            ("90000021", None),
            ("90000552", "992063863"),
        ],
        ids=["cv-with-diacritic", "eenmanszaak-3-branches", "bv-foreign-address"],
    )
    def test_get_registration(self, service: KVKDataService, kvk_number: str, rsin: str | None) -> None:
        # Act
        result = service.get_registration(kvk_number=kvk_number, rsin=rsin)

        # Assert
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.parametrize(
        ("branch_number", "kvk_number"),
        [
            ("990000764192", "90000250"),
            ("990000489902", "90000021"),
        ],
        ids=["commercial-branch", "commercial-branch-eenmanszaak"],
    )
    def test_get_branch(self, service: KVKDataService, branch_number: str, kvk_number: str) -> None:
        # Act
        result = service.get_branch(branch_number=branch_number, kvk_number=kvk_number)

        # Assert
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.parametrize(
        "kvk_number",
        ["99000148", "99000156", "99000164", "99000172"],
        ids=["micro-preliminary", "small-corrected", "medium-definitive", "large-corrected"],
    )
    def test_get_financial_years(self, service: KVKDataService, kvk_number: str) -> None:
        # Act
        result = service.get_financial_years(kvk_number=kvk_number)

        # Assert
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.parametrize(
        "depot_id",
        [
            "-386e3edc:17fda168cb1:d75",
            "49984362:17fda19091e:27ea",
            "49984362:17fda19091e:-343",
            "-386e3edc:17fda29dd8e:-3809",
        ],
        ids=["micro-2018", "small-2019", "medium-2020", "large-2021"],
    )
    def test_get_financial_statement(self, service: KVKDataService, depot_id: str) -> None:
        # Act
        result = service.get_financial_statement(depot_id=depot_id)

        # Assert
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.parametrize(
        "kvk_number",
        ["81408269", "81408420", "81408382"],
        ids=["bv-75-percent", "cv-foreign-tin", "stichting-shielded"],
    )
    def test_get_ubo(self, service: KVKDataService, kvk_number: str) -> None:
        # Act
        result = service.get_ubo(kvk_number=kvk_number)

        # Assert
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.parametrize(
        ("kvk_number", "rsin"),
        [
            ("90006208", "867240465"),
            ("90006216", "867240398"),
        ],
        ids=["extract-english-1", "extract-english-2"],
    )
    def test_get_extract(self, service: KVKDataService, kvk_number: str, rsin: str) -> None:
        # Act
        result = service.get_extract(kvk_number=kvk_number, rsin=rsin)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
