output "snowflake_private_endpoint_id" {
  description = "Private endpoint resource ID required for Snowflake authorization."
  value       = azurerm_private_endpoint.snowflake.id
}

output "snowflake_private_endpoint_network_interface_ids" {
  description = "Network interface IDs used to discover the assigned private IP for DNS configuration."
  value       = [for interface in azurerm_private_endpoint.snowflake.network_interface : interface.id]
}

output "fabric_gateway_subnet_id" {
  description = "Created gateway subnet ID, or null when the customer supplies an existing delegated subnet."
  value       = try(azurerm_subnet.fabric_vnet_gateway[0].id, null)
}
