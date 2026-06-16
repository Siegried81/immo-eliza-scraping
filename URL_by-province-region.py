import requests                                                  # HTTP requests
import time                                                      # delays between requests
import pandas as pd                                              # dataframe + CSV export
from bs4 import BeautifulSoup                                    # HTML parser

HEADERS = {
    "User-Agent": "Mozilla/5.0 SiegExerciseImmo"                 # fake browser header
}

BASE_URL = (
    "https://immovlan.be/en/real-estate"                         # listing endpoint
    "?transactiontypes=for-sale"
    "&propertytypes=house,apartment"
    "&islifeannuity=no"
    "&includenewconstruction=no"
    "&noindex=1"
)

PROVINCES = {                                                    # province slug -> display name
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
    "walloon-brabant": "Brabant-Wallon"
}

MAX_PAGES = 5                                                    # pages to test
DELAY = 0.5                                                      # anti-ban delay


def extract_links(html):                                         # extract property URLs

    soup = BeautifulSoup(html, "html.parser")                    # parse HTML

    links = []                                                   # store URLs

    for a in soup.select('a[href*="/en/detail/"]'):              # select property anchors

        href = a.get("href")                                     # get href value

        if href:

            if href.startswith("/"):                             # build absolute URL
                href = "https://immovlan.be" + href

            links.append(href)                                   # add URL

    return links                                                 # return page URLs


def run():

    session = requests.Session()                                 # persistent session
    session.headers.update(HEADERS)                              # attach headers

    df_all = pd.DataFrame(columns=["province", "url"])           # global dataframe

    for slug, name in PROVINCES.items():                         # loop provinces

        print(f"\n===== {name} =====")                           # province title
        print(f"SLUG = {slug}")                                  # debug slug

        previous_total = len(df_all)                             # growth tracker

        for page in range(1, MAX_PAGES + 1):                     # loop pages

            url = f"{BASE_URL}&provinces={slug}&page={page}"     # build URL

            print(url)                                           # debug URL

            try:

                r = session.get(url, timeout=15)                 # request page

                print("Status:", r.status_code)                  # debug status

                if r.status_code != 200:                         # invalid response
                    break

                links = extract_links(r.text)                    # extract URLs

                print("Links found:", len(links))                # debug count

                if not links:                                    # no data found
                    print("No results → stop.")
                    break

                df_new = pd.DataFrame({                          # temp dataframe
                    "province": [name] * len(links),
                    "url": links
                })

                df_all = pd.concat(                              # append data
                    [df_all, df_new],
                    ignore_index=True
                )

                df_all = df_all.drop_duplicates(                 # remove duplicates
                    subset=["url"]
                )

                current_total = len(df_all)                      # current size

                print(
                    f"{name:<20} | "
                    f"page {page:<3} | "
                    f"found {len(links):<3} | "
                    f"total {current_total}"
                )                                                # progress log

                if current_total == previous_total:              # no new data
                    print("No new unique data → stop.")
                    break

                previous_total = current_total                   # update tracker

                time.sleep(DELAY)                                # wait

            except Exception as e:

                print(f"Error: {e}")                             # show error
                break

    df_all.to_csv(                                               # export CSV
        "debug_provinces.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print("\nUnique provinces found:")                           # province list
    print(sorted(df_all["province"].unique()))

    print("\nCount by province:")                                # rows by province
    print(df_all["province"].value_counts())

    print(f"\nDONE → {len(df_all)} unique properties")           # final count


if __name__ == "__main__":                                       # script entrypoint
    run()                                                        # launch scraper