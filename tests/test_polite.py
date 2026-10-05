"""
Tests for the politeness layer in src/polite.py.

Every network call is faked: the suite must never touch immovlan.be or
zimmo.be, so robots.txt bodies and responses are injected with monkeypatch.
The caches in src.polite are module-level, so each test clears them first.
"""
import sys
import time
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

import requests

from src import polite

ALLOW_ALL = "User-agent: *\nDisallow:\n"
DENY_DETAIL = "User-agent: *\nDisallow: /en/detail/\n"
DENY_ALL = "User-agent: *\nDisallow: /\n"
SLOW = "User-agent: *\nDisallow:\nCrawl-delay: 5\n"


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code


@pytest.fixture(autouse=True)
def clean_caches(monkeypatch):
    """Empty the per-host robots and timing caches, and block real requests."""
    polite._robots_cache.clear()
    polite._last_request_at.clear()
    monkeypatch.setattr(requests, "get", _no_network)
    yield
    polite._robots_cache.clear()
    polite._last_request_at.clear()


def _no_network(*args, **kwargs):
    raise AssertionError("a test tried to make a real HTTP request")


def serve_robots(monkeypatch, body, status_code=200):
    """Answer the one robots.txt fetch src.polite makes per host."""
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return FakeResponse(body, status_code)

    monkeypatch.setattr(polite.requests, "get", fake_get)
    return calls


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, headers=None, timeout=None, **kwargs):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout, **kwargs})
        return FakeResponse("<html></html>")


class TestUserAgent:
    def test_is_a_single_honest_identity_with_a_contact(self):
        assert polite.USER_AGENT.startswith("ImmoElizaBot/")
        assert "mailto:" in polite.USER_AGENT

    def test_does_not_claim_to_be_a_browser(self):
        lowered = polite.USER_AGENT.lower()
        for browser in ("mozilla", "chrome", "safari", "firefox", "edg/"):
            assert browser not in lowered

    def test_is_stable_across_calls(self):
        assert polite.HEADERS["User-Agent"] == polite.USER_AGENT


class TestCanFetch:
    def test_allows_a_path_robots_does_not_forbid(self, monkeypatch):
        serve_robots(monkeypatch, ALLOW_ALL)
        assert polite.can_fetch("https://example.org/en/detail/abc")

    def test_refuses_a_forbidden_path(self, monkeypatch):
        serve_robots(monkeypatch, DENY_DETAIL)
        assert not polite.can_fetch("https://example.org/en/detail/abc")
        assert polite.can_fetch("https://example.org/en/search")

    def test_refuses_everything_when_robots_denies_all(self, monkeypatch):
        serve_robots(monkeypatch, DENY_ALL)
        assert not polite.can_fetch("https://example.org/anything")

    def test_missing_robots_means_allowed(self, monkeypatch):
        serve_robots(monkeypatch, "", status_code=404)
        assert polite.can_fetch("https://example.org/en/detail/abc")

    def test_unreadable_robots_means_refused(self, monkeypatch):
        def boom(url, **kwargs):
            raise requests.ConnectionError("down")

        monkeypatch.setattr(polite.requests, "get", boom)
        # Not reachable is not the same as allowed: we do not get to guess.
        assert not polite.can_fetch("https://example.org/en/detail/abc")

    def test_robots_is_fetched_once_per_host(self, monkeypatch):
        calls = serve_robots(monkeypatch, ALLOW_ALL)
        for page in range(5):
            polite.can_fetch(f"https://example.org/page/{page}")
        assert len(calls) == 1


class TestAssertCanFetch:
    def test_raises_for_a_forbidden_url(self, monkeypatch):
        serve_robots(monkeypatch, DENY_ALL)
        with pytest.raises(polite.RobotsDisallowed):
            polite.assert_can_fetch("https://example.org/x")

    def test_is_silent_for_an_allowed_url(self, monkeypatch):
        serve_robots(monkeypatch, ALLOW_ALL)
        assert polite.assert_can_fetch("https://example.org/x") is None


class TestPoliteGet:
    def test_refuses_before_touching_the_session(self, monkeypatch):
        serve_robots(monkeypatch, DENY_ALL)
        session = FakeSession()

        with pytest.raises(polite.RobotsDisallowed):
            polite.polite_get(session, "https://example.org/x")

        assert session.calls == []

    def test_sends_our_user_agent(self, monkeypatch):
        serve_robots(monkeypatch, ALLOW_ALL)
        monkeypatch.setattr(polite, "REQUEST_DELAY", 0.0)
        session = FakeSession()

        polite.polite_get(session, "https://example.org/x")

        assert session.calls[0]["headers"]["User-Agent"] == polite.USER_AGENT

    def test_extra_headers_cannot_override_the_user_agent(self, monkeypatch):
        serve_robots(monkeypatch, ALLOW_ALL)
        monkeypatch.setattr(polite, "REQUEST_DELAY", 0.0)
        session = FakeSession()

        polite.polite_get(session, "https://example.org/x",
                          headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "fr"})

        sent = session.calls[0]["headers"]
        assert sent["User-Agent"] == polite.USER_AGENT
        assert sent["Accept-Language"] == "fr"

    def test_waits_between_two_requests_to_the_same_host(self, monkeypatch):
        serve_robots(monkeypatch, ALLOW_ALL)
        monkeypatch.setattr(polite, "REQUEST_DELAY", 0.2)
        session = FakeSession()

        started = time.monotonic()
        polite.polite_get(session, "https://example.org/a")
        polite.polite_get(session, "https://example.org/b")

        assert time.monotonic() - started >= 0.2

    def test_passes_extra_kwargs_through(self, monkeypatch):
        serve_robots(monkeypatch, ALLOW_ALL)
        monkeypatch.setattr(polite, "REQUEST_DELAY", 0.0)
        session = FakeSession()

        polite.polite_get(session, "https://example.org/x", timeout=20, verify=False)

        assert session.calls[0]["timeout"] == 20
        assert session.calls[0]["verify"] is False


class TestCrawlDelay:
    def test_robots_crawl_delay_wins_when_larger(self, monkeypatch):
        serve_robots(monkeypatch, SLOW)
        monkeypatch.setattr(polite, "REQUEST_DELAY", 1.0)
        assert polite._delay_for("https://example.org/x") == 5.0

    def test_our_floor_wins_when_larger(self, monkeypatch):
        serve_robots(monkeypatch, ALLOW_ALL)
        monkeypatch.setattr(polite, "REQUEST_DELAY", 1.5)
        assert polite._delay_for("https://example.org/x") == 1.5


class TestConfiguration:
    def test_a_delay_is_configured(self):
        assert polite.REQUEST_DELAY > 0

    def test_worker_counts_stay_modest(self):
        from config import config

        assert config["main_max_workers"] <= 8
        assert config["url_fetcher_max_worker"] <= 8


class TestNoUserAgentRotation:
    """fake_useragent is what rotation was built on; nothing may import it."""

    SOURCES = ["main.py", "secondary.py", "src/url_fetcher.py", "src/html_scraper.py",
               "src/zimmo_url_fetcher.py", "src/zimmo_html_scraper.py", "src/polite.py"]

    @pytest.mark.parametrize("relpath", SOURCES)
    def test_module_does_not_use_fake_useragent(self, relpath):
        source = (BASE_DIR / relpath).read_text(encoding="utf-8")
        assert "fake_useragent" not in source
        assert ".random" not in source
