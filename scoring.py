"""
scoring.py
Shared logic for engagement calculation and ranking across different platforms.
"""

import math

def calculate_engagement_score(likes: int, reposts: int, replies: int) -> int:
    """
    Unified formula for cross-platform engagement.
    Currently: (likes * 2) + (reposts * 3) + replies
    """
    return (likes * 2) + (reposts * 3) + replies

def add_z_scores(posts: list[dict]) -> None:
    """
    Add a normalized_score (Z-Score) to each post in the list.
    Standardizes engagement scores to allow fair cross-platform comparison.
    """
    if not posts:
        return
        
    scores = [p.get('engagement_score', 0) for p in posts]
    mean = sum(scores) / len(scores)
    
    # Calculate population standard deviation
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance)
    
    for p in posts:
        if std_dev == 0:
            p['normalized_score'] = 0.0
        else:
            p['normalized_score'] = (p.get('engagement_score', 0) - mean) / std_dev
