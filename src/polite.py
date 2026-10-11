"""
Politeness layer shared by every fetcher in this project.

Fetching a live site needs three things the first version of the scrapers did
not do, and they live together here so no fetcher can forget one of them:

1. Ask the host's robots.txt whether a path may be fetched at all.
2. Identify the crawler honestly, with a contact address, so the site can reach
   us or block us. Rotating browser User-Agents does the opposite: its only
   purpose is to look like many different humans, which is evasion.
3. Leave a gap between two requests to the same host, and honour a
   Crawl-delay directive when robots.txt sets one.

Everything is configured from config.json, so the delay and the contact
address can be changed without touching the fetchers.
"""
import threading
import time
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import requests

from config import config

# One honest identity instead of a rotating pool. The contact belongs in the
# User-Agent itself because that is the only place a site operator looks.
CONTACT = config.get("scraper_contact", "immo-eliza-scraping@example.org")
USER_AGENT = f"ImmoElizaBot/1.0 (BeCode student project; +mailto:{CONTACT})"

# Minimum seconds between two requests to the same host. robots.txt may ask
# for more, never for less.
REQUEST_DELAY = float(config.get("request_delay_seconds", 1.0))

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_lock = threading.Lock()
_robots_cache = {}
_last_request_at = {}


class RobotsDisallowed(Exception):
    """Raised instead of fetching a URL that the host's robots.txt forbids."""


def _host_of(url):
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _robots_for(url):
    """
    Return the parsed robots.txt of the URL's host, fetched once per host.

    A host whose robots.txt cannot be read is treated as fully disallowed: we
    would otherwise be guessing that crawling is welcome. The file is fetched
    with plain requests, not through the shared session, so a caller cannot end
    up recursing back into this module.
    """
    host = _host_of(url)
    with _lock:
        cached = _robots_cache.get(host)
    if cached is not None:
        return cached

    parser = RobotFileParser()
    robots_url = urlunsplit((urlsplit(url).scheme, urlsplit(url).netloc, "/robots.txt", "", ""))
    parser.set_url(robots_url)
    try:
        response = requests.get(robots_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
        else:
            # 404 means "no rules published", which robots.txt defines as
            # allow-all. Anything else (403, 5xx) we do not get to interpret.
            parser.allow_all = response.status_code == 404
    except requests.RequestException:
        parser.disallow_all = True

    with _lock:
        _robots_cache[host] = parser
    return parser


def can_fetch(url):
    """True when the host's robots.txt lets our User-Agent fetch this URL."""
    return _robots_for(url).can_fetch(USER_AGENT, url)


def assert_can_fetch(url):
    """Raise RobotsDisallowed unless robots.txt allows this URL."""
    if not can_fetch(url):
        raise RobotsDisallowed(f"robots.txt disallows {url} for {USER_AGENT}")


def _delay_for(url):
    """Seconds to wait between requests: our floor, or more if robots.txt asks."""
    declared = _robots_for(url).crawl_delay(USER_AGENT)
    return max(REQUEST_DELAY, float(declared or 0))


def _wait_turn(url):
    """
    Sleep until this host's next slot is free.

    The timestamp is reserved while the lock is held, so N worker threads take
    N turns instead of all sleeping the same gap and then firing together.
    """
    host = _host_of(url)
    delay = _delay_for(url)
    with _lock:
        now = time.monotonic()
        earliest = max(now, _last_request_at.get(host, 0.0) + delay)
        _last_request_at[host] = earliest
    pause = earliest - time.monotonic()
    if pause > 0:
        time.sleep(pause)


def polite_get(session, url, timeout=10, headers=None, **kwargs):
    """
    GET a URL only if robots.txt allows it, after waiting for the host's slot.

    Takes the session so connection reuse still works. Extra headers are merged
    on top of HEADERS, but the User-Agent is always ours: a caller must not be
    able to reintroduce a spoofed or rotating identity.
    """
    assert_can_fetch(url)
    _wait_turn(url)
    merged = {**HEADERS, **(headers or {}), "User-Agent": USER_AGENT}
    return session.get(url, headers=merged, timeout=timeout, **kwargs)
