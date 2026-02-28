"""
tests/test_fetchers_base.py
Tests for the BasePlatformFetcher ABC contract.
"""

import pytest
from fetchers.base import BasePlatformFetcher


def test_cannot_instantiate_base_directly():
    """BasePlatformFetcher must not be instantiatable — it has abstract methods."""
    with pytest.raises(TypeError):
        BasePlatformFetcher()  # type: ignore[abstract]


def test_subclass_missing_both_methods_raises():
    """A subclass that implements neither method should raise TypeError."""
    class EmptyFetcher(BasePlatformFetcher):
        pass

    with pytest.raises(TypeError):
        EmptyFetcher()  # type: ignore[abstract]


def test_subclass_missing_fetch_posts_raises():
    """A subclass that only implements is_configured should raise TypeError."""
    class PartialFetcher(BasePlatformFetcher):
        platform_name = "partial"

        def is_configured(self) -> bool:
            return True

    with pytest.raises(TypeError):
        PartialFetcher()  # type: ignore[abstract]


def test_concrete_subclass_works():
    """A fully concrete subclass should be instantiatable and callable."""
    class DummyFetcher(BasePlatformFetcher):
        platform_name = "dummy"

        def is_configured(self) -> bool:
            return True

        def fetch_posts(self, hours: int = 24, limit: int | None = None) -> list[dict]:
            return []

    fetcher = DummyFetcher()
    assert fetcher.is_configured() is True
    assert fetcher.fetch_posts() == []
    assert fetcher.platform_name == "dummy"
