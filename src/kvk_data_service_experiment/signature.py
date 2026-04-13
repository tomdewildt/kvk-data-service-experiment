import datetime

import xmlsec  # pyright: ignore[reportMissingTypeStubs]
from lxml.etree import Element, QName, SubElement, _Element
from zeep import ns
from zeep.wsse.signature import BinarySignature, _make_sign_key, _sign_node  # pyright: ignore[reportPrivateUsage]
from zeep.wsse.utils import ensure_id, get_security_header

TIMESTAMP_LIFETIME = datetime.timedelta(minutes=5)


class KVKBinarySignature(BinarySignature):
    """
    Extend Zeep's BinarySignature to sign Body, Timestamp, and WS-Addressing headers as KVK requires.
    Response verification is skipped because KVK signs with their server certificate, not the client certificate.
    """

    def apply(self, envelope: _Element, headers: dict) -> tuple[_Element, dict]:  # type: ignore[override]
        security = get_security_header(envelope)
        soap_env = envelope.nsmap.get("soap-env") or ns.SOAP_ENV_11
        digest = self.digest_method or xmlsec.Transform.SHA256  # pyright: ignore[reportAttributeAccessIssue]

        # Add Timestamp to the security header
        timestamp = self._build_timestamp()
        security.append(timestamp)

        # Create the XML signature template and attach it to the security header
        signature = self._build_signature_template(envelope)
        security.insert(0, signature)

        # Set up X509 key info for the signature
        key_info = xmlsec.template.ensure_key_info(signature)
        x509_data = xmlsec.template.add_x509_data(key_info)
        xmlsec.template.x509_data_add_issuer_serial(x509_data)
        xmlsec.template.x509_data_add_certificate(x509_data)

        # Build signing context and sign Body, Timestamp, and WS-Addressing headers
        ctx = xmlsec.SignatureContext()
        ctx.key = _make_sign_key(self.key_data, self.cert_data, self.password)

        _sign_node(ctx, signature, envelope.find(QName(soap_env, "Body").text), digest)
        _sign_node(ctx, signature, timestamp, digest)
        for element in self._find_wsa_headers(envelope, soap_env):
            _sign_node(ctx, signature, element, digest)

        ctx.sign(signature)

        # Replace X509Data with a BinarySecurityToken reference
        bintok = self._build_binary_security_token(x509_data)
        sec_token_ref = self._build_security_token_reference(bintok)

        key_info_node = xmlsec.template.ensure_key_info(signature)
        existing_ref = key_info_node.find(QName(ns.WSSE, "SecurityTokenReference").text)
        if existing_ref is None:
            key_info.append(sec_token_ref)

        parent = x509_data.getparent()
        assert parent is not None
        parent.remove(x509_data)

        security.insert(1, bintok)

        return envelope, headers

    def verify(self, envelope: _Element) -> _Element:  # type: ignore[override]
        return envelope

    def _build_timestamp(self) -> _Element:
        """Build a WSU Timestamp element with Created and Expires."""

        now = datetime.datetime.now(datetime.UTC)
        expires = now + TIMESTAMP_LIFETIME

        timestamp = Element(QName(ns.WSU, "Timestamp"))
        created = SubElement(timestamp, QName(ns.WSU, "Created"))
        created.text = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        expires_el = SubElement(timestamp, QName(ns.WSU, "Expires"))
        expires_el.text = expires.strftime("%Y-%m-%dT%H:%M:%SZ")

        return timestamp

    def _build_signature_template(self, envelope: _Element) -> _Element:
        return xmlsec.template.create(
            envelope,
            xmlsec.Transform.EXCL_C14N,  # pyright: ignore[reportAttributeAccessIssue]
            self.signature_method or xmlsec.Transform.RSA_SHA256,  # pyright: ignore[reportAttributeAccessIssue]
        )

    def _find_wsa_headers(self, envelope: _Element, soap_env: str) -> list[_Element]:
        header = envelope.find(QName(soap_env, "Header").text)
        if header is None:
            return []

        elements: list[_Element] = []
        for tag in ("Action", "MessageID", "To", "ReplyTo"):
            element = header.find(QName(ns.WSA, tag).text)
            if element is not None:
                elements.append(element)
        return elements

    def _build_binary_security_token(self, x509_data: _Element) -> _Element:
        value_type = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
        encoding_type = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"

        bintok = Element(
            QName(ns.WSSE, "BinarySecurityToken"),
            {"ValueType": value_type, "EncodingType": encoding_type},
        )

        x509_cert = x509_data.find(QName(ns.DS, "X509Certificate").text)
        assert x509_cert is not None
        bintok.text = x509_cert.text

        return bintok

    def _build_security_token_reference(self, bintok: _Element) -> _Element:
        sec_token_ref = Element(QName(ns.WSSE, "SecurityTokenReference"))

        value_type = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
        ref = SubElement(sec_token_ref, QName(ns.WSSE, "Reference"), {"ValueType": value_type})
        ref.attrib["URI"] = "#" + ensure_id(bintok)

        return sec_token_ref
