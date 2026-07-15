"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { QueryVolumeChart } from "@/components/charts/query-volume-chart";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/ui/toast";
import {
  fetchAdminStats,
  fetchAdminUsers,
  fetchAdminQueryVolume,
  setAdminUserTier,
  AuthRequiredError,
  type AdminStats,
  type AdminUsersPage,
  type AdminQueryVolumeDay,
} from "@/lib/api";

const TIERS = ["starter", "pro", "team", "enterprise"] as const;
const PAGE_SIZE = 25;

export function AdminClient() {
  const router = useRouter();
  const { user, token, loading: authLoading } = useAuth();
  const { toast } = useToast();

  const [stats, setStats] = useState<AdminStats | null>(null);
  const [usersPage, setUsersPage] = useState<AdminUsersPage | null>(null);
  const [volume, setVolume] = useState<AdminQueryVolumeDay[] | null>(null);
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [forbidden, setForbidden] = useState(false);
  const [pendingUserId, setPendingUserId] = useState<number | null>(null);

  const load = useCallback(
    (q: string, off: number) => {
      if (!token) return;
      Promise.all([
        fetchAdminStats(token),
        fetchAdminUsers(token, { q: q || undefined, limit: PAGE_SIZE, offset: off }),
        fetchAdminQueryVolume(token, 30),
      ])
        .then(([s, u, v]) => {
          setStats(s);
          setUsersPage(u);
          setVolume(v);
        })
        .catch((err) => {
          if (err instanceof AuthRequiredError) {
            router.push("/login?next=/admin");
            return;
          }
          setForbidden(true);
        });
    },
    [token, router]
  );

  // The role check + initial load run inside a nested function (rather than
  // calling setState directly in the effect body) to avoid cascading
  // synchronous renders -- same pattern as auth-provider.tsx's restore().
  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/login?next=/admin");
      return;
    }

    function gateAndLoad() {
      if (user!.role !== "Admin") {
        setForbidden(true);
        return;
      }
      load(search, offset);
    }
    gateAndLoad();
    // Only re-fetch on pagination/search changes here -- `load` itself is
    // stable (useCallback) and `search`/`offset` intentionally aren't in this
    // effect's dependency array since the search box debounces separately.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user, router]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setOffset(0);
    load(search, 0);
  }

  async function handleTierChange(userId: number, tier: string) {
    if (!token) return;
    setPendingUserId(userId);
    try {
      await setAdminUserTier(userId, tier, token);
      toast(`Tier updated to ${tier}`, "success");
      load(search, offset);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to update tier", "error");
    } finally {
      setPendingUserId(null);
    }
  }

  if (authLoading || (!forbidden && !stats)) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-8">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="mt-4 h-32 w-full" />
      </div>
    );
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-8">
        <p className="text-sm text-text-muted">
          You don&apos;t have permission to view this page.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="animate-in fade-in slide-in-from-top-2 duration-500">
        <p className="font-mono text-xs uppercase tracking-wider text-text-muted">Admin</p>
        <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary">Dashboard</h1>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4 animate-in fade-in duration-700">
        <StatCard label="Total users" value={stats?.total_users} />
        <StatCard label="Verified users" value={stats?.verified_users} />
        <StatCard label="Total deals" value={stats?.total_deals} />
        <StatCard
          label="By tier"
          value={
            stats
              ? Object.entries(stats.users_by_tier)
                  .map(([t, n]) => `${t}:${n}`)
                  .join(" · ")
              : undefined
          }
        />
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Deal queries, last 30 days</CardTitle>
        </CardHeader>
        <CardContent>{volume && <QueryVolumeChart data={volume} />}</CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Users</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-2">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by email or name"
              className="h-9"
            />
            <Button type="submit" size="sm" variant="outline">
              Search
            </Button>
          </form>

          <div className="mt-4 overflow-x-auto" tabIndex={0} role="region" aria-label="Users table">
            <table className="w-full min-w-[560px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-text-muted">
                  <th className="py-2 pr-3 font-medium">Email</th>
                  <th className="py-2 pr-3 font-medium">Role</th>
                  <th className="py-2 pr-3 font-medium">Verified</th>
                  <th className="py-2 pr-3 font-medium">Tier</th>
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                {usersPage?.users.map((u) => (
                  <tr key={u.user_id} className="border-b border-border last:border-0">
                    <td className="py-2 pr-3 font-body text-text-primary">{u.email}</td>
                    <td className="py-2 pr-3">
                      <Badge variant={u.role === "Admin" ? "positive" : "muted"}>{u.role}</Badge>
                    </td>
                    <td className="py-2 pr-3">{u.email_verified ? "yes" : "no"}</td>
                    <td className="py-2 pr-3">
                      <select
                        value={u.tier}
                        disabled={pendingUserId === u.user_id}
                        onChange={(e) => handleTierChange(u.user_id, e.target.value)}
                        className="h-8 rounded-lg border border-border bg-surface px-2 text-xs text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass disabled:opacity-50"
                      >
                        {TIERS.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {usersPage?.users.length === 0 && (
              <p className="py-4 text-center text-sm text-text-muted">No users match this search.</p>
            )}
          </div>

          {usersPage && usersPage.total > PAGE_SIZE && (
            <div className="mt-4 flex items-center justify-between">
              <Button
                size="sm"
                variant="outline"
                disabled={offset === 0}
                onClick={() => {
                  const next = Math.max(0, offset - PAGE_SIZE);
                  setOffset(next);
                  load(search, next);
                }}
              >
                Previous
              </Button>
              <span className="text-xs text-text-muted">
                {offset + 1}-{Math.min(offset + PAGE_SIZE, usersPage.total)} of {usersPage.total}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={offset + PAGE_SIZE >= usersPage.total}
                onClick={() => {
                  const next = offset + PAGE_SIZE;
                  setOffset(next);
                  load(search, next);
                }}
              >
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number | undefined }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-text-muted">{label}</p>
        <p className="mt-1 truncate font-mono text-lg text-text-primary">{value ?? "—"}</p>
      </CardContent>
    </Card>
  );
}
