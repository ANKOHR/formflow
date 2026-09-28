import json
import os
import subprocess
import sys
from pathlib import Path

from formflow.fixtures import FIXTURE_DESCRIPTIONS


ROOT = Path(__file__).resolve().parents[1]


def _run(args, cwd):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run([sys.executable, "-m", "formflow", *map(str, args)], cwd=cwd, env=env, text=True, capture_output=True)


def test_cli_fixtures_compile_validate_and_serve_note(tmp_path):
    fixtures_dir = tmp_path / "generated fixtures"
    result = _run(["fixtures", "--out", fixtures_dir], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "fictional" in result.stdout.lower()
    description = fixtures_dir / "leave_request" / "description.txt"
    artifacts = tmp_path / "artifacts"
    result = _run(["compile", description, "--out", artifacts], tmp_path)
    assert result.returncode == 0, result.stderr
    for name in ("spec.json", "parse.json", "workflow.json", "schema.sql", "form.html", "notifications.json", "admin.html"):
        assert (artifacts / name).is_file()
    result = _run(["validate", description], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "SQLite DDL applied cleanly" in result.stdout
    result = _run(["serve-note", artifacts], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Admin submissions are synthetic" in result.stdout
    assert "does not use a language model" in result.stdout
    assert "nothing is sent" in result.stdout

    records = [json.loads(line) for line in (tmp_path / "ff-audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [record["command"] for record in records] == ["fixtures", "compile", "validate", "serve-note"]
    assert all(len(record["input_hash"]) == 64 and len(record["spec_hash"]) == 64 for record in records)
    assert all(record["timestamp_utc"].endswith("+00:00") for record in records)


def test_cli_rejects_ambiguous_and_cyclic_inputs_with_named_errors(tmp_path):
    for name in ("ambiguous", "cyclic_approval"):
        path = tmp_path / f"{name}.txt"
        path.write_text(FIXTURE_DESCRIPTIONS[name] + "\n", encoding="utf-8")
        result = _run(["compile", path, "--out", tmp_path / f"{name}_out"], tmp_path)
        assert result.returncode == 2
        error = json.loads(result.stderr)
        assert error["error"] == ("AmbiguousPhraseError" if name == "ambiguous" else "WorkflowCycleError")
        assert error["line"] is not None
    records = [json.loads(line) for line in (tmp_path / "ff-audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2


def test_cli_validate_detects_sqlite_schema_constraints(tmp_path):
    path = tmp_path / "expense.txt"
    path.write_text(FIXTURE_DESCRIPTIONS["expense_claim"] + "\n", encoding="utf-8")
    result = _run(["validate", path], tmp_path)
    assert result.returncode == 0
