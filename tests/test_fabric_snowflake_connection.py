from infra.fabric.snowflake_connection import connection_payload, ensure_connection, snowflake_server


def test_snowflake_server_accepts_identifier_or_hostname():
    assert snowflake_server("acme-demo") == "acme-demo.snowflakecomputing.com"
    assert snowflake_server("HTTPS://acme-demo.snowflakecomputing.com/") == "acme-demo.snowflakecomputing.com"


def test_connection_payload_uses_keypair_without_leaking_into_connection_details():
    payload = connection_payload(
        display_name="poc",
        server="Org-Account.snowflakecomputing.com",
        warehouse="POC_WH",
        role="POC_MIRROR",
        username="POC_USER",
        private_key="PRIVATE PEM",
        passphrase="SECRET",
    )
    assert payload["connectionDetails"] == {
        "type": "Snowflake",
        "creationMethod": "Snowflake.Databases",
        "parameters": [
            {"dataType": "Text", "name": "server", "value": "org-account.snowflakecomputing.com"},
            {"dataType": "Text", "name": "warehouse", "value": "POC_WH"},
            {"dataType": "Text", "name": "Role", "value": "POC_MIRROR"},
        ],
    }
    assert payload["credentialDetails"]["credentials"]["credentialType"] == "KeyPair"
    assert payload["credentialDetails"]["connectionEncryption"] == "NotEncrypted"


class ExistingClient:
    def list_all(self, path):
        assert path == "connections"
        return [{"id": "existing-id", "displayName": "poc"}]

    _named = staticmethod(lambda objects, name: next((item for item in objects if item["displayName"] == name), None))


def test_ensure_connection_is_idempotent():
    existing = ensure_connection(ExistingClient(), {"displayName": "poc"})
    assert existing["id"] == "existing-id"
