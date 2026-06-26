import { describe, expect, it, vi } from "vitest";
import { applyBoardActions, requestAIChat } from "@/lib/aiApi";
import { initialData } from "@/lib/kanban";

describe("aiApi", () => {
  it("requestAIChat sends payload", async () => {
    const mock = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ assistantMessage: "ok", actions: [] }),
    } as Response);

    const result = await requestAIChat("Move card-1", [
      { role: "user", content: "previous" },
    ]);

    expect(result.assistantMessage).toBe("ok");
    expect(mock).toHaveBeenCalledWith(
      "/api/ai/chat",
      expect.objectContaining({ method: "POST" })
    );

    mock.mockRestore();
  });

  it("applyBoardActions moves and renames", () => {
    const next = applyBoardActions(initialData, [
      {
        type: "rename_column",
        columnId: "col-review",
        title: "Verify",
      },
      {
        type: "move_card",
        cardId: "card-1",
        toColumnId: "col-review",
        position: 0,
      },
    ]);

    const review = next.columns.find((column) => column.id === "col-review");
    const backlog = next.columns.find((column) => column.id === "col-backlog");

    expect(review?.title).toBe("Verify");
    expect(review?.cardIds[0]).toBe("card-1");
    expect(backlog?.cardIds.includes("card-1")).toBe(false);
  });

  it("applyBoardActions appends moved card when position is missing", () => {
    const next = applyBoardActions(initialData, [
      {
        type: "move_card",
        cardId: "card-1",
        toColumnId: "col-review",
      },
    ]);

    const review = next.columns.find((column) => column.id === "col-review");
    expect(review?.cardIds[review.cardIds.length - 1]).toBe("card-1");
  });
});
