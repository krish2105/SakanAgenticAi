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


def markdown_to_pdf_bytes(markdown_text: str, title: str = "Sakan AI — Deal Memo") -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _to_latin1_safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

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
