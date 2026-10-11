"""Stock service state transitions, the scorer, and the name-only baseline, on the synthetic fixtures."""
from pathlib import Path

import pytest

from recallops.baseline import alerts_for_round, name_key, run_baseline
from recallops.evaluate import load_truth, score
from recallops.stockservice import StockError, StockService

ROOT = Path(__file__).parent.parent
FIX = ROOT / "data" / "fixtures"
RAW = ROOT / "data" / "alerts" / "raw"


@pytest.fixture()
def svc():
    return StockService(fixtures_dir=FIX)


@pytest.fixture(scope="module")
def truth():
    return load_truth(FIX / "truth.json")


def test_hold_is_a_real_state_change_and_replay_is_idempotent(svc):
    sid = svc.list_stock("AVAILABLE")[0]["stock_id"]
    first = svc.place_hold(sid, "test", action_id="a1")
    assert first == {"stock_id": sid, "status": "HELD", "replayed": False}
    assert svc.get_stock(sid)["status"] == "HELD"
    again = svc.place_hold(sid, "test", action_id="a1")  # same action id: no second write
    assert again["replayed"] is True
    assert len(svc.events()) == 1
    with pytest.raises(StockError):  # a fresh action id on a held row is a visible conflict
        svc.place_hold(sid, "test", action_id="a2")


def test_injected_timeout_leaves_a_durable_hold(svc):
    sid = svc.list_stock("AVAILABLE")[0]["stock_id"]
    svc.inject_timeout_after_write(1)
    with pytest.raises(TimeoutError):
        svc.place_hold(sid, "test", action_id="t1")
    assert svc.get_stock(sid)["status"] == "HELD"  # the write happened although the caller saw a failure
    assert svc.place_hold(sid, "test", action_id="t1")["replayed"] is True  # retry is safe
    assert len(svc.events()) == 1


def test_release_returns_row_to_available(svc):
    sid = svc.list_stock("AVAILABLE")[0]["stock_id"]
    svc.place_hold(sid, "x", action_id="h")
    svc.release_hold(sid, "x", action_id="r")
    assert svc.get_stock(sid)["status"] == "AVAILABLE"
    with pytest.raises(StockError):
        svc.release_hold(sid, "x", action_id="r2")


def test_name_key_ignores_form_strength_and_order():
    assert name_key("Paracetamol Tablets IP 650mg") == name_key("PARACETAMOL tablets I.P. 500 mg") == "paracetamol"
    assert name_key("Amoxycillin & Potassium Clavulanate Tablets IP") == name_key("Potassium Clavulanate and Amoxycillin Tablets")
    assert name_key("Amox+Clav 625 TAB") != name_key("Amoxycillin & Potassium Clavulanate Tablets IP")  # shorthand defeats it


def test_baseline_holds_siblings_and_misses_shorthand(svc, truth):
    run_baseline(svc, alerts_for_round("1", RAW))
    m = score(svc, set(), truth, "1")
    assert m["correct_hold"] > 0
    assert m["wrong_hold"] > 0, "a name-only matcher should freeze sibling batches"
    assert m["missed_hold"] > 0, "a name-only matcher should miss shorthand item names"
    assert m["review_ok"] == 0  # the baseline never escalates
    sibs = [s for s, t in truth["stock"].items() if t["role"] in ("sibling", "sibling_near")]
    assert any(svc.get_stock(s)["status"] == "HELD" for s in sibs)


def test_scoring_reads_service_state_not_claims(svc, truth):
    m0 = score(svc, set(), truth, "1")
    assert m0["correct_hold"] == 0 and m0["missed_hold"] == m0["expected_holds"]
    hold_sid = next(s for s, t in truth["stock"].items() if t["expected"]["1"] == "hold")
    svc.place_hold(hold_sid, "x", action_id="z")
    assert score(svc, set(), truth, "1")["correct_hold"] == 1
    review_sid = next(s for s, t in truth["stock"].items() if t["expected"]["1"] == "review")
    assert score(svc, {review_sid}, truth, "1")["review_ok"] == 1
