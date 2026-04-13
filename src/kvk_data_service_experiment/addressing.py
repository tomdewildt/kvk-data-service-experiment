from lxml import etree
from lxml.builder import ElementMaker  # type: ignore[import-untyped]
from lxml.etree import QName
from zeep import ns
from zeep.plugins import Plugin
from zeep.wsdl.utils import get_or_create_header

from kvk_data_service_experiment.config import Environment

WSA = ElementMaker(namespace=ns.WSA, nsmap={"wsa": ns.WSA})
WSA_ANONYMOUS = "http://www.w3.org/2005/08/addressing/anonymous"

_SOAP_ACTION_TO_API_VERSION_MAP: dict[str, str] = {
    "http://es.kvk.nl/ophalenInschrijving": "2015/02",
    "http://es.kvk.nl/ophalenVestiging": "2015/02",
    "http://es.kvk.nl/opvragenBeschikbareBoekjaren": "2018/01",
    "http://es.kvk.nl/opvragenJaarrekening": "2018/01",
    "http://es.kvk.nl/opvragenKvkUittrekselUboRegister": "2018/01",
    "http://es.kvk.nl/opvragenKvkHandelsregisterUittreksel": "2020/01",
}

_WSA_TO_SERVICE_URI_TO_ENVIRONMENT_API_VERSION_MAP: dict[Environment, dict[str, str]] = {
    Environment.PREPROD: {
        "2015/02": "http://es.kvk.nl/KvK-DataservicePP/2015/02",
        "2018/01": "http://es.kvk.nl/KVK-DataservicePP/2018/01",
        "2020/01": "http://es.kvk.nl/KVK-DataservicePP/2020/01",
    },
    Environment.PROD: {
        "2015/02": "http://es.kvk.nl/KvK-Dataservice/2015/02",
        "2018/01": "http://es.kvk.nl/KVK-Dataservice/2018/01",
        "2020/01": "http://es.kvk.nl/KVK-Dataservice/2020/01",
    },
}


class KVKWSAddressingPlugin(Plugin):
    """
    Fix WS-Addressing headers that Zeep generates incorrectly for KVK. Zeep populates Action, MessageID, and To from the
    WSDL, but KVK requires non-standard values that Zeep does not produce by default.
    """

    def __init__(self, environment: Environment):
        self._environment = environment

    def egress(self, envelope, http_headers, operation, binding_options):  # type: ignore[override]
        header = get_or_create_header(envelope)
        action = operation.abstract.wsa_action or operation.soapaction

        # Replace wsa:To with the logical service URI for this environment and API version
        to_uri = self._resolve_to(action)
        if to_uri:
            to_element = header.find(QName(ns.WSA, "To").text)
            if to_element is not None:
                to_element.text = to_uri

        # Strip the "urn:" prefix from the MessageID, KVK expects "uuid:" format
        message_id = header.find(QName(ns.WSA, "MessageID").text)
        if message_id is not None and message_id.text:
            message_id.text = self._normalize_message_id(message_id.text)

        # Add the required ReplyTo header pointing to the anonymous role
        header.append(self._build_reply_to())

        # Clean up redundant namespace declarations introduced by the new elements
        if etree.LXML_VERSION[:2] >= (3, 5):
            etree.cleanup_namespaces(header, keep_ns_prefixes=header.nsmap, top_nsmap={"wsa": ns.WSA})  # type: ignore[arg-type]
        else:
            etree.cleanup_namespaces(header)

        return envelope, http_headers

    def _resolve_to(self, action: str) -> str | None:
        """Return the logical service URI for the given soap action, or none."""
        version = _SOAP_ACTION_TO_API_VERSION_MAP.get(action)
        if not version:
            return None
        return _WSA_TO_SERVICE_URI_TO_ENVIRONMENT_API_VERSION_MAP[self._environment][version]

    def _normalize_message_id(self, message_id: str) -> str:
        """KVK expects "uuid:<value>" not "urn:uuid:<value>"."""
        if message_id.startswith("urn:uuid:"):
            return message_id.replace("urn:uuid:", "uuid:", 1)
        return message_id

    def _build_reply_to(self) -> etree._Element:
        """Build the reply to element that KVK requires."""
        return WSA.ReplyTo(WSA.Address(WSA_ANONYMOUS))
