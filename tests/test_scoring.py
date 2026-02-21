import pytest
import math
from scoring import calculate_engagement_score, add_z_scores

def test_calculate_engagement_score():
    # likes*2 + reposts*3 + replies
    assert calculate_engagement_score(10, 5, 2) == (10*2 + 5*3 + 2) # Expected: 20 + 15 + 2 = 37
    assert calculate_engagement_score(0, 0, 0) == 0

def test_add_z_scores_basic():
    posts = [
        {"engagement_score": 10},
        {"engagement_score": 20},
        {"engagement_score": 30},
    ]
    add_z_scores(posts)
    # Statistics used for normalization:
    # - The average engagement score for this set is twenty
    # - Variance reflects the spread of scores around the mean
    # - Standard deviation is used as the denominator for scaling
    assert posts[0]["normalized_score"] == pytest.approx((10 - 20) / 8.1649, rel=1e-4)
    assert posts[1]["normalized_score"] == pytest.approx(0.0)
    assert posts[2]["normalized_score"] == pytest.approx((30 - 20) / 8.1649, rel=1e-4)

def test_add_z_scores_single_post():
    posts = [{"engagement_score": 100}]
    add_z_scores(posts)
    # With a single post, mean equals the score and standard deviation is zero.
    assert posts[0]["normalized_score"] == pytest.approx(0.0)

def test_add_z_scores_zero_variance():
    posts = [
        {"engagement_score": 50},
        {"engagement_score": 50},
    ]
    add_z_scores(posts)
    assert posts[0]["normalized_score"] == pytest.approx(0.0)
    assert posts[1]["normalized_score"] == pytest.approx(0.0)

def test_add_z_scores_empty():
    posts = []
    add_z_scores(posts)
    assert posts == []
