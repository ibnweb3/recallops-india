"""The RecallOps agent loop. Code does the matching and arithmetic; the model is used only for
(1) alias judgements on ambiguous product names and (2) drafting notices.

One call to process_alert() is one round:
  ingest alerts -> reconcile every stock row -> act (place holds, recover from timeouts) -> verify by
  reading the service back -> trace downstream customers -> draft notices -> write the case report.

A second alert is just another round on the same case: every row is re-evaluated, so rows earlier
judged "not listed" can flip to hold (the decision is reopened), and rows already held are left alone.

What it will not do: release a hold on its own, send anything, or call a "no_hold" a clearance.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from . import tracing
from .alerts import AlertEntry
from .llm import LLM, BudgetExceeded
from .matcher import Decision, decide, index_alerts, norm_batch
from .stockservice import StockError, StockService

SCOPE_NOTE = ("A CDSCO NSQ finding is specific to the tested batch. 'No hold' means the batch is not on the alerts read; "
              "it is not a safety clearance. A digital hold does not prove physical removal.")

ALIAS_SYSTEM = ("You compare two drug names from different records and answer only with JSON. "
                "Same product means the same active ingredient(s) and dosage form; brand names, abbreviations, official-name "
                "synonyms (e.g. paracetamol/acetaminophen) and spelling errors are allowed. A different combination or a "
                "missing component means no. If unsure, say unsure.")
DRAFT_SYSTEM = ("You draft short, factual, courteous business notices for an Indian pharmaceutical distributor. "
                "State only the facts given. Never claim a product is unsafe beyond the listed batch, never say other batches are "
                "safe, never promise action you were not told about. 90 words maximum. Plain text, no markdown headings.")


class Agent:
    def __init__(self, service: StockService, llm: LLM | None, out_dir: str | Path, max_llm_drafts: int = 12):
        self.service, self.llm = service, llm
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.items = service.items()
        self.decisions: dict[str, dict] = {}  # stock_id -> latest decision (the case state)
        self.log: list[dict] = []
        self.max_llm_drafts = max_llm_drafts
        self.alias_cache: dict[tuple[str, str], tuple[str, str]] = {}

    # ---------- the model's two jobs
    def _alias_judge(self, stock_name: str, alert_name: str) -> tuple[str, str]:
        key = (stock_name, alert_name)
        if key in self.alias_cache:
            return self.alias_cache[key]
        if self.llm is None:
            return ("unsure", "no model available")
        try:
            raw = self.llm.complete(ALIAS_SYSTEM, f'Record A (distributor item): "{stock_name}"\nRecord B (CDSCO alert product): "{alert_name}"\n'
                                    'Reply as {"same": "yes|no|unsure", "reason": "<=12 words"}', max_tokens=80)
            m = re.search(r"\{.*\}", raw, re.S)
            data = json.loads(m.group(0)) if m else {}
            out = (str(data.get("same", "unsure")).lower(), str(data.get("reason", ""))[:120])
            if out[0] not in ("yes", "no", "unsure"):
                out = ("unsure", "unparseable answer")
        except BudgetExceeded:
            out = ("unsure", "model call cap reached")
        except Exception as e:  # a failed model call must never become a hold or a clearance
            out = ("unsure", f"model error: {type(e).__name__}")
        self.alias_cache[key] = out
        return out

    def _draft(self, kind: str, facts: str, fallback: str, use_model: bool) -> tuple[str, str]:
        if not use_model or self.llm is None:
            return fallback, "template"
        try:
            return self.llm.complete(DRAFT_SYSTEM, f"Draft a {kind}.\nFacts:\n{facts}", draft=True, max_tokens=220), "model"
        except Exception:
            return fallback, "template"

    # ---------- steps
    @tracing.span("TOOL", "reconcile", capture_input=False)
    def reconcile(self, alerts: list[AlertEntry], rnd: str) -> dict[str, Decision]:
        idx = index_alerts(alerts)
        out: dict[str, Decision] = {}
        for row in self.service.list_stock():
            out[row["stock_id"]] = decide(row, self.items[row["item_code"]], idx, self._alias_judge)
        return out

    def _place(self, stock_id: str, reason: str, action_id: str) -> dict:
        """Place one hold; if the call times out, read the service back before doing anything else."""
        try:
            return {"status": "placed", **self.service.place_hold(stock_id, reason, action_id)}
        except TimeoutError:
            state = self.service.get_stock(stock_id)
            if state["status"] == "HELD":
                self.log.append({"event": "timeout_after_write", "stock_id": stock_id, "recovery": "read back: row is HELD, retry not needed"})
                return {"status": "reconciled_after_timeout", "stock_id": stock_id}
            self.log.append({"event": "timeout_before_write", "stock_id": stock_id, "recovery": "row still AVAILABLE, retrying with the same action_id"})
            return {"status": "retried", **self.service.place_hold(stock_id, reason, action_id)}
        except StockError as e:
            return {"status": "conflict", "stock_id": stock_id, "error": str(e)}

    @tracing.span("TOOL", "act_place_holds", capture_input=False)
    def act(self, decisions: dict[str, Decision], rnd: str) -> dict:
        placed, already, conflicts = [], [], []
        for sid, d in decisions.items():
            if d.action != "hold":
                continue
            if self.service.get_stock(sid)["status"] == "HELD":
                already.append(sid)
                continue
            r = self._place(sid, f"{d.reason} [{', '.join(d.alert_refs)}]", f"hold:{sid}")
            (conflicts if r["status"] == "conflict" else placed).append({"stock_id": sid, "how": r["status"]})
        return {"placed": placed, "already_held": already, "conflicts": conflicts}

    @tracing.span("TOOL", "verify_by_readback", capture_input=False)
    def verify(self, decisions: dict[str, Decision]) -> dict:
        problems = []
        want = {sid for sid, d in decisions.items() if d.action == "hold"}
        held = {r["stock_id"] for r in self.service.list_stock("HELD")}
        for sid in sorted(want - held):
            problems.append({"stock_id": sid, "problem": "decided hold but the service shows it is not HELD"})
        for sid in sorted(held - want):
            problems.append({"stock_id": sid, "problem": "HELD in the service but the current decision is not hold (not released automatically)"})
        events = [e for e in self.service.events() if e["kind"] == "hold"]
        dup = len(events) - len({e["stock_id"] for e in events})
        if dup:
            problems.append({"problem": f"{dup} stock rows have more than one hold event"})
        return {"intended_holds": len(want), "held_in_service": len(held), "hold_events": len(events), "duplicate_hold_events": dup,
                "problems": problems, "ledger_gaps": self._ledger_gaps(want)}

    def _ledger_gaps(self, hold_ids: set[str]) -> list[dict]:
        """Held lots whose stock record disagrees with purchases minus attributable sales (arithmetic, no model)."""
        gaps = []
        lots: dict[tuple[str, str], list[str]] = defaultdict(list)
        for sid in hold_ids:
            r = self.service.get_stock(sid)
            lots[(r["item_code"], norm_batch(r["batch_raw"]))].append(sid)
        for (item, nb), sids in lots.items():
            bought = sum(p["qty_boxes"] * p["units_per_box"] for p in self.service.purchases_for_item(item) if norm_batch(p["batch_raw"]) == nb)
            sold = sum(s["qty_units"] for s in self.service.sales_for_item(item) if norm_batch(s["batch_raw"]) == nb)
            blank = sum(s["qty_units"] for s in self.service.sales_for_item(item) if not s["batch_raw"].strip())
            on_hand = sum(self.service.get_stock(s)["qty_units"] for s in sids)
            if bought and on_hand != bought - sold:
                diff = on_hand - (bought - sold)
                gaps.append({"item_code": item, "batch": nb, "stock_units": on_hand, "purchased_minus_sold": bought - sold,
                             "difference": diff, "blank_batch_units_on_item": blank,
                             "explained_by_blank_batch_invoice_lines": diff < 0 and -diff <= blank})
        return gaps

    @tracing.span("TOOL", "trace_downstream", capture_input=False)
    def trace(self, decisions: dict[str, Decision]) -> dict:
        exposed: dict[str, dict] = {}
        unresolved: list[dict] = []
        for sid, d in decisions.items():
            if d.action != "hold":
                continue
            r = self.service.get_stock(sid)
            nb = norm_batch(r["batch_raw"])
            for s in self.service.sales_for_item(r["item_code"]):
                if s["batch_raw"].strip() and norm_batch(s["batch_raw"]) == nb:
                    c = exposed.setdefault(s["customer_id"], {"lines": [], "units": 0, "batches": set()})
                    if s["sale_line"] not in c["lines"]:
                        c["lines"].append(s["sale_line"])
                        c["units"] += s["qty_units"]
                    c["batches"].add(nb)
                elif not s["batch_raw"].strip():
                    unresolved.append({"sale_line": s["sale_line"], "customer_id": s["customer_id"], "item_code": r["item_code"],
                                       "note": "invoice line has no batch number: exposure cannot be confirmed or excluded"})
        seen, uniq = set(), []
        for u in unresolved:
            if u["sale_line"] not in seen:
                seen.add(u["sale_line"])
                uniq.append(u)
        return {"exposed": {k: {**v, "batches": sorted(v["batches"])} for k, v in sorted(exposed.items())}, "unresolved_lines": uniq}

    @tracing.span("TOOL", "draft_notices", capture_input=False)
    def draft(self, decisions: dict[str, Decision], trace: dict, rnd: str) -> dict:
        box = self.out_dir / f"round{rnd}" / "outbox"
        box.mkdir(parents=True, exist_ok=True)
        by_mfr: dict[str, list[str]] = defaultdict(list)
        for sid, d in decisions.items():
            if d.action == "hold":
                r = self.service.get_stock(sid)
                by_mfr[self.items[r["item_code"]]["mfr_name"] or "(manufacturer not recorded)"].append(
                    f"{self.items[r['item_code']]['item_name']} batch {r['batch_raw'].strip()} ({r['qty_units']} units held)")
        written = []
        for mfr, lines in sorted(by_mfr.items()):
            facts = f"Supplier/manufacturer: {mfr}\nBatches placed on digital hold after the CDSCO NSQ alert:\n- " + "\n- ".join(lines)
            fb = f"To {mfr}: we have placed the following batches on hold following a CDSCO NSQ alert and request your guidance on return/replacement:\n- " + "\n- ".join(lines)
            text, how = self._draft("notice to a supplier asking for return/replacement guidance", facts, fb, use_model=False)
            path = box / f"supplier_{re.sub(r'[^A-Za-z0-9]+', '_', mfr)[:40]}.txt"
            path.write_text(f"DRAFT - NOT SENT ({how})\n\n{text}\n\n{SCOPE_NOTE}\n", encoding="utf-8")
            written.append(str(path.name))
        n_model = 0
        for cid, c in trace["exposed"].items():
            cust = self.service.customer(cid)
            facts = (f"Customer: {cust['name']} ({cust['type']}, {cust['city']})\nInvoice lines: {', '.join(c['lines'])}\n"
                     f"Units purchased of affected batches: {c['units']}\nBatch numbers: {', '.join(c['batches'])}\n"
                     "Ask them to check their stock for these batches, stop dispensing them, and reply with what they hold.")
            fb = (f"To {cust['name']}: batches {', '.join(c['batches'])} that we supplied (invoice lines {', '.join(c['lines'])}) appear on a CDSCO NSQ alert. "
                  "Please check your stock, stop dispensing these batches and tell us what you hold.")
            use_model = n_model < self.max_llm_drafts
            text, how = self._draft("notice to a pharmacy customer about batches on an NSQ alert", facts, fb, use_model)
            n_model += how == "model"
            (box / f"customer_{cid}.txt").write_text(f"DRAFT - NOT SENT ({how})\nTo: {cust['contact_email']}\n\n{text}\n\n{SCOPE_NOTE}\n", encoding="utf-8")
            written.append(f"customer_{cid}.txt")
        return {"drafts": len(written), "model_drafted": n_model, "folder": str(box)}

    # ---------- one round
    @tracing.span("AGENT", "process_alert", capture_input=False)
    def process_alert(self, alerts: list[AlertEntry], rnd: str) -> dict:
        calls_before = self.llm.calls if self.llm else 0
        log_before = len(self.log)
        decisions = self.reconcile(alerts, rnd)
        reopened = [{"stock_id": sid, "was": self.decisions[sid]["action"], "now": d.action, "why": d.reason}
                    for sid, d in decisions.items() if sid in self.decisions and self.decisions[sid]["action"] != d.action]
        acted = self.act(decisions, rnd)
        verified = self.verify(decisions)
        traced = self.trace(decisions)
        drafts = self.draft(decisions, traced, rnd)
        for sid, d in decisions.items():
            self.decisions[sid] = {"action": d.action, "reason": d.reason, "alert_refs": d.alert_refs, "round": rnd}
        review = sorted(sid for sid, d in decisions.items() if d.action == "review")
        report = {
            "round": rnd, "alert_rows": len(alerts), "scope_note": SCOPE_NOTE,
            "counts": {a: sum(1 for d in decisions.values() if d.action == a) for a in ("hold", "review", "no_hold")},
            "reopened_decisions": reopened,
            "acted": {k: len(v) for k, v in acted.items()}, "verification": verified,
            "downstream": {"customers_exposed": len(traced["exposed"]), "unresolved_invoice_lines": len(traced["unresolved_lines"])},
            "needs_human_review": review, "drafts": drafts, "recovery_events": self.log[log_before:],
            "llm_calls_this_round": (self.llm.calls - calls_before) if self.llm else 0,
            "alias_judgements": [{"stock": k[0], "alert": k[1], "same": v[0], "why": v[1]} for k, v in self.alias_cache.items()],
        }
        rd = self.out_dir / f"round{rnd}"
        rd.mkdir(parents=True, exist_ok=True)
        (rd / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
        (rd / "trace.json").write_text(json.dumps(traced, indent=1, ensure_ascii=False), encoding="utf-8")
        report["_traced_customers"] = {k: v["lines"] for k, v in traced["exposed"].items()}
        report["_review_ids"] = set(review)
        return report
