"""Parser for FormFlow's deliberately small, line-based phrase grammar."""

import re

from .errors import (
    AmbiguousPhraseError,
    DuplicateFieldError,
    HONESTY,
    InvalidProcessError,
    MissingFormError,
    UnknownFieldError,
    UnsupportedPhraseError,
)

FIELD_TYPES = {"text", "email", "number", "date", "boolean"}
ROLE = r"[a-z][a-z0-9_-]*"
FIELD_NAME = r"[a-z][a-z0-9_ ]*"


def slugify(value):
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not value:
        raise InvalidProcessError("Process name must contain letters or digits.")
    if value[0].isdigit():
        value = "process_" + value
    return value


def normalize_field_name(value):
    return slugify(value)


def _clean_sentence(line):
    return line.strip().rstrip(".").strip()


def _role_chain(value):
    parts = re.split(r"\s+(?:then|followed by)\s+", value.strip(), flags=re.IGNORECASE)
    roles = []
    for part in parts:
        match = re.fullmatch(rf"({ROLE})\s+approval", part.strip(), flags=re.IGNORECASE)
        if not match:
            return None
        roles.append(match.group(1).lower())
    return roles or None


def parse_description(description):
    """Parse one grammar phrase per non-empty line into a stable parse tree."""
    process = None
    fields = []
    approvals = []
    notifications = []
    actions = []
    validations = []
    phrases = []
    seen_fields = set()

    for line_number, raw in enumerate(description.splitlines(), start=1):
        sentence = _clean_sentence(raw)
        if not sentence:
            continue
        if sentence.startswith("#"):
            continue
        if re.search(r"\b(or|might|maybe|either|perhaps)\b", sentence, re.IGNORECASE):
            raise AmbiguousPhraseError(
                "This phrase has more than one possible interpretation in the declared grammar.",
                line=line_number,
                sentence=sentence,
            )

        form_match = re.fullmatch(r"Create an intake form called (.+)", sentence, re.IGNORECASE)
        if form_match:
            if process is not None:
                raise AmbiguousPhraseError("Only one intake form is supported per description.", line=line_number, sentence=sentence)
            name = form_match.group(1).strip()
            process = {"name": name, "slug": slugify(name)}
            phrases.append({"line": line_number, "kind": "process", "name": name})
            continue

        field_match = re.fullmatch(
            rf"Include (?:a|an) (required|optional) field named ({FIELD_NAME}) with type (text|email|number|date|boolean)",
            sentence,
            re.IGNORECASE,
        )
        if field_match:
            required, source_name, field_type = field_match.groups()
            field_name = normalize_field_name(source_name)
            if field_name in seen_fields:
                raise DuplicateFieldError(f"Field '{field_name}' is declared more than once.", line=line_number, sentence=sentence)
            seen_fields.add(field_name)
            field = {
                "name": field_name,
                "label": source_name.replace("_", " ").strip().title(),
                "type": field_type.lower(),
                "required": required.lower() == "required",
                "validation": [],
                "source_line": line_number,
            }
            fields.append(field)
            phrases.append({"line": line_number, "kind": "field", "field": field_name, "type": field["type"], "required": field["required"]})
            continue

        minimum = re.fullmatch(rf"The ({FIELD_NAME}) must be at least (-?\d+(?:\.\d+)?)", sentence, re.IGNORECASE)
        if minimum:
            item = {"field": normalize_field_name(minimum.group(1)), "rule": "minimum", "value": float(minimum.group(2)), "line": line_number, "sentence": sentence}
            validations.append(item)
            phrases.append({"line": line_number, "kind": "validation", "field": item["field"], "rule": item["rule"], "value": item["value"]})
            continue
        maximum = re.fullmatch(rf"The ({FIELD_NAME}) must be at most (-?\d+(?:\.\d+)?)", sentence, re.IGNORECASE)
        if maximum:
            item = {"field": normalize_field_name(maximum.group(1)), "rule": "maximum", "value": float(maximum.group(2)), "line": line_number, "sentence": sentence}
            validations.append(item)
            phrases.append({"line": line_number, "kind": "validation", "field": item["field"], "rule": item["rule"], "value": item["value"]})
            continue
        exact_length = re.fullmatch(rf"The ({FIELD_NAME}) must contain exactly (\d+) characters", sentence, re.IGNORECASE)
        if exact_length:
            item = {"field": normalize_field_name(exact_length.group(1)), "rule": "length", "value": int(exact_length.group(2)), "line": line_number, "sentence": sentence}
            validations.append(item)
            phrases.append({"line": line_number, "kind": "validation", "field": item["field"], "rule": item["rule"], "value": item["value"]})
            continue

        chain = re.fullmatch(r"Require (.+)", sentence, re.IGNORECASE)
        if chain:
            roles = _role_chain(chain.group(1))
            if roles:
                approvals.append({"kind": "chain", "roles": roles, "line": line_number, "sentence": sentence})
                phrases.append({"line": line_number, "kind": "approval_chain", "roles": roles})
                continue

        self_route = re.fullmatch(r"Self-approve (.+) under (\d+(?:\.\d+)?)", sentence, re.IGNORECASE)
        if self_route:
            subject, threshold = self_route.groups()
            approvals.append({"kind": "threshold", "field": "amount", "operator": "<", "value": float(threshold), "role": "requester", "mode": "automatic", "subject": subject.strip(), "line": line_number, "sentence": sentence})
            phrases.append({"line": line_number, "kind": "threshold_route", "operator": "<", "value": float(threshold), "role": "requester"})
            continue

        threshold_range = re.fullmatch(rf"Require ({ROLE}) approval for .+ from (\d+(?:\.\d+)?) to (\d+(?:\.\d+)?)", sentence, re.IGNORECASE)
        if threshold_range:
            role, lower, upper = threshold_range.groups()
            approvals.append({"kind": "threshold", "field": "amount", "operator": "between", "minimum": float(lower), "maximum": float(upper), "role": role.lower(), "mode": "manual", "line": line_number, "sentence": sentence})
            phrases.append({"line": line_number, "kind": "threshold_route", "minimum": float(lower), "maximum": float(upper), "role": role.lower()})
            continue

        threshold_over = re.fullmatch(rf"Require ({ROLE}) approval for .+ over (\d+(?:\.\d+)?)", sentence, re.IGNORECASE)
        if threshold_over:
            role, threshold = threshold_over.groups()
            approvals.append({"kind": "threshold", "field": "amount", "operator": ">", "value": float(threshold), "role": role.lower(), "mode": "manual", "line": line_number, "sentence": sentence})
            phrases.append({"line": line_number, "kind": "threshold_route", "operator": ">", "value": float(threshold), "role": role.lower()})
            continue

        notify = re.fullmatch(rf"Notify the ({ROLE}) by (email|in_app) when (.+)", sentence, re.IGNORECASE)
        if notify:
            recipient, channel, trigger = notify.groups()
            rule = {"kind": "notify", "trigger": trigger.strip().lower(), "channel": channel.lower(), "recipient_role": recipient.lower(), "template": f"{{process_name}}: {trigger.strip().lower()}."}
            notifications.append(rule)
            phrases.append({"line": line_number, "kind": "notification", "recipient_role": recipient.lower(), "trigger": trigger.strip().lower()})
            continue

        escalation = re.fullmatch(rf"Escalate to ({ROLE}) after (\d+) days if ({ROLE}) approval is pending", sentence, re.IGNORECASE)
        if escalation:
            recipient, days, pending_role = escalation.groups()
            rule = {"kind": "escalate", "trigger": "approval_pending", "channel": "in_app", "recipient_role": recipient.lower(), "after_days": int(days), "pending_role": pending_role.lower(), "template": f"{{process_name}}: {pending_role.lower()} approval is pending."}
            notifications.append(rule)
            actions.append({"kind": "escalate", "after_days": int(days), "from_role": pending_role.lower(), "to_role": recipient.lower()})
            phrases.append({"line": line_number, "kind": "escalation", "from_role": pending_role.lower(), "to_role": recipient.lower(), "after_days": int(days)})
            continue

        archive = re.fullmatch(r"Archive completed submissions after (\d+) days", sentence, re.IGNORECASE)
        if archive:
            days = int(archive.group(1))
            actions.append({"kind": "archive", "trigger": "completed", "after_days": days})
            phrases.append({"line": line_number, "kind": "archive", "after_days": days})
            continue

        raise UnsupportedPhraseError(
            "Sentence does not match a declared FormFlow grammar phrase.",
            line=line_number,
            sentence=sentence,
        )

    if process is None:
        raise MissingFormError("Description must include 'Create an intake form called ...'.")
    if not fields:
        raise InvalidProcessError("Description must declare at least one field.")

    field_map = {field["name"]: field for field in fields}
    for validation in validations:
        field = field_map.get(validation["field"])
        if field is None:
            raise UnknownFieldError(
                f"Validation refers to undeclared field '{validation['field']}'.",
                line=validation["line"],
                sentence=validation["sentence"],
            )
        if validation["rule"] in {"minimum", "maximum"} and field["type"] != "number":
            raise InvalidProcessError("Minimum and maximum rules require a number field.", line=validation["line"], sentence=validation["sentence"])
        if validation["rule"] == "length" and field["type"] not in {"text", "email"}:
            raise InvalidProcessError("Exact length rules require a text or email field.", line=validation["line"], sentence=validation["sentence"])
        field["validation"].append({"rule": validation["rule"], "value": validation["value"]})

    for approval in approvals:
        if approval["kind"] != "threshold":
            continue
        field = field_map.get(approval["field"])
        if field is None:
            raise UnknownFieldError(
                f"Threshold route refers to undeclared field '{approval['field']}'.",
                line=approval["line"],
                sentence=approval["sentence"],
            )
        if field["type"] != "number":
            raise InvalidProcessError(
                "Threshold routes require a number field.",
                line=approval["line"],
                sentence=approval["sentence"],
            )
        if approval["operator"] == "between" and approval["minimum"] > approval["maximum"]:
            raise InvalidProcessError(
                "Threshold range lower bound must not exceed its upper bound.",
                line=approval["line"],
                sentence=approval["sentence"],
            )

    return {
        "honesty": HONESTY,
        "process": process,
        "fields": fields,
        "approvals": approvals,
        "actions": actions,
        "notifications": notifications,
        "phrases": phrases,
    }
