"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchMe, loginUser, registerUser, type AuthUser } from "@/lib/api";

const TOKEN_STORAGE_KEY = "sakan_token";

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function restoreSession() {
      const stored = typeof window !== "undefined" ? localStorage.getItem(TOKEN_STORAGE_KEY) : null;
      const me = stored ? await fetchMe(stored) : null;
      if (stored && me) {
        setToken(stored);
        setUser(me);
      } else if (stored) {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
      }
      setLoading(false);
    }
    restoreSession();
  }, []);

  const applyToken = useCallback(async (newToken: string) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    setToken(newToken);
    const me = await fetchMe(newToken);
    setUser(me);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const newToken = await loginUser(email, password);
      await applyToken(newToken);
    },
    [applyToken]
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const newToken = await registerUser(email, password, fullName);
      await applyToken(newToken);
    },
    [applyToken]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
