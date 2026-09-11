terraform {
  required_version = ">= 1.6.0"

  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 2.20.0"
    }
  }
}

provider "snowflake" {
  organization_name = var.bootstrap_organization_name
  account_name      = var.bootstrap_account_name
  user              = var.bootstrap_user
  role              = "ORGADMIN"
  authenticator     = var.bootstrap_authenticator
}

resource "snowflake_account" "poc" {
  name                 = var.poc_account_name
  admin_name           = var.poc_admin_name
  admin_rsa_public_key = var.poc_admin_rsa_public_key
  admin_user_type      = "PERSON"
  first_name           = var.poc_admin_first_name
  last_name            = var.poc_admin_last_name
  email                = var.poc_admin_email
  edition              = "STANDARD"
  region_group         = "PUBLIC"
  region               = "AZURE_WESTUS2"
  comment              = "Azure-hosted Snowflake account for the Microsoft Fabric medallion POC"
  grace_period_in_days = var.account_drop_grace_period_days
  is_org_admin         = false

  lifecycle {
    prevent_destroy = true
  }
}

