from formflow.compiler import compile_description
from formflow.fixtures import FIXTURE_DESCRIPTIONS
from formflow.render import HONESTY_BANNER, generate_admin, generate_form, synthetic_submissions
from formflow.workflow import compile_workflow


def test_form_includes_each_generated_field_type_and_required_marker():
    result = compile_description(FIXTURE_DESCRIPTIONS["supplier_onboarding"])
    form = result["form_html"]
    for field in result["parse"]["fields"]:
        assert f'id="{field["name"]}"' in form
        expected_type = {"text": "text", "email": "email", "number": "number", "date": "date", "boolean": "checkbox"}[field["type"]]
        assert f'type="{expected_type}"' in form
        if field["required"]:
            assert f'id="{field["name"]}" name="{field["name"]}" type="{expected_type}" required' in form
    assert "checkValidity()" in form
    assert HONESTY_BANNER in form


def test_form_regeneration_is_byte_identical():
    parsed = compile_description(FIXTURE_DESCRIPTIONS["expense_claim"])["parse"]
    assert generate_form(parsed).encode("utf-8") == generate_form(parsed).encode("utf-8")


def test_admin_shows_synthetic_rows_valid_workflow_states_and_schema():
    result = compile_description(FIXTURE_DESCRIPTIONS["expense_claim"])
    admin = result["admin_html"]
    rows = synthetic_submissions(result["workflow"])
    for row in rows:
        assert row["id"] in admin
        assert row["state"] in result["workflow"]["states"]
        assert f'<code>{row["state"]}</code>' in admin
    assert result["schema"]["table"] in admin
    assert HONESTY_BANNER in admin
    assert "synthetic demo data" in admin


def test_generated_artifacts_all_state_honesty_boundary():
    result = compile_description(FIXTURE_DESCRIPTIONS["leave_request"])
    assert "does not use a language model" in result["honesty"]
    assert "arbitrary English" in result["honesty"]
    assert "not production systems" in result["honesty"]
    assert "synthetic" in result["honesty"]
    assert "nothing is sent" in result["honesty"]
    assert "does not use a language model" in result["schema"]["ddl"]
    assert result["notifications"]["notice"].startswith("Rules only.")
