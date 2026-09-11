#!/usr/bin/env python3
"""Generate deterministic synthetic banking CSVs for Snowflake.

Every value is artificial and generated locally. The data intentionally joins
across transactional and digital-behavior tables so Fabric can build a useful
fraud-risk profile from one Snowflake source database.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator

CLASSIFICATION = "SYNTHETIC_TEST_DATA"
BASE_TIME = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
TABLES = (
    "TRANSACTIONS",
    "TRANSACTION_RISK",
    "MERCHANTS",
    "DIGITAL_SESSIONS",
    "DEVICES",
    "FRAUD_ALERTS",
)


def stable_int(namespace: str, ordinal: int, modulus: int) -> int:
    if modulus <= 0:
        raise ValueError("modulus must be positive")
    digest = hashlib.sha256(f"fabric-snowflake-poc:{namespace}:{ordinal}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % modulus


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def customer_id(number: int) -> str:
    return f"CUST-{number:06d}"


def transaction_id(number: int) -> str:
    return f"TXN-{number:09d}"


def device_id(number: int) -> str:
    return f"DEVICE-{number:06d}"


def merchant_id(number: int) -> str:
    return f"MER{number:06d}"


def transaction_rows(count: int, customers: int, merchants: int, devices: int) -> Iterator[dict[str, object]]:
    currencies = ("USD", "USD", "USD", "CAD", "EUR")
    types = ("Purchase", "Purchase", "Refund", "Transfer", "ATM")
    categories = ("Grocery", "Dining", "Travel", "Fuel", "Retail", "Healthcare", "Digital")
    channels = ("Mobile", "Web", "POS", "ATM")
    countries = ("US", "US", "US", "CA", "GB")
    statuses = ("Approved", "Approved", "Approved", "Declined", "Pending")
    for ordinal in range(1, count + 1):
        customer_number = stable_int("customer", ordinal, customers) + 1
        account_number = customer_number * 2 - stable_int("account", ordinal, 2)
        timestamp = BASE_TIME - timedelta(seconds=stable_int("timestamp", ordinal, 2_592_000))
        amount_cents = 100 + stable_int("amount", ordinal, 249_900)
        yield {
            "TRANSACTION_ID": transaction_id(ordinal),
            "ACCOUNT_ID": f"ACCT{account_number:09d}",
            "CUSTOMER_ID": customer_id(customer_number),
            "MERCHANT_ID": merchant_id(stable_int("merchant", ordinal, merchants) + 1),
            "DEVICE_ID": device_id(stable_int("device", ordinal, devices) + 1),
            "TRANSACTION_TIMESTAMP": iso(timestamp),
            "AMOUNT": f"{amount_cents / 100:.2f}",
            "CURRENCY": currencies[stable_int("currency", ordinal, len(currencies))],
            "TRANSACTION_TYPE": types[stable_int("type", ordinal, len(types))],
            "MERCHANT_CATEGORY": categories[stable_int("category", ordinal, len(categories))],
            "CHANNEL": channels[stable_int("channel", ordinal, len(channels))],
            "COUNTRY": countries[stable_int("country", ordinal, len(countries))],
            "CARD_PRESENT": stable_int("card_present", ordinal, 2) == 1,
            "TRANSACTION_STATUS": statuses[stable_int("status", ordinal, len(statuses))],
            "SOURCE_BATCH": "initial",
        }


def risk_rows(count: int) -> Iterator[dict[str, object]]:
    for ordinal in range(1, count + 1):
        score = stable_int("risk", ordinal, 10_001) / 100
        factors: list[str] = []
        if score >= 80:
            factors.extend(("velocity", "merchant_risk"))
        elif score >= 45:
            factors.append("device_novelty")
        yield {
            "TRANSACTION_ID": transaction_id(ordinal),
            "RISK_SCORE": f"{score:.2f}",
            "RISK_BAND": "High" if score >= 80 else "Medium" if score >= 45 else "Low",
            "MODEL_VERSION": "synthetic-risk-v1",
            "SCORED_TIMESTAMP": iso(BASE_TIME + timedelta(seconds=ordinal % 300)),
            "RISK_FACTORS_JSON": json.dumps(factors, separators=(",", ":")),
            "SOURCE_BATCH": "initial",
        }


def merchant_rows(count: int) -> Iterator[dict[str, object]]:
    categories = ("Grocery", "Dining", "Travel", "Fuel", "Retail", "Healthcare", "Digital")
    countries = ("US", "US", "US", "CA", "GB")
    for ordinal in range(1, count + 1):
        risk = stable_int("merchant_risk", ordinal, 10)
        yield {
            "MERCHANT_ID": merchant_id(ordinal),
            "MERCHANT_NAME": f"Synthetic Merchant {ordinal:06d}",
            "MERCHANT_CATEGORY": categories[stable_int("merchant_category", ordinal, len(categories))],
            "CITY": f"Synthetic City {stable_int('city', ordinal, 100) + 1:03d}",
            "STATE": f"S{stable_int('state', ordinal, 50) + 1:02d}",
            "COUNTRY": countries[stable_int("merchant_country", ordinal, len(countries))],
            "MERCHANT_RISK_CATEGORY": "High" if risk == 9 else "Medium" if risk >= 6 else "Low",
            "SOURCE_BATCH": "initial",
        }


def device_rows(count: int, customers: int) -> Iterator[dict[str, object]]:
    systems = (("iOS", "18.3", "Mobile"), ("Android", "15", "Mobile"), ("Windows", "11", "Desktop"))
    for ordinal in range(1, count + 1):
        os_name, os_version, _ = systems[(ordinal - 1) % len(systems)]
        trusted = ordinal % 7 != 0
        yield {
            "DEVICE_ID": device_id(ordinal),
            "CUSTOMER_ID": customer_id(((ordinal - 1) % customers) + 1),
            "FIRST_SEEN": iso(BASE_TIME - timedelta(days=30 + (ordinal * 17) % 700)),
            "LAST_SEEN": iso(BASE_TIME - timedelta(hours=(ordinal * 7) % 240)),
            "TRUSTED": trusted,
            "DEVICE_FINGERPRINT": f"SYNTH-FP-{ordinal:08X}",
            "OPERATING_SYSTEM": os_name,
            "OPERATING_SYSTEM_VERSION": os_version,
            "APP_VERSION": f"6.{ordinal % 8}.{ordinal % 13}",
            "RISK_SIGNALS_JSON": "[]" if trusted else '[{"type":"emulator","score":0.75}]',
            "SOURCE_BATCH": "initial",
        }


def session_rows(count: int, customers: int, devices: int) -> Iterator[dict[str, object]]:
    systems = (("iOS", "Mobile"), ("Android", "Mobile"), ("Windows", "Desktop"))
    methods = ("password+mfa", "passkey", "biometric")
    locations = (("US", "NY", "New York"), ("US", "WA", "Seattle"), ("CA", "ON", "Toronto"))
    for ordinal in range(1, count + 1):
        device_number = ((ordinal * 37 - 1) % devices) + 1
        customer_number = ((device_number - 1) % customers) + 1
        started = BASE_TIME - timedelta(minutes=ordinal * 31)
        failed = 2 if ordinal % 29 == 0 else 1 if ordinal % 11 == 0 else 0
        unusual_geo = ordinal % 43 == 0
        country, state, city = ("GB", "ENG", "London") if unusual_geo else locations[ordinal % len(locations)]
        os_name, device_type = systems[(device_number - 1) % len(systems)]
        trusted = device_number % 7 != 0
        risk = min(100, 8 + failed * 24 + (35 if unusual_geo else 0) + (22 if not trusted else 0))
        yield {
            "SESSION_ID": f"SESSION-{ordinal:09d}",
            "CUSTOMER_ID": customer_id(customer_number),
            "DEVICE_ID": device_id(device_number),
            "DEVICE_TYPE": device_type,
            "OPERATING_SYSTEM": os_name,
            "LOGIN_TIMESTAMP": iso(started),
            "LOGOUT_TIMESTAMP": iso(started + timedelta(minutes=3 + ordinal % 87)),
            "AUTHENTICATION_METHOD": methods[ordinal % len(methods)],
            "MFA_USED": ordinal % 5 != 0,
            "FAILED_ATTEMPTS": failed,
            "COUNTRY": country,
            "STATE": state,
            "CITY": city,
            "SESSION_RISK_SCORE": risk,
            "ACTIVITIES_JSON": '[{"type":"login","successful":true}]',
            "SOURCE_BATCH": "initial",
        }


def alert_rows(count: int, customers: int, transactions: int) -> Iterator[dict[str, object]]:
    severities = ("low", "medium", "high", "critical")
    for ordinal in range(1, count + 1):
        status = "resolved" if ordinal % 4 == 0 else "investigating" if ordinal % 3 == 0 else "open"
        yield {
            "ALERT_ID": f"ALERT-{ordinal:08d}",
            "CUSTOMER_ID": customer_id(((ordinal * 13 - 1) % customers) + 1),
            "TRANSACTION_ID": transaction_id(1 + ((ordinal * 7919) % transactions)),
            "CREATED_TIMESTAMP": iso(BASE_TIME - timedelta(hours=ordinal * 9)),
            "ALERT_TYPE": "accountTakeover" if ordinal % 3 == 0 else "transactionAnomaly",
            "SEVERITY": severities[ordinal % len(severities)],
            "STATUS": status,
            "SIGNALS_JSON": '[{"name":"transactionRisk","score":0.81},{"name":"digitalBehavior","score":0.73}]',
            "INVESTIGATOR_NOTES_JSON": "[]" if status == "open" else '[{"note":"Synthetic POC review"}]',
            "SOURCE_BATCH": "initial",
        }


def incremental_rows() -> dict[str, list[dict[str, object]]]:
    anchor = BASE_TIME + timedelta(days=1)
    new_transaction = next(transaction_rows(1, 250, 300, 375))
    new_transaction.update({
        "TRANSACTION_ID": "TXN-900000001",
        "CUSTOMER_ID": "CUST-000001",
        "ACCOUNT_ID": "ACCT000000001",
        "MERCHANT_ID": "MER000001",
        "DEVICE_ID": "DEVICE-000001",
        "TRANSACTION_TIMESTAMP": iso(anchor),
        "AMOUNT": "9999.00",
        "SOURCE_BATCH": "incremental",
    })
    new_risk = next(risk_rows(1))
    new_risk.update({"TRANSACTION_ID": "TXN-900000001", "RISK_SCORE": "97.50", "RISK_BAND": "High", "SCORED_TIMESTAMP": iso(anchor), "SOURCE_BATCH": "incremental"})
    changed_device = next(device_rows(1, 250))
    changed_device.update({"LAST_SEEN": iso(anchor), "TRUSTED": False, "RISK_SIGNALS_JSON": '[{"type":"impossibleTravel","score":0.94}]', "SOURCE_BATCH": "incremental"})
    new_session = next(session_rows(1, 250, 375))
    new_session.update({"SESSION_ID": "SESSION-900000001", "CUSTOMER_ID": "CUST-000001", "DEVICE_ID": "DEVICE-000001", "LOGIN_TIMESTAMP": iso(anchor), "FAILED_ATTEMPTS": 3, "COUNTRY": "GB", "SESSION_RISK_SCORE": 93, "SOURCE_BATCH": "incremental"})
    new_alert = next(alert_rows(1, 250, 10_000))
    new_alert.update({"ALERT_ID": "ALERT-90000001", "CUSTOMER_ID": "CUST-000001", "TRANSACTION_ID": "TXN-900000001", "CREATED_TIMESTAMP": iso(anchor), "SEVERITY": "critical", "STATUS": "open", "SOURCE_BATCH": "incremental"})
    return {
        "TRANSACTIONS": [new_transaction],
        "TRANSACTION_RISK": [new_risk],
        "DIGITAL_SESSIONS": [new_session],
        "DEVICES": [changed_device],
        "FRAUD_ALERTS": [new_alert],
    }


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> int:
    materialized = list(rows)
    if not materialized:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(materialized[0]))
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)


def write_batch(root: Path, name: str, tables: dict[str, Iterable[dict[str, object]]], parameters: dict[str, int]) -> dict[str, object]:
    target = root / name
    counts = {table: write_csv(target / f"{table}.csv", rows) for table, rows in tables.items()}
    manifest = {"classification": CLASSIFICATION, "batch": name, "parameters": parameters, "counts": counts}
    target.mkdir(parents=True, exist_ok=True)
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def generate(root: Path, *, transactions: int, customers: int, merchants: int, devices: int, sessions: int, alerts: int, seed: int) -> list[dict[str, object]]:
    if min(transactions, customers, merchants, devices, sessions) <= 0 or alerts < 0:
        raise ValueError("counts must be positive; alerts can be zero")
    random.seed(seed)  # Seed is recorded and reserved for future generator extensions.
    parameters = {"transactions": transactions, "customers": customers, "merchants": merchants, "devices": devices, "sessions": sessions, "alerts": alerts, "seed": seed}
    initial = {
        "TRANSACTIONS": transaction_rows(transactions, customers, merchants, devices),
        "TRANSACTION_RISK": risk_rows(transactions),
        "MERCHANTS": merchant_rows(merchants),
        "DIGITAL_SESSIONS": session_rows(sessions, customers, devices),
        "DEVICES": device_rows(devices, customers),
        "FRAUD_ALERTS": alert_rows(alerts, customers, transactions),
    }
    return [write_batch(root, "initial", initial, parameters), write_batch(root, "incremental", incremental_rows(), parameters)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("data/snowflake"))
    parser.add_argument("--transactions", type=int, default=10_000)
    parser.add_argument("--customers", type=int, default=250)
    parser.add_argument("--merchants", type=int, default=300)
    parser.add_argument("--devices", type=int, default=375)
    parser.add_argument("--sessions", type=int, default=1_500)
    parser.add_argument("--alerts", type=int, default=150)
    parser.add_argument("--seed", type=int, default=20260910)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(generate(args.out_dir, transactions=args.transactions, customers=args.customers, merchants=args.merchants, devices=args.devices, sessions=args.sessions, alerts=args.alerts, seed=args.seed), indent=2))
