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
    connectivity_type: str = "VirtualNetworkGateway",
    gateway_id: str = "",
) -> dict[str, Any]:
    """Build a documented cloud or VNet-gateway KeyPair request."""
    if connectivity_type not in {"VirtualNetworkGateway", "ShareableCloud"}:
        raise ValueError(
            "FABRIC_SNOWFLAKE_CONNECTIVITY_TYPE must be VirtualNetworkGateway or ShareableCloud"
        )
    if connectivity_type == "VirtualNetworkGateway" and not gateway_id:
        raise ValueError("FABRIC_SNOWFLAKE_GATEWAY_ID is required for private connectivity")
    normalized_server = server.strip().lower()
    if connectivity_type == "VirtualNetworkGateway" and ".privatelink." not in normalized_server:
        raise ValueError(
            "VirtualNetworkGateway requires Snowflake's privatelink-account-url hostname"
        )
    payload: dict[str, Any] = {
        "connectivityType": connectivity_type,
        "displayName": display_name,
        "connectionDetails": {
            "type": "Snowflake",
            "creationMethod": "Snowflake.Databases",
            "parameters": [
                {"dataType": "Text", "name": "server", "value": normalized_server},
                {"dataType": "Text", "name": "warehouse", "value": warehouse},
                {"dataType": "Text", "name": "Role", "value": role},
            ],
        },
        "privacyLevel": "Organizational",
        "credentialDetails": {
            "singleSignOnType": "None",
            "connectionEncryption": (
                "Encrypted" if connectivity_type == "VirtualNetworkGateway" else "NotEncrypted"
            ),
            "skipTestConnection": False,
            "credentials": {
                "credentialType": "KeyPair",
                "identifier": username,
                "privateKey": private_key,
                "passphrase": passphrase,
            },
        },
    }
    if connectivity_type == "VirtualNetworkGateway":
        payload["gatewayId"] = gateway_id
    else:
        payload["allowUsageInUserControlledCode"] = True
    return payload


def ensure_connection(client: FabricClient, payload: dict[str, Any]) -> dict[str, Any]:
    display_name = str(payload["displayName"])
    existing = client._named(client.list_all("connections"), display_name)
    if existing:
        if existing.get("connectivityType") != payload.get("connectivityType"):
            raise FabricApiError(
                f"Existing connection {display_name!r} uses "
                f"{existing.get('connectivityType')!r}, not {payload.get('connectivityType')!r}"
            )
        if payload.get("gatewayId") and existing.get("gatewayId") != payload.get("gatewayId"):
            raise FabricApiError(
                f"Existing connection {display_name!r} is attached to a different gateway"
            )
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
    connectivity_type = os.getenv(
        "FABRIC_SNOWFLAKE_CONNECTIVITY_TYPE", "VirtualNetworkGateway"
    ).strip()
    gateway_id = os.getenv("FABRIC_SNOWFLAKE_GATEWAY_ID", "").strip()
    configured_server = os.getenv("FABRIC_SNOWFLAKE_SERVER", "").strip()
    if connectivity_type == "VirtualNetworkGateway" and not configured_server:
        raise RuntimeError(
            "Set FABRIC_SNOWFLAKE_SERVER to the Snowflake PrivateLink account URL; "
            "a public account hostname is not inferred for private connectivity"
        )
    key_path = Path(required("FABRIC_SNOWFLAKE_PRIVATE_KEY_FILE"))
    passphrase_path = Path(required("FABRIC_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE_FILE"))
    payload = connection_payload(
        display_name=required("FABRIC_SNOWFLAKE_CONNECTION_NAME"),
        server=configured_server or snowflake_server(required("SNOWFLAKE_ACCOUNT")),
        warehouse=required("SNOWFLAKE_WAREHOUSE"),
        role=required("SNOWFLAKE_MIRROR_ROLE"),
        username=required("FABRIC_SNOWFLAKE_USER"),
        private_key=key_path.read_text(encoding="utf-8"),
        passphrase=passphrase_path.read_text(encoding="utf-8").strip(),
        connectivity_type=connectivity_type,
        gateway_id=gateway_id,
    )
    # Fabric performs a live Snowflake connection test during this request. It
    # can take several minutes even though ordinary Fabric API calls are quick.
    connection = ensure_connection(FabricClient(request_timeout=600), payload)
    print(json.dumps({"displayName": connection["displayName"], "id": connection["id"]}, indent=2))


if __name__ == "__main__":
    main()
