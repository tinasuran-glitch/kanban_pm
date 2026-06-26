from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main


def _client(tmp_path: Path) -> TestClient:
    app_main.DB_PATH = str(tmp_path / "pm.db")
    return TestClient(app_main.app)


def test_ai_probe_requires_authentication(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/ai/probe")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_ai_probe_returns_answer_text(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)

    class FakeAIClient:
        def probe(self) -> str:
            return "4"

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.get(
        "/api/ai/probe",
        cookies={app_main.SESSION_COOKIE: app_main.SESSION_VALUE},
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "4"}


def test_ai_probe_maps_config_error(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)

    class FakeAIClient:
        def probe(self) -> str:
            raise app_main.AIConfigError("OPENROUTER_API_KEY is not configured")

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.get(
        "/api/ai/probe",
        cookies={app_main.SESSION_COOKIE: app_main.SESSION_VALUE},
    )

    assert response.status_code == 500


def test_ai_probe_maps_connection_error(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)

    class FakeAIClient:
        def probe(self) -> str:
            raise app_main.AIConnectionError("Unable to reach AI provider")

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.get(
        "/api/ai/probe",
        cookies={app_main.SESSION_COOKIE: app_main.SESSION_VALUE},
    )

    assert response.status_code == 503


def test_ai_probe_maps_provider_error(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)

    class FakeAIClient:
        def probe(self) -> str:
            raise app_main.AIProviderError("AI provider returned an error response")

    monkeypatch.setattr(app_main, "OpenRouterAIClient", lambda: FakeAIClient())

    response = client.get(
        "/api/ai/probe",
        cookies={app_main.SESSION_COOKIE: app_main.SESSION_VALUE},
    )

    assert response.status_code == 502
