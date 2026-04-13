# KVK Data Service Experiment

[![License](https://img.shields.io/github/license/tomdewildt/kvk-data-service-experiment)](https://github.com/tomdewildt/kvk-data-service-experiment/blob/master/LICENSE)

Experiment with the [KVK Data Service](https://www.kvk.nl/producten-bestellen/kvk-dataservice-aansluiten-bedrijf/) SOAP API. See [KVK.md](KVK.md) for detailed notes on how to integrate with it.

# How To Run

Prerequisites:

- mise version `2025.1.0` or later
- uv version `0.6.0` or later
- python version `3.12.0` or later
- KVK Data Service mTLS certificates

### Certificates

Generate the CA bundles from the [KVK-provided certificate files](https://www.kvk.nl/producten-bestellen/kvk-dataservice-aansluiten-bedrijf/):

```bash
cd certificaten_dataservice_2025_12_preprod_omgeving
cat "DigiCert G2 TLS EU RSA4096 SHA384 2022 CA1.crt" "DigiCert Global Root G2.crt" > ../certs/kvk-preprod-ca-bundle.pem

cd ../certificaten_dataservice_2025_12_prd_omgeving
cat "DigiCert G2 TLS EU RSA4096 SHA384 2022 CA1.crt" "DigiCert Global Root G2.crt" > ../certs/kvk-prod-ca-bundle.pem
```

### Development

1. Run `mise run init` to initialize the environment.
2. Copy `.env.example` to `.env` and configure the certificate paths.
3. Run `mise run start -- registration --kvk-number <number>` to fetch a business registration.
4. Run `mise run start -- branch --branch-number <number>` to fetch establishment/branch details.
5. Run `mise run start -- financial-years --kvk-number <number>` to list available financial years.
6. Run `mise run start -- financial-statement --kvk-number <number> --financial-year <year>` to fetch a financial statement.
7. Run `mise run start -- ubo --kvk-number <number>` to fetch a UBO register extract.
8. Run `mise run start -- extract --kvk-number <number>` to fetch a business register extract.

# Test Accounts

Test numbers extracted from [Testset_Handelsregister_Dataservice_v4.8](https://www.kvk.nl/producten-bestellen/kvk-dataservice-aansluiten-testen/).

### Registration (`registration`)

Query by KVK number or RSIN to fetch business registration details.

| KVK Number | RSIN      | Legal Form                                   | Notes                            |
| ---------- | --------- | -------------------------------------------- | -------------------------------- |
| 90000013   | 992177315 | Commanditaire Vennootschap                   | Diacritic (ß) in street name     |
| 90000021   | N.v.t.    | Eenmanszaak                                  | 3 commercial branches            |
| 90000552   | 992063863 | Besloten Vennootschap                        | Foreign address (Czech Republic) |
| 90000064   | 992953327 | Vennootschap Onder Firma                     | Bankruptcy, ended                |
| 90000129   | 992476458 | Onderlinge Waarborg Maatschappij             | 7 functionaries                  |
| 90000706   | 992191865 | Publiekrechtelijke Rechtspersoon (Provincie) | 5 non-commercial branches        |
| 90001451   | 992424276 | Europese Naamloze Vennootschap (SE)          | EU law entity                    |
| 90000390   | 992509038 | Kerkgenootschap                              | Church organization              |
| 90004574   | -         | -                                            | Many branches                    |
| 90000137   | 992660725 | Stichting                                    | Partner name usage               |

### Branch (`branch`)

Query by branch number, KVK number, or RSIN to fetch branch details.

| Branch Number | KVK Number | Notes                     |
| ------------- | ---------- | ------------------------- |
| 990000764192  | 90000250   | Commercial branch         |
| 990000489902  | 90000021   | Commercial branch         |
| 990000626196  | 90001443   | Commercial branch         |
| 990000996027  | 90000129   | Extended legal form       |
| 999999999999  | 90006054   | Vestiging XL              |
| 999999999988  | 90006138   | huisnummerToevoeging      |
| 990000222308  | 90005147   | Longest street name in NL |
| 990000996064  | 90006151   | aanduidingBijHuisnummer   |
| 990000204616  | 90001605   | Non-commercial branch     |
| 990000036919  | 90003527   | Non-commercial branch     |

### Financial Years (`financial-years`)

Query by KVK number to list available financial years.

| KVK Number | Financial Year | Status       | Size        | Notes                  |
| ---------- | -------------- | ------------ | ----------- | ---------------------- |
| 99000148   | 2018           | Actueel      | Micro       | Preliminary            |
| 99000156   | 2019           | Gecorrigeerd | Klein       | Preliminary, corrected |
| 99000164   | 2020           | Actueel      | Middelgroot | Definitive             |
| 99000172   | 2021           | Gecorrigeerd | Groot       | Definitive, corrected  |

### Financial Statement (`financial-statement`)

Query by KVK number and financial year.

| KVK Number | Financial Year | Depot ID                    | Notes              |
| ---------- | -------------- | --------------------------- | ------------------ |
| 99000148   | 2018           | -386e3edc:17fda168cb1:d75   | Micro, preliminary |
| 99000156   | 2019           | 49984362:17fda19091e:27ea   | Small, corrected   |
| 99000164   | 2020           | 49984362:17fda19091e:-343   | Medium, definitive |
| 99000172   | 2021           | -386e3edc:17fda29dd8e:-3809 | Large, corrected   |

### UBO (`ubo`)

Query by KVK number to fetch UBO register extract.

| KVK Number | Legal Form                               | RSIN      | Notes                            |
| ---------- | ---------------------------------------- | --------- | -------------------------------- |
| 81408269   | Besloten Vennootschap                    | 865443750 | Standard, 75% economic interest  |
| 81408420   | Commanditaire Vennootschap               | 865443889 | Foreign TIN                      |
| 81408374   | Europees economisch samenwerkingsverband | 865443853 | Person without BSN, deceased UBO |
| 81408382   | Stichting                                | 865443865 | Shielded personal data           |
| 81408358   | Europese coöperatieve vennootschap (SCE) | 865443828 | UBO under investigation          |
| 81408331   | Europese naamloze vennootschap (SE)      | 865443816 | Multiple UBOs                    |
| 81408447   | Maatschap                                | 865443907 | Multiple UBOs                    |
| 81408463   | Rederij                                  | 865443920 | Diacritics in name               |

### Extract (`extract`)

Query by KVK number or RSIN to fetch a business register extract (DGU).

| KVK Number | RSIN      | Available in English |
| ---------- | --------- | -------------------- |
| 90006208   | 867240465 | Yes                  |
| 90006216   | 867240398 | Yes                  |

# References

[KVK Data Service Docs](https://www.kvk.nl/producten-bestellen/kvk-dataservice-aansluiten-bedrijf/)

[KVK Schemas](http://schemas.kvk.nl/)

[Zeep Docs](https://docs.python-zeep.org/)

[Pydantic Docs](https://docs.pydantic.dev/)

[Pydantic Settings Docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

[Loguru Docs](https://loguru.readthedocs.io/)
