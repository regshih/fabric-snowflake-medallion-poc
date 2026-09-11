#!/usr/bin/env python3
"""Create a reusable Fabric cloud connection for Snowflake key-pair auth.

Private-key material and its passphrase are read only from ignored local files.
They are sent to the Fabric Connections API over TLS and are never printed or
written into a tracked Fabric item definition.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from infra.fabric.client import FabricApiError, FabricClient


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise RuntimeError(f"Set {name} before creating the Fabric Snowflake connection")
    return value


def snowflake_server(account: str) -> str:
    """Convert an org-account identifier into the Snowflake server hostname."""
    value = account.strip().lower()
    if value.startswith("https://"):
        value = value.removeprefix("https://")
    if value.startswith("http://"):
        value = value.removeprefix("http://")
    value = value.rstrip("/")
    return value if value.endswith(".snowflakecomputing.com") else f"{value}.snowflakecomputing.com"


def connection_payload(
    *,
    display_name: str,
    server: str,
    warehouse: str,
    role: str,
    username: str,
    private_key: str,
    passphrase: str,
) -> dict[str, Any]:
    """Build the documented ShareableCloud KeyPair request."""
    return {
        "connectivityType": "ShareableCloud",
        "displayName": display_name,
        "connectionDetails": {
            "type": "Snowflake",
            "creationMethod": "Snowflake.Databases",
            "parameters": [
                {"dataType": "Text", "name": "server", "value": server.lower()},
                {"dataType": "Text", "name": "warehouse", "value": warehouse},
                {"dataType": "Text", "name": "Role", "value": role},
            ],
        },
        "privacyLevel": "Organizational",
        "credentialDetails": {
            "singleSignOnType": "None",
            "connectionEncryption": "NotEncrypted",
            "skipTestConnection": False,
            "credentials": {
                "credentialType": "KeyPair",
                "identifier": username,
                "privateKey": private_key,
                "passphrase": passphrase,
            },
        },
        "allowUsageInUserControlledCode": True,
    }


def ensure_connection(client: FabricClient, payload: dict[str, Any]) -> dict[str, Any]:
    display_name = str(payload["displayName"])
    existing = client._named(client.list_all("connections"), display_name)
    if existing:
        return existing
    response = client.request("POST", "connections", json=payload)
    connection = client._json(response)
    if not connection.get("id"):
        connection = client._named(client.list_all("connections"), display_name) or connection
    if not connection.get("id"):
        raise FabricApiError("Fabric accepted the request but the connection was not visible")
    return connection


def main() -> None:
    load_dotenv()
    key_path = Path(required("FABRIC_SNOWFLAKE_PRIVATE_KEY_FILE"))
    passphrase_path = Path(required("FABRIC_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE_FILE"))
    payload = connection_payload(
        display_name=required("FABRIC_SNOWFLAKE_CONNECTION_NAME"),
        server=os.getenv("FABRIC_SNOWFLAKE_SERVER", "").strip()
        or snowflake_server(required("SNOWFLAKE_ACCOUNT")),
        warehouse=required("SNOWFLAKE_WAREHOUSE"),
        role=required("SNOWFLAKE_MIRROR_ROLE"),
        username=required("FABRIC_SNOWFLAKE_USER"),
        private_key=key_path.read_text(encoding="utf-8"),
        passphrase=passphrase_path.read_text(encoding="utf-8").strip(),
    )
    # Fabric performs a live Snowflake connection test during this request. It
    # can take several minutes even though ordinary Fabric API calls are quick.
    connection = ensure_connection(FabricClient(request_timeout=600), payload)
    print(json.dumps({"displayName": connection["displayName"], "id": connection["id"]}, indent=2))


if __name__ == "__main__":
    main()
