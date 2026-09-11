variable "subscription_id" {
  description = "Azure subscription containing the customer-managed virtual network."
  type        = string
}

variable "resource_group_name" {
  description = "Existing resource group for the private endpoint and virtual network."
  type        = string
}

variable "virtual_network_name" {
  description = "Existing VNet that can resolve and route to the Snowflake private endpoint."
  type        = string
}

variable "private_endpoint_subnet_id" {
  description = "Existing subnet resource ID for the Snowflake private endpoint; do not use the Fabric gateway subnet."
  type        = string
}

variable "snowflake_private_link_service_alias" {
  description = "The privatelink-pls-id value returned by Snowflake SYSTEM$GET_PRIVATELINK_CONFIG()."
  type        = string
  sensitive   = true
}

variable "private_endpoint_name" {
  description = "Name for the dedicated Snowflake private endpoint."
  type        = string
  default     = "pe-snowflake-fabric-poc"
}

variable "create_fabric_gateway_subnet" {
  description = "Create a dedicated subnet delegated to Microsoft.PowerPlatform/vnetaccesslinks."
  type        = bool
  default     = false
}

variable "fabric_gateway_subnet_name" {
  description = "Name of the optional dedicated Fabric VNet data gateway subnet."
  type        = string
  default     = "snet-fabric-vnet-gateway"
}

variable "fabric_gateway_subnet_address_prefixes" {
  description = "Address prefixes for the optional gateway subnet. Size for five reserved addresses plus gateway members and growth."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Customer-approved tags applied to the private endpoint."
  type        = map(string)
  default = {
    workload = "fabric-snowflake-medallion-poc"
  }
}
