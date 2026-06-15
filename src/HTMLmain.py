import requests  # http client used to download html pages
import time  # delay between requests for rate limiting
import json  # used to store structured html dataset
from urllib.parse import urljoin  # normalize relative urls into absolute ones
from bs4 import BeautifulSoup  # html parser for extracting links
from concurrent.futures import ThreadPoolExecutor, as_completed  # send multiple requests at the same time — Imad
from fake_useragent import UserAgent  # gives us random browser identities so the site thinks we are different people each time — Imad

# this generates a new random browser identity each time we call ua.random — Imad
ua = UserAgent()

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

def get_html(url, session=None):
    # if we got a session use it, otherwise just do a normal request — Imad
    requester = session or requests
    try:
        r = requester.get(url, headers={"User-Agent": ua.random}, timeout=10)     # each request gets a different fake browser identity — Imad
        if r.status_code != 200:  # check request success
            return None  # skip invalid responses
        return r.text  # return raw html content
    except:
        return None  # avoid breaking pipeline

# ---------------------------
# Pipeline iterate listing pages, extract property urls, download html pages, store dataset in json format

def run():
    all_links = set()  # global url storage for deduplication

    # keep the connection alive across all requests — Imad
    session = requests.Session()

    for page in range(1, 10):                                                     # loop listing pages, to change!!!
        # each page request uses a different browser identity — Imad
        session.headers.update({"User-Agent": ua.random})
        r = session.get(f"{BASE_URL}&page={page}")                                # fetch html listing page
        if r.status_code != 200:  # validate response
            continue  # skip failed pages

        all_links.update(extract_links(r.text))                                   # extract + merge urls
        time.sleep(1)                                                             # delay to reduce risk of blocking

    print("total links:", len(all_links))                                         # debug total extracted urls

    dataset = []

    # function added for threading, downloads one property and returns url + html — Imad
    def download_one(url):
        html = get_html(url, session=session)
        if html:
            return {"url": url, "html": html}
        return None

    # download 10 properties at the same time instead of one by one — Imad
    with ThreadPoolExecutor(max_workers=10) as task_manager:
        # give all our urls to the pool, it runs download_one on each(task_manager controls the running tasks) — Imad
        tasks_being_done = {task_manager.submit(download_one, url): url for url in all_links}

        # collect results as each download finishes — Imad
        for done_task in as_completed(tasks_being_done):
            result = done_task.result()
            if result:
                dataset.append(result)
                if len(dataset) % 50 == 0:
                    print(f"downloaded {len(dataset)} properties so far...")

    session.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"Done! saved {len(dataset)} properties to {OUTPUT_FILE}")

run()
