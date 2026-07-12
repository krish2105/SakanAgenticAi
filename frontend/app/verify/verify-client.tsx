"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { verifyEmail } from "@/lib/api";

type State = "verifying" | "success" | "error";

export function VerifyClient() {
  const token = useSearchParams().get("token") || "";
  const [state, setState] = useState<State>("verifying");

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!token) {
        setState("error");
        return;
      }
      try {
        await verifyEmail(token);
        if (!cancelled) setState("success");
      } catch {
        if (!cancelled) setState("error");
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-6 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">Sakan AI</p>
      <h1 className="mt-2 font-display text-2xl font-semibold text-text-primary">Email verification</h1>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">
            {state === "verifying" && "Verifying your email…"}
            {state === "success" && "Email verified"}
            {state === "error" && "Couldn't verify"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {state === "verifying" && (
            <p className="text-sm text-text-muted">One moment while we confirm your email address.</p>
          )}
          {state === "success" && (
            <p className="text-sm text-positive">
              Your email address is confirmed. You&apos;re all set.
            </p>
          )}
          {state === "error" && (
            <p className="text-sm text-negative">
              This verification link is invalid or has expired. You can request a new one from your
              account once signed in.
            </p>
          )}
          <Link href="/" className="mt-4 block">
            <Button variant="outline" size="sm">
              Go to command deck
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
