# Second scrapper Zimmo, goal scrapping url for then another program to take the urls.
# Each province will be equal to a list of link/url that have been scrapped from search url for each region.
# Usually link come in 2 part the url that have all the info encoded in it like the province etc, then at the end "&p=N" N decide which page to load as they be many page exemple:
# https://www.zimmo.be/fr/rechercher/?search=...&p=10
import csv
import json
import time
import requests
import urllib3
import threading

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ua = UserAgent()

OUTPUT_FILE = "province_zimmo_url.json"

# I put one less page than the notes, because the last page can sometimes be empty.
province_search_pages = {
    "Antwerpen": {"url": "https://www.zimmo.be/fr/rechercher/?search=...", "pages": 99},
    "Namur": {"url": "https://www.zimmo.be/fr/rechercher/?search=...", "pages": 10},
    "Wavre_brabant_wallon": {"url": "https://www.zimmo.be/fr/rechercher/?search=...", "pages": 4},
    "Arlon_Luxembourg": {"url": "https://www.zimmo.be/fr/rechercher/?search=...", "pages": 2},
    "Liege": {"url": "https://www.zimmo.be/fr/rechercher/?search=...", "pages": 17},
    "Leuze_en_Hainaut": {"url": "https://www.zimmo.be/fr/rechercher/?search=...", "pages": 1},
    "West_flanders_bruges": {"url": "https://www.zimmo.be/fr/rechercher/?search=...", "pages": 46},
    "Limburg_haselt": {"url": "https://www.zimmo.be/fr/rechercher/?search=...", "pages": 32},
    "Vlaams_Brabant_Leuven": {"url": "https://www.zimmo.be/fr/rechercher/?search=...", "pages": 24},
    "East_Flanders_gent": {"url": "https://www.zimmo.be/fr/rechercher/?search=...", "pages": 54},
}

# global session shared by threads (faster than recreating connections)
session = requests.Session()

# lock to avoid race conditions when writing shared structures
lock = threading.Lock()


def make_page_url(search_url, page_number):
    # take the search url and add the page number before #gallery
    clean_url = search_url.replace("#gallery", "")
    return f"{clean_url}&p={page_number}#gallery"


def get_headers():
    # fake a normal browser so Zimmo gives the real page
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }


def get_property_links_from_page(html):
    # grab every href, keep only Zimmo property pages
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for tag in soup.find_all("a", href=True):
        href = tag.get("href")

        if "/fr/" not in href:
            continue

        if "/a-vendre/" not in href:
            continue

        if "/projet-immobilier/" in href:
            continue

        full_url = urljoin("https://www.zimmo.be", href)
        clean_url = full_url.split("?")[0]
        links.append(clean_url)

    return links


def scrape_province_links(province_name, search_url, total_pages):
    province_links = []

    # each thread handles its own pages
    for page_number in range(1, total_pages + 1):

        page_url = make_page_url(search_url, page_number)
        print(f"{province_name}: page {page_number}/{total_pages}")

        try:
            response = session.get(page_url, headers=get_headers(), timeout=10, verify=False)
        except requests.RequestException:
            print(f"failed page: {page_url}")
            continue

        if response.status_code != 200:
            print(f"status {response.status_code}: {page_url}")
            continue

        page_links = get_property_links_from_page(response.text)

        # thread-safe merge
        with lock:
            province_links.extend(page_links)

        time.sleep(0.2)  # small delay to reduce ban risk

    # remove duplicates but keep order
    return province_name, list(dict.fromkeys(province_links))


def fetching_urls_zimmo(output_file):

    all_province_links = []

    # multithread per province (parallel scraping)
    def worker(item):
        province_name, info = item
        return scrape_province_links(province_name, info["url"], info["pages"])

    with ThreadPoolExecutor(max_workers=10) as executor:

        futures = [
            executor.submit(worker, item)
            for item in province_search_pages.items()
        ]

        for future in as_completed(futures):
            province_name, links = future.result()
            for link in links:
                all_province_links.append({"province": province_name, "url": link})

            print(f"{province_name}: {len(links)} urls collected")

    # save result
    #with open(output_file, "w", encoding="utf-8") as file:
    #   json.dump(all_province_links, file, ensure_ascii=False, indent=2)

    keys = ["province", "url"]
    print(f"saved to {output_file}")
    with open(output_file, "w", newline="", encoding="utf-8") as f:        # File output
        writer = csv.DictWriter(f, fieldnames=keys, delimiter=";")
        writer.writeheader()
        writer.writerows(all_province_links)


if __name__ == "__main__":
    start_time = time.perf_counter()
    print("here")
    fetching_urls_zimmo("province_urls_zimmo.csv")
    print(f"Time spend : {time.perf_counter() - start_time}")