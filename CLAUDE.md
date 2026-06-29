# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local-only Kanban board project management app. Single user (`user` / `password`). One board per user. AI chat sidebar that proposes board changes requiring explicit confirmation before applying.

## Running the app

```bash
./scripts/start-mac.sh   # builds and starts all containers, wipes DB
./scripts/stop-mac.sh    # stops containers
```

App is served at `http://localhost:8000`. Linux and Windows equivalents exist in `scripts/`.

Note: `start-mac.sh` deletes `backend/data/pm.db` on every run (fresh DB each start).

## Architecture

Three Docker containers coordinated by nginx:

- **gateway** (nginx, port 8000): routes `/api/*` → backend, everything else → frontend
- **backend** (FastAPI, internal port 8000): API routes and SQLite persistence
- **frontend** (Next.js, internal): SSR-capable app, served via nginx proxy

The backend does **not** serve the frontend directly — nginx handles routing. `OPENROUTER_API_KEY` is read from `.env` at project root.

## Backend

**Commands (run from `backend/`):**
```bash
uv run pytest                      # all tests
uv run pytest tests/test_board_store.py  # single test file
uv run pytest -k "test_name"       # single test
```

**Key files:**
- `backend/app/main.py` — all API routes and Pydantic request/response models
- `backend/app/board_store.py` — SQLite schema init, seed data, board read/write
- `backend/app/ai_client.py` — OpenRouter client (`openai/gpt-oss-120b`)

**Board save strategy:** `save_board` deletes all cards and reinserts them on every PUT to avoid positional constraint conflicts during reorders.

**AI payload normalization:** Raw AI JSON is passed through `_normalize_ai_payload` before schema validation. This resolves column/card IDs by name match, normalizes action type strings, and fixes key casing — because the model doesn't always follow the schema exactly.

**Column structure is fixed:** The 5 columns (`col-backlog`, `col-discovery`, `col-progress`, `col-review`, `col-done`) cannot be added or removed. Titles are editable.

**DB path:** Controlled by `PM_DB_PATH` env var (default `/app/data/pm.db`). The `backend/data/` directory is volume-mounted from the host.

## Frontend

**Commands (run from `frontend/`):**
```bash
npm run dev          # local dev server (not for production use)
npm test             # unit tests (vitest)
npm run test:e2e     # e2e tests (playwright)
npm run lint         # eslint
```

**Key files:**
- `src/app/page.tsx` and `src/app/login/` — board page and login page
- `src/components/KanbanBoard.tsx` — owns all board state, DnD context
- `src/lib/kanban.ts` — data types (`Card`, `Column`, `BoardData`), `moveCard`, `createId`
- `src/lib/boardApi.ts` — fetch wrappers for `/api/board` (GET/PUT)
- `src/lib/aiApi.ts` — fetch wrapper for `/api/ai/chat`

**State flow:** Board state lives in `KanbanBoard` React state. All mutations (drag, add, delete, rename, AI confirm) go through `PUT /api/board` which returns the full updated board.

**AI confirm flow:** AI response includes `actions[]`. These are shown to the user as a pending proposal. On confirm, the frontend applies the actions to local board state and calls `PUT /api/board`. Chat history is kept in component state only — never persisted.

## Color palette

- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991`
- Dark Navy: `#032147`
- Gray Text: `#888888`

CSS variables for these are defined in `frontend/src/app/globals.css`.

## Coding standards

- No over-engineering; no extra features; no defensive programming beyond what's needed
- No emojis anywhere
- Identify root cause before attempting any fix — prove with evidence first
- Keep docs minimal and concise
