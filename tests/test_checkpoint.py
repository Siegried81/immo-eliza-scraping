"""The checkpoint file and the resume that reads it."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import checkpoint  # noqa: E402


def test_records_appended_are_read_back_in_order(tmp_path):
    path = tmp_path / "properties.jsonl"
    checkpoint.append(path, {"property_id": 1, "source_url": "https://x/1", "city": "Liège"})
    checkpoint.append(path, {"property_id": 2, "source_url": "https://x/2"})
    assert [r["property_id"] for r in checkpoint.load(path)] == [1, 2]
    assert checkpoint.load(path)[0]["city"] == "Liège"


def test_a_missing_file_is_an_empty_run(tmp_path):
    assert checkpoint.load(tmp_path / "absent.jsonl") == []


def test_a_truncated_last_line_loses_one_record_not_the_resume(tmp_path):
    path = tmp_path / "properties.jsonl"
    checkpoint.append(path, {"property_id": 1, "source_url": "https://x/1"})
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"property_id": 2, "source_')   # the process died here
    assert [r["property_id"] for r in checkpoint.load(path)] == [1]


def test_resume_skips_done_urls_and_caps_the_rest():
    import main

    urls = {"liege": ["https://x/1", "https://x/2", "https://x/3"], "namur": ["https://x/4"]}
    tasks = main.select_tasks(urls, done_urls={"https://x/1", "https://x/3"}, limit=10)
    assert tasks == [("https://x/2", "liege"), ("https://x/4", "namur")]
    assert main.select_tasks(urls, done_urls=set(), limit=2) == [("https://x/1", "liege"), ("https://x/2", "liege")]
