"""Connect parsing and generators into one deterministic compilation result."""

import json
from pathlib import Path

from .parser import HONESTY, parse_description
from .render import generate_admin, generate_form
from .schema import generate_schema
from .workflow import compile_workflow


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def compile_description(description):
    parse_tree = parse_description(description)
    workflow = compile_workflow(parse_tree)
    schema = generate_schema(parse_tree, workflow)
    form_html = generate_form(parse_tree)
    admin_html = generate_admin(parse_tree, workflow, schema)
    notifications = {
        "honesty": HONESTY,
        "notice": "Rules only. No email, in-app message, or other notification is sent.",
        "rules": parse_tree["notifications"],
    }
    return {
        "product": "FormFlow",
        "honesty": HONESTY,
        "process": parse_tree["process"],
        "parse": parse_tree,
        "workflow": workflow,
        "schema": schema,
        "form_html": form_html,
        "notifications": notifications,
        "admin_html": admin_html,
    }


def write_compilation(result, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "spec.json": canonical_json(result),
        "parse.json": canonical_json(result["parse"]),
        "workflow.json": canonical_json({"honesty": HONESTY, **result["workflow"]}),
        "schema.sql": result["schema"]["ddl"],
        "form.html": result["form_html"],
        "notifications.json": canonical_json(result["notifications"]),
        "admin.html": result["admin_html"],
    }
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8", newline="\n")
    return sorted(files)
