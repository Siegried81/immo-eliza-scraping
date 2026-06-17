import requests  
from bs4 import BeautifulSoup 
import csv 
import re  
import time  
import threading  
from concurrent.futures import ThreadPoolExecutor  
import unicodedata

# --------------------------------------------
# Global configuration: defines scraping settings, output file, and shared state used across threads

HEADERS = {"User-Agent": "Mozilla/5.0 SiegExerciseImmo"}                # I'm not a bot
BASE_URL = "https://immovlan.be/en/real-estate?transactiontypes=for-sale&propertytypes=house,apartment&islifeannuity=no&noindex=1"  # listing page URL
OUTPUT_FILE = "MLscraping_clean.csv"  # final dataset output file

csv_lock = threading.Lock()                                             # lock to prevent concurrent writes in CSV
seen_ids = set()                                                        # stores property IDs to avoid duplicates


# ---------------------------------------------
# Text cleaning functions: normalize raw HTML text into clean ML-ready values

def normalize(txt):                                                     # function to normalize text
    if not txt:                                                         # if text is empty or None: return None
        return None
    txt = unicodedata.normalize("NFKC", txt)                            # normalize unicode characters
    return " ".join(txt.split()).strip()                                # remove extra whitespace and clean string


def clean_int(x):                                                       # function to extract integer from text
    if not x:  
        return None  
    x = re.sub(r"[^\d]", "", str(x))                                    # remove everything except digits
    return int(x) if x else None                                        # convert to int if valid


def fix_url(href):                                                      # function to normalize URL
    if not href:  
        return None 
    return href if href.startswith("http") else "https://immovlan.be" + href  # ensure absolute URL


# ---------------------------------------------
# Property id extraction: extracts unique ID for deduplication & dataset integrity

def extract_property_id(soup):                                          # extract property ID from HTML
    ref = soup.find(string=re.compile("Immovlan ref"))                  # locate label in HTML
    if ref:  # if found
        try:  # try extraction
            return ref.find_next().get_text(strip=True)                 # get value next to label
        except:                                                         # fallback if structure changes
            return None  
    return None                                                         # return None if not found


# ------------------------------------------
# Location extraction: extracts postal code and city

def extract_location(url, soup):  # extract location info
    m = re.search(r"/for-sale/(\d{4})/([^/]+)/", url.lower())           # regex on URL
    if m:  # if pattern found
        return m.group(1), m.group(2).replace("-", " ").title()         # return postal + city

    loc = soup.select_one("p.detail__header_location")                  # HTML selector
    if loc:  # if HTML exists
        txt = normalize(loc.get_text())    
        m = re.search(r"(\d{4})\s+(.+)", txt)                           # extract postal + city
        if m:  
            return m.group(1), m.group(2)                               # return structured values

    return None, None                                                   # if nothing found


# ---------------------------------------------
# Region mapping: converts postal codes into belgian regions and provinces

def get_region(postal):                                                  # map postal to region
    if not postal:  
        return None  
    p = int(postal)  

    if 1000 <= p <= 1299:  
        return "Brussels"
    if 1300 <= p <= 7999:  
        return "Wallonia"
    if 8000 <= p <= 9999:  
        return "Flanders"
    return None                                                           # fallback


def get_province(postal):                                                 # map postal to province
    if not postal:  
        p = int(postal)  

    if 1000 <= p <= 1299: return "Brussels"  
    if 1300 <= p <= 1499: return "Walloon Brabant"  #
    if 1500 <= p <= 1999: return "Flemish Brabant"
    if 2000 <= p <= 2999: return "Antwerp"
    if 3000 <= p <= 3999: return "Limburg"
    if 4000 <= p <= 4999: return "Liege"
    if 5000 <= p <= 5999: return "Namur"
    if 6000 <= p <= 7999: return "Hainaut"
    if 8000 <= p <= 8999: return "West Flanders"
    if 9000 <= p <= 9999: return "East Flanders"

    return None  # unknown case


# -------------------------------------------------------
# Property type detection: detects apartment or house from URL

def property_type(url):                                                     # classify property type
    u = url.lower()                                                         # normalize 

    if "apartment" in u or "studio" in u or "duplex" in u:   
        return "apartment"  
    return "house"                                                          # default type


# ---------------------------------------------------------
# Feature extraction: extracts binary features from listing text

def extract_features(text):                                                  # extract property features
    t = text.lower()  

    return {                                                                 # feature dictionary
        "garage": 1 if "garage" in t or "parking" in t else 0, 
        "terrace": 1 if "terrace" in t or "terrasse" in t else 0,  
        "garden": 1 if "garden" in t or "jardin" in t else 0, 
        "furnished": 1 if "furnished" in t else 0,  
        "cellar": 1 if "cellar" in t or "basement" in t else 0,  
        "attic": 1 if "attic" in t or "loft" in t else 0,  
        "veranda": 1 if "veranda" in t else 0,   
        "swimming_pool": 1 if "pool" in t else 0,  
    }


# ------------------------------------------------------------
# bedrooms & bathrooms: extracts numeric values from HTML list items

def extract_numbers(soup):                                                    # extract beds and baths
    beds = baths = None                                                         
    for li in soup.select("li"):  
        t = li.get_text(" ", strip=True).lower()

        if "bedroom" in t or "chambre" in t:  
            m = re.search(r"\d+", t)  
            if m:  # if found
                beds = int(m.group())  

        if "bath" in t:  # detect bathrooms
            m = re.search(r"\d+", t)   
            if m:  # if found
                baths = int(m.group())  

    return beds, baths                                                          # tuple


# ----------------------------------------------------------
#  extraction: extracts property URLs 

def extract_links(soup):                                                        # extract listing links
    return list(set(                                                            # remove duplicates
        fix_url(a.get("href"))  
        for a in soup.select('a[href*="/en/detail/"]') 
        if a.get("href")                                                        # ensure valid href
    ))


# ------------------------------------------------------------
# Scraping core: downloads page and extracts structured dataset row

def scrape_detail(url):                                                         # scrape single property page
    try:                                                                        # error handling block
        r = requests.get(url, headers=HEADERS, timeout=10)                      # HTTP request
        if r.status_code != 200:                                                # check response
            return                                                              # skip invalid page

        soup = BeautifulSoup(r.text, "html.parser")                             # parse HTML

        prop_id = extract_property_id(soup)                                     # extract ID
        if prop_id in seen_ids:                                                 # duplicate check
            return                                                              # skip it
        seen_ids.add(prop_id)  

        price = clean_int(soup.select_one("span.detail__header_price_data"))    # extract price

        postal, city = extract_location(url, soup)  
        region = get_region(postal) 
        province = get_province(postal)  

        ptype = property_type(url)  

        text = soup.get_text(" ")                                                # full text extraction

        beds, baths = extract_numbers(soup)      
        features = extract_features(text)                                        # extract binary features

        row = [                                                                  # final dataset row
            prop_id,  
            url,  
            price,  
            ptype,  
            postal,  
            city,  
            region,  
            province, 
            beds,  
            baths,  
            features["garage"],  
            features["terrace"],  
            features["garden"],  
            features["furnished"],  
            features["cellar"],  
            features["attic"], 
            features["veranda"],  
            features["swimming_pool"],  
        ]

        with csv_lock:                                                          # thread-safe writing
            with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f, delimiter=";").writerow(row) 

    except Exception as e:  
        print("error:", url, e)  


#----------------------------------------------------------
# csv initialization: creates file and defines schema

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    csv.writer(f, delimiter=";").writerow([ 
        "property_id",
        "url",
        "price",
        "property_type",
        "postal_code",
        "city",
        "region",
        "province",
        "bedrooms",
        "bathrooms",
        "garage",
        "terrace",
        "garden",
        "furnished",
        "cellar",
        "attic",
        "veranda",
        "swimming_pool",
    ])


# ----------------------------------------------------------
# pipeline execution: collects links then scrapes all properties in parallel

def run():                                                                  # main pipeline
    all_links = set()  # store all urls

    for page in range(1, 10):  # iterate pages
        r = requests.get(f"{BASE_URL}&page={page}", headers=HEADERS)        # fetch page
        if r.status_code != 200:  
            continue  

        soup = BeautifulSoup(r.text, "html.parser") 
        all_links.update(extract_links(soup))  
        time.sleep(1)  # delay

    print("total links:", len(all_links))  

    with ThreadPoolExecutor(max_workers=10) as ex:                          # multithreading
        list(ex.map(scrape_detail, all_links))                              # scrape all urls


if __name__ == "__main__":                                                  # python entry point
    run()  
