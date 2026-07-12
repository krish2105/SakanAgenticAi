"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api";

export function ExportPdfButton({ queryId }: { queryId: string }) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => window.open(`${API_BASE}/deals/${queryId}/memo?format=pdf`, "_blank")}
    >
      <Download size={14} />
      Export PDF
    </Button>
  );
}
