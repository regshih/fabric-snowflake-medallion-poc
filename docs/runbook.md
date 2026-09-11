# Operations runbook

## Normal run

1. Confirm the Snowflake warehouse is available and the six source tables are nonempty.
2. Confirm the Fabric capacity is active and `snowflake_bronze` shows healthy replication.
3. Start `pl_snowflake_medallion`, optionally passing an ISO `run_date`.
4. Record the Fabric run ID privately.
5. Verify the pipeline success row, source-validation rows, reconciliation rows, quarantine counts, and Warehouse refresh contract.

Retry with the same pipeline run identity only through the platform retry path. Silver/Gold overwrite writes and audit/reconciliation merges are idempotent at POC grain.

## Incremental demonstration

```powershell
python -m snowflake_source.load --batch incremental
python validation\validate_snowflake.py --mode live
```

Record source counts and UTC time before the load. Watch Fabric replication until the inserted transaction/risk/session/alert and updated device are visible. Run the pipeline, validate `CUST-000001`, and record measured propagation time as an observation—not an SLA.

## Troubleshooting

| Symptom | Check |
|---|---|
| Snowflake login fails | Account identifier, user, authenticator, role, MFA/network policy, key path/passphrase |
| Private connection fails | Private account/OCSP DNS, endpoint approval, Snowflake network policy, gateway status/region, exact warehouse/database/schema casing |
| No tables offered for mirroring | Managed-table type, mirror-role usage/select/create-stream grants, exact database/schema |
| Mirror table is delayed | Replication monitor, inactive-table polling backoff, Snowflake warehouse availability |
| Mirror unexpectedly performs initial copy | Recent DDL, stop/start, long capacity pause, schema-management tools |
| Spark path fails | Mirrored item ID, source schema hierarchy, exact table casing, workspace access |
| Silver count differs | Quarantine table and duplicate business-key logic |
| Alert relationship warns | Synthetic batch completeness and `TRANSACTION_ID` overlap |
| Warehouse query/security fails | Refresh contract, SQL endpoint, RLS/DDM principal binding, workspace role |
| Git connection fails | Fine-grained PAT scope, repository/branch/directory, Fabric workspace Admin role |

## Cost management

The cost surfaces are the Snowflake virtual warehouse, Snowflake storage, cross-region/cloud egress, the existing Fabric capacity while active, and OneLake storage above included mirroring allowance.

- Use the customer-approved warehouse and its resource monitor; coordinate sizing and auto-suspend changes with its owner.
- Mirror only the six POC tables.
- Co-locate Snowflake on Azure and Fabric where practical.
- Monitor repeated reseeds; they can be more expensive than incremental polling.
- Do not stop/start mirroring as a routine scheduler because restart can trigger a full reseed.
- Scale dataset counts deliberately; defaults are for functional evidence, not benchmarking.
- Pause the reusable Fabric capacity only after checking unrelated workloads.

Pricing changes by region, agreement, and date, so the repository intentionally provides no dollar estimate.

## Cleanup

Cleanup is intentionally split across security boundaries.

1. Export only sanitized evidence needed for the customer handoff.
2. Delete the dedicated Fabric workspace through the portal after verifying its exact name and contents.
3. Remove the Fabric Snowflake connection only if no other workspace uses it.
4. Drop only the dedicated Snowflake POC schema with the guarded helper:

   ```powershell
   python -m snowflake_source.cleanup --confirm DELETE_SYNTHETIC_POC_SCHEMA --confirm-schema <dedicated-poc-schema>
   ```

5. Add `--include-dedicated-roles` only after verifying the two roles are dedicated to this POC and are not assigned for another purpose.
6. Pause an existing Fabric capacity only with explicit authorization and after confirming it will not interrupt other workloads.

The helper never drops the configured database or warehouse. Removing Azure private endpoints, DNS records, gateway resources, resource groups, or other customer-owned infrastructure requires a separately reviewed customer change.
