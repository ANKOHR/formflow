import pytest

from formflow.errors import WorkflowCycleError
from formflow.fixtures import FIXTURE_DESCRIPTIONS
from formflow.parser import parse_description
from formflow.workflow import compile_workflow


@pytest.mark.parametrize(
    ("name", "role"),
    [("leave_request", "manager"), ("supplier_onboarding", "finance")],
)
def test_simple_approval_routes_to_declared_role(name, role):
    workflow = compile_workflow(parse_description(FIXTURE_DESCRIPTIONS[name]))
    assert workflow["approver_roles"] == [role]
    assert {"from": "submitted", "to": f"pending_{role}", "on": "submit"} in workflow["transitions"]
    assert {"from": f"pending_{role}", "to": "approved", "on": "approve", "approver_role": role} in workflow["transitions"]
    assert {"from": f"pending_{role}", "to": "rejected", "on": "reject", "approver_role": role} in workflow["transitions"]


def test_expense_threshold_routing_matches_hand_written_expectations():
    workflow = compile_workflow(parse_description(FIXTURE_DESCRIPTIONS["expense_claim"]))
    routes = [t for t in workflow["transitions"] if t["on"] == "route"]
    assert routes == [
        {"from": "submitted", "to": "approved", "on": "route", "approver_role": "requester", "mode": "automatic", "condition": {"field": "amount", "operator": "<", "value": 100.0}},
        {"from": "submitted", "to": "pending_manager", "on": "route", "approver_role": "manager", "mode": "manual", "condition": {"field": "amount", "operator": "between", "minimum": 100.0, "maximum": 1000.0}},
        {"from": "submitted", "to": "pending_finance", "on": "route", "approver_role": "finance", "mode": "manual", "condition": {"field": "amount", "operator": ">", "value": 1000.0}},
    ]
    assert workflow["approver_roles"] == ["manager", "finance"]


def test_cyclic_approval_fixture_is_rejected_with_pointer(fixture_dir):
    from formflow.compiler import compile_description
    from formflow.errors import FormFlowError

    folder = fixture_dir / "cyclic_approval"
    text = (folder / "description.txt").read_text(encoding="utf-8")
    with pytest.raises(WorkflowCycleError) as caught:
        compile_description(text)
    expected = __import__("json").loads((folder / "expected_error.json").read_text(encoding="utf-8"))
    assert caught.value.as_dict() == expected
    assert caught.value.line == 4
