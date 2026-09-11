# Existing enterprise Snowflake private connectivity

This Terraform root creates only the Azure side of a Snowflake private endpoint and, optionally, a dedicated subnet delegated for a Fabric VNet data gateway. It does not create a Snowflake account, database, warehouse, Fabric gateway, or Fabric capacity.

Customers that standardize on Azure-native infrastructure as code can use the equivalent [Bicep deployment](../snowflake-private-endpoint-bicep/README.md).

Use it only after the customer's Snowflake, Azure networking, security, and Fabric administrators approve the target resource group, VNet, subnets, DNS design, and Terraform state location.

## Prerequisites

- An existing Snowflake account hosted on Microsoft Azure. Azure Private Link requires Snowflake Business Critical Edition or higher; an account described organizationally as "enterprise" might not have that product edition.
- An existing customer database and approved virtual warehouse.
- `ACCOUNTADMIN` access for Snowflake PrivateLink discovery and authorization only. Do not use that role for Fabric replication.
- A customer-managed Azure VNet with a private-endpoint subnet.
- A separate subnet for the Fabric VNet data gateway, delegated exclusively to `Microsoft.PowerPlatform/vnetaccesslinks`.
- An approved remote Terraform backend. Never commit state or real `terraform.tfvars`.

## Workflow

1. From an approved Snowflake admin session, run `SELECT SYSTEM$GET_PRIVATELINK_CONFIG();`. Keep its full output private. Copy only `privatelink-pls-id` into ignored `terraform.tfvars`.
2. Copy `terraform.tfvars.example` to ignored `terraform.tfvars`. By default the module expects the network team to supply the gateway subnet. Set `create_fabric_gateway_subnet = true` only when this Terraform root is authorized to add that subnet to the existing VNet.
3. Configure an approved remote backend, then run `terraform init`, `terraform fmt -check`, `terraform validate`, and a reviewed `terraform plan` before apply.
4. Obtain a narrowly scoped Azure federated token outside Terraform, then have the Snowflake administrator authorize the private endpoint with `SYSTEM$AUTHORIZE_PRIVATELINK`. Do not put the token in Terraform, shell history, logs, or Git.
5. Configure customer private DNS so the account and OCSP hostnames returned by `SYSTEM$GET_PRIVATELINK_CONFIG()` resolve to the endpoint's private IP. Test from the gateway VNet with SnowCD and `SYSTEM$ALLOWLIST_PRIVATELINK()`.
6. Register `Microsoft.PowerPlatform`, confirm the dedicated gateway subnet delegation, and create the Fabric VNet data gateway in **Manage connections and gateways**. Record its gateway ID only in ignored `.env`.
7. Set `FABRIC_SNOWFLAKE_SERVER` to Snowflake's `privatelink-account-url`, then run `python -m infra.fabric.snowflake_connection`.

Private endpoint authorization, DNS, and gateway creation deliberately remain separate approval boundaries. They depend on customer tenant roles and private values and should not be hidden inside a one-click POC deployment.

Both Terraform-managed network resources use `prevent_destroy`. A customer-approved retirement change must deliberately remove that guard before destruction; never bypass it as part of ordinary POC cleanup.

## Official references

- [Azure Private Link and Snowflake](https://docs.snowflake.com/en/user-guide/privatelink-azure)
- [`SYSTEM$GET_PRIVATELINK_CONFIG`](https://docs.snowflake.com/en/sql-reference/functions/system_get_privatelink_config)
- [Create a Fabric VNet data gateway](https://learn.microsoft.com/en-us/data-integration/vnet/create-data-gateways)
- [Fabric VNet data gateway overview](https://learn.microsoft.com/en-us/data-integration/vnet/overview)
