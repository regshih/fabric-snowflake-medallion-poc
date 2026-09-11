#!/usr/bin/env python3
"""Idempotently create a Fabric VNet data gateway on an approved delegated subnet."""
from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from infra.fabric.client import FabricApiError, FabricClient
from infra.fabric.deploy import resolve_capacity_id

ALLOWED_SLEEP_MINUTES = {30, 60, 90, 120, 150, 240, 360, 480, 720, 1440}


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise RuntimeError(f"Set {name} before creating the Fabric VNet data gateway")
    return value


def gateway_payload(
    *,
    display_name: str,
    capacity_id: str,
    subscription_id: str,
    resource_group_name: str,
    virtual_network_name: str,
    subnet_name: str,
    inactivity_minutes: int = 30,
    min_members: int = 1,
    max_members: int = 1,
) -> dict[str, Any]:
    if inactivity_minutes not in ALLOWED_SLEEP_MINUTES:
        raise ValueError(f"Unsupported gateway inactivity interval: {inactivity_minutes}")
    if not (1 <= min_members <= max_members <= 11):
        raise ValueError("Gateway member range must satisfy 1 <= min <= max <= 11")
    return {
        "type": "VirtualNetwork",
        "displayName": display_name,
        "capacityId": capacity_id,
        "virtualNetworkAzureResource": {
            "subscriptionId": subscription_id,
            "resourceGroupName": resource_group_name,
            "virtualNetworkName": virtual_network_name,
            "subnetName": subnet_name,
        },
        "inactivityMinutesBeforeSleep": inactivity_minutes,
        "minMemberGatewayCount": min_members,
        "maxMemberGatewayCount": max_members,
    }


def ensure_gateway(client: FabricClient, payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload["displayName"])
    existing = client._named(client.list_all("gateways"), name)
    if existing:
        checks = {
            "type": payload["type"],
            "capacityId": payload["capacityId"],
            "virtualNetworkAzureResource": payload["virtualNetworkAzureResource"],
        }
        drift = [key for key, expected in checks.items() if existing.get(key) != expected]
        if drift:
            raise FabricApiError(
                f"Existing VNet gateway {name!r} differs in {', '.join(drift)}; "
                "review it instead of recreating it"
            )
        return existing
    created = client._json(client.request("POST", "gateways", json=payload))
    if not created.get("id"):
        raise FabricApiError("Fabric created no visible VNet gateway identifier")
    return created


def main() -> None:
    load_dotenv()
    client = FabricClient()
    payload = gateway_payload(
        display_name=required("FABRIC_VNET_GATEWAY_NAME"),
        capacity_id=resolve_capacity_id(client),
        subscription_id=required("FABRIC_VNET_SUBSCRIPTION_ID"),
        resource_group_name=required("FABRIC_VNET_RESOURCE_GROUP"),
        virtual_network_name=required("FABRIC_VNET_NAME"),
        subnet_name=required("FABRIC_VNET_GATEWAY_SUBNET"),
        inactivity_minutes=int(os.getenv("FABRIC_VNET_GATEWAY_INACTIVITY_MINUTES", "30")),
        min_members=int(os.getenv("FABRIC_VNET_GATEWAY_MIN_MEMBERS", "1")),
        max_members=int(os.getenv("FABRIC_VNET_GATEWAY_MAX_MEMBERS", "1")),
    )
    gateway = ensure_gateway(client, payload)
    print(json.dumps({"displayName": gateway["displayName"], "id": gateway["id"]}, indent=2))


if __name__ == "__main__":
    main()
