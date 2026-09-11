import csv

from generators.generate_snowflake_data import generate
from validation.validate_snowflake import validate_files


def test_generator_is_deterministic_and_referentially_valid(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    kwargs = dict(transactions=120, customers=20, merchants=12, devices=30, sessions=40, alerts=9, seed=7)
    first_manifests = generate(first, **kwargs)
    second_manifests = generate(second, **kwargs)
    assert first_manifests == second_manifests
    assert (first / "initial" / "TRANSACTIONS.csv").read_bytes() == (second / "initial" / "TRANSACTIONS.csv").read_bytes()
    result = validate_files(first / "initial")
    assert result["failures"] == []
    assert result["counts"]["TRANSACTIONS"] == 120
    assert result["counts"]["DIGITAL_SESSIONS"] == 40


def test_incremental_batch_contains_insert_and_update_scenarios(tmp_path):
    generate(tmp_path, transactions=25, customers=5, merchants=4, devices=8, sessions=10, alerts=2, seed=9)
    result = validate_files(tmp_path / "incremental")
    assert result["failures"] == []
    with (tmp_path / "incremental" / "DEVICES.csv").open(newline="", encoding="utf-8") as handle:
        device = next(csv.DictReader(handle))
    assert device["DEVICE_ID"] == "DEVICE-000001"
    assert device["TRUSTED"] == "False"
