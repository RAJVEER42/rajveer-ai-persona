"""POST /chat — Server-Sent Events streaming chat endpoint.

SSE protocol:
  event: token   data: <text chunk>
  event: sources data: <json list>
  event: cached  data: {"similarity": ...}   (only on cache hit)
  event: done    data: ""
"""
from __future__ import annotations
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core import agent
from app.services import cache

router = APIRouter()


class Msg(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Msg]


def _sse(event: str, data) -> str:
    # Always JSON-encode so newlines in the payload are escaped (\n) and never
    # collide with the SSE event delimiter (\n\n). Critical for multi-line answers
    # sent in one field (cache hits) and for tokens that contain blank lines.
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    messages = [m.model_dump() for m in req.messages]
    last_user = next((m["content"] for m in reversed(messages)
                      if m["role"] == "user"), "")

    def gen():
        # 1) semantic cache
        hit = cache.get(last_user)
        if hit:
            yield _sse("cached", {"similarity": hit["similarity"]})
            yield _sse("token", hit["answer"])
            yield _sse("sources", hit["sources"])
            yield _sse("done", "")
            return

        # 2) full agent loop, streamed
        collected, sources, errored = [], [], False
        for kind, payload in agent.stream(messages):
            if kind == "token":
                collected.append(payload)
                yield _sse("token", payload)
            elif kind == "error":
                errored = True
            elif kind == "sources":
                sources = payload
                yield _sse("sources", payload)
            elif kind == "done":
                yield _sse("done", "")
        # only cache complete, non-trivial answers (never partial/failed ones)
        answer = "".join(collected).strip()
        if not errored and len(answer) >= 40:
            cache.put(last_user, answer, sources)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})
