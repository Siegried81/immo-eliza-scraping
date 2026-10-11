
class Interests_parser():
    """
    Module parsing a html page in the form of a BeautifullSoup to return a 
    dictionary of three relevant points of interest near a property.
    """
    def __init__(self):
        pass
    
    def parsing(self, soup):
        """
        Method making the dictionary, all values iniated as None then attempt to fill them using other methods
        :param: a BeautifullSoup
        returns a dictionary
        """
        points_of_interest = {"Preschool_distance": None, "Train_station_distance": None, "Supermarket_distance": None}
        for i in range(1, 4):
            # Taking the first three tabs of the 'Point of Interest' section
            tab = soup.find("div", attrs={"id": f"tabs-{i}"})
            if tab:
                if i == 1:
                    points_of_interest["Preschool_distance"] = self.parsing_preschool(tab)
                elif i == 2:
                    points_of_interest["Train_station_distance"] = self.parsing_train_station(tab)
                elif i == 3:
                    points_of_interest["Supermarket_distance"] = self.parsing_supermarket(tab)
        
        return points_of_interest

    def parsing_preschool(self, tab):
        """
        Method finding the distance to the nearest preschool
        :param: a part of a BeautifullSoup
        returns an integer
        """
        #list of sub-titles
        tab_titles = [elem.text.strip() for elem in tab.find_all("h3")]
        if not "Preschools" in tab_titles:
            return None
        #list of walking distances
        distance = [elem.text.strip().split()[:2] for elem in tab.find_all("span", attrs={"title": "Walking"})][tab_titles.index("Preschools")]
        #converting km in m -> list of int
        return self.convert_to_meters(distance)
    
    def parsing_train_station(self, tab):
        """
        Method finding the distance to the train station
        :param: a part of a BeautifullSoup
        returns an integer
        """
        #list of sub-titles
        tab_titles = [elem.text.strip() for elem in tab.find_all("h3")]
        if "Train stations" not in tab_titles:
            return None

        train_row = tab.find_all("div", attrs={"class": "data-row"})[tab_titles.index("Train stations")]
        
        distance = train_row.find("span", attrs={"title": "Walking"}).text.strip().split()[:2]
        return self.convert_to_meters(distance)

    def parsing_supermarket(self, tab):
        """
        Method finding the distance to the nearest supermarket
        :param: a part of a BeautifullSoup
        returns an integer
        """
        distance = tab.find("span", attrs={"title": "Walking"}).text.strip().split()[:2]
        return self.convert_to_meters(distance)
    
    def convert_to_meters(self, distance):
        """
        Method to convert
        :param: list [numerical value as string, unit(m|km) as string]
        returns an integer
        """
        return int(distance[0]) if distance[1] == 'm' else int(float(distance[0]) * 1000)