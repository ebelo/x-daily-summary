"""
classify_embeddings.py
Embedding-based post classification using Ollama's embedding endpoint + cosine similarity.

Instead of calling a generative LLM for every batch of posts (slow, sequential),
this module:
  1. Embeds the 6 category anchor descriptions once (~6 fast embed calls).
  2. Embeds all posts in a loop (~5 ms each via a single forward pass, no generation).
  3. Assigns each post to the category with the highest cosine similarity.

Expected speedup: classification phase ~20 min → ~10 seconds for 800 posts.

Environment variables (read from .env via main.py):
  OLLAMA_EMBED_MODEL  — embedding model to use (default: nomic-embed-text)
  OLLAMA_EMBED_URL    — Ollama embeddings endpoint (default: http://localhost:11434/api/embeddings)
"""

import os
import requests
import numpy as np
from classify import CATEGORIES

# ─────────────────────────────────────────
# Category anchor descriptions
# Richer descriptions give the embedding model more signal than bare category names.
# ─────────────────────────────────────────

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "Geopolitics & Security": (
        "International relations, military conflicts, wars, diplomacy, sanctions, "
        "NATO, UN, terrorism, espionage, border disputes, and national security."
    ),
    "Economics & Markets": (
        "Stock markets, financial markets, GDP, inflation, interest rates, central banks, "
        "crypto, corporate earnings, trade tariffs, supply chains, and economic policy."
    ),
    "AI & Technology": (
        "Artificial intelligence, machine learning, software, hardware, startups, "
        "big tech companies, cybersecurity, data privacy, robotics, and scientific computing."
    ),
    "Health & Science": (
        "Medicine, healthcare, diseases, vaccines, nutrition, fitness, biology, "
        "climate science, space exploration, and scientific research."
    ),
    "Sports & Performance": (
        "Football, soccer, basketball, tennis, athletics, Olympic sports, "
        "esports, sports results, athlete news, and high-performance competition."
    ),
    "Society & Culture": (
        "Social movements, politics, religion, art, music, film, pop culture, "
        "education, gender, race, identity, media, and everyday human trends."
    ),
}


# ─────────────────────────────────────────
# Core helpers
# ─────────────────────────────────────────

def get_embedding(text: str, model: str, ollama_url: str) -> list[float]:
    """
    Call Ollama's /api/embeddings endpoint and return a flat embedding vector.

    Raises requests.HTTPError or requests.ConnectionError on failure.
    """
    response = requests.post(
        ollama_url,
        json={"model": model, "prompt": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity between two vectors. Returns 0.0 for zero-norm inputs."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


# ─────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────

def classify_posts_embedding(
    posts: list[dict],
    ollama_url: str | None = None,
    embed_model: str | None = None,
) -> int:
    """
    Classify posts in-place by embedding cosine similarity.

    Writes a ``"category"`` key directly into each post dict that can be embedded.
    Posts with empty text are skipped (no category key set).

    Args:
        posts:       List of post dicts (must each have a ``"text"`` field).
        ollama_url:  Ollama embeddings endpoint URL. Falls back to env var OLLAMA_EMBED_URL
                     or ``http://localhost:11434/api/embeddings``.
        embed_model: Ollama embedding model name. Falls back to env var OLLAMA_EMBED_MODEL
                     or ``nomic-embed-text``.

    Returns:
        Number of posts successfully classified.
    """
    url = ollama_url or os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings")
    model = embed_model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    # ── Step 1: embed category anchors ──────────────────────────────────────
    print(f"[embed] Embedding {len(CATEGORIES)} category anchors (model={model})...", flush=True)
    category_embeddings: dict[str, list[float]] = {}
    for cat in CATEGORIES:
        description = CATEGORY_DESCRIPTIONS.get(cat, cat)
        try:
            category_embeddings[cat] = get_embedding(description, model, url)
        except Exception as exc:
            print(f"[embed] WARNING: failed to embed category '{cat}': {exc}", flush=True)

    if not category_embeddings:
        print("[embed] ERROR: could not embed any categories. Aborting classification.", flush=True)
        return 0

    # ── Step 2: embed posts and assign category ──────────────────────────────
    posts_to_embed = [p for p in posts if p.get("text", "").strip()]
    print(f"[embed] Embedding {len(posts_to_embed)} posts...", flush=True)

    classified = 0
    for i, post in enumerate(posts_to_embed):
        text = post["text"].strip()
        try:
            post_vec = get_embedding(text, model, url)
        except Exception as exc:
            print(f"[embed] WARNING: failed to embed post {i}: {exc}", flush=True)
            continue

        # Find the category with the highest cosine similarity.
        # post_vec is captured as a default arg to avoid the late-binding loop closure issue.
        best_cat = max(
            category_embeddings.keys(),
            key=lambda cat, vec=post_vec: cosine_similarity(vec, category_embeddings[cat]),
        )
        post["category"] = best_cat
        classified += 1

        # Progress indicator every 100 posts
        if (i + 1) % 100 == 0:
            print(f"[embed] {i + 1}/{len(posts_to_embed)} posts embedded...", flush=True)

    print(f"[embed] Classified {classified}/{len(posts_to_embed)} posts.", flush=True)
    return classified
