from formflow.compiler import compile_description
from formflow.fixtures import FIXTURE_DESCRIPTIONS


def test_notification_rules_match_only_fixture_phrases():
    leave = compile_description(FIXTURE_DESCRIPTIONS["leave_request"])["notifications"]["rules"]
    assert leave == [
        {"kind": "notify", "trigger": "a submission is received", "channel": "email", "recipient_role": "requester", "template": "{process_name}: a submission is received."},
        {"kind": "escalate", "trigger": "approval_pending", "channel": "in_app", "recipient_role": "finance", "after_days": 3, "pending_role": "manager", "template": "{process_name}: manager approval is pending."},
    ]
    supplier = compile_description(FIXTURE_DESCRIPTIONS["supplier_onboarding"])["notifications"]["rules"]
    assert supplier == [
        {"kind": "notify", "trigger": "a submission is received", "channel": "in_app", "recipient_role": "finance", "template": "{process_name}: a submission is received."}
    ]
    assert all(rule["recipient_role"] in {"requester", "finance"} for rule in supplier)


def test_fixture_with_no_notify_phrase_invents_no_rules():
    description = "Create an intake form called Plain Request.\nInclude a required field named summary with type text.\nRequire manager approval."
    result = compile_description(description)
    assert result["notifications"]["rules"] == []

