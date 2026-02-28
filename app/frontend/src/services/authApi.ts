import { getApiBase } from "../config";

/** Full URL to start Google OIDC flow (redirects to Google, then back to frontend with ?token= or ?error=). */
export function getGoogleLoginUrl(): string {
  return `${getApiBase().replace(/\/$/, "")}/auth/login/google`;
}

export type LoginResult =
  | { ok: true; access_token: string }
  | { ok: false; error: string };

export type RegisterResult = { ok: true } | { ok: false; error: string };

export async function register(
  username: string,
  email: string,
  password: string
): Promise<RegisterResult> {
  const base = getApiBase();
  try {
    const r = await fetch(`${base}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username.trim(), email: email.trim(), password }),
    });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      return { ok: false, error: (data.detail as string) || "Registration failed" };
    }
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Network error" };
  }
}

export async function login(username: string, password: string): Promise<LoginResult> {
  const base = getApiBase();
  const form = new URLSearchParams({ username, password });
  try {
    const r = await fetch(`${base}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      return { ok: false, error: (data.detail as string) || "Login failed" };
    }
    const data = (await r.json()) as { access_token: string };
    return { ok: true, access_token: data.access_token };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Network error" };
  }
}
