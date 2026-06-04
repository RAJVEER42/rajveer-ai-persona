"""Tool schemas (OpenAI function-calling format) + a single dispatcher.

The same four tools serve both the chat and voice channels — one brain.
"""
from __future__ import annotations
import json

from app.services import knowledge, calendar_client

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_facts",
            "description": ("Get stable, structured facts about Rajveer from his profile. "
                            "Use for skills, education, contact, project list, achievements, "
                            "leadership, why-hire, strengths, weaknesses."),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": knowledge.FACT_CATEGORIES + ["all"],
                        "description": "Which fact category to fetch ('all' for everything).",
                    }
                },
                "required": ["category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": ("Semantic search over Rajveer's resume and GitHub READMEs. "
                            "Use for nuanced questions about how a project works, its tech "
                            "stack, design tradeoffs, or anything needing detail from docs."),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Check Rajveer's real calendar for open meeting slots (returns IST times).",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "YYYY-MM-DD (optional)."},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD (optional)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_meeting",
            "description": ("Book a confirmed meeting on Rajveer's calendar. Only call AFTER the "
                            "user has confirmed their name, email, and chosen time."),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "start_time_utc": {"type": "string",
                                       "description": "ISO-8601 UTC start time from an offered slot."},
                    "notes": {"type": "string"},
                },
                "required": ["name", "email", "start_time_utc"],
            },
        },
    },
]

_DISPATCH = {
    "lookup_facts": lambda a: knowledge.lookup_facts(a.get("category", "all")),
    "search_knowledge": lambda a: knowledge.search_knowledge(a.get("query", "")),
    "get_available_slots": lambda a: calendar_client.get_available_slots(
        a.get("start_date", ""), a.get("end_date", "")),
    "book_meeting": lambda a: calendar_client.book_meeting(
        a.get("name", ""), a.get("email", ""), a.get("start_time_utc", ""), a.get("notes", "")),
}


def execute_tool(name: str, arguments: str | dict) -> dict:
    args = arguments if isinstance(arguments, dict) else json.loads(arguments or "{}")
    fn = _DISPATCH.get(name)
    if not fn:
        return {"error": f"unknown tool '{name}'"}
    try:
        return fn(args)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{name} failed: {e}"}
