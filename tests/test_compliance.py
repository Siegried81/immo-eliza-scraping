"""The robots.txt gate, against a fake session: no network anywhere.

Fail closed is the property that matters: an unreadable robots.txt disallows,
a missing one allows, and a published Disallow is honoured for our paths.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.compliance import FetchDisallowed, RobotsGate  # noqa: E402


def _session(status=200, text="", error=None):
    session = MagicMock()
    if error:
        session.get.side_effect = error
    else:
        response = MagicMock(status_code=status, text=text)
        session.get.return_value = response
    return session


def test_a_published_disallow_is_honoured():
    gate = RobotsGate()
    session = _session(text="User-agent: *\nDisallow: /fr/annonce/\n")
    assert gate.can_fetch("https://example.be/fr/liste", session) is True
    with pytest.raises(FetchDisallowed):
        gate.assert_can_fetch("https://example.be/fr/annonce/123", session)


def test_an_unreadable_robots_txt_disallows():
    for session in (_session(status=503), _session(error=requests.ConnectionError("down"))):
        assert RobotsGate().can_fetch("https://example.be/anything", session) is False


def test_a_missing_robots_txt_allows():
    assert RobotsGate().can_fetch("https://example.be/anything", _session(status=404)) is True


def test_robots_txt_is_fetched_once_per_host():
    gate = RobotsGate()
    session = _session(text="User-agent: *\nAllow: /\n")
    for i in range(5):
        gate.can_fetch(f"https://example.be/page/{i}", session)
    assert session.get.call_count == 1


def test_crawl_delay_is_read_when_published():
    gate = RobotsGate()
    session = _session(text="User-agent: *\nCrawl-delay: 2\n")
    assert gate.crawl_delay("https://example.be/x", session) == 2.0
