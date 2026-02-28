import { Send, Loader2 } from "lucide-react";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  streaming: boolean;
  disabled?: boolean;
};

export function ChatInput({
  value,
  onChange,
  onSend,
  streaming,
  disabled,
}: Props) {
  return (
    <div className="shrink-0 border-t border-neutral-200 bg-white p-4">
      <div className="max-w-3xl mx-auto flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && onSend()}
          placeholder="Ask about U.S. law..."
          className="flex-1 rounded-lg border border-neutral-300 px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-neutral-400 focus:border-transparent"
          disabled={streaming || disabled}
        />
        <button
          type="button"
          onClick={onSend}
          disabled={streaming || !value.trim() || disabled}
          className="shrink-0 rounded-lg bg-neutral-800 text-white p-2.5 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-neutral-700"
          aria-label="Send"
        >
          {streaming ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>
    </div>
  );
}
