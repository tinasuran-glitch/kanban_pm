# Backend Guide

## Purpose

The backend hosts the FastAPI service for API routes and temporary scaffold pages. During early phases, it proves container and API wiring; later phases add auth, persistence, and AI features.

## Current Contents

- `backend/app/main.py`: FastAPI app with:
	- `GET /api/health` for service health checks.
	- `POST /api/auth/login` for MVP credential validation (`user` / `password`) and session cookie set.
	- `POST /api/auth/logout` for session cookie clear.
	- `GET /api/auth/session` for session cookie validation status.
	- `GET /api/board` for authenticated board read.
	- `PUT /api/board` for authenticated board update.
- `backend/app/board_store.py`: SQLite schema initialization, seed data, board load/save, and payload validation.
- `backend/pyproject.toml`: Python project metadata and dependencies.
- `backend/Dockerfile`: Container image using `uv` to install and run the app.
- `backend/tests/test_auth_logic.py`: Lightweight auth logic tests.
- `backend/tests/test_board_store.py`: Board store persistence and validation tests.

## Runtime

- App command: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Container port: `8000`
- API base during local Docker run: `http://localhost:8000`

Notes:

- UI root `/` is now served by Next.js through the gateway container.
- FastAPI serves API routes under `/api/*`.
- SQLite file path is `PM_DB_PATH` (default `/app/data/pm.db`) and is persisted via Docker volume mount.

## Conventions

- Keep backend changes simple and phase-focused.
- Prefer explicit request/response models when APIs are introduced.
- Add tests as features are added; do not defer coverage to the end.