"""Command line interface for fixture generation and compilation."""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from .audit import append_audit, digest_bytes, digest_json
from .compiler import canonical_json, compile_description, write_compilation
from .errors import FormFlowError
from .fixtures import FIXTURE_DESCRIPTIONS, generate_fixtures
from .parser import HONESTY


def _parser():
    parser = argparse.ArgumentParser(
        prog="ff",
        description="Compile a declared set of process phrases into a review demo. No language model is used; arbitrary English is not understood.",
        epilog=HONESTY,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    fixtures = sub.add_parser("fixtures", help="generate fictional compiler fixtures")
    fixtures.add_argument("--out", required=True, help="directory for generated fixtures")
    compile_cmd = sub.add_parser("compile", help="compile one process description")
    compile_cmd.add_argument("description", help="UTF-8 description file")
    compile_cmd.add_argument("--out", required=True, help="directory for generated artifacts")
    validate = sub.add_parser("validate", help="parse a description and validate its generated SQLite DDL")
    validate.add_argument("description", help="UTF-8 description file")
    note = sub.add_parser("serve-note", help="print local viewing instructions for generated HTML")
    note.add_argument("artifact_dir", nargs="?", default=".", help="directory containing generated admin.html")
    return parser


def _input_hash(command, args):
    pieces = [command.encode("utf-8")]
    if command in {"compile", "validate"}:
        path = Path(args.description)
        pieces.append(path.read_bytes() if path.is_file() else args.description.encode("utf-8"))
    elif command == "fixtures":
        pieces.append(json.dumps(FIXTURE_DESCRIPTIONS, sort_keys=True).encode("utf-8"))
        pieces.append(str(args.out).encode("utf-8"))
    elif command == "serve-note":
        pieces.append(str(args.artifact_dir).encode("utf-8"))
    return digest_bytes(b"\0".join(pieces))


def _handle(args):
    if args.command == "fixtures":
        names = generate_fixtures(args.out)
        payload = {"fixtures": names, "notice": HONESTY}
        print(f"Generated {len(names)} fictional fixtures in {args.out}.")
        print(HONESTY)
        return payload
    if args.command == "compile":
        description = Path(args.description).read_text(encoding="utf-8")
        result = compile_description(description)
        files = write_compilation(result, args.out)
        print(f"Compiled {result['process']['name']} with deterministic rules over the declared grammar.")
        print(HONESTY)
        print(f"Wrote: {', '.join(files)}")
        return result
    if args.command == "validate":
        description = Path(args.description).read_text(encoding="utf-8")
        result = compile_description(description)
        with sqlite3.connect(":memory:") as connection:
            connection.executescript(result["schema"]["ddl"])
        print(f"VALID: {result['process']['name']} parsed; generated SQLite DDL applied cleanly.")
        print(HONESTY)
        return result
    if args.command == "serve-note":
        admin = Path(args.artifact_dir) / "admin.html"
        if not admin.is_file():
            raise FormFlowError(f"No generated admin.html found at {admin}.")
        print(f"Open {admin.resolve()} in a browser to review the generated admin page.")
        print(HONESTY)
        return {"note": "local HTML viewing only", "admin": str(admin), "honesty": HONESTY}
    raise AssertionError("Unknown CLI command.")


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    spec_hash = None
    input_hash = None
    try:
        input_hash = _input_hash(args.command, args)
        result = _handle(args)
        spec_hash = digest_json(result)
        return 0
    except FormFlowError as error:
        error_data = error.as_dict()
        print(canonical_json(error_data), file=sys.stderr, end="")
        spec_hash = digest_json(error_data)
        return 2
    except (OSError, sqlite3.Error) as error:
        error_data = {"error": type(error).__name__, "message": str(error), "line": None, "sentence": None, "honesty": HONESTY}
        print(canonical_json(error_data), file=sys.stderr, end="")
        spec_hash = digest_json(error_data)
        return 2
    finally:
        if input_hash is None:
            input_hash = digest_bytes(" ".join(sys.argv if argv is None else argv).encode("utf-8"))
        try:
            append_audit(args.command, input_hash, spec_hash or hashlib.sha256(b"no-result").hexdigest())
        except OSError as error:
            print(f"Could not append ff-audit.jsonl: {error}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
