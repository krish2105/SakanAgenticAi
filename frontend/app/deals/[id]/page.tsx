"use client";

import { use } from "react";
import { DealResultClient } from "./deal-result-client";

export default function DealResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <DealResultClient queryId={id} />;
}
