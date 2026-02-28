import { useCallback, useEffect, useState } from "react";
import * as chatApi from "../services/chatApi";
import type { ChatMessage } from "../services/chatApi";

function generateSessionId(): string {
  return `s-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

export function useChatSessions(token: string | null) {
  const [sessionIds, setSessionIds] = useState<string[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const loadSessions = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const ids = await chatApi.fetchSessions(token);
      setSessionIds(ids);
      if (ids.length > 0) {
        setActiveId((current) => current ?? ids[0]);
      } else {
        // ChatGPT-style: ensure one session so user can chat without clicking "New chat"
        const newId = generateSessionId();
        setSessionIds([newId]);
        setActiveId(newId);
        setMessages([]);
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  const loadMessages = useCallback(
    async (sessionId: string) => {
      if (!sessionId) return;
      setLoading(true);
      try {
        const list = await chatApi.fetchMessages(sessionId, token);
        setMessages(list);
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    if (activeId) loadMessages(activeId);
    else setMessages([]);
  }, [activeId, loadMessages]);

  const createNewSession = useCallback(() => {
    const id = generateSessionId();
    setSessionIds((prev) => [id, ...prev]);
    setActiveId(id);
    setMessages([]);
  }, []);

  const selectSession = useCallback((id: string) => {
    setActiveId(id);
  }, []);

  const appendMessages = useCallback((userContent: string, assistantContent: string) => {
    setMessages((prev) => [
      ...prev,
      { role: "user", content: userContent },
      { role: "agent", content: assistantContent },
    ]);
  }, []);

  const appendUserMessage = useCallback((content: string) => {
    setMessages((prev) => [...prev, { role: "user", content }]);
  }, []);

  const appendAssistantMessage = useCallback((content: string) => {
    setMessages((prev) => [...prev, { role: "agent", content }]);
  }, []);

  return {
    sessionIds,
    activeId,
    messages,
    loading,
    setMessages,
    loadSessions,
    loadMessages,
    createNewSession,
    selectSession,
    appendMessages,
    appendUserMessage,
    appendAssistantMessage,
  };
}
