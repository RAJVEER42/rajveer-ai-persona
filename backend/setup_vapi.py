"""Create/update the Vapi voice assistant + provision a phone number.

The assistant uses OUR backend as a custom LLM (so voice runs the same
RAG+tools brain as chat), Deepgram for STT, and a Vapi-bundled voice for TTS.
Barge-in + smart endpointing are tuned for the <2s, interruption-safe target.

Usage:
    VAPI_API_KEY=... SERVER_URL=https://...hf.space python setup_vapi.py
    (both can also live in backend/.env)
"""
from __future__ import annotations
import os
import re
import sys
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
VAPI = "https://api.vapi.ai"


def _env(key: str, default: str = "") -> str:
    env = (HERE / ".env").read_text() if (HERE / ".env").exists() else ""
    m = re.search(rf'^{key}=(\S+)', env, re.M)
    return (m.group(1) if m else os.getenv(key, default))


def main() -> None:
    key = _env("VAPI_API_KEY")
    server = _env("SERVER_URL", "https://itachi-42-rajveer-ai-representative.hf.space")
    if not key:
        sys.exit("Set VAPI_API_KEY in env or backend/.env (Vapi dashboard -> API Keys -> Private).")
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    assistant = {
        "name": "Rajveer Bishnoi - AI Representative",
        "firstMessage": "Hey! This is Rajveer's AI representative. I can tell you about his "
                        "background and projects, or set up a call with him. What would you like to know?",
        "firstMessageMode": "assistant-speaks-first",
        "model": {
            "provider": "custom-llm",
            "url": f"{server}/v1",          # Vapi POSTs to {url}/chat/completions
            "model": "openai/gpt-oss-120b",
            "messages": [{"role": "system", "content": "Follow the persona server instructions."}],
        },
        "transcriber": {"provider": "deepgram", "model": "nova-3", "language": "en"},
        "voice": {"provider": "vapi", "voiceId": "Elliot"},
        "silenceTimeoutSeconds": 20,
        "maxDurationSeconds": 600,
        "backgroundDenoisingEnabled": True,
        # barge-in: stop talking fast when the caller interrupts
        "stopSpeakingPlan": {"numWords": 2, "voiceSeconds": 0.3, "backoffSeconds": 1.0},
        # smart endpointing: detect when the caller has actually finished
        "startSpeakingPlan": {"waitSeconds": 0.4, "smartEndpointingEnabled": True},
    }

    # create or update
    existing = httpx.get(f"{VAPI}/assistant", headers=h, timeout=20).json()
    found = next((a for a in existing if a.get("name") == assistant["name"]), None) \
        if isinstance(existing, list) else None
    if found:
        r = httpx.patch(f"{VAPI}/assistant/{found['id']}", headers=h, json=assistant, timeout=20)
        aid = found["id"]
        print(f"Updated assistant {aid} ({r.status_code})")
    else:
        r = httpx.post(f"{VAPI}/assistant", headers=h, json=assistant, timeout=20)
        r.raise_for_status()
        aid = r.json()["id"]
        print(f"Created assistant {aid}")

    # provision a free Vapi phone number bound to the assistant
    nums = httpx.get(f"{VAPI}/phone-number", headers=h, timeout=20).json()
    if isinstance(nums, list) and nums:
        num = nums[0]
        httpx.patch(f"{VAPI}/phone-number/{num['id']}", headers=h,
                    json={"assistantId": aid}, timeout=20)
        print(f"Bound existing number: {num.get('number')}")
    else:
        r = httpx.post(f"{VAPI}/phone-number", headers=h,
                       json={"provider": "vapi", "assistantId": aid,
                             "name": "Rajveer AI line"}, timeout=30)
        if r.status_code < 300:
            print(f"Provisioned number: {r.json().get('number')}")
        else:
            print(f"Could not auto-provision a number ({r.status_code}): {r.text[:200]}\n"
                  f"-> Create one in the Vapi dashboard (Phone Numbers) and attach assistant {aid}.")


if __name__ == "__main__":
    main()
