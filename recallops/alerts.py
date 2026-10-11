"""Parse a CDSCO monthly "NSQ Alert" PDF into structured entries.

Source: Central Drugs Standard Control Organisation, "NSQ Alert For The Month of ...".
Each alert lists drug batches that failed a quality test (Not of Standard Quality).
A failure is specific to the tested batch; it says nothing about other batches.

Dates in the alerts are month/year only (MM/YYYY), so they are kept as "YYYY-MM".
Raw cell text is preserved next to every parsed field so nothing is lost.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pdfplumber

HEADER_KEYS = ("s.no", "product", "batch")
MONTH_RE = re.compile(r"^\s*(\d{1,2})\s*/\s*(\d{4})\s*$")


@dataclass
class AlertEntry:
    source_file: str
    source_sha256: str
    page: int
    sno: str
    product_name: str
    batch_no: str
    mfg_month: str | None  # "YYYY-MM" or None when the cell did not parse
    expiry_month: str | None
    manufacturer: str
    nsq_result: str
    lab: str
    raw: dict = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    # Only the online portal carries these; the monthly PDFs do not.
    reporting_source: str = ""
    report_month: str | None = None  # "YYYY-MM" the alert was published for


def clean(text: str | None) -> str:
    """Collapse the line breaks and runs of spaces that PDF cells carry."""
    return re.sub(r"\s+", " ", (text or "").replace(" ", " ")).strip()


FULL_DATE_RE = re.compile(r"^\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\s*$")


def parse_month(cell: str) -> str | None:
    """MM/YYYY -> "YYYY-MM". A stray DD/MM/YYYY (seen in the March 2025 alert) keeps its month."""
    m = MONTH_RE.match(cell)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
    else:
        m = FULL_DATE_RE.match(cell)
        if not m:
            return None
        month, year = int(m.group(2)), int(m.group(3))
    if not 1 <= month <= 12:
        return None
    return f"{year:04d}-{month:02d}"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_header(row: list[str | None]) -> bool:
    joined = " ".join(clean(c).lower() for c in row)
    return all(k in joined for k in HEADER_KEYS)


def parse_alert_pdf(path: str | Path) -> list[AlertEntry]:
    path = Path(path)
    digest = sha256_of(path)
    entries: list[AlertEntry] = []
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables():
                for row in table:
                    if not row or is_header(row):
                        continue
                    cells = [clean(c) for c in row]
                    if len(cells) < 8 or not (cells[1] or cells[5] or cells[6]):
                        continue  # blank or malformed row
                    sno, product, batch, mfg, exp, maker, result, lab = cells[:8]
                    if not sno and not batch and entries:
                        # An entry that straddles a page break leaves a fragment at the top of
                        # the next page: no S.No and no batch. It continues the previous entry,
                        # cell by cell, so join the text back on.
                        prev = entries[-1]
                        prev.product_name = clean(f"{prev.product_name} {product}")
                        prev.manufacturer = clean(f"{prev.manufacturer} {maker}")
                        prev.nsq_result = clean(f"{prev.nsq_result} {result}")
                        prev.lab = clean(f"{prev.lab} {lab}")
                        prev.issues.append(f"joined a continuation fragment from page {page_no}")
                        continue
                    issues = []
                    mfg_m, exp_m = parse_month(mfg), parse_month(exp)
                    if mfg_m is None:
                        issues.append(f"manufacturing date not MM/YYYY: {mfg!r}")
                    if exp_m is None:
                        issues.append(f"expiry date not MM/YYYY: {exp!r}")
                    if not batch:
                        issues.append("batch number is empty")
                    entries.append(
                        AlertEntry(
                            source_file=path.name,
                            source_sha256=digest,
                            page=page_no,
                            sno=sno.rstrip("."),
                            product_name=product,
                            batch_no=batch,
                            mfg_month=mfg_m,
                            expiry_month=exp_m,
                            manufacturer=maker,
                            nsq_result=result,
                            lab=lab,
                            raw={"mfg": mfg, "expiry": exp},
                            issues=issues,
                        )
                    )
    return entries


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m recallops.alerts <alert.pdf> [out.json]")
        return 2
    src = Path(argv[1])
    entries = parse_alert_pdf(src)
    out = Path(argv[2]) if len(argv) > 2 else Path("data/alerts/parsed") / (src.stem + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([asdict(e) for e in entries], indent=2, ensure_ascii=False), encoding="utf-8")
    bad = [e for e in entries if e.issues]
    print(f"{src.name}: {len(entries)} entries, {len(bad)} with parse issues -> {out}")
    for e in bad[:10]:
        print(f"  #{e.sno} {e.product_name[:40]!r}: {'; '.join(e.issues)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
