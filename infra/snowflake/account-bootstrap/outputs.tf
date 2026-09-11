output "account_name" {
  description = "Created Snowflake POC account name."
  value       = snowflake_account.poc.name
}

output "cloud_region" {
  description = "Canonical Snowflake cloud region used by the account."
  value       = "AZURE_WESTUS2"
}

