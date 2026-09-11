data "azurerm_resource_group" "target" {
  name = var.resource_group_name
}

resource "azurerm_private_endpoint" "snowflake" {
  name                = var.private_endpoint_name
  location            = data.azurerm_resource_group.target.location
  resource_group_name = data.azurerm_resource_group.target.name
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                              = "${var.private_endpoint_name}-connection"
    private_connection_resource_alias = var.snowflake_private_link_service_alias
    is_manual_connection              = true
    request_message                   = "Private Snowflake access for Microsoft Fabric"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_subnet" "fabric_vnet_gateway" {
  count = var.create_fabric_gateway_subnet ? 1 : 0

  name                 = var.fabric_gateway_subnet_name
  resource_group_name  = data.azurerm_resource_group.target.name
  virtual_network_name = var.virtual_network_name
  address_prefixes     = var.fabric_gateway_subnet_address_prefixes

  delegation {
    name = "fabric-vnet-data-gateway"

    service_delegation {
      name    = "Microsoft.PowerPlatform/vnetaccesslinks"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = length(var.fabric_gateway_subnet_address_prefixes) > 0
      error_message = "fabric_gateway_subnet_address_prefixes must contain at least one CIDR when create_fabric_gateway_subnet is true."
    }
  }
}
