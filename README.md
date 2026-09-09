# aeon

`aeon` is a Telegram bot + Mini App with three AI mentors — Marcus Aurelius, Machiavelli, and Carl Jung — each a distinct philosophical personality you can talk to. A dark premium interface wraps the mentors together with a Memento Mori diary, life goals with daily reminders, and a personal cabinet.

## Architecture

One backend service with two "frontends" — the Telegram bot and the Mini App — sharing the same services and database:

```
Mini App (React SPA)          Telegram
      │                           │
      ▼ /api/* (initData auth)    ▼ /tg/webhook (or polling)
┌──────────────────────────────────────────┐
│  Backend: FastAPI + python-telegram-bot  │
│  ├─ api/          Mini App REST routes   │
│  ├─ bot/          handlers, onboarding,  │
│  │                agent chat, reminders  │
│  ├─ services/     shared business logic  │
│  ├─ clients/      Gemini API client      │
│  └─ db/           SQLAlchemy models      │
└──────────┬───────────────────────────────┘
        PostgreSQL
   (single source of truth, incl. dialogue history)
```

PostgreSQL is the single source of truth: profiles, goals, and diary entries created in the Mini App are the same rows the bot reads for reminders and agent context.

## Stack

**Backend** (`backend/`)
- Python 3.12, [uv](https://docs.astral.sh/uv/) for dependency management
- FastAPI + Uvicorn — Mini App REST API, Telegram webhook endpoint, static frontend serving
- python-telegram-bot v21 — onboarding `ConversationHandler`, agent chat, and scheduled daily/weekly notifications
- SQLAlchemy 2.0 (async, asyncpg) + Alembic migrations
- Gemini API (httpx, streaming SSE) — agent answers

**Frontend** (`frontend/`)
- React 19 + TypeScript + Vite
- Tailwind CSS v4 (on top of the ported custom design system in `src/styles.css`)
- TanStack Query — server state (profile, goal, diary)
- React Hook Form + Zod — profile "About" form validation
- Telegram Mini App SDK via `telegram-web-app.js`

## Features

- **Three AI agents** — Marcus Aurelius (stoic mentor), Machiavelli (business tactician), Carl Jung (shadow analyst). Selected in the Mini App or via `/agents`; dialogue happens in the bot chat with streamed answers edited into a single message.
- **Agent book RAG** — paid and trial users receive answers grounded in local excerpts from Marcus Aurelius's *Meditations*, Machiavelli's *The Prince* and *Discourses on Livy*, or Jung's *Man and His Symbols*, with section and page source notes. Basic users keep the prompt-only agents.
- **Onboarding in the bot** — `/start` flow (language → name → staged birth date picker → country) editing one Telegram message, saved straight to PostgreSQL.
- **Memento Mori calendar** — 90 years as 4,680 life weeks, computed from the birth date in the profile.
- **Diary** — reflection notes with quick prompts, stored server-side.
- **Goals** — one active goal connected to localized daily agent notifications (`JobQueue`, configurable hour and timezone).
- **Daily agent notifications** — five ru/en messages per agent, daily rotation, active-goal context, and a direct Mini App action.
- **Weekly life review** — a localized message from one of three rotating agents, the user's life-week number, and a button that opens the calendar.
- **Personal cabinet** — profile memory card, completion progress, plan/tokens.
- **Mini App auth** — every API request is authenticated with Telegram `initData` (HMAC validation) via the `Authorization: tma <initData>` header.
- **Admin panel** — `/admin` (Telegram login; access is a role matrix in the database — `owner` / `support` / `marketing` or custom roles, granted from the panel or with `scripts/grant_admin.py`) shows metrics, users, conversations and payments, manages audience segments and manual broadcasts (dynamic filters or pinned id lists, per-language texts, scheduling, a per-recipient delivery log and a marketing opt-out for users), and lets the product owner edit bot settings without a deploy: per-agent system prompts, the shared response-style block, temperature, history depth and max output tokens are stored as overrides in `bot_settings` (code keeps the defaults; the running bot picks changes up within a minute), and a preview runs a draft prompt against Gemini outside billing.
- **Bilingual (ru/en)** — the Mini App UI, bot messages, and LLM error messages are fully localized; agents reply in the user's language (English prompts + a per-request language directive). Language is detected from Telegram/onboarding and switchable in the profile. Backend catalog in `backend/app/i18n.py`, frontend catalog in `frontend/src/lib/i18n.ts`.

## API

FastAPI serves OpenAPI docs at `/docs`. Main endpoints:

| Endpoint | Description |
| --- | --- |
| `GET /api/me` / `PATCH /api/me` | profile read/update |
| `GET /api/goal` / `POST /api/goal` / `POST /api/goal/close` | active goal |
| `GET /api/diary` / `POST /api/diary` / `DELETE /api/diary/{id}` | diary entries |
| `GET /api/agents` / `POST /api/agents/{id}/dialog` | agents, start bot dialogue |
| `POST /tg/webhook` | Telegram webhook (`BOT_MODE=webhook`) |

Frontend types in `src/lib/types.ts` mirror the backend schemas; regenerate with `pnpm generate:api` (requires the backend running on port 8000).

## Local development

Requirements: Python 3.12+, uv, Node 22+, pnpm, Docker or Podman for PostgreSQL.

1. Start databases:

```bash
docker compose up -d postgres
```

2. Backend (port 8000):

```bash
cd backend
cp ../.env.example .env   # fill in BOT_TOKEN, GEMINI_API_KEY
# for local dev use: DATABASE_URL=postgresql+asyncpg://aeon:aeon@localhost:5432/aeon
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

3. Frontend (port 5173, proxies `/api` and `/tg` to the backend):

```bash
cd frontend
pnpm install
pnpm dev
```

Routing (TanStack Router, `src/router.tsx`): `/` home, `/calendar?tab=life|goal|diary`, `/profile?sheet=about|language|pro`, `/landing` marketing page. Every route renders in a plain browser too (outside Telegram the API answers 401 and the views show empty states), so Mini App screens can be developed at `http://localhost:5173/calendar` and the landing at `/landing`.

Deep links: bot `web_app` buttons link straight to a path (`backend/app/bot/webapp.py`). `https://t.me/<bot>/<app>?startapp=<key>` links cannot carry a path, so `start_param` keys (`calendar`, `calendar_goal`, `calendar_diary`, `calendar_life`, `profile`, `profile_about`, `profile_pro`) are mapped to routes in `src/lib/deeplinks.ts`; legacy `?view=calendar` links from older bot messages are mapped there too. `frontend/vercel.json` rewrites every non-API path to `index.html`.

4. Telegram testing — expose the frontend over HTTPS and point the bot at it:

```bash
ngrok http 5173
# put the https URL into backend .env as MINI_APP_URL, restart the backend
```

With `BOT_MODE=polling` (default) no public URL is needed for the bot itself — only for the Mini App button.

### Agent book RAG

Retrieval is hybrid: Gemini embeddings (`gemini-embedding-001`, 768 dimensions, cosine) and BM25 over the same chunks, fused with reciprocal rank fusion. Chunk texts and vectors live in the `rag_chunks` Postgres table (no pgvector; a few thousand rows per corpus are scanned in memory with numpy), so production needs no files on disk. See `RAG.md` for the design.

Build the ignored local JSON corpus from a text-based PDF, then inspect retrieval without calling the language model:

```bash
cd backend
# one PDF with several works: repeat --work "Title:first_page:last_page"
uv run python scripts/ingest_rag_pdf.py "/path/to/Machiavelli.pdf" \
  --work "Никколо Макиавелли, «Государь»:6:82" \
  --work "Никколо Макиавелли, «Рассуждения о первой декаде Тита Ливия»:83:356"
uv run python -m scripts.query_rag "Когда правителю быть львом, а когда лисой?" --top-k 3

uv run python scripts/build_machiavelli_discourses_en_rag.py "/path/to/Discourses-1883.pdf"
uv run python -m scripts.query_rag "Why can class conflict preserve liberty?" --agent machiavelli --language en --top-k 3
uv run python -m scripts.evaluate_rag evals/machiavelli_discourses_en_golden.json

uv run python scripts/build_aurelius_rag.py "/path/to/Meditations-1985.pdf"
uv run python -m scripts.query_rag "Как не обижаться на грубых людей?" --agent aurelius --top-k 3
uv run python -m scripts.evaluate_rag evals/aurelius_ru_golden.json

uv run python scripts/build_aurelius_en_rag.py "/path/to/Marcus-Aurelius-Meditations.pdf"
uv run python -m scripts.query_rag "How can I stop taking insults personally?" --agent aurelius --language en --top-k 3
uv run python -m scripts.evaluate_rag evals/aurelius_en_golden.json

uv run python scripts/build_jung_rag.py "/path/to/Man-and-His-Symbols-2016.pdf"
uv run python -m scripts.query_rag "Что такое Тень и почему мы её проецируем?" --agent jung --top-k 3
uv run python -m scripts.evaluate_rag evals/jung_ru_golden.json

uv run python scripts/build_jung_en_rag.py "/path/to/Man-And-His-Symbols.pdf"
uv run python -m scripts.query_rag "What is the shadow, and why do we project it?" --agent jung --language en --top-k 3
uv run python -m scripts.evaluate_rag evals/jung_en_golden.json
```

Generated corpora live at `backend/data/rag/<agent>.json`; localized English corpora use `backend/data/rag/<agent>.en.json`. They are intentionally not committed. The Aurelius builders index only the twelve books of their respective Russian and English editions. The Jung builder indexes the six authored sections of the 2016 Russian edition and keeps each contributor in the section metadata. `RAG_ALLOW_BASIC=true` bypasses plan gating for local testing only; leave it `false` outside development.

**Publishing the corpus to a database.** The JSON files are only an intermediate format. `scripts/embed_rag.py` embeds every corpus found in `RAG_DATA_DIR` and upserts it into `rag_chunks`, keyed by `(agent_id, language, chunk_id)`; unchanged chunks are skipped, removed chunks are deleted, and 429/5xx responses are retried with backoff. It reads `DATABASE_URL` and `GEMINI_API_KEY` from settings, so the production database is populated from a laptop (the Railway image does not contain the corpora):

```bash
cd backend
uv run alembic upgrade head                                  # creates rag_chunks (once)
uv run python -m scripts.embed_rag --dry-run                  # what would change
DATABASE_URL="postgresql+asyncpg://user:pass@host:port/db" uv run python -m scripts.embed_rag
uv run python -m scripts.embed_rag --agent jung --language en  # one corpus
uv run python -m scripts.embed_rag --force                    # after changing RAG_EMBEDDING_MODEL/DIM
uv run python -m scripts.evaluate_rag evals/aurelius_en_golden.json --hybrid   # eval the production path
```

Take the production DSN from the Railway Postgres service (public `DATABASE_PUBLIC_URL`; replace `postgresql://` with `postgresql+asyncpg://`). The backend caches each corpus in memory for five minutes, so new embeddings are picked up without a redeploy. If `rag_chunks` is empty for a corpus and no JSON file exists, the backend logs one warning per corpus and answers without book context; if only the query embedding fails, it falls back to BM25.

### Freemium and Telegram Stars

The billing tier is server-owned and cannot be changed through `PATCH /api/me`.

- Free: 3 prompt-only answers per UTC day.
- Trial: 7 days, 5 RAG answers per day, 35 total, one Council of Three. After the RAG allowance, 3 prompt-only answers remain available that day.
- Pro: 350 Stars per recurring 30-day period, 30 RAG answers and 3 councils per day.

Pro is the primary offer everywhere: bot limit messages open the Stars invoice directly, and the Mini App Pro sheet leads with checkout (`POST /api/billing/checkout`). The Trial is offered only as a secondary button in that sheet (`POST /api/billing/trial`); the bot never promotes it. Pro is activated only after Telegram sends `successful_payment`. The bot supports `/subscribe`, `/cancel_subscription`, and the required `/paysupport` command. Payments are not refundable by policy; `/paysupport` explains how to stop the renewal. There is no refund tooling: if Telegram itself reverses a Stars payment, Pro stays active until the end of the paid period.

## Docker

One backend `Dockerfile` for both local compose and Railway (the frontend is served by Vite locally and by Vercel in production). Multi-stage: dependencies resolve into a virtualenv in a builder stage, the runtime stage gets only `.venv` + code, runs as a non-root user, ships a `HEALTHCHECK`, and keeps uvicorn as PID 1 for graceful shutdown. Linted with hadolint in CI.

Migrations run as a separate `migrate` compose service (same image, `alembic upgrade head`); `app` starts only after it completes:

```bash
cp .env.example .env   # fill in tokens
docker compose up --build
```

API: `http://127.0.0.1:8000`. On Railway the same migration step runs via `preDeployCommand` in `railway.toml`.

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`:

- **backend** — ruff, Alembic migrations against a Postgres service container, pytest (`backend/tests/`)
- **frontend** — oxlint, `tsc` + Vite build

On push to `main` (after both jobs pass) it deploys:

- **Backend → Railway** — the root `Dockerfile`, configured by `railway.toml` (migrations via `preDeployCommand`, healthcheck `/api/health`). Deployed with the Railway CLI.
- **Frontend → Vercel** — `frontend/` as the project root; `frontend/vercel.json` rewrites `/api/*` to the Railway domain, so the Mini App keeps same-origin requests and no CORS is needed. (Alternatively, set `VITE_API_URL` to call the backend directly — see [Deploy](#deploy).)

### One-time setup

GitHub repository **secrets**:

| Secret | Where to get it |
| --- | --- |
| `RAILWAY_TOKEN` | Railway project → Settings → Tokens (project token) |
| `VERCEL_TOKEN` | Vercel → Account Settings → Tokens |
| `VERCEL_ORG_ID` | `frontend/.vercel/project.json` after `vercel link` |
| `VERCEL_PROJECT_ID` | same file |

GitHub repository **variable** `RAILWAY_SERVICE` — the Railway service name (defaults to `aeon` in the workflow).

Railway service **environment variables** and Vercel project setup: see [Deploy](#deploy).

## Deploy

Backend runs on **Railway** (the root `Dockerfile`), frontend on **Vercel** (static SPA). Pushes to `main` deploy both automatically — see [CI/CD](#cicd). This section covers the configuration each platform needs.

### Frontend → backend wiring

Two supported ways for the Vercel frontend to reach the Railway backend:

1. **Vercel rewrites (default).** `frontend/vercel.json` proxies `/api/*` to the Railway domain, so the browser makes same-origin requests and CORS is not involved. Replace the placeholder domain with your Railway URL and leave `VITE_API_URL` unset.
2. **Direct + CORS (alternative).** Set `VITE_API_URL=https://<railway-domain>` on Vercel; the frontend then calls Railway directly. The backend allows the Vercel origin automatically once `MINI_APP_URL` (and/or `CORS_ORIGINS`) is set.

### Railway environment variables

Required:

| Variable | Value |
| --- | --- |
| `BOT_TOKEN` | bot token from BotFather |
| `BOT_USERNAME` | bot username without `@` |
| `BOT_MODE` | `webhook` |
| `WEBHOOK_BASE_URL` | the Railway public domain (used for the Telegram webhook) |
| `MINI_APP_URL` | the Vercel frontend URL (also allowed by CORS) |
| `GEMINI_API_KEY` | Gemini API key |
| `DATABASE_URL` | reference the Railway Postgres plugin: `${{ Postgres.DATABASE_URL }}` |

Optional (have defaults):

| Variable | Notes |
| --- | --- |
| `WEBHOOK_SECRET` | auto-generated if empty |
| `CORS_ORIGINS` | extra browser origins (CSV) beyond `MINI_APP_URL`, e.g. Vercel preview domains |
| `GEMINI_MODEL`, `GEMINI_MAX_OUTPUT_TOKENS`, `REMINDER_HOUR`, `REMINDER_TZ`, `INIT_DATA_MAX_AGE` | tuning |

Do **not** set `PORT` (Railway injects it), `STATIC_DIR` (the frontend is on Vercel), or `WEB_PORT` (dev only). Database migrations run automatically before each deploy via `preDeployCommand` (`alembic upgrade head`) in `railway.toml`.

### Vercel environment / setup

- Link the repo with **Root Directory = `frontend`**.
- Default path: put your Railway domain into `frontend/vercel.json`.
- Alternative path: set `VITE_API_URL=https://<railway-domain>` (build-time — redeploy after changing it).

## Migrating from the legacy bot.py

Profiles from the old `registrations` table (JSONB) can be imported once into the new schema:

```bash
cd backend
PYTHONPATH=. uv run python scripts/import_legacy.py
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `BOT_TOKEN` | — | bot token from BotFather |
| `BOT_USERNAME` | resolved via `getMe` | bot username without `@` |
| `BOT_MODE` | `polling` | `polling` or `webhook` |
| `WEBHOOK_SECRET` | random | webhook secret token (webhook mode) |
| `MINI_APP_URL` | — | public HTTPS URL of the Mini App (Vercel) |
| `WEBHOOK_BASE_URL` | falls back to `MINI_APP_URL` | public HTTPS URL of the backend (Railway), used for the webhook |
| `CORS_ORIGINS` | — | extra browser origins (CSV) allowed by CORS, in addition to `MINI_APP_URL` |
| `VITE_API_URL` (frontend) | — | backend base URL for direct API calls; empty uses same-origin / Vercel rewrites |
| `GEMINI_API_KEY` | — | Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `GEMINI_MAX_OUTPUT_TOKENS` | `2500` | max answer tokens |
| `RAG_ENABLED` | `true` | enable local book retrieval |
| `RAG_ALLOW_BASIC` | `false` | allow Basic users to use RAG; local testing override only |
| `RAG_DATA_DIR` | `data/rag` | directory containing per-agent JSON corpora (build input; optional BM25 fallback at runtime) |
| `RAG_TOP_K` | `4` | number of book chunks added to an agent prompt |
| `RAG_EMBEDDING_MODEL` | `gemini-embedding-001` | Gemini embedding model used for chunks and queries |
| `RAG_EMBEDDING_DIM` | `768` | embedding size stored in `rag_chunks`; change requires `embed_rag.py --force` |
| `DATABASE_URL` | local postgres | PostgreSQL DSN (asyncpg) |
| `REMINDER_HOUR` | `9` | default notification hour for new users; each user can change it in the bot |
| `REMINDER_TZ` | `UTC` | default notification timezone for new users; each user can change it in the bot |
| `STATIC_DIR` | — | path to built frontend (set in Docker) |
