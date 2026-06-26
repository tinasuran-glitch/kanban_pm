import { KanbanBoard } from "@/components/KanbanBoard";
import { LogoutButton } from "@/components/LogoutButton";

export default function Home() {
  return (
    <>
      <div className="fixed right-6 top-6 z-50">
        <LogoutButton />
      </div>
      <KanbanBoard />
    </>
  );
}
