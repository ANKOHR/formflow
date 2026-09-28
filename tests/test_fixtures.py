import hashlib
import json
import tempfile
from pathlib import Path

from formflow.compiler import canonical_json, compile_description
from formflow.fixtures import FIXTURE_DESCRIPTIONS, generate_fixtures
from formflow.parser import parse_description


def _tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_fixtures_are_deterministic_and_have_expected_outputs(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert generate_fixtures(first) == list(FIXTURE_DESCRIPTIONS)
    assert generate_fixtures(second) == list(FIXTURE_DESCRIPTIONS)
    assert _tree_digest(first) == _tree_digest(second)
    for name in ("leave_request", "supplier_onboarding", "expense_claim"):
        folder = first / name
        assert (folder / "description.txt").is_file()
        assert (folder / "expected_parse.json").is_file()
        assert (folder / "expected_spec.json").is_file()
        description = (folder / "description.txt").read_text(encoding="utf-8")
        assert canonical_json(parse_description(description)) == (folder / "expected_parse.json").read_text(encoding="utf-8")
        assert canonical_json(compile_description(description)) == (folder / "expected_spec.json").read_text(encoding="utf-8")
    assert (first / "ambiguous" / "expected_error.json").is_file()
    assert (first / "cyclic_approval" / "expected_error.json").is_file()


def test_fixture_descriptions_are_fictional_and_labelled(descriptions):
    assert len(descriptions) == 5
    assert all(description.startswith("# FICTIONAL GENERATED FIXTURE.") for description in descriptions.values())
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        generate_fixtures(root)
        for name in descriptions:
            metadata = json.loads((root / name / "fixture.json").read_text(encoding="utf-8"))
            label = (root / name / "README.txt").read_text(encoding="utf-8")
            assert metadata["generated"] is True
            assert metadata["fictional"] is True
            assert metadata["seed"] == 0
            assert "does not use a language model" in metadata["honesty"]
            assert "FICTIONAL GENERATED FIXTURE" in label
            assert "nothing is sent" in label
