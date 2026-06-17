from fake_useragent import UserAgent   

from src import parse_property, to_json_file, run
import json
import logging
import os
import time

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

  output_filepath = os.path.join(base_dir, "belgium_properties.json")

  user_agent = UserAgent()

  logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
  logger = logging.getLogger(__name__)
  # ---------------------------------------
  # 1. Get Urls
  # ---------------------------------------
  logger.info("Fetching urls...")

  
  urls = {"antwerp": [],
    "limburg": [], 
    "east-flanders": [],
    "vlaams-brabant": [], 
    "west-flanders": [],
    "brussels": [], 
    "hainaut": [], 
    "liege": [],
    "luxembourg": [], 
    "namur": [],
    "brabant-wallon": []}

  run()
  
  start_time = time.perf_counter()
  with open("./data/url_by_province.csv") as csv:
    lines = csv.read().strip().split("\n")[1:]
    for line in lines:
      region, province, url = line.split(";")
      urls[province].append(url)

  logger.info(f"Time spent : {time.perf_counter() - start_time} seconds.")

  # =========================
  # 2. SCRAPE PROPERTY DETAILS
  # =========================
  start_time = time.perf_counter()
  dataset = []
  data_json = {
    "anvers": {},
    "limbourg": {},
    "flandre-orientale": {},
    "brabant-flamand": {},
    "flandre-occidentale": {},
    "bruxelles": {},
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

# ---------------------------------------
# Program entry point
# ---------------------------------------
if __name__ == "__main__":
    main()