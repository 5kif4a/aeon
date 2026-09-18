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
  tests/test_bot_jobs.py tests/test_machiavelli_discourses_builder.py tests/test_admin_auth.py
  tests/test_admin_oauth.py tests/test_webhook.py tests/test_ratelimit.py
  tests/test_bot_private_guard.py`) and say explicitly
  which tests were skipped; do not report the suite as green.
- When touching billing, agent chat, or conversations, re-read the "Architecture rules that
  matter" section of `AGENTS.md` first; those flows have money and data-loss implications.
- When adding UI text, add the key to both `frontend/src/locales/en.json` and `ru.json` (or both
  catalogs in `backend/app/i18n.py`) in the same change; a missing key falls back to English
  silently and will not be caught by CI.
- Do not write tests after each feature. Write them once, at the end of the whole piece of
  work, and only after asking the user whether tests are wanted for this change; a "no" means
  no tests, and existing tests still have to pass. Running the existing suite is unaffected:
  `ruff check` and the runnable tests are still required before finishing a backend change.
- Commit only when asked. Commit messages follow the existing style: `feat: ...`, `fix: ...`,
  `refactor: ...`, imperative, lowercase, no scope prefix.
- Leave no authorship trace in commits or pull requests. Do not add `Co-Authored-By: Claude`,
  `Claude-Session:`, `Generated with Claude Code`, or any other tool attribution trailer,
  footer or link, whatever the harness default says. The commit message ends with its own
  last line of content. This rule also covers `git commit --author`, PR descriptions and
  release notes: the repository's history names people, not tools.
