"""Score a run against the fixture answer key (data/fixtures/truth.json).

Observed outcome per stock row is read from the stock service itself, not from what the run claims:
  HELD in the service            -> "hold"
  still AVAILABLE and flagged    -> "review"
  still AVAILABLE, not flagged   -> "no_hold"
Expected outcome comes from truth.json for the alert round being scored.

Metrics (counts of stock rows):
  correct_hold    expected hold,   observed hold
  missed_hold     expected hold,   observed no_hold          <- safety failure
  wrong_hold      expected no_hold, observed hold            <- cost failure (good stock frozen)
  review_ok       expected review, observed review
  review_held     expected review, observed hold             <- acted without escalating
  review_cleared  expected review, observed no_hold          <- silently cleared an uncertain row
  needless_review expected hold/no_hold, observed review     <- workload, not an error of safety
Also: customers_recall (exposed customers found / total) when a trace is provided.
"""
from __future__ import annotations

import json
from pathlib import Path

from .stockservice import StockService

TRUTH = Path("data/fixtures/truth.json")


def load_truth(path: str | Path = TRUTH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def observed(service: StockService, flagged_for_review: set[str]) -> dict[str, str]:
    out = {}
    for row in service.list_stock():
        sid = row["stock_id"]
        out[sid] = "hold" if row["status"] == "HELD" else "review" if sid in flagged_for_review else "no_hold"
    return out


def score(service: StockService, flagged_for_review: set[str], truth: dict, rnd: str,
          traced_customers: dict[str, list[str]] | None = None) -> dict:
    obs = observed(service, flagged_for_review)
    m = {k: 0 for k in ("correct_hold", "missed_hold", "wrong_hold", "review_ok", "review_held", "review_cleared", "needless_review")}
    wrong, missed = [], []
    for sid, t in truth["stock"].items():
        exp, got = t["expected"][rnd], obs[sid]
        if exp == "hold" and got == "hold":
            m["correct_hold"] += 1
        elif exp == "hold" and got == "no_hold":
            m["missed_hold"] += 1
            missed.append(sid)
        elif exp == "no_hold" and got == "hold":
            m["wrong_hold"] += 1
            wrong.append(sid)
        elif exp == "review" and got == "review":
            m["review_ok"] += 1
        elif exp == "review" and got == "hold":
            m["review_held"] += 1
        elif exp == "review" and got == "no_hold":
            m["review_cleared"] += 1
        elif got == "review":
            m["needless_review"] += 1
    expected_holds = sum(1 for t in truth["stock"].values() if t["expected"][rnd] == "hold")
    m["expected_holds"] = expected_holds
    m["total_rows"] = len(truth["stock"])
    m["wrong_hold_ids"], m["missed_hold_ids"] = wrong, missed
    if traced_customers is not None:
        exposed = set(truth["exposed_customers"][rnd])
        found = set(traced_customers)
        m["customers_exposed"] = len(exposed)
        m["customers_found"] = len(exposed & found)
        m["customers_extra"] = len(found - exposed)
    return m


def summary_line(m: dict) -> str:
    return (f"correct {m['correct_hold']}/{m['expected_holds']}  missed {m['missed_hold']}  wrong {m['wrong_hold']}  "
            f"review ok {m['review_ok']} held-unreviewed {m['review_held']} cleared {m['review_cleared']} needless {m['needless_review']}")
