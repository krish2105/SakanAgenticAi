"""Minimal markdown-to-PDF renderer for the deal memo (no system deps —
pure-Python via fpdf2, since weasyprint/wkhtmltopdf need native libraries
that may not be available wherever this is deployed)."""
from __future__ import annotations

import re

from fpdf import FPDF

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")

# fpdf2's core (built-in) fonts only support latin-1; normalize the common
# "smart" punctuation Claude-generated markdown tends to use before falling
# back to a lossy encode for anything else outside that range.
_UNICODE_TO_LATIN1 = {
    "—": "-",  # em dash
    "–": "-",  # en dash
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    "•": "-",
}


def _to_latin1_safe(text: str) -> str:
    for src, dst in _UNICODE_TO_LATIN1.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _strip_markdown_inline(text: str) -> str:
    return _to_latin1_safe(_BOLD_RE.sub(r"\1", text))


_BRASS = (166, 130, 30)
_BORDER = (216, 222, 232)
_TEXT_MUTED = (91, 100, 120)


def _draw_valuation_chart(pdf: FPDF, low: float, high: float, comps: list[dict]) -> None:
    """Native fpdf2 drawing primitives, not an embedded image -- no image
    library (Pillow/cairosvg) is a dependency of this service, and a hand-drawn
    range-plus-dots chart needs nothing more than rect/line/ellipse anyway.
    Mirrors the frontend's ValuationRangeChart (components/charts/
    valuation-range-chart.tsx): a range band for [low, high], a midpoint
    tick, and one dot per comp price on the same scale."""
    prices = [c["price"] for c in comps if isinstance(c.get("price"), (int, float)) and c["price"] > 0]
    if not prices:
        return

    mid = (low + high) / 2
    lo = min([low, high, *prices])
    hi = max([low, high, *prices])
    span = (hi - lo) or 1
    lo -= span * 0.08
    hi += span * 0.08

    content_width = pdf.w - pdf.l_margin - pdf.r_margin
    x0 = pdf.l_margin
    chart_top = pdf.get_y() + 4
    track_y = chart_top + 8

    def scale(v: float) -> float:
        return x0 + ((v - lo) / (hi - lo)) * content_width

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_xy(x0, chart_top - 6)
    pdf.cell(0, 6, "Valuation vs. comps", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(*_BORDER)
    pdf.set_line_width(0.3)
    pdf.line(x0, track_y, x0 + content_width, track_y)

    pdf.set_fill_color(*_BRASS)
    band_x = scale(low)
    band_w = max(scale(high) - band_x, 1.0)
    pdf.rect(band_x, track_y - 1.8, band_w, 3.6, style="F", round_corners=True, corner_radius=1.8)

    pdf.set_draw_color(*_BRASS)
    pdf.set_line_width(0.6)
    mid_x = scale(mid)
    pdf.line(mid_x, track_y - 3.5, mid_x, track_y + 3.5)

    pdf.set_draw_color(*_TEXT_MUTED)
    pdf.set_line_width(0.3)
    for price in prices:
        px = scale(price)
        pdf.ellipse(px - 1.2, track_y + 5 - 1.2, 2.4, 2.4, style="D")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*_TEXT_MUTED)
    pdf.set_xy(x0, track_y + 10)
    pdf.cell(content_width / 2, 4, f"AED {round(lo):,}", new_x="LEFT")
    pdf.set_xy(x0 + content_width / 2, track_y + 10)
    pdf.cell(content_width / 2, 4, f"AED {round(hi):,}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)


def markdown_to_pdf_bytes(
    markdown_text: str,
    title: str = "Sakan AI — Deal Memo",
    valuation: dict | None = None,
) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _to_latin1_safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    if valuation and valuation.get("low") is not None and valuation.get("high") is not None:
        _draw_valuation_chart(pdf, valuation["low"], valuation["high"], valuation.get("comps") or [])

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        if not line:
            pdf.ln(3)
            continue

        if line.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, _strip_markdown_inline(line[4:]), new_x="LMARGIN", new_y="NEXT")
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 13)
            pdf.ln(1)
            pdf.multi_cell(0, 8, _strip_markdown_inline(line[3:]), new_x="LMARGIN", new_y="NEXT")
        elif line.startswith("# "):
            pdf.set_font("Helvetica", "B", 15)
            pdf.multi_cell(0, 9, _strip_markdown_inline(line[2:]), new_x="LMARGIN", new_y="NEXT")
        elif line.startswith("|"):
            pdf.set_font("Courier", "", 8)
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set(cells) <= {""} or all(re.fullmatch(r"-+", c) for c in cells):
                continue  # skip markdown table separator rows
            pdf.multi_cell(0, 5, _to_latin1_safe(" | ".join(cells)), new_x="LMARGIN", new_y="NEXT")
        elif line.startswith("- ") or line.startswith("* "):
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, f"  - {_strip_markdown_inline(line[2:])}", new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, _strip_markdown_inline(line), new_x="LMARGIN", new_y="NEXT")

    output = pdf.output()
    return bytes(output)
