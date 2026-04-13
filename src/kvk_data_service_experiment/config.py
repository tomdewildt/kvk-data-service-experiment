from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    PREPROD = "preprod"
    PROD = "prod"


class KVKDataServiceConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KVK_", env_file=".env", env_file_encoding="utf-8")

    ENV: Environment = Environment.PROD

    CERT_PATH: Path
    KEY_PATH: Path
    CA_BUNDLE_PATH: Path

    CACHE_DIR: Path | None = Path(".cache")


config = KVKDataServiceConfig()  # type: ignore
