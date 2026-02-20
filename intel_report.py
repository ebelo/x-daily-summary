"""
intel_report.py
Synthesizes raw X summaries into strategic intelligence reports.
Supports two backends: Gemini (cloud) or Ollama (local, e.g. Mistral).

Configure in .env:
  INTEL_BACKEND=gemini  (default)    — uses GEMINI_API_KEY
  INTEL_BACKEND=ollama               — uses OLLAMA_MODEL and OLLAMA_URL
"""

import os
import requests
from google import genai
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_message

SYSTEM_PROMPT = """You are a Senior Strategic Intelligence Analyst. Transform the following social media posts into a high-level "Global Situation Report".

STRUCTURE:
1. Title: Global Situation Report: [Current Date]
2. Executive Summary: One paragraph overview of the most critical global trends.
3. Thematic sections (I, II, III...): Group info into logical themes (e.g. "Middle East", "AI & Tech", "Macroeconomics").
4. Use bullet points for specific developments within themes.
5. VI. Economic Data Points: Market data, crypto, corporate news.
6. VII. Health and Social Perspectives: Secondary social trends.

TONE: Professional, concise, objective. Focus on strategic significance, not just listing facts.
"""


# ─────────────────────────────────────────
# Gemini backend
# ─────────────────────────────────────────

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_message(match="RESOURCE_EXHAUSTED")
)
def _gemini_generate(client, model: str, contents: str):
    """Call Gemini with exponential backoff on rate limit."""
    return client.models.generate_content(model=model, contents=contents)


def _generate_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not set in .env"
    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    try:
        response = _gemini_generate(client, model, prompt)
        return response.text
    except Exception as e:
        return f"Gemini error: {str(e)}"


# ─────────────────────────────────────────
# Ollama backend
# ─────────────────────────────────────────

def _generate_ollama(prompt: str) -> str:
    url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    model = os.getenv("OLLAMA_MODEL", "mistral")
    try:
        response = requests.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=300,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        return f"Ollama error: {str(e)}"


# ─────────────────────────────────────────
# Public API
# ─────────────────────────────────────────

def generate_intel_report(raw_summary_md: str) -> str:
    """Generate a strategic intelligence report from the raw markdown summary."""
    backend = os.getenv("INTEL_BACKEND", "gemini").lower()
    prompt = f"{SYSTEM_PROMPT}\n\nRAW SUMMARY:\n{raw_summary_md}"

    print(f"[intel] Using backend: {backend}")

    if backend == "ollama":
        return _generate_ollama(prompt)
    return _generate_gemini(prompt)
