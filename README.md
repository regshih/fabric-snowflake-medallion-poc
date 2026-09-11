# Microsoft Fabric + Snowflake medallion POC

This public-ready proof of concept mirrors deterministic synthetic retail-banking data from an existing enterprise-managed Snowflake database on Microsoft Azure into Microsoft Fabric. It then builds governed Silver and Gold layers, a Fabric Warehouse serving model, reconciliation evidence, and a customer-risk analytical scenario.

The repository adapts [`regshih/fabric-medallion-multisource-poc`](https://github.com/regshih/fabric-medallion-multisource-poc). It reuses the Fabric REST client, existing-capacity handling, item definitions, notebooks, pipeline observability, Warehouse controls, governance, and validation patterns while replacing the reference sources with Snowflake.

> All records are synthetic test data. Do not use production or real-person data with this POC.

## Architecture

```text
existing Snowflake database and warehouse on Azure
  dedicated POC schema with six managed synthetic tables
             |
             | Azure Private Link + Fabric VNet data gateway
             | Fabric Snowflake Mirroring
             v
snowflake_bronze (source-aligned Bronze Delta replica in OneLake)
             |
             | pl_snowflake_medallion
             v
silver_lh (conformance, quality, quarantine, lineage)
             |
             v
gold_lh (star schema + AggCustomerRiskProfile)
        |                     |
        v                     v
gold_wh / T-SQL       Direct Lake-ready consumption
```

Bronze is the mirrored database itself. A second physical Bronze Lakehouse would add cost without adding a meaningful contract. See [Architecture](ARCHITECTURE.md) and [Snowflake mirroring behavior](docs/snowflake-fabric-mirroring.md).

## Evidence status

| Area | Evidence in this repository |
|---|---|
| Implementation | Complete repository implementation with CI-enforced tests and scans |
| Secret handling | Working-tree and reachable Git-history scanner included |
| Reference deployment | Snowflake-to-Fabric mirror, medallion pipeline, Warehouse, and incremental behavior validated; see the sanitized [results](docs/live-validation-results.md) |
| Private customer route | Implemented and documented; must be validated in each customer's Business Critical-or-higher Snowflake/VNet environment |

The sanitized reference run used an explicitly configured direct cloud connection. That proves the data path and Fabric implementation, not the customer-specific PrivateLink, DNS, or VNet gateway path.

## Analytical outcome

`AggCustomerRiskProfile` combines transaction volume, transaction-model scores, merchant risk, digital sessions, failed authentication, device trust, geography, and fraud alerts. Supporting outputs include:

- dimensions and facts for customers, accounts, merchants, devices, dates, transactions, sessions, and alerts;
- Silver quarantine tables for malformed or orphaned records;
- `reconciliation_results`, `source_validation_results`, and `control_pipeline_run_log`.

## Repository map

| Path | Purpose |
|---|---|
| `generators/` | Deterministic synthetic CSV generation |
| `snowflake_source/` | Schema/table DDL, least-privilege roles, loader, and schema-scoped cleanup |
| `infra/azure/snowflake-private-endpoint/` | Optional Terraform for the Azure private endpoint and dedicated Fabric gateway subnet |
| `infra/azure/snowflake-private-endpoint-bicep/` | Equivalent Azure-native Bicep deployment with optional delete locks |
| `infra/fabric/` | Fabric REST VNet gateway, private connection, workspace, mirror, Git integration, and capacity controls |
| `infra/governance/` | Catalog descriptions/search, domain assignment, and OneLake access tooling |
| `notebooks/`, `pipelines/`, `warehouse/` | Medallion processing, orchestration, serving, and security contracts |
| `validation/`, `tests/`, `tools/` | Offline/live validators, automated contracts, and secret scanning |
| `prompts/` | Standalone LLM code-editor prompt for customer adaptation |

## Prerequisites

- Python 3.11+, Azure CLI, and PowerShell 7+ where used;
- an existing Fabric capacity and permission to create a dedicated workspace;
- an existing Snowflake account hosted on Azure, an approved existing database, and an approved existing virtual warehouse;
- Snowflake Business Critical Edition or higher when Azure Private Link is required;
- customer-approved Azure VNet, private DNS, private-endpoint subnet, and dedicated Fabric VNet data gateway subnet.

This repository never creates or drops the customer's Snowflake account, database, or warehouse.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest -q
python generators\generate_snowflake_data.py --transactions 1000 --customers 50
python validation\validate_snowflake.py --mode files --data-dir data\snowflake\initial
python tools\security_scan.py --working-tree
```

`.env` is ignored. Keep all credentials, customer identifiers, private endpoint values, and gateway IDs outside Git. The default loader authentication is interactive browser SSO; automation supports separately managed encrypted key pairs and a passphrase file.

Follow the ordered [deployment guide](docs/deployment.md), then use the [runbook](docs/runbook.md) for incremental changes, troubleshooting, costs, and safe cleanup.

## Customer implementation prompt

[`prompts/llm-code-editor-prompt.md`](prompts/llm-code-editor-prompt.md) can be pasted into an LLM-enabled code editor opened at this repository. It directs the editor to use an existing enterprise Snowflake database and private Fabric connection, preserve security boundaries, deploy idempotently, and report only evidenced results.

## Security

- No credentials, private keys, passwords, account locators, hosts, tenant/subscription IDs, endpoint values, or live Fabric IDs are committed.
- Fabric automation authenticates with Microsoft Entra ID through Azure CLI/`DefaultAzureCredential`.
- The customer path defaults to a Fabric VNet data gateway and a Snowflake private hostname. Public `ShareableCloud` connectivity requires explicit lab configuration.
- The mirror definition contains only a Fabric connection ID and object names, never connection credentials.
- Snowflake policies do not propagate to Fabric; apply Fabric permissions independently.

Read [SECURITY.md](SECURITY.md) before deployment. Repository visibility must remain private until its owner explicitly approves publication.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Deployment](docs/deployment.md)
- [Snowflake-to-Fabric mirroring](docs/snowflake-fabric-mirroring.md)
- [Runbook, cost, and cleanup](docs/runbook.md)
- [Validation checklist](docs/validation.md)
- [Live validation results](docs/live-validation-results.md)
- [Governance and security](docs/governance-security.md)
- [Known limitations](docs/known-limitations.md)
- [Implementation decisions](docs/implementation-decisions.md)

## Official references

- [Mirroring Snowflake in Fabric](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake)
- [Snowflake mirroring tutorial](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake-tutorial)
- [Fabric VNet data gateway overview](https://learn.microsoft.com/en-us/data-integration/vnet/overview)
- [Snowflake Azure Private Link](https://docs.snowflake.com/en/user-guide/privatelink-azure)
- [Fabric mirrored database REST definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/mirrored-database-definition)

## License

Released under the [MIT License](LICENSE).
