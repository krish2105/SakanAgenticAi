import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Sakan AI — Deal Intelligence Terminal",
    short_name: "Sakan AI",
    description:
      "Agentic real-estate deal intelligence for Dubai: cited comps, defensible valuations, RERA compliance checks, and investor-ready memos.",
    start_url: "/",
    display: "standalone",
    background_color: "#0B1220",
    theme_color: "#0B1220",
    icons: [
      {
        src: "/favicon.ico",
        sizes: "any",
        type: "image/x-icon",
      },
    ],
  };
}
