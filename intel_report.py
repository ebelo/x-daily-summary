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

STRUCTURE YOUR OUTPUT EXACTLY AS FOLLOWS:
1. Title: Global Situation Report: [Current Date]
2. Executive Summary: One paragraph overview of the most critical global trends.
3. Thematic sections (use these EXACT categories, do not invent others):
   - Geopolitics & Security
   - Economics & Markets
   - AI & Technology
   - Health & Science
   - Sports & Performance
   - Society & Culture
4. Use bullet points for specific developments within themes.

TONE: Professional, concise, objective. Focus on strategic significance.

STRICT DATA RULES:
- ONLY include information explicitly present in the RAW SUMMARY provided below.
- Do NOT use knowledge from your training data — no invented names, handles, events, or figures.
- If a section has no relevant data, write "No significant developments identified."
"""

# Simplified prompt for local models — uses fill-in-the-blanks format
# so the model doesn't have to interpret abstract formatting instructions
OLLAMA_SYSTEM_PROMPT = """You are a strategic analyst. Read the social media posts below and complete the following report template. Only use information from the posts. Do not invent any facts, names, or market figures.

---
**Global Situation Report: [fill in today's date]**

**Executive Summary:**
[Write one paragraph summarizing the most critical global developments from the posts.]

**I. Geopolitics & Security**
[Bullet points on military, diplomatic, conflict-related news from the posts only.]

**II. Economics & Markets**
[Bullet points on economic data, stock news, tariffs, crypto, and corporate developments from the posts only.]

**III. AI & Technology**
[Bullet points on AI, software, and tech news from the posts only.]

**IV. Health & Science**
[Bullet points on health, medicine, nutrition, and science news from the posts only. If none, write: No significant developments.]

**V. Other Notable Developments**
[Any other relevant developments not covered above. If none, write: No significant developments.]
---

Complete the report above using ONLY the posts provided. Do not add any information not present in the posts below.

POSTS:
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
# Map-Reduce pipeline (Ollama / local)
# ─────────────────────────────────────────

SECTION_PROMPT = """You are a strategic intelligence analyst. Write a short thematic section for a Global Situation Report using ONLY the posts below. Use bullet points. Be concise and professional.

CRITICAL RULES:
1. ONLY use information explicitly stated in the provided posts.
2. DO NOT hallucinate, guess, infer, or extrapolate.
3. DO NOT speculate on potential impacts, repercussions, or global consequences (e.g., do not mention COVID-19 or historical events unless explicitly in the text).
4. If a post's relation to the topic is weak, just state the facts of the post without padding.

Section topic: {category}

Posts:
{posts}

Write the section now:"""


def _format_posts_for_section(posts: list[dict]) -> str:
    return "\n".join(
        f"- [{p['author']}] {p['text']}" for p in posts
    )


def generate_section(category: str, posts: list[dict]) -> str:
    """Generate one section of the intel report from a small list of posts."""
    if not posts:
        return f"**{category}**\nNo significant developments identified.\n"

    prompt = SECTION_PROMPT.format(
        category=category,
        posts=_format_posts_for_section(posts),
    )
    section_text = _generate_ollama(prompt).strip()

    # Strip any repeated category header the model may have added at the top
    first_line = section_text.splitlines()[0].strip() if section_text else ""
    if category.lower() in first_line.lower():
        section_text = "\n".join(section_text.splitlines()[1:]).strip()

    # Strip hallucinated URLs (model adds links from training memory)
    import re
    section_text = re.sub(r"https?://\S+", "", section_text)
    section_text = re.sub(r"\(\s*\)", "", section_text)  # clean up empty parens left behind
    section_text = re.sub(r"\[\s*\]\(\s*\)", "", section_text)  # clean up empty markdown links
    section_text = "\n".join(line.rstrip() for line in section_text.splitlines())

    return f"**{category}**\n{section_text}\n"


def generate_intel_report_local(
    raw_summary_md: str,
    top_per_category: int = 10,
) -> str:
    """
    Map-reduce pipeline for local models:
      1. Parse ALL posts from the summary markdown
      2. Classify each post individually (1 model call per post)
      3. Select top N per category by engagement
      4. Generate one section per category (1 model call per section)
      5. Assemble the final report
    """
    from classify import parse_posts_from_markdown, classify_post, select_top_per_category
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    model_name = os.getenv("OLLAMA_MODEL", "mistral")
    agent_info = f"Agent: Ollama Intelligence | Model: {model_name}"

    # Step 1: parse all posts
    all_posts = parse_posts_from_markdown(raw_summary_md)
    print(f"[intel] Map-reduce: {len(all_posts)} posts to classify...", flush=True)

    # Step 2: classify every post in batches of 10
    from classify import classify_batch
    batch_size = 10
    
    for i in range(0, len(all_posts), batch_size):
        batch = all_posts[i:i+batch_size]
        texts = [p["text"] for p in batch]
        
        print(f"[intel] Classifying batch {i//batch_size + 1}/{(len(all_posts) + batch_size - 1)//batch_size}...", flush=True)
        results = classify_batch(texts, _generate_ollama)
        
        # Assign results back to posts
        for j, category in enumerate(results):
            if category:
                batch[j]["category"] = category

    classified = [p for p in all_posts if p.get("category")]
    print(f"[intel] {len(classified)}/{len(all_posts)} posts classified (rest unrecognised, skipped)", flush=True)

    # Step 3: select top N per category
    by_category = select_top_per_category(classified, top_n=top_per_category)
    category_counts = {cat: len(posts) for cat, posts in by_category.items()}
    print(f"[intel] Category distribution: {category_counts}", flush=True)

    # Step 4: generate one section per category
    sections = []
    for cat, posts in by_category.items():
        print(f"[intel] Generating section: {cat} ({len(posts)} posts)...", flush=True)
        sections.append(generate_section(cat, posts))

    # Step 4.5: generate an executive summary based on the drafted sections
    combined_sections = "\n\n".join(sections)
    print("[intel] Generating Executive Summary...", flush=True)
    exec_summary_prompt = f"""You are a Strategic Intelligence Analyst.
Read the following 6 drafted sections of a Global Situation Report.
Write a SINGLE PARAGRAPH (max 4-5 sentences) "Executive Summary" that highlights the most critical developments from these sections.
Do not use bullet points. Do not invent facts.

DRAFTED SECTIONS:
{combined_sections}
"""
    exec_summary_text = _generate_ollama(exec_summary_prompt).strip()

    # Step 5: assemble
    report = f"# Global Situation Report: {today}\n"
    report += f"*{agent_info}*\n\n"
    report += "**Executive Summary:**\n"
    report += exec_summary_text + "\n\n---\n\n"
    report += "\n---\n\n".join(sections)
    return report


# ─────────────────────────────────────────
# Public API
# ─────────────────────────────────────────

def generate_intel_report(raw_summary_md: str) -> str:
    """Generate a strategic intelligence report from the raw markdown summary."""
    backend = os.getenv("INTEL_BACKEND", "gemini").lower()
    print(f"[intel] Using backend: {backend}", flush=True)

    if backend == "ollama":
        top_per_cat = int(os.getenv("OLLAMA_TOP_PER_CATEGORY", "10"))
        return generate_intel_report_local(raw_summary_md, top_per_cat)

    model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    prompt = f"{SYSTEM_PROMPT}\n\nRAW SUMMARY:\n{raw_summary_md}"
    raw_report = _generate_gemini(prompt)

    # Prepend attribution for Gemini as well
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    agent_info = f"Agent: Gemini Intelligence | Model: {model_name}"
    
    # If the model already provided a title, we might want to insert below it.
    # But to be safe and consistent with Ollama, we rebuild the header.
    report = f"# Global Situation Report: {today}\n"
    report += f"*{agent_info}*\n\n"
    
    # Remove any title line the model might have returned (usually # Global Situation Report...)
    lines = raw_report.splitlines()
    if lines and (lines[0].startswith("#") or "Global Situation Report" in lines[0]):
        raw_report = "\n".join(lines[1:]).strip()
    
    return report + raw_report
