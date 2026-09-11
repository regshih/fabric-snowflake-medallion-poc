from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IAC = ROOT / "infra" / "azure" / "snowflake-private-endpoint"


def test_private_endpoint_uses_snowflake_alias_and_manual_approval():
    main = (IAC / "main.tf").read_text(encoding="utf-8")
    assert "azurerm_private_endpoint" in main
    assert "private_connection_resource_alias" in main
    assert "is_manual_connection              = true" in main
    assert "Microsoft.PowerPlatform/vnetaccesslinks" in main
    assert main.count("prevent_destroy = true") == 2


def test_iac_does_not_provision_snowflake_data_or_shared_compute():
    terraform = "\n".join(path.read_text(encoding="utf-8") for path in IAC.glob("*.tf"))
    assert "snowflake_account" not in terraform
    assert "snowflake_database" not in terraform
    assert "snowflake_warehouse" not in terraform
    assert 'resource "azurerm_resource_group"' not in terraform


def test_examples_contain_placeholders_only():
    example = (IAC / "terraform.tfvars.example").read_text(encoding="utf-8")
    assert "<azure-subscription-id>" in example
    assert "<privatelink-pls-id-from-snowflake>" in example
    assert "SYSTEM$GET_PRIVATELINK_CONFIG" in (IAC / "README.md").read_text(encoding="utf-8")
