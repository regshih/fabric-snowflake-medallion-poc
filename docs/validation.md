# Validation and evidence checklist

Local tests prove repository contracts; live checks prove platform behavior. Do not substitute one for the other.

## Local gate

```powershell
python -m pytest -q
python generators\generate_snowflake_data.py --transactions 1000 --customers 50 --merchants 25 --devices 75 --sessions 200 --alerts 20
python validation\validate_snowflake.py --mode files --data-dir data\snowflake\initial
python tools\security_scan.py --working-tree
python -m compileall -q generators snowflake_source validation infra tools
```

Verify additionally:

- pipeline JSON parses and every symbolic binding resolves in tests;
- all Fabric notebook sources parse as Python and retain Fabric metadata;
- the mirrored database definition selects exactly six tables and contains no credential material;
- Snowflake identifiers reject injection characters;
- `.env`, data, keys, caches, and logs are ignored;
- documentation contains no claim of a live deployment before one occurs.

## Live Snowflake gate

- [ ] Authentication succeeds with the intended non-admin runtime role.
- [ ] Warehouse is X-Small/approved size, auto-resume enabled, and auto-suspend configured.
- [ ] The database/schema contain exactly the intended POC objects.
- [ ] All six objects are permanent managed tables.
- [ ] Change tracking is enabled on all six tables by the setup role; the mirror role is not granted `MODIFY`.
- [ ] `validation/validate_snowflake.py --mode live` returns positive counts.
- [ ] Alert-to-transaction join returns expected synthetic matches.
- [ ] Loader role cannot access unrelated databases.
- [ ] Mirror role can select/discover POC tables and create streams, but cannot mutate source data.

## Live Fabric gate

- [ ] Dedicated workspace is assigned to the intended existing capacity.
- [ ] `snowflake_bronze` targets the intended connection/database/schema.
- [ ] Only the six selected tables appear.
- [ ] All six replication states are healthy after initial copy.
- [ ] Spark and SQL analytics endpoint can read expected counts.
- [ ] `pl_snowflake_medallion` completes with one shared run ID.
- [ ] Every material stage writes an audit row.
- [ ] Source validation contains six passing object rows.
- [ ] Source = Silver + quarantine for each table after deduplication assumptions are considered.
- [ ] Fact/dimension counts match their corresponding valid Silver grain.
- [ ] `AggCustomerRiskProfile` is populated.
- [ ] Suspicious-transaction drill-through links alert, transaction, merchant, device, and session behavior.
- [ ] Warehouse serving SQL runs successfully.
- [ ] RLS/DDM tests are performed with a temporary least-privilege identity and sanitized evidence.
- [ ] Catalog descriptions/search and optional domain assignment work.

## Incremental gate

- [ ] Record source/mirror counts and UTC time before loading.
- [ ] Apply `data/snowflake/incremental` through the merge loader.
- [ ] Observe the changed/new rows in Snowflake.
- [ ] Observe the same rows in the mirror without manual table copying.
- [ ] Re-run the pipeline and validate the changed customer profile.
- [ ] Record measured propagation time without describing it as a service-level guarantee.
- [ ] Confirm no unexpected reseed occurred.

## Publication gate

```powershell
python tools\security_scan.py --working-tree --git-history
git status --short
```

- [ ] No secret-scan findings.
- [ ] No `.env`, credentials, private keys, generated data, logs, IDs, or customer identities are tracked.
- [ ] `docs/live-validation-results.md` contains sanitized evidence only.
- [ ] Broken links and stale references are removed.
- [ ] Repository visibility is confirmed before creation/push.
