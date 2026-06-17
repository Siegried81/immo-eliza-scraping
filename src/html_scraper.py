from bs4 import BeautifulSoup
from bs4.element import Tag
from points_of_interest import Interests_parser
import json
import logging
import re
import requests
from requests import RequestException
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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

def parse_property(url: str, session: requests.Session, province: str) -> dict:
    """Extract the data detail of each property from the HTML content.
    Args:        
      url (str): The url link to the property.
    Returns:     
      dict | {}: data detail of each property or an empty dict if url not found.   
    """
    if not url:
      return {}
    
    logger.info(f"Processing property in {province} from {url}...")
    try:
      r = session.get(url,timeout=20)
      r.raise_for_status()
    except RequestException as e:
      logger.exception(
        "Failed to fetch property"
      )
      return {}
    
    soup = BeautifulSoup(r.text, "lxml")
    info = {}

    content = soup.find("div", id="main_content")
    if not content:
      logger.error("main_content not found")
      return {}
    
    page_header = content.find("div", class_="detail__header_title")
    if not page_header:
      logger.error("detail__header_title not found")
      return {}
    
    vlancode = page_header.find("span", class_="vlancode")
    if vlancode:
        info["property_id"] = vlancode.get_text(strip=True) 
    else: 
      logger.error("vlancode not found")
      return {}


    address_info = page_header.find(
        "div",
        class_="detail__header_address"
    )

    info["province"] = province
    if address_info:
      spans = address_info.find_all("span")
      info["address"] = (
          spans[0].get_text(strip=True)
          if spans
          else None
      )
      city_tag = address_info.find(
        "span",
        class_="city-line"
      )
      city = city_tag.get_text(strip=True) if city_tag else ""
      parts = city.split(" ", 1)
      info["postcode"] = parts[0] if len(parts) > 1 else None
      info["city"] = parts[1] if len(parts) > 1 else parts[0]
    else:
        info["address"] = None
        info["postcode"] = None
        info["city"] = None

    info["price"] = None

    financial = content.select_one("div.financial")
    if financial:
      price_tag = financial.find("strong", string="Price")
      if price_tag:
          price_text = price_tag.parent.get_text(" ", strip=True)
          price_digits = re.sub(r"[^\d]", "", price_text)
          info["price"] = int(price_digits) if price_digits else None

    lat = None
    lng = None
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string and "AD_LATITUDE" in script.string:
            text = [part.split(" = ")for part in script.string.split(";")]
            lat = float(text[1][1][1:-1])
            lng = float(text[0][1][1:-1])
            break

    info["latitude"] = lat
    info["longitude"] = lng

    property_type = None
    for script in scripts:
        if script.string and "propertyType:" in script.string:
            property_type = script.string.split("propertyType:", 1)[1].split(",", 1)[0].strip().strip("'\"")
            break

    if property_type in ["Apartment", "Appartment"]:
        property_type = "apartment"
    elif property_type == "House":
        property_type = "house"

    info["property_type"] = property_type

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
  
  session = requests.Session()
  session.headers.update({
    "User-Agent": user_a,
    "Accept-Language": "en-US,en;q=0.9"
  })
  data = parse_property(url, session, "brussels")
  to_json_file(data, "./data/data.json")
