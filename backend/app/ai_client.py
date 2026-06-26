from __future__ import annotations

import json
import os
from typing import Any

from openai import APIConnectionError, APIStatusError, OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "openai/gpt-oss-120b"


class AIConfigError(Exception):
    pass


class AIConnectionError(Exception):
    pass


class AIProviderError(Exception):
    pass


class AIInvalidResponseError(Exception):
    pass


class OpenRouterAIClient:
    def __init__(self, api_key: str | None = None, model: str = OPENROUTER_MODEL) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model

    def probe(self) -> str:
        if not self.api_key:
            raise AIConfigError("OPENROUTER_API_KEY is not configured")

        client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=self.api_key)

        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": "2+2",
                    }
                ],
            )
        except APIConnectionError as exc:
            raise AIConnectionError("Unable to reach AI provider") from exc
        except APIStatusError as exc:
            raise AIProviderError("AI provider returned an error response") from exc

        message = completion.choices[0].message.content if completion.choices else None
        text = (message or "").strip()
        if not text:
            raise AIProviderError("AI provider returned an empty response")

        return text

    def request_board_actions(
        self,
        *,
        board: dict[str, Any],
        user_message: str,
        conversation: list[dict[str, str]],
    ) -> dict[str, Any]:
        if not self.api_key:
            raise AIConfigError("OPENROUTER_API_KEY is not configured")

        client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=self.api_key)

        system_prompt = (
            "You are an assistant for a kanban board. "
            "Return strict JSON only with fields assistantMessage (string) "
            "and actions (array). "
            "Each action must use one of these types: "
            "create_card, edit_card, move_card, delete_card, rename_column. "
            "Do not return markdown or extra keys."
        )
        payload = {
            "message": user_message,
            "conversation": conversation,
            "board": board,
        }

        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(payload, separators=(",", ":")),
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=220,
            )
        except APIConnectionError as exc:
            raise AIConnectionError("Unable to reach AI provider") from exc
        except APIStatusError as exc:
            raise AIProviderError("AI provider returned an error response") from exc

        message = completion.choices[0].message.content if completion.choices else None
        text = (message or "").strip()
        if not text:
            raise AIProviderError("AI provider returned an empty response")

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIInvalidResponseError("AI provider returned invalid JSON") from exc
