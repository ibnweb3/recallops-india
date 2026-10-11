"""Evidence-based matching of stock rows to NSQ alert rows. Pure code, no model calls.

A CDSCO NSQ finding belongs to one tested batch of one product from one manufacturer. So the batch
number is necessary, and a hold also needs the product to agree and at least one corroboration
(manufacturer or dates) without any contradiction:

  batch differs                                  -> no_hold ("not listed": a scoped finding, never a clearance)
  batch equal, product agrees, mfr/dates agree   -> hold
  batch equal, product agrees, mfr or dates conflict, or nothing corroborates -> review
  batch equal, product unclear                   -> ask for an alias judgement (callback), else review

"Product agrees" means same name after normalisation, a close typo, or pharmacy shorthand that covers
every component of the alert product. Different official names for one drug (acetaminophen /
paracetamol) cannot be told apart by string matching, so those go to the alias callback.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Callable

from .alerts import AlertEntry

STOP = {"tablets", "tablet", "capsules", "capsule", "injection", "syrup", "suspension", "oral", "ip", "i", "p", "usp", "bp",
        "mg", "mcg", "ml", "g", "iu", "w", "v", "for", "and", "with", "of", "the", "gastro", "resistant", "tab", "cap", "inj",
        "syp", "susp", "nfi", "vet"}
SALT = {"potassium", "sodium", "hydrochloride", "hcl", "hci", "sulphate", "sulfate", "maleate", "phosphate", "magnesium",
        "acetate", "dihydrochloride", "besilate", "tromethamine", "calcium", "hydrobromide", "citrate", "anhydrous", "extended",
        "release", "prolonged", "sustained", "dispersible", "enteric", "coated", "controlled", "orally", "disintegrating", "released"}
CORP = {"pvt", "ltd", "limited", "private", "llp", "co", "company", "pharma", "pharmaceuticals", "pharmaceutical", "laboratories",
        "laboratory", "labs", "healthcare", "health", "care", "lifesciences", "life", "sciences", "biotech", "india", "industries",
        "unit", "the", "ii", "i", "formulations", "remedies", "drugs"}
FUZZY = 0.9
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), start=1)}

AliasJudge = Callable[[str, str], tuple[str, str]]  # (stock name, alert name) -> ("yes"|"no"|"unsure", reason)


def norm_batch(b: str) -> str:
    """Trivial normalisation only: case, separators, O/0 confusion. Never edit-distance."""
    return re.sub(r"[^A-Z0-9]", "", (b or "").upper()).replace("O", "0")


FORMS = ("tablets", "capsules", "injection", "suspension", "syrup", "ointment")


def _is_filler(w: str) -> bool:
    """Stop words, plus dosage-form words with a typo in them ("susepnsion")."""
    return w in STOP or len(w) < 2 or (len(w) >= 6 and any(SequenceMatcher(None, w, f).ratio() >= 0.85 for f in FORMS))


def name_key(name: str) -> str:
    text = re.sub(r"\(.*?\)", " ", (name or "").lower())
    return " ".join(sorted(w for w in re.findall(r"[a-z]+", text) if not _is_filler(w)))


def _words(name: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", re.sub(r"\(.*?\)", " ", (name or "").lower())) if not _is_filler(w)]


def _components(alert_name: str) -> list[list[str]]:
    base = re.split(r"\b(?:tablets?|capsules?|injection|syrup|suspension|ointment|cream|gel)\b",
                    re.sub(r"\(.*?\)", " ", alert_name), maxsplit=1, flags=re.I)[0]
    parts = [p for p in re.split(r"\s*(?:,|&|\band\b|\bwith\b)\s*", base) if p.strip()]
    return [[w for w in re.findall(r"[a-z]+", p.lower()) if w not in SALT and w not in STOP and len(w) > 1] for p in parts]


def name_relation(stock_name: str, alert_name: str) -> str:
    sk, ak = name_key(stock_name), name_key(alert_name)
    if sk and sk == ak:
        return "exact"
    if sk and ak and SequenceMatcher(None, sk, ak).ratio() >= FUZZY:
        return "fuzzy"
    st = [w for w in _words(stock_name) if len(w) >= 3]
    aw = _words(alert_name)
    comps = [c for c in _components(alert_name) if c]
    if st and comps and all(any(a.startswith(s) for a in aw) for s in st) and \
            all(any(a.startswith(s) for s in st for a in comp) for comp in comps):
        return "abbrev"
    close = any(SequenceMatcher(None, s, a).ratio() >= 0.8 or a.startswith(s) for s in st for a in aw)
    return "unknown" if close or (sk and ak and SequenceMatcher(None, sk, ak).ratio() >= 0.5) else "different"


def _sig_tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if w not in CORP and len(w) > 1}


def mfr_relation(stock_mfr: str, alert_mfr: str) -> str:
    s = _sig_tokens(stock_mfr)
    if not s:
        return "unknown"
    a = _sig_tokens(alert_mfr)
    return "match" if len(s & a) / len(s) >= 0.6 else "mismatch"


def parse_stock_month(text: str) -> str | None:
    t = (text or "").strip()
    if not t:
        return None
    m = re.fullmatch(r"(\d{1,2})/(\d{4})", t)
    if m:
        return f"{int(m.group(2)):04d}-{int(m.group(1)):02d}"
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", t)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    m = re.fullmatch(r"\d{1,2}/(\d{1,2})/(\d{4})", t)
    if m:
        return f"{int(m.group(2)):04d}-{int(m.group(1)):02d}"
    m = re.fullmatch(r"([A-Za-z]{3})[- ](\d{2,4})", t)
    if m and m.group(1).lower() in MONTHS:
        y = int(m.group(2))
        return f"{(2000 + y if y < 100 else y):04d}-{MONTHS[m.group(1).lower()]:02d}"
    return None


def dates_relation(row: dict, alert: AlertEntry) -> str:
    mine = (parse_stock_month(row.get("mfg_raw", "")), parse_stock_month(row.get("expiry_raw", "")))
    theirs = (alert.mfg_month, alert.expiry_month)
    pairs = [(a, b) for a, b in zip(mine, theirs) if a and b]
    if not pairs:
        return "unknown"
    return "match" if all(a == b for a, b in pairs) else "mismatch"


@dataclass
class Decision:
    action: str  # hold | review | no_hold
    reason: str
    alert_refs: list[str] = field(default_factory=list)  # "<report_month>#<sno>"
    evidence: list[dict] = field(default_factory=list)
    used_alias_judge: bool = False


def _rank(action: str) -> int:
    return {"hold": 2, "review": 1, "no_hold": 0}[action]


def evaluate_pair(row: dict, item: dict, alert: AlertEntry, judge: AliasJudge | None) -> tuple[str, str, dict]:
    """Decide one stock row against one alert row that has the same normalised batch."""
    rel = name_relation(item["item_name"], alert.product_name)
    mfr = mfr_relation(item.get("mfr_name", ""), alert.manufacturer)
    dts = dates_relation(row, alert)
    ev = {"alert": f"{alert.report_month}#{alert.sno}", "batch": "equal", "name": rel, "mfr": mfr, "dates": dts}
    if rel in ("different", "unknown"):
        corroborated = mfr == "match" or dts == "match"
        if rel == "different" and not corroborated:
            return "no_hold", "batch number equals an alert batch but product, manufacturer and dates do not", ev
        if judge is None:
            return "review", f"batch equal, product name unclear ({rel}); no alias judgement available", ev
        verdict, why = judge(item["item_name"], alert.product_name)
        ev["alias_judgement"] = {"same": verdict, "why": why}
        if verdict == "no":
            if mfr == "match" and dts == "match":  # the name disagrees but everything else agrees: never clear on a model's word
                return "review", "alias check says a different product, but batch, manufacturer and dates all agree: escalated, not cleared", ev
            return "no_hold", "alias check says the stock item is a different product", ev
        if verdict != "yes":
            return "review", "alias check could not decide whether the product is the same", ev
        ev["name"] = f"{rel}->alias_confirmed"
    if mfr == "mismatch":
        return "review", "same batch and product but the manufacturer differs", ev
    if dts == "mismatch":
        return "review", "same batch and product but manufacture/expiry dates differ", ev
    if mfr == "match" or dts == "match":
        return "hold", "batch, product and " + ("manufacturer" if mfr == "match" else "dates") + " agree", ev
    return "review", "batch and product agree but nothing else can corroborate (manufacturer and dates unknown)", ev


def decide(row: dict, item: dict, by_batch: dict[str, list[AlertEntry]], judge: AliasJudge | None = None) -> Decision:
    candidates = by_batch.get(norm_batch(row["batch_raw"]), [])
    if not candidates:
        return Decision("no_hold", "no listed batch matches (scoped to the alerts read; not a safety clearance)")
    best: Decision | None = None
    used = False
    for alert in candidates:
        action, reason, ev = evaluate_pair(row, item, alert, judge)
        used = used or "alias_judgement" in ev
        d = Decision(action, reason, [ev["alert"]], [ev])
        if best is None or _rank(d.action) > _rank(best.action):
            best = d
        elif _rank(d.action) == _rank(best.action):
            best.alert_refs += d.alert_refs
            best.evidence += d.evidence
    assert best is not None
    best.used_alias_judge = used
    return best


def index_alerts(alerts: list[AlertEntry]) -> dict[str, list[AlertEntry]]:
    idx: dict[str, list[AlertEntry]] = {}
    for a in alerts:
        if a.batch_no and a.batch_no.strip().lower() not in ("not mentioned",):
            idx.setdefault(norm_batch(a.batch_no), []).append(a)
    return idx
