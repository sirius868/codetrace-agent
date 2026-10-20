"""Explicit, atomic local output. Records contain source evidence."""
import json
import os
import tempfile
from pathlib import Path


def write_json(target: Path, data: dict):
    return write_text(target, json.dumps(data, ensure_ascii=False, indent=2))


def write_text(target: Path, text: str):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".codetrace-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target.resolve()
