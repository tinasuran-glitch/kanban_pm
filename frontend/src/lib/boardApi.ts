import type { BoardData } from "@/lib/kanban";

export const fetchBoard = async (): Promise<BoardData> => {
  const response = await fetch("/api/board", {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Could not load your board.");
  }

  return (await response.json()) as BoardData;
};

export const saveBoard = async (board: BoardData): Promise<void> => {
  const response = await fetch("/api/board", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    keepalive: true,
    body: JSON.stringify(board),
  });

  if (!response.ok) {
    throw new Error("Could not save board changes.");
  }
};
