# my solo scrapping practice before the real group project

from bs4 import BeautifulSoup
import requests
import pandas as pd

# the website url split into pieces so its easy to change later
root = "https://immovlan.be/en"
endpoint = "real-estate"
params = "transactiontypes=for-sale&propertytypes=house,apartment&isnewconstruction=no&islifeannuity=no&noindex=1"

# grab the first search results page (page of listings, using the search url as a param so it go throught the search page )
response = requests.get(f"{root}/{endpoint}?{params}", headers={"User-Agent": "imad-training"})
print(f"Search page status: {response.status_code}")

# we beautiful soup our htlm so it make become something we can use and take info from later
soup = BeautifulSoup(response.content, "html.parser")

# every property card seems to have an h2 title with a link inside it, and in it we get the href which in a lot of website is a url.
link_tags = soup.select("h2 a")
property_links = [tag.get("href") for tag in link_tags]
print(f"Found {len(property_links)} property links on page 1")#we print a nice message to say how much property we found

# now we try again with more page than 1.using a session so the connection stays open between requests as we are making multible requests it's a waste to not use it
with requests.Session() as session:
    session.headers.update({"User-Agent": "imad-training"})

    for page_num in range(2, 4):
        # same url but we add the page number to it
        page_params = f"transactiontypes=for-sale&propertytypes=house,apartment&isnewconstruction=no&islifeannuity=no&page={page_num}&noindex=1"
        page_response = session.get(f"{root}/{endpoint}?{page_params}")
        page_soup = BeautifulSoup(page_response.content, "html.parser")

        # same thing of getting the href in the H2 a.
        page_link_tags = page_soup.select("h2 a")
        for tag in page_link_tags:
            property_links.append(tag.get("href"))

print(f"Total property links collected: {len(property_links)}")


# function that visits one property page and pulls out all the info it can find
def scrape_one_property(url):
    # ask the server for the property page
    response = requests.get(url, headers={"User-Agent": "imad-training"})

    # if the page didnt load skip it in case
    if response.status_code != 200:
        print(f"Failed to load: {url} (status {response.status_code})")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    #A dictionary to store everything we find about this property
    data = {"url": url}

    # taking the city and postal code
    city_tag = soup.find("span", attrs={"class": "city-line"})
    if city_tag:
        data["location"] = city_tag.text.strip()

    # Taking the price
    price_tag = soup.find("span", attrs={"class": "detail__header_price_data"})
    if price_tag:
        data["price"] = price_tag.text.strip()

    # Take stuff from the highlight boxes (bedrooms, surface, garage etc)
    highlights = soup.find_all("li", attrs={"class": "property-highlight"})
    # sometimes they are in divs instead of li
    if not highlights:
        highlights = soup.find_all("div", attrs={"class": "property-highlight"})

    for h in highlights:
        # clean up the text
        text = " ".join(h.text.split()).replace(" ", " ")
        # try to figure out what this highlight is about and store it
        if "Bedroom" in text:
            data["bedrooms"] = text
        elif "m²" in text and "surface" not in data:
            data["surface"] = text
        elif "Bathroom" in text:
            data["bathrooms"] = text
        elif "Garage" in text:
            data["garages"] = text

    #Take the detailed info section
    more_info = soup.find("div", attrs={"class": "general-info-wrapper"})
    if more_info:
        # the info is in pairs: h4 = label, p = value
        labels = [h.text.replace("\n", "").strip() for h in more_info.find_all("h4")]
        values = [p.text.replace("\n", "").strip() for p in more_info.find_all("p")]

        # zip them together into our dictionary
        for label, value in zip(labels, values):
            data[label] = value

    return data


# now visit each property and collect the data only doing the first 5 for testing
all_properties = []
test_links = property_links[:5]

for i, link in enumerate(test_links):
    print(f"Scraping property {i + 1}/{len(test_links)}: {link}")
    result = scrape_one_property(link)

    # if we got data back add it to our list
    if result:
        all_properties.append(result)

# turn everything into a dataframe
df = pd.DataFrame(all_properties)
print(f"\nDone! Got {len(df)} properties with {len(df.columns)} columns")
print(df.head())

# save it to a csv
df.to_csv("imad_test_scrape.csv", index=False)
print("Saved to imad_test_scrape.csv")
