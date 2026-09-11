# Existing enterprise Snowflake private connectivity with Bicep

This resource-group-scoped Bicep deployment is the Azure-native alternative to the sibling [Terraform root](../snowflake-private-endpoint/README.md). It creates only:

- one Azure private endpoint connected manually to Snowflake's Private Link service;
- optionally, one subnet in an existing VNet delegated exclusively to `Microsoft.PowerPlatform/vnetaccesslinks` for a Fabric VNet data gateway; and
- by default, `CanNotDelete` resource locks on the resources it creates.

It does not create a resource group, VNet, Snowflake account, database, warehouse, Fabric gateway, Fabric capacity, or Fabric workspace. Private DNS records are customer-specific and deliberately remain under the customer's DNS change process.

## Prerequisites

- An existing Snowflake account hosted on Microsoft Azure. Azure Private Link requires Snowflake Business Critical Edition or higher; an organization calling its platform "enterprise" does not establish the Snowflake product edition.
- An approved Azure resource group, VNet, private-endpoint subnet, private DNS design, and separate dedicated Fabric gateway subnet.
- Azure permissions to deploy private endpoints and, if enabled, the delegated subnet and delete locks.
- Snowflake `ACCOUNTADMIN` access for PrivateLink discovery and authorization only. Do not use that role for Fabric replication.

## Prepare local parameters

Run `SELECT SYSTEM$GET_PRIVATELINK_CONFIG();` in an approved Snowflake admin session. Treat the full output as private. Copy only the `privatelink-pls-id` value into an ignored local parameter file:

```powershell
Copy-Item main.bicepparam.example main.bicepparam
```

`main.bicepparam` is ignored by Git. Azure supports connecting a private endpoint by resource ID or alias with manual approval. If Azure rejects Snowflake's alias, obtain the full Private Link service resource ID from Snowflake Support, as Snowflake's official procedure directs.

By default, the network team supplies the gateway subnet. Set `createFabricGatewaySubnet = true`, provide the existing VNet name, and supply at least one approved CIDR only when this deployment is authorized to add the dedicated subnet. The private-endpoint subnet and Fabric gateway subnet must be different subnets.

## Validate and deploy

Select the approved subscription without writing its ID to Git, then run:

```powershell
az bicep build --file main.bicep
az deployment group what-if `
  --resource-group <network-resource-group> `
  --template-file main.bicep `
  --parameters main.bicepparam
az deployment group create `
  --name fabric-snowflake-private-link `
  --resource-group <network-resource-group> `
  --template-file main.bicep `
  --parameters main.bicepparam
```

Review `what-if` through the customer's normal change process before deployment. Use incremental deployment mode, which is the CLI default. Do not commit generated ARM JSON, real parameters, deployment output, or customer identifiers.

The default Azure delete locks are stronger than Terraform's local `prevent_destroy` safeguard and require `Microsoft.Authorization/locks/write`. Set `createDeleteLocks = false` only if the customer's control process supplies an equivalent safeguard. Retirement requires a separately approved removal of each lock before resource deletion.

## Complete private connectivity

1. Record the created private endpoint resource ID without committing it.
2. Obtain a narrowly scoped Azure federated token outside Bicep and have the Snowflake administrator call `SYSTEM$AUTHORIZE_PRIVATELINK`. Never put the token in parameters, deployment history, command history, logs, or Git.
3. Configure private DNS so the Snowflake account and OCSP hostnames returned by `SYSTEM$GET_PRIVATELINK_CONFIG()` resolve to the endpoint private IP.
4. Verify firewall rules, DNS, TLS, and the Approved connection state with SnowCD and `SYSTEM$ALLOWLIST_PRIVATELINK()` where available.
5. Register `Microsoft.PowerPlatform`, create the Fabric VNet data gateway on the dedicated delegated subnet, and store its ID only in ignored `.env`.
6. Set `FABRIC_SNOWFLAKE_SERVER` to Snowflake's `privatelink-account-url` hostname and run `python -m infra.fabric.snowflake_connection`.

## Official references

- [Azure Private Link and Snowflake](https://docs.snowflake.com/en/user-guide/privatelink-azure)
- [Azure private endpoint overview](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview)
- [Bicep private endpoint resource](https://learn.microsoft.com/en-us/azure/templates/microsoft.network/2024-07-01/privateendpoints)
- [Bicep subnet resource](https://learn.microsoft.com/en-us/azure/templates/microsoft.network/2024-07-01/virtualnetworks/subnets)
- [Create a Fabric VNet data gateway](https://learn.microsoft.com/en-us/data-integration/vnet/create-data-gateways)
