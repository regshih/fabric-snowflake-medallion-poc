variable "bootstrap_organization_name" {
  description = "Existing Snowflake organization used to create the POC account."
  type        = string
}

variable "bootstrap_account_name" {
  description = "Existing Snowflake organization account used by the ORGADMIN provider session."
  type        = string
}

variable "bootstrap_user" {
  description = "Existing Snowflake user that can assume ORGADMIN."
  type        = string
}

variable "bootstrap_authenticator" {
  description = "Authentication used for the existing organization account."
  type        = string
  default     = "EXTERNALBROWSER"

  validation {
    condition     = contains(["EXTERNALBROWSER", "SNOWFLAKE_JWT", "OAUTH", "WORKLOAD_IDENTITY"], upper(var.bootstrap_authenticator))
    error_message = "Use EXTERNALBROWSER, SNOWFLAKE_JWT, OAUTH, or WORKLOAD_IDENTITY. Passwords must not be placed in tfvars."
  }
}

variable "poc_account_name" {
  description = "Globally unique account name within the existing Snowflake organization."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9_]{2,30}$", var.poc_account_name))
    error_message = "Use 3-31 letters, numbers, or underscores, beginning with a letter."
  }
}

variable "poc_admin_name" {
  description = "Initial administrator username in the new POC account."
  type        = string
}

variable "poc_admin_first_name" {
  description = "Initial administrator first name. Stored in encrypted Terraform state."
  type        = string
  sensitive   = true
}

variable "poc_admin_last_name" {
  description = "Initial administrator last name. Stored in encrypted Terraform state."
  type        = string
  sensitive   = true
}

variable "poc_admin_email" {
  description = "Initial administrator email. Stored in encrypted Terraform state."
  type        = string
  sensitive   = true
}

variable "poc_admin_rsa_public_key" {
  description = "PKCS#8 RSA public key body for the initial administrator; never supply the private key."
  type        = string
}

variable "account_drop_grace_period_days" {
  description = "Snowflake recovery grace period if account deletion is deliberately enabled later."
  type        = number
  default     = 7

  validation {
    condition     = var.account_drop_grace_period_days >= 3 && var.account_drop_grace_period_days <= 90
    error_message = "Use a grace period from 3 through 90 days."
  }
}

