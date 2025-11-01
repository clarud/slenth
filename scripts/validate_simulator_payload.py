"""
Validate simulator payloads against Transaction schema without hitting the API.

Loads a few rows from transactions_mock_1000_for_participants.csv, converts them
using the same logic as scripts/transaction_simulator.py, and validates them
against app.schemas.transaction.TransactionCreate. Prints a concise report.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List

from app.schemas.transaction import TransactionCreate


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in {"true", "1", "yes", "y"}:
        return True
    if s in {"false", "0", "no", "n"}:
        return False
    return None


def _to_float(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return None


def _to_int(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except Exception:
        return None


BOOLEAN_FIELDS = {
    "swift_f50_present",
    "swift_f59_present",
    "travel_rule_complete",
    "fx_indicator",
    "customer_is_pep",
    "edd_required",
    "edd_performed",
    "sow_documented",
    "is_advised",
    "product_complex",
    "suitability_assessed",
    "product_has_va_exposure",
    "va_disclosure_provided",
    "cash_id_verified",
}

FLOAT_FIELDS = {
    "amount",
    "fx_applied_rate",
    "fx_market_rate",
    "fx_spread_bps",
    "daily_cash_total_customer",
}

INT_FIELDS = {"daily_cash_txn_count"}


def transform_row(row: Dict[str, Any]) -> Dict[str, Any]:
    # Mirror scripts/transaction_simulator.py
    cleaned = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
    payload: Dict[str, Any] = {}
    for key, val in cleaned.items():
        if key in BOOLEAN_FIELDS:
            b = _to_bool(val)
            if b is not None:
                payload[key] = b
        elif key in FLOAT_FIELDS:
            f = _to_float(val)
            if f is not None:
                payload[key] = f
        elif key in INT_FIELDS:
            iv = _to_int(val)
            if iv is not None:
                payload[key] = iv
        else:
            if val != "":
                payload[key] = val
    return payload


def main():
    csv_path = Path(__file__).resolve().parent.parent / "transactions_mock_1000_for_participants.csv"
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, Any]] = []
        for i, row in enumerate(reader):
            rows.append(row)
            if len(rows) >= 5:
                break

    print(f"Loaded {len(rows)} sample rows from {csv_path.name}")
    ok = 0
    bad = 0
    for idx, row in enumerate(rows, start=1):
        payload = transform_row(row)
        try:
            tx = TransactionCreate(**payload)
            _ = tx  # silence linter
            ok += 1
            print(f"Row {idx}: OK")
        except Exception as e:
            bad += 1
            print(f"Row {idx}: FAIL -> {e}")

    print("\nSummary:")
    print(f"  OK:   {ok}")
    print(f"  FAIL: {bad}")


if __name__ == "__main__":
    main()

