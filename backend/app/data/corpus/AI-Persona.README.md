# Scaler Personas — Bauhaus Chat

> **Author:** Rajveer Bishnoi
> **Live demo:** [ai-persona-ten.vercel.app](https://ai-persona-ten.vercel.app)

A multi-persona chatbot where students chat with three Scaler instructor personas — **Anshuman Singh**, **Kshitij Mrigank**, and **Abhimanyu Saxena** — each backed by a different Gemini system prompt, few-shot example set, and reasoning style.

The frontend is built around a strict **Bauhaus design system**: primary red / blue / yellow color blocks, hard offset shadows, thick black borders, and the geometric Outfit typeface.

---

## Personas

| Persona | Voice | Color | Shape |
|---|---|---|---|
| **Anshuman Singh** | Strict + Conceptual — demands precise definitions, ends every reply with a sharp follow-up question | Red `#D02020` | Circle |
| **Kshitij Mrigank** | Interactive + Pattern-Driven — Socratic DSA dialogue, brute force → optimal, hints over answers | Blue `#1040C0` | Square |
| **Abhimanyu Saxena** | Chill + Practical — analogy first (coffee shops, restaurants, APIs as waiters), technical bridge after | Yellow `#F0C020` | Triangle |

Each system prompt contains: persona description, chain-of-thought instruction, output format rules, hard constraints, and 4 few-shot examples. Full annotated prompts are in [`prompts.md`](./prompts.md).

---

## Tech Stack

- **Frontend** — React + Vite, vanilla CSS (Bauhaus design tokens), `lucide-react` icons, Outfit font
- **Backend** — Node.js + Express
- **LLM** — Google Gemini API (`gemini-2.0-flash` by default)

```text
.
├── frontend/         # Vite + React app
├── backend/          # Express API + Gemini integration
├── prompts.md        # All three system prompts, annotated
├── reflection.md     # 300-500 word reflection
└── README.md
```

---

## Setup

### 1. Install dependencies

```bash
npm install --prefix frontend
npm install --prefix backend
```

### 2. Configure backend environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash
PORT=5000
FRONTEND_ORIGIN=http://localhost:5173
```

> The API key is only ever read from the environment — it is never bundled into the frontend or committed to the repo.

### 3. Run both servers

In two terminals:

```bash
# terminal 1
npm run dev --prefix backend
```

```bash
# terminal 2
npm run dev --prefix frontend
```

Open **http://localhost:5173**.

If `GEMINI_API_KEY` is missing, the backend returns a clearly-marked local fallback reply per persona, so the UI keeps working for design review.

---

## Features

- **Persona switcher tabs** are always visible at the top of the screen — clicking a tab swaps the system prompt **and resets the conversation**.
- **Active persona banner** shows the current persona's name, role, and color so it's never ambiguous which voice you're talking to.
- **Suggestion chips** offer 3 quick-start prompts per persona.
- **Typing indicator** with three colored dots animates while Gemini is generating.
- **Reset button** clears the current conversation without changing personas.
- **Hard error UI** — if the backend is unreachable, an inline error bubble explains what's wrong instead of crashing.
- **Mobile responsive** — single-column layout, condensed tabs, and reduced shadows below 720px.

---

## API

### `GET /api/health`
```json
{ "ok": true, "service": "persona-chatbot-backend" }
```

### `GET /api/personas`
```json
[
  { "id": "anshuman", "name": "Anshuman Singh", "title": "Strict + Conceptual" },
  { "id": "kshitij",  "name": "Kshitij Mrigank", "title": "Interactive + Pattern-Driven" },
  { "id": "abhimanyu","name": "Abhimanyu Saxena","title": "Chill + Practical" }
]
```

### `POST /api/chat`
```json
{
  "personaId": "anshuman",
  "message": "What is a stack?",
  "history": [
    { "role": "user", "text": "..." },
    { "role": "assistant", "text": "..." }
  ]
}
```

Returns:
```json
{ "text": "...", "source": "gemini" }
```

`source` is either `"gemini"` (live API call) or `"fallback"` (local stub when key is missing or upstream is throttled).

---

## Deployment (Vercel — single deploy)

This project is deployed to **Vercel** as a single unit:

- Frontend (`/frontend`) — Vite static build
- API (`/api/*.js`) — Vercel serverless functions that wrap `backend/src/{personas,gemini}.js`

### One-shot deploy

```bash
vercel              # first time — link / create the project
vercel --prod       # production deploy
```

### Environment variable (set in Vercel project settings)

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | your Gemini API key |
| `GEMINI_MODEL` | `gemini-2.0-flash` (optional) |

`VITE_API_URL` is **not** required in production — the frontend uses relative paths (`/api/*`) when deployed, since both halves live on the same Vercel domain. It only needs to be set in local dev (and even then, it defaults to `http://localhost:5000`).

### Local Express server (alt path)

The original Express server at `backend/src/server.js` is still functional for local development — `npm run dev --prefix backend` starts it on port 5000. The serverless `api/*.js` handlers re-use the same `personas.js` and `gemini.js` modules, so logic stays in one place.

---

## Testing

A quick smoke test once both servers are running:

```bash
# health
curl http://localhost:5000/api/health

# list personas
curl http://localhost:5000/api/personas

# chat with Kshitij
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"personaId":"kshitij","message":"How do I solve two sum?","history":[]}'

# bad request — should 400
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"personaId":"kshitij"}'
```

---

## What's in the repo

- `prompts.md` — all three system prompts with inline commentary on every design decision
- `reflection.md` — 300–500 word reflection on what worked, the GIGO lesson, and what I'd improve
- `backend/.env.example` — template env file (no real keys)
- `.gitignore` — excludes `node_modules/`, `.env`, build artifacts
