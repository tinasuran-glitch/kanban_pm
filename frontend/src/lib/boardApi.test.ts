import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchBoard, saveBoard } from "@/lib/boardApi";
import { initialData } from "@/lib/kanban";

describe("boardApi", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchBoard returns board payload", async () => {
    const mock = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => initialData,
    } as Response);

    const board = await fetchBoard();

    expect(board.columns).toHaveLength(5);
    expect(mock).toHaveBeenCalledWith(
      "/api/board",
      expect.objectContaining({ method: "GET", cache: "no-store" })
    );
  });

  it("fetchBoard throws on non-200", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({ ok: false } as Response);

    await expect(fetchBoard()).rejects.toThrow("Could not load your board.");
  });

  it("saveBoard sends board payload", async () => {
    const mock = vi.spyOn(global, "fetch").mockResolvedValue({ ok: true } as Response);

    await saveBoard(initialData);

    expect(mock).toHaveBeenCalledWith(
      "/api/board",
      expect.objectContaining({ method: "PUT", keepalive: true })
    );
  });

  it("saveBoard throws on non-200", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({ ok: false } as Response);

    await expect(saveBoard(initialData)).rejects.toThrow("Could not save board changes.");
  });
});
