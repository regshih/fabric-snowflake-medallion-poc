# Security

This public proof of concept contains synthetic data and no credentials. Use Azure CLI / Microsoft Entra ID authentication and Fabric connections. Never place passwords, account keys, SAS tokens, PATs, service-principal secrets, connection strings, or bearer tokens in files, notebook output, command history captures, pipeline JSON, or Fabric Git artifacts.

## Local configuration

Copy `.env.example` to `.env`; `.env` is ignored. Prefer `az login` for Fabric and interactive browser/Entra SSO for Snowflake. For unattended Snowflake access, use a dedicated least-privilege service user with an encrypted, rotated RSA key stored outside the repository. A key path or passphrase may be supplied only through the ignored local environment or a secret manager. Fabric connection credentials belong in Fabric, not in item definitions or Git.

Snowflake native password authentication is supported for compatibility but is not the repository default. Never place a password in `.env.example`, SQL, source code, shell scripts, screenshots, or committed logs.

## Private connectivity

Customer deployments default to Snowflake Azure Private Link through a Fabric VNet data gateway. Keep the Snowflake PrivateLink configuration response, private service alias, endpoint IDs/IPs, private DNS details, and gateway ID outside Git. Use `ACCOUNTADMIN` only for administrator-controlled PrivateLink discovery and authorization; the Fabric runtime principal uses the dedicated least-privilege mirror role.

Use only an ignored local `terraform.tfvars` or `main.bicepparam` for the private endpoint deployment. The Bicep alias parameter is marked secure, and the example files contain placeholders only. Never put the Azure federated token used by `SYSTEM$AUTHORIZE_PRIVATELINK` in either IaC system or Azure deployment history.

The setup and cleanup tools never create or drop the customer database or warehouse. Cleanup is restricted to the configured dedicated schema and, only with an additional flag, the dedicated POC roles.

## Public-release gate

Run `python tools/security_scan.py --working-tree --git-history` before every public release. Review all findings manually. If a real credential was ever committed, revoke/rotate it first, then remove it from the full Git history before publishing.

If that scanner is not yet present in the working tree, the public-release gate is **not complete**. Use an approved secret scanner against both the working tree and every reachable Git commit, and manually inspect `.env*`, notebooks/outputs, pipeline JSON, Fabric Git artifacts, generated data, logs, and documentation. Search at minimum for `AccountKey=`, `SharedAccessSignature=`, `Password=`, `pwd=`, `client_secret`, `access_token`, `Bearer`, `sig=`, and `Authorization:`. Record only pass/fail and affected file paths; never paste a discovered value into an issue or report.

Before publishing, also verify that Azure subscription/tenant/resource IDs, Fabric workspace/item/connection IDs, Snowflake account identifiers/hosts, principal IDs, query/run URLs, and screenshots containing tenant context haven't been added to tracked documentation. These identifiers are not all credentials, but this public POC intentionally keeps environment inventory private.

Notebook source files are committed without outputs. Generated data and logs are ignored.

## Synthetic-data statement

Every customer, account, transaction, device, session, merchant, IP address, and alert is generated for this POC. Identifiers use conspicuous formats such as `CUST-######`, `TXN-#########`, and `DEVICE-######`; no production or real-person data is permitted.

## Reporting

If a credential is found, do not open a public issue containing it. Revoke it and remove it locally before reporting the affected file path to the repository owner.
