"""Matcher rules and agent behaviour on the synthetic fixtures, offline (the model is replaced by stubs)."""
import json
from pathlib import Path

import pytest

from recallops.agent import Agent
from recallops.alerts import AlertEntry
from recallops.baseline import alerts_for_round
from recallops.evaluate import load_truth, score
from recallops.fixtures import SYNONYMS
from recallops.matcher import decide, index_alerts, name_relation, norm_batch, parse_stock_month
from recallops.stockservice import StockService

ROOT = Path(__file__).parent.parent
FIX, RAW = ROOT / "data" / "fixtures", ROOT / "data" / "alerts" / "raw"


def alert(batch="AB-123", product="Telmisartan Tablets IP 40 mg", mfr="Swiss Garnier Life Sciences, Una", mfg="2025-08", exp="2027-07"):
    return AlertEntry("t", "x", 0, "1", product, batch, mfg, exp, mfr, "Dissolution", "lab", report_month="2026-07")


def row(batch="AB123", mfg="08/2025", exp="Jul-27"):
    return {"stock_id": "S1", "batch_raw": batch, "mfg_raw": mfg, "expiry_raw": exp}


def item(name="Telmisartan 40mg Tab", mfr="Swiss Garnier"):
    return {"item_name": name, "mfr_name": mfr}


class Judge:
    """Stands in for the model: knows the synonym table, counts calls."""

    def __init__(self):
        self.calls = 0

    def __call__(self, stock, alert_name):
        self.calls += 1
        for k, v in SYNONYMS.items():
            if v.lower() in stock.lower() and k in alert_name.lower():
                return "yes", "synonym"
        return "no", "different"


def test_batch_normalisation_is_trivial_only():
    assert norm_batch(" ab-123, ") == norm_batch("AB123") == "AB123"
    assert norm_batch("BKBP O2601") == norm_batch("BKBP02601")  # the real duplicate in the AUG alert
    assert norm_batch("AB124") != norm_batch("AB123")  # a one-character neighbour is a different batch


def test_stock_dates_parse_all_fixture_formats():
    for text in ("08/2025", "Aug-25", "2025-08", "28/08/2025", "Aug 2025"):
        assert parse_stock_month(text) == "2025-08", text
    assert parse_stock_month("") is None


def test_name_relations():
    a = "Amoxycillin & Potassium Clavulanate Tablets IP"
    assert name_relation("AMOXYCILLIN & POTASSIUM CLAVULANATE TABLETS I.P.", a) == "exact"
    assert name_relation("Amox+Clav 625 TAB", a) == "abbrev"
    assert name_relation("Acetaminophen Tablets 500mg", "Paracetamol Tablets IP 500 mg") in ("different", "unknown")  # needs drug knowledge
    assert name_relation("Atenolol Tablets IP 50 mg", a) == "different"


def test_decision_rules():
    idx = index_alerts([alert()])
    assert decide(row(), item(), idx).action == "hold"
    assert decide(row(batch="AB124"), item(), idx).action == "no_hold"  # sibling batch
    assert decide(row(), item(mfr="Other Labs"), idx).action == "review"  # manufacturer conflict
    assert decide(row(mfg="01/2025"), item(), idx).action == "review"  # dates conflict
    assert decide(row(mfg="", exp=""), item(mfr=""), idx).action == "review"  # nothing corroborates
    assert decide(row(mfg="", exp=""), item(), idx).action == "hold"  # manufacturer corroborates
    other = item(name="Atenolol Tablets IP 50 mg", mfr="Demo Pharma")
    assert decide(row(mfg="03/2025", exp="02/2027"), other, idx).action == "no_hold"  # collision: only the batch number agrees
    assert decide(row(), other, idx).action == "review"  # dates agree too, and no judge: escalate rather than guess
    assert "not a safety clearance" in decide(row(batch="ZZ9"), item(), idx).reason


def test_alias_judge_used_only_when_needed_and_never_guesses():
    j = Judge()
    idx = index_alerts([alert(product="Paracetamol Tablets IP 500 mg")])
    assert decide(row(), item(name="Acetaminophen 500mg"), idx, j).action == "hold" and j.calls == 1
    assert decide(row(), item(name="Telmisartan 40mg Tab"), idx, j).action in ("no_hold", "review")
    assert decide(row(), item(name="Acetaminophen 500mg"), idx, None).action == "review"  # no judge: escalate, never guess
    # a model "no" must not clear a row when batch, manufacturer and dates all agree
    idx3 = index_alerts([alert(product="Paracetamol, Phenylephrine, Caffeine & Diphenhydramine Tablets")])
    assert decide(row(), item(name="Para+Phen+Caff TAB"), idx3, lambda a, b: ("no", "different combination")).action == "review"
    assert decide(row(mfg="03/2025", exp="02/2027"), item(name="Para+Phen+Caff TAB", mfr="Other"), idx3, lambda a, b: ("no", "x")).action == "no_hold"
    j2 = Judge()
    decide(row(), item(), index_alerts([alert()]), j2)
    assert j2.calls == 0  # clear names never reach the model


@pytest.fixture()
def truth():
    return load_truth(FIX / "truth.json")


def run_two_rounds(tmp_path, judge, inject=0, truth=None):
    svc = StockService(fixtures_dir=FIX)
    agent = Agent(svc, None, tmp_path)
    agent._alias_judge = lambda a, b: judge(a, b)  # deterministic stand-in for the model
    reports, metrics = {}, {}
    for rnd in ("1", "2"):
        if inject and rnd == "1":
            svc.inject_timeout_after_write(inject)
        reports[rnd] = agent.process_alert(alerts_for_round(rnd, RAW), rnd)
        if truth:  # score straight after each round: later rounds legitimately change the state
            metrics[rnd] = score(svc, reports[rnd]["_review_ids"], truth, rnd, reports[rnd]["_traced_customers"])
    return svc, agent, reports, metrics


def test_agent_two_rounds_no_wrong_or_missed_holds(tmp_path, truth):
    _, _, _, metrics = run_two_rounds(tmp_path, Judge(), truth=truth)
    for rnd, m in metrics.items():
        assert m["wrong_hold"] == 0 and m["review_held"] == 0 and m["review_cleared"] == 0, rnd
        assert m["missed_hold"] <= 1, rnd
        assert m["customers_found"] == m["customers_exposed"] and m["customers_extra"] == 0, rnd


def test_second_alert_reopens_earlier_decisions_and_keeps_old_holds(tmp_path):
    svc, _, reports, _ = run_two_rounds(tmp_path, Judge())
    r1, r2 = reports["1"], reports["2"]
    assert r2["reopened_decisions"] and all(x["was"] != x["now"] for x in r2["reopened_decisions"])
    assert any(x["was"] == "no_hold" and x["now"] == "hold" for x in r2["reopened_decisions"])
    assert r2["acted"]["already_held"] == r1["counts"]["hold"]  # round-1 holds are left alone, not repeated
    assert r2["verification"]["duplicate_hold_events"] == 0


def test_timeout_after_write_is_reconciled_by_readback_not_repeated(tmp_path):
    svc, _, reports, _ = run_two_rounds(tmp_path, Judge(), inject=3)
    rec = reports["1"]["recovery_events"]
    assert len(rec) == 3 and all(e["event"] == "timeout_after_write" for e in rec)
    assert reports["1"]["verification"]["duplicate_hold_events"] == 0
    assert reports["1"]["verification"]["problems"] == []
    assert all(svc.get_stock(e["stock_id"])["status"] == "HELD" for e in rec)
    assert reports["2"]["recovery_events"] == []  # per-round, nothing new in round 2


def test_drafts_are_labelled_and_carry_the_scope_note(tmp_path):
    run_two_rounds(tmp_path, Judge())
    files = list((tmp_path / "round1" / "outbox").glob("*.txt"))
    assert files
    for f in files:
        text = f.read_text(encoding="utf-8")
        assert text.startswith("DRAFT - NOT SENT") and "not a safety clearance" in text


def test_report_is_written_and_unresolved_lines_are_listed(tmp_path):
    run_two_rounds(tmp_path, Judge())
    rep = json.loads((tmp_path / "round2" / "report.json").read_text(encoding="utf-8"))
    assert rep["downstream"]["unresolved_invoice_lines"] > 0  # blank-batch invoice lines: exposure unknown, not cleared
    assert "not a safety clearance" in rep["scope_note"]
