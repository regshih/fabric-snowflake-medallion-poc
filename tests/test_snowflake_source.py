from pathlib import Path

import pytest

from snowflake_source.cleanup import cleanup_statements
from snowflake_source.common import connection_parameters, identifier
from snowflake_source.load import merge_file
from snowflake_source.setup import (
    render,
    require_existing_object,
    require_managed_namespace,
    statements,
)


def test_identifier_validation(monkeypatch):
    monkeypatch.setenv("SAFE_NAME", "banking_source")
    assert identifier("SAFE_NAME") == "BANKING_SOURCE"
    monkeypatch.setenv("SAFE_NAME", "unsafe; drop database x")
    with pytest.raises(RuntimeError, match="unquoted"):
        identifier("SAFE_NAME")


def test_external_browser_connection_has_no_secret(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "example-org-account")
    monkeypatch.setenv("SNOWFLAKE_USER", "poc_user")
    monkeypatch.setenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "approved_wh")
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "customer_db")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "poc_schema")
    params = connection_parameters()
    assert params["authenticator"] == "externalbrowser"
    assert "password" not in params
    assert "private_key" not in " ".join(params)


def test_setup_connection_omits_context_for_existing_object_preflight(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "example-org-account")
    monkeypatch.setenv("SNOWFLAKE_USER", "poc_user")
    params = connection_parameters("SNOWFLAKE_SETUP_ROLE", include_context=False)
    assert "warehouse" not in params
    assert "database" not in params
    assert "schema" not in params


def test_key_pair_passphrase_can_be_read_from_ignored_file(monkeypatch, tmp_path: Path):
    passphrase = tmp_path / "passphrase.txt"
    passphrase.write_text("local-test-passphrase\n", encoding="utf-8")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "example-org-account")
    monkeypatch.setenv("SNOWFLAKE_USER", "poc_user")
    monkeypatch.setenv("SNOWFLAKE_AUTHENTICATOR", "SNOWFLAKE_JWT")
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_FILE", str(tmp_path / "key.p8"))
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE_FILE", str(passphrase))
    monkeypatch.delenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", raising=False)
    params = connection_parameters(include_context=False)
    assert params["private_key_file_pwd"] == "local-test-passphrase"


def test_setup_render_is_idempotent_and_has_least_privilege_grants(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "poc_db")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "approved_wh")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "source_schema")
    sql = render()
    assert "CREATE DATABASE" not in sql
    assert "CREATE WAREHOUSE" not in sql
    assert "CREATE SCHEMA IF NOT EXISTS POC_DB.SOURCE_SCHEMA" in sql
    assert "CREATE STREAM ON SCHEMA POC_DB.SOURCE_SCHEMA" in sql
    assert "SELECT ON ALL TABLES" in sql
    assert sql.count("SET CHANGE_TRACKING = TRUE") == 6
    assert "MODIFY ON" not in sql
    assert "{{" not in sql
    assert len(statements(sql)) >= 20


class ShowCursor:
    description = (("created_on",), ("name",))

    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def execute(self, sql):
        self.executed.append(sql)

    def fetchall(self):
        return self.rows


def test_existing_customer_object_preflight_is_exact():
    require_existing_object(ShowCursor([("now", "CUSTOMER_DB")]), "DATABASES", "CUSTOMER_DB")
    with pytest.raises(RuntimeError, match="never creates customer databases or warehouses"):
        require_existing_object(ShowCursor([]), "WAREHOUSES", "APPROVED_WH")


class NamespaceCursor:
    description = (("name",), ("comment",))

    def __init__(self, responses):
        self.responses = iter(responses)

    def execute(self, _sql):
        self.rows = next(self.responses)

    def fetchall(self):
        return self.rows


def test_namespace_preflight_rejects_unmanaged_customer_schema():
    cursor = NamespaceCursor([[('POC_SCHEMA', 'customer production schema')]])
    with pytest.raises(RuntimeError, match="not marked as POC-managed"):
        require_managed_namespace(cursor, "CUSTOMER_DB", "POC_SCHEMA", {})


def test_namespace_preflight_accepts_absent_schema_and_roles():
    cursor = NamespaceCursor([[], [], []])
    require_managed_namespace(
        cursor,
        "CUSTOMER_DB",
        "POC_SCHEMA",
        {"POC_LOADER": {"managed"}, "POC_MIRROR": {"managed"}},
    )


def test_cleanup_never_drops_customer_database_or_warehouse(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "CUSTOMER_DB")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "FABRIC_POC")
    sql = ";".join(cleanup_statements(include_roles=True))
    assert "DROP SCHEMA IF EXISTS CUSTOMER_DB.FABRIC_POC" in sql
    assert "DROP DATABASE" not in sql
    assert "DROP WAREHOUSE" not in sql


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.rows = []

    def execute(self, sql):
        self.executed.append(sql)

    def executemany(self, sql, rows):
        self.executed.append(sql)
        self.rows.extend(rows)


def test_loader_uses_staging_merge_not_row_by_row_dml(tmp_path: Path):
    path = tmp_path / "DEVICES.csv"
    path.write_text("DEVICE_ID,CUSTOMER_ID\nDEVICE-000001,CUST-000001\n", encoding="utf-8")
    cursor = FakeCursor()
    assert merge_file(cursor, "POC_DB", "BANKING_SOURCE", "DEVICES", path) == 1
    combined = "\n".join(cursor.executed)
    assert "CREATE TEMPORARY TABLE STAGE_DEVICES_" in combined
    assert "MERGE INTO POC_DB.BANKING_SOURCE.DEVICES" in combined
    assert "UPDATE ALL BY NAME" in combined
    assert cursor.rows == [("DEVICE-000001", "CUST-000001")]
