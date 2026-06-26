from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_COLUMNS = [
    ("col-backlog", "backlog", "Backlog"),
    ("col-discovery", "discovery", "Discovery"),
    ("col-progress", "progress", "In Progress"),
    ("col-review", "review", "Review"),
    ("col-done", "done", "Done"),
]

SEED_CARDS = [
    {
        "id": "card-1",
        "title": "Align roadmap themes",
        "details": "Draft quarterly themes with impact statements and metrics.",
        "column_id": "col-backlog",
    },
    {
        "id": "card-2",
        "title": "Gather customer signals",
        "details": "Review support tags, sales notes, and churn feedback.",
        "column_id": "col-backlog",
    },
    {
        "id": "card-3",
        "title": "Prototype analytics view",
        "details": "Sketch initial dashboard layout and key drill-downs.",
        "column_id": "col-discovery",
    },
    {
        "id": "card-4",
        "title": "Refine status language",
        "details": "Standardize column labels and tone across the board.",
        "column_id": "col-progress",
    },
    {
        "id": "card-5",
        "title": "Design card layout",
        "details": "Add hierarchy and spacing for scanning dense lists.",
        "column_id": "col-progress",
    },
    {
        "id": "card-6",
        "title": "QA micro-interactions",
        "details": "Verify hover, focus, and loading states.",
        "column_id": "col-review",
    },
    {
        "id": "card-7",
        "title": "Ship marketing page",
        "details": "Final copy approved and asset pack delivered.",
        "column_id": "col-done",
    },
    {
        "id": "card-8",
        "title": "Close onboarding sprint",
        "details": "Document release notes and share internally.",
        "column_id": "col-done",
    },
]

EXPECTED_COLUMN_IDS = [column_id for column_id, _, _ in DEFAULT_COLUMNS]


def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect_db(db_path) as conn:
        create_schema(conn)
        seed_default_data(conn)


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS boards (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL DEFAULT 'Default Board',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS columns (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
          column_id TEXT NOT NULL,
          key TEXT NOT NULL,
          title TEXT NOT NULL,
          position INTEGER NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(board_id, column_id),
          UNIQUE(board_id, key),
          UNIQUE(board_id, position)
        );

        CREATE TABLE IF NOT EXISTS cards (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          board_id INTEGER NOT NULL,
          card_id TEXT NOT NULL,
          column_id TEXT NOT NULL,
          title TEXT NOT NULL,
          details TEXT NOT NULL DEFAULT '',
          position INTEGER NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (board_id, column_id)
            REFERENCES columns(board_id, column_id)
            ON DELETE CASCADE,
          UNIQUE(board_id, card_id),
          UNIQUE(board_id, column_id, position)
        );

        CREATE INDEX IF NOT EXISTS idx_columns_board_position
          ON columns(board_id, position);

        CREATE INDEX IF NOT EXISTS idx_cards_board_column_position
          ON cards(board_id, column_id, position);
        """
    )


def seed_default_data(conn: sqlite3.Connection) -> None:
    user_id = _get_or_create_user(conn, username="user")
    board_id = _get_or_create_board(conn, user_id=user_id)

    for position, (column_id, key, title) in enumerate(DEFAULT_COLUMNS):
        conn.execute(
            """
            INSERT INTO columns (board_id, column_id, key, title, position)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(board_id, column_id)
            DO UPDATE SET key = excluded.key
            """,
            (board_id, column_id, key, title, position),
        )

    cards_count = conn.execute(
        "SELECT COUNT(*) AS count FROM cards WHERE board_id = ?", (board_id,)
    ).fetchone()["count"]
    if cards_count > 0:
        return

    per_column_position: dict[str, int] = {}
    for card in SEED_CARDS:
        next_pos = per_column_position.get(card["column_id"], 0)
        per_column_position[card["column_id"]] = next_pos + 1
        conn.execute(
            """
            INSERT INTO cards (board_id, card_id, column_id, title, details, position)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                board_id,
                card["id"],
                card["column_id"],
                card["title"],
                card["details"],
                next_pos,
            ),
        )


def get_board(conn: sqlite3.Connection, username: str) -> dict[str, Any]:
    board_id = _get_board_id(conn, username)

    columns_rows = conn.execute(
        """
        SELECT column_id, title
        FROM columns
        WHERE board_id = ?
        ORDER BY position
        """,
        (board_id,),
    ).fetchall()

    cards_rows = conn.execute(
        """
        SELECT card_id, column_id, title, details
        FROM cards
        WHERE board_id = ?
        ORDER BY column_id, position
        """,
        (board_id,),
    ).fetchall()

    cards: dict[str, dict[str, str]] = {}
    cards_by_column: dict[str, list[str]] = {row["column_id"]: [] for row in columns_rows}

    for row in cards_rows:
        card_id = row["card_id"]
        cards[card_id] = {
            "id": card_id,
            "title": row["title"],
            "details": row["details"],
        }
        cards_by_column.setdefault(row["column_id"], []).append(card_id)

    columns = [
        {
            "id": row["column_id"],
            "title": row["title"],
            "cardIds": cards_by_column.get(row["column_id"], []),
        }
        for row in columns_rows
    ]

    return {"columns": columns, "cards": cards}


def save_board(conn: sqlite3.Connection, username: str, board: dict[str, Any]) -> dict[str, Any]:
    _validate_board_payload(board)
    board_id = _get_board_id(conn, username)

    columns: list[dict[str, Any]] = board["columns"]
    cards: dict[str, dict[str, str]] = board["cards"]

    card_to_column_and_position: dict[str, tuple[str, int]] = {}
    for column in columns:
        column_id = column["id"]
        for idx, card_id in enumerate(column["cardIds"]):
            card_to_column_and_position[card_id] = (column_id, idx)

    with conn:
        for position, column in enumerate(columns):
            conn.execute(
                """
                UPDATE columns
                SET title = ?, position = ?, updated_at = CURRENT_TIMESTAMP
                WHERE board_id = ? AND column_id = ?
                """,
                (column["title"].strip(), position, board_id, column["id"]),
            )

        # Rebuild card rows from the incoming payload to avoid transient
        # unique-position conflicts when cards are reordered.
        conn.execute("DELETE FROM cards WHERE board_id = ?", (board_id,))

        for card_id, card in cards.items():
            column_id, position = card_to_column_and_position[card_id]
            conn.execute(
                """
                INSERT INTO cards (board_id, card_id, column_id, title, details, position)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    board_id,
                    card_id,
                    column_id,
                    card["title"].strip(),
                    card["details"].strip(),
                    position,
                ),
            )

    return get_board(conn, username)


def _validate_board_payload(board: dict[str, Any]) -> None:
    if "columns" not in board or "cards" not in board:
        raise ValueError("Invalid board payload.")

    columns = board["columns"]
    cards = board["cards"]

    if not isinstance(columns, list) or not isinstance(cards, dict):
        raise ValueError("Invalid board payload types.")

    column_ids = [column.get("id") for column in columns]
    if column_ids != EXPECTED_COLUMN_IDS:
        raise ValueError("Column structure is fixed for MVP.")

    seen_card_ids: set[str] = set()
    for column in columns:
        title = str(column.get("title", "")).strip()
        if not title:
            raise ValueError("Column title cannot be empty.")

        card_ids = column.get("cardIds", [])
        if not isinstance(card_ids, list):
            raise ValueError("cardIds must be an array.")

        for card_id in card_ids:
            if card_id in seen_card_ids:
                raise ValueError("Card ids must be unique across columns.")
            if card_id not in cards:
                raise ValueError("Each cardId must exist in cards map.")
            seen_card_ids.add(card_id)

    if set(cards.keys()) != seen_card_ids:
        raise ValueError("All cards must be assigned to exactly one column.")

    for card_id, card in cards.items():
        if card.get("id") != card_id:
            raise ValueError("Card id mismatch in cards map.")
        if not str(card.get("title", "")).strip():
            raise ValueError("Card title cannot be empty.")
        if "details" not in card:
            raise ValueError("Card details is required.")


def _get_or_create_user(conn: sqlite3.Connection, username: str) -> int:
    conn.execute(
        "INSERT INTO users (username) VALUES (?) ON CONFLICT(username) DO NOTHING",
        (username,),
    )
    row = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return int(row["id"])


def _get_or_create_board(conn: sqlite3.Connection, user_id: int) -> int:
    conn.execute(
        "INSERT INTO boards (user_id) VALUES (?) ON CONFLICT(user_id) DO NOTHING",
        (user_id,),
    )
    row = conn.execute(
        "SELECT id FROM boards WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return int(row["id"])


def _get_board_id(conn: sqlite3.Connection, username: str) -> int:
    row = conn.execute(
        """
        SELECT b.id AS board_id
        FROM boards b
        JOIN users u ON u.id = b.user_id
        WHERE u.username = ?
        """,
        (username,),
    ).fetchone()
    if row is None:
        raise ValueError("Board not found for user.")
    return int(row["board_id"])
