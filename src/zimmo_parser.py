from bs4 import BeautifulSoup
import requests


def scrapping(url):
    """
    Function scrapping html page from an url
    :param: string of one url
    returns BeautifulSoup object
    """
    response = requests.get(url, headers={"User-Agent": "max-exercice"})
    soup = BeautifulSoup(response.content, "html")
    return soup


def parsing(soup):
    """
    Function parsing an html page for relevant informations
    :param: BeautifulSoup object
    returns a dictionary 
    """
    property_id = soup.find("div", attrs={"class": "zimmo-code"}).text.split(": ")[1][:-1]
    total_land_surface = ""
    details = soup.find("section", attrs={"id": "main-features"})
    lis = details.find_all("li")
    for li in lis:
        cat = li.find("strong")
        if cat: cat = cat.text
        value = li.find("span")
        if value: value = value.text.strip()
        match cat:
            case "Prix":
                price = int(value.replace("€ ", "").replace(".", ""))
            case "Adresse":
                address, rest = value.split(", ")
                postal_code, city_name = rest.split()
            case "Type":
                property_type = "House" if "Maison" in value else "Appartment"
            case "Surf. habitable":
                livable_surface = int(value.split()[0])
            case "Sup. du terrain":
                total_land_surface = int(value.split()[0])
            case "Chambres":
                bedroom_count = int(value)
            case "Construit en":
                try:
                    build_year = int(value)
                except ValueError:
                    build_year = None
            case "PEB":
                try:
                    peb_category = int(value.split()[0])
                except ValueError:
                    peb_category = None
            
    if not total_land_surface:
        total_land_surface = livable_surface
    
    garages_div = soup.find("div", attrs={"class":"col-xs-7 info-name"}, string="Garages")

    if garages_div:
        garages_value = garages_div.find_next_sibling("div", attrs={"class":"col-xs-5 info-value"}).get_text(strip=True)
        if garages_value != "0":
            garages_value = 1
        else:
            garages_value = 0
    else:
        garages_value = 0

    return {"property_id": property_id, "property_type": property_type, "postal_code": postal_code, "city_name": city_name, "address": address, "price": price, "bedroom_count": bedroom_count, "livable_surface": livable_surface, "total_surface": total_land_surface, "build_year": build_year, "garage": garages_value, "peb_category": peb_category}

