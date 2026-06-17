from fake_useragent import UserAgent   
from src import parse_property, to_json_file, fetch_urls
import logging
import os
import pandas as pd
import time
import csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
  """
  Main entry point of the seating application.

  This program:
  1. Loads configuration from a JSON file.
  """
  # ---------------------------------------
  # Load configuration file
  # ---------------------------------------
  # Get project base directory
  base_dir = os.path.dirname(__file__)
  url_by_province_filepath = os.path.join(base_dir, "./data/url_by_province.csv")
  output_filepath = os.path.join(base_dir, "./data/data.json")

  user_agent = UserAgent()

  logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
  logger = logging.getLogger(__name__)
# ---------------------------------------
# Choose URL source mode
# ---------------------------------------
  print("\n=== Choose URL source ===")
  print("1. Use previously scraped URLs")
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
    logger.info("Fetching URLs...")
    fetch_urls(url_by_province_filepath)

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

  print("\nDo you want to continue scraping details?")
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
        logger.info("Options are 1 or 2. Please choose again.")

  # =========================
  # 2. SCRAPE PROPERTY DETAILS
  # =========================
  if start_scraping:
    start_time = time.perf_counter()
    logger.info(f"Time spent : {time.perf_counter() - start_time} seconds.")
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
    property_ids = []

    for province, url_list in urls.items():
      for url in url_list:
        try:
          data = parse_property(url, {"User-Agent": user_agent.random}, province)

          if data["property_id"] not in property_ids:
            property_ids.append(data["property_id"])
            dataset.append(data)
            if data["postcode"] not in data_json[province]:
              data_json[province][data["postcode"]] = []
            data_json[province][data["postcode"]].append(data)
          time.sleep(0.2)  # prevent blocking
        except:
          continue
    logger.info(f"Time spent : {time.perf_counter() - start_time} seconds.")

    # ---------------------------------------
    # 3. Save properties data to JSON file
    # ---------------------------------------
    logger.info(f"Saving data to {output_filepath}...")
    to_json_file(data_json, output_filepath)

    final_df = pd.DataFrame(dataset)

    final_df.to_json("../data/dataframe.json", orient="records", force_ascii=False, indent=4)

# ---------------------------------------
# Program entry point
# ---------------------------------------
if __name__ == "__main__":
    main()