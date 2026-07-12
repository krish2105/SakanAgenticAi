"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  clearTokens,
  fetchMe,
  getAccessToken,
  loginUser,
  logoutUser,
  onTokenChange,
  registerUser,
  type AuthUser,
} from "@/lib/api";

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

  // Restore a session from storage on mount. api.ts owns token storage now.
  // The work lives in a nested async function so no setState runs synchronously
  // in the effect body (authedGet also transparently refreshes an expired
  // access token during fetchMe).
  useEffect(() => {
    let cancelled = false;
    async function restore() {
      const stored = getAccessToken();
      const me = stored ? await fetchMe(stored) : null;
      if (cancelled) return;
      if (stored && me) {
        setToken(getAccessToken());
        setUser(me);
      } else if (stored) {
        clearTokens();
      }
      setLoading(false);
    }
    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  // Stay in sync when a background refresh rotates the access token, or a failed
  // refresh clears it (multi-tab-aware for the current tab's in-memory state).
  useEffect(() => {
    return onTokenChange((newAccess) => {
      setToken(newAccess);
      if (!newAccess) setUser(null);
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await loginUser(email, password); // stores tokens
    setToken(getAccessToken());
    setUser(await fetchMe(getAccessToken() || ""));
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    await registerUser(email, password, fullName); // stores tokens
    setToken(getAccessToken());
    setUser(await fetchMe(getAccessToken() || ""));
  }, []);

  const logout = useCallback(() => {
    void logoutUser(); // revoke server-side + clear storage (fires onTokenChange)
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
