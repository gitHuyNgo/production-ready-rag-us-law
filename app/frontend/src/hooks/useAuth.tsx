import { createContext, useCallback, useContext, useState } from "react";
import * as authApi from "../services/authApi";

const TOKEN_KEY = "us-law-token";

export function getAuthHeaders(): Record<string, string> {
  const t = localStorage.getItem(TOKEN_KEY);
  if (!t) return {};
  return { Authorization: `Bearer ${t}` };
}

type AuthContextValue = {
  token: string | null;
  login: (username: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  setTokenFromOAuth: (accessToken: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));

  const login = useCallback(async (username: string, password: string) => {
    const result = await authApi.login(username, password);
    if (result.ok) {
      localStorage.setItem(TOKEN_KEY, result.access_token);
      setToken(result.access_token);
      return { ok: true };
    }
    return { ok: false, error: result.error };
  }, []);

  const setTokenFromOAuth = useCallback((accessToken: string) => {
    localStorage.setItem(TOKEN_KEY, accessToken);
    setToken(accessToken);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        login,
        setTokenFromOAuth,
        logout,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
