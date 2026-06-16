#Second scrapper Zimmo, goal scrapping url for then another program to take the urls.
#Each province will be equal to a list of link/url that have been scrapped from search url for each region.
#Usually link come in 2 part the url that have all the info encoded in it like the province etc, then at the end "&p=N" N decide which page to load as they be many page exemple: https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJwbGFjZUlkIjp7ImluIjpbMTEzXX0sImNhdGVnb3J5Ijp7ImluIjpbIkhPVVNFIiwiQVBBUlRNRU5UIl19fSwic29ydGluZyI6W3sidHlwZSI6IlJBTktJTkdfU0NPUkUiLCJvcmRlciI6IkRFU0MifV0sInBhZ2luZyI6eyJmcm9tIjoxODUsInNpemUiOjIxfX0%3D&p=10
#As you can see at the end there is a &p=

import json
import time
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ua = UserAgent()

OUTPUT_FILE = "province_zimmo_url.json"

# I put one less page than the notes, because the last page can sometimes be empty.
province_search_pages = {
    "Antwerpen": {
        "url": "https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJwbGFjZUlkIjp7ImluIjpbMTEzXX0sImNhdGVnb3J5Ijp7ImluIjpbIkhPVVNFIiwiQVBBUlRNRU5UIl19fSwic29ydGluZyI6W3sidHlwZSI6IlJBTktJTkdfU0NPUkUiLCJvcmRlciI6IkRFU0MifV0sInBhZ2luZyI6eyJmcm9tIjoxODUsInNpemUiOjIxfX0%3D",
        "pages": 99,
    },
    "Namur": {
        "url": "https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJjYXRlZ29yeSI6eyJpbiI6WyJIT1VTRSIsIkFQQVJUTUVOVCJdfSwicGxhY2VJZCI6eyJpbiI6WzU1Nl19fX0%3D",
        "pages": 10,
    },
    "Wavre_brabant_wallon": {
        "url": "https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJjYXRlZ29yeSI6eyJpbiI6WyJIT1VTRSIsIkFQQVJUTUVOVCJdfSwicGxhY2VJZCI6eyJpbiI6WzMxOV19fX0%3D",
        "pages": 4,
    },
    "Arlon_Luxembourg": {
        "url": "https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJjYXRlZ29yeSI6eyJpbiI6WyJIT1VTRSIsIkFQQVJUTUVOVCJdfSwicGxhY2VJZCI6eyJpbiI6WzU3OV19fX0%3D",
        "pages": 2,
    },
    "Liege": {
        "url": "https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJjYXRlZ29yeSI6eyJpbiI6WyJIT1VTRSIsIkFQQVJUTUVOVCJdfSwicGxhY2VJZCI6eyJpbiI6WzE1OV19fX0%3D",
        "pages": 17,
    },
    "Leuze_en_Hainaut": {
        "url": "https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJjYXRlZ29yeSI6eyJpbiI6WyJIT1VTRSIsIkFQQVJUTUVOVCJdfSwicGxhY2VJZCI6eyJpbiI6WzM3OV19fX0%3D",
        "pages": 1,
    },
    "West_flanders_bruges": {
        "url": "https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJjYXRlZ29yeSI6eyJpbiI6WyJIT1VTRSIsIkFQQVJUTUVOVCJdfSwicGxhY2VJZCI6eyJpbiI6WzI1Nl19fX0%3D",
        "pages": 46,
    },
    "Limburg_haselt": {
        "url": "https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJjYXRlZ29yeSI6eyJpbiI6WyJIT1VTRSIsIkFQQVJUTUVOVCJdfSwicGxhY2VJZCI6eyJpbiI6WzMzMzFdfX19",
        "pages": 32,
    },
    "Vlaams_Brabant_Leuven": {
        "url": "https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJjYXRlZ29yeSI6eyJpbiI6WyJIT1VTRSIsIkFQQVJUTUVOVCJdfSwicGxhY2VJZCI6eyJpbiI6WzIyNl19fX0%3D",
        "pages": 24,
    },
    "East_Flanders_gent": {
        "url": "https://www.zimmo.be/fr/rechercher/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJjYXRlZ29yeSI6eyJpbiI6WyJIT1VTRSIsIkFQQVJUTUVOVCJdfSwicGxhY2VJZCI6eyJpbiI6WzU4MF19fX0%3D",
        "pages": 54,
    },
}


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


def scrape_province_links(province_name, search_url, total_pages, session):
    province_links = []

    for page_number in range(1, total_pages + 1):
        page_url = make_page_url(search_url, page_number)
        print(f"{province_name}: page {page_number}/{total_pages}")

        try:
            response = session.get(page_url, headers=get_headers(), timeout=20, verify=False)
        except requests.RequestException:
            print(f"failed page: {page_url}")
            continue

        if response.status_code != 200:
            print(f"status {response.status_code}: {page_url}")
            continue

        page_links = get_property_links_from_page(response.text)
        province_links.extend(page_links)
        time.sleep(1)

    # remove duplicates but keep the same order
    return list(dict.fromkeys(province_links))


def run():
    all_province_links = {}

    with requests.Session() as session:
        for province_name, info in province_search_pages.items():
            links = scrape_province_links(
                province_name,
                info["url"],
                info["pages"],
                session,
            )

            all_province_links[province_name] = links
            print(f"{province_name}: {len(links)} urls collected")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(all_province_links, file, ensure_ascii=False, indent=2)

    print(f"saved to {OUTPUT_FILE}")


run()
