/** API and WebSocket base URLs from env. */

export function getApiBase(): string {
  const env = import.meta.env.VITE_API_URL;
  if (env) return env.replace(/\/$/, "");
  return window.location.origin;
}

export function getWsBase(): string {
  const env = import.meta.env.VITE_WS_URL;
  if (env) return env.replace(/^http/, "ws");
  // Use current origin so Vite proxy (or same host) can forward WebSocket to the API
  const { protocol, host } = window.location;
  const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${host}`;
}
