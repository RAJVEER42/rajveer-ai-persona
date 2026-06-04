<div align="center">

# DocBlock

<img width="3004" height="1532" alt="image" src="https://github.com/user-attachments/assets/e99ea11a-ec12-4a6c-8194-730315e66f59" />


### A neo-brutalist take on Google NotebookLM — drop a PDF, talk to it.

<br />

<img src="https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=nextdotjs" alt="Next.js" />
<img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=000" alt="React" />
<img src="https://img.shields.io/badge/Tailwind-4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=fff" alt="Tailwind" />
<img src="https://img.shields.io/badge/Qdrant-Vector_DB-DC382C?style=for-the-badge&logo=qdrant&logoColor=fff" alt="Qdrant" />
<img src="https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=for-the-badge&logo=groq&logoColor=fff" alt="Groq" />
<img src="https://img.shields.io/badge/HuggingFace-MiniLM-FFD21E?style=for-the-badge&logo=huggingface&logoColor=000" alt="HF" />
<img src="https://img.shields.io/badge/LangChain-RAG-1C3C3C?style=for-the-badge&logo=langchain&logoColor=fff" alt="LangChain" />

<br /><br />

**Built by [Rajveer Bishnoi](https://github.com/RAJVEER42) · Assignment 03**

[Live Demo](https://your-vercel-deployment.vercel.app/) · [Report Bug](https://github.com/RAJVEER42/notebook-LLM/issues) · [Request Feature](https://github.com/RAJVEER42/notebook-LLM/issues)

</div>

---

## What is this?

DocBlock is a Retrieval-Augmented Generation (RAG) app that turns any document
into a chat partner. You upload a file, it gets chunked, embedded, and indexed
into a private vector collection — then every answer the LLM gives is grounded
in retrieved excerpts from *your* document, with page-level citations.

The UI is deliberately loud: thick black strokes, candy-bright blocks, hard
offset shadows, and mono type. It's designed to look like a sticker pack, not
a chatbot.

> **Why "neo-brutalist"?**
> Most AI products lean glassy and polite. DocBlock leans the other way —
> chunky borders, raw color blocks, sharp shadows. The interface should feel
> as physical as the document you just dropped into it.

---

## Highlights

| | |
|---|---|
| **Bring-your-own document** | Upload any PDF or `.txt` file (≤ 15 MB) |
| **Per-document isolation** | Every upload gets its own Qdrant collection — chats never leak across files |
| **Grounded answers** | The LLM is forced to refuse questions it can't answer from the retrieved context |
| **Page-aware citations** | Each answer expands to show exact chunks with page numbers |
| **Persistent session** | Refresh-safe via `localStorage` |
| **Snappy UI** | 3px strokes, hard shadows, hover-tilt on every interactive surface |

---

## Architecture

```
        ┌─────────────────────────┐
        │   Upload (PDF / TXT)    │
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │   Page-level loader     │  WebPDFLoader / inline text
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │ Recursive chunking      │  size 1100, overlap 180
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │ HuggingFace embeddings  │  all-MiniLM-L6-v2 · 384-d
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │   Qdrant collection     │  docblock_<sessionId>
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │  Question  ─►  top-k=6  │
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │ Groq · Llama 3.3 70B    │  temperature 0.15
        └────────────┬────────────┘
                     ▼
        ┌─────────────────────────┐
        │  Answer + Citations     │
        └─────────────────────────┘
```

---

## Tech stack

<table>
  <tr>
    <td><b>Frontend</b></td>
    <td>Next.js 16 (App Router) · React 19 · Tailwind v4 · custom brutalist CSS</td>
  </tr>
  <tr>
    <td><b>Backend</b></td>
    <td>Next.js Route Handlers (Node runtime)</td>
  </tr>
  <tr>
    <td><b>Vector DB</b></td>
    <td>Qdrant Cloud (free tier)</td>
  </tr>
  <tr>
    <td><b>Embeddings</b></td>
    <td>HuggingFace Inference API · <code>sentence-transformers/all-MiniLM-L6-v2</code></td>
  </tr>
  <tr>
    <td><b>LLM</b></td>
    <td>Groq · <code>llama-3.3-70b-versatile</code></td>
  </tr>
  <tr>
    <td><b>RAG glue</b></td>
    <td>LangChain (<code>community</code>, <code>qdrant</code>, <code>textsplitters</code>)</td>
  </tr>
  <tr>
    <td><b>PDF parsing</b></td>
    <td><code>WebPDFLoader</code> — browser-compatible, serverless-safe</td>
  </tr>
  <tr>
    <td><b>Hosting</b></td>
    <td>Vercel</td>
  </tr>
</table>

---

## Chunking strategy

DocBlock uses LangChain's `RecursiveCharacterTextSplitter` with a deliberately
sentence-aware separator chain.

```js
{
  chunkSize: 1100,
  chunkOverlap: 180,
  separators: ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]
}
```

**The splitter walks down that list in order** — paragraphs first, then line
breaks, then sentence terminators, then clauses, then words, and only falls
back to character splits as a last resort. This keeps natural prose units
intact whenever the chunk size allows.

After splitting, every chunk is:

- **Trimmed** and **dropped if shorter than 24 characters** — those are
  almost always page numbers, footers, or splitter artefacts that hurt
  retrieval recall.
- **Annotated** with `{ source, page, chunkIndex, charCount, wordCount }`.
- **Page-tagged** so citations can point at a real page in the source PDF.

> The 1100/180 ratio (~16% overlap) is the compromise: large enough to keep
> ideas spanning a chunk boundary recoverable, small enough to avoid pulling
> the same content under multiple chunk IDs at retrieval time.

The chunking config is also returned in the `/api/ingest` response under a
`strategy` key, which makes A/B testing different splitters trivial.

---

## RAG pipeline

### 1. Ingestion · `POST /api/ingest`

- Accepts a single file via `multipart/form-data` (field name `file`).
- Validates: ≤ 15 MB, MIME `application/pdf` or `text/plain`.
- PDFs → `WebPDFLoader` with `splitPages: true` so page numbers survive.
- TXT → wrapped as a single `Document` with `page: 1`.
- Documents are chunked, filtered, and embedded.
- A new `sessionId` (10-char nanoid) gets its own collection
  `docblock_<sessionId>` in Qdrant.

<details>
<summary><b>Example response</b></summary>

```json
{
  "sessionId": "abc123",
  "fileName": "paper.pdf",
  "pages": 12,
  "chunks": 42,
  "strategy": {
    "splitter": "recursive-character",
    "chunkSize": 1100,
    "chunkOverlap": 180
  }
}
```

</details>

### 2. Retrieval + generation · `POST /api/chat`

<details>
<summary><b>Request shape</b></summary>

```json
{
  "sessionId": "abc123",
  "question": "What is this paper about?",
  "history": [{ "role": "user", "content": "..." }]
}
```

</details>

The route then:

1. Opens the per-session Qdrant collection.
2. Runs a top-`k = 6` similarity search using the same embedding model used at index time.
3. Formats retrieved excerpts as `[excerpt N | page X | chunk #Y]`.
4. Builds the prompt — strict system prompt + last 6 turns + user question.
5. Calls Groq's `llama-3.3-70b-versatile` at `temperature: 0.15`.
6. Returns the answer plus structured citations (page, chunk index, 240-char snippet).

### 3. Grounding

The system prompt explicitly instructs the model to:

- treat the supplied excerpts as the **only** source of truth;
- reply `"I couldn't find that in the document."` when the excerpts don't cover the question;
- cite pages inline as `(p. N)`;
- never invent facts, numbers, names, or quotes.

Combined with the low temperature, this keeps responses tightly bound to the document.

---

## Project structure

```
app/
├── layout.js              ← fonts + metadata
├── page.js                ← brutalist UI (upload + chat)
├── globals.css            ← design tokens (palette, shadows, animations)
└── api/
    ├── ingest/route.js    ← parse → chunk → embed → index
    └── chat/route.js      ← retrieve → ground → generate

lib/
└── rag.js                 ← embedder + Qdrant helpers

public/                    ← static assets
.env.local                 ← API keys (gitignored)
```

---

## Getting started

### 1. Clone and install

```bash
git clone https://github.com/RAJVEER42/notebook-LLM.git
cd notebook-LLM
npm install --legacy-peer-deps
```

### 2. Configure environment

Create `.env.local` at the project root:

```env
GROQ_API_KEY=your_groq_key
HUGGINGFACE_API_KEY=your_hf_inference_key
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
```

| Service | Where to get it |
|---|---|
| Groq API key | https://console.groq.com/keys |
| HuggingFace token | https://huggingface.co/settings/tokens (needs Inference API access) |
| Qdrant cluster | https://cloud.qdrant.io/ (free tier works) |

### 3. Run

```bash
npm run dev
```

Open <http://localhost:3000> and drop a PDF.

---

## Deployment

DocBlock is built for one-click Vercel deploys.

1. Push this repo to GitHub.
2. Import it into Vercel (auto-detects Next.js).
3. Add the four env vars above in **Settings → Environment Variables**.
4. Deploy.

> **Serverless notes**
> `/api/ingest` runs with `maxDuration: 60`, `/api/chat` with `maxDuration: 300`,
> both on the Node runtime. PDF parsing uses `WebPDFLoader` so there are no
> native dependencies — it just works inside Vercel's serverless environment.

---

## Design system

The brutalist look is enforced via a small set of CSS tokens:

| Token | Value | Used for |
|---|---|---|
| Stroke | `3px solid #000` | Every interactive surface |
| Shadow | `6px 6px 0 0 #000` | Resting elevation |
| Shadow (lift) | `10px 10px 0 0 #000` | Hover state |
| Pink | `#ff5da2` | Primary actions, accents |
| Yellow | `#ffd23f` | Header, active blocks |
| Blue | `#4d80ff` | User messages, CTAs |
| Green | `#36d399` | Success, "live" indicators |
| Lilac | `#c084fc` | Tertiary accents |
| Paper | `#fff8e7` | Background |
| Display font | Space Grotesk | Headings, body |
| Mono font | JetBrains Mono | Inputs, labels, tags |

**Interaction rules:**

- Hover → `translate(-2px, -2px)` + thicker shadow + slight tilt
- Active → `translate(2px, 2px)` + tight shadow (the block "sinks in")
- All transitions in 140–160 ms for a snappy, physical feel

---

## Roadmap

- [ ] Multi-document chat (query across several uploaded files)
- [ ] Streaming responses (token-by-token)
- [ ] Highlight the cited region inside an inline PDF preview
- [ ] Export chat as Markdown / PDF
- [ ] Hybrid retrieval (BM25 + dense) for keyword-heavy docs
- [ ] Re-ranking with a cross-encoder

---

## License & credits

Built as a learning project — feel free to fork, remix, and ship your own version.

<div align="center">

<br />

**Made by [Rajveer Bishnoi](https://github.com/RAJVEER42)**

<sub>GenAI course · Assignment 03 · 2026</sub>

</div>
