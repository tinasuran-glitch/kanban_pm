import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const method = init?.method ?? "GET";

    if (method === "GET") {
      return {
        ok: true,
        json: async () => initialData,
      } as Response;
    }

    return {
      ok: true,
      json: async () => ({}),
    } as Response;
  });

  beforeEach(() => {
    vi.spyOn(global, "fetch").mockImplementation(fetchMock);
  });

  afterEach(() => {
    fetchMock.mockClear();
    vi.restoreAllMocks();
  });

  const renderBoard = async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);
  };

  const hasPutCall = () =>
    fetchMock.mock.calls.some(([, init]) => (init?.method ?? "GET") === "PUT");

  it("loads board from backend", async () => {
    await renderBoard();

    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/board",
      expect.objectContaining({ method: "GET", cache: "no-store" })
    );
  });

  it("renames a column", async () => {
    await renderBoard();
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    await userEvent.tab();

    expect(input).toHaveValue("New Name");
    await waitFor(() => expect(hasPutCall()).toBe(true));
  });

  it("adds and removes a card", async () => {
    await renderBoard();
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();
    await waitFor(() => expect(hasPutCall()).toBe(true));

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
    await waitFor(() => expect(hasPutCall()).toBe(true));
  });

  it("shows pending AI suggestion and cancels with no board save", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const url = String(input);

      if (url === "/api/ai/chat" && method === "POST") {
        return {
          ok: true,
          json: async () => ({
            assistantMessage: "I can rename Review.",
            actions: [
              { type: "rename_column", columnId: "col-review", title: "QA" },
            ],
          }),
        } as Response;
      }

      if (url === "/api/board" && method === "GET") {
        return {
          ok: true,
          json: async () => initialData,
        } as Response;
      }

      return {
        ok: true,
        json: async () => ({}),
      } as Response;
    });

    await renderBoard();

    await userEvent.type(screen.getByLabelText("Chat message"), "Rename review to QA");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    await screen.findByText("Pending Suggestion");
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByText("Pending Suggestion")).not.toBeInTheDocument();
    const putCalls = fetchMock.mock.calls.filter(
      ([input, init]) => String(input) === "/api/board" && (init?.method ?? "GET") === "PUT"
    );
    expect(putCalls).toHaveLength(0);
  });

  it("confirms AI suggestion and applies board changes", async () => {
    const boardAfterApply = {
      ...initialData,
      columns: initialData.columns.map((column) =>
        column.id === "col-review" ? { ...column, title: "QA" } : column
      ),
    };

    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const url = String(input);

      if (url === "/api/ai/chat" && method === "POST") {
        return {
          ok: true,
          json: async () => ({
            assistantMessage: "Ready to rename Review.",
            actions: [
              { type: "rename_column", columnId: "col-review", title: "QA" },
            ],
          }),
        } as Response;
      }

      if (url === "/api/board" && method === "GET") {
        const hasSaved = fetchMock.mock.calls.some(
          ([calledUrl, calledInit]) =>
            String(calledUrl) === "/api/board" && (calledInit?.method ?? "GET") === "PUT"
        );
        return {
          ok: true,
          json: async () => (hasSaved ? boardAfterApply : initialData),
        } as Response;
      }

      if (url === "/api/board" && method === "PUT") {
        return {
          ok: true,
          json: async () => ({}),
        } as Response;
      }

      return {
        ok: true,
        json: async () => ({}),
      } as Response;
    });

    await renderBoard();

    await userEvent.type(screen.getByLabelText("Chat message"), "Rename review to QA");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("Pending Suggestion");

    await userEvent.click(screen.getByRole("button", { name: "Confirm apply" }));

    await waitFor(() => {
      const putCalls = fetchMock.mock.calls.filter(
        ([input, init]) =>
          String(input) === "/api/board" && (init?.method ?? "GET") === "PUT"
      );
      expect(putCalls).toHaveLength(1);

      const [, putInit] = putCalls[0];
      const payload = JSON.parse(String(putInit?.body));
      const reviewColumn = payload.columns.find(
        (column: { id: string; title: string }) => column.id === "col-review"
      );
      expect(reviewColumn.title).toBe("QA");
    });

    expect(screen.queryByText("Pending Suggestion")).not.toBeInTheDocument();
  });
});
