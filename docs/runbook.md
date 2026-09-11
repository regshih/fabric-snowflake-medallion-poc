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
| Fabric connection fails without a useful error | Exact uppercase warehouse/database/schema names; gateway route; Snowflake network policy |
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

- Use X-Small and 60-second auto-suspend for the seed/load warehouse unless measured demand requires more.
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
4. Drop the Snowflake database with the guarded helper:

   ```powershell
   python -m snowflake_source.cleanup --confirm DELETE_SYNTHETIC_SNOWFLAKE_POC
   ```

5. Add `--include-shared-objects` only after proving the configured warehouse and roles are dedicated to this POC.
6. Pause an existing Fabric capacity only with explicit authorization and after confirming it will not interrupt other workloads.

The repository never deletes an Azure resource group, subscription resource, customer database, or unverified shared object.
