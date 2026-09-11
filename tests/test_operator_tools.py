from __future__ import annotations

import pytest

from infra.fabric.git_integration import _connection_url, github_pat
from tools.fabric_sql import split_batches
from tools.security_scan import scan_text


def test_split_batches_handles_go_lines_only() -> None:
    sql = "SELECT 'GO is data';\nGO\nSELECT 2;\n go -- next batch\nSELECT 3;"
    assert split_batches(sql) == ["SELECT 'GO is data';", "SELECT 2;", "SELECT 3;"]


def test_github_pat_rejects_cli_oauth_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "gho_not-a-fabric-pat")
    with pytest.raises(RuntimeError, match="classic or fine-grained"):
        github_pat()


def test_github_pat_accepts_fine_grained_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "github_pat_synthetic_test_value")
    assert github_pat().startswith("github_pat_")


def test_github_pat_accepts_future_pat_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PAT", "future_pat_format_with_enough_length")
    assert github_pat() == "future_pat_format_with_enough_length"


def test_connection_url_reads_named_parameter() -> None:
    connection = {
        "connectionDetails": {
            "parameters": [
                {"name": "unrelated", "value": "x"},
                {"name": "url", "value": "https://github.com/example/repo/"},
            ]
        }
    }
    assert _connection_url(connection) == "https://github.com/example/repo"


def test_secret_scanner_detects_encrypted_keys_and_modern_github_tokens() -> None:
    encrypted_key = "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----"
    fine_grained_pat = "github_" + "pat_" + ("a" * 30)
    findings = scan_text("fixture", f"{encrypted_key}\n{fine_grained_pat}")
    assert any("private-key" in finding for finding in findings)
    assert any("github-token" in finding for finding in findings)


def test_secret_scanner_detects_environment_inventory() -> None:
    separator = chr(45)
    guid = separator.join(("12345678", "1234", "4123", "8123", "123456789abc"))
    snowsight = "https://app." + "snowflake.com/example-org/example-account/"
    host = "example-org-example-account.privatelink." + "snowflakecomputing.com"
    findings = scan_text("fixture", f"{guid}\n{snowsight}\n{host}")
    assert any("live-environment-guid" in finding for finding in findings)
    assert any("snowflake-snowsight-account-url" in finding for finding in findings)
    assert any("snowflake-account-host" in finding for finding in findings)
