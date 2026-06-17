from bs4 import BeautifulSoup
from bs4.element import Tag
from .points_of_interest import Interests_parser
import html
import json
import logging
import pandas as pd
import re
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

#"property_id": None, "property_type": None, "province": None, "postal_code": None, "city_name": None, "address": None, "price": None, 
FIELD_MAP = {"livable_surface": None, "total_surface": None, "bedroom_count": None, "build_year": None, "property_state": None,"peb_category": None, "garage": None, "terrace": None, "swimming_pool": None}

interests = Interests_parser()

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
    more_info_titles = [h.text.replace("\n", "").strip() for h in more_info.find_all("h4")]
    more_info_contents = [p.text.replace("\n", "").strip() for p in more_info.find_all("p")]
    
    for i, title in enumerate(more_info_titles):
        match title:
            case "State of the property":
                field["property_state"] = more_info_contents[i]
            case "Build Year":
                field["build_year"] = int(more_info_contents[i])
            case "Number of bedrooms":
                field["bedroom_count"] = int(more_info_contents[i])
            case "Livable surface":
                field["livable_surface"] = int(more_info_contents[i].split()[0])
            case "Total land surface":
                field["total_surface"] = int(more_info_contents[i].split()[0])
            case "Garage":
                field["garage"] = 1 if more_info_contents[i] == "YES" else 0
            case "Terrace":
                field["terrace"] = 1 if more_info_contents[i] == "YES" else 0
            case "Specific primary energy consumption":
                field["peb_category"] = int(more_info_contents[i].split()[0])
            case "Swimming pool":
                field["swimming_pool"] = 1 if more_info_contents[i] == "YES" else 0
            

    return field

def parse_property(url: str, header: dict, province: str) -> dict:
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
      r = requests.get(url, headers=header, timeout=20)
      r.raise_for_status()
    except requests.RequestException as e:
      logger.error(e)
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
    else: return {}


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
      city = city_tag.get_text(strip=True) if city_tag else None
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
          info["price"] = int(re.sub(r"[^\d]", "", price_text))

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
  url = "https://immovlan.be/en/detail/studio/for-sale/1190/vorst/vbe35475"
  data = parse_property(url, {
          "User-Agent": user_a,
          "Accept-Language": "en-US,en;q=0.9"
        }, "brussels")
  
  to_json_file(data, "../data/data.json")
