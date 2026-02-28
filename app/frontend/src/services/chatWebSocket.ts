import { getWsBase } from "../config";
import type { ChatMessage } from "./chatApi";

export type StreamMessage =
  | { t: "chunk"; content: string }
  | { t: "done"; received_content: string }
  | { t: "error"; error: string };

function buildWsUrl(sessionId: string, token: string | null): string {
  let url = `${getWsBase()}/chat/`;
  const params = new URLSearchParams();
  params.set("session_id", sessionId);
  if (token) params.set("token", token);
  url += "?" + params.toString();
  return url;
}

/** Getter so the same socket can be reused for multiple messages with the correct handler each time. */
export function createChatWebSocket(
  sessionId: string,
  token: string | null,
  getMessageHandler: () => ((msg: StreamMessage) => void) | undefined,
  onClose: () => void
): WebSocket {
  const ws = new WebSocket(buildWsUrl(sessionId, token));
  ws.addEventListener("message", (event: MessageEvent) => {
    try {
      const msg = JSON.parse(event.data) as StreamMessage;
      getMessageHandler()?.(msg);
    } catch {
      getMessageHandler()?.({ t: "error", error: "Invalid response" });
    }
  });
  ws.addEventListener("close", onClose);
  return ws;
}

export function sendChatMessage(
  ws: WebSocket,
  history: ChatMessage[],
  content: string
): void {
  const payload = JSON.stringify({
    history: history.map((m) => ({ role: m.role, content: m.content })),
    role: "user",
    content,
  });
  ws.send(payload);
}
