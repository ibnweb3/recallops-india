"""Run the baseline or the agent over both alert rounds and score against the fixture answer key.

  python -m recallops.run baseline
  python -m recallops.run agent [--no-llm] [--inject-timeout N] [--name my-run]

The baseline is stateless (a fresh stock service per round). The agent keeps one case across rounds, so
round 2 reopens decisions from round 1. Output goes to runs/<name>/ (git-ignored).
Each process traces under one neatlogs workflow name: recallops-baseline or recallops-agent.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from . import tracing
from .agent import Agent
from .baseline import alerts_for_round, run_baseline
from .evaluate import load_truth, score, summary_line
from .stockservice import StockService

FIXTURES = Path("data/fixtures")


def _metrics_view(m: dict) -> dict:
    return {k: v for k, v in m.items() if not k.endswith("_ids")}


@tracing.span("WORKFLOW", "recallops_baseline_run", capture_input=False)
def baseline_workflow(rounds: list[str], out: Path) -> dict:
    truth, results = load_truth(FIXTURES / "truth.json"), {}
    for rnd in rounds:
        t0 = time.time()
        service = StockService(db_path=out / f"stock-round{rnd}.sqlite", fixtures_dir=FIXTURES)
        run_baseline(service, alerts_for_round(rnd))
        m = score(service, set(), truth, rnd)
        results[rnd] = {**_metrics_view(m), "seconds": round(time.time() - t0, 2), "llm_calls": 0}
        print(f"baseline round {rnd}: {summary_line(m)}")
    return results


@tracing.span("WORKFLOW", "recallops_agent_run", capture_input=False)
def agent_workflow(rounds: list[str], out: Path, llm, inject_timeout: int, inject_round: str) -> dict:
    truth, results = load_truth(FIXTURES / "truth.json"), {}
    service = StockService(db_path=out / "stock.sqlite", fixtures_dir=FIXTURES)
    agent = Agent(service, llm, out)
    for rnd in rounds:
        t0 = time.time()
        if inject_timeout and rnd == inject_round:
            service.inject_timeout_after_write(inject_timeout)
        report = agent.process_alert(alerts_for_round(rnd), rnd)
        m = score(service, report["_review_ids"], truth, rnd, report["_traced_customers"])
        results[rnd] = {**_metrics_view(m), "seconds": round(time.time() - t0, 2), "llm_calls": report["llm_calls_this_round"],
                        "reopened": len(report["reopened_decisions"]), "recovery_events": len(report["recovery_events"]),
                        "duplicate_hold_events": report["verification"]["duplicate_hold_events"],
                        "verification_problems": len(report["verification"]["problems"]), "unresolved_invoice_lines": report["downstream"]["unresolved_invoice_lines"]}
        print(f"agent round {rnd}: {summary_line(m)} | customers {m['customers_found']}/{m['customers_exposed']} (+{m['customers_extra']}) | "
              f"llm calls {report['llm_calls_this_round']} | reopened {len(report['reopened_decisions'])} | recoveries {len(report['recovery_events'])}")
    if llm:
        results["llm_usage"] = llm.usage()
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["baseline", "agent"])
    ap.add_argument("--rounds", default="1,2")
    ap.add_argument("--name", default=None)
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--inject-timeout", type=int, default=0, help="make the next N place_hold calls time out after writing")
    ap.add_argument("--inject-round", default="2")
    args = ap.parse_args()
    name = args.name or f"{args.mode}-{time.strftime('%Y%m%d-%H%M%S')}"
    out = Path("runs") / name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    traced = tracing.setup(f"recallops-{args.mode}", tags=["hackathon", "synthetic-fixtures", f"run:{name}"])
    rounds = args.rounds.split(",")
    t0 = time.time()
    if args.mode == "baseline":
        results = baseline_workflow(rounds, out)
    else:
        from .llm import LLM

        results = agent_workflow(rounds, out, None if args.no_llm else LLM(), args.inject_timeout, args.inject_round)
    results["_run"] = {"name": name, "mode": args.mode, "traced": traced, "seconds": round(time.time() - t0, 2),
                       "inject_timeout": args.inject_timeout}
    (out / "metrics.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    diag = tracing.flush()
    if diag is not None:
        results["_run"]["neatlogs_delivery"] = diag
        (out / "metrics.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
        print(f"neatlogs delivery counters: {diag}")
    print(f"metrics -> {out / 'metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
