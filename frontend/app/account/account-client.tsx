"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/components/auth-provider";
import { UsageTimeseriesChart } from "@/components/charts/usage-timeseries-chart";
import {
  fetchSessions,
  revokeAllSessions,
  revokeSession,
  fetchApiKeys,
  createApiKey,
  revokeApiKey,
  fetchApiUsageTimeseries,
  type AuthSession,
  type ApiKeySummary,
  type DailyUsage,
} from "@/lib/api";

export function AccountClient() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  useEffect(() => {
    if (!loading && !user) router.push("/login?next=/account");
  }, [loading, user, router]);

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <div className="animate-in fade-in slide-in-from-top-2 duration-500">
        <p className="font-mono text-xs uppercase tracking-wider text-text-muted">Account</p>
        <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary">Your account</h1>
      </div>

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
      {!loading && user && <ApiKeysPanel />}
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

function ApiKeysPanel() {
  const { token } = useAuth();
  const { toast } = useToast();
  const [keys, setKeys] = useState<ApiKeySummary[] | null>(null);
  const [usage, setUsage] = useState<DailyUsage[] | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [justCreatedKey, setJustCreatedKey] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    fetchApiKeys(token)
      .then((data) => setKeys(data))
      .catch(() => toast("Couldn't load API keys", "error"));
    fetchApiUsageTimeseries(token).then(setUsage).catch(() => setUsage(null));
  }, [token, toast]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !newName.trim()) return;
    setCreating(true);
    try {
      const created = await createApiKey(newName.trim(), token);
      setJustCreatedKey(created.api_key);
      setNewName("");
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to create API key", "error");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(id: number) {
    if (!token) return;
    setBusyId(id);
    try {
      await revokeApiKey(id, token);
      setKeys((prev) => (prev ? prev.filter((k) => k.id !== id) : prev));
      toast("API key revoked", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to revoke key", "error");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>Developer API keys</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-xs text-text-muted">
          Read-only, rate-limited access to comps data for your own integrations. Send the key as
          an <code className="rounded bg-surface-raised px-1">X-API-Key</code> header to{" "}
          <code className="rounded bg-surface-raised px-1">GET /partner/v1/comps</code>.
        </p>

        {justCreatedKey && (
          <div className="rounded-lg border border-brass/40 bg-brass/10 p-3">
            <p className="text-xs font-medium text-text-primary">
              Copy this now — it won&apos;t be shown again:
            </p>
            <div className="mt-1 flex items-center gap-2">
              <code className="min-w-0 flex-1 truncate rounded bg-surface px-2 py-1 text-xs text-brass">
                {justCreatedKey}
              </code>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  navigator.clipboard?.writeText(justCreatedKey);
                  toast("Copied to clipboard", "success");
                }}
              >
                Copy
              </Button>
            </div>
            <button
              onClick={() => setJustCreatedKey(null)}
              className="mt-2 text-xs text-text-muted underline decoration-dotted hover:text-text-primary"
            >
              Done
            </button>
          </div>
        )}

        {keys === null ? (
          <Skeleton className="h-10 w-full" />
        ) : keys.length === 0 ? (
          <p className="text-sm text-text-muted">No API keys yet.</p>
        ) : (
          keys.map((k) => (
            <div key={k.id} className="flex items-center justify-between gap-4 rounded-lg border border-border p-3">
              <div className="min-w-0">
                <p className="truncate text-sm text-text-primary">{k.name}</p>
                <p className="mt-0.5 font-mono text-xs text-text-muted">
                  {k.key_prefix}… · created {new Date(k.created_at).toLocaleDateString()}
                </p>
              </div>
              <Button variant="ghost" size="sm" disabled={busyId === k.id} onClick={() => handleRevoke(k.id)}>
                Revoke
              </Button>
            </div>
          ))
        )}

        <form onSubmit={handleCreate} className="flex gap-2 pt-1">
          <Input
            placeholder="Key name (e.g. My integration)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <Button type="submit" size="sm" disabled={creating || !newName.trim()}>
            Create
          </Button>
        </form>

        {keys && keys.length > 0 && usage && usage.length > 0 && <UsageTimeseriesChart days={usage} />}
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
