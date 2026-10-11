"""Generate SYNTHETIC distributor records from real CDSCO NSQ alert batches.

Everything in data/fixtures is made up: the distributor, customers, quantities, invoices, dates and
every deliberate error. What is real is the set of alert rows (data/alerts/raw/portal-*.jsonl) that
the affected stock lots are built from, plus the real manufacturer and product names in them.
Every CSV carries a `_synthetic` column set to "Y" and the folder carries SYNTHETIC-FIXTURE.txt.

Two alert rounds are modelled, using the real portal months:
  round 1 = JUL-2026 alert,  round 2 = JUL-2026 + AUG-2026 (the second alert adds batches).

truth.json says, for every stock row and each round, what a careful operator should do:
  hold       strong evidence: batch (after trivial normalisation) + product + manufacturer or dates
  review     weak or conflicting evidence: must be escalated, never silently held or cleared
  no_hold    not an affected batch (decoys: sibling batches, batch-number collisions, unrelated)
A failure belongs to the tested batch only, so a "no_hold" is a scoped finding, not a safety clearance.

Usage: python -m recallops.fixtures [--seed N] [--out data/fixtures]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

from .alerts import AlertEntry
from .portal import parse_portal_jsonl

DEFAULT_SEED = 20261011
AS_OF = date(2026, 10, 10)
RAW = Path("data/alerts/raw")
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

NON_DRUG = re.compile(
    r"soap|shampoo|bandage|cotton|gauze|guaze|syringe|chlorine|hajmola|wash|cleansing|formaldehyde|"
    r"cypermeth|diabetis|dr\.? puri|beauty|powder|drops|mouthwash|ors\b|oral rehydration", re.I)
SALT_WORDS = {
    "potassium", "sodium", "hydrochloride", "hcl", "hci", "sulphate", "sulfate", "maleate", "phosphate",
    "magnesium", "acetate", "dihydrochloride", "besilate", "tromethamine", "calcium", "hydrobromide", "citrate",
    "anhydrous", "gastro-resistant", "gastro", "resistant", "extended", "release", "prolonged", "sustained",
    "dispersible", "enteric", "coated", "controlled", "oral", "orally", "disintegrating"}
FORM_WORDS = {"tablets": "TAB", "tablet": "TAB", "capsules": "CAP", "capsule": "CAP", "injection": "INJ",
              "syrup": "SYP", "suspension": "SUSP", "ointment": "OINT", "cream": "CRM", "gel": "GEL"}
GENERICS = [
    "Atenolol Tablets IP 50 mg", "Metoprolol Succinate ER Tablets 25 mg", "Amlodipine Tablets IP 5 mg", "Enalapril Maleate Tablets IP 2.5 mg",
    "Ramipril Capsules IP 2.5 mg", "Furosemide Tablets IP 40 mg", "Spironolactone Tablets IP 25 mg", "Hydrochlorothiazide Tablets IP 12.5 mg",
    "Warfarin Sodium Tablets IP 5 mg", "Digoxin Tablets IP 0.25 mg", "Simvastatin Tablets IP 20 mg", "Fenofibrate Capsules IP 160 mg",
    "Levothyroxine Sodium Tablets IP 50 mcg", "Carbimazole Tablets IP 5 mg", "Hydroxychloroquine Tablets IP 200 mg", "Prednisone Tablets IP 10 mg",
    "Escitalopram Tablets IP 10 mg", "Sertraline Tablets IP 50 mg", "Fluoxetine Capsules IP 20 mg", "Amitriptyline Tablets IP 25 mg",
    "Olanzapine Tablets IP 5 mg", "Risperidone Tablets IP 2 mg", "Lorazepam Tablets IP 1 mg", "Carbamazepine Tablets IP 200 mg",
    "Phenobarbitone Tablets IP 30 mg", "Sodium Valproate Tablets IP 200 mg", "Lamotrigine Tablets IP 50 mg", "Tamsulosin Capsules 0.4 mg",
    "Finasteride Tablets IP 5 mg", "Sildenafil Citrate Tablets IP 50 mg", "Ranitidine Tablets IP 150 mg", "Famotidine Tablets IP 20 mg",
    "Lansoprazole Capsules IP 30 mg", "Esomeprazole Tablets IP 40 mg", "Ursodeoxycholic Acid Tablets IP 300 mg", "Lactulose Solution IP 10 g/15 ml",
    "Doxycycline Capsules IP 100 mg", "Cefadroxil Capsules IP 500 mg", "Ceftriaxone Injection IP 1 g", "Gentamicin Sulphate Eye Drops 0.3%",
    "Fluconazole Tablets IP 150 mg", "Acyclovir Tablets IP 400 mg", "Oseltamivir Capsules 75 mg", "Isoniazid Tablets IP 300 mg",
    "Rifampicin Capsules IP 450 mg", "Ethambutol Tablets IP 800 mg", "Pyrazinamide Tablets IP 750 mg", "Chloroquine Phosphate Tablets IP 250 mg",
    "Primaquine Phosphate Tablets IP 7.5 mg", "Artesunate Injection 60 mg", "Mebendazole Tablets IP 100 mg", "Ivermectin Tablets IP 12 mg",
    "Cetirizine Tablets IP 10 mg", "Fexofenadine Tablets 120 mg", "Chlorpheniramine Maleate Tablets IP 4 mg", "Salbutamol Inhaler 100 mcg",
    "Budesonide Inhaler 200 mcg", "Theophylline SR Tablets 200 mg", "Diclofenac Gel IP 1%", "Naproxen Tablets IP 250 mg",
    "Etoricoxib Tablets 90 mg", "Tramadol Capsules IP 50 mg", "Morphine Sulphate Injection IP 10 mg/ml", "Insulin Human Injection IP 40 IU/ml",
    "Glibenclamide Tablets IP 5 mg", "Pioglitazone Tablets IP 15 mg", "Sitagliptin Tablets 100 mg", "Folic Acid Syrup 5 mg/5 ml",
    "Vitamin B12 Injection 1000 mcg", "Zinc Sulphate Syrup 20 mg/5 ml", "Potassium Chloride Oral Solution 500 mg/5 ml", "Heparin Sodium Injection IP 5000 IU",
]
FICTIONAL_MAKERS = ["Demo Pharma Alpha", "Demo Pharma Beta", "Demo Labs Gamma", "Demo Healthcare Delta", "Demo Remedies Epsilon",
                    "Demo Lifesciences Zeta", "Demo Biotech Eta", "Demo Formulations Theta"]
SYNONYMS = {  # same drug, different official name (INN/BAN vs USAN): needs drug knowledge, not string matching
    "paracetamol": "Acetaminophen", "amoxycillin": "Amoxicillin", "salbutamol": "Albuterol", "levosalbutamol": "Levalbuterol",
    "mecobalamin": "Methylcobalamin", "lignocaine": "Lidocaine", "frusemide": "Furosemide", "glibenclamide": "Glyburide",
    "cefpodoxime": "Cefpodoxim", "rifampicin": "Rifampin"}
CITIES = [("Delhi", "DL"), ("Mumbai", "MH"), ("Pune", "MH"), ("Jaipur", "RJ"), ("Lucknow", "UP"),
          ("Chennai", "TN"), ("Bengaluru", "KA"), ("Hyderabad", "TS"), ("Kolkata", "WB"), ("Ahmedabad", "GJ"),
          ("Chandigarh", "CH"), ("Indore", "MP"), ("Kochi", "KL"), ("Patna", "BR"), ("Bhopal", "MP")]
CUSTOMER_STEMS = ["Green Cross Chemist", "City Medicals", "Sunrise Pharmacy", "Lifeline Drug House", "Apex Hospital Pharmacy",
                  "Care Plus Clinic", "Metro Health Stores", "Hope Nursing Home", "Royal Medicos", "Unity Pharmacy",
                  "Health First Chemist", "Pioneer Medical Hall", "Trust Hospital Stores", "Kalyan Medicals", "Nova Clinic Pharmacy",
                  "Shree Drug Agency", "Ocean View Pharmacy", "Silver Oak Medicos", "Midtown Chemists", "Evergreen Hospital Stores",
                  "Harmony Pharmacy", "Orbit Medical Stores", "Blue Cross Dispensary", "Lotus Chemists", "Vista Health Mart",
                  "Sai Medical Hall", "Zenith Pharma Retail", "Crest Clinic Dispensary"]


# ---------- text mess ----------

def norm_batch(b: str) -> str:
    """The trivial normalisation a matcher is allowed: case, separators, O/0 confusion."""
    return re.sub(r"[^A-Z0-9]", "", (b or "").upper()).replace("O", "0")


def short_mfr(manufacturer: str) -> str:
    head = re.split(r"[,.(\-]| {2,}| - |\n", manufacturer)[0]
    words = [w for w in head.split() if w.lower().strip(".") not in {"pvt", "ltd", "limited", "private", "llp", "p"}]
    return " ".join(words[:3]).title() or manufacturer[:20].title()


def abbreviate(product: str) -> str:
    """Pharmacy-counter shorthand: 'Amoxycillin & Potassium Clavulanate Tablets IP 625' -> 'Amox+Clav 625 TAB'."""
    text = re.sub(r"\(.*?\)", " ", product)
    form = next((FORM_WORDS[w] for w in re.findall(r"[a-z]+", text.lower()) if w in FORM_WORDS), "")
    strengths = re.findall(r"\d+(?:\.\d+)?\s?(?:mg|mcg|ml|g|iu|%)", text, flags=re.I)
    base = re.split(r"\b(?:tablets?|capsules?|injection|syrup|suspension|ointment|cream|gel)\b", text, maxsplit=1, flags=re.I)[0]
    parts = [p for p in re.split(r"\s*(?:,|&|\band\b|\bwith\b)\s*", base) if p.strip()]
    heads = []
    for p in parts:
        words = [w for w in re.findall(r"[A-Za-z]+", p) if w.lower() not in SALT_WORDS]
        if words:
            heads.append(words[0][:4].capitalize())
    name = "+".join(heads[:3]) or product[:8]
    if strengths:
        name += " " + re.sub(r"\s", "", strengths[0]).lower()
    return f"{name} {form}".strip()


def typo(name: str, rng: random.Random) -> str:
    words = name.split(" ")
    i = max(range(len(words)), key=lambda k: len(words[k]))
    w = words[i]
    if len(w) < 5:
        return name
    j = rng.randrange(1, len(w) - 2)
    words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
    return " ".join(words)


def batch_variant(b: str, rng: random.Random) -> tuple[str, str]:
    """A messy but same-batch spelling. Returns (text, how)."""
    clean_b = re.sub(r"\s+", " ", b).strip()
    options = ["lower", "nosep", "space", "comma", "pad"]
    if "0" in clean_b or "O" in clean_b.upper():
        options.append("o0")
    how = rng.choice(options)
    if how == "lower":
        return clean_b.lower(), how
    if how == "nosep":
        out = re.sub(r"[-/ .]", "", clean_b)
        return (out if out != clean_b else clean_b.lower()), (how if out != clean_b else "lower")
    if how == "space":
        k = max(2, len(clean_b) // 2)
        return clean_b[:k] + " " + clean_b[k:], how
    if how == "comma":
        return clean_b + ",", how
    if how == "pad":
        return f" {clean_b}  ", how
    idx = [i for i, c in enumerate(clean_b) if c in "0Oo"]
    i = rng.choice(idx)
    return clean_b[:i] + ("O" if clean_b[i] == "0" else "0") + clean_b[i + 1:], how


def sibling_batch(b: str, taken: set[str], rng: random.Random) -> str:
    """A different batch of the same product: change the last alphanumeric character."""
    chars = list(re.sub(r"\s+", " ", b).strip())
    for _ in range(50):
        c = list(chars)
        idx = [i for i, ch in enumerate(c) if ch.isalnum()]
        i = idx[-1] if rng.random() < 0.7 else rng.choice(idx)
        if c[i].isdigit():
            c[i] = str((int(c[i]) + rng.randint(1, 8)) % 10)
        else:
            c[i] = chr(ord("A") + (ord(c[i].upper()) - ord("A") + rng.randint(1, 20)) % 26)
        cand = "".join(c)
        if norm_batch(cand) not in taken:
            return cand
    return b + "9"


def fake_batch(rng: random.Random, taken: set[str]) -> str:
    while True:
        pat = rng.choice(["{L}{L}{D}{D}{D}{D}", "{D}{D}{D}{D}{D}{D}", "{L}{D}{D}{D}{D}{L}", "{L}{L}-{D}{D}{D}", "T{D}{D}{D}{D}{D}"])
        out = pat.replace("{L}", "@").replace("{D}", "#")
        b = "".join(rng.choice("ABCDEFGHJKLMNPRSTVWXYZ") if ch == "@" else str(rng.randint(0, 9)) if ch == "#" else ch for ch in out)
        if norm_batch(b) not in taken:
            return b


def month_text(ym: str | None, rng: random.Random, style: str) -> str:
    if not ym:
        return ""
    y, m = int(ym[:4]), int(ym[5:])
    if style == "mm/yyyy":
        return f"{m:02d}/{y}"
    if style == "mon-yy":
        return f"{MONTH_ABBR[m - 1]}-{y % 100:02d}"
    if style == "yyyy-mm":
        return f"{y}-{m:02d}"
    if style == "dd/mm/yyyy":
        return f"{rng.choice([1, 28]):02d}/{m:02d}/{y}"
    return f"{MONTH_ABBR[m - 1]} {y}"


def shift_month(ym: str, delta: int) -> str:
    y, m = int(ym[:4]), int(ym[5:])
    k = y * 12 + (m - 1) + delta
    return f"{k // 12:04d}-{k % 12 + 1:02d}"


# ---------- generator ----------

def build(seed: int = DEFAULT_SEED, out: str | Path = "data/fixtures", raw_dir: Path = RAW) -> dict:
    rng = random.Random(seed)
    jul = parse_portal_jsonl(raw_dir / "portal-JUL-2026.jsonl")
    aug = parse_portal_jsonl(raw_dir / "portal-AUG-2026.jsonl")
    all_alert = jul + aug
    alert_batches = {norm_batch(e.batch_no) for e in all_alert}

    def usable(e: AlertEntry) -> bool:
        return not e.issues and not NON_DRUG.search(e.product_name)

    # Group alert rows that are the same physical batch (real data reports some batches twice).
    def group(entries: list[AlertEntry]) -> dict[str, list[AlertEntry]]:
        g: dict[str, list[AlertEntry]] = {}
        for e in entries:
            if e.batch_no and "Not Mentioned" not in e.batch_no:
                key = norm_batch(e.batch_no) + "|" + short_mfr(e.manufacturer).lower()[:8]
                g.setdefault(key, []).append(e)
        return g

    jul_groups, aug_groups = group([e for e in jul if usable(e) or e.batch_no in ("T-2611 36",)]), group([e for e in aug if usable(e)])
    forced_jul = [k for k in jul_groups if k.startswith(("25460922|", "I7881|", "MWDC5421G|", "18260226A|", "25CT0314|"))]
    forced_aug = [k for k in aug_groups if k.startswith(("25460922|", "BKBP02601|"))]
    jul_pick = forced_jul + rng.sample([k for k in jul_groups if k not in forced_jul], 58 - len(forced_jul) + 0)
    aug_pick = forced_aug + rng.sample([k for k in aug_groups if k not in forced_aug and k not in jul_pick], 30 - len(forced_aug))

    items: list[dict] = []
    stock: list[dict] = []
    lots: dict[str, dict] = {}
    mfr_pool = sorted({short_mfr(e.manufacturer) for e in all_alert})
    taken = set(alert_batches)

    def new_item(name: str, mfr: str) -> str:
        code = f"IT{len(items) + 1:04d}"
        items.append({"item_code": code, "item_name": name, "mfr_name": mfr,
                      "units_per_box": rng.choice([10, 10, 6, 12, 15]), "_synthetic": "Y"})
        return code

    def add_lot(item_code: str, role: str, batch_raw: str, mfg: str | None, exp: str | None, refs: dict,
                expected: dict, mess: list[str], warehouse: str | None = None, extra: dict | None = None) -> str:
        lot_id = f"L{len(lots) + 1:04d}"
        warehouse = warehouse or rng.choice(["WH-DEL", "WH-MUM"])
        lots[lot_id] = {"lot_id": lot_id, "item_code": item_code, "role": role, "batch_true_text": batch_raw,
                        "alert_refs": refs, "expected": expected, "mess": mess, "stock_ids": [],
                        "mfg_month": mfg, "expiry_month": exp, "warehouse": warehouse, **(extra or {})}
        return lot_id

    # --- affected lots from real alert rows
    def make_affected(rows: list[AlertEntry], origin: str, profile: str) -> None:
        e = rows[0]
        refs: dict[str, list[str]] = {}
        for r in rows:
            refs.setdefault(r.report_month or "?", []).append(r.sno)
        mess: list[str] = []
        name = re.sub(r"\s+", " ", e.product_name).strip().rstrip(",.)")
        mfr = short_mfr(e.manufacturer)
        batch = re.sub(r"\s+", " ", e.batch_no).strip().rstrip(",")
        mfg_s, exp_s = e.mfg_month, e.expiry_month
        action = "hold"
        if profile in ("exact", "norm_batch") and any(k in name.lower() for k in SYNONYMS) and rng.random() < 0.6:
            profile = "synonym"
        if profile == "exact":
            pass
        elif profile == "norm_batch":
            batch, how = batch_variant(batch, rng)
            mess.append(f"batch:{how}")
        elif profile == "abbrev_name":
            name = abbreviate(name)
            mess.append("name:abbrev")
        elif profile == "typo_name":
            name = typo(name, rng)
            mess.append("name:typo")
        elif profile == "synonym":
            hit = next((k for k in SYNONYMS if k in name.lower()), None)
            if hit:
                name = re.sub(hit, SYNONYMS[hit], name, flags=re.I)
                mess.append(f"name:synonym:{hit}->{SYNONYMS[hit].lower()}")
        elif profile == "no_dates":
            mfg_s = exp_s = None
            mess.append("dates:blank")
        elif profile == "no_mfr":
            mfr = ""
            mess.append("mfr:blank")
        elif profile == "weak":
            name = abbreviate(name)
            batch, how = batch_variant(batch, rng)
            mfr, mfg_s, exp_s = "", None, None
            mess += ["name:abbrev", f"batch:{how}", "mfr:blank", "dates:blank"]
            action = "review"
        code = new_item(name, mfr)
        in_jul = any(r.report_month == "2026-07" for r in rows)
        expected = {"1": action if in_jul else "no_hold", "2": action}
        lot_id = add_lot(code, "affected", batch, mfg_s, exp_s, refs, expected, mess,
                         extra={"origin": origin, "alert_batch": e.batch_no, "evidence": "weak" if action == "review" else "strong",
                                "reopened_in_round_2": not in_jul})
        # lots with strong evidence sometimes sit in both warehouses
        if action == "hold" and rng.random() < 0.25:
            lots[lot_id]["split_warehouse"] = True

    profiles = ["exact"] * 34 + ["norm_batch"] * 22 + ["abbrev_name"] * 14 + ["typo_name"] * 6 + ["synonym"] * 12 + ["no_dates"] * 6 + ["no_mfr"] * 6 + ["weak"] * 6
    rng.shuffle(profiles)
    pi = iter(profiles * 3)
    for key in jul_pick:
        make_affected(jul_groups[key], "JUL-2026", next(pi))
    for key in aug_pick:
        make_affected(aug_groups[key], "AUG-2026", "weak" if len([l for l in lots.values() if l["evidence"] == "weak"]) < 3 and rng.random() < 0.1 else next(pi))
    n_affected = len(lots)
    affected_by_item = {l["item_code"]: l for l in lots.values()}

    # --- siblings: same item, different batch, different dates (name-only matching holds these wrongly)
    for lot in list(lots.values()):
        if lot["role"] != "affected" or rng.random() > 0.65:
            continue
        for _ in range(rng.choice([1, 1, 2])):
            near = rng.random() < 0.5
            b = sibling_batch(lot["batch_true_text"], taken, rng)
            taken.add(norm_batch(b))
            base = lot["mfg_month"] or "2025-06"
            add_lot(lot["item_code"], "sibling_near" if near else "sibling", b, shift_month(base, rng.choice([-5, -3, 3, 5])),
                    shift_month(base, rng.choice([19, 21, 29, 31])), {}, {"1": "no_hold", "2": "no_hold"},
                    ["different batch of an affected product"], extra={"sibling_of": lot["lot_id"]})

    # --- manufacturer mismatch: product + batch match an alert row but the manufacturer is another company
    jul_lots = [l for l in lots.values() if l["role"] == "affected" and l["origin"] == "JUL-2026" and l["evidence"] == "strong"]
    for src in rng.sample(jul_lots, 6):
        src_item = next(i for i in items if i["item_code"] == src["item_code"])
        other = rng.choice([m for m in mfr_pool if m.lower()[:8] != src_item["mfr_name"].lower()[:8]])
        code = new_item(re.sub(r"\s+", " ", src_item["item_name"]), other)
        add_lot(code, "mfr_mismatch", src["batch_true_text"], src["mfg_month"], src["expiry_month"], {}, {"1": "review", "2": "review"},
                ["same batch and product text as an alert row but a different manufacturer"], extra={"mirrors": src["lot_id"]})

    # --- unrelated lots. Two kinds, both with invented batch numbers:
    #   (a) generics that appear in NO alert (fictional makers): plain stock the matcher should leave alone
    #   (b) products whose name does appear in the alerts, but other batches (a name-only matcher freezes them)
    picked_batches = {norm_batch(l["alert_batch"]) for l in lots.values() if l["role"] == "affected"}
    alert_text = " ".join(e.product_name.lower() for e in all_alert)
    generics = [g for g in GENERICS if g.split()[0].lower() not in alert_text]
    unrelated_items: list[tuple[str, AlertEntry]] = []
    for g in generics:
        code = new_item(g, rng.choice(FICTIONAL_MAKERS))
        for _ in range(rng.choice([1, 2, 2, 3])):
            b = fake_batch(rng, taken)
            taken.add(norm_batch(b))
            mfg = shift_month("2025-01", rng.randint(0, 14))
            add_lot(code, "unrelated", b, mfg, shift_month(mfg, 24), {}, {"1": "no_hold", "2": "no_hold"}, ["product not in any alert"])
    other_rows = [e for e in all_alert if usable(e) and norm_batch(e.batch_no) not in picked_batches]
    rng.shuffle(other_rows)
    for e in other_rows[:30]:
        code = new_item(re.sub(r"\s+", " ", e.product_name).strip().rstrip(",.)"), short_mfr(e.manufacturer))
        unrelated_items.append((code, e))
        for _ in range(rng.choice([1, 1, 2])):
            b = fake_batch(rng, taken)
            taken.add(norm_batch(b))
            mfg = shift_month("2025-01", rng.randint(0, 14))
            add_lot(code, "unrelated_namealike", b, mfg, shift_month(mfg, 24), {}, {"1": "no_hold", "2": "no_hold"},
                    ["product name appears in an alert (other batch)"])

    # --- batch-number collisions: a different product whose batch equals an alert batch
    short_alerts = [e for e in all_alert if usable(e) and len(norm_batch(e.batch_no)) <= 5][:40]
    for e in rng.sample(short_alerts, min(8, len(short_alerts))):
        code, src = rng.choice(unrelated_items)
        if norm_batch(src.batch_no) == norm_batch(e.batch_no) or src.product_name == e.product_name:
            continue
        add_lot(code, "collision", e.batch_no, "2025-03", "2027-02", {}, {"1": "no_hold", "2": "no_hold"},
                ["batch number equals an alert batch of a different product"], extra={"collides_with": e.batch_no})

    # ---------- stock rows, purchases, customers, sales ----------
    date_styles = ["mm/yyyy", "mon-yy", "yyyy-mm", "dd/mm/yyyy", "mon yyyy"]
    purchases: list[dict] = []
    sales: list[dict] = []
    item_by_code = {i["item_code"]: i for i in items}
    customers = []
    combos = [(stem, c) for stem in CUSTOMER_STEMS for c in CITIES]
    for n, (stem, (city, st)) in enumerate(rng.sample(combos, 60), start=1):
        customers.append({"customer_id": f"C{n:03d}", "name": f"[SYNTHETIC] {stem}, {city}",
                          "type": "hospital" if "Hospital" in stem or "Nursing" in stem else "clinic" if "Clinic" in stem else "pharmacy",
                          "city": city, "state": st, "contact_email": f"c{n:03d}@example.invalid", "_synthetic": "Y"})
    suppliers = ["SYNTH TRADERS NORTH", "SYNTH TRADERS WEST", "SYNTH TRADERS SOUTH"]
    inv_no = 0
    line_no = 0
    ledger_gap_lots = set(rng.sample([k for k, l in lots.items() if l["role"] in ("affected", "unrelated", "unrelated_namealike")], 5))

    for lot_id, lot in lots.items():
        item = item_by_code[lot["item_code"]]
        upb = item["units_per_box"]
        boxes = rng.randint(4, 40)
        received = boxes * upb
        mfg_m = lot["mfg_month"]
        p_month = shift_month(mfg_m, rng.randint(1, 4)) if mfg_m else "2025-09"
        p_date = date(int(p_month[:4]), int(p_month[5:]), rng.randint(1, 27))
        if p_date > AS_OF - timedelta(days=30):
            p_date = AS_OF - timedelta(days=rng.randint(40, 120))
        inv_no += 1
        mfr_name = item["mfr_name"]
        purchases.append({"purchase_invoice": f"PI-{inv_no:05d}", "date": p_date.isoformat(),
                          "supplier": rng.choice([mfr_name or suppliers[0], mfr_name or suppliers[1], rng.choice(suppliers)]),
                          "item_code": item["item_code"], "batch_raw": lot["batch_true_text"], "qty_boxes": boxes,
                          "units_per_box": upb, "warehouse": lot["warehouse"], "_synthetic": "Y"})
        sold_total = int(received * rng.choice([0, 0, 0.1, 0.3, 0.5, 0.8])) if lot["role"] != "mfr_mismatch" else int(received * 0.3)
        n_lines = 0 if sold_total == 0 else rng.randint(1, 4)
        left = sold_total
        for k in range(n_lines):
            qty = left if k == n_lines - 1 else max(1, int(left * rng.uniform(0.2, 0.6)))
            left -= qty
            if qty <= 0:
                continue
            line_no += 1
            c = rng.choice(customers)
            s_date = p_date + timedelta(days=rng.randint(5, 150))
            s_date = min(s_date, AS_OF - timedelta(days=rng.randint(1, 20)))
            blank = lot["role"] == "affected" and rng.random() < 0.12
            b_text = "" if blank else (batch_variant(lot["batch_true_text"], rng)[0] if rng.random() < 0.2 else lot["batch_true_text"])
            sales.append({"sale_line": f"SL-{line_no:05d}", "invoice_no": f"SI-{(line_no + 1) // 2 + 1000:05d}", "date": s_date.isoformat(),
                          "customer_id": c["customer_id"], "item_code": item["item_code"], "batch_raw": b_text,
                          "qty_units": qty, "warehouse": lot["warehouse"], "_synthetic": "Y", "_lot": lot_id})
        on_hand = received - sold_total
        gap = 0
        if lot_id in ledger_gap_lots and on_hand > 30:
            gap = rng.randint(5, 20)
            lot["ledger_gap_units"] = gap
        lot["received_units"], lot["sold_units"], lot["on_hand_true_units"] = received, sold_total, on_hand
        # one stock row, or two when the lot is split across warehouses
        splits = [(lot["warehouse"], on_hand + gap)]
        if lot.get("split_warehouse") and on_hand >= 20:
            first = on_hand // 2
            other = "WH-MUM" if lot["warehouse"] == "WH-DEL" else "WH-DEL"
            splits = [(lot["warehouse"], first + gap), (other, on_hand - first)]
        style = rng.choice(date_styles)
        for wh, qty in splits:
            sid = f"S{len(stock) + 1:04d}"
            stock.append({"stock_id": sid, "warehouse": wh, "item_code": item["item_code"], "batch_raw": lot["batch_true_text"],
                          "mfg_raw": month_text(lot["mfg_month"], rng, style), "expiry_raw": month_text(lot["expiry_month"], rng, style),
                          "qty_units": qty, "status": "AVAILABLE", "_synthetic": "Y", "_lot": lot_id})
            lot["stock_ids"].append(sid)

    # ---------- truth ----------
    stock_truth = {}
    for row in stock:
        lot = lots[row["_lot"]]
        stock_truth[row["stock_id"]] = {"lot_id": lot["lot_id"], "role": lot["role"], "expected": lot["expected"], "mess": lot["mess"]}
    exposure: dict[str, dict] = {"1": {}, "2": {}}
    unresolved_lines: dict[str, list] = {"1": [], "2": []}
    hold_items = {r: {lots[l]["item_code"] for l in lots if lots[l]["expected"][r] == "hold"} for r in ("1", "2")}
    for s in sales:
        lot = lots[s["_lot"]]
        for r in ("1", "2"):
            if lot["expected"][r] == "hold" and s["batch_raw"]:
                exposure[r].setdefault(s["customer_id"], []).append(s["sale_line"])
            elif lot["expected"][r] == "hold" and not s["batch_raw"]:
                unresolved_lines[r].append(s["sale_line"])
    truth = {
        "synthetic": True, "seed": seed, "as_of": AS_OF.isoformat(),
        "rounds": {"1": {"alerts": ["portal-JUL-2026"]}, "2": {"alerts": ["portal-JUL-2026", "portal-AUG-2026"]}},
        "expected_actions": ["hold", "review", "no_hold"],
        "note": "no_hold is a scoped finding about listed batches, never a safety clearance.",
        "stock": stock_truth,
        "lots": {k: {kk: vv for kk, vv in v.items() if kk != "stock_ids"} | {"stock_ids": v["stock_ids"]} for k, v in lots.items()},
        "exposed_customers": {r: {c: sorted(v) for c, v in d.items()} for r, d in exposure.items()},
        "unresolved_sales_lines": {r: sorted(v) for r, v in unresolved_lines.items()},
    }

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "items.csv", items)
    write_csv(out / "stock.csv", [{k: v for k, v in r.items() if not k.startswith("_lot")} for r in stock])
    write_csv(out / "purchases.csv", purchases)
    write_csv(out / "customers.csv", customers)
    write_csv(out / "sales.csv", [{k: v for k, v in r.items() if k != "_lot"} for r in sales])
    (out / "truth.json").write_text(json.dumps(truth, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "SYNTHETIC-FIXTURE.txt").write_text(
        "SYNTHETIC DATA. The distributor, customers, quantities, invoices and dates in this folder are invented.\n"
        "Only the alert rows they are built from (data/alerts/raw) are real CDSCO NSQ data.\n"
        "truth.json (the answer key) is for evaluation only and must not be given to the agent.\n", encoding="utf-8")
    counts = {}
    for l in lots.values():
        counts[l["role"]] = counts.get(l["role"], 0) + 1
    return {"lots": len(lots), "stock_rows": len(stock), "items": len(items), "sales_lines": len(sales),
            "purchases": len(purchases), "roles": counts,
            "expected_round1": count_actions(stock_truth, "1"), "expected_round2": count_actions(stock_truth, "2")}


def count_actions(stock_truth: dict, rnd: str) -> dict:
    out: dict[str, int] = {}
    for t in stock_truth.values():
        out[t["expected"][rnd]] = out.get(t["expected"][rnd], 0) + 1
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", default="data/fixtures")
    args = ap.parse_args()
    print(json.dumps(build(args.seed, args.out), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
