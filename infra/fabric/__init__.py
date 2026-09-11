"""Microsoft Fabric deployment automation for the Snowflake medallion POC."""

from .client import FabricApiError, FabricClient

__all__ = ["FabricApiError", "FabricClient"]
