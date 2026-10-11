"""Tests against real rows copied from the CDSCO online portal (JUL-2026 and AUG-2026 NSQ alerts).

Expected values were read from the portal output itself, not invented.
"""
from pathlib import Path

import pytest

from recallops.portal import parse_mon_year, parse_portal_jsonl

RAW = Path(__file__).parent.parent / "data" / "alerts" / "raw"


@pytest.fixture(scope="module")
def jul():
    return parse_portal_jsonl(RAW / "portal-JUL-2026.jsonl")


@pytest.fixture(scope="module")
def aug():
    return parse_portal_jsonl(RAW / "portal-AUG-2026.jsonl")


def test_month_names_parse():
    assert parse_mon_year("Jun-2026") == "2026-06"
    assert parse_mon_year("AUG-2026") == "2026-08"
    assert parse_mon_year("Foo-2026") is None
    assert parse_mon_year(None) is None


def test_row_counts_match_the_portal(jul, aug):
    # "Showing 1 to 10 of 239 entries" for Jul-2026 / All sources; 220 for the default AUG-2026 view
    assert len(jul) == 239
    assert len(aug) == 220


def test_every_row_is_tagged_with_its_reporting_month(jul, aug):
    assert {e.report_month for e in jul} == {"2026-07"}
    assert {e.report_month for e in aug} == {"2026-08"}


def test_first_august_row(aug):
    e = aug[0]
    assert e.product_name == "Chlorine Tablets"
    assert e.batch_no == "292"
    assert (e.mfg_month, e.expiry_month) == ("2026-06", "2026-12")
    assert e.lab == "FDL, Vadodara"
    assert e.reporting_source == "State Lab"


def test_line_breaks_are_collapsed_but_raw_text_is_kept(jul):
    e = next(x for x in jul if x.raw["str_batch_no"] == "T-2611\n36")
    assert e.batch_no == "T-2611 36"
    assert "batch number was split across lines" in e.issues


def test_missing_batch_and_dates_are_flagged_not_dropped(jul):
    rows = [e for e in jul if e.batch_no == "Not Mentioned"]
    assert len(rows) == 2
    for e in rows:
        assert e.mfg_month is None and e.expiry_month is None
        assert any("no usable batch number" in i for i in e.issues)
        assert "manufacturing date missing" in e.issues


def test_expiry_before_manufacture_is_flagged(aug):
    e = next(x for x in aug if x.batch_no == "IT04501")
    assert (e.mfg_month, e.expiry_month) == ("2025-07", "2025-06")
    assert any("before manufacture" in i for i in e.issues)


def test_trailing_comma_on_batch_is_flagged_and_kept(aug):
    e = next(x for x in aug if x.batch_no == "GTF2327C,")
    assert "batch has stray punctuation" in e.issues


def test_real_duplicate_report_of_one_batch_is_preserved(aug):
    # The same Themis bupivacaine batch appears twice, once as BKBP02601 and once as "BKBP O2601".
    themis = [e for e in aug if e.batch_no in ("BKBP02601", "BKBP O2601")]
    assert sorted(e.batch_no for e in themis) == ["BKBP O2601", "BKBP02601"]
    assert len({e.lab for e in themis}) == 2
