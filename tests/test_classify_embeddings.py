"""
tests/test_classify_embeddings.py
Tests for classify_embeddings.py — embedding-based post classification.

All tests monkeypatch requests.post to avoid needing a live Ollama instance.
"""

import sys
import pathlib
import math
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from classify_embeddings import (
    cosine_similarity,
    classify_posts_embedding,
    CATEGORY_DESCRIPTIONS,
)
from classify import CATEGORIES


# ─────────────────────────────────────────────────────────────
# cosine_similarity unit tests
# ─────────────────────────────────────────────────────────────

def test_cosine_identical_vectors():
    """Identical vectors must give similarity 1.0."""
    v = [1.0, 2.0, 3.0]
    assert math.isclose(cosine_similarity(v, v), 1.0, abs_tol=1e-6)


def test_cosine_orthogonal_vectors():
    """Orthogonal vectors must give similarity 0.0."""
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert math.isclose(cosine_similarity(a, b), 0.0, abs_tol=1e-6)


def test_cosine_zero_vector_returns_zero():
    """Zero-norm vector must return 0.0 without crashing."""
    assert math.isclose(cosine_similarity([0.0, 0.0], [1.0, 0.0]), 0.0, abs_tol=1e-6)


def test_cosine_opposite_vectors():
    """Opposite vectors must give similarity -1.0."""
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert math.isclose(cosine_similarity(a, b), -1.0, abs_tol=1e-6)


# ─────────────────────────────────────────────────────────────
# classify_posts_embedding integration tests (mocked HTTP)
# ─────────────────────────────────────────────────────────────

def _make_embed_response(vector: list[float]):
    """Build a minimal mock response object for requests.post."""
    class MockResponse:
        def raise_for_status(self):
            # Intentionally a no-op: mock response always represents a 200 OK.
            pass
        def json(self):
            return {"embedding": vector}
    return MockResponse()


def test_classify_posts_embedding_assigns_correct_category(monkeypatch):
    """
    Posts should be assigned to the category whose anchor embedding is
    most similar. We fake embeddings so each category gets a distinct
    one-hot vector, making the expected assignment deterministic.
    """
    dim = len(CATEGORIES)
    # Each category anchor is a one-hot vector at its own index
    cat_vectors = {cat: [1.0 if j == i else 0.0 for j in range(dim)]
                   for i, cat in enumerate(CATEGORIES)}

    call_count = [0]

    def fake_post(url, json=None, timeout=None):
        prompt = json.get("prompt", "")
        # Map description → category vector
        for cat, desc in CATEGORY_DESCRIPTIONS.items():
            if prompt == desc:
                call_count[0] += 1
                return _make_embed_response(cat_vectors[cat])
        # Default: post text — return vector for "AI & Technology" (index 2)
        call_count[0] += 1
        return _make_embed_response(cat_vectors["AI & Technology"])

    monkeypatch.setattr("classify_embeddings.requests.post", fake_post)

    posts = [{"text": "GPT-5 just dropped, it's incredible!"}]
    result_count = classify_posts_embedding(posts)

    assert result_count == 1
    assert posts[0].get("category") == "AI & Technology"


def test_classify_posts_embedding_skips_empty_text(monkeypatch):
    """Posts with empty text should be skipped entirely (no 'category' key set)."""
    monkeypatch.setattr(
        "classify_embeddings.requests.post",
        lambda *a, **kw: _make_embed_response([1.0, 0.0]),
    )
    posts = [{"text": ""}, {"text": "   "}]
    result_count = classify_posts_embedding(posts)
    assert result_count == 0
    assert "category" not in posts[0]
    assert "category" not in posts[1]


def test_classify_posts_embedding_all_same_vector_picks_first(monkeypatch):
    """
    When all embeddings are identical, max() picks the first category in the dict.
    The key requirement is: no crash, and some valid category is always returned.
    """
    monkeypatch.setattr(
        "classify_embeddings.requests.post",
        lambda *a, **kw: _make_embed_response([1.0] * 10),
    )
    posts = [{"text": "Some post with ambiguous topic."}]
    classify_posts_embedding(posts)
    assert posts[0].get("category") in CATEGORIES


def test_classify_posts_embedding_handles_http_error(monkeypatch):
    """If an embed call fails for a post, it should be skipped gracefully."""
    embed_call = [0]

    def flaky_post(url, json=None, timeout=None):
        prompt = json.get("prompt", "")
        # Category anchors succeed; post embed fails
        for desc in CATEGORY_DESCRIPTIONS.values():
            if prompt == desc:
                return _make_embed_response([1.0, 0.0, 0.0])
        embed_call[0] += 1
        raise OSError("simulated network error")

    monkeypatch.setattr("classify_embeddings.requests.post", flaky_post)

    posts = [{"text": "This post will fail to embed."}]
    result_count = classify_posts_embedding(posts)
    assert result_count == 0
    assert "category" not in posts[0]


def test_classify_posts_embedding_multiple_posts(monkeypatch):
    """All non-empty posts should receive a category from the known CATEGORIES list."""
    monkeypatch.setattr(
        "classify_embeddings.requests.post",
        lambda *a, **kw: _make_embed_response([0.5] * 8),
    )
    posts = [
        {"text": f"Post number {i}"} for i in range(5)
    ]
    result_count = classify_posts_embedding(posts)
    assert result_count == 5
    for post in posts:
        assert post.get("category") in CATEGORIES


def test_category_descriptions_cover_all_categories():
    """Every CATEGORY must have a rich description defined."""
    for cat in CATEGORIES:
        assert cat in CATEGORY_DESCRIPTIONS, f"Missing description for: {cat}"
        assert len(CATEGORY_DESCRIPTIONS[cat]) > 30, f"Description too short for: {cat}"
