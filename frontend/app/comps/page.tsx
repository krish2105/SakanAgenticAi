import { fetchComps } from "@/lib/api";
import { CompsExplorerClient } from "./comps-explorer-client";

export default async function CompsExplorerPage() {
  const initialComps = await fetchComps({ limit: 100 });
  return <CompsExplorerClient initialComps={initialComps} />;
}
