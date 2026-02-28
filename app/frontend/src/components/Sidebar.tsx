import { MessageSquarePlus } from "lucide-react";

type Props = {
  sessionIds: string[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  disabled?: boolean;
};

function sessionLabel(id: string): string {
  return id.length > 20 ? id.slice(0, 17) + "…" : id;
}

export function Sidebar({
  sessionIds,
  activeId,
  onSelect,
  onNewChat,
  disabled,
}: Props) {
  return (
    <aside className="w-56 shrink-0 border-r border-neutral-200 bg-white flex flex-col">
      <div className="p-2">
        <button
          type="button"
          onClick={onNewChat}
          disabled={disabled}
          className="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 disabled:opacity-50"
        >
          <MessageSquarePlus className="w-4 h-4" />
          New chat
        </button>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-2">
        {sessionIds.length === 0 && (
          <p className="text-neutral-500 text-xs px-2 py-1">No chats yet</p>
        )}
        {sessionIds.map((id) => (
          <button
            key={id}
            type="button"
            onClick={() => onSelect(id)}
            disabled={disabled}
            className={`w-full text-left rounded-lg px-3 py-2 text-sm truncate disabled:opacity-50 ${
              id === activeId
                ? "bg-neutral-200 text-neutral-900 font-medium"
                : "text-neutral-600 hover:bg-neutral-100"
            }`}
          >
            {sessionLabel(id)}
          </button>
        ))}
      </div>
    </aside>
  );
}
