from bs4 import BeautifulSoup                     
from concurrent.futures import ThreadPoolExecutor 
from fake_useragent import UserAgent    
import logging   
import os                      
import pandas as pd      
import requests                                   
import time        
import sys                               

# this generates a new random browser identity each time we call ua.random
user_agent = UserAgent()

"""Defines scraping parameters like target URL, price brackets to maximize search 
  coverage, and geographical data. Sets up dual logging for file tracking 
  and terminal status updates."""

# --- Setup Logger 1: The Scraper Tracker ---
file_logger = logging.getLogger('fetcher')
file_logger.setLevel(logging.INFO)

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
log_file_path = os.path.join(project_root, 'data', 'url_fetcher.log')
# Create a file handler for just the scraper logs
file_handler = logging.FileHandler(log_file_path, mode='w')
file_handler.setFormatter(logging.Formatter('%(asctime)s - SCRAPE - %(message)s'))
file_logger.addHandler(file_handler)

# --- Setup Logger 2: The Error Tracker ---
terminal_logger = logging.getLogger('fetcher_terminal')
terminal_logger.setLevel(logging.INFO)

# Create a separate file handler for just errors
terminal_handler = logging.StreamHandler(sys.stdout)
terminal_handler.setFormatter(logging.Formatter('%(asctime)s - INFO - %(message)s'))
terminal_logger.addHandler(terminal_handler)

BASE_URL = "https://immovlan.be/en/real-estate?transactiontypes=for-sale&propertytypes=house,apartment&islifeannuity=no&includenewconstruction=no&noindex=1"

# We add price ranges to break the site's limit and get more results
PRICE_RANGES = [
    (0, 200000), (200001, 300000), (300001, 400000), 
    (400001, 500000), (500001, 750000), (750001, 1000000), (1000001, 99999999)
]

                                                  # dict mapping regions to their respective provinces
GEO_DATA = {
    "bruxelles": {
        "name": "Bruxelles-Capitale", 
        "provinces": ["brussels"]},
    "flandre": {
        "name": "Flandre", 
        "provinces": [
            "antwerp", 
            "limburg", 
            "east-flanders", 
            "vlaams-brabant", 
            "west-flanders"]},
    "wallonie": {
        "name": "Wallonie", 
        "provinces": [
            "hainaut", 
            "liege", 
            "luxembourg", 
            "namur", 
            "brabant-wallon"]}
}

MAX_PAGES = 50
MAX_WORKERS = 10                                  # max nb of threads running simultaneously

def extract_links(html):

    """Parses the HTML response to identify all property detail links,
    converts relative paths to absolute URLs, and returns a unique set."""

    if not html: return []                        
    soup = BeautifulSoup(html, "html.parser")     
    links = []
    for a in soup.select('a[href*="/en/detail/"]'): # find all links pointing to property details
        href = a.get("href")                      # retrieve 'href' attribute from the anchor tag
        if href:                                  
            if href.startswith("/"):              # if link exist, convert it to an absolute URL
                href = "https://immovlan.be" + href
            links.append(href)                    # append the full URL to the list
    return list(set(links))                      

def fetch_data(region_slug, province_slug, region_name, min_p, max_p, session):

    """Iterates through search result pages for a specific province and price 
    range, extracts property URLs, and stores them with their associated 
    regional metadata."""

    results = []                                  
    file_logger.info("Threader scaping in %s between %i € and %i €", province_slug, min_p, max_p)
    if min_p == 0:
        terminal_logger.warning("Threader scaping in %s between %i € and %i €", province_slug, min_p, max_p)   # Heartbeat Log
    for page in range(1, MAX_PAGES + 1):
                                                  
        url = f"{BASE_URL}&regions={region_slug}&provinces={province_slug}&minprice={min_p}&maxprice={max_p}&page={page}"
        try:
            r = session.get(url, headers={"User-Agent": user_agent.random}, timeout=20)      
            if r.status_code != 200: break
            
            links = extract_links(r.text) 
            if not links: break 
            
            for link in links:                    
                results.append({"region": region_name, "province": province_slug, "url": link})

                   
            time.sleep(0.3)
            
        except Exception as e:
            terminal_logger.error(f"[ERROR] {province_slug} page {page}: {e}")
            break
            
    return results

def fetch_urls(filepath):

    """Orchestrates a multi-threaded scraping operation across all defined 
    regions and price ranges, aggregates the discovered URLs, removes 
    duplicates, and exports the final list to a CSV file."""
    
    all_data = [] 
    tasks = [(reg, prov, data["name"], p[0], p[1]) for reg, data in GEO_DATA.items() for prov in data["provinces"] for p in PRICE_RANGES]
    
    try:                                             
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:   
            with requests.Session() as session:
                futures = [executor.submit(fetch_data, *task, session) for task in tasks]
                for future in futures:  
                    all_data.extend(future.result())
    except KeyboardInterrupt: # catch the ctrl+C
        terminal_logger.warning("Keyboard interruption.")

    df = pd.DataFrame(all_data)                  
    df = df.drop_duplicates(subset=["url"])

    df.to_csv(filepath, index=False, sep=";", encoding="utf-8-sig")
 
    print(f"Total unique URLs: {len(df)}")

if __name__ == "__main__": 
    pass