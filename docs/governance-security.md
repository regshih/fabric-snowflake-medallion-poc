# Governance and security

## Independent authorization planes

| Plane | Control |
|---|---|
| Snowflake loader | Dedicated role with POC warehouse/database/schema usage and table DML only |
| Snowflake mirror | Dedicated role with warehouse/database/schema usage, schema `CREATE STREAM`, and table `SELECT` |
| Fabric connection | Credential stored and managed by Fabric, never Git |
| Private network | Snowflake PrivateLink, customer private DNS, and a Fabric VNet data gateway |
| Fabric workspace/items | Workspace roles and item permissions |
| OneLake | OneLake security roles where supported |
| Warehouse | Object grants, row-level security, and dynamic data masking |
| GitHub/Fabric Git | Repository permissions and supported-item synchronization |

Snowflake security policies do not propagate through Mirroring. A source principal's ability to select a table authorizes replication, while access to the replicated Delta data is controlled separately in Fabric.

## Authentication choices

Interactive customer demos should prefer Microsoft Entra SSO/external browser. Noninteractive execution should use an encrypted, rotated RSA private key or an approved OAuth workload pattern, stored outside the repository. Password authentication is a compatibility option only and must remain in a secret manager, Fabric connection, ignored local environment, or ephemeral process variable.

Fabric automation uses Microsoft Entra tokens obtained through Azure CLI/`DefaultAzureCredential`. No application registration or client secret is required for the local POC flow.

The runtime Fabric connection uses the least-privilege Snowflake role. `ACCOUNTADMIN` is limited to administrator-controlled PrivateLink discovery/authorization and is never assigned to the loader or mirror principal.

## Repository controls

- `.gitignore` excludes local environments, `.env`, Snowflake configuration, keys/certificates, generated data, logs, caches, and infrastructure state.
- `.env.example` contains identifiers/placeholders and explicitly excludes secrets.
- `tools/security_scan.py` scans the working tree and Git history for common key/token/password patterns.
- CI runs tests and both scans with read-only repository permissions.
- Fabric item definitions contain symbolic placeholders until deployment.
- Customer user, role-assignment principal, workspace, item, tenant, subscription, and account identifiers are not published in evidence.
- Snowflake PrivateLink output, private service aliases, endpoint IDs/IPs, DNS zones, and Fabric gateway IDs remain in customer-controlled configuration.

## Existing-resource safety

The setup verifies and reuses an approved existing database and warehouse. It creates only a dedicated schema, six tables, and two POC roles. Cleanup drops only that schema and, when explicitly requested, those roles. It never drops or modifies the customer database or warehouse.

## Fabric serving controls

The Warehouse scripts demonstrate RLS and masking only where the current Fabric Warehouse feature supports them. Bind a temporary customer-approved test identity through a private copy of the template, verify Viewer behavior, then remove that assignment. Workspace administrators can bypass or alter controls; do not present POC policy as a complete production authorization model.

## Synthetic data

All IDs, names, addresses, IP addresses, fingerprints, scores, notes, and events are generated. Documentation and manifests label the data `SYNTHETIC_TEST_DATA`. Production data, real customer records, account numbers, card numbers, credentials, and exported customer metadata are prohibited.
