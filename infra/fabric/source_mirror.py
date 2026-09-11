#!/usr/bin/env python3
"""Idempotently create and start a selective Fabric Snowflake mirror."""
from __future__ import annotations

import base64
import json
import os
import time
import uuid

from dotenv import load_dotenv

from infra.fabric.client import FabricApiError, FabricClient
from infra.fabric.deploy import resolve_capacity_id

TABLES = (
    "TRANSACTIONS",
    "TRANSACTION_RISK",
    "MERCHANTS",
    "DIGITAL_SESSIONS",
    "DEVICES",
    "FRAUD_ALERTS",
)


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise RuntimeError(f"Set {name} before creating the Snowflake mirror")
    return value


def enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def encoded(value: dict) -> str:
    return base64.b64encode(json.dumps(value, separators=(",", ":")).encode()).decode()


def definition_part(definition: dict, path: str) -> dict:
    parts = definition.get("definition", definition).get("parts", [])
    part = next((value for value in parts if value.get("path") == path), None)
    if not part:
        raise FabricApiError(f"Fabric item definition is missing {path!r}")
    try:
        return json.loads(base64.b64decode(part["payload"]))
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise FabricApiError(f"Fabric item definition part {path!r} is invalid") from exc


def snowflake_definition(name: str, connection_id: str, database: str, schema: str) -> dict:
    """Return a credential-free definition selecting only the six POC tables."""
    logical_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"fabric-snowflake-mirror:{name}"))
    mirroring = {
        "properties": {
            "source": {
                "type": "Snowflake",
                "typeProperties": {"connection": connection_id, "database": database},
            },
            "target": {
                "type": "MountedRelationalDatabase",
                "typeProperties": {"defaultSchema": schema, "format": "Delta", "retentionInDays": 7},
            },
            "mountedTables": [
                {"source": {"typeProperties": {"schemaName": schema, "tableName": table}}}
                for table in TABLES
            ],
        }
    }
    platform = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "MirroredDatabase", "displayName": name},
        "config": {"version": "2.0", "logicalId": logical_id},
    }
    return {
        "parts": [
            {"path": "mirroring.json", "payload": encoded(mirroring), "payloadType": "InlineBase64"},
            {"path": ".platform", "payload": encoded(platform), "payloadType": "InlineBase64"},
        ]
    }


def get_definition(client: FabricClient, workspace_id: str, item_id: str) -> dict:
    response = client.request("POST", f"workspaces/{workspace_id}/items/{item_id}/getDefinition", json={})
    return client.wait_for_operation(response)


def ensure_snowflake(client: FabricClient, workspace_id: str) -> dict:
    name = required("FABRIC_SNOWFLAKE_MIRROR_NAME")
    connection_id = required("FABRIC_SNOWFLAKE_CONNECTION_ID")
    database = required("SNOWFLAKE_DATABASE").upper()
    schema = required("SNOWFLAKE_SCHEMA").upper()
    path = f"workspaces/{workspace_id}/mirroredDatabases"
    existing = client._named(client.list_all(path), name)
    expected_definition = snowflake_definition(name, connection_id, database, schema)
    if existing:
        current = definition_part(get_definition(client, workspace_id, str(existing["id"])), "mirroring.json")
        expected = definition_part(expected_definition, "mirroring.json")
        if current.get("properties", {}).get("source") != expected["properties"]["source"] or current.get("properties", {}).get("mountedTables") != expected["properties"]["mountedTables"]:
            if not enabled("FABRIC_ALLOW_SNOWFLAKE_MIRROR_RECREATE"):
                raise FabricApiError(
                    "The existing mirror targets different Snowflake objects. Set "
                    "FABRIC_ALLOW_SNOWFLAKE_MIRROR_RECREATE=true to authorize replacement and reseed."
                )
            response = client.request("DELETE", f"{path}/{existing['id']}")
            client.wait_for_operation(response)
            for _ in range(60):
                if not client._named(client.list_all(path), name):
                    break
                time.sleep(2)
            else:
                raise FabricApiError("Timed out waiting for the old Snowflake mirror to be removed")
            existing = None
    if not existing:
        response = client.request(
            "POST",
            path,
            json={
                "displayName": name,
                "description": "Source-aligned Bronze replica of six synthetic Snowflake managed tables.",
                "definition": expected_definition,
            },
        )
        client.wait_for_operation(response)
        existing = client._named(client.list_all(path), name)
    if not existing:
        raise FabricApiError("Snowflake mirrored database was not visible after creation")
    status_path = f"{path}/{existing['id']}"
    status = client.request("POST", f"{status_path}/getMirroringStatus", json={}).json()
    if status.get("status") not in {"Running", "Starting"}:
        response = client.request("POST", f"{status_path}/startMirroring", json={})
        client.wait_for_operation(response)
    return existing


def main() -> None:
    load_dotenv()
    client = FabricClient()
    workspace_name = required("FABRIC_WORKSPACE_NAME")
    workspace = client._named(client.workspaces(), workspace_name)
    if not workspace:
        workspace = client.ensure_workspace(
            workspace_name,
            resolve_capacity_id(client),
            "Synthetic banking medallion POC using Snowflake on Azure and Microsoft Fabric.",
        )
    mirror = ensure_snowflake(client, str(workspace["id"]))
    print(json.dumps({"workspace": workspace_name, "snowflakeMirror": mirror["displayName"]}, indent=2))


if __name__ == "__main__":
    main()
