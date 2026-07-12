"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";
import { Button } from "@/components/ui/button";

export function AuthStatus() {
  const { user, loading, logout } = useAuth();
  const { t } = useLocale();

  if (loading) return <div className="h-9 w-20" />;

  if (!user) {
    return (
      <Link href="/login">
        <Button variant="outline" size="sm">
          {t("auth.signIn")}
        </Button>
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="hidden font-mono text-xs text-text-muted sm:inline">{user.email}</span>
      <Button variant="ghost" size="sm" onClick={logout}>
        {t("auth.signOut")}
      </Button>
    </div>
  );
}
