"""Parse NSQ rows copied from the CDSCO online portal (cdscoonline.gov.in/CDSCO/viewPublicNSQDrug).

Newer alerts are not PDFs: the portal renders one table per reporting month from JSON, with
month names ("Jun-2026") instead of MM/YYYY. data/alerts/raw/portal-<MON>-<YYYY>.jsonl holds each
row exactly as the portal served it, one JSON array per line, in this column order (the portal's
own field names, keys dropped to keep the files small):

    str_product_name, str_batch_no, dt_manufacturing_date, dt_expiry_date, str_manufactured_by,
    str_nsq_result, str_reporting_source, str_reported_by_lab_or_state, dt_reporting_month_year

Values are verbatim, including the portal's typos, stray line breaks and "?" placeholders.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

from .alerts import AlertEntry, clean

COLUMNS = (
    "str_product_name",
    "str_batch_no",
    "dt_manufacturing_date",
    "dt_expiry_date",
    "str_manufactured_by",
    "str_nsq_result",
    "str_reporting_source",
    "str_reported_by_lab_or_state",
    "dt_reporting_month_year",
)
MONTHS = {m: i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), start=1)}
MON_YEAR_RE = re.compile(r"^\s*([A-Za-z]{3})-(\d{4})\s*$")
NO_BATCH = {"", "not mentioned", "na", "n/a", "nil", "-"}


def parse_mon_year(cell: str | None) -> str | None:
    """"Jun-2026" / "AUG-2026" -> "2026-06" / "2026-08"; anything else -> None."""
    m = MON_YEAR_RE.match(cell or "")
    if not m or m.group(1).lower() not in MONTHS:
        return None
    return f"{int(m.group(2)):04d}-{MONTHS[m.group(1).lower()]:02d}"


def parse_portal_jsonl(path: str | Path) -> list[AlertEntry]:
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    entries: list[AlertEntry] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if len(row) != len(COLUMNS):
            raise ValueError(f"{path.name}:{line_no}: expected {len(COLUMNS)} columns, got {len(row)}")
        raw = dict(zip(COLUMNS, row))
        batch = clean(raw["str_batch_no"])
        mfg, exp = parse_mon_year(raw["dt_manufacturing_date"]), parse_mon_year(raw["dt_expiry_date"])
        issues: list[str] = []
        if batch.lower() in NO_BATCH:
            issues.append(f"no usable batch number: {raw['str_batch_no']!r}")
        if raw["dt_manufacturing_date"] is None:
            issues.append("manufacturing date missing")
        elif mfg is None:
            issues.append(f"manufacturing date not Mon-YYYY: {raw['dt_manufacturing_date']!r}")
        if raw["dt_expiry_date"] is None:
            issues.append("expiry date missing")
        elif exp is None:
            issues.append(f"expiry date not Mon-YYYY: {raw['dt_expiry_date']!r}")
        if mfg and exp and exp < mfg:
            issues.append(f"expiry {exp} is before manufacture {mfg}")
        if batch != batch.strip(" ,"):
            issues.append("batch has stray punctuation")
        if re.search(r"[\r\n]", raw["str_batch_no"] or ""):
            issues.append("batch number was split across lines")
        entries.append(
            AlertEntry(
                source_file=path.name,
                source_sha256=digest,
                page=0,
                sno=str(line_no),
                product_name=clean(raw["str_product_name"]),
                batch_no=batch,
                mfg_month=mfg,
                expiry_month=exp,
                manufacturer=clean(raw["str_manufactured_by"]),
                nsq_result=clean(raw["str_nsq_result"]),
                lab=clean(raw["str_reported_by_lab_or_state"]),
                raw={k: raw[k] for k in ("str_batch_no", "dt_manufacturing_date", "dt_expiry_date")},
                issues=issues,
                reporting_source=clean(raw["str_reporting_source"]),
                report_month=parse_mon_year(raw["dt_reporting_month_year"]),
            )
        )
    return entries


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m recallops.portal <portal-MON-YYYY.jsonl> [out.json]")
        return 2
    src = Path(argv[1])
    entries = parse_portal_jsonl(src)
    out = Path(argv[2]) if len(argv) > 2 else Path("data/alerts/parsed") / (src.stem + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([asdict(e) for e in entries], indent=2, ensure_ascii=False), encoding="utf-8")
    bad = [e for e in entries if e.issues]
    print(f"{src.name}: {len(entries)} entries, {len(bad)} with parse issues -> {out}")
    for e in bad[:15]:
        print(f"  #{e.sno} {e.product_name[:40]!r} [{e.batch_no}]: {'; '.join(e.issues)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
