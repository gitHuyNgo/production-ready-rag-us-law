import { getApiBase } from "../config";

export type ChatMessage = { role: "user" | "agent"; content: string };

export async function fetchSessions(token: string | null): Promise<string[]> {
  const base = getApiBase();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(`${base}/chat/sessions`, { headers });
  if (!r.ok) return [];
  const data = (await r.json()) as { session_ids?: string[] };
  return data.session_ids ?? [];
}

export async function fetchMessages(
  sessionId: string,
  token: string | null
): Promise<ChatMessage[]> {
  const base = getApiBase();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(`${base}/chat/sessions/${encodeURIComponent(sessionId)}/messages`, {
    headers,
  });
  if (!r.ok) return [];
  const data = (await r.json()) as { messages?: { role: string; content: string }[] };
  const list = data.messages ?? [];
  return list.map((m) => ({
    role: (m.role === "assistant" || m.role === "agent" ? "agent" : "user") as "user" | "agent",
    content: m.content,
  }));
}
