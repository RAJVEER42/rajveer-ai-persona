"""Voice eval harness — turns your real Vapi calls into report metrics.

Make a few test calls first (browser 🎙 Talk or the phone number): do one Q&A
with an interruption, and one full book-by-voice. Then run:

    python -m evals.voice_evals

It fetches recent calls from the Vapi API and reports first-response latency,
call durations, cost, and a booking-success heuristic — the numbers Part C
("voice quality") asks for. Reads VAPI_API_KEY from backend/.env.
"""
from __future__ import annotations
import re
import statistics as st
from datetime import datetime, timezone
from pathlib import Path

import httpx

ENV = (Path(__file__).resolve().parents[1] / ".env").read_text()
KEY = re.search(r"^VAPI_API_KEY=(\S+)", ENV, re.M).group(1)
BOOK_WORDS = ("booked", "confirmed", "scheduled", "calendar invite", "you're all set",
              "see you", "meeting is set", "booking")


def _iso(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def _response_latencies(messages: list[dict]) -> list[float]:
    """Seconds between a user turn ending and the next bot turn starting."""
    lat = []
    for i, m in enumerate(messages):
        if m.get("role") != "user":
            continue
        u_end = m.get("secondsFromStart")
        if u_end is not None:
            u_end += (m.get("duration") or 0) / 1000 if (m.get("duration") or 0) > 50 else (m.get("duration") or 0)
        for n in messages[i + 1:]:
            if n.get("role") in ("bot", "assistant"):
                b_start = n.get("secondsFromStart")
                if u_end is not None and b_start is not None and b_start >= u_end:
                    lat.append(round(b_start - u_end, 2))
                break
    return [x for x in lat if 0 <= x < 30]


def main() -> None:
    r = httpx.get("https://api.vapi.ai/call", headers={"Authorization": f"Bearer {KEY}"},
                  params={"limit": 50}, timeout=25)
    r.raise_for_status()
    data = r.json()
    calls = data if isinstance(data, list) else data.get("results", data.get("data", []))
    if not calls:
        print("No calls found. Make a few test calls (🎙 Talk or the phone number) first.")
        return

    rows, all_lat, durations, costs, booked = [], [], [], [], 0
    for c in calls:
        started, ended = _iso(c.get("startedAt", "")), _iso(c.get("endedAt", ""))
        dur = round((ended - started).total_seconds(), 1) if started and ended else None
        msgs = c.get("messages", []) or []
        transcript = (c.get("transcript") or "").lower()
        lat = _response_latencies(msgs)
        first_lat = lat[0] if lat else None
        is_booked = any(w in transcript for w in BOOK_WORDS)
        if is_booked:
            booked += 1
        if dur:
            durations.append(dur)
        if c.get("cost"):
            costs.append(c["cost"])
        all_lat += lat
        rows.append((c.get("type"), c.get("status"), dur, first_lat,
                     "BOOKED" if is_booked else "", len(msgs)))

    print(f"=== Voice eval over {len(calls)} calls ===\n")
    print(f"{'type':9} {'status':10} {'dur(s)':7} {'1st-resp(s)':12} {'booked':7} msgs")
    for t, sstat, dur, fl, bk, nm in rows:
        print(f"{(t or '?'):9} {(sstat or '?'):10} {str(dur or '-'):7} {str(fl or '-'):12} {bk:7} {nm}")

    print("\n--- aggregate (paste-ready for the report) ---")
    if all_lat:
        srt = sorted(all_lat)
        p95 = srt[min(len(srt) - 1, int(len(srt) * 0.95))]
        print(f"first-response latency: median {st.median(all_lat):.2f}s · p95 {p95:.2f}s "
              f"· n={len(all_lat)} turns")
    else:
        print("first-response latency: no per-message timing available "
              "(Vapi `messages[].secondsFromStart` missing) — read it from the call timeline in the dashboard")
    if durations:
        print(f"avg call duration: {st.mean(durations):.0f}s")
    print(f"booking success: {booked}/{len(calls)} calls reached a booking confirmation")
    if costs:
        print(f"cost: ${sum(costs):.3f} total · ${st.mean(costs):.3f}/call avg")


if __name__ == "__main__":
    main()
