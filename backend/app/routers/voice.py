"""OpenAI-compatible endpoint so Vapi can use our backend as a *custom LLM*.

Vapi handles the hard real-time parts (Deepgram STT, TTS, turn-taking, barge-in)
and calls POST /v1/chat/completions for each turn. We ignore Vapi's system
message, run OUR agent (same RAG + tools as chat, voice tone on), and stream
the answer back in OpenAI chunk format. This keeps a single brain across chat
and voice — the tools execute server-side, invisible to Vapi.
"""
from __future__ import annotations
import json
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from app import config
from app.core import agent

router = APIRouter()


class OAIMessage(BaseModel):
    role: str
    content: str | None = None


class OAIRequest(BaseModel):
    model: str | None = None
    messages: list[OAIMessage] = []
    stream: bool = True
    temperature: float | None = None


def _chunk(text: str | None, finish: str | None = None) -> str:
    delta = {} if text is None else {"content": text}
    payload = {
        "id": "chatcmpl-persona",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": config.LLM_MODEL,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/v1/chat/completions")
def vapi_completions(req: OAIRequest):
    # Use only the conversational turns; our own system prompt is injected by the agent.
    convo = [{"role": m.role, "content": m.content or ""}
             for m in req.messages if m.role in ("user", "assistant") and m.content]

    if req.stream:
        def gen():
            yield _chunk("")  # open the stream
            for kind, payload in agent.stream(convo, voice=True):
                if kind == "token" and payload:
                    yield _chunk(payload)
            yield _chunk(None, finish="stop")
            yield "data: [DONE]\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache",
                                          "X-Accel-Buffering": "no"})

    # non-streaming fallback
    result = agent.run(convo, voice=True)
    return JSONResponse({
        "id": "chatcmpl-persona",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": config.LLM_MODEL,
        "choices": [{"index": 0, "message": {"role": "assistant",
                     "content": result["answer"]}, "finish_reason": "stop"}],
    })


@router.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": config.LLM_MODEL,
            "object": "model", "owned_by": "rajveer-persona"}]}
