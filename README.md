# Microsoft Fabric + Snowflake medallion POC

This public-ready proof of concept mirrors synthetic retail-banking data from Snowflake hosted on Microsoft Azure into Microsoft Fabric, then builds governed Silver and Gold layers, a Fabric Warehouse serving model, reconciliation evidence, and a customer-risk analytical scenario.

The repository is an adaptation of [`regshih/fabric-medallion-multisource-poc`](https://github.com/regshih/fabric-medallion-multisource-poc). It reuses the Fabric REST client, workspace and existing-capacity handling, item definitions, notebooks, pipeline observability, Warehouse controls, governance, and validation patterns while replacing the two reference sources with one Snowflake database.

> All records are deterministic synthetic test data. Do not use production or real-person data with this POC.

## Architecture

```text
Snowflake on Azure
  six managed synthetic banking tables
             |
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

Bronze is the mirrored database itself. A second physical Bronze Lakehouse would add cost without adding a meaningful contract. See [ARCHITECTURE.md](ARCHITECTURE.md) and [Snowflake mirroring behavior](docs/snowflake-fabric-mirroring.md).

## Evidence status

| Area | Evidence in this repository |
|---|---|
| Implementation | Complete local repository implementation |
| Automated tests | 44 passing tests at initial publication gate |
| Secret handling | Working-tree and Git-history scanner included |
| Snowflake/Fabric deployment | Not claimed; requires a customer's Snowflake account, Fabric connection, and active capacity |
| End-to-end pipeline | Not claimed until the live checklist is completed |

The repository deliberately distinguishes local implementation from deployed infrastructure and live validation. Update [docs/live-validation-results.md](docs/live-validation-results.md) only with sanitized evidence from an actual run.

## Analytical outcome

`AggCustomerRiskProfile` combines transaction volume, transaction-model scores, merchant risk, digital sessions, failed authentication, device trust, geography, and fraud alerts. Supporting outputs include:

- `DimCustomer`, `DimAccount`, `DimMerchant`, `DimDevice`, and `DimDate`
- `FactTransactions`, `FactDigitalSessions`, and `FactFraudAlerts`
- `AggCustomerRiskProfile`
- `reconciliation_results`, `source_validation_results`, and `control_pipeline_run_log`
- Silver quarantine tables for malformed or orphaned records

## Repository map

| Path | Purpose |
|---|---|
| `generators/` | Deterministic synthetic CSV generation |
| `snowflake_source/` | Snowflake DDL/grants, connection helper, loader, and guarded cleanup |
| `infra/snowflake/account-bootstrap/` | Optional Terraform account creation from an existing Snowflake organization |
| `infra/fabric/` | Fabric REST workspace, items, Snowflake mirror, Git integration, and capacity controls |
| `infra/governance/` | Catalog descriptions/search, domain assignment, and OneLake access tooling |
| `notebooks/` | Source validation, Silver, Gold, Warehouse, reconciliation, audit, and demo notebooks |
| `pipelines/` | `pl_snowflake_medallion` orchestration with success/failure paths |
| `warehouse/` | Gold serving, RLS, masking, and validation SQL |
| `validation/`, `tests/` | Offline/live validators and automated contracts |
| `tools/` | Fabric SQL/Git helpers and secret scanner |
| `prompts/` | Standalone LLM code-editor prompt for customer adaptation |

## Quick start

Prerequisites are Python 3.11+, Azure CLI, PowerShell 7+ where used, an existing Fabric capacity, and a Snowflake account hosted on Azure. Organizations with an existing Snowflake `ORGADMIN` account can create a dedicated Azure West US 2 account through the optional [Terraform bootstrap module](infra/snowflake/account-bootstrap/README.md).

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

`.env` is ignored. Keep all credentials outside Git. The default loader authentication is interactive browser SSO; key-pair paths and passphrases are local-only values.

Follow [docs/deployment.md](docs/deployment.md) for the ordered Snowflake and Fabric setup. Use [docs/runbook.md](docs/runbook.md) for operations, incremental changes, troubleshooting, costs, and cleanup.

## Customer implementation prompt

[`prompts/llm-code-editor-prompt.md`](prompts/llm-code-editor-prompt.md) can be pasted into an LLM-enabled code editor together with this repository. It tells the editor how to inspect the environment, preserve the security boundary, deploy idempotently, validate evidence, and avoid unsupported claims.

## Security

- No credentials, private keys, passwords, account locators, tenant/subscription IDs, or live item IDs are committed.
- Fabric automation authenticates with Microsoft Entra ID through Azure CLI/`DefaultAzureCredential`.
- Snowflake loaders default to interactive SSO and support separately managed encrypted key pairs.
- The mirror definition contains only a Fabric connection ID and object names—not connection credentials.
- Source security policies do not propagate to Fabric; apply Fabric permissions independently.

Read [SECURITY.md](SECURITY.md) before deployment.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Snowflake-to-Fabric mirroring](docs/snowflake-fabric-mirroring.md)
- [Deployment](docs/deployment.md)
- [Runbook, cost, and cleanup](docs/runbook.md)
- [Validation checklist](docs/validation.md)
- [Live validation results template](docs/live-validation-results.md)
- [Governance and security](docs/governance-security.md)
- [Known limitations](docs/known-limitations.md)
- [Implementation decisions](docs/implementation-decisions.md)

## Official references

- [Microsoft Fabric Mirroring overview](https://learn.microsoft.com/en-us/fabric/mirroring/overview)
- [Mirroring Snowflake in Fabric](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake)
- [Snowflake mirroring tutorial](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake-tutorial)
- [Snowflake mirroring limitations](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake-limitations)
- [Fabric mirrored database REST definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/mirrored-database-definition)
- [Snowflake Python connector authentication](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect)

## License

Released under the [MIT License](LICENSE).
