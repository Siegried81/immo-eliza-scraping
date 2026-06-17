# import requests
# from bs4 import BeautifulSoup

# def get_immo_data():
    
#   url = """https://immovlan.be/en/real-estate?transactiontypes=for-sale&propertytypes=house,apartment&propertysubtypes=residence,villa,mixed-building,master-house,bungalow,cottage,chalet,mansion,apartment,ground-floor,penthouse,duplex,studio,loft,triplex&islifeannuity=no&noindex=1"""    
    								# User-Agent 
#   headers = {"User-Agent": "SiegExerciceImmo"}
    
#    response = requests.get(url, headers=headers)
    
    								# test status
#    if response.status_code == 200:
#        print("Connexion ok !")
#       soup = BeautifulSoup(response.content, "html.parser")
        
        							# test title to check BS4 with HTML
#       print("Title of the scraped page :", soup.title.string)
#    else:
#        print(f"Error : {response.status_code}")

#if __name__ == "__main__":
#    get_immo_data()


import requests
from bs4 import BeautifulSoup
import time

headers = {"User-Agent": "SiegExerciceImmo"}
                                    # list to store final links
property_links = []
                                    # prepare all urls
urls_to_scrape = []
prop_types = ["house", "apartment"]

for prop_type in prop_types:
    for min_price in range(0, 3000000, 5000):
        max_price = min_price + 5000
        for page in range(1, 10):   # clean loop through 10 pages
            url = f"https://immovlan.be/en/real-estate?transactiontypes=for-sale&propertytypes={prop_type}&islifeannuity=no&noindex=1&minprice={min_price}&maxprice={max_price}&page={page}"
            urls_to_scrape.append(url)


print("Connexion ok, search for links")

                                    # single loop to scrape everything
for url in urls_to_scrape:
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
                                    # find html links tags
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                                    # filter to list detail urls
                if "/detail/" in href and "public-sale" not in href:
                    if href.startswith("/"):
                        complete_url = "https://immovlan.be" + href
                    else:
                        complete_url = href
                    
                                    # no duplicates in links
                    if complete_url not in property_links:
                        property_links.append(complete_url)
            
                                    # single check to stop everything
            if len(property_links) >= 200:
                break
                
                                    # slight anti ban safe delay
            time.sleep(0.1)
            
    except Exception as e:
                                    # skip page if temporary error
        continue

print(f"Nb of links found on this page : {len(property_links)}")

                                    # print final collected urls
for l in property_links[:50]:
    print("-", l)