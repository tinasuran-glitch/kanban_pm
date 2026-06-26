# Frontend Code Guide

## Purpose

This document describes the current frontend implementation in `frontend/` so future changes can preserve behavior while backend, auth, and AI features are integrated.

## Stack

- Next.js App Router (TypeScript)
- React client components for interactive board UI
- Tailwind CSS v4-style import in `src/app/globals.css`
- `@dnd-kit` for drag and drop behavior
- Vitest + Testing Library for unit/component tests
- Playwright for browser e2e tests

## Current App Structure

- `src/app/layout.tsx`
- `src/app/page.tsx`
- `src/app/globals.css`
- `src/components/*`
- `src/lib/kanban.ts`

The home page currently renders a single client component (`KanbanBoard`) at `/`.

## Data Model (Current Frontend-Only)

`src/lib/kanban.ts` defines:

- `Card` with `id`, `title`, `details`
- `Column` with `id`, `title`, `cardIds`
- `BoardData` with `columns` and `cards`

It also provides:

- `initialData` containing 5 columns and seed cards
- `moveCard(columns, activeId, overId)` for within/across-column drag outcomes
- `createId(prefix)` for client-side card id generation

## Component Responsibilities

- `KanbanBoard.tsx`
- Owns board state in React state (`useState`), initially from `initialData`
- Handles drag start/end with `DndContext` and `DragOverlay`
- Handles rename column, add card, delete card
- Renders 5-column grid and board header

- `KanbanColumn.tsx`
- Droppable column container
- Editable column title input
- Sortable card list via `SortableContext`
- Empty-state drop target text
- Includes `NewCardForm`

- `KanbanCard.tsx`
- Sortable draggable card
- Card title/details display
- Remove button

- `KanbanCardPreview.tsx`
- Lightweight drag overlay preview card

- `NewCardForm.tsx`
- Toggleable add-card form
- Validates non-empty title
- Emits `onAdd(title, details)` to parent

## Current Behavior

- Board has fixed count/order of columns in initial state.
- Column titles are editable inline.
- Cards can be added and removed.
- Cards can be reordered within a column and moved across columns.
- All state is currently in-memory only (no backend persistence yet).

## Styling Notes

- Visual tokens are defined in `src/app/globals.css` using CSS variables.
- Theme colors match project palette (`accent-yellow`, `primary-blue`, `secondary-purple`, `navy-dark`, `gray-text`).
- Fonts are loaded in `layout.tsx` with `Space_Grotesk` (display) and `Manrope` (body).

## Existing Tests

Unit/component tests:

- `src/lib/kanban.test.ts`
- Verifies `moveCard` for same-column reorder, cross-column move, and drop-to-column-end behavior.

- `src/components/KanbanBoard.test.tsx`
- Verifies rendering 5 columns, renaming a column, adding/removing a card.

E2E tests:

- `tests/kanban.spec.ts`
- Verifies board load, adding a card, and drag-drop between columns.

## Constraints for Upcoming Integration

- Preserve current board interactions when moving to backend-backed state.
- Preserve Next.js server-side capability in architecture changes.
- Keep UI structure and visual direction unless explicitly changed.
- Add new functionality incrementally with focused tests per change.
