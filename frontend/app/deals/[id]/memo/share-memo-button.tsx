"use client";

import { useState } from "react";
import { Share2, Check, Copy, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";
import { createMemoShareLink, revokeMemoShareLink } from "@/lib/api";
import { capture } from "@/lib/analytics";

export function ShareMemoButton({ queryId }: { queryId: string }) {
  const { token } = useAuth();
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleShare() {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const { share_url } = await createMemoShareLink(queryId, token);
      setShareUrl(share_url);
      capture("memo_share_link_created", { query_id: queryId });
    } catch {
      setError("Couldn't create a share link. The memo may not be ready yet.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    if (!shareUrl) return;
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function handleRevoke() {
    if (!token) return;
    setLoading(true);
    try {
      await revokeMemoShareLink(queryId, token);
      capture("memo_share_link_revoked", { query_id: queryId });
      setShareUrl(null);
    } catch {
      setError("Couldn't revoke the link. Try again.");
    } finally {
      setLoading(false);
    }
  }

  if (shareUrl) {
    return (
      <div className="flex flex-col items-end gap-1">
        <div className="flex items-center gap-1.5 rounded-lg border border-border bg-surface p-1 pe-2">
          <input
            readOnly
            value={shareUrl}
            className="w-40 truncate bg-transparent font-mono text-xs text-text-muted focus:outline-none sm:w-56"
            onFocus={(e) => e.currentTarget.select()}
            aria-label="Share link"
          />
          <button
            type="button"
            onClick={handleCopy}
            className="rounded p-1 text-text-muted hover:bg-border/40 hover:text-text-primary"
            aria-label="Copy share link"
          >
            {copied ? <Check size={14} className="text-positive" /> : <Copy size={14} />}
          </button>
          <button
            type="button"
            onClick={handleRevoke}
            disabled={loading}
            className="rounded p-1 text-text-muted hover:bg-border/40 hover:text-negative"
            aria-label="Revoke share link"
          >
            <X size={14} />
          </button>
        </div>
        {error && <p className="text-xs text-negative">{error}</p>}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button variant="outline" size="sm" onClick={handleShare} disabled={loading || !token}>
        <Share2 size={14} />
        {loading ? "Creating link…" : "Share"}
      </Button>
      {error && <p className="text-xs text-negative">{error}</p>}
    </div>
  );
}
