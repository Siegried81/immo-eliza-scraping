import bs4
import requests
import csv
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# Config
Region_map = {
    "bruxelles": "Bruxelles", "anvers": "Flandre", "limbourg": "Flandre",
    "flandre-orientale": "Flandre", "flandre-occidentale": "Flandre",
    "brabant-flamand": "Flandre", "liege": "Wallonie", "namur": "Wallonie",
    "hainaut": "Wallonie", "luxembourg": "Wallonie", "brabant-wallon": "Wallonie",
}

Search_urls = {
    "bruxelles": "https://www.zimmo.be/fr/bruxelles/a-vendre/",
    "anvers": "https://www.zimmo.be/fr/anvers/a-vendre/",
    "limbourg": "https://www.zimmo.be/fr/limbourg/a-vendre/",
    "flandre-orientale": "https://www.zimmo.be/fr/flandre-orientale/a-vendre/",
    "flandre-occidentale": "https://www.zimmo.be/fr/flandre-occidentale/a-vendre/",
    "brabant-flamand": "https://www.zimmo.be/fr/brabant-flamand/a-vendre/",
    "liege": "https://www.zimmo.be/fr/liege/a-vendre/",
    "namur": "https://www.zimmo.be/fr/namur/a-vendre/",
    "hainaut": "https://www.zimmo.be/fr/hainaut/a-vendre/",
    "luxembourg": "https://www.zimmo.be/fr/luxembourg/a-vendre/",
    "brabant-wallon": "https://www.zimmo.be/fr/brabant-wallon/a-vendre/",
}

Csv_file = "zimmo_parser_optimized.csv"
Max_workers = 20
Headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
Session = requests.Session()

# Core functions
def fetch_soup(url):
    try:
        r = Session.get(url, headers=Headers, timeout=15)               # Request the URL
        return bs4.BeautifulSoup(r.text, "html.parser") if r.status_code == 200 else None # Return parser
    except: return None                                                 # Return None on error

def extract_links(soup):
    if not soup: return []
    links = []
    for a in soup.find_all("a", href=True):                             # Loop through all links
        href = a["href"]
        if "/a-vendre/" in href and "/recherche/" not in href and href.startswith("/fr/"):
            links.append("https://www.zimmo.be" + href.split("?")[0])   # Clean and store links
    return list(set(links))                                             # Ensure uniqueness

def parse_property(url, geo, prov):
    soup = fetch_soup(url)
    if not soup: return None
    try:
        property_id = soup.find("div", attrs={"class": "zimmo-code"}).text.split(": ")[1][:-1] # find prop ID
        details = soup.find("section", attrs={"id": "main-features"})   # find features section
        if not details: return None
        
        data = {
            "region": geo, "province": prov, "url": url, "property_id": property_id,
            "price": None, "address": None, "postal_code": None, "city_name": None,
            "property_type": None, "livable_surface": None, "total_surface": None,
            "bedroom_count": None, "build_year": None, "peb_category": None, "garage": 0
        }
        
        for li in details.find_all("li"):                               # iterate through features
            cat = li.find("strong").text if li.find("strong") else None
            value = li.find("span").text.strip() if li.find("span") else ""
            match cat:                                                  # match feature type
                case "Prix": data["price"] = int(value.replace("€ ", "").replace(".", ""))
                case "Adresse":
                    address, rest = value.split(", ")                   # split address components
                    data["address"] = address
                    data["postal_code"], data["city_name"] = rest.split(maxsplit=1)
                case "Type": data["property_type"] = "House" if "Maison" in value else "Appartment"
                case "Surf. habitable": data["livable_surface"] = int(value.split()[0])
                case "Sup. du terrain": data["total_surface"] = int(value.split()[0])
                case "Chambres": data["bedroom_count"] = int(value)
                case "Construit en": data["build_year"] = int(value) if value.isdigit() else None
                case "PEB":
                    parts = value.split()
                    data["peb_category"] = int(parts[0]) if parts[0].isdigit() else None
        
        if not data["total_surface"]: data["total_surface"] = data["livable_surface"] # init defaults
        
        garages_div = soup.find("div", attrs={"class":"col-xs-7 info-name"}, string="Garages") 
        data["garage"] = 1 if (garages_div and garages_div.find_next_sibling("div").get_text(strip=True) != "0") else 0
        return data
    except Exception as e:                                              # handle parsing errors
        print(f"Erreur lors du parsing: {e}")
        return None

# Scrape engine
def run():
    all_links_to_scrape = []
    for prov, base_url in Search_urls.items():
        for page in range(1, 100): 
            soup = fetch_soup(f"{base_url}?p={page}")                   # Paginated fetch
            links = extract_links(soup)
            if not links: break                                         # Stop if page empty
            for link in links:
                all_links_to_scrape.append((link, Region_map[prov], prov))
    
    all_properties = []
    with ThreadPoolExecutor(max_workers=Max_workers) as executor:       # Parallel parsing
        futures = [executor.submit(parse_property, l, g, p) for l, g, p in all_links_to_scrape]
        for f in as_completed(futures):
            res = f.result()
            if res: all_properties.append(res)

    all_properties.sort(key=lambda x: (x["region"], x["province"]))     # Sorting logic
    
    keys = ["region", "province", "property_id", "url", "property_type", "postal_code", "city_name", 
            "address", "price", "bedroom_count", "livable_surface", "total_surface", "build_year", "garage", "peb_category"]
    with open(Csv_file, "w", newline="", encoding="utf-8") as f:        # File output
        writer = csv.DictWriter(f, fieldnames=keys, delimiter=";")
        writer.writeheader()
        writer.writerows(all_properties)
    print(f"Done {len(all_properties)} links found.")

if __name__ == "__main__":
    run()
