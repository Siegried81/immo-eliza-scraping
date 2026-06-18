import bs4
import requests
import csv
import logging
import os
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent   
import sys

file_logger = logging.getLogger('zimmo_scraper')
file_logger.setLevel(logging.INFO)

file_logger.propagate = False

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
log_file_path = os.path.join(project_root, 'data', 'zimmo_errors.log')

file_handler = logging.FileHandler(log_file_path, mode='w')
file_handler.setFormatter(logging.Formatter('%(asctime)s - ZIMMO - %(message)s'))
file_logger.addHandler(file_handler)

terminal_logger = logging.getLogger('scraper_terminal')
terminal_logger.setLevel(logging.INFO)

terminal_handler = logging.StreamHandler(sys.stdout)
terminal_handler.setFormatter(logging.Formatter('%(asctime)s - INFO - %(message)s'))
terminal_logger.addHandler(terminal_handler)

# Config
Region_map = {
    "bruxelles": "Bruxelles", "Antwerpen": "Flandre", "Limburg_haselt": "Flandre",
    "East_Flanders_gent": "Flandre", "West_flanders_bruges": "Flandre",
    "Vlaams_Brabant_Leuven": "Flandre", "Liege": "Wallonie", "Namur": "Wallonie",
    "Leuze_en_Hainaut": "Wallonie", "Arlon_Luxembourg": "Wallonie", "Wavre_brabant_wallon": "Wallonie",
}

Provinces_map = {
    "bruxelles": "Bruxelles", "Antwerpen": "Antwerp", "Limburg_haselt": "Limburg",
    "East_Flanders_gent": "East Flanders", "West_flanders_bruges": "West Flanders",
    "Vlaams_Brabant_Leuven": "Vlaams-Brabant", "Liege": "Liege", "Namur": "Namur",
    "Leuze_en_Hainaut": "Hainaut", "Arlon_Luxembourg": "Luxembourg", "Wavre_brabant_wallon": "Brabant-Wallon",
}

Csv_file = "zimmo_parser_optimized.csv"
Max_workers = 25

Session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=Max_workers, pool_maxsize=Max_workers)
Session.mount('https://', adapter)
Session.mount('http://', adapter)

user_agent = UserAgent()
counter = 0

def fetch_soup(url):
    try:
        r = Session.get(url, headers={"User-Agent": user_agent.random}, timeout=10)               
        return bs4.BeautifulSoup(r.text, "html.parser") if r.status_code == 200 else None 
    except: return None                                                 

def parse_float(value):
    value = value.replace(".", "")
    value = value.replace(",", ".")
    value = re.sub(r"[^(\d|\.)]", "", value)
    if value:
        return float(value)
    else:
        return None
def parse_property(url, geo, prov):
    global counter
    counter += 1
    if counter % 300 == 0:
        terminal_logger(f"page {counter} currently in {Provinces_map[prov]}")
    soup = fetch_soup(url)
    if not soup: return None
    try:
        property_id = soup.find("div", attrs={"class": "zimmo-code"}).text.split(": ")[1][:-1] 
        details = soup.find("section", attrs={"id": "main-features"})   
        if not details: return None
        
        data = {
            "region": geo, "province": Provinces_map[prov], "property_id": property_id,
            "price": None, "address": None, "postal_code": None, "city_name": None,
            "property_type": None, "livable_surface": None, "total_surface": None,
            "bedroom_count": None, "build_year": None, "peb_category": None, "garage": None
        }
        
        for li in details.find_all("li"):                               
            cat = li.find("strong").text if li.find("strong") else None
            value = li.find("span").text.strip() if li.find("span") else ""
            match cat:                                                  
                case "Prix": data["price"] = parse_float(value)
                case "Adresse":
                    address, rest = value.split(", ")                   
                    data["address"] = address
                    data["postal_code"], data["city_name"] = rest.split(maxsplit=1)
                case "Type": data["property_type"] = "House" if "Maison" in value else "Appartment"
                case "Surf. habitable": data["livable_surface"] = parse_float(value)
                case "Sup. du terrain": data["total_surface"] = parse_float(value)
                case "Chambres": data["bedroom_count"] = parse_float(value)
                case "Construit en": data["build_year"] = parse_float(value)
                case "PEB":
                    parts = value.split()
                    data["peb_category"] = int(parts[0]) if parts[0].isdigit() else None
        
        if not data["total_surface"]: data["total_surface"] = data["livable_surface"] 
        
        garages_div = soup.find("div", attrs={"class":"col-xs-7 info-name"}, string="Garages") 
        data["garage"] = 1 if (garages_div and garages_div.find_next_sibling("div").get_text(strip=True) != "0") else 0
        return data
    except Exception as e:                                              
        file_logger.error(e)
        return None

def html_scraper_zimmo(input_file):

    all_links_to_scrape = []
    with open(input_file, newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            all_links_to_scrape.append((row["url"], Region_map[row['province']], row['province']))
    
    all_properties = []
    start_time = time.perf_counter()
    with ThreadPoolExecutor(max_workers=Max_workers) as executor:       
        futures = [executor.submit(parse_property, l, g, p) for l, g, p in all_links_to_scrape]
        for f in as_completed(futures):
            res = f.result()
            if res: all_properties.append(res)

    all_properties.sort(key=lambda x: (x["region"], x["province"]))     
    print(f"Time spent : {time.perf_counter() - start_time} s")
    return all_properties


def to_csv(Csv_file, all_properties):
    keys = ["region", "province", "property_id", "property_type", "postal_code", "city_name", 
            "address", "price", "bedroom_count", "livable_surface", "total_surface", "build_year", "garage", "peb_category"]
    with open(Csv_file, "w", newline="", encoding="utf-8") as f:       
        writer = csv.DictWriter(f, fieldnames=keys, delimiter=";")
        writer.writeheader()
        writer.writerows(all_properties)
    print(f"Done {len(all_properties)} links found.")
    

if __name__ == "__main__":
    pass
