import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { MessageList } from "../components/MessageList";
import { ChatInput } from "../components/ChatInput";
import { useAuth } from "../hooks/useAuth";
import { useChatSessions } from "../hooks/useChatSessions";
import { useChatWebSocket } from "../hooks/useChatWebSocket";

export default function ChatPage() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [input, setInput] = useState("");

  const {
    sessionIds,
    activeId,
    messages,
    createNewSession,
    selectSession,
    appendUserMessage,
    appendAssistantMessage,
  } = useChatSessions(token);

  const onDone = useCallback(
    (_userContent: string, assistantContent: string) => {
      appendAssistantMessage(assistantContent);
    },
    [appendAssistantMessage]
  );

  const { send, streaming, streamContent, error, closeConnection } =
    useChatWebSocket(activeId, token, onDone);

  useEffect(() => {
    return () => closeConnection();
  }, [closeConnection]);

  const handleLogout = useCallback(() => {
    logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || streaming || !activeId) return;
    setInput("");
    appendUserMessage(text);
    send(messages, text);
  }, [input, streaming, activeId, messages, send, appendUserMessage]);

  const title = activeId
    ? (activeId.length > 24 ? activeId.slice(0, 21) + "…" : activeId)
    : "US Law RAG Chat";

  return (
    <div className="h-screen flex flex-col bg-neutral-50 text-neutral-900">
      <Header
        title={title}
        onToggleSidebar={() => setSidebarOpen((o) => !o)}
        onLogout={handleLogout}
      />
      <div className="flex-1 flex min-h-0">
        {sidebarOpen && (
          <Sidebar
            sessionIds={sessionIds}
            activeId={activeId}
            onSelect={selectSession}
            onNewChat={createNewSession}
            disabled={streaming}
          />
        )}
        <div className="flex-1 flex flex-col min-w-0">
          <MessageList
            messages={messages}
            streamContent={streamContent}
            error={error}
          />
          <ChatInput
            value={input}
            onChange={setInput}
            onSend={handleSend}
            streaming={streaming}
            disabled={!activeId}
          />
        </div>
      </div>
    </div>
  );
}
