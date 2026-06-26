from types import SimpleNamespace
import json

import pytest

from app.ai_client import (
    AIConfigError,
    AIInvalidResponseError,
    AIProviderError,
    OpenRouterAIClient,
)


class FakeCompletions:
    def __init__(self) -> None:
        self.last_create_kwargs = None

    def create(self, **kwargs):
        self.last_create_kwargs = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="4"),
                )
            ]
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())


def test_probe_builds_expected_request(monkeypatch) -> None:
    fake_client = FakeOpenAIClient()

    def fake_openai(*, base_url: str, api_key: str):
        assert base_url == "https://openrouter.ai/api/v1"
        assert api_key == "test-key"
        return fake_client

    monkeypatch.setattr("app.ai_client.OpenAI", fake_openai)

    client = OpenRouterAIClient(api_key="test-key")
    answer = client.probe()

    assert answer == "4"
    assert fake_client.chat.completions.last_create_kwargs == {
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": "2+2"}],
    }


def test_probe_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    client = OpenRouterAIClient(api_key=None)

    with pytest.raises(AIConfigError, match="OPENROUTER_API_KEY"):
        client.probe()


def test_probe_rejects_empty_response(monkeypatch) -> None:
    class EmptyResponseClient:
        def __init__(self) -> None:
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content="   "))]
                    )
                )
            )

    monkeypatch.setattr(
        "app.ai_client.OpenAI",
        lambda **kwargs: EmptyResponseClient(),
    )

    client = OpenRouterAIClient(api_key="test-key")

    with pytest.raises(AIProviderError, match="empty response"):
        client.probe()


def test_request_board_actions_builds_expected_request(monkeypatch) -> None:
    fake_client = FakeOpenAIClient()

    def fake_openai(*, base_url: str, api_key: str):
        assert base_url == "https://openrouter.ai/api/v1"
        assert api_key == "test-key"
        return fake_client

    monkeypatch.setattr("app.ai_client.OpenAI", fake_openai)

    def create_json_response(**kwargs):
        fake_client.chat.completions.last_create_kwargs = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"assistantMessage":"Done","actions":[]}'
                    )
                )
            ]
        )

    fake_client.chat.completions.create = create_json_response

    client = OpenRouterAIClient(api_key="test-key")
    result = client.request_board_actions(
        board={"columns": [], "cards": {}},
        user_message="Move card-1",
        conversation=[{"role": "user", "content": "Move it"}],
    )

    assert result == {"assistantMessage": "Done", "actions": []}
    sent = fake_client.chat.completions.last_create_kwargs
    assert sent["model"] == "openai/gpt-oss-120b"
    assert sent["response_format"] == {"type": "json_object"}
    user_content = sent["messages"][1]["content"]
    parsed_user_content = json.loads(user_content)
    assert parsed_user_content["message"] == "Move card-1"
    assert parsed_user_content["conversation"] == [{"role": "user", "content": "Move it"}]
    assert parsed_user_content["board"] == {"columns": [], "cards": {}}


def test_request_board_actions_rejects_invalid_json(monkeypatch) -> None:
    class InvalidJsonClient:
        def __init__(self) -> None:
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))]
                    )
                )
            )

    monkeypatch.setattr("app.ai_client.OpenAI", lambda **kwargs: InvalidJsonClient())

    client = OpenRouterAIClient(api_key="test-key")

    with pytest.raises(AIInvalidResponseError, match="invalid JSON"):
        client.request_board_actions(
            board={"columns": [], "cards": {}},
            user_message="Move card-1",
            conversation=[],
        )
