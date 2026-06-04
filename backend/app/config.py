"""Central settings, loaded from environment variables.

Everything the persona needs is configurable here so the same code runs
locally and on HF Spaces. Only HF_TOKEN is strictly required for the brain;
retrieval is fully local and free.
"""
from __future__ import annotations
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()  # load backend/.env if present
except Exception:  # noqa: BLE001
    pass

# --- paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CORPUS_DIR = DATA_DIR / "corpus"
INDEX_DIR = DATA_DIR / "index"
RESUME_MD = DATA_DIR / "resume.md"
PERSONA_YAML = DATA_DIR / "persona.yaml"
REPOS_JSON = CORPUS_DIR / "github_repos.json"

# --- retrieval (100% local, $0) ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")  # 384-dim, ONNX via fastembed
EMBED_DIM = 384
TOP_K = int(os.getenv("TOP_K", "5"))

# --- LLM brain: HuggingFace Inference Providers router (OpenAI-compatible) ---
# Same pattern Rajveer used in agent-cli-scaler.
HF_TOKEN = os.getenv("HF_TOKEN", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://router.huggingface.co/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")  # reliable tool-calling on HF router
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "700"))

# --- calendar (Cal.com, free tier) ---
CALCOM_API_KEY = os.getenv("CALCOM_API_KEY", "")
CALCOM_EVENT_TYPE_ID = os.getenv("CALCOM_EVENT_TYPE_ID", "")
CALCOM_BASE_URL = os.getenv("CALCOM_BASE_URL", "https://api.cal.com/v2")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")  # IST

# --- semantic cache ---
CACHE_THRESHOLD = float(os.getenv("CACHE_THRESHOLD", "0.92"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
CACHE_MAX_ENTRIES = int(os.getenv("CACHE_MAX_ENTRIES", "200"))

# --- server / CORS ---
FRONTEND_URL = os.getenv("FRONTEND_URL", "*")
