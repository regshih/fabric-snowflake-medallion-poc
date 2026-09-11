# Known limitations

## Evidence boundary

The checked-in automated tests are local evidence. The sanitized reference run established direct cloud Snowflake-to-Fabric replication and medallion behavior, but did not test a customer PrivateLink endpoint, DNS, or Fabric VNet data gateway. Complete `docs/validation.md` in each target environment.

## Snowflake Mirroring

- Fabric connection and mirroring identifiers are case-sensitive and mismatches can produce weak diagnostics.
- Workspace identity is not currently supported for Snowflake Mirroring.
- Direct Fabric workspace Private Link to Snowflake is not currently supported; private access needs a VNet or on-premises data gateway.
- Snowflake Azure Private Link requires Business Critical Edition or higher. Customer DNS, endpoint authorization, network policy, subnet sizing, and gateway region/permissions are environment-specific.
- This POC uses permanent managed tables. External, transient, temporary, and dynamic tables are not supported by the intended path.
- Fabric currently limits a mirrored database to 1,000 tables; this POC selects six.
- Mirroring continuously polls and has no scheduling window. Inactive-table polling can back off to an hour.
- DDL, stop/start, schema recreation, and long Fabric-capacity pauses can trigger a full reseed.
- Snowflake RLS, masking, and column policies are not copied into Fabric.
- The mirrored SQL analytics endpoint is read-only.

Sources: [overview](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake), [tutorial](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake-tutorial), [limitations](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake-limitations), and [FAQ](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake-mirroring-faq).

## POC design

- The synthetic risk score is explanatory demo logic, not a trained or validated fraud model.
- Source tables are relational and store bounded JSON examples as strings; the POC does not claim exhaustive Snowflake semi-structured-type compatibility.
- Silver and Gold use full overwrite at bounded POC scale. Production workloads need measured incremental/partition/file-optimization design.
- Snowflake primary-key declarations are informational and not enforced; the loader and Silver deduplication provide POC idempotency.
- Defaults do not establish throughput, concurrency, skew, recovery, or cost characteristics.
- The repository requires an existing database and warehouse and deliberately does not provision, resize, suspend, resume, or delete them.
- One Snowflake database replaces the two external platforms from the reference POC. The retained scenario demonstrates cross-domain joins, not multi-platform integration.
- Fabric REST APIs and item definitions evolve. Revalidate official documentation before customer deployment.
