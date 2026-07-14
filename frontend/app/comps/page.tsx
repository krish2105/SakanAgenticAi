import type { Metadata } from "next";
import { fetchComps } from "@/lib/api";
import { CompsExplorerClient } from "./comps-explorer-client";

export const metadata: Metadata = {
  title: "Comps Explorer",
  description: "Search and filter Dubai comparable transactions directly on a map.",
};

export default async function CompsExplorerPage() {
  const initialComps = await fetchComps({ limit: 100 });
  return <CompsExplorerClient initialComps={initialComps} />;
}
