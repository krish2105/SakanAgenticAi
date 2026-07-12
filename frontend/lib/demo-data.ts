// Fallback data so the UI is fully demoable even when the FastAPI backend
// isn't running yet. Real Dubai community/building names, consistent with
// the synthetic dataset generator (backend/scripts/generate_dataset.py).
import type { Tick, Comp, MarketTrendPoint, DeveloperLeaderboardEntry, OffPlanFunnelEntry } from "@/lib/types";

export const DEMO_TICKS: Tick[] = [
  { building: "Marina Gate II", community: "Dubai Marina", beds: 2, price: 2_150_000, type: "Sale" },
  { building: "Damac Hills - Camelia", community: "DAMAC Hills", beds: 3, price: 2_650_000, type: "Off-Plan" },
  { building: "Burj Vista 2", community: "Downtown Dubai", beds: 1, price: 1_780_000, type: "Sale" },
  { building: "Saheel", community: "Arabian Ranches", beds: 4, price: 5_200_000, type: "Sale" },
  { building: "The Pulse Residence", community: "Dubai South", beds: 2, price: 1_320_000, type: "Off-Plan" },
  { building: "Bay Central", community: "Dubai Marina", beds: 0, price: 890_000, type: "Sale" },
  { building: "JVC District 13", community: "Jumeirah Village Circle", beds: 2, price: 1_150_000, type: "Mortgage" },
  { building: "Executive Towers", community: "Business Bay", beds: 2, price: 1_960_000, type: "Sale" },
  { building: "Sobha Hartland Waves", community: "Mohammed Bin Rashid City", beds: 3, price: 3_450_000, type: "Off-Plan" },
  { building: "Al Barari Ashjar", community: "Al Barari", beds: 4, price: 6_800_000, type: "Sale" },
];

export const DEMO_COMMUNITIES = [
  "Business Bay",
  "Dubai Marina",
  "Jumeirah Village Circle",
  "Downtown Dubai",
  "Arabian Ranches",
  "DAMAC Hills",
  "Dubai South",
  "Mohammed Bin Rashid City",
  "Al Barari",
  "Jumeirah Lake Towers",
  "Palm Jumeirah",
  "Dubai Hills Estate",
  "Al Furjan",
  "Motor City",
  "Dubai Silicon Oasis",
];

export const DEMO_SNAPSHOT = [
  { community: "Business Bay", avg_price_per_sqft: 1685 },
  { community: "Dubai Marina", avg_price_per_sqft: 1820 },
  { community: "Downtown Dubai", avg_price_per_sqft: 2340 },
  { community: "Jumeirah Village Circle", avg_price_per_sqft: 1140 },
];

export const DEMO_COMPS: Comp[] = [
  { transaction_id: "TXN-00042", building: "Marina Gate II", community: "Dubai Marina", property_type: "Apartment", bedrooms: 2, size_sqft: 1180, price: 2_150_000, price_per_sqft: 1822, date: "2026-05-12" },
  { transaction_id: "TXN-00118", building: "Bay Central", community: "Dubai Marina", property_type: "Apartment", bedrooms: 2, size_sqft: 1120, price: 1_980_000, price_per_sqft: 1768, date: "2026-04-03" },
  { transaction_id: "TXN-00256", building: "Marina Pinnacle", community: "Dubai Marina", property_type: "Apartment", bedrooms: 2, size_sqft: 1205, price: 2_240_000, price_per_sqft: 1859, date: "2026-06-01" },
];

export const DEMO_TRENDS: MarketTrendPoint[] = Array.from({ length: 6 }, (_, i) => ({
  community: "Dubai Marina",
  month: `2026-${String(i + 1).padStart(2, "0")}`,
  avg_price_per_sqft: 1740 + i * 18,
}));

export const DEMO_LEADERBOARD: DeveloperLeaderboardEntry[] = [
  { developer_id: "DEV-01", name: "Emaar Properties", track_record_score: 92, active_projects_count: 14, delivery_delay_rate: 0.06 },
  { developer_id: "DEV-02", name: "DAMAC Properties", track_record_score: 81, active_projects_count: 11, delivery_delay_rate: 0.14 },
  { developer_id: "DEV-03", name: "Sobha Realty", track_record_score: 88, active_projects_count: 8, delivery_delay_rate: 0.09 },
];

export const DEMO_FUNNEL: OffPlanFunnelEntry[] = [
  { project_id: "PRJ-01", name: "Sobha Hartland Waves", community: "MBR City", percent_sold: 78 },
  { project_id: "PRJ-02", name: "Camelia", community: "DAMAC Hills", percent_sold: 62 },
  { project_id: "PRJ-03", name: "The Pulse Residence", community: "Dubai South", percent_sold: 41 },
];
