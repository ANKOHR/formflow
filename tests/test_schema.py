import sqlite3

import pytest

from formflow.compiler import compile_description
from formflow.fixtures import FIXTURE_DESCRIPTIONS


@pytest.mark.parametrize("name", ["leave_request", "supplier_onboarding", "expense_claim"])
def test_generated_ddl_applies_and_matches_columns(name):
    result = compile_description(FIXTURE_DESCRIPTIONS[name])
    with sqlite3.connect(":memory:") as connection:
        connection.executescript(result["schema"]["ddl"])
        info = connection.execute(f"PRAGMA table_info({result['schema']['table']})").fetchall()
        names = [row[1] for row in info]
        assert names == [column["name"] for column in result["schema"]["columns"]]
        assert info[0][5] == 1
        assert info[1][3] == 1
        ddl_sql = connection.execute("SELECT sql FROM sqlite_master WHERE type='table'").fetchone()[0]
        assert "CHECK" in ddl_sql


def test_schema_required_validation_checks_enforce_data_rules():
    result = compile_description(FIXTURE_DESCRIPTIONS["expense_claim"])
    with sqlite3.connect(":memory:") as connection:
        connection.executescript(result["schema"]["ddl"])
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO expense_claim (employee, amount) VALUES ('A', -1)")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO expense_claim (employee, amount) VALUES ('A', NULL)")
        connection.execute("INSERT INTO expense_claim (employee, amount) VALUES ('A', 100)")


def test_optional_fields_are_nullable_and_date_field_has_check():
    leave = compile_description(FIXTURE_DESCRIPTIONS["leave_request"])
    with sqlite3.connect(":memory:") as connection:
        connection.executescript(leave["schema"]["ddl"])
        info = {row[1]: row for row in connection.execute("PRAGMA table_info(leave_request)")}
        assert info["reason"][3] == 0
        assert info["employee"][3] == 1
        assert "date(start_date)" in connection.execute("SELECT sql FROM sqlite_master WHERE name='leave_request'").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO leave_request (employee, start_date, end_date) VALUES ('A', '2024-02-31', '2024-03-01')")
