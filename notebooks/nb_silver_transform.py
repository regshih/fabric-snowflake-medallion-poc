# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# PARAMETERS CELL ********************

pipeline_run_id = "manual"
run_date = ""
workspace_id = ""
snowflake_source_lakehouse_id = ""
snowflake_source_schema = ""
silver_lakehouse_id = ""
audit_lakehouse_id = ""

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from datetime import datetime, timezone
from delta.tables import DeltaTable
from pyspark.sql import Row
from pyspark.sql import functions as F
from pyspark.sql.types import LongType, StringType, StructField, StructType, TimestampType
from pyspark.sql.window import Window

STAGE = "silver_transform"
_started = datetime.now(timezone.utc)


def require_parameters():
    required = ["workspace_id", "snowflake_source_lakehouse_id", "snowflake_source_schema",
                "silver_lakehouse_id", "audit_lakehouse_id"]
    missing = [name for name in required if not str(globals()[name]).strip()]
    if missing:
        raise ValueError("Missing deployment parameters: " + ", ".join(missing))


require_parameters()


def path(lakehouse_id, table_name):
    return f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com/{lakehouse_id}/Tables/{table_name}"


def read_source(lakehouse_id, table_name, schema_name=""):
    object_name = f"{schema_name}/{table_name}" if schema_name else table_name
    return spark.read.format("delta").load(path(lakehouse_id, object_name))


def latest(df, keys, order_column):
    window = Window.partitionBy(*keys).orderBy(F.col(order_column).desc_nulls_last())
    return df.withColumn("_row_number", F.row_number().over(window)).filter("_row_number = 1").drop("_row_number")


def json_text(df, column):
    field = next(item for item in df.schema.fields if item.name == column)
    return F.col(column) if field.dataType.typeName() == "string" else F.to_json(F.col(column))


def with_lineage(df, source_system):
    return (df.withColumn("source_system", F.lit(source_system))
              .withColumn("pipeline_run_id", F.lit(pipeline_run_id))
              .withColumn("run_date", F.to_date(F.lit(run_date)) if run_date else F.current_date())
              .withColumn("silver_loaded_at", F.current_timestamp()))


def replace_table(df, table_name):
    # A deterministic full refresh is appropriate for this POC and makes retries idempotent.
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(path(silver_lakehouse_id, table_name))


def split_quality(df, valid_condition, table_name, reason):
    # coalesce is essential: Spark's three-valued logic would otherwise put
    # rows whose rule evaluates to NULL in neither the valid nor invalid set.
    is_valid = F.coalesce(valid_condition, F.lit(False))
    invalid = with_lineage(df.filter(~is_valid).withColumn("quarantine_reason", F.lit(reason)), "quality")
    replace_table(invalid, "quarantine_" + table_name)
    return df.filter(is_valid), invalid.count()


def write_audit(status, rows_read, rows_written, error_message=None):
    ended = datetime.now(timezone.utc)
    schema = StructType([
        StructField("pipeline_run_id", StringType(), False), StructField("run_date", StringType(), True),
        StructField("stage", StringType(), False), StructField("status", StringType(), False),
        StructField("rows_read", LongType(), False), StructField("rows_written", LongType(), False),
        StructField("started_at", TimestampType(), False), StructField("ended_at", TimestampType(), False),
        StructField("duration_seconds", LongType(), False), StructField("error_message", StringType(), True),
    ])
    incoming = spark.createDataFrame([Row(
        pipeline_run_id=pipeline_run_id, run_date=run_date or None, stage=STAGE, status=status,
        rows_read=int(rows_read), rows_written=int(rows_written), started_at=_started, ended_at=ended,
        duration_seconds=int((ended - _started).total_seconds()), error_message=error_message)], schema)
    audit_path = path(audit_lakehouse_id, "control_pipeline_run_log")
    if DeltaTable.isDeltaTable(spark, audit_path):
        (DeltaTable.forPath(spark, audit_path).alias("t").merge(
            incoming.alias("s"), "t.pipeline_run_id=s.pipeline_run_id AND t.stage=s.stage")
         .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute())
    else:
        incoming.write.format("delta").mode("overwrite").save(audit_path)


rows_read = rows_written = 0
try:
    raw_txn = read_source(snowflake_source_lakehouse_id, "TRANSACTIONS", snowflake_source_schema)
    raw_risk = read_source(snowflake_source_lakehouse_id, "TRANSACTION_RISK", snowflake_source_schema)
    raw_merchants = read_source(snowflake_source_lakehouse_id, "MERCHANTS", snowflake_source_schema)
    raw_sessions = read_source(snowflake_source_lakehouse_id, "DIGITAL_SESSIONS", snowflake_source_schema)
    raw_devices = read_source(snowflake_source_lakehouse_id, "DEVICES", snowflake_source_schema)
    raw_alerts = read_source(snowflake_source_lakehouse_id, "FRAUD_ALERTS", snowflake_source_schema)
    rows_read = sum(df.count() for df in [raw_txn, raw_risk, raw_merchants, raw_sessions, raw_devices, raw_alerts])

    transactions = latest(raw_txn, ["TRANSACTION_ID"], "TRANSACTION_TIMESTAMP").select(
        F.trim("TRANSACTION_ID").alias("TransactionID"), F.trim("ACCOUNT_ID").alias("AccountID"),
        F.trim("CUSTOMER_ID").alias("CustomerID"), F.trim("MERCHANT_ID").alias("MerchantID"),
        F.trim("DEVICE_ID").alias("DeviceID"), F.to_timestamp("TRANSACTION_TIMESTAMP").alias("TransactionTimestamp"),
        F.col("AMOUNT").cast("decimal(18,2)").alias("Amount"), F.upper("CURRENCY").alias("Currency"),
        F.col("TRANSACTION_TYPE").alias("TransactionType"), F.col("MERCHANT_CATEGORY").alias("MerchantCategory"),
        F.col("CHANNEL").alias("Channel"), F.col("COUNTRY").alias("Country"),
        F.col("CARD_PRESENT").cast("boolean").alias("CardPresent"),
        F.col("TRANSACTION_STATUS").alias("TransactionStatus"), F.col("SOURCE_BATCH").alias("SourceBatch"))
    txn_ok = (F.col("TransactionID").rlike(r"^TXN-[0-9]{9}$") & F.col("CustomerID").isNotNull() &
              F.col("TransactionTimestamp").isNotNull() & (F.col("Amount") >= 0))
    transactions, _ = split_quality(transactions, txn_ok, "transactions", "invalid key, timestamp, or amount")

    risk = latest(raw_risk, ["TRANSACTION_ID"], "SCORED_TIMESTAMP").select(
        F.trim("TRANSACTION_ID").alias("TransactionID"), F.col("RISK_SCORE").cast("double").alias("RiskScore"),
        F.col("RISK_BAND").alias("RiskBand"), F.col("MODEL_VERSION").alias("ModelVersion"),
        F.to_timestamp("SCORED_TIMESTAMP").alias("ScoredTimestamp"),
        F.col("RISK_FACTORS_JSON").cast("string").alias("RiskFactors"), F.col("SOURCE_BATCH").alias("SourceBatch"))
    valid_txn_ids = transactions.select("TransactionID").withColumn("_transaction_exists", F.lit(True))
    risk = risk.join(valid_txn_ids, "TransactionID", "left")
    risk, _ = split_quality(risk, F.col("RiskScore").between(0, 100) & F.col("_transaction_exists"),
                            "transaction_risk", "risk score outside 0..100 or orphan TransactionID")
    risk = risk.drop("_transaction_exists")

    merchants = latest(raw_merchants, ["MERCHANT_ID"], "SOURCE_BATCH").select(
        F.col("MERCHANT_ID").alias("MerchantID"), F.col("MERCHANT_NAME").alias("MerchantName"),
        F.col("MERCHANT_CATEGORY").alias("MerchantCategory"), F.col("CITY").alias("City"),
        F.col("STATE").alias("State"), F.col("COUNTRY").alias("Country"),
        F.col("MERCHANT_RISK_CATEGORY").alias("MerchantRiskCategory"), F.col("SOURCE_BATCH").alias("SourceBatch"))
    merchants, _ = split_quality(merchants, F.col("MerchantID").isNotNull() & F.col("MerchantName").isNotNull(),
                                 "merchants", "missing merchant business key or name")

    sessions = latest(raw_sessions, ["SESSION_ID"], "LOGIN_TIMESTAMP").select(
        F.col("SESSION_ID").alias("SessionID"), F.col("CUSTOMER_ID").alias("CustomerID"),
        F.col("DEVICE_ID").alias("DeviceID"), F.col("DEVICE_TYPE").alias("DeviceType"),
        F.col("OPERATING_SYSTEM").alias("OperatingSystem"),
        F.to_timestamp("LOGIN_TIMESTAMP").alias("LoginTimestamp"), F.to_timestamp("LOGOUT_TIMESTAMP").alias("LogoutTimestamp"),
        F.col("AUTHENTICATION_METHOD").alias("AuthenticationMethod"),
        F.col("MFA_USED").cast("boolean").alias("MfaUsed"), F.col("FAILED_ATTEMPTS").cast("int").alias("FailedAttempts"),
        F.col("COUNTRY").alias("Country"), F.col("STATE").alias("State"), F.col("CITY").alias("City"),
        F.col("SESSION_RISK_SCORE").cast("double").alias("SessionRiskScore"),
        F.col("ACTIVITIES_JSON").cast("string").alias("ActivitiesJSON"))
    sessions, _ = split_quality(sessions, F.col("SessionID").isNotNull() & F.col("CustomerID").isNotNull() &
                                F.col("DeviceID").isNotNull() & F.col("LoginTimestamp").isNotNull(),
                                "sessions", "missing key, device, customer, or valid login timestamp")

    devices = latest(raw_devices, ["DEVICE_ID"], "LAST_SEEN").select(
        F.col("DEVICE_ID").alias("DeviceID"), F.col("CUSTOMER_ID").alias("CustomerID"),
        F.to_timestamp("FIRST_SEEN").alias("FirstSeen"), F.to_timestamp("LAST_SEEN").alias("LastSeen"),
        F.col("TRUSTED").cast("boolean").alias("Trusted"), F.col("DEVICE_FINGERPRINT").alias("DeviceFingerprint"),
        F.col("OPERATING_SYSTEM").alias("OperatingSystem"),
        F.col("OPERATING_SYSTEM_VERSION").alias("OperatingSystemVersion"), F.col("APP_VERSION").alias("AppVersion"),
        F.col("RISK_SIGNALS_JSON").cast("string").alias("RiskSignalsJSON"))
    devices, _ = split_quality(devices, F.col("DeviceID").isNotNull() & F.col("CustomerID").isNotNull(),
                               "devices", "missing device or customer business key")

    alerts = latest(raw_alerts, ["ALERT_ID"], "CREATED_TIMESTAMP").select(
        F.col("ALERT_ID").alias("AlertID"), F.col("CUSTOMER_ID").alias("CustomerID"),
        F.col("TRANSACTION_ID").alias("TransactionID"), F.to_timestamp("CREATED_TIMESTAMP").alias("CreatedTimestamp"),
        F.col("ALERT_TYPE").alias("AlertType"), F.lower("SEVERITY").alias("Severity"),
        F.lower("STATUS").alias("Status"), F.col("SIGNALS_JSON").cast("string").alias("SignalsJSON"),
        F.col("INVESTIGATOR_NOTES_JSON").cast("string").alias("InvestigatorNotesJSON"))
    alerts, _ = split_quality(alerts, F.col("AlertID").isNotNull() & F.col("CustomerID").isNotNull() &
                              F.col("CreatedTimestamp").isNotNull() & F.col("Severity").isin("low", "medium", "high", "critical"),
                              "fraud_alerts", "missing key/timestamp or invalid severity")

    outputs = {"transactions": transactions, "transaction_risk": risk, "merchants": merchants,
               "sessions": sessions, "devices": devices, "fraud_alerts": alerts}
    for name, df in outputs.items():
        enriched = with_lineage(df, "snowflake")
        replace_table(enriched, name)
        rows_written += enriched.count()
    write_audit("Succeeded", rows_read, rows_written)
except Exception as exc:
    write_audit("Failed", rows_read, rows_written, str(exc)[:2000])
    raise

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
