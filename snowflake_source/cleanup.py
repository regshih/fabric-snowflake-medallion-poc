#!/usr/bin/env python3
"""Drop only the configured Snowflake POC database and optional warehouse/roles."""
from __future__ import annotations

import argparse

from snowflake_source.common import connect, identifier

CONFIRMATION = "DELETE_SYNTHETIC_SNOWFLAKE_POC"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--include-shared-objects", action="store_true", help="Also drop configured warehouse and roles")
    args = parser.parse_args()
    if args.confirm != CONFIRMATION:
        raise SystemExit(f"Refusing cleanup; pass --confirm {CONFIRMATION}")
    database = identifier("SNOWFLAKE_DATABASE", "FABRIC_SNOWFLAKE_POC")
    statements = [f"DROP DATABASE IF EXISTS {database}"]
    if args.include_shared_objects:
        statements.extend([
            f"DROP WAREHOUSE IF EXISTS {identifier('SNOWFLAKE_WAREHOUSE', 'FABRIC_POC_WH')}",
            f"DROP ROLE IF EXISTS {identifier('SNOWFLAKE_LOADER_ROLE', 'FABRIC_POC_LOADER')}",
            f"DROP ROLE IF EXISTS {identifier('SNOWFLAKE_MIRROR_ROLE', 'FABRIC_POC_MIRROR')}",
        ])
    with connect() as connection:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
    print("Configured Snowflake POC objects removed")


if __name__ == "__main__":
    main()
