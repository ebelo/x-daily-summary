import sys
import pathlib
import pytest
from unittest.mock import patch, MagicMock

# Ensure the project root is on sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from intel_report import generate_intel_report_local

@patch("intel_report.generate_section")
@patch("intel_report._generate_ollama")
@patch("classify_embeddings.classify_posts_embedding")
def test_generate_intel_report_local(mock_classify_embedding, mock_generate_ollama, mock_generate_section):
    """Test the full local Map-Reduce pipeline, including the Executive Summary pass."""

    # Mock input with two posts
    posts = [
        {"author_username": "user1", "text": "Post 1 text", "engagement_score": 100, "platform": "x"},
        {"author_username": "user2", "text": "Post 2 text", "engagement_score": 200, "platform": "x"}
    ]

    # 1. Mock the embedding classifier: assign categories directly into post dicts (in-place)
    def fake_classify(post_list, ollama_url=None, embed_model=None):
        post_list[0]["category"] = "Geopolitics & Security"
        post_list[1]["category"] = "AI & Technology"
        return 2
    mock_classify_embedding.side_effect = fake_classify

    # 2. Mock the category section generation
    def mock_section_gen(cat, posts):
        return f"**{cat}**\n- Mocked bullet for {cat} ({len(posts)} posts)"
    mock_generate_section.side_effect = mock_section_gen

    # 3. Mock the final executive summary generation pass
    mock_generate_ollama.return_value = "This is the mock executive summary."

    # Execute the pipeline
    result = generate_intel_report_local(posts, top_per_category=10)

    # Did it call the embedding classifier?
    mock_classify_embedding.assert_called_once()

    # Did it generate two sections?
    assert mock_generate_section.call_count == 2

    # Did it make exactly one call to the LLM (for the executive summary)?
    mock_generate_ollama.assert_called_once()

    # Does the final report contain the assembled parts?
    assert "# Global Situation Report:" in result
    assert "Agent: Ollama Intelligence | Model:" in result
    assert "**Executive Summary:**\nThis is the mock executive summary." in result
    assert "**Geopolitics & Security**\n- Mocked bullet for Geopolitics & Security (1 posts)" in result
    assert "**AI & Technology**\n- Mocked bullet for AI & Technology (1 posts)" in result
