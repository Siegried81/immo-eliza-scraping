"""robots.txt gate: every fetch asks first, and fails closed.

Why a module and not a line: both the URL collector and the property parser
call `session.get`, and a rule that lives in one of them is a rule the other
forgets. `assert_can_fetch` is the single entry point; it raises rather than
returning False so a disallowed URL cannot be fetched by a caller that forgot
to look at the result.

Fail closed: a robots.txt that cannot be read (5xx, timeout, connection error)
disallows, because the rules may exist and we failed to read them. A 4xx means
no file is published, which RFC 9309 reads as no rules declared, so it allows.
One parser per host, fetched once, so the gate never costs more requests than
it saves.
"""

import threading
import urllib.robotparser
from urllib.parse import urlparse

import requests


class FetchDisallowed(Exception):
    """The site's robots.txt forbids this URL for us, or could not be read."""


class RobotsGate:
    _UNREADABLE = object()
    _NO_RULES = object()

    def __init__(self, user_agent: str = "*", timeout: float = 10.0):
        self.user_agent = user_agent
        self.timeout = timeout
        self._parsers: dict[str, object] = {}
        self._lock = threading.Lock()

    def _parser_for(self, origin: str, session: requests.Session):
        with self._lock:
            if origin in self._parsers:
                return self._parsers[origin]
        try:
            response = session.get(f"{origin}/robots.txt", timeout=self.timeout)
            if 400 <= response.status_code < 500:
                parser = self._NO_RULES
            elif response.status_code >= 500:
                parser = self._UNREADABLE
            else:
                parser = urllib.robotparser.RobotFileParser()
                parser.parse(response.text.splitlines())
        except requests.RequestException:
            parser = self._UNREADABLE
        with self._lock:
            self._parsers[origin] = parser
        return parser

    def can_fetch(self, url: str, session: requests.Session) -> bool:
        parsed = urlparse(url)
        parser = self._parser_for(f"{parsed.scheme}://{parsed.netloc}", session)
        if parser is self._UNREADABLE:
            return False
        if parser is self._NO_RULES:
            return True
        return parser.can_fetch(self.user_agent, url)

    def assert_can_fetch(self, url: str, session: requests.Session) -> None:
        if not self.can_fetch(url, session):
            raise FetchDisallowed(f"robots.txt does not allow fetching {url}")

    def crawl_delay(self, url: str, session: requests.Session) -> float | None:
        """The delay the host asks for, when it publishes one."""
        parsed = urlparse(url)
        parser = self._parser_for(f"{parsed.scheme}://{parsed.netloc}", session)
        if parser in (self._UNREADABLE, self._NO_RULES):
            return None
        delay = parser.crawl_delay(self.user_agent)
        return float(delay) if delay else None


#: Shared by every thread of a run: one robots.txt per host, read once.
GATE = RobotsGate()
