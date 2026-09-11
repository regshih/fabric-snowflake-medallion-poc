# Snowflake on Azure to Microsoft Fabric

## What the integration does

Microsoft Fabric Snowflake Mirroring continuously copies selected Snowflake managed tables into the customer's OneLake and converts the data to analytics-ready Delta/Parquet. Fabric also creates a read-only SQL analytics endpoint. This is physical replication, not a zero-copy shortcut.

This POC treats the `snowflake_bronze` mirrored database as the source-aligned Bronze layer. The first deliberate transformation copy is `silver_lh`, where the pipeline standardizes types and names, deduplicates rows, validates relationships, records lineage, and quarantines invalid data.

Official references:

- [Mirroring Snowflake in Microsoft Fabric](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake)
- [Snowflake mirroring tutorial](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake-tutorial)
- [Snowflake mirroring limitations](https://learn.microsoft.com/en-us/fabric/mirroring/snowflake-limitations)
- [Mirrored database REST definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/mirrored-database-definition)

## POC object selection

The checked-in definition selects only six managed tables from `BANKING_SOURCE`:

| Snowflake table | Analytical purpose |
|---|---|
| `TRANSACTIONS` | Transaction facts and customer/account behavior |
| `TRANSACTION_RISK` | Deterministic synthetic model scores |
| `MERCHANTS` | Merchant attributes and risk categories |
| `DIGITAL_SESSIONS` | Authentication, location, and session risk |
| `DEVICES` | Device trust and synthetic risk signals |
| `FRAUD_ALERTS` | Fraud investigation alerts linked to transactions |

Selective mirroring bounds Snowflake compute and Fabric capacity consumption and avoids accidentally ingesting unrelated customer tables.

## Permissions

The Fabric connection principal needs a role that can use the configured warehouse, database, and schema; create streams in the selected schema; select the mirrored tables; and discover/describe those objects. `snowflake_source/sql/00_setup.sql` creates a dedicated `FABRIC_POC_MIRROR` role with the minimum POC grants. A Snowflake administrator must assign that role to the actual connection principal using a private copy of `10_assign_roles.template.sql`.

Snowflake row-access, masking, and column policies do not propagate to OneLake. Reapply access controls through Fabric workspace/item permissions, OneLake security, semantic-model security, and Warehouse RLS/DDM as appropriate.

## Authentication

Fabric supports Snowflake username/password, Microsoft Entra SSO, and RSA key-pair authentication. Workspace identity is not currently supported for this source. Prefer Entra SSO for an interactive POC or a separately managed, rotated key pair for noninteractive use. Never commit a password, private key, passphrase, Fabric connection credential, or exported connection definition.

Local loaders default to `externalbrowser`. If a customer chooses key-pair authentication, the encrypted private-key file must live outside the repository and its path/passphrase must be supplied through the ignored local environment.

## Networking

For a publicly reachable Snowflake endpoint allowed by the account network policy, the Fabric cloud connection can connect directly. For private connectivity, use a Fabric virtual network data gateway or an on-premises data gateway with network access to the Snowflake private endpoint. Direct Private Link from the Fabric workspace to Snowflake is not currently supported.

The Snowflake account should be hosted on Azure in the same region as the Fabric capacity where practical. Cross-region placement can add latency and egress charges.

## Operational behavior and limitations

- Identifiers are case-sensitive at the Fabric connection and mirroring boundary. The repository deliberately uses unquoted uppercase identifiers.
- Managed and Iceberg tables are supported. This POC uses managed tables; it does not depend on external, transient, temporary, or dynamic tables.
- Fabric currently mirrors at most 1,000 tables per mirrored database.
- Mirroring continuously polls Snowflake; it has no replication schedule window.
- Inactive tables can back off to polling intervals of up to an hour, then return to normal polling after changes are detected.
- DDL changes, stop/start operations, and long capacity pauses can cause a full table reseed and additional Snowflake compute.
- The mirrored database and its SQL analytics endpoint are read-only. Silver and Gold calculations belong in Lakehouses or a Warehouse.
- Source policies are a different authorization boundary and must be recreated in Fabric.

## Cost controls

Start with the six selected tables and the X-Small, 60-second-auto-suspend warehouse in the setup template. Reusing the writer warehouse can reduce wake-up overhead, while a dedicated warehouse improves budget isolation. Monitor warehouse credits, Fabric capacity utilization, and unexpected initial-copy/reseed activity. Stopping and restarting mirroring solely to save idle compute can be counterproductive because restart triggers a reseed.
