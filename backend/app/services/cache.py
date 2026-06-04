"""Semantic cache — answer reuse for paraphrased questions.

"Who is Rajveer?" and "Tell me about Rajveer" should hit the same cached answer.
We embed the query and compare (cosine) against cached query vectors; a hit above
threshold returns instantly (~ms) instead of running the full agent loop (~1-2s,
~tokens). Calendar/booking queries always bypass — slots and bookings are live.
"""
from __future__ import annotations
import time

import numpy as np

from app import config
from app.services import embeddings

_CALENDAR_HINTS = ("book", "schedule", "meeting", "slot", "availab",
                   "calendar", "call with", "appointment")

_entries: list[dict] = []  # {vec, query, answer, sources, ts}


def _bypass(query: str) -> bool:
    q = query.lower()
    return any(h in q for h in _CALENDAR_HINTS)


def get(query: str):
    if _bypass(query):
        return None
    _evict()
    if not _entries:
        return None
    qv = embeddings.embed_one(query)
    sims = np.array([float(np.dot(qv, e["vec"])) for e in _entries])
    i = int(sims.argmax())
    if sims[i] >= config.CACHE_THRESHOLD:
        return {"answer": _entries[i]["answer"],
                "sources": _entries[i]["sources"],
                "similarity": round(float(sims[i]), 3)}
    return None


def put(query: str, answer: str, sources: list) -> None:
    if _bypass(query) or not answer.strip():
        return
    qv = embeddings.embed_one(query)
    # skip near-duplicates
    for e in _entries:
        if float(np.dot(qv, e["vec"])) >= 0.98:
            return
    _entries.append({"vec": qv, "query": query, "answer": answer,
                     "sources": sources, "ts": time.time()})
    if len(_entries) > config.CACHE_MAX_ENTRIES:
        _entries.pop(0)


def _evict() -> None:
    now = time.time()
    cutoff = now - config.CACHE_TTL_SECONDS
    _entries[:] = [e for e in _entries if e["ts"] >= cutoff]


def stats() -> dict:
    return {"size": len(_entries), "threshold": config.CACHE_THRESHOLD,
            "ttl_seconds": config.CACHE_TTL_SECONDS}
