#!/usr/bin/env python3
"""Render or explicitly apply idempotent Snowflake POC setup SQL."""
from __future__ import annotations

import argparse
from pathlib import Path

from snowflake_source.common import connect, identifier

ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "snowflake_source" / "sql" / "00_setup.sql"


def render() -> str:
    values = {
        "DATABASE": identifier("SNOWFLAKE_DATABASE", "FABRIC_SNOWFLAKE_POC"),
        "SCHEMA": identifier("SNOWFLAKE_SCHEMA", "BANKING_SOURCE"),
        "WAREHOUSE": identifier("SNOWFLAKE_WAREHOUSE", "FABRIC_POC_WH"),
        "LOADER_ROLE": identifier("SNOWFLAKE_LOADER_ROLE", "FABRIC_POC_LOADER"),
        "MIRROR_ROLE": identifier("SNOWFLAKE_MIRROR_ROLE", "FABRIC_POC_MIRROR"),
    }
    sql = SQL_PATH.read_text(encoding="utf-8")
    for name, value in values.items():
        sql = sql.replace("{{" + name + "}}", value)
    if "{{" in sql:
        raise RuntimeError("An unresolved setup placeholder remains")
    return sql


def statements(sql: str) -> list[str]:
    return [value.strip() for value in sql.split(";") if value.strip() and not value.lstrip().startswith("-- Review")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Execute setup; otherwise print rendered SQL")
    args = parser.parse_args()
    sql = render()
    if not args.apply:
        print(sql)
        return
    # The database, schema, and warehouse do not exist on the first run, so
    # authenticate without asking the connector to establish that context.
    with connect("SNOWFLAKE_SETUP_ROLE", include_context=False) as connection:
        with connection.cursor() as cursor:
            for statement in statements(sql):
                cursor.execute(statement)
    print("Snowflake POC objects configured")


if __name__ == "__main__":
    main()
