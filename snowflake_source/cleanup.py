#!/usr/bin/env python3
"""Drop only the dedicated POC schema and, when authorized, its custom roles."""
from __future__ import annotations

import argparse

from snowflake_source.common import connect, identifier
from snowflake_source.setup import (
    LOADER_ROLE_COMMENTS,
    MIRROR_ROLE_COMMENTS,
    require_managed_namespace,
)

CONFIRMATION = "DELETE_SYNTHETIC_POC_SCHEMA"


def cleanup_statements(include_roles: bool) -> list[str]:
    database = identifier("SNOWFLAKE_DATABASE")
    schema = identifier("SNOWFLAKE_SCHEMA")
    result = [f"DROP SCHEMA IF EXISTS {database}.{schema}"]
    if include_roles:
        result.extend([
            f"DROP ROLE IF EXISTS {identifier('SNOWFLAKE_LOADER_ROLE', 'FABRIC_POC_LOADER')}",
            f"DROP ROLE IF EXISTS {identifier('SNOWFLAKE_MIRROR_ROLE', 'FABRIC_POC_MIRROR')}",
        ])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--confirm-schema", required=True, help="Exact dedicated schema name")
    parser.add_argument(
        "--include-dedicated-roles",
        action="store_true",
        help="Also drop the two configured POC roles after confirming they are dedicated",
    )
    args = parser.parse_args()
    if args.confirm != CONFIRMATION:
        raise SystemExit(f"Refusing cleanup; pass --confirm {CONFIRMATION}")
    database = identifier("SNOWFLAKE_DATABASE")
    schema = identifier("SNOWFLAKE_SCHEMA")
    if args.confirm_schema.upper() != schema:
        raise SystemExit(f"Refusing cleanup; --confirm-schema must exactly identify {schema}")
    statements = cleanup_statements(args.include_dedicated_roles)
    with (
        connect("SNOWFLAKE_SETUP_ROLE", include_context=False) as connection,
        connection.cursor() as cursor,
    ):
        roles = {}
        if args.include_dedicated_roles:
            roles = {
                identifier("SNOWFLAKE_LOADER_ROLE", "FABRIC_POC_LOADER"): LOADER_ROLE_COMMENTS,
                identifier("SNOWFLAKE_MIRROR_ROLE", "FABRIC_POC_MIRROR"): MIRROR_ROLE_COMMENTS,
            }
        require_managed_namespace(cursor, database, schema, roles)
        for statement in statements:
            cursor.execute(statement)
    print("Configured Snowflake POC schema removed; customer database and warehouse were preserved")


if __name__ == "__main__":
    main()
