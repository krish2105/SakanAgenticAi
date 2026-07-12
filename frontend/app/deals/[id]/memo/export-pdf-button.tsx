"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";
import { downloadDealMemoPdf } from "@/lib/api";

export function ExportPdfButton({ queryId }: { queryId: string }) {
  const { token } = useAuth();
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    if (!token) return;
    setDownloading(true);
    setError(null);
    try {
      await downloadDealMemoPdf(queryId, token);
    } catch {
      setError("Couldn't export the PDF. Try again.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button variant="outline" size="sm" onClick={handleClick} disabled={downloading || !token}>
        <Download size={14} />
        {downloading ? "Exporting…" : "Export PDF"}
      </Button>
      {error && <p className="text-xs text-negative">{error}</p>}
    </div>
  );
}
