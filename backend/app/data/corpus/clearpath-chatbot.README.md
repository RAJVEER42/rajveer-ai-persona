# ClearPath Support Chatbot

RAG-powered customer support chatbot for ClearPath project management tool. Built from scratch — no LangChain, LlamaIndex, or managed retrieval services.

**🌐 Live Demo:** [https://clearpath-chatbot-928213635181.asia-south1.run.app](https://clearpath-chatbot-928213635181.asia-south1.run.app)
### ❗️NOTE : (due to some problem in my GCP payment, The live link may not work {Thinking of shifting it to DigitalOcean soon...}) 

## How to run locally

```bash
# Clone and setup
git clone https://github.com/RAJVEER42/clearpath-chatbot.git
cd clearpath-chatbot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install CPU-only PyTorch first (avoids multi-GB CUDA downloads)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install backend dependencies
pip install -r backend/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY from https://console.groq.com

# Start backend (first run builds the vector index from 30 PDFs, takes ~30-60s)
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend (development)

```bash
# In a separate terminal
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### Frontend (production)

```bash
cd frontend
npm install
npm run build
# Built files go to frontend/dist/ — FastAPI serves them automatically at http://localhost:8000
```

### Docker

```bash
docker build -t clearpath-chatbot .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key_here clearpath-chatbot
# Open http://localhost:8000
```

## Models used

| Model | Groq model string | Used for |
|-------|-------------------|----------|
| Llama 3.1 8B | `llama-3.1-8b-instant` | Simple queries — greetings, single-fact lookups, yes/no |
| Llama 3.3 70B | `llama-3.3-70b-versatile` | Complex queries — comparisons, complaints, multi-step reasoning |

## Environment config

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | API key from [Groq console](https://console.groq.com) |
| `PORT` | No | `8000` | Backend server port |

## Architecture

Three-layer pipeline:

1. **Hybrid Retrieval Pipeline** — PDFs parsed with PyMuPDF, section-aware chunking (500 tokens, 100 overlap), embedded with `all-MiniLM-L6-v2`, dual retrieval using BM25 keyword search (custom implementation) + FAISS semantic search (cosine similarity via `IndexFlatIP`), results merged via Reciprocal Rank Fusion (RRF), top-k=5 with 0.3 threshold and automatic fallback. Vector index persisted to disk and reloaded on restart.

2. **Model Router** — Deterministic rule-based classifier (6 rules: word count ≥15, complex-intent keywords, multiple question marks, complaint markers, conditional/compound markers, negation patterns). No LLM calls. Both models are actually used. Every decision logged as JSON to stdout.

3. **Output Evaluator** — Three flags: `no_context` (answered without chunks), `refusal` (LLM declined to answer), `conflicting_sources` (chunks from 4+ different documents — domain-specific check). Conversational queries (greetings, small talk) bypass all checks. Flags surface to the user as inline warning banners in the chat UI.

## Routing log format

Every query produces a JSON log line to stdout:

```json
{
  "query": "How do I reset my password?",
  "classification": "simple",
  "model_used": "llama-3.1-8b-instant",
  "tokens_input": 512,
  "tokens_output": 134,
  "latency_ms": 980
}
```

## Eval harness

```bash
# With the backend running:
cd eval
python run_eval.py
# 15/15 passed
```

## Bonus challenges attempted

### ✅ Eval Harness
15 hand-written test queries with expected answers in `eval/test_queries.json`. Covers simple lookups, complex multi-part questions, off-topic rejection (triggers `refusal` flag), complaints, and edge cases. Validates classification, answer content, and evaluator flags. Run with `cd eval && python run_eval.py`.

### ✅ Conversation Memory
Implemented in `backend/services/memory.py`. Uses in-memory dict keyed by `conversation_id`, preserving last 5 turns per session. The `conversation_id` is returned in every API response and sent back by the client on subsequent requests. Design tradeoff: 5 turns keeps token cost low (~500 extra tokens per request) while enabling follow-up questions like "tell me more about that." Known limitation: memory is lost on container restart (see Q4 in Written_answers.md).

### ✅ Live Deploy (GCP Cloud Run — Business-Grade)
Deployed on Google Cloud Platform using Cloud Run + Artifact Registry in `asia-south1` (Mumbai). Multi-stage Docker build (Node.js build stage + Python 3.11 runtime). Public HTTPS URL with auto-scaling 0→3 instances. Qualifies for extra bonus marks as a business-grade cloud provider.

**Live at:** [https://clearpath-chatbot-928213635181.asia-south1.run.app](https://clearpath-chatbot-928213635181.asia-south1.run.app)

## Project structure

```
clearpath-chatbot/
├── README.md
├── Written_answers.md
├── Dockerfile
├── .env.example
├── docs/                        # 30 ClearPath PDF files
├── backend/
│   ├── main.py                  # FastAPI app, startup lifespan
│   ├── config.py                # Centralised settings (pydantic-settings)
│   ├── routers/chat.py          # POST /query endpoint
│   └── services/
│       ├── ingestion.py         # PDF parsing + section-aware chunking
│       ├── embeddings.py        # sentence-transformers wrapper
│       ├── retriever.py         # BM25 + FAISS + RRF hybrid retrieval
│       ├── router.py            # Deterministic 6-rule classifier
│       ├── llm.py               # Groq API calls with retry logic
│       ├── evaluator.py         # 3-flag output evaluator
│       └── memory.py            # In-memory conversation history
├── frontend/
│   └── src/
│       ├── App.tsx              # Root state + API integration
│       ├── components/
│       │   ├── chat-message.tsx # Message bubbles + evaluator banners
│       │   ├── debug-panel.tsx  # Sliding debug drawer
│       │   ├── chat-input.tsx   # Auto-growing textarea + RGB border
│       │   └── empty-state.tsx  # Prompt suggestion cards
│       └── types/index.ts       # Shared TypeScript interfaces
└── eval/
    ├── run_eval.py              # Test runner
    └── test_queries.json        # 15 test cases
```

## Known issues

- **In-memory conversation history** — lost on container restart / Cloud Run cold start. Swap `_conversations` dict in `memory.py` for Redis or Firestore to fix.
- **PDF table extraction is lossy** — tabular data (pricing matrices, keyboard shortcut tables) loses row/column structure during PyMuPDF extraction, causing poor retrieval of table-specific facts.
- **General-purpose embedding model** — `all-MiniLM-L6-v2` is not fine-tuned on ClearPath vocabulary; domain-specific terms may embed suboptimally.
- **Streaming not implemented** — full response delivered at once; no token-by-token streaming.
