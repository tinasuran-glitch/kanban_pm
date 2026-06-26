# Database Schema Proposal (Part 5)

This proposal defines a normalized SQLite schema for the MVP Kanban.

## Goals

- Support multiple users in schema, even though MVP login is hardcoded.
- Support one board per user in MVP logic.
- Preserve fixed column order/count while allowing column title edits.
- Persist board state only (no chat history persistence in MVP).

## Tables

### users

- `id` INTEGER PRIMARY KEY
- `username` TEXT NOT NULL UNIQUE
- `created_at` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

Purpose:

- Identity anchor for future real auth.
- MVP record will include `username = 'user'`.

### boards

- `id` INTEGER PRIMARY KEY
- `user_id` INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE
- `name` TEXT NOT NULL DEFAULT 'Default Board'
- `created_at` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
- `updated_at` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

Purpose:

- One board per user (enforced by `UNIQUE(user_id)`).

### columns

- `id` INTEGER PRIMARY KEY
- `board_id` INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE
- `key` TEXT NOT NULL
- `title` TEXT NOT NULL
- `position` INTEGER NOT NULL
- `created_at` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
- `updated_at` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
- UNIQUE (`board_id`, `key`)
- UNIQUE (`board_id`, `position`)

Purpose:

- Fixed structure with editable titles.
- `key` is stable identity (`backlog`, `discovery`, `progress`, `review`, `done`).
- `position` controls canonical order.

### cards

- `id` INTEGER PRIMARY KEY
- `board_id` INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE
- `column_id` INTEGER NOT NULL REFERENCES columns(id) ON DELETE CASCADE
- `title` TEXT NOT NULL
- `details` TEXT NOT NULL DEFAULT ''
- `position` INTEGER NOT NULL
- `created_at` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
- `updated_at` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
- UNIQUE (`column_id`, `position`)

Purpose:

- Cards belong to one column and are ordered within that column.

## Representation of Fixed Columns + Editable Titles

- Fixedness is enforced at service layer and seed data:
  - Create exactly 5 columns per board with fixed `key` values.
  - Disallow create/delete/reorder of columns in MVP API.
- Editable behavior:
  - Allow updates to `columns.title` only.

## Migration and Initialization Approach

- On backend startup:
  - Open SQLite file (create if missing).
  - Execute idempotent DDL (`CREATE TABLE IF NOT EXISTS ...`).
  - Seed MVP user (`user`) if absent.
  - Seed board for that user if absent.
  - Seed 5 columns with fixed keys/positions if absent.
  - Optionally seed starter cards for first-run UX.

- Migration style for MVP:
  - Keep a simple `schema_version` table with one integer row.
  - Apply ordered SQL migration scripts from `backend/migrations/` if version increases.

## API Shape Mapping (for upcoming parts)

Board read response can remain frontend-friendly:

- `columns`: array ordered by `position`
- `cards`: object keyed by card id
- `column.cardIds`: derived by selecting cards ordered by `position`

This preserves current frontend model while using normalized storage internally.

## Persistence Boundaries

Persisted:

- User board, columns, cards, and ordering.

Not persisted in MVP:

- AI chat conversation history.
- Transient UI state (pending confirmations, open forms).

## Minimal Indexes

- `idx_columns_board_position` on (`board_id`, `position`)
- `idx_cards_column_position` on (`column_id`, `position`)
- `idx_cards_board` on (`board_id`)

These keep board reads/moves efficient without over-indexing.
