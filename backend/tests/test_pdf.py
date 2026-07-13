"""Phase 8 -- coverage for app/services/pdf.py (the memo PDF export)."""
from __future__ import annotations

from app.services.pdf import markdown_to_pdf_bytes


def test_produces_a_valid_pdf_byte_stream():
    pdf = markdown_to_pdf_bytes("# Deal Memo\n\nValuation: **AED 1,850,000**\n\n- comp one\n- comp two")
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")  # PDF magic number
    assert len(pdf) > 500


def test_handles_unicode_smart_punctuation_without_crashing():
    # fpdf2 core fonts are latin-1 only; the renderer must normalize the
    # "smart" punctuation Claude-generated memos use rather than raise.
    tricky = "Valuation range — AED 1M–2M … see “comps” and ‘notes’ • bullet"
    pdf = markdown_to_pdf_bytes(tricky, title="Memo — Über Test")
    assert pdf.startswith(b"%PDF")


def test_empty_markdown_still_renders():
    pdf = markdown_to_pdf_bytes("")
    assert pdf.startswith(b"%PDF")
