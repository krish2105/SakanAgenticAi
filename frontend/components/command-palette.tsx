"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { Search, LogOut, Sun, Moon, Languages, type LucideIcon } from "lucide-react";
import { NAV_ITEMS } from "@/lib/nav-items";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";
import { capture } from "@/lib/analytics";
import { cn } from "@/lib/utils";

interface Command {
  id: string;
  label: string;
  hint?: string;
  icon: LucideIcon;
  run: () => void;
}

/** Global Cmd+K / Ctrl+K launcher. Mounted once in app/layout.tsx so it's
 * reachable from any page; a visible trigger in the header dispatches the
 * same "sakan:open-command-palette" event this listens for, so the two stay
 * decoupled instead of needing a shared context provider just for this. */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const { token, logout } = useAuth();
  const { t, locale, setLocale } = useLocale();

  function openPalette() {
    setQuery("");
    setActiveIndex(0);
    setOpen(true);
  }

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((prev) => {
          if (prev) return false;
          setQuery("");
          setActiveIndex(0);
          return true;
        });
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("sakan:open-command-palette", openPalette);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("sakan:open-command-palette", openPalette);
    };
  }, []);

  // Focus the input once it mounts -- syncing focus with an external DOM
  // node in response to `open` changing is exactly what this effect is for,
  // it doesn't set any React state itself.
  useEffect(() => {
    if (!open) return;
    const id = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [open]);

  const commands = useMemo<Command[]>(() => {
    const nav: Command[] = NAV_ITEMS.map((item) => ({
      id: `nav-${item.href}`,
      label: t(item.labelKey),
      hint: item.href,
      icon: item.icon,
      run: () => router.push(item.href),
    }));

    const actions: Command[] = [
      {
        id: "toggle-theme",
        label: theme === "dark" ? "Switch to light mode" : "Switch to dark mode",
        icon: theme === "dark" ? Sun : Moon,
        run: () => setTheme(theme === "dark" ? "light" : "dark"),
      },
      {
        id: "toggle-locale",
        label: locale === "ar" ? "Switch to English" : "التبديل إلى العربية (Switch to Arabic)",
        icon: Languages,
        run: () => setLocale(locale === "ar" ? "en" : "ar"),
      },
    ];

    if (token) {
      actions.push({
        id: "sign-out",
        label: "Sign out",
        icon: LogOut,
        run: () => logout(),
      });
    }

    return [...nav, ...actions];
  }, [t, router, theme, setTheme, locale, setLocale, token, logout]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) => c.label.toLowerCase().includes(q) || c.hint?.toLowerCase().includes(q));
  }, [commands, query]);

  function runCommand(cmd: Command) {
    capture("command_palette_run", { command_id: cmd.id });
    cmd.run();
    setOpen(false);
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 pt-[15vh] backdrop-blur-sm"
      onClick={() => setOpen(false)}
      role="presentation"
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-xl border border-border bg-surface shadow-2xl shadow-black/20"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <Search size={16} className="shrink-0 text-text-muted" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIndex(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActiveIndex((i) => Math.max(i - 1, 0));
              } else if (e.key === "Enter" && filtered[activeIndex]) {
                e.preventDefault();
                runCommand(filtered[activeIndex]);
              }
            }}
            placeholder="Jump to a page or run a command…"
            className="w-full bg-transparent font-body text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
            aria-label="Command palette search"
          />
          <kbd className="hidden shrink-0 rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-text-muted sm:inline">
            Esc
          </kbd>
        </div>

        <ul className="max-h-80 overflow-y-auto p-2" role="listbox">
          {filtered.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-text-muted">No matches</li>
          )}
          {filtered.map((cmd, i) => {
            const Icon = cmd.icon;
            return (
              <li key={cmd.id} role="option" aria-selected={i === activeIndex}>
                <button
                  type="button"
                  onClick={() => runCommand(cmd)}
                  onMouseEnter={() => setActiveIndex(i)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                    i === activeIndex ? "bg-brass/10 text-text-primary" : "text-text-muted hover:bg-border/30"
                  )}
                >
                  <Icon size={16} className="shrink-0" />
                  <span className="flex-1 truncate font-body">{cmd.label}</span>
                  {cmd.hint && <span className="shrink-0 font-mono text-xs text-text-muted">{cmd.hint}</span>}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
