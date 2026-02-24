"""
tests/test_classify.py
Tests for classify.py: post parsing, classification, and category selection.
"""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from classify import (
    classify_post,
    classify_batch,
    select_top_per_category,
    CATEGORIES,
)


# ─────────────────────────────────────────────────────────────
# classify_post tests
# ─────────────────────────────────────────────────────────────

def test_classify_returns_known_category():
    """classify_post must always return one of the known CATEGORIES."""
    mock_fn = lambda prompt: "Geopolitics & Security"
    result = classify_post("Ukrainian forces advance.", mock_fn)
    assert result in CATEGORIES


def test_classify_partial_match():
    """Partial response like 'Economics' should still match 'Economics & Markets'."""
    mock_fn = lambda prompt: "Economics"
    result = classify_post("S&P 500 record high.", mock_fn)
    assert result == "Economics & Markets"


def test_classify_unknown_returns_none():
    """Unrecognised response should return None."""
    mock_fn = lambda prompt: "some random gibberish xyz 12345"
    result = classify_post("Random tweet.", mock_fn)
    assert result is None


# ─────────────────────────────────────────────────────────────
# select_top_per_category tests
# ─────────────────────────────────────────────────────────────

def _make_posts(category: str, count: int, base_engagement: int = 100) -> list[dict]:
    return [
        {"text": f"Post {i}", "engagement_score": base_engagement + i, "author": "user", "category": category}
        for i in range(count)
    ]


def test_select_top_n_limits_per_category():
    posts = _make_posts("Geopolitics & Security", 20)
    result = select_top_per_category(posts, top_n=5)
    assert len(result["Geopolitics & Security"]) == 5


def test_select_sorted_by_engagement():
    posts = _make_posts("Economics & Markets", 10)
    result = select_top_per_category(posts, top_n=3)
    selected = result["Economics & Markets"]
    engagements = [p["engagement_score"] for p in selected]
    assert engagements == sorted(engagements, reverse=True)


def test_classify_batch_success():
    """classify_batch should parse a numbered list of categories."""
    mock_fn = lambda prompt: "1. Geopolitics & Security\n2. Economics & Markets\n3. Unknown Category"
    texts = ["War in Ukraine", "GDP growth", "Random post"]
    results = classify_batch(texts, mock_fn)
    
    assert results[0] == "Geopolitics & Security"
    assert results[1] == "Economics & Markets"
    assert results[2] is None


def test_classify_batch_partial_response():
    """classify_batch should handle if the model returns fewer lines than requested."""
    mock_fn = lambda prompt: "1. AI & Technology"
    texts = ["New AI model", "Another tweet"]
    results = classify_batch(texts, mock_fn)
    
    assert results[0] == "AI & Technology"
    assert results[1] is None


def test_select_empty_category_omitted():
    posts = _make_posts("Geopolitics & Security", 5)
    result = select_top_per_category(posts, top_n=10)
    # Economics & Markets had no posts, should be absent or empty
    assert "Economics & Markets" not in result or len(result["Economics & Markets"]) == 0


def test_sports_performance_category_exists():
    """Sports & Performance must be a valid category."""
    assert "Sports & Performance" in CATEGORIES


def test_society_culture_category_exists():
    """Society & Culture must be a valid category."""
    assert "Society & Culture" in CATEGORIES


def test_other_category_removed():
    """The generic Other category should no longer exist."""
    assert "Other" not in CATEGORIES


def test_select_unknown_category_is_skipped():
    posts = [{'text': 'tweet', 'engagement': 50, 'author': 'u', 'category': 'totally unknown'}]
    result = select_top_per_category(posts, top_n=5)
    # Unknown category posts are skipped — no category should have this post
    total = sum(len(v) for v in result.values())
    assert total == 0
