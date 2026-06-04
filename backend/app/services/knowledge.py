"""The two retrieval tools — the hybrid heart of the RAG system.

lookup_facts(category)   -> deterministic structured facts from persona.yaml
search_knowledge(query)  -> semantic search over the FAISS corpus

Why hybrid: facts like skills/education/contact must read identically every
time (YAML guarantees that); nuanced questions ("how does DocBlock work?") need
semantic matching across chunked READMEs (FAISS handles that). The LLM picks.
"""
from __future__ import annotations
import json

import faiss
import yaml

from app import config
from app.services import embeddings

# --- loaded once at import ---
_index = faiss.read_index(str(config.INDEX_DIR / "faiss.index"))
_chunks: list[dict] = json.loads((config.INDEX_DIR / "chunks.json").read_text("utf-8"))
_persona: dict = yaml.safe_load(config.PERSONA_YAML.read_text("utf-8"))

# Below this similarity the top hit is effectively noise -> let the model refuse.
RELEVANCE_FLOOR = 0.45

FACT_CATEGORIES = ["identity", "contact", "education", "experience", "skills",
                   "projects", "achievements", "leadership", "why_hire",
                   "strengths", "weaknesses"]


def lookup_facts(category: str) -> dict:
    """Return structured facts for a category (fast, deterministic)."""
    cat = (category or "").strip().lower()
    if cat in ("all", ""):
        data = {k: _persona[k] for k in FACT_CATEGORIES if k in _persona}
    elif cat in _persona:
        data = {cat: _persona[cat]}
    else:
        return {"error": f"unknown category '{category}'",
                "available": FACT_CATEGORIES}
    return {"category": cat or "all", "facts": data}


def search_knowledge(query: str, k: int | None = None) -> dict:
    """Semantic search over resume + GitHub + persona corpus."""
    k = k or config.TOP_K
    qv = embeddings.embed([query])
    scores, ids = _index.search(qv, k)
    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue
        c = _chunks[idx]
        results.append({
            "score": round(float(score), 3),
            "title": c.get("title"),
            "source": c.get("source"),
            "repo": c.get("repo"),
            "section": c.get("section"),
            "text": c["text"],
        })
    top = results[0]["score"] if results else 0.0
    return {
        "query": query,
        "results": results,
        "max_score": top,
        "weak_match": top < RELEVANCE_FLOOR,  # signal for the model to be cautious
    }
