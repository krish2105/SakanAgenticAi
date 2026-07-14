"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/components/auth-provider";
import { fetchSessions, revokeAllSessions, revokeSession, type AuthSession } from "@/lib/api";

export function AccountClient() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  useEffect(() => {
    if (!loading && !user) router.push("/login?next=/account");
  }, [loading, user, router]);

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <p className="font-mono text-xs uppercase tracking-wider text-text-muted">Account</p>
      <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary">Your account</h1>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {loading || !user ? (
            <>
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-4 w-1/2" />
            </>
          ) : (
            <>
              <Row label="Name" value={user.full_name || "—"} />
              <Row label="Email" value={user.email} />
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-text-muted">Role</span>
                <Badge variant="muted">{user.role}</Badge>
              </div>
              <div className="flex flex-wrap gap-3 pt-2">
                <Link href="/billing">
                  <Button variant="outline" size="sm">
                    Plan &amp; billing
                  </Button>
                </Link>
                <Link href="/deals">
                  <Button variant="outline" size="sm">
                    My deals
                  </Button>
                </Link>
                {user.role === "Admin" && (
                  <Link href="/admin">
                    <Button variant="outline" size="sm">
                      Admin dashboard
                    </Button>
                  </Link>
                )}
                <Button variant="ghost" size="sm" onClick={() => logout()}>
                  Sign out
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {!loading && user && <SessionsPanel />}
    </div>
  );
}

function SessionsPanel() {
  const { token, logout } = useAuth();
  const { toast } = useToast();
  const [sessions, setSessions] = useState<AuthSession[] | null>(null);
  const [busyId, setBusyId] = useState<number | "all" | null>(null);

  // A plain (non-async) function kicking off a .then()/.catch() chain, not
  // async/await -- calling an async function directly from an effect body
  // trips react-hooks/set-state-in-effect even when the setState only
  // happens after an await; same pattern as admin-client.tsx's `load`.
  const load = useCallback(() => {
    if (!token) return;
    fetchSessions(token)
      .then((data) => setSessions(data))
      .catch(() => {
        toast("Couldn't load active sessions", "error");
      });
  }, [token, toast]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRevoke(id: number) {
    if (!token) return;
    setBusyId(id);
    try {
      await revokeSession(id, token);
      setSessions((prev) => (prev ? prev.filter((s) => s.id !== id) : prev));
      toast("Session signed out", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to sign out that session", "error");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRevokeAll() {
    if (!token) return;
    setBusyId("all");
    try {
      await revokeAllSessions(token);
      toast("Signed out everywhere", "success");
      logout();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to sign out everywhere", "error");
      setBusyId(null);
    }
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>Active sessions</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {sessions === null ? (
          <>
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </>
        ) : sessions.length === 0 ? (
          <p className="text-sm text-text-muted">No other active sessions.</p>
        ) : (
          <>
            {sessions.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between gap-4 rounded-lg border border-border p-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm text-text-primary">{s.user_agent || "Unknown device"}</p>
                  <p className="mt-0.5 text-xs text-text-muted">
                    {s.ip_address ? `${s.ip_address} · ` : ""}
                    Signed in {new Date(s.created_at).toLocaleString()}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={busyId === s.id}
                  onClick={() => handleRevoke(s.id)}
                >
                  Sign out
                </Button>
              </div>
            ))}
            <Button
              variant="outline"
              size="sm"
              className="self-start"
              disabled={busyId === "all"}
              onClick={handleRevokeAll}
            >
              Sign out everywhere
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-sm text-text-muted">{label}</span>
      <span className="truncate text-sm text-text-primary">{value}</span>
    </div>
  );
}
