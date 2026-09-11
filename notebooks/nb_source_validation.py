# Fabric notebook source

# METADATA ********************
# META {"kernel_info": {"name": "synapse_pyspark"}}

# PARAMETERS CELL ********************

pipeline_run_id = "manual"
run_date = ""
workspace_id = ""
snowflake_source_lakehouse_id = ""
snowflake_source_schema = ""
audit_lakehouse_id = ""

# METADATA ********************
# META {"language": "python", "language_group": "synapse_pyspark"}

# CELL ********************

from datetime import datetime, timezone
from delta.tables import DeltaTable
from pyspark.sql import Row
from pyspark.sql.types import LongType, StringType, StructField, StructType, TimestampType

STAGE = "source_validation_snowflake"
_started = datetime.now(timezone.utc)


def required(name, value):
    if not str(value).strip():
        raise ValueError(f"Required deployment parameter is empty: {name}")


for _name in ("workspace_id", "snowflake_source_lakehouse_id", "snowflake_source_schema", "audit_lakehouse_id"):
    required(_name, globals()[_name])


def table_path(lakehouse_id, table_name, schema_name=""):
    object_path = f"{schema_name}/{table_name}" if schema_name else table_name
    return f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com/{lakehouse_id}/Tables/{object_path}"


AUDIT_SCHEMA = StructType([
    StructField("pipeline_run_id", StringType(), False), StructField("run_date", StringType(), True),
    StructField("stage", StringType(), False), StructField("status", StringType(), False),
    StructField("rows_read", LongType(), False), StructField("rows_written", LongType(), False),
    StructField("started_at", TimestampType(), False), StructField("ended_at", TimestampType(), False),
    StructField("duration_seconds", LongType(), False), StructField("error_message", StringType(), True),
])


def write_audit(status, rows_read=0, rows_written=0, error_message=None):
    ended = datetime.now(timezone.utc)
    incoming = spark.createDataFrame([Row(
        pipeline_run_id=pipeline_run_id, run_date=run_date or None, stage=STAGE, status=status,
        rows_read=int(rows_read), rows_written=int(rows_written), started_at=_started, ended_at=ended,
        duration_seconds=int((ended - _started).total_seconds()), error_message=error_message,
    )], AUDIT_SCHEMA)
    path = table_path(audit_lakehouse_id, "control_pipeline_run_log")
    if DeltaTable.isDeltaTable(spark, path):
        (DeltaTable.forPath(spark, path).alias("t").merge(
            incoming.alias("s"), "t.pipeline_run_id=s.pipeline_run_id AND t.stage=s.stage")
         .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute())
    else:
        incoming.write.format("delta").mode("overwrite").save(path)


EXPECTED = {
    "TRANSACTIONS": {"TRANSACTION_ID", "CUSTOMER_ID", "ACCOUNT_ID", "MERCHANT_ID", "TRANSACTION_TIMESTAMP", "AMOUNT"},
    "TRANSACTION_RISK": {"TRANSACTION_ID", "RISK_SCORE", "RISK_BAND", "SCORED_TIMESTAMP"},
    "MERCHANTS": {"MERCHANT_ID", "MERCHANT_NAME", "MERCHANT_RISK_CATEGORY"},
    "DIGITAL_SESSIONS": {"SESSION_ID", "CUSTOMER_ID", "DEVICE_ID", "LOGIN_TIMESTAMP", "FAILED_ATTEMPTS"},
    "DEVICES": {"DEVICE_ID", "CUSTOMER_ID", "TRUSTED", "OPERATING_SYSTEM"},
    "FRAUD_ALERTS": {"ALERT_ID", "CUSTOMER_ID", "TRANSACTION_ID", "CREATED_TIMESTAMP", "SEVERITY"},
}

results = []
total_rows = 0
try:
    for object_name, expected_columns in EXPECTED.items():
        try:
            df = spark.read.format("delta").load(table_path(snowflake_source_lakehouse_id, object_name, snowflake_source_schema))
            count = df.count()
            missing = sorted(expected_columns - set(df.columns))
            status = "PASS" if count > 0 and not missing else "FAIL"
            notes = "schema and read succeeded" if status == "PASS" else f"row_count={count}; missing={missing}"
            total_rows += count
        except Exception as exc:
            count, status, notes = 0, "FAIL", f"read failed: {type(exc).__name__}: {str(exc)[:500]}"
        results.append((pipeline_run_id, run_date, "snowflake", object_name, count, "source_read_and_schema", status, notes))

    validation_df = spark.createDataFrame(results, [
        "pipeline_run_id", "run_date", "source", "object", "source_count", "validation_type", "status", "notes",
    ])
    output = table_path(audit_lakehouse_id, "source_validation_results")
    if DeltaTable.isDeltaTable(spark, output):
        (DeltaTable.forPath(spark, output).alias("t").merge(
            validation_df.alias("s"), "t.pipeline_run_id=s.pipeline_run_id AND t.source=s.source AND t.object=s.object")
         .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute())
    else:
        validation_df.write.format("delta").mode("overwrite").save(output)
    failed = validation_df.filter("status = 'FAIL'").count()
    if failed:
        raise RuntimeError(f"Snowflake source validation failed for {failed} object(s)")
    write_audit("Succeeded", total_rows, len(results))
except Exception as exc:
    write_audit("Failed", total_rows, len(results), str(exc)[:2000])
    raise

# METADATA ********************
# META {"language": "python", "language_group": "synapse_pyspark"}
