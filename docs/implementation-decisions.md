# Implementation decisions

| Decision | Choice | Rationale |
|---|---|---|
| Repository | `fabric-snowflake-medallion-poc` | Clear source and platform scope |
| Source scope | One Snowflake database on Azure | Replaces both reference source platforms as requested |
| Business scenario | Retain six banking entities and customer-risk profile | Maximizes reuse and preserves a compelling analytical outcome |
| Snowflake objects | Permanent managed tables with uppercase unquoted identifiers | Stable mirroring path and predictable case behavior |
| Bronze | Fabric Snowflake mirrored database | Avoids a redundant copy |
| Mirror selection | Six explicit tables | Bounds cost and prevents unrelated ingestion |
| Capacity | Reuse an existing capacity; dedicated workspace | Cost-aware isolation without provisioning another capacity |
| Snowflake compute | X-Small, 60-second auto-suspend default | POC-safe starting point |
| Authentication | Interactive SSO by default; external encrypted key pair for automation | Avoids committed long-lived secrets |
| Source loading | CSV generation plus staging-table `MERGE ALL BY NAME` | Deterministic, retry-safe, inspectable |
| Transformation | Reuse Fabric Spark Silver/Gold notebooks | Preserves proven reference logic |
| Deployment | Fabric REST API with runtime symbolic binding | Keeps environment IDs out of source |
| Live state | No deployment claims in initial public repository | Evidence must be measured and sanitized |
| License | MIT | Permissive public/customer reuse |

The primary reference was `regshih/fabric-medallion-multisource-poc` at commit `3db050c8fbd4a4492973dc9e758e14cd87ee59ae`. Reused components were adapted rather than copied blindly; obsolete source provisioning and live evidence were removed.
