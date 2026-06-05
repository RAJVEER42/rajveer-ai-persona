"""One-time corpus build: resume + GitHub READMEs + repo cards + persona facts
-> chunk -> embed (local bge-small) -> FAISS index on disk.

Run:  python -m app.ingestion.ingest
Output: app/data/index/faiss.index  +  app/data/index/chunks.json

Design notes
------------
- Section-aware chunking for the resume (split on `## ` headers) keeps a chunk's
  section context intact, which improves retrieval precision.
- Recursive character splitting for READMEs (mirrors Rajveer's DocBlock: prefer
  paragraph -> line -> sentence boundaries before hard cuts).
- Repo "cards" guarantee every original repo is represented even when it has no
  README (e.g. phi3-pr-reviewer).
- Cosine similarity via a normalized inner-product FAISS index (IndexFlatIP).
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import faiss
import numpy as np
import yaml
from fastembed import TextEmbedding

from app import config

# ---------- chunking helpers ----------

def _recursive_split(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    """Split text on the strongest available boundary that fits `size`."""
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    seps = ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]
    sep = next((s for s in seps if s in text), "")
    chunks: list[str] = []
    if sep:
        parts, buf = text.split(sep), ""
        for part in parts:
            piece = (buf + sep + part) if buf else part
            if len(piece) <= size:
                buf = piece
            else:
                if buf:
                    chunks.append(buf)
                buf = part if len(part) <= size else ""
                if len(part) > size:  # a single oversized part -> hard window it
                    chunks.extend(_window(part, size, overlap))
        if buf:
            chunks.append(buf)
    else:
        chunks = _window(text, size, overlap)
    # stitch overlap between adjacent chunks for recall across boundaries
    out: list[str] = []
    for i, c in enumerate(chunks):
        c = c.strip()
        if len(c) < 24:  # drop footers / page-number artefacts (DocBlock rule)
            continue
        if i > 0 and overlap:
            tail = chunks[i - 1][-overlap:]
            c = (tail + " " + c).strip()
        out.append(c)
    return out


def _window(text: str, size: int, overlap: int) -> list[str]:
    step = max(1, size - overlap)
    return [text[i:i + size] for i in range(0, len(text), step)]


# ---------- source loaders ----------

def load_resume_chunks() -> list[dict]:
    text = config.RESUME_MD.read_text(encoding="utf-8")
    chunks: list[dict] = []
    # split on level-2 headers, keep the header with its body
    sections = re.split(r"\n(?=## )", text)
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        header = sec.splitlines()[0].lstrip("# ").strip() or "Summary"
        for piece in _recursive_split(sec, size=700, overlap=80):
            chunks.append({
                "text": piece,
                "source": "resume",
                "section": header,
                "title": f"Resume — {header}",
            })
    return chunks


def load_readme_chunks() -> list[dict]:
    chunks: list[dict] = []
    for path in sorted(config.CORPUS_DIR.glob("*.README.md")):
        repo = path.name.replace(".README.md", "")
        raw = path.read_text(encoding="utf-8")
        clean = _strip_markdown_noise(raw)
        for piece in _recursive_split(clean, size=900, overlap=150):
            chunks.append({
                "text": piece,
                "source": "github",
                "repo": repo,
                "doc_type": "readme",
                "title": f"GitHub README — {repo}",
            })
    return chunks


def load_commit_chunks() -> list[dict]:
    """Commit-history subjects per repo — so questions answerable only from
    commit history ('we'll check') have grounding."""
    chunks: list[dict] = []
    for path in sorted(config.CORPUS_DIR.glob("*.commits.md")):
        repo = path.name.replace(".commits.md", "")
        raw = path.read_text(encoding="utf-8")
        for piece in _recursive_split(raw, size=900, overlap=120):
            chunks.append({
                "text": piece,
                "source": "github",
                "repo": repo,
                "doc_type": "commits",
                "title": f"GitHub commit history — {repo}",
            })
    return chunks


def load_repo_card_chunks() -> list[dict]:
    repos = json.loads(config.REPOS_JSON.read_text(encoding="utf-8"))
    chunks: list[dict] = []
    for r in repos:
        desc = r.get("description") or "no description provided"
        topics = ", ".join(r.get("topics") or []) or "n/a"
        card = (
            f"GitHub repository '{r['name']}' by Rajveer Bishnoi (RAJVEER42). "
            f"Primary language: {r.get('language') or 'mixed'}. "
            f"Description: {desc}. Topics: {topics}. "
            f"URL: {r.get('html_url')}. "
            f"Homepage: {r.get('homepage') or 'none'}."
        )
        chunks.append({
            "text": card,
            "source": "github",
            "repo": r["name"],
            "doc_type": "repo_card",
            "title": f"GitHub repo — {r['name']}",
        })
    return chunks


def load_persona_chunks() -> list[dict]:
    data = yaml.safe_load(config.PERSONA_YAML.read_text(encoding="utf-8"))
    chunks: list[dict] = []

    def add(text: str, section: str):
        text = text.strip()
        if text:
            chunks.append({"text": text, "source": "personal",
                           "section": section, "title": f"About Rajveer — {section}"})

    wh = data.get("why_hire", {})
    add("Why Rajveer is a strong fit for the AI Engineer role: " +
        " ".join(wh.get("points", [])), "why_hire")
    add("Rajveer's strengths: " + " ".join(data.get("strengths", [])), "strengths")
    add("Rajveer's honest weaknesses / growth areas: " +
        " ".join(data.get("weaknesses", [])), "weaknesses")
    for p in data.get("projects", []):
        body = (f"{p['name']} — {p.get('tagline','')}. "
                f"Stack: {', '.join(p.get('stack', []))}. "
                f"Status: {p.get('status','')}. "
                + " ".join(p.get("highlights", [])))
        add(body, f"project:{p['name']}")
    return chunks


def _strip_markdown_noise(md: str) -> str:
    md = re.sub(r"<img[^>]*>", "", md)              # drop image tags
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)    # drop image markdown
    md = re.sub(r"<[^>]+>", " ", md)                # drop remaining html tags
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md


# ---------- build ----------

def build() -> None:
    print("Loading sources...")
    chunks = (load_resume_chunks() + load_readme_chunks() + load_commit_chunks()
              + load_repo_card_chunks() + load_persona_chunks())
    print(f"  {len(chunks)} chunks from "
          f"{sum(c['source']=='resume' for c in chunks)} resume, "
          f"{sum(c['source']=='github' for c in chunks)} github, "
          f"{sum(c['source']=='personal' for c in chunks)} personal")

    print(f"Embedding with {config.EMBED_MODEL} (local, $0)...")
    model = TextEmbedding(config.EMBED_MODEL)
    vectors = np.array(list(model.embed([c["text"] for c in chunks])), dtype="float32")
    faiss.normalize_L2(vectors)  # cosine similarity via inner product

    index = faiss.IndexFlatIP(config.EMBED_DIM)
    index.add(vectors)

    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(config.INDEX_DIR / "faiss.index"))
    (config.INDEX_DIR / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {index.ntotal} vectors -> {config.INDEX_DIR}")


if __name__ == "__main__":
    build()
