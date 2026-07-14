import { describe, it, expect, vi, afterEach } from "vitest";
import { compsToCsv, downloadCompsCsv } from "@/lib/csv-export";
import type { Comp } from "@/lib/types";

const COMP: Comp = {
  transaction_id: "TXN-1",
  building: "Marina Gate II",
  community: "Dubai Marina",
  property_type: "Apartment",
  bedrooms: 2,
  size_sqft: 1100,
  price: 2100000,
  price_per_sqft: 1909,
  date: "2026-01-15",
  data_provenance: "dld_open_free",
};

describe("compsToCsv", () => {
  it("renders a header row followed by one row per comp", () => {
    const csv = compsToCsv([COMP]);
    const lines = csv.split("\r\n");
    expect(lines[0]).toBe(
      "Transaction ID,Building,Community,Property Type,Bedrooms,Size (sqft),Price (AED),Price per sqft (AED),Date,Data source"
    );
    expect(lines[1]).toBe("TXN-1,Marina Gate II,Dubai Marina,Apartment,2,1100,2100000,1909,2026-01-15,dld_open_free");
  });

  it("returns just the header for an empty list", () => {
    const csv = compsToCsv([]);
    expect(csv.split("\r\n")).toHaveLength(1);
  });

  it("quotes fields containing commas, quotes, or newlines", () => {
    const comp: Comp = { ...COMP, building: 'Tower "A", Block 1' };
    const csv = compsToCsv([comp]);
    expect(csv).toContain('"Tower ""A"", Block 1"');
  });

  it("renders missing optional fields as empty rather than the literal 'undefined'", () => {
    const comp: Comp = { ...COMP, data_provenance: undefined };
    const csv = compsToCsv([comp]);
    expect(csv.split("\r\n")[1].endsWith(",")).toBe(true);
  });
});

describe("downloadCompsCsv", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("creates an object URL, triggers a download, and revokes the URL", () => {
    const createUrl = vi.fn().mockReturnValue("blob:mock-url");
    const revokeUrl = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL: createUrl, revokeObjectURL: revokeUrl });

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    downloadCompsCsv([COMP], "my-comps.csv");

    expect(createUrl).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeUrl).toHaveBeenCalledWith("blob:mock-url");
  });
});
