# KVK Data Service Experiment
[![License](https://img.shields.io/github/license/tomdewildt/kvk-data-service-experiment)](https://github.com/tomdewildt/kvk-data-service-experiment/blob/master/LICENSE)

Experiment with the [KVK Data Service](https://www.kvk.nl/producten-bestellen/kvk-dataservice-aansluiten-bedrijf/) SOAP API.

# How To Run

Prerequisites:
* mise version ```2025.1.0``` or later
* uv version ```0.6.0``` or later
* python version ```3.12.0``` or later
* KVK Data Service mTLS certificates

### Certificates

Generate the CA bundles from the [KVK-provided certificate files](https://www.kvk.nl/producten-bestellen/kvk-dataservice-aansluiten-bedrijf/):

```bash
cd certificaten_dataservice_2025_12_preprod_omgeving
cat "DigiCert G2 TLS EU RSA4096 SHA384 2022 CA1.crt" "DigiCert Global Root G2.crt" > ../certs/kvk-preprod-ca-bundle.pem

cd ../certificaten_dataservice_2025_12_prd_omgeving
cat "DigiCert G2 TLS EU RSA4096 SHA384 2022 CA1.crt" "DigiCert Global Root G2.crt" > ../certs/kvk-prod-ca-bundle.pem
```

### Development

1. Run ```mise run init``` to initialize the environment.
2. Copy ```.env.example``` to ```.env``` and configure the certificate paths.
3. Run ```mise run start -- inschrijving <kvk-nummer>``` to query the Inschrijving service.
4. Run ```mise run start -- vestiging <vestigingsnummer>``` to query the Vestiging service.
5. Run ```mise run start -- jaarrekening <kvk-nummer>``` to query the Jaarrekening service.
6. Run ```mise run start -- ubo <kvk-nummer>``` to query the UBO Register service.
7. Run ```mise run start -- uittreksel <kvk-nummer>``` to query the Handelsregister Uittreksel service.

# References

[KVK Data Service Docs](https://www.kvk.nl/producten-bestellen/kvk-dataservice-aansluiten-bedrijf/)

[KVK Schemas](http://schemas.kvk.nl/)

[Zeep Docs](https://docs.python-zeep.org/)

[Pydantic Docs](https://docs.pydantic.dev/)

[Pydantic Settings Docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

[Loguru Docs](https://loguru.readthedocs.io/)
