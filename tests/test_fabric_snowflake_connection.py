import pytest

from infra.fabric.snowflake_connection import (
    connection_payload,
    ensure_connection,
    snowflake_server,
)


def test_snowflake_server_accepts_identifier_or_hostname():
    assert snowflake_server("acme-demo") == "acme-demo.snowflakecomputing.com"
    assert snowflake_server("HTTPS://acme-demo.snowflakecomputing.com/") == "acme-demo.snowflakecomputing.com"


def test_connection_payload_uses_keypair_without_leaking_into_connection_details():
    payload = connection_payload(
        display_name="poc",
        server="Org-Account.privatelink.snowflakecomputing.com",
        warehouse="POC_WH",
        role="POC_MIRROR",
        username="POC_USER",
        private_key="PRIVATE PEM",
        passphrase="test-passphrase",
        connectivity_type="VirtualNetworkGateway",
        gateway_id="gateway-id",
    )
    assert payload["connectionDetails"] == {
        "type": "Snowflake",
        "creationMethod": "Snowflake.Databases",
        "parameters": [
            {
                "dataType": "Text",
                "name": "server",
                "value": "org-account.privatelink.snowflakecomputing.com",
            },
            {"dataType": "Text", "name": "warehouse", "value": "POC_WH"},
            {"dataType": "Text", "name": "Role", "value": "POC_MIRROR"},
        ],
    }
    assert payload["credentialDetails"]["credentials"]["credentialType"] == "KeyPair"
    assert payload["credentialDetails"]["connectionEncryption"] == "Encrypted"
    assert payload["connectivityType"] == "VirtualNetworkGateway"
    assert payload["gatewayId"] == "gateway-id"
    assert "allowUsageInUserControlledCode" not in payload


def test_private_gateway_rejects_public_snowflake_hostname():
    with pytest.raises(ValueError, match="privatelink-account-url"):
        connection_payload(
            display_name="poc",
            server="org-account.snowflakecomputing.com",
            warehouse="POC_WH",
            role="POC_MIRROR",
            username="POC_USER",
            private_key="PRIVATE PEM",
            passphrase="test-passphrase",
            connectivity_type="VirtualNetworkGateway",
            gateway_id="gateway-id",
        )


def test_public_cloud_connection_is_explicit_and_has_no_gateway():
    payload = connection_payload(
        display_name="poc-public",
        server="org-account.snowflakecomputing.com",
        warehouse="POC_WH",
        role="POC_MIRROR",
        username="POC_USER",
        private_key="PRIVATE PEM",
        passphrase="test-passphrase",
        connectivity_type="ShareableCloud",
    )
    assert payload["connectivityType"] == "ShareableCloud"
    assert payload["credentialDetails"]["connectionEncryption"] == "NotEncrypted"
    assert "gatewayId" not in payload
    assert payload["allowUsageInUserControlledCode"] is True


class ExistingClient:
    def list_all(self, path):
        assert path == "connections"
        return [{
            "id": "existing-id",
            "displayName": "poc",
            "connectivityType": "ShareableCloud",
        }]

    _named = staticmethod(lambda objects, name: next((item for item in objects if item["displayName"] == name), None))


def test_ensure_connection_is_idempotent():
    existing = ensure_connection(
        ExistingClient(), {"displayName": "poc", "connectivityType": "ShareableCloud"}
    )
    assert existing["id"] == "existing-id"
