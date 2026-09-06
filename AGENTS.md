# AGENTS.md — working guide for coding agents

`aeon` is a Telegram bot + Mini App with three AI mentors (Marcus Aurelius, Machiavelli, Carl Jung).
One FastAPI backend serves both the Mini App REST API and the Telegram bot; PostgreSQL is the single
source of truth (including dialogue history), Gemini generates answers.
Product/economics context lives in `README.md`, `monetization.md`, `marketing.md`, `RAG.md`.

## Repository layout

```
backend/                Python 3.12, FastAPI + python-telegram-bot v21, SQLAlchemy 2 async, Alembic
  app/main.py           FastAPI app, lifespan starts the bot (polling|webhook), /tg/webhook, /api/health
  app/core/             config.py (pydantic-settings, lru_cache), telegram_auth.py (initData HMAC)
  app/api/              deps.py (CurrentUser via `Authorization: tma <initData>`), schemas.py, routes/
  app/bot/              application.py (handlers + JobQueue), chat.py (agent dialogue in the bot),
                        handlers/{onboarding,commands,payments,ops}.py, jobs.py (daily/weekly), ui.py, messaging.py
  app/services/         business logic shared by API and bot: billing, agent_chat, conversations,
                        users, goals, diary, rag; events (product_events log), stats (metrics),
                        ops (pushes to the product-owner Telegram group)
  app/clients/gemini.py httpx client for generateContent / streamGenerateContent (SSE)
  app/db/               models.py, session.py (engine + SessionFactory, expire_on_commit=False)
  app/agents.py         agent registry: ids, localized names/roles/intros, English system prompts
  app/i18n.py           every user-facing backend string, ru/en
  migrations/           Alembic; revision ids are dated slugs (e.g. 20260902_conversations)
  scripts/              RAG corpus builders, eval/audit tools, import_legacy.py
  tests/                pytest (asyncio auto mode); API tests need a live Postgres
frontend/               React 19 + TypeScript + Vite + Tailwind v4 + TanStack Query + TanStack Router + RHF/Zod
  src/router.tsx        TanStack Router: /landing, and the `app` layout (/, /calendar?tab, /profile?sheet);
                        no initData gate, every screen opens in a plain browser for development
  src/lib/deeplinks.ts  start_param and legacy ?view= → route mapping, applied before the router starts
  src/App.tsx           AppShell: Outlet, agent/dialog actions via useAppShell(), BackButton, BottomNav
  src/views/            HomeView, CalendarView (life grid + goal + diary), ProfileView (billing), LandingView
  src/hooks/queries.ts  all server state (query keys: profile, goal, diary, billing)
  src/lib/api.ts        fetch wrapper; src/lib/types.ts mirrors backend schemas (camelCase)
  src/lib/i18n.ts       + src/locales/{en,ru}.json (key sets must stay identical)
  src/lib/telegram.ts   thin wrapper over window.Telegram.WebApp
Dockerfile, docker-compose.yml, railway.toml, .github/workflows/ci.yml
```

## Commands

Backend (run from `backend/`):

```bash
uv sync                                   # deps (uv, package = false)
uv run alembic upgrade head               # migrations (needs DATABASE_URL)
uv run uvicorn app.main:app --reload --port 8000
uv run ruff check app scripts tests       # lint (E,F,I,UP,B,W; E501 ignored; line-length 100)
uv run pytest -q                          # all tests; API/billing tests need Postgres on localhost:5432
uv run pytest -q tests/test_rag.py tests/test_bot_ui.py tests/test_bot_jobs.py   # no DB needed
uv run alembic revision -m "..."          # new migration; set a dated revision id like existing ones
```

Frontend (run from `frontend/`):

```bash
pnpm install
pnpm dev                                  # :5173, proxies /api and /tg to :8000
pnpm build                                # tsc -b && vite build (CI gate)
pnpm exec oxlint src                      # lint (CI gate)
pnpm format                               # prettier (+ tailwind plugin)
pnpm generate:api                         # openapi-typescript from a running backend
```

Infra: `docker compose up -d postgres` for the local database. CI (`.github/workflows/ci.yml`)
runs hadolint, ruff, alembic upgrade against a Postgres service, pytest, oxlint, `pnpm build`, then
deploys backend to Railway and frontend to Vercel on push to `main`.

Before finishing any backend change run `ruff check` and the tests you can run; before finishing
any frontend change run `pnpm build` and `pnpm exec oxlint src`. Both must be clean: CI blocks on them.

## Architecture rules that matter

**Auth.** Every `/api/*` route takes `CurrentUser` (`app/api/deps.py`), which validates Telegram
`initData` (HMAC, `INIT_DATA_MAX_AGE`) and calls `users.get_or_create_user`. There is no other auth.
The bot identifies users by `chat_id == telegram user id` (private chats only); `User.id` is that id.

**Billing is server-owned.** Plans are `Free | Trial | Pro`. The truth is
`billing.effective_plan(user)` computed from `pro_expires_at` / `trial_expires_at`; the `users.plan`
column is a denormalized cache, never trust it for entitlements. Never add `plan`/`tokens` to
`ProfileUpdate`. Limits come from `Settings` (`FREE_DAILY_QUESTIONS`, `TRIAL_*`, `PRO_*`).
The reserve/release pattern is mandatory around every Gemini call:
`billing.reserve_agent_question` (or `reserve_council`) → generate → on failure
`release_agent_question` / `release_council`. Counters live in `daily_usages` per UTC date.
Pro is activated only by `successful_payment` (Stars, `currency="XTR"`); invoice payloads are bound to
the user id via `billing.pro_invoice_payload` and checked in both `precheckout` and `successful_payment`.

**Agent dialogue flow** (`app/bot/chat.py` → `app/services/agent_chat.py`): the Mini App never
talks to Gemini; `POST /api/agents/{id}/dialog` only sets the active agent and pushes the first
message into the bot chat. Answers stream via `streamGenerateContent` and are edited into a single
Telegram message; on stream failure there is a non-stream fallback. RAG context is added only when
the grant mode is `rag` (`AccessGrant.generation_plan` is set on the in-memory `user.plan` before
generation; `rag.plan_has_rag_access` gates on it, `RAG_ALLOW_BASIC` is dev-only).

**Conversations.** `conversations` + `conversation_messages` are the durable history. A partial
unique index enforces **one active conversation per user across all agents**; `start_session`
closes every other active session. `agent_chat.get_history` / `append_history` read and write
these tables directly (there is no cache layer). Council answers are stored as closed sessions
with `agent_id="council"`.

**Notifications.** `JobQueue` runs `send_daily_notifications` and `send_life_weekly_reviews`
every 15 minutes in-process; per-user `reminder_timezone` / `reminder_hour` decide "due",
`last_daily_notification_date` / `last_life_weekly_date` prevent duplicates. Only users with a
`birth_date` receive anything. A weekly review suppresses that day's daily message.
Running more than one backend replica will duplicate notifications; keep a single instance.

**Ops notifications.** `product_events` is an append-only log written by services inside the
same transaction as the state change (`events.record`: `user_created`, `trial_started`,
`payment_succeeded`, `subscription_canceled`, `question_limit_hit`, `generation_failed`, ...).
The bot/API layer announces to the product-owner group through `services/ops.py`
(`OPS_CHAT_ID`, optional forum threads); sends are fire-and-forget and never raise, alerts are
throttled per kind. `/stats [7|30]` answers only in the ops group or to `OPS_ADMIN_IDS`; the
`ops_digests` job posts daily/weekly/monthly digests at `OPS_DIGEST_HOUR` and dedupes through
`ops_digest_sent` events. Ops texts are internal English and carry user ids, never names or
message content. Because the bot sits in a group, every user-facing handler is filtered to
`filters.ChatType.PRIVATE`; keep it that way for new handlers.

**Admin panel.** `/admin` on the frontend (`src/views/admin/*`, own layout, not the Mini App
shell) talks to `/api/admin/*` (`app/api/routes/admin.py`, read models in `services/admin.py`).
`AdminUser` (`app/api/deps.py`) accepts `Authorization: tma <initData>` inside Telegram or
`Authorization: admin <token>` from a browser; the token is issued by `POST /api/admin/auth/telegram`
after verifying a Telegram Login Widget payload (`app/core/admin_auth.py`). Access is only the
`OPS_ADMIN_IDS` allowlist; there are no roles in the database. Opening a dialogue and granting
Pro are recorded as `admin_view_conversation` / `pro_granted` events.

**Sessions in the bot.** Bot handlers open short-lived `SessionFactory()` sessions and let the
object detach; `expire_on_commit=False` makes that safe. API routes use the `SessionDep`
dependency. Never keep a session open across a Gemini call or a Telegram send.

**Settings.** `get_settings()` is `lru_cache`d; env is read once per process (tests rely on
`os.environ.setdefault` before the first import of `app.*`).

## Conventions

- Code, identifiers, comments, and log messages are English. Every user-visible string goes into
  `backend/app/i18n.py` (bot, API errors, LLM error texts) or `frontend/src/locales/*.json`
  (Mini App). Add keys to **both** `en` and `ru`; the frontend types keys off `en.json`.
- Agent prompts are English with a per-request language directive (`_language_directive`).
  Russian replies must use the respectful «Вы».
- API JSON fields are camelCase (Pydantic schemas map to snake_case columns in `to_user_fields`
  / `from_user`). Keep `frontend/src/lib/types.ts` in sync with `backend/app/api/schemas.py`.
- New agent ids must be added to `app/agents.py`, `frontend/src/lib/agents.ts`, the RAG allowlist
  in `rag.retrieve`, and (if notified) the rotation tables in `app/i18n.py`.
- Migrations: one file per change, dated revision id, always implement `downgrade`. Views
  `conversation_overview` / `conversation_messages_view` are created in a migration; update them
  there if the underlying columns change.
- Tests: `asyncio_mode = auto`; DB tests create and delete fixed user ids (`900_000_0xx`);
  pure-logic tests (RAG, keyboards, i18n rotation) must stay DB-free.
- Frontend routing: add screens as routes in `src/router.tsx`; deep-linkable UI state (tab, open
  sheet) goes into validated search params, not `useState`. Bot buttons get their URLs from
  `webapp.build_webapp_url(view, **params)`; new `startapp` keys go into `src/lib/deeplinks.ts`.
- Frontend: Tailwind utility classes in JSX, shared class strings in `src/lib/ui.ts`, design tokens
  in `src/styles.css` `@theme`. Server state only through hooks in `src/hooks/queries.ts`; update
  the cache in `onSuccess` rather than refetching everything. Haptics via `lib/telegram.haptic`.
- Formatting: ruff for Python (formatter owns line length), prettier for the frontend.

## Things not to do

- Do not call Gemini without a billing grant, and do not swallow a failed generation without
  releasing the grant.
- Do not read `user.plan` to decide access; use `effective_plan` or the grant.
- Do not commit anything under `backend/data/` (RAG corpora are built locally per environment).
- Do not set `PORT`, `STATIC_DIR`, or `WEB_PORT` in Railway; `PORT` is injected.
- Do not add a second active conversation path or bypass `conversations.start_session`.
- Do not put Russian or English UI text inline in code.
- Do not edit `frontend/vercel.json` rewrite target or `.env.example` defaults casually; they are
  the production wiring.

## Environment

Copy `.env.example` to `backend/.env` for local work. Minimum for a useful dev loop:
`BOT_TOKEN`, `GEMINI_API_KEY`, `DATABASE_URL=postgresql+asyncpg://aeon:aeon@localhost:5432/aeon`,
`BOT_MODE=polling`. `MINI_APP_URL` (an https ngrok URL to
the Vite dev server) is needed only to open the Mini App from Telegram. Production runs
`BOT_MODE=webhook` with `WEBHOOK_BASE_URL` set to the Railway domain.
