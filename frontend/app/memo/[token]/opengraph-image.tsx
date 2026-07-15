import { ImageResponse } from "next/og";
import { fetchSharedMemo } from "@/lib/api";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const BRASS = "#E38B4A";
const BG = "#0A1615";
const TEXT_PRIMARY = "#F1EDE5";
const TEXT_MUTED = "#93A6A3";

/** Auto-wired by Next's file-convention metadata system (next/og's
 * ImageResponse, built into Next.js -- no @vercel/og install needed) --
 * dropping this file next to the page is enough for og:image to pick it up
 * on every share of a memo link. Shows only the query text, never the
 * memo's valuation numbers or comps -- the share card is a teaser, not a
 * second copy of the data the link already protects behind its token. */
export default async function Image({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const memo = await fetchSharedMemo(token);
  const headline = memo?.raw_query || "Deal memo";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: BG,
          padding: 72,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 14, height: 14, borderRadius: 4, background: BRASS }} />
          <span style={{ fontSize: 32, fontWeight: 600, color: TEXT_PRIMARY }}>Sakan AI</span>
          <span style={{ fontSize: 18, color: TEXT_MUTED, letterSpacing: 2, textTransform: "uppercase" }}>
            Deal Intelligence Terminal
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <span style={{ fontSize: 22, color: BRASS, letterSpacing: 3, textTransform: "uppercase" }}>
            Shared Deal Memo
          </span>
          <span style={{ fontSize: 56, fontWeight: 600, color: TEXT_PRIMARY, lineHeight: 1.2, maxWidth: 980 }}>
            {headline}
          </span>
          <span style={{ fontSize: 24, color: TEXT_MUTED }}>
            Cited comps, a defensible valuation, and a RERA compliance check — every claim shows its work.
          </span>
        </div>
      </div>
    ),
    { ...size }
  );
}
