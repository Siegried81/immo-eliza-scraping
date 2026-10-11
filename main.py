"""Collect Immovlan listings: URLs per province, then one record per property.

    python main.py                       # interactive: the two menus below
    python main.py --yes                 # no prompts: reuse the URL file, then scrape
    python main.py --yes --resume        # skip what data/properties.jsonl already holds
    python main.py --yes --refetch-urls  # collect the URL list again first

Three things the orchestration guarantees, because losing them cost real runs:

- **robots.txt first.** Every fetch goes through `src.compliance.GATE`, and the
  run stops before the thread pool starts if the site disallows us. A scraper
  that asks after the fact is a scraper that already fetched.
- **Progress survives a crash.** Each parsed property is appended to
  `data/properties.jsonl` the moment it arrives. `--resume` reads it back and
  skips those URLs, so a blocked IP at 90% costs the last 10%, not the run.
- **No prompt when nobody is there.** `--yes` answers both menus, so the script
  can run from a scheduler or a CI job without hanging on `input()`.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from src import parse_property, to_json_file, fetch_urls
from src import checkpoint
from src.compliance import GATE, FetchDisallowed
import argparse
import csv
import logging
import os
import pandas as pd
import requests
import time
import sys
from config import config

logger = logging.getLogger('main_logger')
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - INFO - %(message)s'))
logger.addHandler(handler)

MAX_WORKERS = config["main_max_workers"]
MAX_PROPERTIES = config["main_max_scraped_properties"]

PROVINCES = (
    "antwerp", "limburg", "east-flanders", "vlaams-brabant", "west-flanders",
    "brussels", "hainaut", "liege", "luxembourg", "namur", "brabant-wallon",
)


def select_tasks(urls_by_province: dict, done_urls: set, limit: int) -> list:
    """The (url, province) pairs to scrape this run: not done yet, at most `limit`.

    Separate from `main` so the resume logic is testable without a network:
    the dedup against the checkpoint and the cap are the two things that decide
    how much a re-run costs.
    """
    tasks = []
    for province, url_list in urls_by_province.items():
        for url in url_list:
            if url in done_urls:
                continue
            tasks.append((url, province))
            if len(tasks) >= limit:
                return tasks
    return tasks


def _ask(prompt: str, options: dict, auto: str | None):
    """A numbered menu, or the `auto` answer when the run is unattended."""
    if auto is not None:
        return options[auto]
    while True:
        choice = input(prompt).strip()
        if choice in options:
            return options[choice]
        print(f"Options are {', '.join(options)}. Please choose again.")


def main():
    """Orchestrate URL selection, the threaded property scrape, and the exports."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--yes", action="store_true",
                        help="no prompts: reuse the URL file when it exists, then scrape")
    parser.add_argument("--refetch-urls", action="store_true",
                        help="collect the URL list again even when the file exists")
    parser.add_argument("--resume", action="store_true",
                        help="keep the records in data/properties.jsonl and skip their URLs")
    parser.add_argument("--max", type=int, default=MAX_PROPERTIES,
                        help=f"properties to scrape this run (config: {MAX_PROPERTIES})")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    url_by_province_filepath = os.path.join(base_dir, "data", "url_by_province.csv")
    output_filepath = os.path.join(base_dir, "data", "data.json")
    output_dataframe_filepath = os.path.join(base_dir, "data", "dataframe.json")
    checkpoint_path = os.path.join(base_dir, "data", "properties.jsonl")


    # ---------------------------------------
    # 1. Get URLs
    # ---------------------------------------
    use_existing_urls = False
    if os.path.exists(url_by_province_filepath):
        print("\n=== Choose URL source ===")
        print("1. Use previously scraped URLs")
        print("2. Scrape URLs again")
        auto = ("2" if args.refetch_urls else "1") if (args.yes or args.refetch_urls) else None
        use_existing_urls = _ask("Choose an option: ", {"1": True, "2": False}, auto)
    else:
        logger.info("No existing URL source found. Start scraping URLs.")

    if not use_existing_urls:
        start_time = time.perf_counter()
        logger.info("Fetching URLs...")
        fetch_urls(url_by_province_filepath)
        logger.info("Time spent : %f seconds.", time.perf_counter() - start_time)

    urls = {province: [] for province in PROVINCES}
    total_urls = 0
    if os.path.exists(url_by_province_filepath):
        with open(url_by_province_filepath, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter=";"):
                province = row.get("province", "").strip().lower()
                url = row.get("url", "").strip()
                if province in urls and url.startswith("http"):
                    urls[province].append(url)
                    total_urls += 1

    print("\n=== URL Source Loaded ===")
    print(f"Total URLs: {total_urls}")

    print("\nDo you want to scrape details?")
    print("1. Yes")
    print("2. No (exit)")
    start_scraping = _ask("Choose 1 or 2: ", {"1": True, "2": False}, "1" if args.yes else None)
    if not start_scraping:
        return

    # =========================
    # 2. SCRAPE PROPERTY DETAILS
    # =========================
    done = checkpoint.load(checkpoint_path) if args.resume else []
    done_urls = {record.get("source_url") for record in done}
    tasks = select_tasks(urls, done_urls, args.max)
    if done:
        logger.info("Resuming: %d properties already in %s, %d URLs left to fetch.",
                    len(done), checkpoint_path, len(tasks))
    if not tasks:
        logger.info("Nothing left to scrape.")
        dataset = done
    else:
        start_time = time.perf_counter()
        dataset = list(done)
        property_ids = {record["property_id"] for record in done if "property_id" in record}

        with requests.Session() as session:
            adapter = requests.adapters.HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
            session.mount('https://', adapter)
            session.mount('http://', adapter)

            # Asked once, before any worker starts: a site that disallows us
            # must not be hit 25 times in parallel to find that out.
            try:
                GATE.assert_can_fetch(tasks[0][0], session)
            except FetchDisallowed as e:
                logger.error("%s - nothing fetched.", e)
                sys.exit(2)

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_task = {
                    executor.submit(parse_property, url, province, session): (url, province)
                    for url, province in tasks
                }
                for future in as_completed(future_to_task):
                    url, province = future_to_task[future]
                    try:
                        data = future.result()
                    except Exception as e:
                        logger.error("%s (%s): %s", url, province, e)
                        continue
                    if not data or "property_id" not in data:
                        continue
                    if data["property_id"] in property_ids:
                        continue
                    property_ids.add(data["property_id"])
                    record = {**data, "source_url": url}
                    # Written now, not at the end: this line is what --resume reads back.
                    checkpoint.append(checkpoint_path, record)
                    dataset.append(record)
        logger.info("Time spent : %f seconds.", time.perf_counter() - start_time)

    # ---------------------------------------
    # 3. Save properties data to JSON files
    # ---------------------------------------
    data_json = {province: {} for province in PROVINCES}
    for record in dataset:
        data_json.setdefault(record.get("province", ""), {}).setdefault(record.get("postcode"), []).append(record)

    logger.info("Saving %d properties to %s...", len(dataset), output_filepath)
    to_json_file(data_json, output_filepath)

    final_df = pd.DataFrame(dataset)
    final_df.to_json(output_dataframe_filepath, orient="records", force_ascii=False, indent=4)
    final_df.info()


if __name__ == "__main__":
    main()
