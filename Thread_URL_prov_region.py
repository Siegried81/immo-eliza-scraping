import requests                                   
import time                                       
import pandas as pd      
import os                                         
from bs4 import BeautifulSoup                     
from concurrent.futures import ThreadPoolExecutor 


HEADERS = {"User-Agent": "Mozilla/5.0 SiegExerciceImmo"}    # I'm not a bot
BASE_URL = "https://immovlan.be/en/real-estate?transactiontypes=for-sale&propertytypes=house,apartment&islifeannuity=no&includenewconstruction=no&noindex=1"

                                                  # dict mapping regions to their respective provinces
GEO_DATA = {
    "bruxelles": {"name": "Bruxelles-Capitale", "provinces": ["brussels"]},
    "flandre": {"name": "Flandre", "provinces": ["antwerp", "limburg", "east-flanders", "flemish-brabant", "west-flanders"]},
    "wallonie": {"name": "Wallonie", "provinces": ["hainaut", "liege", "luxembourg", "namur", "brabant-wallon"]}
}

MAX_PAGES = 200        
DELAY = 0.5
MAX_WORKERS = 10                                  # max nb of threads running simultaneously

def extract_links(html):
    """fct to parse HTML content and extract property detail links."""
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

def fetch_data(region_slug, province_slug, region_name):
    """fct executed by threads to scrape a specific province."""
    session = requests.Session()                  # persistent session for efficient networking
    session.headers.update(HEADERS)               # apply defined headers to the session
    results = []                                  # local list to collect data for this specific thread
        
    for page in range(1, MAX_PAGES + 1):
                                                  # URL with region, province & page nb filters
        url = f"{BASE_URL}&regions={region_slug}&provinces={province_slug}&page={page}"
        try:
            r = session.get(url, timeout=20)      # get request
            if r.status_code != 200: break
            
            links = extract_links(r.text) 
            if not links: break 
            
            for link in links:
                results.append({"region": region_name, "province": province_slug, "url": link})
            
            time.sleep(DELAY)
            
        except Exception as e:
            print(f"[ERROR] {province_slug} page {page}: {e}")
            break
            
    return results

def run():
    all_data = []
                                                  # list of tasks for each province in the hierarchy
    tasks = [(reg, prov, data["name"]) for reg, data in GEO_DATA.items() for prov in data["provinces"]]
    
    try:                                             
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:   # tasks in //
            futures = [executor.submit(fetch_data, reg, prov, name) for reg, prov, name in tasks]
            for future in futures:  
                all_data.extend(future.result())
    except KeyboardInterrupt:
                                                 # catch the ctrl+C
        print("Keyboard interruption.")

    df = pd.DataFrame(all_data)                   # convert list of dic into DF
    df = df.drop_duplicates(subset=["url"])
    
    df.to_csv(save_path, index=False, sep=";", encoding="utf-8-sig")
 
    print(f"Total unique URLs: {len(df)}")

if __name__ == "__main__": 
    run()