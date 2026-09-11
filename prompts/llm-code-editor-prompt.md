# LLM code-editor prompt: Fabric + Snowflake medallion POC

Copy the content below into an LLM-enabled code editor opened at the root of this repository. Replace only known non-secret placeholders. Never put a credential in this prompt.

---

## Environment placeholders

| Placeholder | Meaning | Safe default/behavior |
|---|---|---|
| `<GITHUB_OWNER>` | GitHub user or organization | Ask only if it cannot be inferred |
| `<REPOSITORY_NAME>` | Repository target; keep private until owner approval | `fabric-snowflake-medallion-poc` |
| `<FABRIC_WORKSPACE_NAME>` | Dedicated Fabric workspace | `fabric-snowflake-medallion-poc` |
| `<FABRIC_CAPACITY_NAME>` | Existing reusable capacity | Inspect and reuse a suitable nonproduction capacity |
| `<AZURE_SUBSCRIPTION_ID>` | Azure subscription for the Fabric capacity | Infer only from an unambiguous authenticated context; never commit |
| `<AZURE_TENANT_ID>` | Microsoft Entra tenant | Infer only when unambiguous; never commit |
| `<FABRIC_REGION>` | Fabric capacity region | Prefer the Snowflake Azure region |
| `<SNOWFLAKE_ACCOUNT>` | Snowflake account identifier | Required at runtime; never commit a customer value |
| `<SNOWFLAKE_WAREHOUSE>` | Existing customer-approved warehouse | Required; no default |
| `<SNOWFLAKE_DATABASE>` | Existing enterprise database | Required; no default |
| `<SNOWFLAKE_SCHEMA>` | New dedicated POC schema in the existing database | Required; no default |
| `<SNOWFLAKE_LOADER_ROLE>` | Synthetic data loader role | `FABRIC_POC_LOADER` |
| `<SNOWFLAKE_MIRROR_ROLE>` | Fabric mirroring role | `FABRIC_POC_MIRROR` |
| `<SNOWFLAKE_PRIVATE_HOST>` | Snowflake `privatelink-account-url` hostname | Required at runtime; never commit |
| `<FABRIC_VNET_GATEWAY_ID>` | Existing Fabric VNet data gateway | Required at runtime; never commit |

Names and non-secret IDs may be supplied locally. Passwords, private keys, key passphrases, OAuth tokens, personal access tokens, connection strings, Fabric connection credentials, and real customer data must not appear in the prompt or repository.

## Role and objective

You are the lead engineer implementing and validating a customer-safe Microsoft Fabric proof of concept. Use this repository as the primary implementation. Preserve its tested patterns unless current official documentation or the target environment requires a change.

The architecture is:

```text
Snowflake hosted on Microsoft Azure
  six permanent managed synthetic banking tables
                     |
                     | Microsoft Fabric Snowflake Mirroring
                     v
snowflake_bronze mirrored database (source-aligned Bronze in OneLake)
                     |
                     | Fabric pipeline and Spark notebooks
                     v
silver_lh (conformance, quality, quarantine, lineage)
                     |
                     v
gold_lh (dimensions, facts, AggCustomerRiskProfile)
               |                         |
               v                         v
          gold_wh / SQL             Direct Lake-ready
```

Deliver a working, evidence-backed POC where permissions and environment allow. Do not label anything deployed, validated, secure, or supported without corresponding evidence.

## Mandatory safety rules

1. Treat the repository as public from the first edit.
2. Never commit `.env`, credentials, keys, tokens, account locators, hosts, tenant/subscription IDs, Fabric workspace/item/connection IDs, principal identities, query/run URLs, generated data, logs, notebook output, or tenant screenshots.
3. Use `.env.example` only for placeholders and safe defaults.
4. Use Azure CLI/Microsoft Entra authentication for Fabric.
5. Default local Snowflake access to interactive browser/Entra SSO. For automation, use an encrypted, rotated RSA key stored outside the repository or another customer-approved workload identity pattern.
6. Never solve a Snowflake access error by granting `ACCOUNTADMIN`, ownership of unrelated objects, or broad future grants outside the POC schema.
7. Never mirror an entire customer database by default. Select the six POC tables explicitly.
8. Never create, resize, suspend, resume, or delete the customer's Snowflake account, database, or warehouse.
9. Do not delete shared capacity, connections, workspaces, resource groups, private endpoints, DNS, gateways, or repositories without explicit authorization and exact-target verification.
10. Keep cleanup scoped to the dedicated POC schema and optional dedicated roles, protected by an explicit confirmation flag.
11. Run working-tree and Git-history secret scans before any public push. Rotate a real exposed credential before rewriting history.
12. Keep the repository private until its owner explicitly approves publication.

## Inspect before changing

1. Read `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `docs/implementation-decisions.md`, and `.env.example`.
2. Run `git status --short`; preserve unrelated user changes.
3. Run the local tests before editing and record the baseline count.
4. Inspect the authenticated Azure/Fabric context without printing tokens.
5. Inspect Snowflake only through an approved authenticated session. Do not echo connection parameters.
6. Confirm whether the intended Fabric capacity is active and whether reuse can affect other workspaces.
7. Verify current product behavior from official Microsoft Fabric and Snowflake documentation before changing mirror definitions, authentication, networking, or supported-object claims.
8. Record inferred non-secret decisions in `docs/implementation-decisions.md`.

## Required source implementation

Use permanent managed tables in `<SNOWFLAKE_DATABASE>.<SNOWFLAKE_SCHEMA>`:

- `TRANSACTIONS`
- `TRANSACTION_RISK`
- `MERCHANTS`
- `DIGITAL_SESSIONS`
- `DEVICES`
- `FRAUD_ALERTS`

Keep identifiers unquoted and uppercase to avoid case drift at the Fabric boundary. Preserve shared synthetic `CUSTOMER_ID`, `TRANSACTION_ID`, `DEVICE_ID`, `MERCHANT_ID`, and `ACCOUNT_ID` relationships.

Use `snowflake_source/sql/00_setup.sql` as the reviewed, idempotent setup contract. It must verify and reuse `<SNOWFLAKE_DATABASE>` and `<SNOWFLAKE_WAREHOUSE>`, then create only the dedicated POC schema, six tables, and separate loader/mirror roles. It must never create or alter the database or warehouse. The mirror role should have only warehouse/database/schema usage, schema `CREATE STREAM`, table `SELECT`, and required discovery privileges. A Snowflake administrator assigns the roles to actual principals in a private working copy of the assignment template.

Generate deterministic synthetic data with `generators/generate_snowflake_data.py`. Validate files before loading. Load through session-scoped staging tables and keyed `MERGE`, not unbounded row-by-row mutations. Demonstrate an incremental insert/update batch and make retries safe.

## Required Fabric implementation

Reuse an existing suitable Fabric capacity and create a dedicated workspace. Do not attach POC items to the reference workspace or an unrelated production workspace.

Create `snowflake_bronze` using the credential-free Fabric REST mirrored-database definition in `infra/fabric/source_mirror.py`. Bind the Fabric connection ID at runtime. Select exactly the six tables. If immutable source drift would require recreation, fail closed unless `FABRIC_ALLOW_SNOWFLAKE_MIRROR_RECREATE=true` is explicitly set; document that recreation can cause a full reseed.

Deploy:

- `silver_lh`
- `gold_lh`
- `gold_wh`
- `nb_source_validation`
- `nb_silver_transform`
- `nb_gold_build`
- `nb_warehouse_publish`
- `nb_reconciliation`
- `nb_pipeline_log`
- `nb_gold_consumption_demo`
- `pl_snowflake_medallion`

The pipeline must use one shared run ID and run date, log start/success, validate the source, build Silver, build Gold, publish the Warehouse contract, reconcile results, and log each material failure path.

## Medallion contracts

Bronze is the Snowflake mirror. Do not create an empty or redundant Bronze Lakehouse.

Silver must provide:

- explicit types and normalized analytical names;
- UTC-compatible timestamps;
- business-key deduplication;
- risk-range and relationship validation;
- valid tables for all six entities;
- meaningful quarantine tables and reasons;
- `source_system`, `pipeline_run_id`, `run_date`, and load timestamp lineage.

Gold must provide a compact star schema:

- `DimCustomer`, `DimAccount`, `DimMerchant`, `DimDevice`, `DimDate`;
- `FactTransactions`, `FactDigitalSessions`, `FactFraudAlerts`;
- `AggCustomerRiskProfile`;
- reconciliation and audit outputs.

At least one investigation query must combine transaction risk, merchant information, device trust, session/authentication behavior, and a linked fraud alert. Keep the risk calculation deterministic and explainable; do not claim it is an ML model.

## Governance and security

Treat Snowflake and Fabric as separate authorization planes. Snowflake row-access, masking, and column policies do not propagate through Mirroring. Apply customer-approved Fabric workspace/item access, OneLake security, semantic-model security, and Warehouse RLS/DDM independently.

Keep catalog descriptions and lineage useful. Assign a Fabric domain only if an existing approved domain ID and permission are available. Use dry-run behavior before governance mutations.

For Warehouse security tests, use a temporary least-privilege identity, record sanitized pass/fail evidence, and remove the temporary access afterward. Never commit the identity.

## Networking and cost

Assume an existing enterprise Snowflake environment and require the private route by default. Confirm that the actual Snowflake product edition is Business Critical or higher, discover/authorize Azure PrivateLink through a customer Snowflake administrator, configure private account and OCSP DNS, and use a Fabric VNet data gateway on a dedicated subnet delegated to `Microsoft.PowerPlatform/vnetaccesslinks`. Reuse an approved existing gateway or create it idempotently with `infra/fabric/vnet_gateway.py` only after explicit customer approval. Set the Fabric connection to `VirtualNetworkGateway`, the approved gateway ID, and `<SNOWFLAKE_PRIVATE_HOST>`. Never commit PrivateLink output, endpoint values, DNS inventory, or gateway IDs.

Allow `ShareableCloud` only when the owner explicitly authorizes a public-network lab exception. Clearly label its evidence as direct cloud rather than private-path validation.

Prefer region alignment between Snowflake on Azure and the Fabric capacity. Mirror only required tables, use bounded data, monitor Snowflake credits/Fabric utilization, and watch for unexpected reseeds. Remember that mirroring polls continuously and that stop/start, DDL, schema recreation, or a long capacity pause can trigger a full reseed.

## Validation gates

Run locally:

```powershell
python -m pytest -q
python generators\generate_snowflake_data.py --transactions 1000 --customers 50 --merchants 25 --devices 75 --sessions 200 --alerts 20
python validation\validate_snowflake.py --mode files --data-dir data\snowflake\initial
python -m compileall -q generators snowflake_source validation infra tools
python tools\security_scan.py --working-tree
```

For live validation, complete every applicable item in `docs/validation.md`. Capture source/mirror/Silver/quarantine/Gold counts, healthy replication states, the pipeline run result, audit/reconciliation rows, risk-profile output, Warehouse security, incremental propagation, and absence of unexpected reseed.

Before publishing:

```powershell
python tools\security_scan.py --working-tree --git-history
git status --short
```

Manually inspect tracked files for environment identifiers and screenshots. Do not publish until tests and both scans pass.

## Documentation and evidence standard

Keep `README.md`, architecture, mirroring behavior, deployment, runbook, validation, limitations, security, cost, cleanup, and implementation decisions synchronized with the code. Link only to current official product documentation for behavioral claims.

Maintain three distinct statuses:

1. locally implemented/tested;
2. Snowflake/Fabric infrastructure deployed;
3. end-to-end/incremental behavior verified.

Never promote a lower status into a higher claim. Put sanitized measured results in `docs/live-validation-results.md`; state "Not run" when no live evidence exists and identify whether evidence used the private or direct cloud route.

## Completion criteria

The task is complete only when:

- repository tests and compilation pass;
- file generation and validation pass;
- the mirror definition is selective and credential-free;
- least-privilege role SQL is reviewed;
- notebook and pipeline symbolic bindings resolve without embedded environment IDs;
- secret scans pass;
- documentation reflects actual evidence;
- cleanup is safe and explicitly guarded;
- setup and cleanup preserve the existing Snowflake database and warehouse;
- PrivateLink, DNS, VNet gateway, and private connection checks are evidenced in the customer environment;
- any optional live deployment has customer authorization and recorded sanitized evidence.

If credentials, permissions, capacity state, or networking block live execution, finish all safe offline work, document the exact blocker and next command, and do not fabricate success.

---
