from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent   
from src import parse_property, to_json_file, fetch_urls
import csv
import logging
import os
import pandas as pd
import requests
import time
import csv
import requests
import sys
from config import config

logger = logging.getLogger('main_logger')
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - INFO - %(message)s'))
logger.addHandler(handler)

MAX_WORKERS = config["main_max_workers"]
MAX_PROPERTIES = config["main_max_scraped_properties"]

def main():
  """
    Orchestrates the scraping process by managing URL source selection,
    property data extraction using multi-threading, and saving the results.
  """

  # ---------------------------------------
  # Load configuration file
  # ---------------------------------------
  # Get project base directory
  base_dir = os.path.dirname(__file__)
  url_by_province_filepath = os.path.join(base_dir, "./data/url_by_province.csv")
  output_filepath = os.path.join(base_dir, "./data/data.json")
  output_dataframe_filepath = os.path.join(base_dir, "./data/dataframe.json")
  
  user_agent = UserAgent()

# ---------------------------------------
# Choose URL source mode
# ---------------------------------------
  print("\n=== Choose URL source ===")
  print("1. Use previou1y scraped URLs")
  print("2. Scrape URLs again")

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
         print("Options are 1 or 2. Please choose again.")
  else:
    logger.info("No existing URL source found. Start scraping URLs.")

  # ---------------------------------------
  # 1. Get Urls
  # ---------------------------------------
  """Determines whether to fetch fresh URLs from the source or load 
     existing ones from a CSV file for the scraping process."""
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
    fetch_urls(url_by_province_filepath)

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

  print("\n=== URL Source Loaded ===")
  print(f"Total URLs: {total_urls}")
  

  print("\nDo you want to scrape details?")
  print("1. Yes")
  print("2. No (exit)")
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
        print("Options are 1 or 2. Please choose again.")

  # =========================
  # 2. SCRAPE PROPERTY DETAILS
  # =========================
  """Initializes a ThreadPoolExecutor to concurrently scrape detailed property 
    data, handles request sessions, and processes results to populate the dataset."""

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
    count = 0
    stop = False
    property_ids = set()
    tasks = []  

    for province, url_list in urls.items():
      for url in url_list:
        tasks.append((url, {"User-Agent": user_agent.random}, province))
        count += 1
        if count >= MAX_PROPERTIES:
            stop = True
            break
      if stop:
        break

    with requests.Session() as session:
      
      adapter = requests.adapters.HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
      session.mount('https://', adapter)
      session.mount('http://', adapter)
      with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        future_to_task = {
          executor.submit(parse_property, url, header, province, session): (url, province)
          for url, header, province in tasks
        }  
        
        for future in as_completed(future_to_task):
          try:
            data = future.result()
          except Exception as e:
            logger.error(e)
            continue
          
          if not data or "property_id" not in data:
            continue

          if data["property_id"] in property_ids:
            continue

          property_ids.add(data["property_id"])
          dataset.append(data)
          if data["postcode"] not in data_json[data["province"]]:
            data_json[data["province"]][data["postcode"]] = []
          data_json[data["province"]][data["postcode"]].append(data)
    seconds_past = time.perf_counter() - start_time
    logger.info("Time spent : %f seconds.", seconds_past)

    # ---------------------------------------
    # 3. Save properties data to JSON file
    # ---------------------------------------
    """ Aggregates the scraped data into a structured JSON format and exports 
        the dataset to both a JSON file and a pandas DataFrame."""

    logger.info("Saving data to %s...", output_filepath)
    to_json_file(data_json, output_filepath)

    final_df = pd.DataFrame(dataset)
    final_df.to_json(output_dataframe_filepath, orient="records", force_ascii=False, indent=4)
    final_df.info()


# ---------------------------------------
# Program entry point
# ---------------------------------------
if __name__ == "__main__":
    main()