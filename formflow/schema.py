"""Generate deterministic, SQLite-valid DDL from the parsed entity model."""

from .errors import HONESTY


def _sql_literal(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def generate_schema(parse_tree, workflow):
    process = parse_tree["process"]
    fields = parse_tree["fields"]
    table = process["slug"]
    state_values = ", ".join("'" + state.replace("'", "''") + "'" for state in workflow["states"])
    columns = [
        "id INTEGER PRIMARY KEY AUTOINCREMENT",
        f"status TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN ({state_values}))",
        "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
    ]
    column_info = [
        {"name": "id", "type": "INTEGER", "primary_key": True, "required": True},
        {"name": "status", "type": "TEXT", "primary_key": False, "required": True, "checks": [f"status IN ({state_values})"]},
        {"name": "created_at", "type": "TEXT", "primary_key": False, "required": True},
    ]

    for field in fields:
        sql_type = {"text": "TEXT", "email": "TEXT", "date": "TEXT", "number": "REAL", "boolean": "INTEGER"}[field["type"]]
        pieces = [field["name"], sql_type]
        if field["required"]:
            pieces.append("NOT NULL")
        checks = []
        if field["type"] == "boolean":
            checks.append(f"{field['name']} IN (0, 1)")
        if field["type"] == "date":
            checks.append(f"date({field['name']}) IS NOT NULL AND date({field['name']}) = {field['name']} AND {field['name']} GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'")
        for validation in field["validation"]:
            value = _sql_literal(validation["value"])
            if validation["rule"] == "minimum":
                checks.append(f"{field['name']} >= {value}")
            elif validation["rule"] == "maximum":
                checks.append(f"{field['name']} <= {value}")
            elif validation["rule"] == "length":
                checks.append(f"length({field['name']}) = {value}")
        for index, check in enumerate(checks, start=1):
            pieces.append(f"CHECK ({check})")
        columns.append(" ".join(pieces))
        column_info.append({
            "name": field["name"],
            "type": sql_type,
            "primary_key": False,
            "required": field["required"],
            "checks": checks,
        })

    honesty_comments = f"-- FormFlow honesty boundary: {HONESTY}\n"
    ddl = (
        honesty_comments
        + "-- SQLite DDL only. No data is inserted and no notifications are sent.\n"
        f"CREATE TABLE {table} (\n    " + ",\n    ".join(columns) + "\n);\n"
    )
    return {"table": table, "columns": column_info, "ddl": ddl}
