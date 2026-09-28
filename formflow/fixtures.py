"""Generate fictional, deterministic fixture descriptions and expectations."""

import json
from pathlib import Path

from .compiler import canonical_json, compile_description
from .errors import FormFlowError
from .parser import HONESTY, parse_description

FIXTURE_SEED = 0
_FIXTURE_LABEL = (
    "# FICTIONAL GENERATED FIXTURE. No real person or organization is represented. "
    + HONESTY
)

FIXTURE_DESCRIPTIONS = {
    "leave_request": f"""{_FIXTURE_LABEL}
Create an intake form called Leave Request.
Include a required field named employee with type text.
Include a required field named start date with type date.
Include a required field named end date with type date.
Include an optional field named reason with type text.
Require manager approval.
Notify the requester by email when a submission is received.
Escalate to finance after 3 days if manager approval is pending.
Archive completed submissions after 365 days.""",
    "supplier_onboarding": f"""{_FIXTURE_LABEL}
Create an intake form called Supplier Onboarding.
Include a required field named company with type text.
Include a required field named contact email with type email.
Include a required field named tax id with type text.
Include a required field named documents with type text.
The tax id must contain exactly 9 characters.
Require finance approval.
Notify the finance by in_app when a submission is received.""",
    "expense_claim": f"""{_FIXTURE_LABEL}
Create an intake form called Expense Claim.
Include a required field named employee with type text.
Include a required field named amount with type number.
Include an optional field named reason with type text.
The amount must be at least 0.
Self-approve expense claims under 100.
Require manager approval for expense claims from 100 to 1000.
Require finance approval for expense claims over 1000.
Notify the requester by email when a submission is received.""",
    "ambiguous": f"""{_FIXTURE_LABEL}
Create an intake form called Ambiguous Request.
Include a required field named amount with type number.
Managers or finance might approve high value claims.""",
    "cyclic_approval": f"""{_FIXTURE_LABEL}
Create an intake form called Cyclic Request.
Include a required field named summary with type text.
Require manager approval then finance approval then manager approval.""",
}


def generate_fixtures(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated = []
    for name, description in FIXTURE_DESCRIPTIONS.items():
        folder = out / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "description.txt").write_text(description + "\n", encoding="utf-8", newline="\n")
        metadata = {
            "name": name,
            "generated": True,
            "fictional": True,
            "seed": FIXTURE_SEED,
            "notice": "Fictional generated fixture for compiler review. No real person or organization is represented.",
            "honesty": HONESTY,
        }
        (folder / "fixture.json").write_text(canonical_json(metadata), encoding="utf-8", newline="\n")
        (folder / "README.txt").write_text(
            "FICTIONAL GENERATED FIXTURE\nNo real person or organization is represented.\n"
            + HONESTY
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        if name == "ambiguous":
            try:
                parse_description(description)
            except FormFlowError as error:
                expected = error.as_dict()
            else:
                raise AssertionError("The ambiguous fixture unexpectedly parsed.")
            (folder / "expected_error.json").write_text(canonical_json(expected), encoding="utf-8", newline="\n")
        elif name == "cyclic_approval":
            (folder / "expected_parse.json").write_text(canonical_json(parse_description(description)), encoding="utf-8", newline="\n")
            try:
                compile_description(description)
            except FormFlowError as error:
                expected = error.as_dict()
            else:
                raise AssertionError("The cyclic approval fixture unexpectedly compiled.")
            (folder / "expected_error.json").write_text(canonical_json(expected), encoding="utf-8", newline="\n")
        else:
            parse_tree = parse_description(description)
            spec = compile_description(description)
            (folder / "expected_parse.json").write_text(canonical_json(parse_tree), encoding="utf-8", newline="\n")
            (folder / "expected_spec.json").write_text(canonical_json(spec), encoding="utf-8", newline="\n")
        generated.append(name)
    return generated
