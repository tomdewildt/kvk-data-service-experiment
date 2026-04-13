import hashlib
from pathlib import Path

from kvk_data_service_experiment.cache import XmlFileCache


class TestXmlFileCache:
    def test_cache_returns_none_for_unknown_url(self, tmp_path: Path) -> None:
        # Arrange
        cache = XmlFileCache(tmp_path)

        # Act
        result = cache.get("http://example.com/schema.xsd")

        # Assert
        assert result is None

    def test_cache_returns_bytes_content_after_adding(self, tmp_path: Path) -> None:
        # Arrange
        cache = XmlFileCache(tmp_path)
        url = "http://example.com/schema.xsd"

        # Act
        cache.add(url, b"<schema/>")

        # Assert
        assert cache.get(url) == b"<schema/>"

    def test_cache_stores_string_content_as_bytes(self, tmp_path: Path) -> None:
        # Arrange
        cache = XmlFileCache(tmp_path)
        url = "http://example.com/schema.xsd"

        # Act
        cache.add(url, "<schema/>")

        # Assert
        assert cache.get(url) == b"<schema/>"

    def test_cache_uses_sha256_of_url_as_filename(self, tmp_path: Path) -> None:
        # Arrange
        cache = XmlFileCache(tmp_path)
        url = "http://example.com/schema.xsd"

        # Act
        cache.add(url, b"<schema/>")

        # Assert
        expected_filename = hashlib.sha256(url.encode()).hexdigest() + ".xml"
        assert (tmp_path / expected_filename).exists()

    def test_cache_creates_nested_directories_if_missing(self, tmp_path: Path) -> None:
        # Arrange
        cache_dir = tmp_path / "nested" / "cache"

        # Act
        cache = XmlFileCache(cache_dir)

        # Assert
        assert cache_dir.exists()
        cache.add("http://example.com/test.xsd", b"<test/>")
        assert cache.get("http://example.com/test.xsd") == b"<test/>"

    def test_cache_stores_different_urls_independently(self, tmp_path: Path) -> None:
        # Arrange
        cache = XmlFileCache(tmp_path)

        # Act
        cache.add("http://example.com/a.xsd", b"<a/>")
        cache.add("http://example.com/b.xsd", b"<b/>")

        # Assert
        assert cache.get("http://example.com/a.xsd") == b"<a/>"
        assert cache.get("http://example.com/b.xsd") == b"<b/>"

    def test_cache_overwrites_existing_entry_for_same_url(self, tmp_path: Path) -> None:
        # Arrange
        cache = XmlFileCache(tmp_path)
        url = "http://example.com/schema.xsd"

        # Act
        cache.add(url, b"<old/>")
        cache.add(url, b"<new/>")

        # Assert
        assert cache.get(url) == b"<new/>"
