"use client";
import { ThemeProvider } from "next-themes";
import { AnalyticsProvider } from "@/components/analytics-provider";
import { AuthProvider } from "@/components/auth-provider";
import { LocaleProvider } from "@/components/locale-provider";
import { ToastProvider } from "@/components/ui/toast";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
      <LocaleProvider>
        <AuthProvider>
          <ToastProvider>
            <AnalyticsProvider>{children}</AnalyticsProvider>
          </ToastProvider>
        </AuthProvider>
      </LocaleProvider>
    </ThemeProvider>
  );
}
