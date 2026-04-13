# KVK Data Service Integration Guide

This document describes how this project connects to the KVK Data Service SOAP API. It covers the full request flow, signing, WS-Addressing, and the gotchas that are not obvious from the KVK documentation alone.

## Overview

The KVK Data Service is a SOAP 1.1 API secured with mutual TLS (mTLS) and WS-Security XML signatures. It requires WS-Addressing headers with specific logical service URIs that differ per environment and API version.

## Environments & Endpoints

| Environment | HTTP Endpoint (mTLS)                 | Purpose    |
| ----------- | ------------------------------------ | ---------- |
| PREPROD     | `https://dataservice.preprod.kvk.nl` | Testing    |
| PROD        | `https://dataservice.kvk.nl`         | Production |

The HTTP endpoint is where the SOAP request is POSTed over mTLS. This is **not** the same as the `wsa:To` header value (see WS-Addressing section below).

## WSDLs

The KVK Data Service is split across four separate WSDLs, each covering a different set of operations. The client loads all four on startup and routes each method to the correct one.

| WSDL                                                                                                                                                             | Operations                                             | API Version |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ----------- |
| [`dataservice/catalogus/2015/02`](http://schemas.kvk.nl/contracts/kvk/dataservice/catalogus/2015/02/KVK-KvKDataservice.wsdl)                                     | `ophalenInschrijving`, `ophalenVestiging`              | 2015/02     |
| [`opvragenjaarrekening/2018/01`](http://schemas.kvk.nl/contracts/kvk/opvragenjaarrekening/2018/01/kvk-Opvragenjaarrekening.wsdl)                                 | `opvragenBeschikbareBoekjaren`, `opvragenJaarrekening` | 2018/01     |
| [`ubo/2018/01`](http://schemas.kvk.nl/contracts/kvk/ubo/2018/01/kvk-opvragenKvkUittrekselUboRegister.wsdl)                                                       | `opvragenKvkUittrekselUboRegister`                     | 2018/01     |
| [`kvkhandelsregisteruittreksel/2020/01`](http://schemas.kvk.nl/contracts/kvk/kvkhandelsregisteruittreksel/2020/01/kvk-opvragenKvkHandelsregisterUittreksel.wsdl) | `opvragenkvkhandelsregisteruitreksel`                  | 2020/01     |

The WSDL naming is inconsistent. the file names, operation names, and URL paths don't follow a single convention. These URLs were discovered by probing `schemas.kvk.nl`; they are not documented anywhere.

## WSDL & Schema Caching

On first request, zeep fetches each WSDL and all imported XSD schemas from `http://schemas.kvk.nl/`. These are cached as XML files on disk in `.cache/` using SHA256 hashes of the URL as filenames. Subsequent requests load from cache.

## Request Flow

When a CLI command like `registration --kvk-number 90000021` is executed:

### 1. Zeep builds the SOAP envelope

Zeep generates the SOAP Body from the WSDL-defined request type:

```xml
<soap-env:Body>
  <ns0:ophalenInschrijvingRequest>
    <ns0:klantreferentie>auto-generated-uuid</ns0:klantreferentie>
    <ns0:kvkNummer>90000021</ns0:kvkNummer>
  </ns0:ophalenInschrijvingRequest>
</soap-env:Body>
```

### 2. Zeep auto-adds WS-Addressing headers

Because the WSDL has a `wsam:Addressing` policy, zeep automatically adds three WS-Addressing headers before plugins run:

- `wsa:Action`: the SOAP action URI (e.g. `http://es.kvk.nl/ophalenInschrijving`)
- `wsa:MessageID`: a generated UUID (format: `urn:uuid:<value>`)
- `wsa:To`: defaults to the HTTP endpoint URL

### 3. KVKWSAddressingPlugin modifies headers

Our plugin runs after zeep's auto-added headers and makes three corrections:

1. **Replaces `wsa:To`** with the correct logical service URI. KVK does NOT expect the HTTP endpoint here. The value depends on the environment and API version:

   | API Version | Preprod `wsa:To`                             | Prod `wsa:To`                              |
   | ----------- | -------------------------------------------- | ------------------------------------------ |
   | 2015/02     | `http://es.kvk.nl/KvK-DataservicePP/2015/02` | `http://es.kvk.nl/KvK-Dataservice/2015/02` |
   | 2018/01     | `http://es.kvk.nl/KVK-DataservicePP/2018/01` | `http://es.kvk.nl/KVK-Dataservice/2018/01` |
   | 2020/01     | `http://es.kvk.nl/KVK-DataservicePP/2020/01` | `http://es.kvk.nl/KVK-Dataservice/2020/01` |

   The mapping from operation to API version is determined by the `soapAction`.

2. **Fixes `wsa:MessageID` format** from `urn:uuid:<value>` to `uuid:<value>`. KVK rejects the `urn:uuid:` prefix that zeep generates by default.

3. **Adds `wsa:ReplyTo`** with the anonymous address. Zeep does not add this but KVK requires it:

   ```xml
   <wsa:ReplyTo>
     <wsa:Address>http://www.w3.org/2005/08/addressing/anonymous</wsa:Address>
   </wsa:ReplyTo>
   ```

### 4. KVKBinarySignature signs the envelope

The WSSE plugin runs after all headers are in place. It performs these steps:

#### a) Add Timestamp

A `wsu:Timestamp` element is added to the `wsse:Security` header with a 5-minute lifetime:

```xml
<wsu:Timestamp wsu:Id="...">
  <wsu:Created>2026-04-07T16:00:00Z</wsu:Created>
  <wsu:Expires>2026-04-07T16:05:00Z</wsu:Expires>
</wsu:Timestamp>
```

#### b) Create XML Signature

A `ds:Signature` node is created using EXCL-C14N canonicalization and RSA-SHA256.

#### c) Sign six elements

Each signed element gets a `wsu:Id` attribute and a corresponding `ds:Reference` in the signature:

| #   | Element         | Description                |
| --- | --------------- | -------------------------- |
| 1   | `soap:Body`     | The SOAP request payload   |
| 2   | `wsu:Timestamp` | Request validity window    |
| 3   | `wsa:Action`    | The operation being called |
| 4   | `wsa:MessageID` | Unique request identifier  |
| 5   | `wsa:To`        | Logical service URI        |
| 6   | `wsa:ReplyTo`   | Reply address              |

**Algorithms:**

- Signature: `RSA-SHA256` (`http://www.w3.org/2001/04/xmldsig-more#rsa-sha256`)
- Digest: `SHA-256` (`http://www.w3.org/2001/04/xmlenc#sha256`)
- Canonicalization: `EXCL-C14N` (`http://www.w3.org/2001/10/xml-exc-c14n#`)

#### d) Add BinarySecurityToken

The client's X.509 certificate is embedded as a `wsse:BinarySecurityToken` in the Security header. The signature's `KeyInfo` references this token.

#### e) Skip response verification

KVK signs responses with their server certificate, not the client certificate. Zeep's default would try to verify with the client cert and fail. Our implementation returns the envelope unchanged. There is no way to verify response signatures without KVK's server signing certificate, which they do not provide. TLS already ensures the response came from KVK's server.

### 5. mTLS transport

The request is sent over HTTPS with mutual TLS:

- **Client cert + key**: presented during TLS handshake
- **CA bundle**: KVK's certificate chain for verifying the server

### 6. Response handling

Zeep deserializes the XML response into Python objects. The helper converts these to plain dicts. Non-JSON-serializable types (e.g. `deque`) are handled by `default=str` in the JSON encoder.

## Available Operations

| CLI Command           | SOAP Operation                        | WSDL         | API Version |
| --------------------- | ------------------------------------- | ------------ | ----------- |
| `registration`        | `ophalenInschrijving`                 | catalogus    | 2015/02     |
| `branch`              | `ophalenVestiging`                    | catalogus    | 2015/02     |
| `financial-years`     | `opvragenBeschikbareBoekjaren`        | jaarrekening | 2018/01     |
| `financial-statement` | `opvragenJaarrekening`                | jaarrekening | 2018/01     |
| `ubo`                 | `opvragenKvkUittrekselUboRegister`    | ubo          | 2018/01     |
| `extract`             | `opvragenkvkhandelsregisteruitreksel` | uittreksel   | 2020/01     |

### xs:choice parameters

Several operations use `xs:choice` in their request types, meaning exactly one of the alternatives must be provided (not multiple):

- **`ophalenInschrijving`**: `kvkNummer` OR `rsin`
- **`ophalenVestiging`**: `vestigingsnummer` OR `kvkNummer` OR `rsin`
- **`opvragenkvkhandelsregisteruitreksel`**: `kvkNummer` OR `kvkNummer` + `vestigingsNummer` OR `rsin`

Passing multiple choice fields causes zeep to reject the request with an unexpected keyword error.

### Financial statement workflow

Fetching a financial statement is a two-step process:

1. Call `opvragenBeschikbareBoekjaren` with a `kvkNummer` to get available depot IDs
2. Call `opvragenJaarrekening` with a `depotId` to fetch the actual statement

The `depotId` is required; `kvkNummer` and `boekjaar` are optional on the second call.

### Operations without `klantreferentie`

The `klantreferentie` parameter (correlation ID) is required for the catalogus and jaarrekening WSDLs but is **not** part of the extract (uittreksel) WSDL request type.

## Common Pitfalls

1. **`wsa:To` is NOT the HTTP endpoint.** It's a logical service URI that varies by environment and API version. Sending the HTTP endpoint URL as `wsa:To` causes `WSA01: WS-Addressing niet aanwezig of incorrect`.

2. **`wsa:MessageID` must use `uuid:` prefix**, not `urn:uuid:`. Zeep's default addressing plugin generates `urn:uuid:` which KVK rejects.

3. **Zeep auto-adds WS-Addressing headers** when the WSDL has `wsam:Addressing` policy. Adding your own plugin that also adds Action/MessageID/To will cause duplicates.

4. **Response signature verification fails** because KVK signs with their server cert, not your client cert. Override `verify()` to skip it.

5. **SHA-1 vs SHA-256**: KVK accepts both RSA-SHA1 and RSA-SHA256 for request signing, but their responses use RSA-SHA256 exclusively.

6. **The `klantreferentie` parameter** is required for catalogus and jaarrekening operations. It's a correlation ID (max 50 chars) that you generate. Not to be confused with `wsa:MessageID`. Not all WSDLs include it in their request type.

7. **Four separate WSDLs** are needed. The operations are not in a single WSDL. The URLs don't follow a consistent naming pattern and were not documented by KVK.

8. **`wsa:Action` and `wsa:To` must be a valid combination.** An invalid combination returns `AUTHPSTBS09: De wsa:To en wsa:Action combinatie is niet geldig`.

## Certificate Setup

KVK provides CA bundle certificates per environment. Generate them from KVK's cert files:

```bash
# Preprod
cat "DigiCert G2 TLS EU RSA4096 SHA384 2022 CA1.crt" "DigiCert Global Root G2.crt" > certs/kvk-preprod-ca-bundle.pem

# Production
cat "DigiCert G2 TLS EU RSA4096 SHA384 2022 CA1.crt" "DigiCert Global Root G2.crt" > certs/kvk-prod-ca-bundle.pem
```

Your client certificate and key must be:

- RSA 2048-bit minimum with SHA-256
- From an eIDAS-recognized provider
- Organization Validation (OV) for production; Domain Validation (DV) is accepted for preprod

## Sources

All KVK-specific details (endpoints, `wsa:To` URIs, `wsa:Action` values, MessageID format, signing requirements, certificate requirements) were found on the KVK Data Service product page. This is the primary source for connection requirements:

- [KVK Dataservice Aansluiten Bedrijf](https://www.kvk.nl/producten-bestellen/kvk-dataservice-aansluiten-bedrijf/)
  
  - Main product page with connection requirements, SOAP header examples, endpoint URLs, `wsa:To` values per environment/version, MessageID format (`uuid:<value>`), supported signature algorithms, and certificate requirements. Also provides SoapUI example projects and certificate downloads.

The WSDLs and XSD schemas define the SOAP operations and request/response types:

- [Catalogus WSDL (2015/02)](http://schemas.kvk.nl/contracts/kvk/dataservice/catalogus/2015/02/KVK-KvKDataservice.wsdl)
  
  - Registration and branch operations.

- [Jaarrekening WSDL (2018/01)](http://schemas.kvk.nl/contracts/kvk/opvragenjaarrekening/2018/01/kvk-Opvragenjaarrekening.wsdl)
  
  - Financial years and financial statement operations.

- [UBO WSDL (2018/01)](http://schemas.kvk.nl/contracts/kvk/ubo/2018/01/kvk-opvragenKvkUittrekselUboRegister.wsdl)

  - UBO register extract operation.

- [Uittreksel WSDL (2020/01)](http://schemas.kvk.nl/contracts/kvk/kvkhandelsregisteruittreksel/2020/01/kvk-opvragenKvkHandelsregisterUittreksel.wsdl)

  - Business register extract (DGU) operation.

- [XSD Schemas](http://schemas.kvk.nl/schemas/kvk/dataservice/catalogus/2015/02/)

  - Type definitions for request/response messages.

Zeep-specific behavior (auto-added WS-Addressing, `BinarySignature` signing scope, `serialize_object` helper) was determined by reading the zeep source code:

- [Zeep Docs](https://docs.python-zeep.org/)

- [Zeep Source - soap.py](https://github.com/mvantellingen/python-zeep/blob/master/src/zeep/wsdl/bindings/soap.py)

- [Zeep Source - signature.py](https://github.com/mvantellingen/python-zeep/blob/master/src/zeep/wsse/signature.py)

  - `BinarySignature` only signs Body + Timestamp; WS-Addressing headers are not signed by default.

- [Zeep Source - wsa.py](https://github.com/mvantellingen/python-zeep/blob/master/src/zeep/wsa.py)

  - `WsAddressingPlugin` uses `urn:uuid:` format for MessageID.
