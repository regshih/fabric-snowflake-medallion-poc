from pathlib import Path

import pytest

from snowflake_source.common import connection_parameters, identifier
from snowflake_source.load import merge_file
from snowflake_source.setup import render, statements


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
    params = connection_parameters()
    assert params["authenticator"] == "externalbrowser"
    assert "password" not in params
    assert "private_key" not in " ".join(params)


def test_bootstrap_connection_omits_not_yet_created_context(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "example-org-account")
    monkeypatch.setenv("SNOWFLAKE_USER", "poc_user")
    params = connection_parameters("SNOWFLAKE_SETUP_ROLE", include_context=False)
    assert "warehouse" not in params
    assert "database" not in params
    assert "schema" not in params


def test_setup_render_is_idempotent_and_has_least_privilege_grants(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "poc_db")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "source_schema")
    sql = render()
    assert "CREATE DATABASE IF NOT EXISTS POC_DB" in sql
    assert "CREATE STREAM ON SCHEMA POC_DB.SOURCE_SCHEMA" in sql
    assert "SELECT ON ALL TABLES" in sql
    assert sql.count("SET CHANGE_TRACKING = TRUE") == 6
    assert "MODIFY ON" not in sql
    assert "{{" not in sql
    assert len(statements(sql)) >= 20


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
