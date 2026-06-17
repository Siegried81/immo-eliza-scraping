from bs4 import BeautifulSoup                                                 
import requests                                                               
from concurrent.futures import ThreadPoolExecutor                             

def scrapping(url):                                                           
    """Function scrapping html page from an url"""                            
    try:                                                                      # try-catch for network
        response = requests.get(url, headers={"User-Agent": "max-exercice"}, timeout=10) 
        return BeautifulSoup(response.content, "html.parser")                 # init parser & return
    except Exception as e:                                                    # handle any network err
        print(f"Erreur de connexion pour {url}: {e}")                         
        return None                                                           

def parsing(soup):                                                            # fct to parse html info
    """Function parsing an html page for relevant informations"""            
    if not soup: return None                                                 
    
    try:                                                                      # try-catch for parsing
        property_id = soup.find("div", attrs={"class": "zimmo-code"}).text.split(": ")[1][:-1] # find prop ID
        
        details = soup.find("section", attrs={"id": "main-features"})         # find features section
        lis = details.find_all("li")                                          
        
        price = address = postal_code = city_name = property_type = None      
        livable_surface = total_land_surface = bedroom_count = build_year = peb_category = None # init defaults

        for li in lis:                                                        # iterate through features
            cat = li.find("strong").text if li.find("strong") else None       
            value = li.find("span").text.strip() if li.find("span") else ""   
            
            match cat:                                                        # match feature type
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
                    build_year = int(value) if value.isdigit() else None      
                case "PEB":                                                  
                    peb_category = int(value.split()[0]) if value.split()[0].isdigit() else None 
            
        if not total_land_surface: total_land_surface = livable_surface       
        
        garages_div = soup.find("div", attrs={"class":"col-xs-7 info-name"}, string="Garages") 
        garages_value = 1 if (garages_div and garages_div.find_next_sibling("div").get_text(strip=True) != "0") else 0 

        return {                                                             
            "property_id": property_id, "property_type": property_type, "postal_code": postal_code, 
            "city_name": city_name, "address": address, "price": price, "bedroom_count": bedroom_count, 
            "livable_surface": livable_surface, "total_surface": total_land_surface, 
            "build_year": build_year, "garage": garages_value, "peb_category": peb_category
        }
    except Exception as e:                                                    
        print(f"Erreur lors du parsing: {e}")                                 
        return None                                                           

def process_url(url):                                                         # wrapper for threading
    """Wrapper pour le threading"""                                          
    soup = scrapping(url)                                                     
    return parsing(soup)                                                      

def run_scraper(url_list):                                                    # multithread runner
    """Exécute le scraping en multithread"""                                
    print(f"Début du scraping de {len(url_list)} URLs...")                   
    with ThreadPoolExecutor(max_workers=10) as executor:                   
        results = list(executor.map(process_url, url_list))                   
    
    return [r for r in results if r is not None]                           

if __name__ == "__main__":                                                    
    urls_a_scraper = ["https://www.zimmo.be/url_exemple_1"]                   
    data = run_scraper(urls_a_scraper)                                       
    print(f"Scraping terminé. {len(data)} propriétés récupérées.")           