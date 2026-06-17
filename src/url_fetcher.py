from bs4 import BeautifulSoup                     
from concurrent.futures import ThreadPoolExecutor 
from fake_useragent import UserAgent   
import logging                             
import pandas as pd      
import requests                                   
import time                                       


# this generates a new random browser identity each time we call ua.random
user_agent = UserAgent()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://immovlan.be/en/real-estate?transactiontypes=for-sale&propertytypes=house,apartment&islifeannuity=no&includenewconstruction=no&noindex=1"

# We add price ranges to break the site's limit and get more results
PRICE_RANGES = [
    (0, 200000), (200001, 300000), (300001, 400000), 
    (400001, 500000), (500001, 750000), (750001, 1000000), (1000001, 99999999)
]

                                                  # dict mapping regions to their respective provinces
GEO_DATA = {
    "bruxelles": {"name": "Bruxelles-Capitale", "provinces": ["brussels"]},
    "flandre": {"name": "Flandre", "provinces": ["antwerp", "limburg", "east-flanders", "vlaams-brabant", "west-flanders"]},
    "wallonie": {"name": "Wallonie", "provinces": ["hainaut", "liege", "luxembourg", "namur", "brabant-wallon"]}
}

MAX_PAGES = 50
MAX_WORKERS = 10                                  # max nb of threads running simultaneously

def extract_links(html):
    # fct to parse HTML content and extract property detail links
    if not html: return []                        # if HTML empty, return an empty list
    soup = BeautifulSoup(html, "html.parser")     # initialize the HTML parser
    links = []
    for a in soup.select('a[href*="/en/detail/"]'): # find all links pointing to property details
        href = a.get("href")                      # retrieve 'href' attribute from the anchor tag
        if href:                                  
            if href.startswith("/"):              # if link exist, convert it to an absolute URL
                href = "https://immovlan.be" + href
            links.append(href)                    # append the full URL to the list
    return list(set(links))                       # return unique URLs by converting to a set

def fetch_data(region_slug, province_slug, region_name, min_p, max_p, session):
    # fct executed by threads to scrape a specific province
    #session = requests.Session()                  # persistent session for efficient networking
    results = []                                  # local list to collect data for this specific thread
    logger.info(f"Threader scraping in {province_slug} between {min_p} € and {max_p} €")
    for page in range(1, MAX_PAGES + 1):
                                                  # URL with region, province & page nb filters
        url = f"{BASE_URL}&regions={region_slug}&provinces={province_slug}&minprice={min_p}&maxprice={max_p}&page={page}"
        try:
            r = session.get(url, headers={"User-Agent": user_agent.random}, timeout=20)      # get request
            if r.status_code != 200: break
            
            links = extract_links(r.text) 
            if not links: break 
            
            for link in links:                    # iterate through links & add it
                results.append({"region": region_name, "province": province_slug, "url": link})

                   
            time.sleep(0.2)
            
        except Exception as e:
            logger.info(f"[ERROR] {province_slug} page {page}: {e}")
            break
            
    return results

def fetch_urls(filepath):
    all_data = [] # list of tasks for each province in the hierarchy
    tasks = [(reg, prov, data["name"], p[0], p[1]) for reg, data in GEO_DATA.items() for prov in data["provinces"] for p in PRICE_RANGES]
    
    try:                                             
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:   # tasks in //
            with requests.Session() as session:
                futures = [executor.submit(fetch_data, *task, session) for task in tasks]
                for future in futures:  
                    all_data.extend(future.result())
    except KeyboardInterrupt: # catch the ctrl+C
        #print("Keyboard interruption.")
        logger.info("Keyboard interruption.")

    df = pd.DataFrame(all_data)                   # convert list of dic into DF
    df = df.drop_duplicates(subset=["url"])

    df.to_csv(filepath, index=False, sep=";", encoding="utf-8-sig")
 
    print(f"Total unique URLs: {len(df)}")

if __name__ == "__main__": 
    start_time = time.perf_counter()
    filepath = "../data/url_by_province.csv"
    fetch_urls(filepath)
    print(f"Time spent : {time.perf_counter() - start_time} seconds.")