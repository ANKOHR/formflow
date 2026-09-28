import json
import sqlite3

import pytest

from formflow.compiler import compile_description, write_compilation
from formflow.errors import FormFlowError
from formflow.fixtures import FIXTURE_DESCRIPTIONS


@pytest.mark.parametrize("name", ["leave_request", "supplier_onboarding", "expense_claim"])
def test_end_to_end_compile_emits_consistent_runnable_system(name, tmp_path):
    result = compile_description(FIXTURE_DESCRIPTIONS[name])
    out = tmp_path / name
    files = write_compilation(result, out)
    assert files == ["admin.html", "form.html", "notifications.json", "parse.json", "schema.sql", "spec.json", "workflow.json"]
    with sqlite3.connect(":memory:") as connection:
        connection.executescript((out / "schema.sql").read_text(encoding="utf-8"))
        table = result["schema"]["table"]
        assert connection.execute("SELECT name FROM sqlite_master WHERE name=?", (table,)).fetchone()[0] == table
    spec = json.loads((out / "spec.json").read_text(encoding="utf-8"))
    assert spec["process"] == result["process"]
    assert spec["schema"]["ddl"] == (out / "schema.sql").read_text(encoding="utf-8")
    assert spec["form_html"] == (out / "form.html").read_text(encoding="utf-8")
    assert spec["admin_html"] == (out / "admin.html").read_text(encoding="utf-8")
    assert json.loads((out / "notifications.json").read_text(encoding="utf-8")) == result["notifications"]


def test_compile_rejects_ambiguous_fixture_and_cycle_fixture():
    for name, error_name in (("ambiguous", "AmbiguousPhraseError"), ("cyclic_approval", "WorkflowCycleError")):
        with pytest.raises(FormFlowError) as caught:
            compile_description(FIXTURE_DESCRIPTIONS[name])
        assert caught.value.code == error_name
