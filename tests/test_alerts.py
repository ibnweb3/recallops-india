"""Tests against the real CDSCO NSQ alert for March 2025 (data/alerts/raw/NSQ-2025-03.pdf).

Expected values were read from the PDF itself (pdfplumber table output), not invented.
"""
from pathlib import Path

import pytest

from recallops.alerts import parse_alert_pdf, parse_month

PDF = Path(__file__).parent.parent / "data" / "alerts" / "raw" / "NSQ-2025-03.pdf"


@pytest.fixture(scope="module")
def entries():
    return parse_alert_pdf(PDF)


def test_month_parsing():
    assert parse_month("09/2024") == "2024-09"
    assert parse_month("01/07/2024") == "2024-07"  # stray DD/MM/YYYY keeps its month
    assert parse_month("13/2024") is None
    assert parse_month("") is None


def test_seventy_entries_with_serials_one_to_seventy(entries):
    assert [e.sno for e in entries] == [str(i) for i in range(1, 71)]


def test_first_row_matches_the_pdf(entries):
    e = entries[0]
    assert e.product_name.startswith("Amoxicillin Sodium and Clavulanate Potas")
    assert e.batch_no == "4032409004"
    assert (e.mfg_month, e.expiry_month) == ("2024-09", "2028-08")
    assert e.nsq_result == "Particulate Matter"
    assert e.lab == "CDL, Kolkata"


def test_split_entries_are_joined(entries):
    by_sno = {e.sno: e for e in entries}
    # fragment at the top of page 2 belongs to S.No 9
    assert "Microbial limit test" in by_sno["9"].nsq_result
    assert "Calcium D-Pantothenate Syrup" in by_sno["9"].product_name
    # fragment at the top of page 3 belongs to S.No 18
    assert "Nalagarh Road" in by_sno["18"].manufacturer
    assert "Panthenol and Nicotinamide Injection" in by_sno["18"].product_name
    # fragment at the top of page 8 belongs to S.No 67
    assert "Layer with Silicone Gel" in by_sno["67"].product_name


def test_every_entry_has_batch_and_dates(entries):
    for e in entries:
        assert e.batch_no, e.sno
        assert e.mfg_month and e.expiry_month, e.sno


def test_day_month_year_variant_keeps_month(entries):
    e = next(x for x in entries if x.sno == "19")
    assert (e.mfg_month, e.expiry_month) == ("2024-07", "2026-06")
    assert e.raw["mfg"] == "01/07/2024"  # original text is kept
