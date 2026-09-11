import base64
import json

from infra.fabric.source_mirror import TABLES, definition_part, enabled, snowflake_definition


def test_snowflake_definition_is_deterministic_selective_and_credential_free():
    first = snowflake_definition("snowflake_bronze", "connection-id", "FABRIC_SNOWFLAKE_POC", "BANKING_SOURCE")
    second = snowflake_definition("snowflake_bronze", "connection-id", "FABRIC_SNOWFLAKE_POC", "BANKING_SOURCE")
    assert first == second
    parts = {part["path"]: part for part in first["parts"]}
    mirroring = json.loads(base64.b64decode(parts["mirroring.json"]["payload"]))
    assert mirroring["properties"]["source"] == {
        "type": "Snowflake",
        "typeProperties": {"connection": "connection-id", "database": "FABRIC_SNOWFLAKE_POC"},
    }
    selected = [item["source"]["typeProperties"]["tableName"] for item in mirroring["properties"]["mountedTables"]]
    assert selected == list(TABLES)
    assert all(item["source"]["typeProperties"]["schemaName"] == "BANKING_SOURCE" for item in mirroring["properties"]["mountedTables"])
    assert "credential" not in json.dumps(first).lower()
    assert definition_part(first, "mirroring.json") == mirroring


def test_destructive_recreate_flag_is_explicit(monkeypatch):
    monkeypatch.delenv("FABRIC_ALLOW_SNOWFLAKE_MIRROR_RECREATE", raising=False)
    assert not enabled("FABRIC_ALLOW_SNOWFLAKE_MIRROR_RECREATE")
    monkeypatch.setenv("FABRIC_ALLOW_SNOWFLAKE_MIRROR_RECREATE", "true")
    assert enabled("FABRIC_ALLOW_SNOWFLAKE_MIRROR_RECREATE")
