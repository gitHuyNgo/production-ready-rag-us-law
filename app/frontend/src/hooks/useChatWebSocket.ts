import { useCallback, useRef, useState } from "react";
import type { ChatMessage } from "../services/chatApi";
import {
  createChatWebSocket,
  sendChatMessage,
  type StreamMessage,
} from "../services/chatWebSocket";

export function useChatWebSocket(
  sessionId: string | null,
  token: string | null,
  onDone: (userContent: string, assistantContent: string) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const handlerRef = useRef<(msg: StreamMessage) => void>(() => {});
  const [streaming, setStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState("");
  const [error, setError] = useState<string | null>(null);

  const closeConnection = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStreaming(false);
    setStreamContent("");
  }, []);

  const send = useCallback(
    (history: ChatMessage[], content: string) => {
      if (!sessionId || streaming) return;

      setError(null);
      setStreaming(true);
      setStreamContent("");

      const handleMessage = (msg: StreamMessage) => {
        if (msg.t === "chunk") setStreamContent((prev) => prev + msg.content);
        else if (msg.t === "done") {
          onDone(content, msg.received_content);
          setStreaming(false);
          setStreamContent("");
        } else if (msg.t === "error") {
          setError(msg.error);
          setStreaming(false);
          setStreamContent("");
        }
      };

      handlerRef.current = handleMessage;

      const onClose = () => {
        wsRef.current = null;
        setStreaming(false);
        setStreamContent("");
      };

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        sendChatMessage(wsRef.current, history, content);
        return;
      }

      const ws = createChatWebSocket(
        sessionId,
        token,
        () => handlerRef.current,
        onClose
      );
      wsRef.current = ws;

      ws.addEventListener("open", () => {
        sendChatMessage(ws, history, content);
      });
      ws.addEventListener("error", () => {
        setError("Connection error");
        setStreaming(false);
      });
    },
    [sessionId, token, streaming, onDone]
  );

  return { send, streaming, streamContent, error, setError, closeConnection };
}
