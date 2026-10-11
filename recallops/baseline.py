"""The "before": naive name-only matching.

For every stock row, normalise the item name and the alert product name (lower-case, drop dosage-form
and pharmacopoeia words, drop strengths, sort the remaining words) and hold the row if the two agree,
or are very close. It ignores batch, manufacturer and dates, which is what a rushed operator or a
simple script does, and it never asks for a review. No model calls.

Expected failure modes (they are the point): it holds every sibling batch of an affected product, and
it misses stock whose item name is shorthand ("Amox+Clav 625 TAB").
"""
from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from .alerts import AlertEntry
from .evaluate import load_truth, score, summary_line
from .portal import parse_portal_jsonl
from .stockservice import StockService

RAW = Path("data/alerts/raw")
STOP = {"tablets", "tablet", "capsules", "capsule", "injection", "syrup", "suspension", "oral", "ip", "i", "p", "usp", "bp",
        "mg", "mcg", "ml", "g", "iu", "w", "v", "for", "and", "with", "of", "the", "gastro", "resistant", "tab", "cap", "inj", "syp", "susp"}
FUZZY = 0.9


def name_key(name: str) -> str:
    text = re.sub(r"\(.*?\)", " ", name.lower())
    words = [w for w in re.findall(r"[a-z]+", text) if w not in STOP and len(w) > 1]
    return " ".join(sorted(words))


def alerts_for_round(rnd: str, raw_dir: Path = RAW) -> list[AlertEntry]:
    months = ["JUL"] if rnd == "1" else ["JUL", "AUG"]
    out: list[AlertEntry] = []
    for m in months:
        out += parse_portal_jsonl(raw_dir / f"portal-{m}-2026.jsonl")
    return out


def run_baseline(service: StockService, alerts: list[AlertEntry]) -> dict:
    items = service.items()
    alert_keys = {name_key(a.product_name) for a in alerts if a.product_name}
    alert_keys.discard("")
    held = []
    for row in service.list_stock("AVAILABLE"):
        key = name_key(items[row["item_code"]]["item_name"])
        if key and (key in alert_keys or any(SequenceMatcher(None, key, k).ratio() >= FUZZY for k in alert_keys)):
            service.place_hold(row["stock_id"], "name-only match to NSQ alert", action_id=f"baseline-{row['stock_id']}")
            held.append(row["stock_id"])
    return {"held": held}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", choices=["1", "2"], default="1")
    ap.add_argument("--fixtures", default="data/fixtures")
    args = ap.parse_args()
    service = StockService(fixtures_dir=args.fixtures)
    result = run_baseline(service, alerts_for_round(args.round))
    m = score(service, set(), load_truth(Path(args.fixtures) / "truth.json"), args.round)
    print(f"baseline round {args.round}: held {len(result['held'])} rows | {summary_line(m)}")
    print(json.dumps({k: v for k, v in m.items() if not k.endswith("_ids")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
