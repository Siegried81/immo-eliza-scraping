import requests
import re
from bs4 import BeautifulSoup
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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

  # Remove IPA / phonetic pronunciation blocks
  # Example: (/bəˈrɑːk oʊˈbɑːmə/)
  text = re.sub(r"\([^)]*[/ˈˌ][^)]*\)", "", text)

  # Replace common HTML entities
  text = re.sub(r"&nbsp;", " ", text)
  text = re.sub(r"&amp;", "&", text)

  # Replace multiple spaces, tabs and line breaks with a single space
  text = re.sub(r"\s+", " ", text)

  # Remove spaces before punctuation marks
  # Example: "hello ." -> "hello."
  text = re.sub(r"\s+([.,;:!?])", r"\1", text)

  return text.strip() 

def parse_more_info(more_info: str | None) -> dict:
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
        "land_surface": "Total land surface",
        "primary_energy_consumption": "Specific primary energy consumption",
        "planning_permission_granted": "Planning permission granted",
        "g_score": "G-score",
        "p_score": "P-score",
        "swimming_pool": "Swimming pool",
        "cellar": "Cellar",
        "veranda": "Veranda",
        "dining_room": "Dining room",
        "attic": "Attic",
        "co2_emission": "CO2 emission",
        "epc_validity_date": "Validity date EPC/PEB",
        "peb_category": "PEB category",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "province": "Province",
    }
        
    cleaned_more_info = {
        field_name: raw_dict.get(page_label, "")
        for field_name, page_label in FIELD_MAP.items()
    }

    return cleaned_more_info

def parse_property(url: str, header) -> dict:
    """Extract the data detail of each property from the HTML content.
    Args:        
      url (str): The url link to the property.
    Returns:     
      dict | {}: data detail of each property or an empty dict if url not found.   
    """
    if not url:
      return {}
    
    logger.info(f"Processing data from {url}...")
    r = requests.get(url, headers=header)
    soup = BeautifulSoup(r.text, "lxml")
    info = {}

    content = soup.find("div", id="main_content")
    header = content.find("div", class_="detail__header_title")
    info['property_id'] = header.find("span", class_="vlancode").get_text(strip=True)
    info['url'] = url
    info["name"] = header.find("span", class_="detail__header_title_main").get_text(" ", strip=True).rsplit(" ", 1)[0]

    address_info = header.find("div", class_="detail__header_address")
    info["address"] = address_info.find_all("span")[0].get_text(strip=True)
    city = address_info.find("span", class_="city-line").get_text(strip=True)
    info["postcode"], info["city"] = city.split(" ", 1)

    description = content.find("div", class_="dynamic-description").get_text(strip=True)
    info["description"] = clean_text(description)

    financial = content.select_one("div.financial")
    price_li = financial.find("strong", string="Price").parent
    price_text = price_li.get_text(" ", strip=True)
    info["price"] = re.sub(r"[^\d]", "", price_text)

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
