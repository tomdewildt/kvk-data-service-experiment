from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol

import pytest
from lxml import etree
from lxml.etree import QName, _Element
from zeep import ns

from kvk_data_service_experiment.addressing import KVKWSAddressingPlugin
from kvk_data_service_experiment.client import KVKClient
from kvk_data_service_experiment.config import Environment
from kvk_data_service_experiment.service import KVKDataService
from kvk_data_service_experiment.signature import KVKBinarySignature

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class FakeKVKClient(KVKClient):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _record(self, method: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((method, kwargs))
        return {"method": method, **kwargs}

    def get_available_financial_years(self, *, kvk_number: str) -> dict[str, Any]:
        return self._record("get_available_financial_years", kvk_number=kvk_number)

    def get_branch(
        self,
        *,
        branch_number: str | None = None,
        kvk_number: str | None = None,
        rsin: str | None = None,
    ) -> dict[str, Any]:
        return self._record("get_branch", branch_number=branch_number, kvk_number=kvk_number, rsin=rsin)

    def get_extract(self, *, kvk_number: str | None = None, rsin: str | None = None) -> dict[str, Any]:
        return self._record("get_extract", kvk_number=kvk_number, rsin=rsin)

    def get_financial_statement(self, *, depot_id: str) -> dict[str, Any]:
        return self._record("get_financial_statement", depot_id=depot_id)

    def get_registration(self, *, kvk_number: str | None = None, rsin: str | None = None) -> dict[str, Any]:
        return self._record("get_registration", kvk_number=kvk_number, rsin=rsin)

    def get_ubo_register(self, *, kvk_number: str) -> dict[str, Any]:
        return self._record("get_ubo_register", kvk_number=kvk_number)


class SoapEnvelopeFactory(Protocol):
    def __call__(
        self,
        *,
        action: str = ...,
        message_id: str = ...,
        to: str = ...,
    ) -> _Element: ...


class SignedSoapEnvelopeFactory(Protocol):
    def __call__(self) -> _Element: ...


class SoapOperationFactory(Protocol):
    def __call__(self, *, wsa_action: str | None = ..., soapaction: str = ...) -> SimpleNamespace: ...


def qname(namespace: str, localname: str) -> str:
    return str(QName(namespace, localname))


@pytest.fixture()
def soap_envelope() -> SoapEnvelopeFactory:
    def _build(
        *,
        action: str = "http://es.kvk.nl/ophalenInschrijving",
        message_id: str = "urn:uuid:abc-123",
        to: str = "https://dataservice.preprod.kvk.nl",
    ) -> _Element:
        soap_env = ns.SOAP_ENV_11
        wsa = ns.WSA

        envelope = etree.Element(QName(soap_env, "Envelope"), nsmap={"soap-env": soap_env, "wsa": wsa})
        header = etree.SubElement(envelope, QName(soap_env, "Header"))
        etree.SubElement(envelope, QName(soap_env, "Body"))

        action_el = etree.SubElement(header, QName(wsa, "Action"))
        action_el.text = action
        msg_id_el = etree.SubElement(header, QName(wsa, "MessageID"))
        msg_id_el.text = message_id
        to_el = etree.SubElement(header, QName(wsa, "To"))
        to_el.text = to

        return envelope

    return _build  # type: ignore[return-value]


@pytest.fixture()
def fake_client() -> FakeKVKClient:
    return FakeKVKClient()


@pytest.fixture()
def kvk_binary_signature() -> KVKBinarySignature:
    return KVKBinarySignature(str(FIXTURES_DIR / "test.key"), str(FIXTURES_DIR / "test.pem"))


@pytest.fixture()
def preprod_addressing_plugin() -> KVKWSAddressingPlugin:
    return KVKWSAddressingPlugin(Environment.PREPROD)


@pytest.fixture()
def prod_addressing_plugin() -> KVKWSAddressingPlugin:
    return KVKWSAddressingPlugin(Environment.PROD)


@pytest.fixture()
def service(fake_client: FakeKVKClient) -> KVKDataService:
    return KVKDataService(fake_client)


@pytest.fixture()
def signed_soap_envelope(soap_envelope: SoapEnvelopeFactory) -> SignedSoapEnvelopeFactory:
    def _build() -> _Element:
        envelope = soap_envelope(message_id="uuid:test-message-id", to="http://es.kvk.nl/KvK-DataservicePP/2015/02")

        wsa = ns.WSA
        header = envelope.find(qname(ns.SOAP_ENV_11, "Header"))
        assert header is not None
        body = envelope.find(qname(ns.SOAP_ENV_11, "Body"))
        assert body is not None
        etree.SubElement(body, "TestRequest")

        reply_to = etree.SubElement(header, QName(wsa, "ReplyTo"))
        address = etree.SubElement(reply_to, QName(wsa, "Address"))
        address.text = "http://www.w3.org/2005/08/addressing/anonymous"

        return envelope

    return _build  # type: ignore[return-value]


@pytest.fixture()
def soap_operation() -> SoapOperationFactory:
    def _build(*, wsa_action: str | None = None, soapaction: str = "") -> SimpleNamespace:
        return SimpleNamespace(abstract=SimpleNamespace(wsa_action=wsa_action), soapaction=soapaction)

    return _build  # type: ignore[return-value]
