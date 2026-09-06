# CLAUDE.md

Project guide for Claude Code. The canonical, tool-agnostic guide is `AGENTS.md`; it is imported
here so both files stay in sync. Edit `AGENTS.md` for anything that applies to every coding agent
and keep this file for Claude Code specifics only.

@AGENTS.md

## Claude Code specifics

- Work from the repo root; `backend/` and `frontend/` are separate toolchains (`uv` and `pnpm`).
  Prefer absolute paths in Bash calls rather than chaining `cd`.
- Pre-approved commands live in `.claude/settings.local.json` (`uv run *`, `uv add *`,
  `npx oxlint *`, local curl health checks). Add new read-only checks there instead of asking
  each time.
- Local Postgres is often not running. If `pytest` fails with a connection error on
  `localhost:5432`, run the DB-free subset (`tests/test_rag.py tests/test_bot_ui.py
  tests/test_bot_jobs.py tests/test_machiavelli_discourses_builder.py`) and say explicitly
  which tests were skipped; do not report the suite as green.
- When touching billing, agent chat, or conversations, re-read the "Architecture rules that
  matter" section of `AGENTS.md` first; those flows have money and data-loss implications.
- When adding UI text, add the key to both `frontend/src/locales/en.json` and `ru.json` (or both
  catalogs in `backend/app/i18n.py`) in the same change; a missing key falls back to English
  silently and will not be caught by CI.
- Commit only when asked. Commit messages follow the existing style: `feat: ...`, `fix: ...`,
  `refactor: ...`, imperative, lowercase, no scope prefix.
