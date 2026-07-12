"use client";

import { DEMO_COMMUNITIES } from "@/lib/demo-data";

export interface CompsFilters {
  community: string;
  type: string;
  bedrooms: string;
}

const PROPERTY_TYPES = ["Apartment", "Villa", "Townhouse"];
const BEDROOM_OPTIONS = ["0", "1", "2", "3", "4", "5"];

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-text-muted">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-lg border border-border bg-surface px-2 text-sm text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass"
      >
        <option value="">Any</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

export function CompsFilterBar({
  filters,
  onChange,
}: {
  filters: CompsFilters;
  onChange: (filters: CompsFilters) => void;
}) {
  return (
    <div className="flex flex-wrap gap-3">
      <Select
        label="Community"
        value={filters.community}
        onChange={(v) => onChange({ ...filters, community: v })}
        options={DEMO_COMMUNITIES}
      />
      <Select
        label="Property type"
        value={filters.type}
        onChange={(v) => onChange({ ...filters, type: v })}
        options={PROPERTY_TYPES}
      />
      <Select
        label="Bedrooms"
        value={filters.bedrooms}
        onChange={(v) => onChange({ ...filters, bedrooms: v })}
        options={BEDROOM_OPTIONS}
      />
    </div>
  );
}
