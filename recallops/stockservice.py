"""A small local stock service over the SYNTHETIC fixtures, with real state transitions.

It stands in for the distributor's billing/inventory system. Holds are state changes, not log lines:
a stock row goes AVAILABLE -> HELD, and the only way to know it happened is to read it back.

* place_hold is idempotent per action_id: repeating an action_id returns the original result and
  writes nothing, which is what lets a caller safely retry after a timeout.
* A different action_id on an already-held row is rejected, so a blind retry with a fresh id is
  visible as a conflict instead of a silent double write.
* Failure injection (for the recovery demo): `inject_timeout_after_write` makes the next N
  place_hold calls commit and then raise TimeoutError, as a flaky network would.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

FIXTURES = Path("data/fixtures")


class StockError(Exception):
    pass


class StockService:
    def __init__(self, db_path: str | Path = ":memory:", fixtures_dir: str | Path = FIXTURES):
        self.db = sqlite3.connect(str(db_path))
        self.db.row_factory = sqlite3.Row
        self.fixtures_dir = Path(fixtures_dir)
        self._timeouts_left = 0
        self._create()
        self._load()

    # ---- setup
    def _create(self) -> None:
        self.db.executescript(
            """
            DROP TABLE IF EXISTS stock; DROP TABLE IF EXISTS items; DROP TABLE IF EXISTS sales;
            DROP TABLE IF EXISTS customers; DROP TABLE IF EXISTS purchases; DROP TABLE IF EXISTS events;
            CREATE TABLE stock (stock_id TEXT PRIMARY KEY, warehouse TEXT, item_code TEXT, batch_raw TEXT,
                                mfg_raw TEXT, expiry_raw TEXT, qty_units INTEGER, status TEXT, hold_reason TEXT);
            CREATE TABLE items (item_code TEXT PRIMARY KEY, item_name TEXT, mfr_name TEXT, units_per_box INTEGER);
            CREATE TABLE sales (sale_line TEXT PRIMARY KEY, invoice_no TEXT, date TEXT, customer_id TEXT, item_code TEXT,
                                batch_raw TEXT, qty_units INTEGER, warehouse TEXT);
            CREATE TABLE customers (customer_id TEXT PRIMARY KEY, name TEXT, type TEXT, city TEXT, state TEXT, contact_email TEXT);
            CREATE TABLE purchases (purchase_invoice TEXT PRIMARY KEY, date TEXT, supplier TEXT, item_code TEXT, batch_raw TEXT,
                                    qty_boxes INTEGER, units_per_box INTEGER, warehouse TEXT);
            CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, action_id TEXT, stock_id TEXT, kind TEXT,
                                 from_status TEXT, to_status TEXT, reason TEXT);
            CREATE UNIQUE INDEX events_action ON events(action_id) WHERE action_id IS NOT NULL;
            """
        )

    def _load(self) -> None:
        for table, cols in (("stock", ["stock_id", "warehouse", "item_code", "batch_raw", "mfg_raw", "expiry_raw", "qty_units", "status"]),
                            ("items", ["item_code", "item_name", "mfr_name", "units_per_box"]),
                            ("sales", ["sale_line", "invoice_no", "date", "customer_id", "item_code", "batch_raw", "qty_units", "warehouse"]),
                            ("customers", ["customer_id", "name", "type", "city", "state", "contact_email"]),
                            ("purchases", ["purchase_invoice", "date", "supplier", "item_code", "batch_raw", "qty_boxes", "units_per_box", "warehouse"])):
            with open(self.fixtures_dir / f"{table}.csv", encoding="utf-8", newline="") as f:
                rows = [[r[c] for c in cols] for r in csv.DictReader(f)]
            self.db.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", rows)
        self.db.commit()

    # ---- reads
    def get_stock(self, stock_id: str) -> dict:
        row = self.db.execute("SELECT * FROM stock WHERE stock_id=?", (stock_id,)).fetchone()
        if row is None:
            raise StockError(f"unknown stock_id {stock_id}")
        return dict(row)

    def list_stock(self, status: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM stock", ()
        if status:
            q, args = q + " WHERE status=?", (status,)
        return [dict(r) for r in self.db.execute(q + " ORDER BY stock_id", args)]

    def items(self) -> dict[str, dict]:
        return {r["item_code"]: dict(r) for r in self.db.execute("SELECT * FROM items")}

    def sales_for_item(self, item_code: str) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM sales WHERE item_code=? ORDER BY date, sale_line", (item_code,))]

    def purchases_for_item(self, item_code: str) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM purchases WHERE item_code=? ORDER BY date", (item_code,))]

    def customer(self, customer_id: str) -> dict:
        return dict(self.db.execute("SELECT * FROM customers WHERE customer_id=?", (customer_id,)).fetchone())

    def events(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM events ORDER BY seq")]

    # ---- writes
    def inject_timeout_after_write(self, n: int = 1) -> None:
        self._timeouts_left = n

    def place_hold(self, stock_id: str, reason: str, action_id: str) -> dict:
        prior = self.db.execute("SELECT * FROM events WHERE action_id=?", (action_id,)).fetchone()
        if prior is not None:  # idempotent replay: same action_id never writes twice
            return {"stock_id": prior["stock_id"], "status": self.get_stock(prior["stock_id"])["status"], "replayed": True}
        row = self.get_stock(stock_id)
        if row["status"] != "AVAILABLE":
            raise StockError(f"{stock_id} is {row['status']}, not AVAILABLE")
        with self.db:
            self.db.execute("UPDATE stock SET status='HELD', hold_reason=? WHERE stock_id=?", (reason, stock_id))
            self.db.execute("INSERT INTO events (action_id, stock_id, kind, from_status, to_status, reason) VALUES (?,?,?,?,?,?)",
                            (action_id, stock_id, "hold", "AVAILABLE", "HELD", reason))
        if self._timeouts_left > 0:  # the write is durable but the caller never hears back
            self._timeouts_left -= 1
            raise TimeoutError(f"place_hold({stock_id}) timed out waiting for the response")
        return {"stock_id": stock_id, "status": "HELD", "replayed": False}

    def release_hold(self, stock_id: str, reason: str, action_id: str) -> dict:
        if self.db.execute("SELECT 1 FROM events WHERE action_id=?", (action_id,)).fetchone():
            return {"stock_id": stock_id, "status": self.get_stock(stock_id)["status"], "replayed": True}
        row = self.get_stock(stock_id)
        if row["status"] != "HELD":
            raise StockError(f"{stock_id} is {row['status']}, not HELD")
        with self.db:
            self.db.execute("UPDATE stock SET status='AVAILABLE', hold_reason=NULL WHERE stock_id=?", (stock_id,))
            self.db.execute("INSERT INTO events (action_id, stock_id, kind, from_status, to_status, reason) VALUES (?,?,?,?,?,?)",
                            (action_id, stock_id, "release", "HELD", "AVAILABLE", reason))
        return {"stock_id": stock_id, "status": "AVAILABLE", "replayed": False}
