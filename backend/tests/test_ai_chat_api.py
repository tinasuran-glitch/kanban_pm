from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main


def _client(tmp_path: Path) -> TestClient:
    app_main.DB_PATH = str(tmp_path / "pm.db")
    app_main.init_db(app_main.DB_PATH)
    return TestClient(app_main.app)


def _auth_cookies() -> dict[str, str]:
    return {app_main.SESSION_COOKIE: app_main.SESSION_VALUE}


def test_ai_chat_requires_authentication(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/api/ai/chat",
        json={"message": "Move card-1 to review", "conversation": []},
    )

    assert response.status_code == 401


def test_ai_chat_accepts_valid_action_response(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)

    class FakeAIClient:
        def request_board_actions(self, **kwargs):
            assert "board" in kwargs
            assert kwargs["user_message"] == "Move card-1 to review"
            assert kwargs["conversation"] == [
                {"role": "user", "content": "Please move card-1"}
            ]
            return {
                "assistantMessage": "I can move that card.",
                "actions": [
                    {
                        "type": "move_card",
                        "cardId": "card-1",
                        "toColumnId": "col-review",
                        "position": 0,
                    }
                ],
            }

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.post(
        "/api/ai/chat",
        cookies=_auth_cookies(),
        json={
            "message": "Move card-1 to review",
            "conversation": [{"role": "user", "content": "Please move card-1"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistantMessage"] == "I can move that card."
    assert payload["actions"][0]["type"] == "move_card"


def test_ai_chat_noop_response(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)

    class FakeAIClient:
        def request_board_actions(self, **kwargs):
            return {
                "assistantMessage": "No board change needed.",
                "actions": [],
            }

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.post(
        "/api/ai/chat",
        cookies=_auth_cookies(),
        json={"message": "Any updates?", "conversation": []},
    )

    assert response.status_code == 200
    assert response.json() == {
        "assistantMessage": "No board change needed.",
        "actions": [],
    }


def test_ai_chat_rejects_invalid_payload_and_preserves_board(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    cookies = _auth_cookies()

    before = client.get("/api/board", cookies=cookies)
    assert before.status_code == 200
    board_before = before.json()

    class FakeAIClient:
        def request_board_actions(self, **kwargs):
            return {
                "assistantMessage": "Trying malformed action.",
                "actions": [
                    {
                        "type": "move_card",
                        "cardId": "card-1",
                    }
                ],
            }

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.post(
        "/api/ai/chat",
        cookies=cookies,
        json={"message": "Move card-1", "conversation": []},
    )

    assert response.status_code == 502
    assert "schema validation" in response.json()["detail"]

    after = client.get("/api/board", cookies=cookies)
    assert after.status_code == 200
    assert after.json() == board_before


def test_ai_chat_normalizes_create_card_missing_column_id(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)

    class FakeAIClient:
        def request_board_actions(self, **kwargs):
            return {
                "assistantMessage": "Added a card.",
                "actions": [
                    {
                        "type": "create_card",
                        "cardId": "card-9",
                        "title": "hello",
                        "details": "",
                    }
                ],
            }

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.post(
        "/api/ai/chat",
        cookies=_auth_cookies(),
        json={"message": "add a card named hello in Done", "conversation": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["actions"][0]["type"] == "create_card"
    assert payload["actions"][0]["columnId"] == "col-done"
    assert "cardId" not in payload["actions"][0]


def test_ai_chat_normalizes_create_card_with_nested_card_object(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)

    class FakeAIClient:
        def request_board_actions(self, **kwargs):
            return {
                "assistantMessage": "Added a card.",
                "actions": [
                    {
                        "type": "create_card",
                        "card": {
                            "id": "card-9",
                            "title": "hello",
                            "details": "",
                        },
                    }
                ],
            }

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.post(
        "/api/ai/chat",
        cookies=_auth_cookies(),
        json={"message": "add a card named hello in Done", "conversation": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["actions"][0]["type"] == "create_card"
    assert payload["actions"][0]["columnId"] == "col-done"
    assert payload["actions"][0]["title"] == "hello"
    assert payload["actions"][0]["details"] == ""
    assert "card" not in payload["actions"][0]


def test_ai_chat_normalizes_move_card_with_titles(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)

    class FakeAIClient:
        def request_board_actions(self, **kwargs):
            return {
                "assistantMessage": "Moved the card to Discovery.",
                "actions": [
                    {
                        "type": "moveCard",
                        "card": "Align roadmap themes",
                        "toColumn": "Discovery",
                    }
                ],
            }

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.post(
        "/api/ai/chat",
        cookies=_auth_cookies(),
        json={"message": "move Align roadmap themes to Discovery", "conversation": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["actions"][0]["type"] == "move_card"
    assert payload["actions"][0]["cardId"] == "card-1"
    assert payload["actions"][0]["toColumnId"] == "col-discovery"


def test_ai_chat_normalizes_malformed_create_card_keys(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)

    class FakeAIClient:
        def request_board_actions(self, **kwargs):
            return {
                "assistantMessage": "Added card.",
                "actions": [
                    {
                        "type": "create_card",
                        "cardId:": "\u00a0\u00a0",
                        "columnId": "col-done",
                    }
                ],
            }

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.post(
        "/api/ai/chat",
        cookies=_auth_cookies(),
        json={"message": "add a card named hello in Done", "conversation": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["actions"][0]["type"] == "create_card"
    assert payload["actions"][0]["columnId"] == "col-done"
    assert payload["actions"][0]["title"] == "hello"
