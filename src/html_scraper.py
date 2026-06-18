from bs4 import BeautifulSoup
from bs4.element import Tag
from src.points_of_interest import Interests_parser
import json
import logging
import re
import requests
from requests import RequestException
from html import unescape
import os
import sys

# Putting the logs in a file saves time and better history.  filemode 'w' to overwrite a previous run (default 'a' for append)
#logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
#logger = logging.getLogger(__name__)

# --- Setup Logger 1: The Scraper Tracker ---
file_logger = logging.getLogger('scraper')
file_logger.setLevel(logging.INFO)

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
log_file_path = os.path.join(project_root, 'data', 'html_scraper.log')
# Create a file handler for just the scraper logs
file_handler = logging.FileHandler(log_file_path, mode='w')
file_handler.setFormatter(logging.Formatter('%(asctime)s - SCRAPE - %(message)s'))
file_logger.addHandler(file_handler)


# --- Setup Logger 2: The Error Tracker ---
terminal_logger = logging.getLogger('scraper_terminal')
terminal_logger.setLevel(logging.INFO)

# Create a separate file handler for just errors
terminal_handler = logging.StreamHandler(sys.stdout)
terminal_handler.setFormatter(logging.Formatter('%(asctime)s - INFO - %(message)s'))
terminal_logger.addHandler(terminal_handler)

FIELD_MAP = {
  "property_state": None,
  "build_year": None, 
  "bedroom_count": None, 
  "livable_surface": None, 
  "total_surface": None, 
  "garage": None, 
  "terrace": None, 
  "peb_category": None, 
  "swimming_pool": None
}

interests = Interests_parser()

counter = 0

def safe_int(value: str) -> int | None:
    """
    Extract first integer from a messy string.

    Examples:
        "1998" → 1998
        "125 m²" → 125
        "1,200 EUR" → 1200
        "Unknown" → None
        "" → None
    """
    if not value:
        return None

    value = value.replace(",", "")
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None

def parse_bool(value: str) -> int:
  """
    Parse string boolean-like value:
    "YES" (case-insensitive, trimmed) -> 1
    any other value -> 0
  """
  return 1 if value.strip().upper() == "YES" else 0

def js_to_json(text):
    """
      Extract first JS object from text safely
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                raw = text[start:i+1]

                # convert JS object to JSON format
                raw = re.sub(r'(\w+)\s*:', r'"\1":', raw)
                raw = raw.replace("'", '"')

                try:
                    return json.loads(raw)
                except:
                    return None

def parse_more_info(more_info: Tag | None) -> dict:
    """Extract the more info detail of each property from the HTML content.
    Args:        
      html (str): The HTML content to parse.
    Returns:     
      dict | {}: data detail of each property or an empty dict if url not found.   
    """

    if more_info is None:
        return FIELD_MAP
    
    field = FIELD_MAP.copy()
    titles = [h.text.replace("\n", "").strip() for h in more_info.find_all("h4")]
    contents = [p.text.replace("\n", "").strip() for p in more_info.find_all("p")]
    
    for title, content in zip(titles, contents):
        match title:
            case "State of the property":
                field["property_state"] = content
            case "Build Year":
                field["build_year"] = safe_int(content)
            case "Number of bedrooms":
                field["bedroom_count"] = safe_int(content)
            case "Livable surface":
                field["livable_surface"] = safe_int(content)
            case "Total land surface":
                field["total_surface"] = safe_int(content)
            case "Garage":
                field["garage"] = parse_bool(content)
            case "Terrace":
                field["terrace"] = parse_bool(content)
            case "Specific primary energy consumption":
                field["peb_category"] =  safe_int(content)
            case "Swimming pool":
                field["swimming_pool"] = parse_bool(content)
            
    return field

def parse_property(url: str, header: dict, province: str, session: requests.Session) -> dict:
    """Extract the data detail of each property from the HTML content.
    Args:        
      url (str): The url link to the property.
    Returns:     
      dict | {}: data detail of each property or an empty dict if url not found.   
    """
    global counter 
    counter += 1
    if not url:
        terminal_logger.warning("No url")
        return {}

    file_logger.info("Processing property in %s from %s...", province, url)
    if counter % 300 == 0:
      terminal_logger.warning("Page n° %i : Processing property in %s from %s...", counter, province, url)   # Heartbeat log
    try:
      r = session.get(url, headers=header, timeout=10)
      r.raise_for_status()
    except session.RequestException as e:
      terminal_logger.error(e)
      return {}
    
    soup = BeautifulSoup(r.text, "lxml")
    info = {}

    scripts = soup.find_all("script")

    general_info = None
    street_address = None
    lat = lng = None

    # =========================
    # SINGLE PASS SCRIPT PARSE
    # =========================
    for script in scripts:
        if not script.string:
            continue

        text = script.string

        # ---- GENERAL INFO ----
        if general_info is None and "STORAGE_KEY_PROPERTY_DETAILS" in text:
            try:
                match = re.search(r"JSON\.stringify\((\{.*\})\)", text, re.DOTALL)
                if match:
                    general_info = js_to_json(match.group(1))
            except Exception:
                terminal_logger.error("General info parse error")

        # ---- ADDRESS (JSON-LD) ----
        if street_address is None and "PostalAddress" in text:
            try:
                data = json.loads(text)
                if isinstance(data, dict) and data.get("@type") == "PostalAddress":
                    street_address = data.get("streetAddress")
            except Exception:
                terminal_logger.error("Postal address parse error")
                pass

        # ---- LAT/LNG ----
        if lat is None and "AD_LATITUDE" in text:
            try:
                parts = [p.split(" = ") for p in text.split(";")]
                lat = float(parts[1][1][1:-1])
                lng = float(parts[0][1][1:-1])
            except Exception:
                terminal_logger.error("Latitude and longtitude parse error")
                pass

        # early exit nếu đủ dữ liệu
        if general_info and street_address and lat and lng:
            break

    if not general_info:
        terminal_logger.error("General info not found")
        return {}

    # =========================
    # NORMALIZE DATA
    # =========================

    property_type_mapping = {1: "house", 2: "apartment"}

    property_type_id = general_info.get("propertyTypeId")

    info["property_type"] = property_type_mapping.get(property_type_id)
    info["property_id"] = general_info.get("reference")
    info["postcode"] = general_info.get("zipCode")
    info["city"] = general_info.get("city")
    info["province"] = province
    info["address"] = unescape(street_address) if street_address else None
    info["latitude"] = lat
    info["longitude"] = lng

    price_raw = general_info.get("price")
    info["price"] = (
        int(float(price_raw.replace(" ", "").replace(".", "").replace(",", ".")))
        if isinstance(price_raw, str) and price_raw.strip()
        else None
    )

    # =========================
    # EXTRA PARSERS
    # =========================
    content = soup.find("div", id="main_content")

    if content:
        more_info = content.find("div", class_="general-info-wrapper")
        info.update(parse_more_info(more_info))
        info.update(interests.parsing(soup))

    return info

def to_json_file(data: dict, filepath: str) -> None:
  """Save the data to a JSON file.
  Args:        
    data (dict): The data to save.
    filename (str): The name of the file to save to.
  Returns:     
    None
  """
  with open(filepath, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__": 
  user_a = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
  url = "https://immovlan.be/en/detail/residence/for-sale/6120/nalinnes/vbe34060"
  # url = "https://immovlan.be/en/detail/cottage/for-sale/7760/velaines/rwc42720"
  # url = "https://immovlan.be/nl/detail/studio/te-huur/1000/brussel/vbe35350"
  session = requests.Session()
  session.headers.update()
  data = parse_property(url, {
    "User-Agent": user_a,
    "Accept-Language": "en-US,en;q=0.9"
  }, "brussels", session)
  to_json_file(data, "./data/data.json")
