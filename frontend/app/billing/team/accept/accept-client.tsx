"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";
import { acceptTeamInvite, AuthRequiredError } from "@/lib/api";

type State = "accepting" | "success" | "error";

export function AcceptInviteClient() {
  const router = useRouter();
  const { token: authToken, loading: authLoading } = useAuth();
  const inviteToken = useSearchParams().get("token") || "";
  const [state, setState] = useState<State>("accepting");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!authToken) {
      const next = `/billing/team/accept?token=${encodeURIComponent(inviteToken)}`;
      router.push(`/login?next=${encodeURIComponent(next)}`);
      return;
    }

    let cancelled = false;
    async function run() {
      if (!inviteToken) {
        setState("error");
        return;
      }
      try {
        await acceptTeamInvite(inviteToken, authToken!);
        if (!cancelled) setState("success");
      } catch (err) {
        if (cancelled) return;
        if (err instanceof AuthRequiredError) {
          router.push(`/login?next=${encodeURIComponent(`/billing/team/accept?token=${inviteToken}`)}`);
          return;
        }
        setErrorDetail(err instanceof Error ? err.message : null);
        setState("error");
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [authLoading, authToken, inviteToken, router]);

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-6 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">Sakan AI</p>
      <h1 className="mt-2 font-display text-2xl font-semibold text-text-primary">Team invite</h1>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">
            {state === "accepting" && "Joining team…"}
            {state === "success" && "You're on the team"}
            {state === "error" && "Couldn't accept this invite"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {state === "accepting" && (
            <p className="text-sm text-text-muted">One moment while we confirm your invite.</p>
          )}
          {state === "success" && (
            <p className="text-sm text-positive">
              You now share this team&apos;s unmetered plan. Head to your billing page to see the roster.
            </p>
          )}
          {state === "error" && (
            <p className="text-sm text-negative">
              {errorDetail || "This invite is invalid or has expired. Ask the team owner to send a new one."}
            </p>
          )}
          <Link href={state === "success" ? "/billing" : "/"} className="mt-4 block">
            <Button variant="outline" size="sm">
              {state === "success" ? "Go to billing" : "Go to command deck"}
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
