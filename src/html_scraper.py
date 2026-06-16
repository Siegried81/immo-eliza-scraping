import requests
import re
from bs4 import BeautifulSoup
import json
import logging
from bs4.element import Tag
import html
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FIELD_MAP = {
    "property_state": "State of the property",
    "is_rented": "Currently leased",
    "build_year": "Build Year",
    "num_bedrooms": "Number of bedrooms",
    "livable_surface": "Livable surface",
    "furnished": "Furnished",
    "kitchen_equipment": "Kitchen equipment",
    "kitchen_type": "Kitchen type",
    "num_bathrooms": "Number of bathrooms",
    "num_showers": "Number of showers",
    "num_toilets": "Number of toilets",
    "heating_type": "Type of heating",
    "glazing_type": "Type of glazing",
    "elevator": "Elevator",
    "num_facades": "Number of facades",
    "num_floors": "Number of floors",
    "orientation": "Orientation of the front facade",
    "garden": "Garden",
    "terrace": "Terrace",
    "terrace_orientation": "Terrace orientation",
    "sewer_connection": "Sewer Connection",
    "gas": "Gas",
    "running_water": "Running water",
    "balcony": "Balcony",
    "land_surface": "Total land surface",
    "primary_energy_consumption": "Specific primary energy consumption",
    "epc_peb_reference": "EPC/PEB reference",
    "planning_permission_granted": "Planning permission granted",
    "g_score": "G-score",
    "p_score": "P-score",
    "swimming_pool": "Swimming pool",
    "cellar": "Cellar",
    "veranda": "Veranda",
    "dining_room": "Dining room",
    "attic": "Attic",
    "co2_emission": "CO2 emission",
    "cert_electrical_installation": "Certification - Electrical installation",
    "epc_validity_date": "Validity date EPC/PEB",
    "peb_category": "PEB category",
    "latitude": "Latitude",
    "longitude": "Longitude",
}
 
def clean_text(text: str) -> str:
  """Clean the extracted text by removing extra whitespace and special characters.
  Args:        
    text (str): The text to clean.
  Returns:     
    str: The cleaned text.
  """
  # Remove references/citations
  # Examples: [1], [12], [a], [citation needed]
  text = re.sub(r"\[[^\]]*\]", "", text)

  # Replace common HTML entities
  text = html.unescape(text)

  # Replace multiple spaces, tabs and line breaks with a single space
  text = re.sub(r"\s+", " ", text)

  # Remove spaces before punctuation marks
  # Example: "hello ." -> "hello."
  text = re.sub(r"\s+([.,;:!?])", r"\1", text)

  return text.strip() 

def parse_more_info(more_info: Tag | None) -> dict:
    """Extract the more info detail of each property from the HTML content.
    Args:        
      html (str): The HTML content to parse.
    Returns:     
      dict | {}: data detail of each property or an empty dict if url not found.   
    """

    if more_info is None:
        return {
            field: ""
            for field in FIELD_MAP.keys()
        }
    
    more_info_titles = [h.text.replace("\n", "").strip() for h in more_info.find_all("h4")]
    more_info_contents = [p.text.replace("\n", "").strip() for p in more_info.find_all("p")]
    
    raw_dict = dict(zip(more_info_titles, more_info_contents))
    if len(more_info_titles) != len(more_info_contents):
      logger.warning(
        f"Mismatch titles={len(more_info_titles)} "
        f"contents={len(more_info_contents)}"
      )

    cleaned_more_info = {
        field_name: raw_dict.get(page_label, "")
        for field_name, page_label in FIELD_MAP.items()
    }

    return cleaned_more_info

def get_province_by_postcode(postcode: str):
    try:
        p = int(str(postcode).strip())
    except:
        return None

    # Brussels-Capital Region
    if 1000 <= p <= 1299:
        return "Brussels-Capital Region"

    # Flemish Brabant (Leuven area + surroundings)
    if 1300 <= p <= 1499:
        return "Walloon Brabant"
    if 1500 <= p <= 1999:
        return "Flemish Brabant"

    # Antwerp
    if 2000 <= p <= 2999:
        return "Antwerp"

    # Limburg
    if 3500 <= p <= 3999:
        return "Limburg"

    # East Flanders
    if 9000 <= p <= 9999:
        return "East Flanders"

    # West Flanders
    if 8000 <= p <= 8999:
        return "West Flanders"

    # Hainaut
    if 6000 <= p <= 6599 or 7000 <= p <= 7999:
        return "Hainaut"

    # Liège
    if 4000 <= p <= 4999:
        return "Liège"

    # Namur
    if 5000 <= p <= 5999:
        return "Namur"

    # Luxembourg
    if 6600 <= p <= 6999:
        return "Luxembourg"

    return None

def get_province(postcode=None, city=None):
    # ưu tiên postcode
    if postcode:
        result = get_province_by_postcode(postcode)
        if result:
            return result

    # fallback city
    if city:
        return get_province_by_city(city)

    return None

def parse_property(url: str, header: dict) -> dict:
    """Extract the data detail of each property from the HTML content.
    Args:        
      url (str): The url link to the property.
    Returns:     
      dict | {}: data detail of each property or an empty dict if url not found.   
    """
    if not url:
      return {}
    
    logger.info(f"Processing data from {url}...")
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
    info["property_id"] = vlancode.get_text(strip=True) if vlancode else ""

    info['url'] = url

    name_tag = page_header.find(
      "span",
      class_="detail__header_title_main"
    )

    info["name"] = (
      name_tag.get_text(" ", strip=True).rsplit(" ", 1)[0]
      if name_tag
      else ""
    )

    address_info = page_header.find(
        "div",
        class_="detail__header_address"
    )

    if address_info:
      spans = address_info.find_all("span")
      info["address"] = (
          spans[0].get_text(strip=True)
          if spans
          else ""
      )
      city_tag = address_info.find(
        "span",
        class_="city-line"
      )
      city = city_tag.get_text(strip=True) if city_tag else ""
      parts = city.split(" ", 1)
      info["postcode"] = parts[0] if len(parts) > 1 else ""
      info["city"] = parts[1] if len(parts) > 1 else parts[0]
      info["province"] = get_province_by_postcode(info["postcode"])
    else:
        info["address"] = ""
        info["postcode"] = ""
        info["city"] = ""
        info["province"] = ""

    description_tag = content.find("div", class_="dynamic-description")

    info["description"] = (
        clean_text(description_tag.get_text(strip=True))
        if description_tag
        else ""
    )

    info["price"] = ""
    info["cadastral_income"] = ""
    financial = content.select_one("div.financial")
    if financial:
      price_tag = financial.find("strong", string="Price")
      if price_tag:
          price_text = price_tag.parent.get_text(" ", strip=True)
          info["price"] = re.sub(r"[^\d]", "", price_text)

      cadastral_income_tag = financial.find("strong", string="Cadastral income")
      if cadastral_income_tag:
          cadastral_income_text = cadastral_income_tag.parent.get_text(" ", strip=True)
          info["cadastral_income"] = re.sub(r"[^\d]", "", cadastral_income_text)


    more_info = content.find("div", class_="general-info-wrapper")
    info.update(parse_more_info(more_info))

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
