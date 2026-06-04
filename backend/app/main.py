"""FastAPI app — the single backend serving both chat and (later) voice."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.core.prompts import PROMPT_VERSION
from app.routers import chat, voice
from app.services import cache

WEB_DIR = config.BASE_DIR / "web"  # static-exported Next.js chat UI

app = FastAPI(title="Rajveer Bishnoi — AI Persona", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if config.FRONTEND_URL == "*" else [config.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def no_cache_html(request, call_next):
    """Never let browsers cache HTML — so a new deploy's hashed JS is always picked
    up. (Hashed static chunks can still cache; only the HTML must revalidate.)"""
    resp = await call_next(request)
    ctype = resp.headers.get("content-type", "")
    if ctype.startswith("text/html"):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


app.include_router(chat.router)
app.include_router(voice.router)  # OpenAI-compatible endpoint for Vapi custom LLM


@app.get("/health")
def health():
    return {"status": "ok", "model": config.LLM_MODEL,
            "prompt_version": PROMPT_VERSION, "cache": cache.stats()}


@app.get("/cache/stats")
def cache_stats():
    return cache.stats()


@app.get("/resume")
def resume():
    pdf = config.DATA_DIR / "resume.pdf"
    if pdf.exists():
        return FileResponse(pdf, media_type="application/pdf",
                            filename="Rajveer_Bishnoi_Resume.pdf")
    return FileResponse(config.RESUME_MD, media_type="text/markdown")


# Serve the static chat UI at "/" (mounted LAST so API routes win).
# POST /chat etc. are unaffected — StaticFiles only handles GET of real files.
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
