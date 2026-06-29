# Code Review

Reviewed files: all backend Python, all frontend TypeScript/TSX, Dockerfiles, docker-compose, scripts, docs, and test suites.

Findings are ordered by priority within each section. Each item has a concrete action.

---

## Bugs

### B1 — Board shows seed data flash before API load (KanbanBoard.tsx:26)

`KanbanBoard` initializes React state with `initialData` and renders the board grid unconditionally. The `isLoading` flag only shows a loading message above the board — it does not gate rendering of the column/card grid. So users see the hardcoded seed cards for a frame before the real board loads.

**Action:** Initialize board state to `null` and conditionally render the board grid only when board state is non-null.

```tsx
const [board, setBoard] = useState<BoardData | null>(null);
// ...
{board ? (
  <section>
    {board.columns.map(...)}
  </section>
) : null}
```

---

### B2 — `handleDeleteCard` only removes cardId from the specified column (KanbanBoard.tsx:150)

`handleDeleteCard(columnId, cardId)` removes the cardId only from the column matching `columnId`, while the AI `delete_card` action correctly removes from all columns. If state ever becomes inconsistent (card referenced in multiple columns), `handleDeleteCard` would leave a dangling cardId reference in any other column while the card entry is gone from `cards`.

**Action:** Mirror the AI delete behavior — filter out the cardId from all columns, not just the specified one:

```tsx
columns: prev.columns.map((column) => ({
  ...column,
  cardIds: column.cardIds.filter((id) => id !== cardId),
})),
```

The `columnId` parameter can then be removed from the function signature and all call sites.

---

### B3 — `pendingBoardRef.current` cleared before save, lost on failure (KanbanBoard.tsx:83)

In `flush()`, `pendingBoardRef.current = null` is set before `await persistBoard(boardToSave)`. If `persistBoard` throws, the board-to-save is gone and will never be retried. The UI shows a save error, but the next user interaction that triggers `schedulePersist` will save whatever state exists at that point — potentially losing the change that failed.

**Action:** Only clear `pendingBoardRef.current` after a successful save:

```tsx
const boardToSave = pendingBoardRef.current;
pendingBoardRef.current = null;          // move this...
await persistBoard(boardToSave);         // ...to after this line
```

---

### B4 — `boards.updated_at` never updates (board_store.py:242)

`save_board` updates `columns.updated_at` and rebuilds `cards`, but never updates `boards.updated_at`. The board's timestamp stays at its creation time.

**Action:** Add an `UPDATE boards SET updated_at = CURRENT_TIMESTAMP WHERE id = ?` call inside the `save_board` transaction.

---

## Architecture Issues

### A1 — `saveBoard` response body discarded; unnecessary second fetch on AI confirm (boardApi.ts:16, KanbanBoard.tsx:208)

`PUT /api/board` already returns the full authoritative board, but `saveBoard()` in `boardApi.ts` only checks `response.ok` and discards the body. For normal mutations, the UI stays on optimistic state that may silently diverge from what the server persisted. For AI confirm (`handleConfirmAIApply`), this forces an extra `fetchBoard()` round-trip after the PUT.

**Action:** Have `saveBoard` return the board from the response body, and update `handleConfirmAIApply` to use that instead of calling `fetchBoard()` again.

```ts
// boardApi.ts
export const saveBoard = async (board: BoardData): Promise<BoardData> => {
  const response = await fetch("/api/board", { method: "PUT", ... });
  if (!response.ok) throw new Error("Could not save board changes.");
  return (await response.json()) as BoardData;
};
```

---

### A2 — No auth guard at the routing layer; board page renders before 401 is received

The board page at `/` has no server-side or middleware auth check. The client renders, then calls `fetchBoard()`, which gets a 401, then shows a load error — but never redirects to `/login`. If the session expires mid-session, the user sees "Could not load saved board. Showing local fallback." rather than being sent to the login page.

**Action:** Add a Next.js middleware file (`frontend/src/middleware.ts`) that checks for the `pm_session` cookie and redirects to `/login` when absent:

```ts
import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const session = request.cookies.get("pm_session");
  if (!session && !request.nextUrl.pathname.startsWith("/login")) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
}

export const config = { matcher: ["/((?!_next|favicon.ico).*)"] };
```

---

### A3 — `@app.on_event("startup")` is deprecated (main.py:439)

FastAPI 0.116 (the version in pyproject.toml) has deprecated `@app.on_event` in favor of the `lifespan` context manager.

**Action:** Replace with:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DB_PATH)
    yield

app = FastAPI(title="Project Management MVP Backend", lifespan=lifespan)
```

---

### A4 — Test files mutate a module-level global without cleanup (test_ai_api.py:9, test_ai_chat_api.py:9)

Both `_client()` helpers set `app_main.DB_PATH = str(tmp_path / "pm.db")` directly on the module. If tests from these files interleave with other test files that also import `app.main` (not currently an issue, but fragile), DB_PATH could be wrong.

**Action:** Use `monkeypatch.setattr` instead:

```python
def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(app_main, "DB_PATH", str(tmp_path / "pm.db"))
    app_main.init_db(app_main.DB_PATH)
    return TestClient(app_main.app)
```

---

### A5 — `start-mac.sh` deletes the database on every run

`rm -f backend/data/pm.db` runs unconditionally on every `./scripts/start-mac.sh`. Any data from the previous session is silently destroyed.

**Action:** Either remove the `rm -f` line (let the existing DB persist across restarts, which is what the Docker volume mount intends), or rename the script `reset-mac.sh` and create a separate `start-mac.sh` that does not wipe the DB. Having both scripts makes the intent explicit.

---

## Missing Test Coverage

### T1 — No test for save failure behavior in `KanbanBoard`

The `schedulePersist` / `persistBoard` error path (B3 above) is untested. `KanbanBoard.test.tsx` only exercises the happy path.

**Action:** Add a unit test that mocks `PUT /api/board` to fail and verifies the save error message appears.

---

### T2 — No test for auth expiry / 401 on board load

There is no test that verifies what the UI shows when `GET /api/board` returns 401 (session expired). Currently it shows a fallback error banner; with A2 fixed it should redirect.

**Action:** Add a test that mocks `fetchBoard` throwing and verifies the redirect or error state.

---

### T3 — E2E tests are incomplete (marked in PLAN.md)

Several e2e scenarios remain unimplemented: auth flow (login → board → logout), board persistence across refresh, and AI suggest-to-confirm flow. Playwright is configured and the test skeleton exists in `frontend/tests/kanban.spec.ts`.

**Action:** Implement the three marked E2E tests. These are the highest-value regression guards for the full stack.

---

## Code Quality

### Q1 — `_normalize_ai_payload` is 120 lines in a single function (main.py:303)

The function handles create_card, move_card/edit_card/delete_card, and rename_column normalization in one block. It is correct but hard to read and test in isolation.

**Action:** Extract per-action helpers: `_normalize_create_card_action`, `_normalize_move_or_edit_action`, `_normalize_rename_column_action`. The main function becomes a dispatcher loop. Each helper is independently testable.

---

### Q2 — `KanbanBoard.tsx` is 415 lines managing three independent concerns

Board state + persistence, drag-and-drop, and AI chat sidebar are all co-located. The AI chat state (`messages`, `chatInput`, `chatError`, `isAiThinking`, `isApplyingAi`, `pendingActions`, `pendingBoardRef`) is independent of board drag/drop state.

**Action:** Extract an `AISidebar` component that accepts `board` and `onBoardUpdate` as props and owns all AI chat state internally. `KanbanBoard` shrinks to board state + drag-drop.

---

### Q3 — `boards.name` and `columns.key` are dead columns

`boards.name` is set to `'Default Board'` at creation but never returned by `get_board()` or used anywhere. `columns.key` (e.g. `'backlog'`, `'discovery'`) is seeded and stored but never returned by `get_board()` — the API only uses `column_id`. Both columns exist in schema and seed but serve no function in the current codebase.

**Action:** Remove `boards.name` from `create_schema`. Evaluate whether `columns.key` has a future use — if not, remove it from schema and `DEFAULT_COLUMNS`. If it is intended as a stable semantic identifier (distinct from editable title), document that intent.

---

### Q4 — `initialData` imported and used as initial board state (KanbanBoard.tsx:16, 26)

After fixing B1, `initialData` will no longer be needed in `KanbanBoard`. Currently it creates a coupling between the frontend seed fixture and the component's loading behavior.

**Action:** After B1 is fixed, remove the `initialData` import from `KanbanBoard.tsx`. `initialData` in `kanban.ts` can remain for tests that need a known board fixture.

---

### Q5 — `test_ai_api.py` file name is misleading

The file only tests the `/api/ai/probe` endpoint. The chat endpoint tests are in `test_ai_chat_api.py`. A reader expecting "AI API tests" would look in `test_ai_api.py` and miss the chat tests.

**Action:** Rename `test_ai_api.py` to `test_ai_probe_api.py`.

---

## Documentation Discrepancies

### D1 — `DATABASE_SCHEMA.md` describes wrong foreign key for `cards.column_id`

The doc says `cards.column_id INTEGER NOT NULL REFERENCES columns(id) ON DELETE CASCADE`, implying an integer FK to the `columns` autoincrement PK. The actual implementation uses `column_id TEXT NOT NULL` with a composite FK `REFERENCES columns(board_id, column_id)` on the text `column_id` field. The implementation is intentionally different and more correct for this pattern.

**Action:** Update `DATABASE_SCHEMA.md` to match the actual schema — `column_id TEXT NOT NULL` with the composite FK.

---

### D2 — `schema_version` migration table described in docs but never implemented

`DATABASE_SCHEMA.md` proposes a `schema_version` table with ordered migration scripts from `backend/migrations/`. Neither the table nor the `migrations/` directory exists.

**Action:** Either implement the migration system (worthwhile before any schema change), or remove the migration section from the doc and replace with a note that the current approach is idempotent DDL only (`CREATE TABLE IF NOT EXISTS`).

---

### D3 — `start-mac.sh` documented behavior (CLAUDE.md) understates the risk

CLAUDE.md says "Note: `start-mac.sh` deletes `backend/data/pm.db` on every run (fresh DB each start)." This is accurate but buries the data-loss behavior. See A5 for the fix recommendation.

---

## Summary Table

| ID | Area | Priority | Effort |
|----|------|----------|--------|
| B1 | Board flashes seed data before load | High | Small |
| B2 | `handleDeleteCard` leaves dangling cardIds | High | Small |
| B3 | Pending board state lost on save failure | Medium | Small |
| B4 | `boards.updated_at` never updates | Low | Trivial |
| A1 | `saveBoard` discards response body | Medium | Small |
| A2 | No routing-layer auth guard | High | Small |
| A3 | `@app.on_event` deprecated | Low | Trivial |
| A4 | Global DB_PATH mutation in tests | Low | Trivial |
| A5 | `start-mac.sh` silently wipes DB | Medium | Small |
| T1 | No test for save failure | Medium | Small |
| T2 | No test for 401 on board load | Medium | Small |
| T3 | E2E tests incomplete | Medium | Medium |
| Q1 | `_normalize_ai_payload` too large | Low | Medium |
| Q2 | `KanbanBoard.tsx` too many concerns | Low | Medium |
| Q3 | Dead DB columns (`boards.name`, `columns.key`) | Low | Trivial |
| Q4 | `initialData` import in `KanbanBoard` after B1 fix | Low | Trivial |
| Q5 | Misleading test file name | Low | Trivial |
| D1 | `DATABASE_SCHEMA.md` wrong FK type | Low | Trivial |
| D2 | `schema_version` table missing | Low | Trivial |
| D3 | CLAUDE.md understates DB wipe risk | Low | Trivial |
