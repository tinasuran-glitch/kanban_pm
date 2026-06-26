# Project Plan

This document is the execution checklist for the MVP. Work proceeds in order. Each part has scope, tasks, tests, and success criteria.

## Confirmed Decisions

- Preserve Next.js server-side capabilities (no static-only downgrade).
- Kanban has fixed column count/order; column titles are editable.
- Auth implementation choice: simple cookie-based session after validating `user` / `password`.
- Database uses normalized tables (not board-as-single-JSON-row design).
- Persist board state only for MVP (chat history remains transient).
- AI response format uses strict schema validation.
- AI-proposed board changes require explicit user confirmation before apply.
- Scripts implementation choice: OS wrapper scripts call Docker Compose.
- Testing level: simple but necessary (targeted unit + integration + e2e smoke per phase).

## Part 1: Planning and Baseline Documentation

### Checklist

- [x] Expand this plan with task-level execution details, test strategy, and success criteria.
- [x] Add `frontend/AGENTS.md` describing current frontend architecture and test setup.
- [x] Pause for user review and approval before implementation work begins.

### Tests

- [x] N/A (documentation-only step).

### Success Criteria

- [x] Plan is explicit enough to execute without ambiguity.
- [x] User approves plan before Part 2 starts.

## Part 2: Scaffolding (Docker, FastAPI, Scripts)

### Checklist

- [x] Create backend project skeleton in `backend/` with FastAPI app entrypoint.
- [x] Add Dockerfile and Docker Compose config for local dev/run.
- [x] Use `uv` in container image for Python dependency management.
- [x] Add simple API route (`/api/health`) and temporary hello page route.
- [x] Add start/stop scripts for macOS, Linux, Windows in `scripts/` using Docker Compose wrappers.
- [x] Add backend AGENTS documentation in `backend/AGENTS.md`.

### Tests

- [x] Container builds successfully.
- [x] App starts via scripts on local machine.
- [x] `GET /api/health` returns success payload.
- [x] Root route returns temporary hello content.

### Success Criteria

- [x] One command starts full stack in Docker.
- [x] API and page are reachable locally.

## Part 3: Integrate Existing Frontend with Server-Side Next Support

### Checklist

- [x] Keep Next.js app as a server-capable app (SSR features preserved).
- [x] Integrate frontend runtime with backend container orchestration.
- [x] Route `/` to Next.js app while backend continues to serve API routes.
- [x] Ensure current Kanban demo UI works unchanged functionally.
- [x] Add/update build/run docs for this architecture.

### Tests

- [x] Frontend unit tests pass.
- [ ] Frontend e2e smoke tests pass in containerized setup. (Pending local Playwright browser installation)
- [x] Manual check that `/` renders Kanban and backend API still responds.

### Success Criteria

- [x] Single deployed stack serves Next UI and FastAPI endpoints.
- [x] No regression in current Kanban interactions.

## Part 4: MVP Sign-In/Sign-Out Gate

### Checklist

- [x] Add login screen at initial `/` access.
- [x] Validate only hardcoded credentials (`user`, `password`).
- [x] Issue simple cookie session on successful login.
- [x] Add logout action that clears session and redirects to login.
- [x] Protect board page from unauthenticated access.

### Tests

- [x] Backend auth unit tests for login success/failure and logout.
- [x] Integration test for protected route requiring auth. (Manual curl verification)
- [ ] Frontend e2e flow: blocked when logged out, access after login, blocked again after logout.

### Success Criteria

- [x] Unauthenticated users cannot reach board.
- [x] Auth flow is stable and simple.

## Part 5: Database Modeling and Sign-Off

### Checklist

- [x] Draft schema doc in `docs/` using normalized tables.
- [x] Include table definitions for users, boards, columns, cards, and ordering.
- [x] Include migration/initialization approach for SQLite file creation.
- [x] Explain how fixed column structure with editable titles is represented.
- [x] Explain persistence boundaries (board persisted, chat history not persisted).
- [x] Pause for user sign-off before schema implementation.

### Tests

- [x] N/A for implementation (design/document review step).

### Success Criteria

- [x] User approves schema and persistence approach.

## Part 6: Backend Board API + SQLite Persistence

### Checklist

- [x] Implement SQLite connection/bootstrap (create DB if missing).
- [x] Add minimal migration/init flow for normalized schema.
- [x] Implement board read endpoint for authenticated user.
- [x] Implement board update endpoint(s) for rename/move/edit/add/delete operations.
- [x] Ensure only one board per user for MVP logic.

### Tests

- [x] Backend unit tests for data access and service logic.
- [x] API tests for auth, validation, read, and write flows.
- [x] Restart test proving board state persists across server restart.

### Success Criteria

- [x] Board mutations persist and reload correctly for user.
- [x] DB initializes automatically on first run.

## Part 7: Frontend + Backend Wiring

### Checklist

- [x] Replace local in-memory board source with backend API calls.
- [x] Load board on app start after login.
- [x] Persist rename/move/add/delete edits via API.
- [x] Add minimal loading/error states (simple and clear).

### Tests

- [x] Frontend unit tests for API client and core state update paths.
- [x] Integration tests for board load and mutation calls.
- [ ] E2E test covering login, board edit, refresh, and persistence.

### Success Criteria

- [x] Board is fully backend-driven and persistent.
- [x] Current UX remains responsive and understandable.

## Part 8: AI Connectivity (OpenRouter)

### Checklist

- [x] Add backend AI client using `OPENROUTER_API_KEY` from `.env`.
- [x] Configure model `openai/gpt-oss-120b`.
- [x] Add backend route to run connectivity probe prompt (`2+2`).
- [x] Add resilient error mapping for missing key/network/provider errors.

### Tests

- [x] Unit test for AI client request construction.
- [x] Integration test with mocked provider response.
- [x] Manual smoke call returning expected math answer.

### Success Criteria

- [x] AI call path is functional and diagnosable.

## Part 9: Structured AI Board-Action Contract

### Checklist

- [x] Define strict JSON schema for AI response payload.
- [x] Include fields for assistant message and optional board patch/action list.
- [x] Send board JSON snapshot + user message + transient conversation context.
- [x] Reject invalid AI outputs and surface safe error to client.
- [x] Keep conversation context runtime-only for MVP (no DB persistence).

### Tests

- [x] Schema validation unit tests (valid/invalid payloads).
- [x] Integration tests for accepted action, rejected malformed output, and no-op response.
- [x] Safety test ensuring invalid AI payload never mutates DB.

### Success Criteria

- [x] All AI outputs are validated before any business action.
- [x] Backend behavior is deterministic on malformed AI responses.

## Part 10: Sidebar Chat UX + Confirmed AI Apply

### Checklist

- [x] Add chat sidebar UI integrated with existing board layout.
- [x] Show user/assistant messages and pending AI-suggested board updates.
- [x] Require explicit confirm/cancel for any AI-proposed board mutation.
- [x] On confirm, apply mutation via backend and refresh board state.
- [x] On cancel, keep board unchanged and continue chat.

### Tests

- [x] Frontend unit tests for confirmation workflow state.
- [x] Integration tests for confirm apply and cancel no-op behavior.
- [ ] E2E test for end-to-end AI suggestion to confirmed board update.

### Success Criteria

- [x] AI can assist and propose changes without silent auto-mutation.
- [x] User remains in control of all board updates.

## Cross-Cutting Constraints

- Keep implementation simple and minimal; avoid over-engineering.
- Keep docs concise and practical.
- Identify root cause before any fix during implementation.
- Respect project color palette and existing frontend visual language.
- Target around 80% coverage when practical, but prioritize high-value tests over coverage chasing.