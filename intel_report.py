"""
intel_report.py
Uses Google GenAI SDK to synthesize raw X summaries into strategic intelligence reports.
"""

import os
import time
from google import genai
from datetime import datetime, timezone
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_message

SYSTEM_PROMPT = """
You are a Senior Strategic Intelligence Analyst. Your task is to transform a raw list of social media posts (X/Twitter) into a high-level "Global Situation Report".

STRUCTURE YOUR REPORT AS FOLLOWS:
1. Title: Global Situation Report: [Current Date]
2. Executive Summary: A one-paragraph high-level overview of the most critical global trends and events captured in the data.
3. Thematic sections (I, II, III...): Group the information into logical geopolitical or industry themes (e.g., "Middle East Crisis", "AI & Technology Breakthroughs", "Macroeconomic Shifts"). 
4. Use bullet points for specific developments within themes.
5. VI. Economic Data Points: A specific section for market data, crypto, or corporate revenue news.
6. VII. Health and Social Perspectives: Any secondary trends regarding lifestyle, health, or social observations.

TONE:
Professional, concise, and objective. Focus on "Strategic Significance" rather than just listing facts.

INPUT DATA:
The following is a markdown summary of posts from the last 24 hours.
"""

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_message(match="RESOURCE_EXHAUSTED")
)
def _generate_with_retry(client, model, contents):
    """Internal helper to call Gemini with exponential backoff."""
    return client.models.generate_content(
        model=model,
        contents=contents
    )


def generate_intel_report(raw_summary_md: str) -> str:
    """Sends the raw summary to Gemini and returns a synthesized intelligence report."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not found in environment."

    client = genai.Client(api_key=api_key)
    prompt = f"{SYSTEM_PROMPT}\n\nRAW SUMMARY:\n{raw_summary_md}"
    
    try:
        # Using gemini-flash-latest (1.5 Flash) which often has higher quota
        response = _generate_with_retry(client, 'gemini-flash-latest', prompt)
        return response.text
    except Exception as e:
        return f"Error after retries: {str(e)}"
