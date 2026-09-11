#!/usr/bin/env python3
"""Idempotently merge generated synthetic CSV batches into Snowflake."""
from __future__ import annotations

import argparse
import csv
import json
import uuid
from pathlib import Path

from snowflake_source.common import connect, identifier, unquoted_identifier

TABLE_COLUMNS = {
    "TRANSACTIONS": (
        "TRANSACTION_ID", "ACCOUNT_ID", "CUSTOMER_ID", "MERCHANT_ID", "DEVICE_ID",
        "TRANSACTION_TIMESTAMP", "AMOUNT", "CURRENCY", "TRANSACTION_TYPE",
        "MERCHANT_CATEGORY", "CHANNEL", "COUNTRY", "CARD_PRESENT", "TRANSACTION_STATUS",
        "SOURCE_BATCH",
    ),
    "TRANSACTION_RISK": (
        "TRANSACTION_ID", "RISK_SCORE", "RISK_BAND", "MODEL_VERSION", "SCORED_TIMESTAMP",
        "RISK_FACTORS_JSON", "SOURCE_BATCH",
    ),
    "MERCHANTS": (
        "MERCHANT_ID", "MERCHANT_NAME", "MERCHANT_CATEGORY", "CITY", "STATE", "COUNTRY",
        "MERCHANT_RISK_CATEGORY", "SOURCE_BATCH",
    ),
    "DIGITAL_SESSIONS": (
        "SESSION_ID", "CUSTOMER_ID", "DEVICE_ID", "DEVICE_TYPE", "OPERATING_SYSTEM",
        "LOGIN_TIMESTAMP", "LOGOUT_TIMESTAMP", "AUTHENTICATION_METHOD", "MFA_USED",
        "FAILED_ATTEMPTS", "COUNTRY", "STATE", "CITY", "SESSION_RISK_SCORE",
        "ACTIVITIES_JSON", "SOURCE_BATCH",
    ),
    "DEVICES": (
        "DEVICE_ID", "CUSTOMER_ID", "FIRST_SEEN", "LAST_SEEN", "TRUSTED",
        "DEVICE_FINGERPRINT", "OPERATING_SYSTEM", "OPERATING_SYSTEM_VERSION", "APP_VERSION",
        "RISK_SIGNALS_JSON", "SOURCE_BATCH",
    ),
    "FRAUD_ALERTS": (
        "ALERT_ID", "CUSTOMER_ID", "TRANSACTION_ID", "CREATED_TIMESTAMP", "ALERT_TYPE",
        "SEVERITY", "STATUS", "SIGNALS_JSON", "INVESTIGATOR_NOTES_JSON", "SOURCE_BATCH",
    ),
}
PRIMARY_KEYS = {table: columns[0] for table, columns in TABLE_COLUMNS.items()}


def read_csv(path: Path) -> tuple[list[str], list[tuple[str | None, ...]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        columns = [column.upper() for column in reader.fieldnames]
        rows = [tuple(None if row[name] == "" else row[name] for name in reader.fieldnames) for row in reader]
    return columns, rows


def validated_csv(
    table: str, path: Path
) -> tuple[list[str], list[tuple[str | None, ...]]]:
    if table not in PRIMARY_KEYS:
        raise ValueError(f"Unsupported table: {table}")
    columns, rows = read_csv(path)
    if tuple(columns) != TABLE_COLUMNS[table]:
        raise ValueError(
            f"{path} header must exactly match the approved {table} synthetic-data contract"
        )
    return columns, rows


def merge_rows(
    cursor,
    database: str,
    schema: str,
    table: str,
    columns: list[str],
    rows: list[tuple[str | None, ...]],
) -> int:
    database = unquoted_identifier(database, "database")
    schema = unquoted_identifier(schema, "schema")
    table = unquoted_identifier(table, "table")
    if table not in TABLE_COLUMNS or tuple(columns) != TABLE_COLUMNS[table]:
        raise ValueError(f"Columns do not match the approved {table} synthetic-data contract")
    if not rows:
        return 0
    key = PRIMARY_KEYS[table]
    qualified = f"{database}.{schema}.{table}"
    stage = f"STAGE_{table}_{uuid.uuid4().hex[:10].upper()}"
    column_sql = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    cursor.execute(f"CREATE TEMPORARY TABLE {stage} LIKE {qualified}")
    try:
        # Values are bound parameters; every interpolated identifier was either
        # normalized above or matched against the fixed TABLE_COLUMNS contract.
        cursor.executemany(
            f"INSERT INTO {stage} ({column_sql}) VALUES ({placeholders})",  # nosec B608
            rows,
        )
        cursor.execute(
            f"MERGE INTO {qualified} AS target USING {stage} AS source "
            f"ON target.{key} = source.{key} "
            "WHEN MATCHED THEN UPDATE ALL BY NAME "
            "WHEN NOT MATCHED THEN INSERT ALL BY NAME"
        )
    finally:
        cursor.execute(f"DROP TABLE IF EXISTS {stage}")
    return len(rows)


def merge_file(cursor, database: str, schema: str, table: str, path: Path) -> int:
    columns, rows = validated_csv(table, path)
    return merge_rows(cursor, database, schema, table, columns, rows)


def load_batch(root: Path, batch: str) -> dict[str, int]:
    batch_dir = root / batch
    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("classification") != "SYNTHETIC_TEST_DATA":
        raise ValueError("Refusing to load data without SYNTHETIC_TEST_DATA classification")
    database = identifier("SNOWFLAKE_DATABASE")
    schema = identifier("SNOWFLAKE_SCHEMA")
    prepared: dict[str, tuple[list[str], list[tuple[str | None, ...]]]] = {}
    for table in PRIMARY_KEYS:
        path = batch_dir / f"{table}.csv"
        if path.exists():
            prepared[table] = validated_csv(table, path)
    loaded: dict[str, int] = {}
    with connect() as connection:
        with connection.cursor() as cursor:
            for table, (columns, rows) in prepared.items():
                loaded[table] = merge_rows(cursor, database, schema, table, columns, rows)
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
