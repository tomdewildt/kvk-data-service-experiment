import uuid
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from requests import Session
from zeep import CachingClient, Settings
from zeep.helpers import serialize_object
from zeep.transports import Transport

from kvk_data_service_experiment.addressing import KVKWSAddressingPlugin
from kvk_data_service_experiment.cache import XmlFileCache
from kvk_data_service_experiment.config import Environment, KVKDataServiceConfig
from kvk_data_service_experiment.signature import KVKBinarySignature

WSDL_CATALOGUS = "http://schemas.kvk.nl/contracts/kvk/dataservice/catalogus/2015/02/KVK-KvKDataservice.wsdl"
WSDL_JAARREKENING = "http://schemas.kvk.nl/contracts/kvk/opvragenjaarrekening/2018/01/kvk-Opvragenjaarrekening.wsdl"
WSDL_UBO = "http://schemas.kvk.nl/contracts/kvk/ubo/2018/01/kvk-opvragenKvkUittrekselUboRegister.wsdl"
WSDL_UITTREKSEL = "http://schemas.kvk.nl/contracts/kvk/kvkhandelsregisteruittreksel/2020/01/kvk-opvragenKvkHandelsregisterUittreksel.wsdl"
ENDPOINTS = {
    Environment.PREPROD: "https://dataservice.preprod.kvk.nl",
    Environment.PROD: "https://dataservice.kvk.nl",
}


class KVKClient(ABC):
    @abstractmethod
    def get_available_financial_years(self, *, kvk_number: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_branch(
        self,
        *,
        branch_number: str | None = None,
        kvk_number: str | None = None,
        rsin: str | None = None,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_extract(self, *, kvk_number: str | None = None, rsin: str | None = None) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_financial_statement(self, *, depot_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_registration(self, *, kvk_number: str | None = None, rsin: str | None = None) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_ubo_register(self, *, kvk_number: str) -> dict[str, Any]:
        pass


class ZeepKVKClient(KVKClient):
    def __init__(self, config: KVKDataServiceConfig):
        session = Session()
        session.cert = (str(config.CERT_PATH), str(config.KEY_PATH))
        session.verify = str(config.CA_BUNDLE_PATH)

        cache = XmlFileCache(config.CACHE_DIR) if config.CACHE_DIR else None
        transport = Transport(session=session, cache=cache)

        settings = Settings()
        settings.strict = False  # type: ignore[assignment]
        settings.xml_huge_tree = True  # type: ignore[assignment]

        wsse = KVKBinarySignature(config.KEY_PATH, config.CERT_PATH)
        plugins = [KVKWSAddressingPlugin(config.ENV)]
        endpoint = ENDPOINTS[config.ENV]

        self._catalogus = self._create_client(WSDL_CATALOGUS, transport, wsse, settings, plugins, endpoint)
        self._jaarrekening = self._create_client(WSDL_JAARREKENING, transport, wsse, settings, plugins, endpoint)
        self._ubo = self._create_client(WSDL_UBO, transport, wsse, settings, plugins, endpoint)
        self._uittreksel = self._create_client(WSDL_UITTREKSEL, transport, wsse, settings, plugins, endpoint)

    @staticmethod
    def _create_client(
        wsdl: str,
        transport: Transport,
        wsse: KVKBinarySignature,
        settings: Settings,
        plugins: list[KVKWSAddressingPlugin],
        endpoint: str,
    ) -> CachingClient:
        client = CachingClient(wsdl, transport=transport, wsse=wsse, settings=settings, plugins=plugins)
        client.service._binding_options["address"] = endpoint
        return client

    def get_available_financial_years(self, *, kvk_number: str) -> dict[str, Any]:
        logger.info("Fetching available financial years (kvk_number={})", kvk_number)
        response = self._jaarrekening.service.opvragenBeschikbareBoekjaren(
            klantreferentie=self._reference(),
            kvkNummer=kvk_number,
        )
        return self._serialize(response)

    def get_branch(
        self,
        *,
        branch_number: str | None = None,
        kvk_number: str | None = None,
        rsin: str | None = None,
    ) -> dict[str, Any]:
        logger.info(
            "Fetching branch (branch_number={}, kvk_number={}, rsin={})",
            branch_number,
            kvk_number,
            rsin,
        )
        if branch_number:
            choice = {"vestigingsnummer": branch_number}
        elif kvk_number:
            choice = {"kvkNummer": kvk_number}
        else:
            choice = {"rsin": rsin}
        response = self._catalogus.service.ophalenVestiging(
            klantreferentie=self._reference(),
            **choice,
        )
        return self._serialize(response)

    def get_extract(self, *, kvk_number: str | None = None, rsin: str | None = None) -> dict[str, Any]:
        logger.info("Fetching business register extract (kvk_number={}, rsin={})", kvk_number, rsin)
        choice = {"kvkNummer": kvk_number} if kvk_number else {"rsin": rsin}
        response = self._uittreksel.service.opvragenkvkhandelsregisteruitreksel(
            **choice,
        )
        return self._serialize(response)

    def get_financial_statement(self, *, depot_id: str) -> dict[str, Any]:
        logger.info("Fetching financial statement (depot_id={})", depot_id)
        response = self._jaarrekening.service.opvragenJaarrekening(
            klantreferentie=self._reference(),
            depotId=depot_id,
        )
        return self._serialize(response)

    def get_registration(self, *, kvk_number: str | None = None, rsin: str | None = None) -> dict[str, Any]:
        logger.info("Fetching registration (kvk_number={}, rsin={})", kvk_number, rsin)
        choice = {"kvkNummer": kvk_number} if kvk_number else {"rsin": rsin}
        response = self._catalogus.service.ophalenInschrijving(
            klantreferentie=self._reference(),
            **choice,
        )
        return self._serialize(response)

    def get_ubo_register(self, *, kvk_number: str) -> dict[str, Any]:
        logger.info("Fetching UBO register extract (kvk_number={})", kvk_number)
        response = self._ubo.service.opvragenKvkUittrekselUboRegister(
            klantreferentie=self._reference(),
            kvkNummer=kvk_number,
        )
        return self._serialize(response)

    @staticmethod
    def _reference() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _serialize(response: Any) -> dict[str, Any]:
        return serialize_object(response, dict)  # type: ignore[no-any-return]


def create_kvk_client(config: KVKDataServiceConfig) -> KVKClient:
    return ZeepKVKClient(config)
