from types import SimpleNamespace

import pytest
from lxml.etree import QName, _Element
from zeep import ns

from kvk_data_service_experiment.addressing import (
    _SOAP_ACTION_TO_API_VERSION_MAP,
    _WSA_TO_SERVICE_URI_TO_ENVIRONMENT_API_VERSION_MAP,
    WSA_ANONYMOUS,
    KVKWSAddressingPlugin,
)
from kvk_data_service_experiment.config import Environment

from .conftest import SoapEnvelopeFactory, SoapOperationFactory, qname


class TestKVKWsAddressingPlugin:
    @pytest.mark.parametrize(
        ("environment", "action", "expected_wsa_to"),
        [
            (
                "preprod",
                "http://es.kvk.nl/ophalenInschrijving",
                "http://es.kvk.nl/KvK-DataservicePP/2015/02",
            ),
            (
                "prod",
                "http://es.kvk.nl/ophalenInschrijving",
                "http://es.kvk.nl/KvK-Dataservice/2015/02",
            ),
            (
                "preprod",
                "http://es.kvk.nl/ophalenVestiging",
                "http://es.kvk.nl/KvK-DataservicePP/2015/02",
            ),
            (
                "prod",
                "http://es.kvk.nl/ophalenVestiging",
                "http://es.kvk.nl/KvK-Dataservice/2015/02",
            ),
            (
                "preprod",
                "http://es.kvk.nl/opvragenBeschikbareBoekjaren",
                "http://es.kvk.nl/KVK-DataservicePP/2018/01",
            ),
            (
                "prod",
                "http://es.kvk.nl/opvragenBeschikbareBoekjaren",
                "http://es.kvk.nl/KVK-Dataservice/2018/01",
            ),
            (
                "preprod",
                "http://es.kvk.nl/opvragenJaarrekening",
                "http://es.kvk.nl/KVK-DataservicePP/2018/01",
            ),
            (
                "prod",
                "http://es.kvk.nl/opvragenJaarrekening",
                "http://es.kvk.nl/KVK-Dataservice/2018/01",
            ),
            (
                "preprod",
                "http://es.kvk.nl/opvragenKvkUittrekselUboRegister",
                "http://es.kvk.nl/KVK-DataservicePP/2018/01",
            ),
            (
                "prod",
                "http://es.kvk.nl/opvragenKvkUittrekselUboRegister",
                "http://es.kvk.nl/KVK-Dataservice/2018/01",
            ),
            (
                "preprod",
                "http://es.kvk.nl/opvragenKvkHandelsregisterUittreksel",
                "http://es.kvk.nl/KVK-DataservicePP/2020/01",
            ),
            (
                "prod",
                "http://es.kvk.nl/opvragenKvkHandelsregisterUittreksel",
                "http://es.kvk.nl/KVK-Dataservice/2020/01",
            ),
        ],
        ids=[
            "preprod-ophalenInschrijving-2015/02",
            "prod-ophalenInschrijving-2015/02",
            "preprod-ophalenVestiging-2015/02",
            "prod-ophalenVestiging-2015/02",
            "preprod-opvragenBeschikbareBoekjaren-2018/01",
            "prod-opvragenBeschikbareBoekjaren-2018/01",
            "preprod-opvragenJaarrekening-2018/01",
            "prod-opvragenJaarrekening-2018/01",
            "preprod-opvragenKvkUittrekselUboRegister-2018/01",
            "prod-opvragenKvkUittrekselUboRegister-2018/01",
            "preprod-opvragenKvkHandelsregisterUittreksel-2020/01",
            "prod-opvragenKvkHandelsregisterUittreksel-2020/01",
        ],
    )
    def test_plugin_replaces_wsa_to_with_logical_service_uri(
        self,
        environment: str,
        action: str,
        expected_wsa_to: str,
        soap_envelope: SoapEnvelopeFactory,
        soap_operation: SoapOperationFactory,
        request: pytest.FixtureRequest,
    ) -> None:
        # Arrange
        plugin: KVKWSAddressingPlugin = request.getfixturevalue(f"{environment}_addressing_plugin")
        envelope: _Element = soap_envelope(action=action)
        operation: SimpleNamespace = soap_operation(wsa_action=action)

        # Act
        result_envelope, _ = plugin.egress(envelope, {}, operation, {})

        # Assert
        to = result_envelope.find(f".//{qname(ns.WSA, 'To')}")
        assert to is not None
        assert to.text == expected_wsa_to

    def test_plugin_falls_back_to_soapaction_when_wsa_action_is_none(
        self,
        preprod_addressing_plugin: KVKWSAddressingPlugin,
        soap_envelope: SoapEnvelopeFactory,
        soap_operation: SoapOperationFactory,
    ) -> None:
        # Arrange
        envelope: _Element = soap_envelope()
        operation: SimpleNamespace = soap_operation(wsa_action=None, soapaction="http://es.kvk.nl/ophalenInschrijving")

        # Act
        result_envelope, _ = preprod_addressing_plugin.egress(envelope, {}, operation, {})

        # Assert
        to = result_envelope.find(f".//{qname(ns.WSA, 'To')}")
        assert to is not None
        assert to.text == "http://es.kvk.nl/KvK-DataservicePP/2015/02"

    def test_plugin_leaves_wsa_to_unchanged_for_unknown_action(
        self,
        preprod_addressing_plugin: KVKWSAddressingPlugin,
        soap_envelope: SoapEnvelopeFactory,
        soap_operation: SoapOperationFactory,
    ) -> None:
        # Arrange
        envelope: _Element = soap_envelope()
        operation: SimpleNamespace = soap_operation(wsa_action="http://es.kvk.nl/unknownAction")

        # Act
        result_envelope, _ = preprod_addressing_plugin.egress(envelope, {}, operation, {})

        # Assert
        to = result_envelope.find(f".//{qname(ns.WSA, 'To')}")
        assert to is not None
        assert to.text == "https://dataservice.preprod.kvk.nl"

    def test_plugin_replaces_urn_uuid_prefix_with_uuid_prefix(
        self,
        preprod_addressing_plugin: KVKWSAddressingPlugin,
        soap_envelope: SoapEnvelopeFactory,
        soap_operation: SoapOperationFactory,
    ) -> None:
        # Arrange
        envelope: _Element = soap_envelope(message_id="urn:uuid:550e8400-e29b-41d4-a716-446655440000")
        operation: SimpleNamespace = soap_operation(wsa_action="http://es.kvk.nl/ophalenInschrijving")

        # Act
        result_envelope, _ = preprod_addressing_plugin.egress(envelope, {}, operation, {})

        # Assert
        msg_id = result_envelope.find(f".//{qname(ns.WSA, 'MessageID')}")
        assert msg_id is not None
        assert msg_id.text == "uuid:550e8400-e29b-41d4-a716-446655440000"

    def test_plugin_leaves_uuid_prefix_unchanged_when_already_correct(
        self,
        preprod_addressing_plugin: KVKWSAddressingPlugin,
        soap_envelope: SoapEnvelopeFactory,
        soap_operation: SoapOperationFactory,
    ) -> None:
        # Arrange
        envelope: _Element = soap_envelope(message_id="uuid:already-correct")
        operation: SimpleNamespace = soap_operation(wsa_action="http://es.kvk.nl/ophalenInschrijving")

        # Act
        result_envelope, _ = preprod_addressing_plugin.egress(envelope, {}, operation, {})

        # Assert
        msg_id = result_envelope.find(f".//{qname(ns.WSA, 'MessageID')}")
        assert msg_id is not None
        assert msg_id.text == "uuid:already-correct"

    def test_plugin_replaces_only_the_first_urn_uuid_prefix(
        self,
        preprod_addressing_plugin: KVKWSAddressingPlugin,
        soap_envelope: SoapEnvelopeFactory,
        soap_operation: SoapOperationFactory,
    ) -> None:
        # Arrange
        envelope: _Element = soap_envelope(message_id="urn:uuid:urn:uuid:nested")
        operation: SimpleNamespace = soap_operation(wsa_action="http://es.kvk.nl/ophalenInschrijving")

        # Act
        result_envelope, _ = preprod_addressing_plugin.egress(envelope, {}, operation, {})

        # Assert
        msg_id = result_envelope.find(f".//{qname(ns.WSA, 'MessageID')}")
        assert msg_id is not None
        assert msg_id.text == "uuid:urn:uuid:nested"

    def test_plugin_adds_reply_to_header_with_anonymous_address(
        self,
        preprod_addressing_plugin: KVKWSAddressingPlugin,
        soap_envelope: SoapEnvelopeFactory,
        soap_operation: SoapOperationFactory,
    ) -> None:
        # Arrange
        envelope: _Element = soap_envelope()
        operation: SimpleNamespace = soap_operation(wsa_action="http://es.kvk.nl/ophalenInschrijving")

        # Act
        result_envelope, _ = preprod_addressing_plugin.egress(envelope, {}, operation, {})

        # Assert
        reply_to = result_envelope.find(f".//{qname(ns.WSA, 'ReplyTo')}")
        assert reply_to is not None
        address = reply_to.find(qname(ns.WSA, "Address"))
        assert address is not None
        assert address.text == WSA_ANONYMOUS

    def test_plugin_adds_reply_to_in_wsa_namespace(
        self,
        preprod_addressing_plugin: KVKWSAddressingPlugin,
        soap_envelope: SoapEnvelopeFactory,
        soap_operation: SoapOperationFactory,
    ) -> None:
        # Arrange
        envelope: _Element = soap_envelope()
        operation: SimpleNamespace = soap_operation(wsa_action="http://es.kvk.nl/ophalenInschrijving")

        # Act
        result_envelope, _ = preprod_addressing_plugin.egress(envelope, {}, operation, {})

        # Assert
        reply_to = result_envelope.find(f".//{qname(ns.WSA, 'ReplyTo')}")
        assert reply_to is not None
        assert reply_to.tag == QName(ns.WSA, "ReplyTo")

    def test_plugin_returns_http_headers_unchanged(
        self,
        preprod_addressing_plugin: KVKWSAddressingPlugin,
        soap_envelope: SoapEnvelopeFactory,
        soap_operation: SoapOperationFactory,
    ) -> None:
        # Arrange
        envelope: _Element = soap_envelope()
        operation: SimpleNamespace = soap_operation(wsa_action="http://es.kvk.nl/ophalenInschrijving")
        original_headers: dict[str, str] = {"Content-Type": "text/xml", "SOAPAction": "test"}

        # Act
        _, returned_headers = preprod_addressing_plugin.egress(envelope, original_headers, operation, {})

        # Assert
        assert returned_headers is original_headers


class TestActionToVersionMapping:
    def test_all_six_operations_map_to_expected_api_versions(self) -> None:
        # Arrange
        expected: dict[str, str] = {
            "http://es.kvk.nl/ophalenInschrijving": "2015/02",
            "http://es.kvk.nl/ophalenVestiging": "2015/02",
            "http://es.kvk.nl/opvragenBeschikbareBoekjaren": "2018/01",
            "http://es.kvk.nl/opvragenJaarrekening": "2018/01",
            "http://es.kvk.nl/opvragenKvkUittrekselUboRegister": "2018/01",
            "http://es.kvk.nl/opvragenKvkHandelsregisterUittreksel": "2020/01",
        }

        # Act & Assert
        assert _SOAP_ACTION_TO_API_VERSION_MAP == expected

    def test_every_api_version_has_wsa_to_uri_for_both_environments(self) -> None:
        # Arrange
        all_versions: set[str] = set(_SOAP_ACTION_TO_API_VERSION_MAP.values())

        # Act & Assert
        for env in Environment:
            assert env in _WSA_TO_SERVICE_URI_TO_ENVIRONMENT_API_VERSION_MAP, f"Missing environment {env} in _WSA_TO"
            for version in all_versions:
                assert version in _WSA_TO_SERVICE_URI_TO_ENVIRONMENT_API_VERSION_MAP[env], (
                    f"Missing version {version} for {env} in _WSA_TO"
                )

    def test_preprod_wsa_to_uris_contain_pp_suffix(self) -> None:
        # Act & Assert
        for version, uri in _WSA_TO_SERVICE_URI_TO_ENVIRONMENT_API_VERSION_MAP[Environment.PREPROD].items():
            assert "PP/" in uri, f"Preprod URI for {version} should contain 'PP/': {uri}"

    def test_prod_wsa_to_uris_do_not_contain_pp_suffix(self) -> None:
        # Act & Assert
        for version, uri in _WSA_TO_SERVICE_URI_TO_ENVIRONMENT_API_VERSION_MAP[Environment.PROD].items():
            assert "PP/" not in uri, f"Prod URI for {version} should not contain 'PP/': {uri}"
