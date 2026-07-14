"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/components/auth-provider";

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
    </div>
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
