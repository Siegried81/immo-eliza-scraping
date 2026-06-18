from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent   
from src import fetching_urls_zimmo, html_scraper_zimmo, to_csv
import csv
import logging
import os
import pandas as pd
import requests
import time
import sys

logger = logging.getLogger('main_logger')
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - INFO - %(message)s'))
logger.addHandler(handler)

MAX_WORKERS = 25

def main():
  """
  Main entry point of the seating application.

  This program:
  1. Loads configuration from a JSON file. -> not anymore, replaced by a UserAgent().random
  """
  # ---------------------------------------
  # Load configuration file
  # ---------------------------------------
  # Get project base directory
  base_dir = os.path.dirname(__file__)
  url_by_province_filepath = os.path.join(base_dir, "./data/zimmo_urls_by_province.csv")
  output_filepath = os.path.join(base_dir, "./data/zimmo_properties.csv")
  output_dataframe_filepath = os.path.join(base_dir, "./data/dataframe.json")


  user_agent = UserAgent()

# ---------------------------------------
# Choose URL source mode
# ---------------------------------------
  logger.info("\n=== Choose URL source ===")
  logger.info("1. Use previou1y scraped URLs")
  logger.info("2. Scrape URLs again")

  use_existing_urls = False
  if os.path.exists(url_by_province_filepath):
    while True:
      choice_url_mode = input("Choose an option: ")

      if choice_url_mode == "1":
          use_existing_urls = True
          break

      elif choice_url_mode == "2":
          use_existing_urls = False
          break

      else:
          logger.info("Options are 1 or 2. Please choose again.")
  else:
    logger.info("No existing URL source found. Start scraping URLs.")

  # ---------------------------------------
  # 1. Get Urls
  # ---------------------------------------
  urls = {
     "antwerp": [],
    "limburg": [], 
    "east-flanders": [],
    "vlaams-brabant": [], 
    "west-flanders": [],
    "brussels": [], 
    "hainaut": [], 
    "liege": [],
    "luxembourg": [], 
    "namur": [],
    "brabant-wallon": []
  }
  
  if not use_existing_urls:
    start_time = time.perf_counter()
    logger.info("Fetching URLs...")
    fetching_urls_zimmo(url_by_province_filepath)

    seconds_past = time.perf_counter() - start_time
    logger.info("Time spent : %f seconds.", seconds_past)   # quicker than f""

  total_urls = 0
  if os.path.exists(url_by_province_filepath):
    with open(url_by_province_filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            province = row.get("province", "").strip().lower()
            url = row.get("url", "").strip()

            if province in urls and url.startswith("http"):
                urls[province].append(url)
                total_urls += 1

  logger.info("\n=== URL Source Loaded ===")
  logger.info(f"Total URLs: {total_urls}")
  

  logger.info("\nDo you want to scrape details?")
  logger.info("1. Yes")
  logger.info("2. No (exit)")
  start_scraping = False
  while True:
    choice = input("Choose 1 or 2: ").strip()

    if choice == "1":
        start_scraping = True
        break

    elif choice == "2":
        start_scraping = False
        break

    else:
        logger.info("Options are 1 or 2. Please choose again.")

  # =========================
  # 2. SCRAPE PROPERTY DETAILS
  # =========================

  if start_scraping:
    start_time = time.perf_counter()
    dataset = []
    data_json = {
      "antwerp": {},
      "limburg": {},
      "east-flanders": {},
      "vlaams-brabant": {},
      "west-flanders": {},
      "brussels": {},
      "hainaut": {},
      "liege": {},
      "luxembourg": {},
      "namur": {},
      "brabant-wallon": {},
    }
    dataset = html_scraper_zimmo(url_by_province_filepath)
    seconds_past = time.perf_counter() - start_time
    logger.info("Time spent : %f seconds.", seconds_past)

    # ---------------------------------------
    # 3. Save properties data to JSON file
    # ---------------------------------------
    to_csv(output_filepath, dataset)

# ---------------------------------------
# Program entry point
# ---------------------------------------
if __name__ == "__main__":
    main()