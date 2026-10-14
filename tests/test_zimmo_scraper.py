"""The Zimmo detail scraper survives its progress message.

Importing the module opens data/zimmo_errors.log in 'w' mode, which would wipe
a real run's log, so the file handler is replaced before the import.
"""
import importlib
import logging
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))


@pytest.fixture
def scraper(monkeypatch):
    monkeypatch.setattr(logging, "FileHandler", lambda *a, **k: logging.NullHandler())
    sys.modules.pop("src.zimmo_html_scraper", None)
    module = importlib.import_module("src.zimmo_html_scraper")
    monkeypatch.setattr(module, "fetch_soup", lambda url: None)
    return module


def test_the_300th_property_logs_progress_instead_of_crashing(scraper, monkeypatch):
    """parse_property called the logger object itself every 300th page: TypeError."""
    monkeypatch.setattr(scraper, "counter", 299)
    assert scraper.parse_property("https://www.zimmo.be/x", "Flanders", "Antwerpen") is None
    assert scraper.counter == 300
