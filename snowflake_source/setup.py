#!/usr/bin/env python3
"""Render or explicitly apply idempotent Snowflake POC setup SQL."""
from __future__ import annotations

import argparse
from pathlib import Path

from snowflake_source.common import connect, identifier

ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "snowflake_source" / "sql" / "00_setup.sql"
SCHEMA_COMMENTS = {
    "Synthetic banking source tables for Fabric Mirroring",
    "Managed by fabric-snowflake-medallion-poc; synthetic source schema",
}
LOADER_ROLE_COMMENTS = {
    "Loads synthetic POC data only",
    "Managed by fabric-snowflake-medallion-poc; synthetic loader",
}
MIRROR_ROLE_COMMENTS = {
    "Least-privilege role used by Microsoft Fabric Mirroring",
    "Managed by fabric-snowflake-medallion-poc; Fabric mirror",
}


def render() -> str:
    values = {
        "DATABASE": identifier("SNOWFLAKE_DATABASE"),
        "SCHEMA": identifier("SNOWFLAKE_SCHEMA"),
        "WAREHOUSE": identifier("SNOWFLAKE_WAREHOUSE"),
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


def require_existing_object(cursor, kind: str, name: str) -> None:
    """Fail before mutation when a customer-owned database/warehouse is absent."""
    if kind not in {"DATABASES", "WAREHOUSES"}:
        raise ValueError(f"Unsupported Snowflake object kind: {kind}")
    cursor.execute(f"SHOW {kind} LIKE '{name}'")
    columns = [str(column[0]).lower() for column in cursor.description or []]
    if "name" not in columns:
        raise RuntimeError(f"Snowflake SHOW {kind} did not return a name column")
    name_index = columns.index("name")
    if not any(str(row[name_index]).upper() == name for row in cursor.fetchall()):
        singular = kind.removesuffix("S").lower()
        raise RuntimeError(
            f"Configured Snowflake {singular} {name!r} does not exist or is not visible; "
            "this repository never creates customer databases or warehouses"
        )


def require_managed_namespace(cursor, database: str, schema: str, roles: dict[str, set[str]]) -> None:
    """Reject reuse of a same-named customer schema or role not created by this POC."""
    cursor.execute(f"SHOW SCHEMAS LIKE '{schema}' IN DATABASE {database}")
    columns = [str(column[0]).lower() for column in cursor.description or []]
    for row in cursor.fetchall():
        values = dict(zip(columns, row))
        if (
            str(values.get("name", "")).upper() == schema
            and str(values.get("comment", "")) not in SCHEMA_COMMENTS
        ):
            raise RuntimeError(f"Schema {database}.{schema} already exists and is not marked as POC-managed")
    for role, allowed_comments in roles.items():
        cursor.execute(f"SHOW ROLES LIKE '{role}'")
        role_columns = [str(column[0]).lower() for column in cursor.description or []]
        for row in cursor.fetchall():
            values = dict(zip(role_columns, row))
            if str(values.get("name", "")).upper() == role and str(values.get("comment", "")) not in allowed_comments:
                raise RuntimeError(f"Role {role} already exists and is not marked as POC-managed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Execute setup; otherwise print rendered SQL")
    args = parser.parse_args()
    sql = render()
    if not args.apply:
        print(sql)
        return
    database = identifier("SNOWFLAKE_DATABASE")
    warehouse = identifier("SNOWFLAKE_WAREHOUSE")
    schema = identifier("SNOWFLAKE_SCHEMA")
    loader_role = identifier("SNOWFLAKE_LOADER_ROLE", "FABRIC_POC_LOADER")
    mirror_role = identifier("SNOWFLAKE_MIRROR_ROLE", "FABRIC_POC_MIRROR")
    # Authenticate without setting context so preflight can fail before any
    # mutation if customer-owned objects are missing.
    with (
        connect("SNOWFLAKE_SETUP_ROLE", include_context=False) as connection,
        connection.cursor() as cursor,
    ):
        require_existing_object(cursor, "DATABASES", database)
        require_existing_object(cursor, "WAREHOUSES", warehouse)
        require_managed_namespace(
            cursor,
            database,
            schema,
            {
                loader_role: LOADER_ROLE_COMMENTS,
                mirror_role: MIRROR_ROLE_COMMENTS,
            },
        )
        for statement in statements(sql):
            cursor.execute(statement)
    print("Snowflake POC objects configured")


if __name__ == "__main__":
    main()
