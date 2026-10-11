"""Append-only progress file, so a run that dies keeps what it had.

The results used to live in memory until the whole batch finished and were
written once at the end: a crash, a Ctrl-C or a blocked IP at 90% lost every
property already parsed. Each parsed property is now appended as one JSON line
the moment it arrives, and `--resume` reads that file back to skip the URLs
already done. JSON Lines rather than one JSON document because appending a
line is atomic enough for a thread pool and needs no rewrite of the file.
"""

import json
import threading
from pathlib import Path

_WRITE_LOCK = threading.Lock()


def append(path: Path, record: dict) -> None:
    """Add one property to the checkpoint. Thread-safe; creates the file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with _WRITE_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def load(path: Path) -> list[dict]:
    """Every property already checkpointed, in order. A missing file is empty.

    A truncated last line (the process died mid-write) is skipped rather than
    raised: losing one record is the expected cost of a crash, losing the resume
    is not.
    """
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records
