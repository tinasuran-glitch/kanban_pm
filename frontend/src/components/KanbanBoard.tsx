"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, moveCard, type BoardData } from "@/lib/kanban";
import { fetchBoard, saveBoard } from "@/lib/boardApi";
import {
  applyBoardActions,
  requestAIChat,
  type BoardAction,
  type ConversationMessage,
} from "@/lib/aiApi";

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatError, setChatError] = useState<string | null>(null);
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [isApplyingAi, setIsApplyingAi] = useState(false);
  const [pendingActions, setPendingActions] = useState<BoardAction[] | null>(null);
  const pendingBoardRef = useRef<BoardData | null>(null);
  const isSavingRef = useRef(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  useEffect(() => {
    const loadBoard = async () => {
      setIsLoading(true);
      setLoadError(null);

      try {
        const payload = await fetchBoard();
        setBoard(payload);
      } catch {
        setLoadError("Could not load saved board. Showing local fallback.");
      } finally {
        setIsLoading(false);
      }
    };

    void loadBoard();
  }, []);

  const persistBoard = async (nextBoard: BoardData) => {
    setSaveError(null);

    try {
      await saveBoard(nextBoard);
    } catch {
      setSaveError("Save failed. Your latest change may not be persisted.");
    }
  };

  const schedulePersist = (nextBoard: BoardData) => {
    pendingBoardRef.current = nextBoard;

    if (isSavingRef.current) {
      return;
    }

    const flush = async () => {
      isSavingRef.current = true;
      try {
        while (pendingBoardRef.current) {
          const boardToSave = pendingBoardRef.current;
          pendingBoardRef.current = null;
          await persistBoard(boardToSave);
        }
      } finally {
        isSavingRef.current = false;
      }
    };

    void flush();
  };

  const updateBoard = (updater: (prev: BoardData) => BoardData) => {
    setBoard((prev) => {
      if (!prev) {
        return prev;
      }
      const next = updater(prev);
      schedulePersist(next);
      return next;
    });
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    updateBoard((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    updateBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    updateBoard((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    updateBoard((prev) => {
      return {
        ...prev,
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => id !== cardId)
        ),
        columns: prev.columns.map((column) =>
          column.id === columnId
            ? {
                ...column,
                cardIds: column.cardIds.filter((id) => id !== cardId),
              }
            : column
        ),
      };
    });
  };

  const handleAskAI = async () => {
    const prompt = chatInput.trim();
    if (!prompt || isAiThinking) {
      return;
    }

    const conversation = messages.slice(-8);

    setChatInput("");
    setChatError(null);
    setIsAiThinking(true);
    setMessages((prev) => [...prev, { role: "user", content: prompt }]);

    try {
      const response = await requestAIChat(prompt, conversation);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.assistantMessage },
      ]);
      setPendingActions(response.actions.length > 0 ? response.actions : null);
    } catch {
      setChatError("AI request failed. Try again.");
    } finally {
      setIsAiThinking(false);
    }
  };

  const handleConfirmAIApply = async () => {
    if (!pendingActions || pendingActions.length === 0 || isApplyingAi || !board) {
      return;
    }

    setIsApplyingAi(true);
    setSaveError(null);

    const nextBoard = applyBoardActions(board, pendingActions);
    setBoard(nextBoard);

    try {
      await saveBoard(nextBoard);
      const refreshed = await fetchBoard();
      setBoard(refreshed);
      setPendingActions(null);
    } catch {
      setSaveError("Save failed. Your latest change may not be persisted.");
      try {
        const fallback = await fetchBoard();
        setBoard(fallback);
      } catch {
        // Keep current board state if refresh also fails.
      }
    } finally {
      setIsApplyingAi(false);
    }
  };

  const handleCancelAIApply = () => {
    setPendingActions(null);
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        {isLoading ? (
          <div className="rounded-2xl border border-[var(--stroke)] bg-white/90 px-4 py-3 text-sm text-[var(--gray-text)]">
            Loading board...
          </div>
        ) : null}
        {loadError ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {loadError}
          </div>
        ) : null}
        {saveError ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {saveError}
          </div>
        ) : null}
        {board ? (
        <>
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6 lg:grid-cols-2 2xl:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <aside className="flex min-h-[640px] flex-col rounded-3xl border border-[var(--stroke)] bg-white/90 p-5 shadow-[var(--shadow)] backdrop-blur">
            <div className="border-b border-[var(--stroke)] pb-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                AI Assistant
              </p>
              <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">
                Suggest Board Changes
              </h2>
              <p className="mt-2 text-sm text-[var(--gray-text)]">
                Ask for edits, review suggestions, then confirm or cancel before apply.
              </p>
            </div>

            <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-1">
              {messages.length === 0 ? (
                <p className="rounded-2xl border border-dashed border-[var(--stroke)] px-3 py-4 text-sm text-[var(--gray-text)]">
                  Try: Move card-1 to Review and rename Review to QA.
                </p>
              ) : null}
              {messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`rounded-2xl px-3 py-3 text-sm leading-6 ${
                    message.role === "user"
                      ? "ml-6 bg-[var(--primary-blue)]/10 text-[var(--navy-dark)]"
                      : "mr-6 border border-[var(--stroke)] bg-white text-[var(--navy-dark)]"
                  }`}
                >
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--gray-text)]">
                    {message.role}
                  </p>
                  {message.content}
                </div>
              ))}
            </div>

            {pendingActions ? (
              <div className="mt-4 rounded-2xl border border-[var(--accent-yellow)]/50 bg-[var(--accent-yellow)]/10 p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--navy-dark)]">
                  Pending Suggestion
                </p>
                <p className="mt-1 text-sm text-[var(--navy-dark)]">
                  {pendingActions.length} action{pendingActions.length === 1 ? "" : "s"} ready to apply.
                </p>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={handleConfirmAIApply}
                    disabled={isApplyingAi}
                    className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isApplyingAi ? "Applying..." : "Confirm apply"}
                  </button>
                  <button
                    type="button"
                    onClick={handleCancelAIApply}
                    disabled={isApplyingAi}
                    className="rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--navy-dark)] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : null}

            {chatError ? (
              <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                {chatError}
              </div>
            ) : null}

            <form
              className="mt-4 space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                void handleAskAI();
              }}
            >
              <textarea
                aria-label="Chat message"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                rows={3}
                placeholder="Describe the change you want..."
                className="w-full resize-none rounded-2xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
              <button
                type="submit"
                disabled={isAiThinking || isApplyingAi || !chatInput.trim()}
                className="w-full rounded-2xl bg-[var(--secondary-purple)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isAiThinking ? "Thinking..." : "Send"}
              </button>
            </form>
          </aside>
        </div>
        </>
        ) : null}
      </main>
    </div>
  );
};
