from app.board_store import connect_db, get_board, init_db, save_board


def test_get_board_returns_seeded_data(tmp_path) -> None:
    db_path = tmp_path / "pm.db"
    init_db(str(db_path))

    with connect_db(str(db_path)) as conn:
        board = get_board(conn, username="user")

    assert [column["id"] for column in board["columns"]] == [
        "col-backlog",
        "col-discovery",
        "col-progress",
        "col-review",
        "col-done",
    ]
    assert len(board["cards"]) == 8


def test_save_board_persists_changes_across_connections(tmp_path) -> None:
    db_path = tmp_path / "pm.db"
    init_db(str(db_path))

    with connect_db(str(db_path)) as conn:
        board = get_board(conn, username="user")

        board["columns"][0]["title"] = "Ideas"

        card = board["cards"]["card-1"]
        board["cards"]["card-99"] = {
            "id": "card-99",
            "title": "New persisted card",
            "details": "Created in test",
        }

        board["columns"][0]["cardIds"].remove("card-1")
        board["columns"][2]["cardIds"].append("card-1")
        board["columns"][0]["cardIds"].append("card-99")

        card["title"] = "Moved card"

        save_board(conn, username="user", board=board)

    with connect_db(str(db_path)) as conn:
        reloaded = get_board(conn, username="user")

    assert reloaded["columns"][0]["title"] == "Ideas"
    assert "card-99" in reloaded["cards"]
    assert "card-1" in reloaded["columns"][2]["cardIds"]
    assert reloaded["cards"]["card-1"]["title"] == "Moved card"


def test_save_board_rejects_invalid_column_structure(tmp_path) -> None:
    db_path = tmp_path / "pm.db"
    init_db(str(db_path))

    with connect_db(str(db_path)) as conn:
        board = get_board(conn, username="user")
        board["columns"] = board["columns"][1:]

        try:
            save_board(conn, username="user", board=board)
            raise AssertionError("Expected ValueError for invalid column structure")
        except ValueError as exc:
            assert "Column structure is fixed" in str(exc)


def test_save_board_allows_reordering_within_same_column(tmp_path) -> None:
    db_path = tmp_path / "pm.db"
    init_db(str(db_path))

    with connect_db(str(db_path)) as conn:
        board = get_board(conn, username="user")

        progress_column = next(
            column for column in board["columns"] if column["id"] == "col-progress"
        )
        original_ids = progress_column["cardIds"][:]
        progress_column["cardIds"] = [original_ids[1], original_ids[0]]

        save_board(conn, username="user", board=board)

    with connect_db(str(db_path)) as conn:
        reloaded = get_board(conn, username="user")

    reloaded_progress = next(
        column for column in reloaded["columns"] if column["id"] == "col-progress"
    )
    assert reloaded_progress["cardIds"] == [original_ids[1], original_ids[0]]
