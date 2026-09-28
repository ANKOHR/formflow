"""Self-contained HTML form and synthetic admin page renderers."""

import html
import json

HONESTY_BANNER = (
    "DEMO ONLY: FormFlow uses deterministic rules over a declared grammar, not a language model, and does not understand arbitrary English. "
    "This generated system is for review, not production. These submissions are synthetic. Notification rules are definitions only and nothing is sent."
)


def _input_type(field_type):
    return {"text": "text", "email": "email", "number": "number", "date": "date", "boolean": "checkbox"}[field_type]


def _validation_attributes(field):
    attributes = []
    for rule in field["validation"]:
        if rule["rule"] == "minimum":
            attributes.append(f' min="{rule["value"]:g}"')
        elif rule["rule"] == "maximum":
            attributes.append(f' max="{rule["value"]:g}"')
        elif rule["rule"] == "length":
            attributes.extend([f' minlength="{rule["value"]}"', f' maxlength="{rule["value"]}"'])
    return "".join(attributes)


def generate_form(parse_tree):
    process = html.escape(parse_tree["process"]["name"])
    field_html = []
    for field in parse_tree["fields"]:
        name = html.escape(field["name"], quote=True)
        label = html.escape(field["label"])
        required = " required" if field["required"] else ""
        required_label = ' <span aria-label="required">*</span>' if field["required"] else ""
        field_html.append(
            f'<div class="field"><label for="{name}">{label}{required_label}</label>'
            f'<input id="{name}" name="{name}" type="{_input_type(field["type"])}"{required}{_validation_attributes(field)}></div>'
        )
    body = "\n      ".join(field_html)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{process} intake form | FormFlow demo</title>
  <style>
    body {{ font: 16px system-ui, sans-serif; max-width: 46rem; margin: 2rem auto; padding: 0 1rem; color: #172033; }}
    .banner {{ padding: 1rem; border: 2px solid #a15b00; background: #fff5df; }}
    .field {{ margin: 1rem 0; }} label {{ display: block; font-weight: 650; margin-bottom: .35rem; }}
    input {{ box-sizing: border-box; width: 100%; padding: .65rem; font: inherit; }}
    input[type=checkbox] {{ width: auto; }} button {{ padding: .7rem 1rem; font: inherit; }}
    #result {{ margin-top: 1rem; }}
  </style>
</head>
<body>
  <p class="banner">{html.escape(HONESTY_BANNER)}</p>
  <main>
    <h1>{process}</h1>
    <form id="intake-form">
      {body}
      <button type="submit">Validate demo form</button>
    </form>
    <p id="result" role="status"></p>
  </main>
  <script>
    document.getElementById("intake-form").addEventListener("submit", function (event) {{
      event.preventDefault();
      if (!this.checkValidity()) {{ this.reportValidity(); return; }}
      document.getElementById("result").textContent = "The demo form passed local checks. No data is stored.";
    }});
  </script>
</body>
</html>
'''


def synthetic_submissions(workflow):
    states = workflow["states"]
    pending = next((state for state in states if state.startswith("pending_")), "submitted")
    candidates = [pending, "approved", "rejected"]
    rows = []
    for index, state in enumerate(candidates, start=1):
        if state not in states:
            state = "submitted"
        rows.append({"id": f"DEMO-{index:03d}", "state": state, "subject": f"Synthetic example {index}"})
    return rows


def generate_admin(parse_tree, workflow, schema):
    process = html.escape(parse_tree["process"]["name"])
    rows = "\n".join(
        f'<tr><td>{html.escape(row["id"])}</td><td>{html.escape(row["subject"])}</td><td><code>{html.escape(row["state"])}</code></td></tr>'
        for row in synthetic_submissions(workflow)
    )
    columns = ", ".join(html.escape(column["name"]) for column in schema["columns"])
    workflow_json = html.escape(json.dumps(workflow, sort_keys=True, separators=(",", ":")))
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{process} admin | FormFlow demo</title>
  <style>
    body {{ font: 16px system-ui, sans-serif; max-width: 64rem; margin: 2rem auto; padding: 0 1rem; color: #172033; }}
    .banner {{ padding: 1rem; border: 2px solid #a15b00; background: #fff5df; }}
    table {{ border-collapse: collapse; width: 100%; }} th, td {{ text-align: left; padding: .6rem; border-bottom: 1px solid #ccd2dc; }}
    code {{ background: #eef1f6; padding: .15rem .3rem; }}
  </style>
</head>
<body>
  <p class="banner">{html.escape(HONESTY_BANNER)}</p>
  <main>
    <h1>{process} submissions</h1>
    <p>Every row below is synthetic demo data.</p>
    <table>
      <thead><tr><th>Reference</th><th>Example</th><th>Workflow state</th></tr></thead>
      <tbody>
        {rows}
      </tbody>
    </table>
    <h2>Schema reference</h2>
    <p>SQLite table: <code>{html.escape(schema["table"])}</code></p>
    <p>Columns: {columns}</p>
    <details><summary>Generated workflow specification</summary><pre>{workflow_json}</pre></details>
  </main>
</body>
</html>
'''
