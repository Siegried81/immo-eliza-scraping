
import os
import json
from src import parse_property, to_json_file
import logging
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
  config_filepath = os.path.join(base_dir, "config.json")
  output_filepath = os.path.join(base_dir, "belgium_properties.json")
  with open(config_filepath, "r", encoding="utf-8") as f:
    config = json.load(f)

  # ---------------------------------------
  # 1. Get Urls
  # ---------------------------------------
  logger.info("Fetching urls...")
  # Example:
  urls = ["https://immovlan.be/en/detail/residence/for-sale/9600/ronse/rbw18859",
          "https://immovlan.be/en/detail/penthouse/for-sale/2500/lier/rbw20388", 
          "https://immovlan.be/en/detail/duplex/for-sale/1070/anderlecht/vbe34263"
        ]

  # =========================
  # 2. SCRAPE PROPERTY DETAILS
  # =========================
  dataset = []
  for url in urls:
    try:
      data = parse_property(url, {
        "User-Agent": config["user_agent"],
        "Accept-Language": config["accept_language"]
      })
      dataset.append(data)
      time.sleep(0.5)  # prevent blocking
    except:
      continue

  # ---------------------------------------
  # 3. Save properties data to JSON file
  # ---------------------------------------
  logger.info(f"Saving data to {output_filepath}...")
  to_json_file(dataset, output_filepath)

# ---------------------------------------
# Program entry point
# ---------------------------------------
if __name__ == "__main__":
    main()
