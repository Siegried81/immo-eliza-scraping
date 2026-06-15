import requests  # http client used to download html pages
import time  # delay between requests for rate limiting
import json  # used to store structured html dataset
from urllib.parse import urljoin  # normalize relative urls into absolute ones
from bs4 import BeautifulSoup  # html parser for extracting links

HEADERS = {"User-Agent": "Mozilla/5.0 SiegExerciseImmo"}                        # I'm not a bot

BASE_URL = "https://immovlan.be/en/real-estate?transactiontypes=for-sale&propertytypes=house,apartment&islifeannuity=no&includenewconstruction=no&noindex=1"  # listing endpoint

OUTPUT_FILE = "HTMLscraping.json"                                         

# ---------------------------
# extract property links from listing html
# parses search result page - extracts detail page urls only - returns deduplicated set

def extract_links(html):
    soup = BeautifulSoup(html, "html.parser")                                   # parse listing page html
    links = set()  # store unique urls

    for a in soup.select('a[href*="/en/detail/"]'):                             # filter only property links
        href = a.get("href")                                                    # extract raw href from html tag
        if href:                                                                # ensure href exists
            links.add(urljoin("https://immovlan.be", href))                     # convert to absolute url

    return links  

# ---------------------------
# Download html page: fetches raw html from a property url, returns full page source as string

def get_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)                       # http request with timeout
        if r.status_code != 200:  # check request success
            return None  # skip invalid responses
        return r.text  # return raw html content
    except:
        return None  # avoid breaking pipeline

# ---------------------------
# Pipeline iterate listing pages, extract property urls, download html pages, store dataset in json format

def run():
    all_links = set()  # global url storage for deduplication

    for page in range(1, 10):                                                     # loop listing pages, to change!!!
        r = requests.get(f"{BASE_URL}&page={page}", headers=HEADERS)              # fetch html listing page
        if r.status_code != 200:  # validate response
            continue  # skip failed pages

        all_links.update(extract_links(r.text))                                   # extract + merge urls
        time.sleep(1)                                                             # delay to reduce risk of blocking

    print("total links:", len(all_links))                                         # debug total extracted urls

    dataset = []  

    for url in all_links:                                                         # iterate all property urls
        html = get_html(url)                                                      # download html page

        if html:                                                                  # ensure valid html exists
            dataset.append({  
                "url": url,  
                "html": html 
            })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:  
        json.dump(dataset, f, ensure_ascii=False, indent=2)  

    print("Done")  

run()  