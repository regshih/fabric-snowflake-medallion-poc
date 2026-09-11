from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IAC = ROOT / "infra" / "snowflake" / "account-bootstrap"


def test_account_bootstrap_targets_azure_and_is_protected() -> None:
    main = (IAC / "main.tf").read_text(encoding="utf-8")
    assert 'source  = "snowflakedb/snowflake"' in main
    assert 'region               = "AZURE_WESTUS2"' in main
    assert 'edition              = "STANDARD"' in main
    assert "admin_rsa_public_key" in main
    assert "prevent_destroy = true" in main


def test_account_bootstrap_does_not_accept_password_tfvars() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in IAC.glob("*.tf")
    ).lower()
    example = (IAC / "terraform.tfvars.example").read_text(encoding="utf-8").lower()
    assert "admin_password" not in combined
    assert "password" not in example
    assert "private_key" not in example

