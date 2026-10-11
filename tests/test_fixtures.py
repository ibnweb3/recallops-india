"""Invariants of the synthetic fixture generator. These test the generator's own promises (labels,
determinism, conservation, and that decoys really are decoys); they do not test any matcher."""
import csv
import json
from pathlib import Path

import pytest

from recallops.fixtures import AS_OF, build, norm_batch
from recallops.portal import parse_portal_jsonl

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "alerts" / "raw"


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("fx")
    summary = build(out=out)
    return out, summary, json.loads((out / "truth.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def alerts():
    jul = parse_portal_jsonl(RAW / "portal-JUL-2026.jsonl")
    aug = parse_portal_jsonl(RAW / "portal-AUG-2026.jsonl")
    return jul, aug


def test_every_table_is_labelled_synthetic(built):
    out, _, truth = built
    assert truth["synthetic"] is True
    assert (out / "SYNTHETIC-FIXTURE.txt").read_text(encoding="utf-8").startswith("SYNTHETIC DATA")
    for name in ("items", "stock", "purchases", "customers", "sales"):
        rows = read(out / f"{name}.csv")
        assert rows and {r["_synthetic"] for r in rows} == {"Y"}, name


def test_same_seed_gives_identical_files_and_a_new_seed_differs(built, tmp_path):
    out, _, _ = built
    again = tmp_path / "again"
    build(out=again)
    for f in ("items.csv", "stock.csv", "sales.csv", "purchases.csv", "truth.json"):
        assert (out / f).read_bytes() == (again / f).read_bytes(), f
    other = tmp_path / "other"
    build(seed=1, out=other)
    assert (out / "stock.csv").read_bytes() != (other / "stock.csv").read_bytes()


def test_committed_fixtures_are_reproducible(built):
    out, _, _ = built
    committed = ROOT / "data" / "fixtures"
    for f in ("items.csv", "stock.csv", "sales.csv", "purchases.csv", "customers.csv", "truth.json"):
        assert (out / f).read_text(encoding="utf-8").splitlines() == (committed / f).read_text(encoding="utf-8").splitlines(), f


def test_every_role_is_present(built):
    _, summary, _ = built
    for role in ("affected", "sibling", "sibling_near", "mfr_mismatch", "unrelated", "unrelated_namealike", "collision"):
        assert summary["roles"].get(role, 0) > 0, role
    assert summary["expected_round2"]["hold"] > summary["expected_round1"]["hold"]  # the second alert adds holds


def test_units_are_conserved_except_for_the_deliberate_ledger_gaps(built):
    out, _, truth = built
    purchases = {(p["item_code"], p["batch_raw"]): p for p in read(out / "purchases.csv")}
    stock = {s["stock_id"]: s for s in read(out / "stock.csv")}
    gaps = 0
    for lot in truth["lots"].values():
        p = purchases[(lot["item_code"], lot["batch_true_text"])]
        received = int(p["qty_boxes"]) * int(p["units_per_box"])
        assert received == lot["received_units"]
        assert received == lot["sold_units"] + lot["on_hand_true_units"]
        recorded = sum(int(stock[s]["qty_units"]) for s in lot["stock_ids"])
        gap = lot.get("ledger_gap_units", 0)
        assert recorded == lot["on_hand_true_units"] + gap
        gaps += bool(gap)
    assert gaps >= 3


def test_decoys_are_decoys(built, alerts):
    out, _, truth = built
    jul, aug = alerts
    alert_norm = {norm_batch(e.batch_no): e for e in jul + aug}
    items = {i["item_code"]: i for i in read(out / "items.csv")}
    for lot in truth["lots"].values():
        n = norm_batch(lot["batch_true_text"])
        if lot["role"] in ("sibling", "sibling_near", "unrelated", "unrelated_namealike"):
            assert n not in alert_norm, lot["lot_id"]
            assert lot["expected"] == {"1": "no_hold", "2": "no_hold"}
        elif lot["role"] == "collision":
            assert n in alert_norm and lot["expected"] == {"1": "no_hold", "2": "no_hold"}
            assert items[lot["item_code"]]["item_name"].lower()[:12] != alert_norm[n].product_name.lower()[:12]
        elif lot["role"] == "mfr_mismatch":
            assert n in alert_norm and lot["expected"] == {"1": "review", "2": "review"}
        elif lot["role"] == "affected":
            assert n == norm_batch(lot["alert_batch"]), lot["lot_id"]  # same batch after trivial normalisation
            assert lot["expected"]["2"] in ("hold", "review")


def test_second_alert_reopens_lots_that_round_one_did_not_list(built):
    _, _, truth = built
    reopened = [l for l in truth["lots"].values() if l["role"] == "affected" and l["reopened_in_round_2"]]
    assert reopened
    for l in reopened:
        assert l["expected"]["1"] == "no_hold" and l["expected"]["2"] in ("hold", "review")


def test_exposure_truth_only_names_customers_with_lines_on_held_lots(built):
    out, _, truth = built
    sales = {s["sale_line"]: s for s in read(out / "sales.csv")}
    for rnd in ("1", "2"):
        for cust, lines in truth["exposed_customers"][rnd].items():
            for ln in lines:
                assert sales[ln]["customer_id"] == cust and sales[ln]["batch_raw"]
        for ln in truth["unresolved_sales_lines"][rnd]:
            assert sales[ln]["batch_raw"] == ""  # blank batch on the invoice: exposure cannot be confirmed
    assert truth["exposed_customers"]["1"] and len(truth["exposed_customers"]["2"]) >= len(truth["exposed_customers"]["1"])


def test_dates_never_after_as_of(built):
    out, _, _ = built
    for f, col in (("sales.csv", "date"), ("purchases.csv", "date")):
        assert max(r[col] for r in read(out / f)) <= AS_OF.isoformat()
