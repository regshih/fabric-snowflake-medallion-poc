#!/usr/bin/env python3
"""Validate generated CSVs or live Snowflake source tables."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

TABLE_KEYS = {
    "TRANSACTIONS": "TRANSACTION_ID",
    "TRANSACTION_RISK": "TRANSACTION_ID",
    "MERCHANTS": "MERCHANT_ID",
    "DIGITAL_SESSIONS": "SESSION_ID",
    "DEVICES": "DEVICE_ID",
    "FRAUD_ALERTS": "ALERT_ID",
}
PATTERNS = {
    "TRANSACTION_ID": re.compile(r"^TXN-\d{9}$"),
    "CUSTOMER_ID": re.compile(r"^CUST-\d{6}$"),
    "ACCOUNT_ID": re.compile(r"^ACCT\d{9}$"),
    "MERCHANT_ID": re.compile(r"^MER\d{6}$"),
    "DEVICE_ID": re.compile(r"^DEVICE-\d{6}$"),
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_files(root: Path) -> dict[str, object]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    observed: dict[str, int] = {}
    loaded: dict[str, list[dict[str, str]]] = {}
    for table, expected in manifest.get("counts", {}).items():
        path = root / f"{table}.csv"
        if not path.is_file():
            failures.append(f"missing {path.name}")
            continue
        table_rows = rows(path)
        loaded[table] = table_rows
        observed[table] = len(table_rows)
        if len(table_rows) != expected:
            failures.append(f"{table}: expected {expected}, observed {len(table_rows)}")
        key = TABLE_KEYS[table]
        values = [row.get(key, "") for row in table_rows]
        if len(values) != len(set(values)):
            failures.append(f"{table}: duplicate {key}")
    for table, table_rows in loaded.items():
        for row_number, row in enumerate(table_rows, 2):
            for column, pattern in PATTERNS.items():
                if column in row and row[column] and not pattern.fullmatch(row[column]):
                    failures.append(f"{table}:{row_number}: invalid {column}")
                    break
    if manifest.get("batch") == "initial" and loaded:
        transaction_ids = {row["TRANSACTION_ID"] for row in loaded.get("TRANSACTIONS", [])}
        merchant_ids = {row["MERCHANT_ID"] for row in loaded.get("MERCHANTS", [])}
        device_ids = {row["DEVICE_ID"] for row in loaded.get("DEVICES", [])}
        for row in loaded.get("TRANSACTION_RISK", []):
            if row["TRANSACTION_ID"] not in transaction_ids:
                failures.append("TRANSACTION_RISK contains orphan TRANSACTION_ID")
                break
        for row in loaded.get("TRANSACTIONS", []):
            if row["MERCHANT_ID"] not in merchant_ids:
                failures.append("TRANSACTIONS contains orphan MERCHANT_ID")
                break
        for row in loaded.get("DIGITAL_SESSIONS", []):
            if row["DEVICE_ID"] not in device_ids:
                failures.append("DIGITAL_SESSIONS contains orphan DEVICE_ID")
                break
    result = {"classification": manifest.get("classification"), "batch": manifest.get("batch"), "counts": observed, "failures": failures}
    if failures:
        raise ValueError(json.dumps(result, indent=2))
    return result


def validate_live() -> dict[str, object]:
    from snowflake_source.common import connect, identifier

    database = identifier("SNOWFLAKE_DATABASE", "FABRIC_SNOWFLAKE_POC")
    schema = identifier("SNOWFLAKE_SCHEMA", "BANKING_SOURCE")
    counts: dict[str, int] = {}
    with connect() as connection:
        with connection.cursor() as cursor:
            for table in TABLE_KEYS:
                cursor.execute(f"SELECT COUNT(*) FROM {database}.{schema}.{table}")
                counts[table] = int(cursor.fetchone()[0])
            cursor.execute(
                f"SELECT COUNT(*) FROM {database}.{schema}.FRAUD_ALERTS a "
                f"JOIN {database}.{schema}.TRANSACTIONS t ON a.TRANSACTION_ID=t.TRANSACTION_ID"
            )
            joined_alerts = int(cursor.fetchone()[0])
    if any(value <= 0 for value in counts.values()):
        raise ValueError(f"One or more source tables are empty: {counts}")
    return {"database": database, "schema": schema, "counts": counts, "joined_alerts": joined_alerts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("files", "live"), default="files")
    parser.add_argument("--data-dir", type=Path, default=Path("data/snowflake/initial"))
    args = parser.parse_args()
    result = validate_files(args.data_dir) if args.mode == "files" else validate_live()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
