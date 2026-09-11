"""Shared, secret-safe Snowflake connection helpers."""
from __future__ import annotations

import os
import re
from typing import Any

from dotenv import load_dotenv

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,254}$")


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise RuntimeError(f"Set {name} in the process environment or ignored .env file")
    return value


def identifier(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default or "").strip()
    if not value or not IDENTIFIER.fullmatch(value):
        raise RuntimeError(f"{name} must be an unquoted Snowflake identifier")
    return value.upper()


def connection_parameters(role_variable: str = "SNOWFLAKE_ROLE") -> dict[str, Any]:
    """Build connector settings without logging credential material."""
    load_dotenv()
    authenticator = os.getenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser").strip()
    params: dict[str, Any] = {
        "account": required("SNOWFLAKE_ACCOUNT"),
        "user": required("SNOWFLAKE_USER"),
        "authenticator": authenticator,
        "warehouse": identifier("SNOWFLAKE_WAREHOUSE", "FABRIC_POC_WH"),
        "database": identifier("SNOWFLAKE_DATABASE", "FABRIC_SNOWFLAKE_POC"),
        "schema": identifier("SNOWFLAKE_SCHEMA", "BANKING_SOURCE"),
        "session_parameters": {"QUERY_TAG": "fabric-snowflake-medallion-poc"},
        "login_timeout": 30,
        "network_timeout": 120,
    }
    role = os.getenv(role_variable, "").strip()
    if role:
        params["role"] = identifier(role_variable)
    if authenticator.upper() == "SNOWFLAKE_JWT":
        params["private_key_file"] = required("SNOWFLAKE_PRIVATE_KEY_FILE")
        passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "")
        if passphrase:
            params["private_key_file_pwd"] = passphrase
    elif authenticator.lower() == "snowflake":
        params["password"] = required("SNOWFLAKE_PASSWORD")
    return params


def connect(role_variable: str = "SNOWFLAKE_ROLE"):
    import snowflake.connector

    return snowflake.connector.connect(**connection_parameters(role_variable))
