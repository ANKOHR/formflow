# FormFlow

FormFlow turns a description written with a small set of declared process phrases into an inspectable intake demo: an approval workflow, SQLite DDL, a self-contained HTML form, validation rules, notification rule definitions, and a self-contained admin page. It is a deterministic compiler, not a general natural-language system.

## Quickstart

Requirements: Python 3.10 or newer and pytest for the test suite. Runtime code uses only the Python standard library. No GPU packages or workloads are used.

```powershell
python -m pip install -e .
python -m formflow fixtures --out build/fixtures
python -m formflow compile build/fixtures/leave_request/description.txt --out build/leave-request
python -m formflow validate build/fixtures/expense_claim/description.txt
python -m formflow serve-note build/leave-request
python -m pytest -q
```

The compile command writes `spec.json`, `parse.json`, `workflow.json`, `schema.sql`, `form.html`, `notifications.json`, and `admin.html`. Open `form.html` and `admin.html` in a browser to inspect the generated pages. The form checks required fields locally and stores no data. `validate` applies the generated DDL to an in-memory SQLite database. Each CLI invocation appends its command, input hash, spec hash, and UTC timestamp to `ff-audit.jsonl` in the current directory.

You can also use the module form without installing the `ff` entry point, for example `python -m formflow validate path/to/description.txt`.
The `ff` console command is installed by `pip install -e .`. On Windows, the Python Scripts directory must be on `PATH`; otherwise use the equivalent `python -m formflow` command shown above.

## Architecture

```text
description.txt
      |
      v
line-based declared-phrase parser
      |  named errors include line and sentence
      v
stable parse tree
      |
      +--> approval workflow graph compiler --> cycle check --> workflow.json
      +--> entity and validation compiler --> SQLite DDL --> schema.sql
      +--> field renderer --> self-contained intake page --> form.html
      +--> notify and escalate phrases --> rule list --> notifications.json
      +--> workflow plus synthetic rows --> self-contained admin page --> admin.html
      |
      v
spec.json contains the shared parse tree and every generated output
```

All generators read the same parse tree. The workflow graph compiler turns role chains into states and transitions and runs cycle detection over the resulting directed graph. Threshold phrases become conditional transitions. The schema generator converts fields, required markers, and validation rules into SQLite column definitions and `CHECK` constraints. The form, admin page, and notification definitions are generated without external assets.

## HONESTY BOUNDARY

FormFlow parses descriptions with deterministic rules over a declared grammar. It does not use a language model and does not understand arbitrary English. Phrases outside the grammar are rejected with a named error and a pointer to the offending sentence. The generated systems are demos for review, not production systems. The admin UI shows synthetic submissions, not real data. Notifications are rule definitions only, and nothing is sent. The CLI, README, and every generated system artifact state these limits plainly.

## Declared grammar

Use one sentence per non-empty line. Lines beginning with `#` are ignored comments; generated fixture descriptions use one to label their fictional status and repeat the honesty boundary. The parser is case-insensitive for keywords and role names, but field types are limited to the list below. A field name is normalized to lowercase with spaces replaced by underscores. Numbers in threshold and validation phrases are decimal numeric literals. There is no fallback to arbitrary-English interpretation.

| Phrase | Example | Compiles to |
| --- | --- | --- |
| Form name | `Create an intake form called Leave Request.` | Process name `Leave Request` and stable table slug `leave_request` |
| Field | `Include a required field named employee with type text.` | Required `TEXT` column and a labelled HTML input |
| Optional field | `Include an optional field named reason with type text.` | Nullable column and input without a required marker |
| Field types | `text`, `email`, `number`, `date`, `boolean` | SQLite `TEXT`, `TEXT`, `REAL`, `TEXT`, `INTEGER`; form input types `text`, `email`, `number`, `date`, `checkbox` |
| Minimum | `The amount must be at least 0.` | Parse validation, HTML `min`, and SQLite `CHECK (amount >= 0)` |
| Maximum | `The amount must be at most 1000.` | Parse validation, HTML `max`, and SQLite `CHECK (amount <= 1000)` |
| Exact length | `The tax id must contain exactly 9 characters.` | Parse validation, HTML length attributes, and SQLite length check |
| Approval chain | `Require manager approval then finance approval.` | Ordered pending states and approve/reject transitions for each named role |
| Approval chain wording | `Require manager approval followed by finance approval.` | Same ordered chain form |
| Self route | `Self-approve expense claims under 100.` | Automatic requester route to `approved` when `amount < 100` |
| Range route | `Require manager approval for expense claims from 100 to 1000.` | Manual manager route with an inclusive lower and upper bound |
| Upper route | `Require finance approval for expense claims over 1000.` | Manual finance route when `amount > 1000` |
| Notify | `Notify the requester by email when a submission is received.` | Email rule with the explicit `requester` recipient and a `{process_name}` template placeholder |
| In-app notify | `Notify the finance by in_app when a submission is received.` | In-app rule with the explicit `finance` recipient |
| Escalate | `Escalate to finance after 3 days if manager approval is pending.` | In-app escalation rule from the explicit pending role to the explicit recipient role |
| Archive | `Archive completed submissions after 365 days.` | Archive action with a completion trigger and retention delay |

The accepted type names are exact. Validation phrases must refer to a declared field. Minimum and maximum checks require a number field. Exact length requires a text or email field. A phrase containing unresolved alternatives such as `or` or `might` is rejected as `AmbiguousPhraseError`. Any other phrase that does not match this catalogue is rejected as `UnsupportedPhraseError`. A repeated role that creates a cycle in the compiled workflow is rejected as `WorkflowCycleError`.

## Fixtures and determinism

`ff fixtures --out DIR` generates leave request, supplier onboarding, expense claim, ambiguous, and cyclic approval fixtures. Every fixture directory has a `README.txt` and `fixture.json` marking it as fictional and generated. The expected parse tree, compiled spec, or named error is written beside the description. The fixture metadata records seed `0`; the generator currently uses no random number generation. Each fixture description begins with a fictional label and the honesty boundary in a parser-ignored comment. The same description produces byte-identical JSON, DDL, and HTML.

The expense fixture routes values below 100 to automatic self-approval, values from 100 through 1000 to manager approval, and values over 1000 to finance approval. No real people, companies, claims, notifications, or submissions are involved.

## CLI reference

```text
ff fixtures --out DIR
ff compile DESCRIPTION --out DIR
ff validate DESCRIPTION
ff serve-note [ARTIFACT_DIR]
```

`compile` creates files only in the requested output directory. `validate` checks parsing, workflow compilation, and SQLite DDL application without creating a persistent database. `serve-note` prints instructions to open an existing generated `admin.html`; it does not start a network server. All commands append an audit record to the current directory's `ff-audit.jsonl`.

## Tests

Run the full fixture-driven suite with `python -m pytest -q`. It covers parser success and rejection, deterministic fixture generation, approval graph routing and cycle detection, SQLite DDL application and constraints, form and admin rendering, notification recipient fidelity, CLI behavior, audit records, and end-to-end compilation.
