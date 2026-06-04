"""The agent loop — runs on the HF Inference Providers router (OpenAI-compatible).

A hand-rolled loop (no LangChain): call the LLM with the 4 tools, execute any
tool calls, feed results back, repeat until the model answers. ~1-2 iterations
for almost every query. Streams the final answer token-by-token so both the
chat SSE endpoint and Vapi's custom-LLM streaming stay low-latency.

Yields tuples: ("token", str) | ("sources", list) | ("done", None)
"""
from __future__ import annotations
import json
import time
from typing import Iterator

from openai import OpenAI, APIError, RateLimitError, APITimeoutError

from app import config
from app.core import tools as toolmod
from app.core.prompts import SYSTEM_PROMPT, VOICE_ADDENDUM

MAX_ITERS = 5
RETRIES = 3            # the HF router occasionally returns 429 "queue_exceeded"
BACKOFF = (0.6, 1.5, 3.0)

import re

# gpt-oss emits typographic Unicode (em/en dashes, narrow/no-break spaces) that
# render badly in chat and TTS. Normalize each streamed chunk to clean text.
_DASH = re.compile(r'\s*[\u2014\u2013]\s*')          # em/en dash -> ', '
_BAD_SPACES = ['\u202f', '\u00a0', '\u2009', '\u200b']  # narrow/nbsp/thin/zero-width


def _normalize(text: str) -> str:
    for ch in _BAD_SPACES:
        text = text.replace(ch, ' ' if ch != '\u200b' else '')
    text = text.replace('‑', '-').replace('‐', '-')  # non-breaking / unicode hyphen
    text = _DASH.sub(', ', text)
    return text.replace(' -- ', ', ').replace('--', ', ')


def _create_stream(client: OpenAI, convo: list[dict]):
    """Open a streamed completion, retrying transient router errors."""
    last = None
    for attempt in range(RETRIES):
        try:
            return client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=convo,
                tools=toolmod.TOOLS,
                tool_choice="auto",
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS,
                stream=True,
            )
        except (RateLimitError, APITimeoutError, APIError) as e:  # transient
            last = e
            if attempt < RETRIES - 1:
                time.sleep(BACKOFF[attempt])
    raise last

_client: OpenAI | None = None


def _client_singleton() -> OpenAI:
    global _client
    if _client is None:
        if not config.HF_TOKEN:
            raise RuntimeError("HF_TOKEN not set — the brain needs it.")
        _client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.HF_TOKEN)
    return _client


def _system(voice: bool) -> dict:
    content = SYSTEM_PROMPT + (VOICE_ADDENDUM if voice else "")
    return {"role": "system", "content": content}


def stream(messages: list[dict], voice: bool = False) -> Iterator[tuple[str, object]]:
    """messages = prior conversation [{role, content}, ...] ending with the user turn."""
    client = _client_singleton()
    convo: list[dict] = [_system(voice), *messages]
    sources: list[dict] = []

    for _ in range(MAX_ITERS):
        try:
            resp = _create_stream(client, convo)
        except Exception:  # noqa: BLE001 — router unavailable after retries
            yield ("token", "Sorry, I'm having a brief connection issue on my "
                            "end. Could you ask that again in a moment?")
            yield ("error", True)  # signal: do NOT cache this partial/failed answer
            yield ("sources", _dedup_sources(sources))
            yield ("done", None)
            return

        content_parts: list[str] = []
        tool_calls: dict[int, dict] = {}  # index -> {id, name, args}

        for chunk in resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                clean = _normalize(delta.content)
                content_parts.append(clean)
                yield ("token", clean)
            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    slot = tool_calls.setdefault(
                        tc.index, {"id": "", "name": "", "args": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["args"] += tc.function.arguments

        if not tool_calls:
            break  # the streamed content was the final answer

        # record the assistant's tool-call turn, then execute each tool
        convo.append({
            "role": "assistant",
            "content": "".join(content_parts) or None,
            "tool_calls": [
                {"id": t["id"], "type": "function",
                 "function": {"name": t["name"], "arguments": t["args"] or "{}"}}
                for t in tool_calls.values()
            ],
        })
        for t in tool_calls.values():
            result = toolmod.execute_tool(t["name"], t["args"])
            if t["name"] == "search_knowledge":
                for r in result.get("results", [])[:3]:
                    sources.append({k: r.get(k) for k in ("title", "source", "repo", "score")})
            convo.append({
                "role": "tool",
                "tool_call_id": t["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })

    yield ("sources", _dedup_sources(sources))
    yield ("done", None)


def run(messages: list[dict], voice: bool = False) -> dict:
    """Non-streaming convenience wrapper (used by tests + evals)."""
    answer, sources = [], []
    for kind, payload in stream(messages, voice):
        if kind == "token":
            answer.append(payload)
        elif kind == "sources":
            sources = payload
    return {"answer": "".join(answer).strip(), "sources": sources}


def _dedup_sources(sources: list[dict]) -> list[dict]:
    seen, out = set(), []
    for s in sources:
        key = (s.get("title"), s.get("repo"))
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out
