import json

import pytest

from formflow.compiler import canonical_json
from formflow.errors import AmbiguousPhraseError, UnsupportedPhraseError
from formflow.fixtures import FIXTURE_DESCRIPTIONS
from formflow.parser import parse_description


@pytest.mark.parametrize("name", ["leave_request", "supplier_onboarding", "expense_claim", "cyclic_approval"])
def test_fixtures_parse_to_expected_trees(name, fixture_dir):
    folder = fixture_dir / name
    result = parse_description((folder / "description.txt").read_text(encoding="utf-8"))
    assert canonical_json(result) == (folder / "expected_parse.json").read_text(encoding="utf-8")


def test_ambiguous_fixture_has_named_error_and_offending_sentence(fixture_dir):
    from formflow.errors import FormFlowError

    folder = fixture_dir / "ambiguous"
    with pytest.raises(AmbiguousPhraseError) as caught:
        parse_description((folder / "description.txt").read_text(encoding="utf-8"))
    expected = json.loads((folder / "expected_error.json").read_text(encoding="utf-8"))
    assert caught.value.as_dict() == expected
    assert expected["line"] == 4
    assert expected["sentence"] == "Managers or finance might approve high value claims"


def test_unsupported_phrase_names_error_and_points_to_sentence():
    description = "Create an intake form called Test.\nInclude a required field named amount with type number.\nApprove it quickly."
    with pytest.raises(UnsupportedPhraseError) as caught:
        parse_description(description)
    assert caught.value.line == 3
    assert caught.value.sentence == "Approve it quickly"


def test_same_description_has_byte_identical_parse_tree():
    description = FIXTURE_DESCRIPTIONS["expense_claim"]
    first = canonical_json(parse_description(description)).encode("utf-8")
    second = canonical_json(parse_description(description)).encode("utf-8")
    assert first == second


def test_validation_of_unknown_field_is_rejected():
    from formflow.errors import UnknownFieldError

    text = "Create an intake form called Test.\nInclude a required field named amount with type number.\nThe total must be at least 0."
    with pytest.raises(UnknownFieldError) as caught:
        parse_description(text)
    assert caught.value.line == 3


def test_threshold_routing_requires_a_declared_number_field():
    from formflow.errors import InvalidProcessError

    text = "Create an intake form called Test.\nInclude a required field named amount with type text.\nSelf-approve claims under 100."
    with pytest.raises(InvalidProcessError) as caught:
        parse_description(text)
    assert caught.value.line == 3
