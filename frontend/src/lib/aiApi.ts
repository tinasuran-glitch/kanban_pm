import type { BoardData } from "@/lib/kanban";
import { createId } from "@/lib/kanban";

export type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
};

export type CreateCardAction = {
  type: "create_card";
  columnId: string;
  title: string;
  details: string;
};

export type EditCardAction = {
  type: "edit_card";
  cardId: string;
  title?: string;
  details?: string;
};

export type MoveCardAction = {
  type: "move_card";
  cardId: string;
  toColumnId: string;
  position?: number;
};

export type DeleteCardAction = {
  type: "delete_card";
  cardId: string;
};

export type RenameColumnAction = {
  type: "rename_column";
  columnId: string;
  title: string;
};

export type BoardAction =
  | CreateCardAction
  | EditCardAction
  | MoveCardAction
  | DeleteCardAction
  | RenameColumnAction;

export type AIChatResponse = {
  assistantMessage: string;
  actions: BoardAction[];
};

export const requestAIChat = async (
  message: string,
  conversation: ConversationMessage[]
): Promise<AIChatResponse> => {
  const response = await fetch("/api/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation }),
  });

  if (!response.ok) {
    throw new Error("Could not get AI response.");
  }

  return (await response.json()) as AIChatResponse;
};

const clampIndex = (value: number, length: number): number => {
  if (value < 0) {
    return 0;
  }
  if (value > length) {
    return length;
  }
  return value;
};

export const applyBoardActions = (
  board: BoardData,
  actions: BoardAction[]
): BoardData => {
  let next: BoardData = {
    columns: board.columns.map((column) => ({ ...column, cardIds: [...column.cardIds] })),
    cards: Object.fromEntries(
      Object.entries(board.cards).map(([id, card]) => [id, { ...card }])
    ),
  };

  for (const action of actions) {
    if (action.type === "create_card") {
      const column = next.columns.find((candidate) => candidate.id === action.columnId);
      if (!column) {
        continue;
      }
      const id = createId("card");
      next.cards[id] = {
        id,
        title: action.title,
        details: action.details || "No details yet.",
      };
      column.cardIds.push(id);
      continue;
    }

    if (action.type === "edit_card") {
      const card = next.cards[action.cardId];
      if (!card) {
        continue;
      }
      next.cards[action.cardId] = {
        ...card,
        title: action.title ?? card.title,
        details: action.details ?? card.details,
      };
      continue;
    }

    if (action.type === "move_card") {
      const sourceColumn = next.columns.find((column) =>
        column.cardIds.includes(action.cardId)
      );
      const targetColumn = next.columns.find(
        (column) => column.id === action.toColumnId
      );

      if (!sourceColumn || !targetColumn) {
        continue;
      }

      sourceColumn.cardIds = sourceColumn.cardIds.filter(
        (id) => id !== action.cardId
      );
      const requestedPosition =
        typeof action.position === "number"
          ? action.position
          : targetColumn.cardIds.length;
      const insertAt = clampIndex(requestedPosition, targetColumn.cardIds.length);
      targetColumn.cardIds.splice(insertAt, 0, action.cardId);
      continue;
    }

    if (action.type === "delete_card") {
      if (!next.cards[action.cardId]) {
        continue;
      }
      const { [action.cardId]: _deleted, ...rest } = next.cards;
      next.cards = rest;
      next.columns = next.columns.map((column) => ({
        ...column,
        cardIds: column.cardIds.filter((id) => id !== action.cardId),
      }));
      continue;
    }

    if (action.type === "rename_column") {
      next.columns = next.columns.map((column) =>
        column.id === action.columnId
          ? { ...column, title: action.title.trim() || column.title }
          : column
      );
    }
  }

  return next;
};
