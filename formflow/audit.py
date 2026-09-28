"""Append-only, deterministic-hash audit records for CLI invocations."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest_json(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return digest_bytes(raw)


def append_audit(command, input_hash, spec_hash, path="ff-audit.jsonl"):
    record = {
        "command": command,
        "input_hash": input_hash,
        "spec_hash": spec_hash,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    target = Path(path)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return record
