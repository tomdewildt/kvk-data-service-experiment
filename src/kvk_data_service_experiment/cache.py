import hashlib
from pathlib import Path

from loguru import logger
from zeep.cache import Base as CacheBase


class XmlFileCache(CacheBase):
    def __init__(self, path: Path):
        self._path = path
        self._path.mkdir(parents=True, exist_ok=True)

    def add(self, url: str, content: bytes | str) -> None:
        filename = hashlib.sha256(url.encode()).hexdigest() + ".xml"
        filepath = self._path / filename
        if isinstance(content, str):
            filepath.write_text(content)
        else:
            filepath.write_bytes(content)
        logger.debug("Cached '{}' to '{}'", url, filepath)

    def get(self, url: str) -> bytes | None:
        filename = hashlib.sha256(url.encode()).hexdigest() + ".xml"
        filepath = self._path / filename
        if filepath.exists():
            logger.debug("Cache item found for '{}'", url)
            return filepath.read_bytes()
        logger.debug("Cache item missing for '{}'", url)
        return None
