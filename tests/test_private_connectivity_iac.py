from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IAC = ROOT / "infra" / "azure" / "snowflake-private-endpoint"
BICEP_IAC = ROOT / "infra" / "azure" / "snowflake-private-endpoint-bicep"


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


def test_terraform_enforces_remote_azure_backend_with_placeholder_example():
    versions = (IAC / "versions.tf").read_text(encoding="utf-8")
    backend = (IAC / "backend.hcl.example").read_text(encoding="utf-8")
    assert 'backend "azurerm" {}' in versions
    assert "use_azuread_auth     = true" in backend
    assert "<terraform-state-storage-account>" in backend


def test_bicep_uses_manual_snowflake_connection_and_fabric_delegation():
    main = (BICEP_IAC / "main.bicep").read_text(encoding="utf-8")
    assert "Microsoft.Network/privateEndpoints@2024-07-01" in main
    assert "manualPrivateLinkServiceConnections" in main
    assert "snowflakePrivateLinkServiceAliasOrResourceId" in main
    assert "Microsoft.PowerPlatform/vnetaccesslinks" in main
    assert "Microsoft.Authorization/locks@2020-05-01" in main


def test_bicep_does_not_create_shared_or_snowflake_resources():
    main = (BICEP_IAC / "main.bicep").read_text(encoding="utf-8")
    assert "Microsoft.Resources/resourceGroups" not in main
    assert "snowflake_database" not in main
    assert "snowflake_warehouse" not in main
    assert "resource existingVnet" in main
    assert " existing = if " in main


def test_bicep_example_contains_placeholders_only():
    example = (BICEP_IAC / "main.bicepparam.example").read_text(encoding="utf-8")
    assert "<azure-subscription-id>" in example
    assert "<privatelink-pls-id-from-SYSTEM$GET_PRIVATELINK_CONFIG>" in example
    assert "SYSTEM$AUTHORIZE_PRIVATELINK" in (BICEP_IAC / "README.md").read_text(
        encoding="utf-8"
    )
