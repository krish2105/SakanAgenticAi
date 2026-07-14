import type { Metadata } from "next";
import { SavedCompsClient } from "./saved-comps-client";

export const metadata: Metadata = {
  title: "Saved comps — Sakan AI",
  description: "Your watchlist of saved comparable transactions.",
};

export default function SavedCompsPage() {
  return <SavedCompsClient />;
}
