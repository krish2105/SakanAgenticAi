import type { Comp } from "@/lib/types";

const COLUMNS: { key: keyof Comp; label: string }[] = [
  { key: "transaction_id", label: "Transaction ID" },
  { key: "building", label: "Building" },
  { key: "community", label: "Community" },
  { key: "property_type", label: "Property Type" },
  { key: "bedrooms", label: "Bedrooms" },
  { key: "size_sqft", label: "Size (sqft)" },
  { key: "price", label: "Price (AED)" },
  { key: "price_per_sqft", label: "Price per sqft (AED)" },
  { key: "date", label: "Date" },
  { key: "data_provenance", label: "Data source" },
];

/** Quotes a field only when it actually needs it (contains a comma, quote,
 * or newline) -- keeps plain numbers/short strings readable in the raw
 * output while still producing valid CSV for the rest. */
function csvField(value: unknown): string {
  const str = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
}

export function compsToCsv(comps: Comp[]): string {
  const header = COLUMNS.map((c) => csvField(c.label)).join(",");
  const rows = comps.map((comp) => COLUMNS.map((c) => csvField(comp[c.key])).join(","));
  return [header, ...rows].join("\r\n");
}

/** Client-side only -- no backend round trip, so this works even if the
 * backend is degraded and the comps came from the demo-data fallback. */
export function downloadCompsCsv(comps: Comp[], filename = "sakan-comps.csv"): void {
  const csv = compsToCsv(comps);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
