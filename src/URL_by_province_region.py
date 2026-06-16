import requests                                              # http requests
import time                                                  # delay (anti-ban)
import pandas as pd                                          # dataframe + dedup + csv export
from bs4 import BeautifulSoup                                # html parsing

HEADERS = {"User-Agent": "Mozilla/5.0 SiegExerciseImmo"}     # fake browser header

BASE_URL = "https://immovlan.be/en/real-estate?transactiontypes=for-sale&propertytypes=house,apartment&islifeannuity=no&includenewconstruction=no&noindex=1"  # base listing url

# PROVINCES = slug -> display name
PROVINCES = {
    "antwerp": "Anvers",
    "limburg": "Limbourg",
    "east-flanders": "Flandre-Orientale",
    "flemish-brabant": "Brabant-Flamand",
    "west-flanders": "Flandre-Occidentale",
    "brussels": "Bruxelles",
    "hainaut": "Hainaut",
    "liege": "Liège",
    "luxembourg": "Luxembourg",
    "namur": "Namur",
    "brabant-wallon": "Brabant Wallon"
}

MAX_PAGES = 200                                              # safety cap per region
DELAY = 0.5                                                  # request delay


def extract_links(html):                                     # extract property urls
    soup = BeautifulSoup(html, "html.parser")                # parse html
    links = []                                               # store urls

    for a in soup.select('a[href*="/en/detail/"]'):          # select property cards
        href = a.get("href")                                 # get link
        if href:
            if href.startswith("/"):                         # normalize relative url
                href = "https://immovlan.be" + href
            links.append(href)                               # add url

    return links


def scrape_by_province(session):                               # scrape all regions
    df = pd.DataFrame(columns=["level", "region", "url"])    # result dataframe

    for slug, name in PROVINCES.items():                       # loop regions
        print(f"\n===== PROVINCES: {name} =====")

        prev = len(df)                                       # previous size tracker

        for page in range(1, MAX_PAGES + 1):                 # pagination loop
            url = f"{BASE_URL}&provinces={slug}&page={page}"

            try:
                r = session.get(url, timeout=15)             # http request
                if r.status_code != 200:                     # stop if invalid page
                    break

                links = extract_links(r.text)                # extract urls
                if not links:                                # stop if empty page
                    break

                df_new = pd.DataFrame({                      # temp df
                    "level": "region",
                    "region": name,
                    "url": links
                })

                df = pd.concat([df, df_new], ignore_index=True)  # append
                df = df.drop_duplicates(subset=["url"])          # deduplicate

                current = len(df)                             # current total

                print(f"{name:<18} | page {page:<3} | found {len(links):<3} | total {current}")

                if current == prev:                          # no growth -> stop
                    print("No growth → stop region")
                    break

                prev = current                                # update tracker
                time.sleep(DELAY)                             # sleep

            except KeyboardInterrupt:                         # allow CTRL+C
                raise
            except Exception as e:                            # error handling
                print(f"Error {name} page {page}: {e}")
                break

    return df

def run():                                                 # main runner

    session = requests.Session()                           # session for speed
    session.headers.update(HEADERS)                        # set headers

    try:
        df_province = scrape_by_province(session)   

    except KeyboardInterrupt:                              # manual stop
        print("\nStopped manually")
        return

    df_province.to_csv("immo_by_province.csv", index=False, sep=";", encoding="utf-8-sig")

    print(f"DONE PROVINCE → {len(df_province)} rows")


if __name__ == "__main__":
    run()
