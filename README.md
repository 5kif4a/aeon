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
└──────────┬────────────────┬──────────────┘
        PostgreSQL        Redis
   (source of truth)  (agent dialogue
                       history, TTL)
```

PostgreSQL is the single source of truth: profiles, goals, and diary entries created in the Mini App are the same rows the bot reads for reminders and agent context.

## Stack

**Backend** (`backend/`)
- Python 3.12, [uv](https://docs.astral.sh/uv/) for dependency management
- FastAPI + Uvicorn — Mini App REST API, Telegram webhook endpoint, static frontend serving
- python-telegram-bot v21 — onboarding `ConversationHandler`, agent chat, `JobQueue` daily goal reminders
- SQLAlchemy 2.0 (async, asyncpg) + Alembic migrations
- Redis — per-agent dialogue history with TTL
- Gemini API (httpx, streaming SSE) — agent answers

**Frontend** (`frontend/`)
- React 19 + TypeScript + Vite
- Tailwind CSS v4 (on top of the ported custom design system in `src/styles.css`)
- TanStack Query — server state (profile, goal, diary)
- React Hook Form + Zod — profile "About" form validation
- Telegram Mini App SDK via `telegram-web-app.js`

## Features

- **Three AI agents** — Marcus Aurelius (stoic mentor), Machiavelli (business tactician), Carl Jung (shadow analyst). Selected in the Mini App or via `/agents`; dialogue happens in the bot chat with streamed answers edited into a single message.
- **Onboarding in the bot** — `/start` flow (language → name → staged birth date picker → country) editing one Telegram message, saved straight to PostgreSQL.
- **Memento Mori calendar** — 90 years as 4,680 life weeks, computed from the birth date in the profile.
- **Diary** — reflection notes with quick prompts, stored server-side.
- **Goals** — one active goal with daily bot reminders (`JobQueue`, configurable hour and timezone) until closed.
- **Personal cabinet** — profile memory card, completion progress, plan/tokens.
- **Mini App auth** — every API request is authenticated with Telegram `initData` (HMAC validation) via the `Authorization: tma <initData>` header.
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

Requirements: Python 3.12+, uv, Node 22+, pnpm, Docker or Podman for PostgreSQL/Redis.

1. Start databases:

```bash
docker compose up -d postgres redis
```

2. Backend (port 8000):

```bash
cd backend
cp ../.env.example .env   # fill in BOT_TOKEN, GEMINI_API_KEY
# for local dev use: DATABASE_URL=postgresql+asyncpg://aeon:aeon@localhost:5432/aeon
#                    REDIS_URL=redis://localhost:6379/0
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

4. Telegram testing — expose the frontend over HTTPS and point the bot at it:

```bash
ngrok http 5173
# put the https URL into backend .env as MINI_APP_URL, restart the backend
```

With `BOT_MODE=polling` (default) no public URL is needed for the bot itself — only for the Mini App button.

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
| `REDIS_URL` | `${{ Redis.REDIS_URL }}` to enable per-agent dialogue history |
| `GEMINI_MODEL`, `GEMINI_MAX_OUTPUT_TOKENS`, `REDIS_AGENT_HISTORY_TTL`, `REMINDER_HOUR`, `REMINDER_TZ`, `INIT_DATA_MAX_AGE` | tuning |

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
| `DATABASE_URL` | local postgres | PostgreSQL DSN (asyncpg) |
| `REDIS_URL` | — | Redis DSN; empty disables dialogue history |
| `REDIS_AGENT_HISTORY_TTL` | `2592000` | dialogue history TTL, seconds |
| `REMINDER_HOUR` | `9` | daily goal reminder hour |
| `REMINDER_TZ` | `UTC` | reminder timezone |
| `STATIC_DIR` | — | path to built frontend (set in Docker) |
