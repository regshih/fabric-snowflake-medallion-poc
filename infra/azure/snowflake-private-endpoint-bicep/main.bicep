targetScope = 'resourceGroup'

@description('Azure region for the private endpoint. Defaults to the deployment resource group location.')
param location string = resourceGroup().location

@description('Existing subnet resource ID for the Snowflake private endpoint. Do not use the Fabric gateway subnet.')
@minLength(1)
param privateEndpointSubnetId string

@secure()
@description('The Snowflake privatelink-pls-id alias returned by SYSTEM$GET_PRIVATELINK_CONFIG(), or the full Private Link service resource ID supplied by Snowflake Support.')
@minLength(1)
param snowflakePrivateLinkServiceAliasOrResourceId string

@description('Name for the dedicated Snowflake private endpoint.')
@minLength(2)
@maxLength(64)
param privateEndpointName string = 'pe-snowflake-fabric-poc'

@description('Create a dedicated subnet delegated to Microsoft.PowerPlatform/vnetaccesslinks for a Fabric VNet data gateway.')
param createFabricGatewaySubnet bool = false

@description('Name of the existing VNet in this deployment resource group. Required when createFabricGatewaySubnet is true.')
param virtualNetworkName string = ''

@description('Name of the optional dedicated Fabric VNet data gateway subnet.')
@minLength(1)
@maxLength(80)
param fabricGatewaySubnetName string = 'snet-fabric-vnet-gateway'

@description('Address prefixes for the optional gateway subnet. Supply at least one CIDR when createFabricGatewaySubnet is true.')
param fabricGatewaySubnetAddressPrefixes array = []

@description('Create Azure CanNotDelete locks on resources created by this deployment. Lock creation requires Microsoft.Authorization/locks/write permission.')
param createDeleteLocks bool = true

@description('Customer-approved tags applied to the private endpoint.')
param tags object = {
  workload: 'fabric-snowflake-medallion-poc'
}

resource existingVnet 'Microsoft.Network/virtualNetworks@2024-07-01' existing = if (createFabricGatewaySubnet) {
  name: virtualNetworkName
}

resource fabricGatewaySubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = if (createFabricGatewaySubnet) {
  parent: existingVnet
  name: fabricGatewaySubnetName
  properties: {
    addressPrefixes: fabricGatewaySubnetAddressPrefixes
    delegations: [
      {
        name: 'fabric-vnet-data-gateway'
        properties: {
          serviceName: 'Microsoft.PowerPlatform/vnetaccesslinks'
        }
      }
    ]
  }
}

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: privateEndpointName
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    manualPrivateLinkServiceConnections: [
      {
        name: '${privateEndpointName}-connection'
        properties: {
          privateLinkServiceId: snowflakePrivateLinkServiceAliasOrResourceId
          groupIds: []
          requestMessage: 'Private Snowflake access for Microsoft Fabric'
        }
      }
    ]
  }
}

resource privateEndpointDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (createDeleteLocks) {
  name: 'prevent-delete'
  scope: privateEndpoint
  properties: {
    level: 'CanNotDelete'
    notes: 'Remove only through an approved retirement change for the Fabric Snowflake POC.'
  }
}

resource fabricGatewaySubnetDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (createFabricGatewaySubnet && createDeleteLocks) {
  name: 'prevent-delete'
  scope: fabricGatewaySubnet
  properties: {
    level: 'CanNotDelete'
    notes: 'Remove only through an approved retirement change for the Fabric VNet data gateway subnet.'
  }
}

output privateEndpointId string = privateEndpoint.id
output privateEndpointConnectionName string = '${privateEndpointName}-connection'
output fabricGatewaySubnetId string = createFabricGatewaySubnet ? fabricGatewaySubnet!.id : ''
