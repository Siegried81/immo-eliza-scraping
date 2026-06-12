import pandas as pd
import time
import random
from random import randint
from bs4 import BeautifulSoup
import requests

time.sleep(random.uniform(1.0, 2.0))

# - Get request object from URL
url = "https://immovlan.be/"
r = requests.get(url)
print(url, r.status_code)
# - Extract the content into a variable using BeautifulSoup
soup = BeautifulSoup(r.content, "html")

# - Get title
for elem in soup.find_all("a", attrs={"class": "meta-title meta-title-link"}):
    if "film" in elem.get("href"):
        titles.append(elem.get("title"))

# - Get movie links
links = []
for elem in soup.find_all("a", attrs={"class": "meta-title meta-title-link"}):
    links.append(elem.get("href"))
    
movie_links = ["http://www.allocine.fr" + elem for elem in links if "film" in elem]

# - Get synopsis
for link in movie_links:
    current_r = requests.get(link)
    current_soup = BeautifulSoup(current_r.content, "html")


    for elem in current_soup.find_all("section", attrs={"id": "synopsis-details"}):
        # Get the text of the synopsis
        for elem2 in elem.find_all("div", attrs={"class":"content-txt"}):
            synopsis.append(elem2.text)


# Check the length of the lists before creating the dataframe
len(titles), len(synopsis), len(movie_links)