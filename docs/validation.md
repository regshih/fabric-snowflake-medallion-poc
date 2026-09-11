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
- documentation distinguishes the validated direct reference path from the unvalidated customer private path.

## Private connectivity gate

- [ ] Snowflake is hosted on Azure and the actual product edition is Business Critical or higher.
- [ ] `SYSTEM$GET_PRIVATELINK_CONFIG()` is obtained by an approved administrator and never committed or logged.
- [ ] The Azure private endpoint is created in the approved subnet and authorized in Snowflake.
- [ ] The Snowflake account and OCSP hostnames resolve to private IPs from the gateway VNet.
- [ ] TLS connectivity succeeds from the VNet, using SnowCD or another approved test.
- [ ] `Microsoft.PowerPlatform` is registered and the dedicated gateway subnet is delegated only to `Microsoft.PowerPlatform/vnetaccesslinks`.
- [ ] The Fabric VNet data gateway is online in the correct region/capacity and uses the intended VNet/subnet.
- [ ] The Fabric connection reports `VirtualNetworkGateway`, the intended gateway ID, and the private Snowflake hostname.
- [ ] Any public endpoint access matches the customer's Snowflake and Azure network policy.

## Live Snowflake gate

- [ ] Authentication succeeds with the intended non-admin runtime role.
- [ ] The configured existing database and approved warehouse were verified before setup.
- [ ] The dedicated POC schema contains exactly the intended POC objects; unrelated database schemas are unchanged.
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
- [ ] Repository remains private until its owner explicitly approves publication.
- [ ] Cleanup dry-run contains only the dedicated schema and optional dedicated roles, never database/warehouse deletion.
