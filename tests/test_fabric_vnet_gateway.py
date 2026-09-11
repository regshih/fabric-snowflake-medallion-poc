from __future__ import annotations

import pytest

from infra.fabric.client import FabricApiError
from infra.fabric.vnet_gateway import ensure_gateway, gateway_payload


def payload():
    return gateway_payload(
        display_name="customer-gateway",
        capacity_id="capacity-id",
        subscription_id="subscription-id",
        resource_group_name="network-rg",
        virtual_network_name="customer-vnet",
        subnet_name="fabric-gateway-subnet",
    )


def test_gateway_payload_uses_dedicated_vnet_contract():
    result = payload()
    assert result["type"] == "VirtualNetwork"
    assert result["inactivityMinutesBeforeSleep"] == 30
    assert result["minMemberGatewayCount"] == 1
    assert result["maxMemberGatewayCount"] == 1
    assert result["virtualNetworkAzureResource"]["subnetName"] == "fabric-gateway-subnet"


class ExistingClient:
    def __init__(self, item):
        self.item = item

    def list_all(self, path):
        assert path == "gateways"
        return [self.item]

    _named = staticmethod(
        lambda objects, name: next(
            (item for item in objects if item["displayName"] == name), None
        )
    )


def test_existing_gateway_is_reused_only_when_network_and_capacity_match():
    expected = payload()
    existing = {**expected, "id": "gateway-id"}
    assert ensure_gateway(ExistingClient(existing), expected)["id"] == "gateway-id"

    drifted = {**existing, "capacityId": "different-capacity"}
    with pytest.raises(FabricApiError, match="differs in capacityId"):
        ensure_gateway(ExistingClient(drifted), expected)


def test_gateway_scaling_and_sleep_values_are_validated():
    with pytest.raises(ValueError, match="inactivity"):
        gateway_payload(
            display_name="x", capacity_id="c", subscription_id="s",
            resource_group_name="r", virtual_network_name="v", subnet_name="n",
            inactivity_minutes=31,
        )
    with pytest.raises(ValueError, match="member range"):
        gateway_payload(
            display_name="x", capacity_id="c", subscription_id="s",
            resource_group_name="r", virtual_network_name="v", subnet_name="n",
            min_members=2, max_members=1,
        )
