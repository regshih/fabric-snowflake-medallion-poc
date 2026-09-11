terraform {
  required_version = ">= 1.8.0"

  # Backend values are intentionally supplied from ignored backend.hcl.
  # This prevents accidental use of local state for Private Link inventory.
  backend "azurerm" {}

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.4"
    }
  }
}

provider "azurerm" {
  resource_provider_registrations = "none"

  features {
    enhanced_validation {
      locations          = true
      resource_providers = true
      preflight_enabled  = true
    }
  }

  subscription_id = var.subscription_id
}
