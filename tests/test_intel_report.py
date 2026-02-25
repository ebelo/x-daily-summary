import sys
import pathlib
import pytest
from unittest.mock import patch, MagicMock

# Ensure the project root is on sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from intel_report import generate_intel_report_local

@patch("classify.classify_batch")
@patch("intel_report.generate_section")
@patch("intel_report._generate_ollama")
def test_generate_intel_report_local(mock_generate_ollama, mock_generate_section, mock_classify_batch):
    """Test the full local Map-Reduce pipeline, including the Executive Summary pass."""
    
    # Mock input with two posts
    posts = [
        {"author_username": "user1", "text": "Post 1 text", "engagement_score": 100, "platform": "x"},
        {"author_username": "user2", "text": "Post 2 text", "engagement_score": 200, "platform": "x"}
    ]

    # 1. Mock the batch classification to classify both posts
    mock_classify_batch.return_value = ["Geopolitics & Security", "AI & Technology"]

    # 2. Mock the category section generation
    def mock_section_gen(cat, posts):
        return f"**{cat}**\n- Mocked bullet for {cat} ({len(posts)} posts)"
    mock_generate_section.side_effect = mock_section_gen

    # 3. Mock the final executive summary generation pass
    mock_generate_ollama.return_value = "This is the mock executive summary."

    # Execute the pipeline
    result = generate_intel_report_local(posts, top_per_category=10)

    # Assertions
    # Did it extract the two posts and classify them?
    mock_classify_batch.assert_called_once()
    
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
