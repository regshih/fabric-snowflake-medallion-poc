# Snowflake account bootstrap with Terraform

This optional module creates a dedicated Snowflake **account hosted on Microsoft Azure West US 2**. It uses the official `snowflakedb/snowflake` provider and the stable `snowflake_account` resource.

It cannot create an organization's first Snowflake account. The provider must authenticate to an existing Snowflake organization account through a user that can assume `ORGADMIN`. This is a Snowflake control-plane requirement, not a Terraform limitation.

## Security boundary

- The new account administrator uses an RSA public key; no initial password enters Terraform configuration or state.
- Authenticate the bootstrap provider with `EXTERNALBROWSER` for an interactive run, or configure an approved noninteractive method entirely through process environment variables.
- Never put a password, OAuth token, or private key in `terraform.tfvars`.
- Personal administrator fields are marked sensitive but still exist in Terraform state. Use an encrypted, access-controlled remote backend for anything beyond a disposable POC.
- `prevent_destroy` protects the Snowflake account from an accidental `terraform destroy`.

## Usage

Generate and protect a private key outside the repository. Place only its public-key body in an ignored `terraform.tfvars` file.

```powershell
Set-Location infra\snowflake\account-bootstrap
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

After the account is created, configure the repository's ignored `.env` for the new account and run `python -m snowflake_source.setup --apply` followed by the data generator and loader described in `docs/deployment.md`.

The nearest Snowflake region to the Fabric capacity in West US 3 is the canonical Snowflake region `AZURE_WESTUS2`; Snowflake does not currently list Azure West US 3 as an account region.

References:

- [Official Terraform `snowflake_account` resource](https://registry.terraform.io/providers/snowflakedb/snowflake/latest/docs/resources/account)
- [Snowflake `CREATE ACCOUNT`](https://docs.snowflake.com/en/sql-reference/sql/create-account)
- [Snowflake cloud region identifiers](https://docs.snowflake.com/en/user-guide/admin-account-identifier)

