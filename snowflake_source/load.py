#!/usr/bin/env python3
"""Idempotently merge generated synthetic CSV batches into Snowflake."""
from __future__ import annotations

import argparse
import csv
import json
import uuid
from pathlib import Path

from snowflake_source.common import connect, identifier

PRIMARY_KEYS = {
    "TRANSACTIONS": "TRANSACTION_ID",
    "TRANSACTION_RISK": "TRANSACTION_ID",
    "MERCHANTS": "MERCHANT_ID",
    "DIGITAL_SESSIONS": "SESSION_ID",
    "DEVICES": "DEVICE_ID",
    "FRAUD_ALERTS": "ALERT_ID",
}


def read_csv(path: Path) -> tuple[list[str], list[tuple[str | None, ...]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        columns = [column.upper() for column in reader.fieldnames]
        rows = [tuple(None if row[name] == "" else row[name] for name in reader.fieldnames) for row in reader]
    return columns, rows


def merge_file(cursor, database: str, schema: str, table: str, path: Path) -> int:
    columns, rows = read_csv(path)
    if not rows:
        return 0
    if table not in PRIMARY_KEYS:
        raise ValueError(f"Unsupported table: {table}")
    key = PRIMARY_KEYS[table]
    if key not in columns:
        raise ValueError(f"{path} does not contain primary key {key}")
    qualified = f"{database}.{schema}.{table}"
    stage = f"STAGE_{table}_{uuid.uuid4().hex[:10].upper()}"
    column_sql = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    cursor.execute(f"CREATE TEMPORARY TABLE {stage} LIKE {qualified}")
    try:
        cursor.executemany(f"INSERT INTO {stage} ({column_sql}) VALUES ({placeholders})", rows)
        cursor.execute(
            f"MERGE INTO {qualified} AS target USING {stage} AS source "
            f"ON target.{key} = source.{key} "
            "WHEN MATCHED THEN UPDATE ALL BY NAME "
            "WHEN NOT MATCHED THEN INSERT ALL BY NAME"
        )
    finally:
        cursor.execute(f"DROP TABLE IF EXISTS {stage}")
    return len(rows)


def load_batch(root: Path, batch: str) -> dict[str, int]:
    batch_dir = root / batch
    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("classification") != "SYNTHETIC_TEST_DATA":
        raise ValueError("Refusing to load data without SYNTHETIC_TEST_DATA classification")
    database = identifier("SNOWFLAKE_DATABASE", "FABRIC_SNOWFLAKE_POC")
    schema = identifier("SNOWFLAKE_SCHEMA", "BANKING_SOURCE")
    loaded: dict[str, int] = {}
    with connect() as connection:
        with connection.cursor() as cursor:
            for table in PRIMARY_KEYS:
                path = batch_dir / f"{table}.csv"
                if path.exists():
                    loaded[table] = merge_file(cursor, database, schema, table, path)
        connection.commit()
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/snowflake"))
    parser.add_argument("--batch", choices=("initial", "incremental"), required=True)
    args = parser.parse_args()
    print(json.dumps(load_batch(args.data_dir, args.batch), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
