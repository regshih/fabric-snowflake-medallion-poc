# Deployment guide

This sequence assumes the customer already operates Snowflake on Microsoft Azure and has an approved existing database and virtual warehouse. Commands contain placeholders only. Keep environment values in ignored `.env`, an approved secret manager, or process variables.

## 1. Confirm ownership and prerequisites

- Python 3.11 or later and Azure CLI authenticated to the intended tenant/subscription;
- an active existing Fabric capacity and permission to create a dedicated workspace;
- Snowflake on Azure, an approved existing database/warehouse, and permission to create one dedicated POC schema and roles;
- Snowflake Business Critical Edition or higher for Azure Private Link;
- Azure networking, Snowflake, DNS, Fabric, and security owners identified;
- workspace Contributor/Admin and permission to create or use a Fabric VNet data gateway.

"Enterprise Snowflake" can describe an organization's platform without meaning Snowflake's Business Critical product edition. Confirm the actual edition before designing PrivateLink.

## 2. Prepare Snowflake PrivateLink and Azure networking

1. In an approved Snowflake administrator session, run `SELECT SYSTEM$GET_PRIVATELINK_CONFIG();`. Only `ACCOUNTADMIN` can obtain this account-level configuration. Treat the complete result as private environment inventory.
2. Give the `privatelink-pls-id` value to the Azure network deployment through an ignored variable or secret workflow. The optional [`infra/azure/snowflake-private-endpoint`](../infra/azure/snowflake-private-endpoint/README.md) Terraform root can create the Azure private endpoint and, when authorized, a separate Fabric-gateway subnet.
3. Review and apply Terraform through the customer's approved remote-state and change-management process. Do not commit state, plan files, or real variables.
4. Have the Snowflake administrator authorize the Azure private endpoint using a narrowly scoped Azure token obtained outside Terraform. Do not store the token in state, Git, command history, or logs.
5. Configure private DNS for both the Snowflake account hostname and OCSP hostname returned by Snowflake. Validate resolution and TLS connectivity from the VNet with the customer's approved tools, including SnowCD where available.

The private endpoint subnet and Fabric gateway subnet are different subnets. The gateway subnet must be dedicated and delegated to `Microsoft.PowerPlatform/vnetaccesslinks`. Register the `Microsoft.PowerPlatform` resource provider before gateway creation.

## 3. Create the Fabric VNet data gateway

In Fabric **Manage connections and gateways**, create a VNet data gateway using the approved subscription, VNet, dedicated delegated subnet, region, and capacity. As an alternative, after filling the `FABRIC_VNET_*` values in ignored `.env`, run the idempotent REST helper:

```powershell
python -m infra.fabric.vnet_gateway
```

The helper creates one auto-sleeping gateway only when no same-named gateway exists; it fails closed on VNet or capacity drift. Creation requires the Fabric `Gateway.ReadWrite.All` delegated scope and the documented Azure permissions on the VNet/subnet. Record the returned gateway ID only in ignored `.env` as `FABRIC_SNOWFLAKE_GATEWAY_ID`.

Invoking gateway creation remains a customer control-plane decision because tenant permissions, regional availability, subnet policy, capacity cost, and organizational approvals cannot safely be inferred by this repository.

## 4. Install and validate locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
az login
python -m pytest -q
```

Set `SNOWFLAKE_DATABASE` and `SNOWFLAKE_WAREHOUSE` to existing approved objects; there are intentionally no defaults. Set `SNOWFLAKE_ACCOUNT` for connector login and `FABRIC_SNOWFLAKE_SERVER` to the `privatelink-account-url` hostname for the Fabric connection. Never add these customer values to tracked files.

Use `externalbrowser` for interactive Snowflake SSO or an encrypted private key stored outside the repository. A key passphrase can be provided from a protected file through `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE_FILE`.

## 5. Create only the POC schema objects

Render and review the setup contract:

```powershell
New-Item -ItemType Directory -Force output | Out-Null
python -m snowflake_source.setup > output\rendered-setup.sql
python -m snowflake_source.setup --apply
```

The apply path first verifies that the configured database and warehouse already exist. It also refuses to reuse a same-named schema or role unless its comment identifies an earlier run of this POC. It creates only the dedicated schema, six managed synthetic tables, change-tracking settings, and least-privilege loader/mirror roles. It never creates, alters, resizes, suspends, resumes, or drops the customer database or warehouse.

Assign the two roles to actual principals from a private working copy of `snowflake_source/sql/10_assign_roles.template.sql`. Never grant `ACCOUNTADMIN`, database ownership, or access to unrelated schemas to solve a connection issue.

## 6. Generate, validate, and load synthetic data

```powershell
python generators\generate_snowflake_data.py
python validation\validate_snowflake.py --mode files --data-dir data\snowflake\initial
python -m snowflake_source.load --batch initial
python validation\validate_snowflake.py --mode live
```

Generated data is ignored. Loading uses session-scoped staging tables and keyed `MERGE` operations so retries are safe.

## 7. Create the private Fabric Snowflake connection

Keep the defaults below in ignored `.env`:

```text
FABRIC_SNOWFLAKE_CONNECTIVITY_TYPE=VirtualNetworkGateway
FABRIC_SNOWFLAKE_GATEWAY_ID=<customer-gateway-id>
FABRIC_SNOWFLAKE_SERVER=<privatelink-account-url-hostname>
```

Then run:

```powershell
python -m infra.fabric.snowflake_connection
```

The helper fails if private mode lacks an explicit private hostname or gateway ID. If an existing connection has a different connectivity type or gateway, it also fails closed instead of silently weakening the network path. `ShareableCloud` remains an explicit maintainer-lab option and is not the customer default.

The helper sends the encrypted PKCS#8 key to Fabric over TLS for its live connection test. It never prints the key or passphrase. Keep only the returned connection GUID in ignored `.env` as `FABRIC_SNOWFLAKE_CONNECTION_ID`.

## 8. Create the workspace and selective mirror

Set an existing `FABRIC_CAPACITY_ID` or `FABRIC_CAPACITY_NAME`, configure `FABRIC_WORKSPACE_NAME`, and run:

```powershell
python -m infra.fabric.source_mirror
```

The mirror selects exactly six tables. It fails closed if an existing item targets different source objects. `FABRIC_ALLOW_SNOWFLAKE_MIRROR_RECREATE=true` explicitly authorizes replacement and a potentially costly full reseed.

Wait for the initial copy to report healthy replication, then confirm Spark can read the case-sensitive schema/table paths.

## 9. Deploy and run the medallion items

```powershell
python -m infra.fabric.deploy
python -m infra.fabric.deploy --run --run-date 2026-09-10
```

The second command starts billable customer compute. Capture only sanitized evidence. Apply the reviewed Warehouse and governance contracts using the commands in the [runbook](runbook.md).

## 10. Evidence and publication gates

Complete [validation.md](validation.md), including PrivateLink authorization, DNS, VNet gateway, mirror health, source/Silver/Gold counts, incremental propagation, Warehouse security, and absence of unexpected reseed.

```powershell
python tools\security_scan.py --working-tree --git-history
git status --short
```

Repository publication is a separate owner decision. Keep it private until the owner explicitly approves changing visibility.
