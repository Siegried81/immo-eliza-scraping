import csv
import requests
import threading
import time
import urllib3

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ua = UserAgent()

OUTPUT_FILE = "province_zimmo_url.json"


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


session = requests.Session()

# lock to avoid race conditions when writing shared structures
lock = threading.Lock()


def make_page_url(search_url, page_number):
    """
    Function to add a page number to an url
    :param: string of url
    :param: string of page number
    Returns a string for the new url
    """
    clean_url = search_url.replace("#gallery", "")
    return f"{clean_url}&p={page_number}#gallery"


def get_headers():
    """
    Function making random headers for a requests
    Returns a dictionary
    """
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }


def get_property_links_from_page(html):
    """
    Function taking every links targeting property pages
    :param: an html
    Returns a list of links
    """
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
    """
    Function scraping links by province
    :param: string province name
    :param: string url
    :param: integer number of pages
    Returns a tuble (string(province name), list of links)
    """
    province_links = []

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

        time.sleep(0.2) 

    # remove duplicates but keep order
    return province_name, list(dict.fromkeys(province_links))


def fetching_urls_zimmo(output_file):
    """
    Function principal for fetching urls
    :param: string for output_file path
    Outputs a csv file with a province and an url per line
    """
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

    keys = ["province", "url"]
    print(f"saved to {output_file}")
    with open(output_file, "w", newline="", encoding="utf-8") as f:        
        writer = csv.DictWriter(f, fieldnames=keys, delimiter=";")
        writer.writeheader()
        writer.writerows(all_province_links)

if __name__ == "__main__":
    pass