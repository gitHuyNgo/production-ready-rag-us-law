import { useCallback, useEffect, useRef, useState } from "react";
import { Send, User, Bot, Loader2, AlertCircle, RefreshCw } from "lucide-react";

const STORAGE_KEY = "us-law-chat-history";

type Role = "user" | "agent";

interface Message {
  role: Role;
  content: string;
}

function loadHistory(): Message[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Message[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveHistory(messages: Message[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  } catch {
    // ignore
  }
}

function getWsUrl(): string {
  const env = import.meta.env.VITE_WS_URL;
  if (env) return env;
  const { protocol, hostname } = window.location;
  const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${hostname}:8000/chat/`;
}

export default function App() {
  const [history, setHistory] = useState<Message[]>(() => loadHistory());
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const persist = useCallback((next: Message[]) => {
    setHistory(next);
    saveHistory(next);
  }, []);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [history, streamContent]);

  const ensureConnection = useCallback(() => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) return ws;
    if (ws) {
      ws.close();
      wsRef.current = null;
    }
    const url = getWsUrl();
    const next = new WebSocket(url);
    next.addEventListener("close", () => {
      wsRef.current = null;
      setStreaming(false);
      setStreamContent("");
    });
    wsRef.current = next;
    return next;
  }, []);

  const send = useCallback(() => {
    const text = input.trim();
    if (!text || streaming) return;

    const userMsg: Message = { role: "user", content: text };
    const nextHistory = [...history, userMsg];
    persist(nextHistory);
    setInput("");
    setError(null);
    setStreaming(true);
    setStreamContent("");

    const payload = JSON.stringify({
      history: history.map((m) => ({ role: m.role, content: m.content })),
      role: "user",
      content: text,
    });

    const ws = ensureConnection();
    const historyWithUser = nextHistory;

    const onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data) as {
          t: string;
          content?: string;
          received_content?: string;
          error?: string;
        };
        if (msg.t === "chunk" && typeof msg.content === "string") {
          setStreamContent((prev) => prev + msg.content);
        } else if (msg.t === "done" && typeof msg.received_content === "string") {
          const fullHistory = [...historyWithUser, { role: "agent" as const, content: msg.received_content }];
          persist(fullHistory);
          setStreaming(false);
          setStreamContent("");
          ws.removeEventListener("message", onmessage);
        } else if (msg.t === "error") {
          setError(msg.error ?? "Unknown error");
          setStreaming(false);
          setStreamContent("");
          ws.removeEventListener("message", onmessage);
        }
      } catch {
        setError("Invalid response");
        setStreaming(false);
        ws.removeEventListener("message", onmessage);
      }
    };

    if (ws.readyState === WebSocket.OPEN) {
      ws.addEventListener("message", onmessage);
      ws.send(payload);
      return;
    }

    ws.addEventListener("open", () => {
      ws.send(payload);
    }, { once: true });
    ws.addEventListener("message", onmessage);
    ws.addEventListener("error", () => {
      setError("Connection error");
      setStreaming(false);
      ws.removeEventListener("message", onmessage);
    }, { once: true });
    ws.addEventListener("close", () => {
      wsRef.current = null;
      ws.removeEventListener("message", onmessage);
    }, { once: true });
  }, [history, input, streaming, persist, ensureConnection]);

  const refreshChat = useCallback(() => {
    if (streaming) return;
    setHistory([]);
    setStreamContent("");
    setError(null);
    saveHistory([]);
  }, [streaming]);

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return (
    <div className="h-screen flex flex-col bg-neutral-50 text-neutral-900">
      <header className="shrink-0 border-b border-neutral-200 bg-white px-4 py-3 flex items-center justify-between gap-2">
        <h1 className="text-lg font-semibold tracking-tight">US Law RAG Chat</h1>
        <button
          type="button"
          onClick={refreshChat}
          disabled={streaming}
          className="shrink-0 rounded-lg p-2 text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Refresh chat"
          title="Clear chat"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </header>

      <div
        ref={listRef}
        className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 max-w-3xl w-full mx-auto"
      >
        {history.length === 0 && !streamContent && !error && (
          <p className="text-neutral-500 text-sm">Ask a question about U.S. law. History is saved in this browser.</p>
        )}
        {history.map((m, i) => (
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

      <div className="shrink-0 border-t border-neutral-200 bg-white p-4">
        <div className="max-w-3xl mx-auto flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Ask about U.S. law..."
            className="flex-1 rounded-lg border border-neutral-300 px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-neutral-400 focus:border-transparent"
            disabled={streaming}
          />
          <button
            type="button"
            onClick={send}
            disabled={streaming || !input.trim()}
            className="shrink-0 rounded-lg bg-neutral-800 text-white p-2.5 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-neutral-700 transition-colors"
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
    </div>
  );
}
