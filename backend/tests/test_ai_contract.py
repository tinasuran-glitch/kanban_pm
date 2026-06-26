import pytest
from pydantic import ValidationError

from app.main import AIChatResponsePayload


def test_ai_contract_accepts_valid_payload() -> None:
    payload = {
        "assistantMessage": "I can do that.",
        "actions": [
            {
                "type": "move_card",
                "cardId": "card-1",
                "toColumnId": "col-review",
                "position": 0,
            }
        ],
    }

    validated = AIChatResponsePayload.model_validate(payload)

    assert validated.assistantMessage == "I can do that."
    assert len(validated.actions) == 1


def test_ai_contract_rejects_unknown_action_type() -> None:
    payload = {
        "assistantMessage": "Trying unsupported action.",
        "actions": [
            {
                "type": "archive_card",
                "cardId": "card-1",
            }
        ],
    }

    with pytest.raises(ValidationError):
        AIChatResponsePayload.model_validate(payload)


def test_ai_contract_rejects_missing_edit_fields() -> None:
    payload = {
        "assistantMessage": "I can edit this card.",
        "actions": [
            {
                "type": "edit_card",
                "cardId": "card-1",
            }
        ],
    }

    with pytest.raises(ValidationError):
        AIChatResponsePayload.model_validate(payload)


def test_ai_contract_allows_move_card_without_position() -> None:
    payload = {
        "assistantMessage": "I moved the card.",
        "actions": [
            {
                "type": "move_card",
                "cardId": "card-1",
                "toColumnId": "col-review",
            }
        ],
    }

    validated = AIChatResponsePayload.model_validate(payload)

    assert validated.actions[0].type == "move_card"
