"""
Loads config.json once, at import time, so a bad config fails straight away
instead of halfway through a scrape.

Keys:
  main_max_workers             threads for the property detail scrape
  main_max_scraped_properties  stop after this many properties
  url_fetcher_max_worker       threads for the search result page scrape
  url_fetcher_max_pages        pages per province and price range
  request_delay_seconds        minimum gap between two requests to one host
  scraper_contact              address advertised in the User-Agent

The worker counts are small on purpose: src/polite.py serialises requests per
host, so extra threads only wait in line.
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

except FileNotFoundError:
    raise RuntimeError(f"Config file not found: {CONFIG_PATH}")

except json.JSONDecodeError as e:
    raise RuntimeError(f"Invalid config JSON: {e}")