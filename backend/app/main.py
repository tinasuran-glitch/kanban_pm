import os
import re
from typing import Annotated, Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from fastapi import FastAPI, HTTPException, Request, Response

from app.ai_client import (
    AIConfigError,
    AIConnectionError,
    AIInvalidResponseError,
    AIProviderError,
    OpenRouterAIClient,
)
from app.board_store import connect_db, get_board, init_db, save_board

app = FastAPI(title="Project Management MVP Backend")
SESSION_COOKIE = "pm_session"
SESSION_VALUE = "mvp-user"
AUTH_USERNAME = "user"
DB_PATH = os.getenv("PM_DB_PATH", "/app/data/pm.db")


class LoginPayload(BaseModel):
    username: str
    password: str


class CardPayload(BaseModel):
    id: str
    title: str
    details: str


class ColumnPayload(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class BoardPayload(BaseModel):
    columns: list[ColumnPayload]
    cards: dict[str, CardPayload]


class ConversationMessagePayload(BaseModel):
    model_config = {"extra": "forbid"}
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Conversation content cannot be empty.")
        return value


class AIChatPayload(BaseModel):
    model_config = {"extra": "forbid"}
    message: str
    conversation: list[ConversationMessagePayload] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be empty.")
        return value


class CreateCardAction(BaseModel):
    model_config = {"extra": "forbid"}
    type: Literal["create_card"]
    columnId: str
    title: str
    details: str = ""

    @field_validator("columnId", "title")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty.")
        return value


class EditCardAction(BaseModel):
    model_config = {"extra": "forbid"}
    type: Literal["edit_card"]
    cardId: str
    title: str | None = None
    details: str | None = None

    @field_validator("cardId")
    @classmethod
    def validate_card_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("cardId cannot be empty.")
        return value

    @model_validator(mode="after")
    def validate_changes_present(self) -> "EditCardAction":
        if self.title is None and self.details is None:
            raise ValueError("edit_card requires title or details.")
        return self


class MoveCardAction(BaseModel):
    model_config = {"extra": "forbid"}
    type: Literal["move_card"]
    cardId: str = Field(validation_alias=AliasChoices("cardId", "card_id"))
    toColumnId: str = Field(
        validation_alias=AliasChoices("toColumnId", "to_column_id", "columnId")
    )
    position: int | None = Field(default=None, ge=0)

    @field_validator("cardId", "toColumnId")
    @classmethod
    def validate_move_fields(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty.")
        return value


class DeleteCardAction(BaseModel):
    model_config = {"extra": "forbid"}
    type: Literal["delete_card"]
    cardId: str

    @field_validator("cardId")
    @classmethod
    def validate_delete_card_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("cardId cannot be empty.")
        return value


class RenameColumnAction(BaseModel):
    model_config = {"extra": "forbid"}
    type: Literal["rename_column"]
    columnId: str
    title: str

    @field_validator("columnId", "title")
    @classmethod
    def validate_rename_fields(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty.")
        return value


BoardAction = Annotated[
    CreateCardAction | EditCardAction | MoveCardAction | DeleteCardAction | RenameColumnAction,
    Field(discriminator="type"),
]


class AIChatResponsePayload(BaseModel):
    model_config = {"extra": "forbid"}
    assistantMessage: str
    actions: list[BoardAction] = Field(default_factory=list)

    @field_validator("assistantMessage")
    @classmethod
    def validate_assistant_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("assistantMessage cannot be empty.")
        return value


def _normalize_action_type(value: Any) -> str:
    text = str(value or "").strip()
    lowered = text.lower()
    mapping = {
        "createcard": "create_card",
        "editcard": "edit_card",
        "movecard": "move_card",
        "deletecard": "delete_card",
        "renamecolumn": "rename_column",
        "create": "create_card",
        "edit": "edit_card",
        "move": "move_card",
        "delete": "delete_card",
        "rename": "rename_column",
    }
    collapsed = lowered.replace("_", "").replace("-", "")
    return mapping.get(collapsed, lowered)


def _infer_card_title_from_message(message: str) -> str | None:
    text = message.strip()
    if not text:
        return None

    patterns = [
        r"\bnamed\s+['\"]?([^'\"]+?)['\"]?(?:\s+in\b|\s+to\b|$)",
        r"\bcalled\s+['\"]?([^'\"]+?)['\"]?(?:\s+in\b|\s+to\b|$)",
        r"\badd\s+(?:a\s+)?card\s+['\"]?([^'\"]+?)['\"]?(?:\s+in\b|\s+to\b|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return candidate

    return None


def _sanitize_action_keys(action: dict[str, Any]) -> dict[str, Any]:
    key_map = {
        "type": "type",
        "cardid": "cardId",
        "card_id": "cardId",
        "cardtitle": "cardTitle",
        "title": "title",
        "name": "title",
        "details": "details",
        "description": "details",
        "columnid": "columnId",
        "column_id": "columnId",
        "column": "column",
        "columntitle": "columnTitle",
        "tocolumn": "toColumn",
        "tocolumnid": "toColumnId",
        "to_column_id": "toColumnId",
        "position": "position",
        "card": "card",
        "id": "id",
    }

    sanitized: dict[str, Any] = {}
    for raw_key, raw_value in action.items():
        cleaned_key = str(raw_key).strip().replace("\u00a0", " ")
        collapsed = re.sub(r"[^a-zA-Z0-9_]+", "", cleaned_key).lower()
        target_key = key_map.get(collapsed)
        if not target_key:
            sanitized[cleaned_key] = raw_value
            continue

        if isinstance(raw_value, str):
            sanitized[target_key] = raw_value.replace("\u00a0", " ").strip()
        else:
            sanitized[target_key] = raw_value

    return sanitized


def _resolve_column_id(board: dict[str, Any], candidate: Any) -> str | None:
    text = str(candidate or "").strip()
    if not text:
        return None

    for column in board["columns"]:
        if text == column["id"]:
            return str(column["id"])

    lowered = text.lower()
    for column in board["columns"]:
        title = str(column.get("title", "")).strip().lower()
        if lowered == title:
            return str(column["id"])

    return None


def _resolve_card_id(board: dict[str, Any], candidate: Any) -> str | None:
    text = str(candidate or "").strip()
    if not text:
        return None

    if text in board["cards"]:
        return text

    lowered = text.lower()
    for card_id, card in board["cards"].items():
        title = str(card.get("title", "")).strip().lower()
        if lowered == title:
            return str(card_id)

    return None


def _find_column_id_from_text(board: dict[str, Any], text: str) -> str | None:
    normalized = text.strip().lower()
    if not normalized:
        return None

    for column in board["columns"]:
        title = str(column.get("title", "")).strip().lower()
        if title and title in normalized:
            return str(column["id"])
    return None


def _normalize_ai_payload(
    raw_result: dict[str, Any],
    *,
    board: dict[str, Any],
    user_message: str,
) -> dict[str, Any]:
    if not isinstance(raw_result, dict):
        return raw_result

    actions = raw_result.get("actions")
    if not isinstance(actions, list):
        return raw_result

    inferred_from_message = _find_column_id_from_text(board, user_message)

    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            continue
        actions[index] = _sanitize_action_keys(action)

    for action in actions:
        if not isinstance(action, dict):
            continue
        action["type"] = _normalize_action_type(action.get("type"))

        action_type = action.get("type")

        if action_type == "create_card":
            nested_card = action.get("card")
            if isinstance(nested_card, dict):
                if "title" not in action and nested_card.get("title"):
                    action["title"] = nested_card.get("title")
                if "details" not in action and "details" in nested_card:
                    action["details"] = nested_card.get("details")
                action.pop("card", None)

            if "title" not in action and action.get("name"):
                action["title"] = action.get("name")

            if "title" not in action:
                inferred_title = _infer_card_title_from_message(user_message)
                if inferred_title:
                    action["title"] = inferred_title

            action.pop("cardId", None)

            if "columnId" in action and str(action["columnId"]).strip():
                resolved = _resolve_column_id(board, action["columnId"])
                if resolved:
                    action["columnId"] = resolved
                continue

            candidate = (
                action.get("column")
                or action.get("columnTitle")
                or action.get("toColumnId")
                or action.get("column_id")
                or inferred_from_message
            )

            resolved_column = _resolve_column_id(board, candidate)
            if resolved_column:
                action["columnId"] = resolved_column
            continue

        if action_type in {"move_card", "edit_card", "delete_card"}:
            if "cardId" not in action:
                candidate_card = (
                    action.get("card")
                    or action.get("cardTitle")
                    or action.get("title")
                    or action.get("id")
                )
                resolved_card = _resolve_card_id(board, candidate_card)
                if resolved_card:
                    action["cardId"] = resolved_card

            action.pop("card", None)
            action.pop("cardTitle", None)
            action.pop("id", None)

            if action_type == "move_card" and (
                "toColumnId" not in action or not str(action.get("toColumnId", "")).strip()
            ):
                candidate_column = (
                    action.get("toColumn")
                    or action.get("column")
                    or action.get("columnTitle")
                    or action.get("to_column_id")
                    or inferred_from_message
                )
                resolved_column = _resolve_column_id(board, candidate_column)
                if resolved_column:
                    action["toColumnId"] = resolved_column

            if action_type == "move_card":
                action.pop("toColumn", None)
                action.pop("column", None)
                action.pop("columnTitle", None)
                action.pop("to_column_id", None)

            continue

        if action_type == "rename_column" and (
            "columnId" not in action or not str(action.get("columnId", "")).strip()
        ):
            candidate_column = (
                action.get("column")
                or action.get("columnTitle")
                or inferred_from_message
            )
            resolved_column = _resolve_column_id(board, candidate_column)
            if resolved_column:
                action["columnId"] = resolved_column

            action.pop("column", None)
            action.pop("columnTitle", None)

    return raw_result


def is_valid_credentials(username: str, password: str) -> bool:
    return username == "user" and password == "password"


def is_authenticated_cookie(cookie_value: str | None) -> bool:
    return cookie_value == SESSION_VALUE


def require_authenticated_username(request: Request) -> str:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not is_authenticated_cookie(cookie):
        raise HTTPException(status_code=401, detail="Authentication required")
    return AUTH_USERNAME


@app.on_event("startup")
def startup() -> None:
    init_db(DB_PATH)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


@app.post("/api/auth/login")
def login(payload: LoginPayload, response: Response) -> dict[str, str]:
    if not is_valid_credentials(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    response.set_cookie(
        key=SESSION_COOKIE,
        value=SESSION_VALUE,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/",
    )
    return {"status": "ok"}


@app.post("/api/auth/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"status": "ok"}


@app.get("/api/auth/session")
def session(request: Request) -> dict[str, bool]:
    session_cookie = request.cookies.get(SESSION_COOKIE)
    return {"authenticated": is_authenticated_cookie(session_cookie)}


@app.get("/api/board")
def read_board(request: Request) -> dict[str, object]:
    username = require_authenticated_username(request)
    with connect_db(DB_PATH) as conn:
        board = get_board(conn, username=username)
    return board


@app.put("/api/board")
def update_board(payload: BoardPayload, request: Request) -> dict[str, object]:
    username = require_authenticated_username(request)
    try:
        with connect_db(DB_PATH) as conn:
            board = save_board(conn, username=username, board=payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return board


@app.get("/api/ai/probe")
def ai_probe(request: Request) -> dict[str, str]:
    require_authenticated_username(request)

    try:
        answer = OpenRouterAIClient().probe()
    except AIConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AIConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"answer": answer}


@app.post("/api/ai/chat")
def ai_chat(payload: AIChatPayload, request: Request) -> dict[str, Any]:
    username = require_authenticated_username(request)
    with connect_db(DB_PATH) as conn:
        board = get_board(conn, username=username)

    conversation = [message.model_dump() for message in payload.conversation]

    try:
        raw_result = OpenRouterAIClient().request_board_actions(
            board=board,
            user_message=payload.message,
            conversation=conversation,
        )
        normalized_result = _normalize_ai_payload(
            raw_result,
            board=board,
            user_message=payload.message,
        )
        response_payload = AIChatResponsePayload.model_validate(normalized_result)
    except AIConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AIConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AIInvalidResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail=f"AI payload failed schema validation: {exc.errors()}") from exc

    return response_payload.model_dump(exclude_none=True)
