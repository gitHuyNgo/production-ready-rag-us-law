import { useRef, useEffect } from "react";
import { User, Bot, AlertCircle } from "lucide-react";
import type { ChatMessage } from "../services/chatApi";

type Props = {
  messages: ChatMessage[];
  streamContent: string;
  error: string | null;
};

export function MessageList({ messages, streamContent, error }: Props) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, streamContent]);

  return (
    <div
      ref={listRef}
      className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 max-w-3xl w-full mx-auto"
    >
      {messages.length === 0 && !streamContent && !error && (
        <p className="text-neutral-500 text-sm">
          Ask a question about U.S. law. Type below to start.
        </p>
      )}
      {messages.map((m, i) => (
        <div
          key={i}
          className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}
        >
          {m.role === "agent" && (
            <div className="shrink-0 w-8 h-8 rounded-full bg-neutral-200 flex items-center justify-center">
              <Bot className="w-4 h-4 text-neutral-600" />
            </div>
          )}
          <div
            className={`rounded-lg px-4 py-2 max-w-[85%] sm:max-w-[75%] ${
              m.role === "user"
                ? "bg-neutral-800 text-white"
                : "bg-white border border-neutral-200 text-neutral-900"
            }`}
          >
            <p className="text-sm whitespace-pre-wrap break-words">{m.content}</p>
          </div>
          {m.role === "user" && (
            <div className="shrink-0 w-8 h-8 rounded-full bg-neutral-800 flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
          )}
        </div>
      ))}
      {streamContent && (
        <div className="flex gap-3 justify-start">
          <div className="shrink-0 w-8 h-8 rounded-full bg-neutral-200 flex items-center justify-center">
            <Bot className="w-4 h-4 text-neutral-600" />
          </div>
          <div className="rounded-lg px-4 py-2 bg-white border border-neutral-200 max-w-[85%] sm:max-w-[75%]">
            <p className="text-sm whitespace-pre-wrap break-words">
              {streamContent}
              <span className="inline-block w-2 h-4 bg-neutral-400 animate-pulse ml-0.5 align-middle" aria-hidden />
            </p>
          </div>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}
    </div>
  );
}
