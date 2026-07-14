"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { capture, identifyUser, resetAnalytics } from "@/lib/analytics";
import {
  clearTokens,
  fetchMe,
  getAccessToken,
  loginUser,
  logoutUser,
  onTokenChange,
  registerUser,
  startDemoSession,
  type AuthUser,
} from "@/lib/api";

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string, turnstileToken?: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string, turnstileToken?: string) => Promise<void>;
  continueAsDemo: () => Promise<void>;
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

  const login = useCallback(async (email: string, password: string, turnstileToken?: string) => {
    await loginUser(email, password, turnstileToken); // stores tokens
    setToken(getAccessToken());
    const me = await fetchMe(getAccessToken() || "");
    setUser(me);
    if (me) {
      identifyUser(me.user_id, { email: me.email, role: me.role });
      capture("user_logged_in");
    }
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string, turnstileToken?: string) => {
    await registerUser(email, password, fullName, turnstileToken); // stores tokens
    setToken(getAccessToken());
    const me = await fetchMe(getAccessToken() || "");
    setUser(me);
    if (me) {
      identifyUser(me.user_id, { email: me.email, role: me.role });
      capture("user_signed_up");
    }
  }, []);

  const continueAsDemo = useCallback(async () => {
    await startDemoSession(); // stores tokens
    setToken(getAccessToken());
    const me = await fetchMe(getAccessToken() || "");
    setUser(me);
    if (me) {
      identifyUser(me.user_id, { email: me.email, role: me.role, demo: true });
      capture("demo_session_started");
    }
  }, []);

  const logout = useCallback(() => {
    void logoutUser(); // revoke server-side + clear storage (fires onTokenChange)
    capture("user_logged_out");
    resetAnalytics();
    setToken(null);
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, continueAsDemo, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
