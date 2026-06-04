"""Cal.com v2 client — real availability + real booking.

Two tools the agent calls:
  get_available_slots(start_date, end_date) -> open slots in IST
  book_meeting(name, email, start_time_utc)  -> confirmed booking

Both fail gracefully with a clear message if CALCOM_API_KEY isn't set yet, so
the rest of the system runs before the calendar is wired.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

import httpx

from app import config

IST = timezone(timedelta(hours=5, minutes=30))


def _headers(api_version: str) -> dict:
    return {
        "Authorization": f"Bearer {config.CALCOM_API_KEY}",
        "cal-api-version": api_version,
        "Content-Type": "application/json",
    }


def _configured() -> bool:
    return bool(config.CALCOM_API_KEY and config.CALCOM_EVENT_TYPE_ID)


def get_available_slots(start_date: str = "", end_date: str = "") -> dict:
    """Open slots between two YYYY-MM-DD dates (defaults: next 5 days)."""
    if not _configured():
        return {"error": "Calendar not configured yet.", "slots": []}
    today = datetime.now(IST).date()
    start = start_date or today.isoformat()
    end = end_date or (today + timedelta(days=5)).isoformat()
    try:
        r = httpx.get(
            f"{config.CALCOM_BASE_URL}/slots",
            headers=_headers("2024-09-04"),
            params={
                "eventTypeId": config.CALCOM_EVENT_TYPE_ID,
                "start": start,
                "end": end,
                "timeZone": config.TIMEZONE,
            },
            timeout=10,
        )
        r.raise_for_status()
        payload = r.json().get("data", {})
    except Exception as e:  # noqa: BLE001
        return {"error": f"Could not fetch slots: {e}", "slots": []}

    slots: list[dict] = []
    # Cal.com returns { "YYYY-MM-DD": [{"start": "...Z"}, ...] }
    for day, items in (payload.items() if isinstance(payload, dict) else []):
        for it in items:
            iso = it.get("start") if isinstance(it, dict) else it
            try:
                dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            except Exception:  # noqa: BLE001
                continue
            ist = dt.astimezone(IST)
            slots.append({
                "start_utc": dt.astimezone(timezone.utc).isoformat(),
                "display_ist": ist.strftime("%a %d %b, %I:%M %p IST"),
            })
    slots.sort(key=lambda s: s["start_utc"])
    return {"slots": slots[:12], "count": len(slots), "timezone": "IST"}


def book_meeting(name: str, email: str, start_time_utc: str,
                 notes: str = "") -> dict:
    """Create a confirmed booking. start_time_utc must be ISO-8601 UTC."""
    if not _configured():
        return {"error": "Calendar not configured yet.", "booked": False}
    if not (name and email and start_time_utc):
        return {"error": "Need name, email, and a chosen time.", "booked": False}
    try:
        r = httpx.post(
            f"{config.CALCOM_BASE_URL}/bookings",
            headers=_headers("2024-08-13"),
            json={
                "start": start_time_utc,
                "eventTypeId": int(config.CALCOM_EVENT_TYPE_ID),
                "attendee": {"name": name, "email": email,
                             "timeZone": config.TIMEZONE},
                "metadata": {"booked_via": "ai-persona", "notes": notes[:400]},
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json().get("data", {})
    except Exception as e:  # noqa: BLE001
        return {"error": f"Booking failed: {e}", "booked": False}

    return {
        "booked": True,
        "confirmation": data.get("uid") or data.get("id"),
        "meeting_url": data.get("meetingUrl") or data.get("location"),
        "when_ist": _to_ist(start_time_utc),
        "attendee": email,
    }


def _to_ist(iso_utc: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return dt.astimezone(IST).strftime("%a %d %b, %I:%M %p IST")
    except Exception:  # noqa: BLE001
        return iso_utc
