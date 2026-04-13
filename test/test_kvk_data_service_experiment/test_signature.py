import datetime
from unittest.mock import patch

from lxml.etree import _Element
from zeep import ns

from kvk_data_service_experiment.signature import TIMESTAMP_LIFETIME, KVKBinarySignature

from .conftest import SignedSoapEnvelopeFactory, qname


class TestKVKBinarySignature:
    def test_signature_adds_timestamp_to_security_header(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        timestamp = result_envelope.find(f".//{qname(ns.WSU, 'Timestamp')}")
        assert timestamp is not None

    def test_signature_timestamp_contains_created_and_expires_elements(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        timestamp = result_envelope.find(f".//{qname(ns.WSU, 'Timestamp')}")
        assert timestamp is not None
        created = timestamp.find(qname(ns.WSU, "Created"))
        assert created is not None and created.text is not None
        expires = timestamp.find(qname(ns.WSU, "Expires"))
        assert expires is not None and expires.text is not None

    def test_signature_timestamp_expires_5_minutes_after_created(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()
        frozen_now = datetime.datetime(2026, 1, 15, 12, 0, 0, tzinfo=datetime.UTC)

        # Act
        with patch("kvk_data_service_experiment.signature.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = frozen_now
            mock_dt.UTC = datetime.UTC
            result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        timestamp = result_envelope.find(f".//{qname(ns.WSU, 'Timestamp')}")
        assert timestamp is not None
        created = timestamp.find(qname(ns.WSU, "Created"))
        assert created is not None
        expires = timestamp.find(qname(ns.WSU, "Expires"))
        assert expires is not None
        assert created.text == "2026-01-15T12:00:00Z"
        assert expires.text == "2026-01-15T12:05:00Z"

    def test_timestamp_lifetime_constant_is_5_minutes(self) -> None:
        assert TIMESTAMP_LIFETIME == datetime.timedelta(minutes=5)

    def test_signature_creates_ds_signature_node(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        signature = result_envelope.find(f".//{qname(ns.DS, 'Signature')}")
        assert signature is not None

    def test_signature_signs_exactly_six_elements(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        signature = result_envelope.find(f".//{qname(ns.DS, 'Signature')}")
        assert signature is not None
        signed_info = signature.find(qname(ns.DS, "SignedInfo"))
        assert signed_info is not None
        references = signed_info.findall(qname(ns.DS, "Reference"))
        assert len(references) == 6

    def test_signature_assigns_wsu_id_to_all_signed_elements(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        tags = [
            qname(ns.SOAP_ENV_11, "Body"),
            qname(ns.WSU, "Timestamp"),
            qname(ns.WSA, "Action"),
            qname(ns.WSA, "MessageID"),
            qname(ns.WSA, "To"),
            qname(ns.WSA, "ReplyTo"),
        ]
        for tag in tags:
            element = result_envelope.find(f".//{tag}")
            assert element is not None, f"Element {tag} not found"
            wsu_id = element.attrib.get(qname(ns.WSU, "Id"))
            assert wsu_id is not None, f"Element {tag} is missing wsu:Id"

    def test_signature_reference_uris_point_to_signed_element_ids(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        signature = result_envelope.find(f".//{qname(ns.DS, 'Signature')}")
        assert signature is not None
        signed_info = signature.find(qname(ns.DS, "SignedInfo"))
        assert signed_info is not None
        references = signed_info.findall(qname(ns.DS, "Reference"))
        ref_uris = {str(ref.attrib["URI"]).lstrip("#") for ref in references}

        wsu_id_attr = qname(ns.WSU, "Id")
        all_ids = {str(el.attrib[wsu_id_attr]) for el in result_envelope.iter() if wsu_id_attr in el.attrib}

        assert ref_uris.issubset(all_ids), f"Dangling references: {ref_uris - all_ids}"

    def test_signature_includes_binary_security_token(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        bst = result_envelope.find(f".//{qname(ns.WSSE, 'BinarySecurityToken')}")
        assert bst is not None

    def test_signature_binary_security_token_has_x509v3_value_type(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        bst = result_envelope.find(f".//{qname(ns.WSSE, 'BinarySecurityToken')}")
        assert bst is not None
        assert bst.attrib["ValueType"] == (
            "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
        )
        assert bst.attrib["EncodingType"] == (
            "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"
        )

    def test_signature_binary_security_token_contains_base64_certificate_data(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        bst = result_envelope.find(f".//{qname(ns.WSSE, 'BinarySecurityToken')}")
        assert bst is not None
        assert bst.text is not None
        assert len(bst.text.strip()) > 0

    def test_signature_security_token_reference_points_to_binary_security_token(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        bst = result_envelope.find(f".//{qname(ns.WSSE, 'BinarySecurityToken')}")
        assert bst is not None
        bst_id = bst.attrib.get(qname(ns.WSU, "Id"))
        assert bst_id is not None

        ref = result_envelope.find(f".//{qname(ns.WSSE, 'SecurityTokenReference')}/{qname(ns.WSSE, 'Reference')}")
        assert ref is not None
        assert ref.attrib["URI"] == f"#{bst_id}"

    def test_signature_verify_returns_envelope_unchanged(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result = kvk_binary_signature.verify(envelope)

        # Assert
        assert result is envelope

    def test_signature_uses_excl_c14n_canonicalization(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        signed_info = result_envelope.find(f".//{qname(ns.DS, 'SignedInfo')}")
        assert signed_info is not None
        c14n_method = signed_info.find(qname(ns.DS, "CanonicalizationMethod"))
        assert c14n_method is not None
        assert c14n_method.attrib["Algorithm"] == "http://www.w3.org/2001/10/xml-exc-c14n#"

    def test_signature_uses_rsa_sha256_signature_method(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        signed_info = result_envelope.find(f".//{qname(ns.DS, 'SignedInfo')}")
        assert signed_info is not None
        sig_method = signed_info.find(qname(ns.DS, "SignatureMethod"))
        assert sig_method is not None
        assert sig_method.attrib["Algorithm"] == "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"

    def test_signature_uses_sha256_digest_for_all_references(
        self, kvk_binary_signature: KVKBinarySignature, signed_soap_envelope: SignedSoapEnvelopeFactory
    ) -> None:
        # Arrange
        envelope: _Element = signed_soap_envelope()

        # Act
        result_envelope, _ = kvk_binary_signature.apply(envelope, {})

        # Assert
        signed_info = result_envelope.find(f".//{qname(ns.DS, 'SignedInfo')}")
        assert signed_info is not None
        references = signed_info.findall(qname(ns.DS, "Reference"))
        for ref in references:
            digest_method = ref.find(qname(ns.DS, "DigestMethod"))
            assert digest_method is not None
            assert digest_method.attrib["Algorithm"] == "http://www.w3.org/2001/04/xmlenc#sha256"
