# Deployment guide

This sequence proves each boundary before downstream Fabric items are deployed. Commands contain placeholders only. Keep environment values in ignored `.env` or process variables.

## 1. Prerequisites

- Python 3.11 or later
- Azure CLI authenticated to the intended tenant/subscription
- an existing active Fabric capacity and permission to create a dedicated workspace
- a Snowflake account hosted on Microsoft Azure
- a Snowflake administrative role for initial setup
- a Snowflake loader principal and a separate Fabric connection principal
- Fabric workspace Contributor or Admin access, depending on the operation

Review Snowflake network policy and decide between direct connectivity and a Fabric VNet/on-premises data gateway before creating the Fabric connection.

## 2. Local installation and validation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
az login
python -m pytest -q
```

Populate the ignored `.env` with identifiers. Use `externalbrowser` for interactive Snowflake SSO or point to an encrypted private key stored outside the repository. Never write a private key, passphrase, password, token, or Fabric connection credential into a tracked file.

## 3. Configure Snowflake

Review the rendered setup SQL before applying it:

```powershell
New-Item -ItemType Directory -Force output | Out-Null
python -m snowflake_source.setup > output\rendered-setup.sql
```

`output/rendered-setup.sql` is ignored local output. It creates an X-Small auto-suspending warehouse, POC database/schema, six managed tables, and dedicated loader/mirror roles.

Set `SNOWFLAKE_SETUP_ROLE` locally to an appropriately privileged current Snowflake role, then apply after review:

```powershell
python -m snowflake_source.setup --apply
```

In a private working copy of `snowflake_source/sql/10_assign_roles.template.sql`, assign the two roles to the actual principals. Do not grant `ACCOUNTADMIN` or broad database ownership to the Fabric connection to bypass a permissions problem.

## 4. Generate, validate, and load synthetic data

The default dataset is intentionally modest: 10,000 transactions/scores, 300 merchants, 1,500 sessions, 375 devices, and 150 alerts.

```powershell
python generators\generate_snowflake_data.py
python validation\validate_snowflake.py --mode files --data-dir data\snowflake\initial
python -m snowflake_source.load --batch initial
python validation\validate_snowflake.py --mode live
```

Generated data is ignored. Loading is idempotent: each CSV is inserted into a session-scoped staging table and merged into its managed target using the business key.

## 5. Create the Fabric Snowflake connection

In Fabric **Manage connections and gateways**, create the Snowflake connection using the exact case-sensitive server, warehouse, database, and schema identifiers.

Supported choices for this POC:

- Microsoft Entra SSO for an interactive demonstration;
- RSA key pair for a separately managed service account;
- Snowflake native username/password only when the credential is stored in Fabric and never exported to Git.

Select the VNet or on-premises gateway if the Snowflake endpoint is private. Test the connection, then put only the Fabric connection GUID in ignored `.env` as `FABRIC_SNOWFLAKE_CONNECTION_ID`.

## 6. Create workspace and source mirror

The downstream deployer expects the source mirror to exist. Set `FABRIC_CAPACITY_ID` or `FABRIC_CAPACITY_NAME` to an existing capacity and configure `FABRIC_WORKSPACE_NAME`. The mirror helper idempotently creates the dedicated workspace when absent, assigns the existing capacity, and creates/starts the selective mirror:

```powershell
python -m infra.fabric.source_mirror
```

The definition mirrors exactly six tables. It fails closed if an existing item points at different source objects. Setting `FABRIC_ALLOW_SNOWFLAKE_MIRROR_RECREATE=true` authorizes replacement and a potentially expensive full reseed; review this change before using it. If tenant policy requires portal-created workspaces, create the same named workspace manually and assign the configured capacity before running the helper.

Wait until all six tables complete initial copy and report healthy replication. Confirm Spark can read the case-sensitive schema/table paths.

## 7. Deploy and run Fabric medallion items

The deployment reuses the configured capacity and creates or updates `silver_lh`, `gold_lh`, `gold_wh`, seven notebooks, and `pl_snowflake_medallion`.

```powershell
python -m infra.fabric.deploy
python -m infra.fabric.deploy --run --run-date 2026-09-10
```

The second command starts billable Fabric/Snowflake work. Capture its run ID in a private evidence log, then publish only sanitized results.

## 8. Warehouse and governance

Inspect the generated Warehouse contract, then apply the reviewed SQL:

```powershell
python tools\fabric_sql.py warehouse\00_refresh_gold_serving.sql
python tools\fabric_sql.py warehouse\10_apply_security.sql
python tools\fabric_sql.py warehouse\20_validate_security.sql
python -m infra.governance.catalog_setup
python -m infra.governance.catalog_setup --apply
python -m infra.governance.catalog_search --search snowflake
```

Use a private copy of `warehouse/configure_risk_investigator.template.sql` to bind customer principals. Do not commit their identities.

## 9. Optional Git integration

Create the GitHub repository only after tests and both secret scans pass. Fabric Git supports a subset of item types; do not claim unsupported items are synchronized.

```powershell
.\tools\connect-fabric-git.ps1
```

The helper reads workspace/repository values from the local environment and removes the PAT from the process after use. Prefer a fine-grained, short-lived token with only the permissions required for initial connection.

## 10. Evidence gate

Complete [validation.md](validation.md) before calling the POC deployed. Required evidence includes source and mirror counts, replication health, one successful pipeline run, quarantine/reconciliation results, Gold output, Warehouse queries/security, incremental propagation, catalog discovery, and clean working-tree/history secret scans.
