# Live validation results

> Status: Executed successfully in a dedicated POC environment.

This file contains sanitized evidence only. Do not commit account locators, tenant/subscription IDs, workspace/item IDs, user names, connection IDs, query IDs, tokens, or screenshots containing them.

## Environment summary

| Attribute | Sanitized value |
|---|---|
| Validation date (UTC) | 2026-09-11 |
| Snowflake cloud | Microsoft Azure |
| Region alignment | Snowflake Azure West US 2; Fabric West US 3 |
| Fabric capacity SKU | F4 (existing capacity reused) |
| Dataset parameters | 10,000 baseline transactions plus one deterministic incremental transaction |

## Counts after the incremental run

| Table | Snowflake source | Fabric mirror | Silver valid | Quarantine | Gold equivalent |
|---|---:|---:|---:|---:|---:|
| Transactions | 10,001 | 10,001 | 10,001 | 0 | 10,001 |
| Transaction risk | 10,001 | 10,001 | 10,001 | 0 | n/a |
| Merchants | 300 | 300 | 300 | 0 | 300 |
| Digital sessions | 1,501 | 1,501 | 1,501 | 0 | 1,501 |
| Devices | 375 | 375 | 375 | 0 | 375 |
| Fraud alerts | 151 | 151 | 151 | 0 | 151 |

## Pipeline and incremental observations

- Pipeline status: two completed runs with no Fabric failure payload (10m15s baseline; 11m58s incremental).
- Reconciliation status: 14/14 checks passed across the two runs; zero warnings or failures.
- Gold customer profiles: 250 after each run; the deterministic incremental customer was `Medium` risk at 68.35.
- Incremental propagation observation: current mirror counts converged in approximately two minutes; the device metric recorded one update event while its current row count remained 375.
- Unexpected reseed observed: no.

## Security/governance evidence

- Least-privilege Snowflake roles: verified with a dedicated key-pair service user; runtime role has usage/select/create-stream and no table `MODIFY`.
- Fabric source/serving security: six explicitly selected managed tables; connection credential is stored in Fabric, not item definitions or Git.
- Warehouse RLS/DDM: one enabled RLS policy and two masked columns verified; enforcement with a customer Viewer identity remains a customer-environment step.
- Catalog descriptions/search: item descriptions deployed; cross-workspace catalog search remains an optional tenant-governance step.
- Fabric Git: private GitHub repository used; Fabric Git connection remains optional because it requires a customer-managed PAT/connection.
- Working-tree and history secret scans: passed before private-repository push.
