import type { Metadata } from "next";
import { DealsHistoryClient } from "./deals-history-client";

export const metadata: Metadata = {
  title: "My deals — Sakan AI",
  description: "Your saved deal queries, valuations, and compliance memos.",
};

export default function DealsPage() {
  return <DealsHistoryClient />;
}
