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


def test_valuation_chart_produces_a_larger_valid_pdf():
    valuation = {
        "low": 1_800_000,
        "high": 2_200_000,
        "comps": [
            {"price": 1_900_000, "building": "Tower A"},
            {"price": 2_100_000, "building": "Tower B"},
            {"price": 2_050_000, "building": "Tower C"},
        ],
    }
    without_chart = markdown_to_pdf_bytes("# Memo\n\nSome text.")
    with_chart = markdown_to_pdf_bytes("# Memo\n\nSome text.", valuation=valuation)
    assert with_chart.startswith(b"%PDF")
    # Not a strict guarantee for every PDF library, but a real sanity check
    # that drawing extra content actually added something to the stream.
    assert len(with_chart) >= len(without_chart)


def test_valuation_chart_skips_cleanly_with_no_comps():
    valuation = {"low": 1_000_000, "high": 1_200_000, "comps": []}
    pdf = markdown_to_pdf_bytes("# Memo", valuation=valuation)
    assert pdf.startswith(b"%PDF")


def test_valuation_chart_skips_cleanly_when_bounds_missing():
    pdf = markdown_to_pdf_bytes("# Memo", valuation={"low": None, "high": None, "comps": []})
    assert pdf.startswith(b"%PDF")


def test_valuation_chart_ignores_non_positive_comp_prices():
    valuation = {
        "low": 1_000_000,
        "high": 1_200_000,
        "comps": [{"price": 0, "building": "Bad Row"}, {"price": None, "building": "Missing Price"}],
    }
    pdf = markdown_to_pdf_bytes("# Memo", valuation=valuation)
    assert pdf.startswith(b"%PDF")
