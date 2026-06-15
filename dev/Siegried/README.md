## Exploratory Tests and Scraping Scripts Documentation

### 1. First connection test

- The first objective was to verify that a connection to the Immovlan website could be established succesfully.
- A simple HTTP request was sent using the `requests` library.
- A custom User-Agent was added to make the request doesn't look like a bot.
- The response status code was checked to confirm that the page was accessible.
- The HTML content was parsed using BeautifulSoup.
- The page title was printed to verify that the HTML had been downloaded and parsed correctly.

### 2. URL collection tests

- Several listing pages were explored to understand the structure of Immovlan URLs.
- Different property types were tested:
  - house
  - apartment
- Multiple price ranges were generated automatically to increase the number of collected listings.
- A loop was used to browse several result pages for each search.
- All generated URLs were stored in a list before starting the scraping process.

### 3. Property link extraction

- Each listing page was downloaded and parsed with BeautifulSoup.
- All `a` tags containing an `href` attribute were extracted.
- Links were filtered to keep only property detail pages.
- URLs containing `detail` were considered valid property listings.
- URLs related to public sales were excluded.
- Relative URLs were converted into complete URLs by adding the Immovlan domain.
- Duplicate links were removed before storing them.

### 4. Anti-blocking tests

- Small delays were added between requests using `time.sleep()` (still not a bot).
- Request timeouts were added to avoid freezing when a page did not respond.
- Error handling with `try/except` blocks was implemented to prevent the scraper from stoping if a request failed.
- The scraper was tested on multiple pages to verify its stability.

### 5. HTML structure exploration

- Several property pages were inspected manually.
- The goal was to identify where important information was stored in the HTML structure.
- Different CSS selectors were tested to locate:
  - property price
  - property location
  - property characteristics
  - property reference number
  - points of interest

### 6. Property ID extraction

- The "Immovlan ref" field was identified as a unique identifier.
- Tests showed that this value remained stable for a given property.
- This identifier was used to avoid duplicate entries in the final dataset.
- All property IDs were stored in a set called `seen_ids`.

### 7. Location extraction

- The first method was to extract the postal code and city directly from the property URL.
- A fallback method extracted the information from the HTML page when needed.
- Additional processing was used to identify the region and the province.

### 8. Property type detection

- Property type was determined from the URL.
- Listings containing keywords such as apartment/studio/duplex were classified as apartments.
- All other listings were classified as houses (except new building and with annuality rate).

### 9. Feature extraction

- The complete page text was analysed.
- Keyword detection was used to identify property characteristics.
- Binary features were created for:
  - garage
  - terrace
  - garden
  - furnished
  - cellar
  - attic
  - veranda
  - swimming pool
- Each feature was stored as either:
  - 1 = present
  - 0 = absent

### 10. Bedrooms and bathrooms extraction

- HTML list elements were explored to locate room information.
- Regular expressions were used to extract numerical values.
- English and French terms were supported.
- The scraper extracted the number of bedrooms & bathrooms

### 11. Points of Interest (POI) extraction

- POI means Points Of Interest.
- Several property pages contained a section showing nearby facilities.
- Different tabs were explored to identify available information.
- The following distances were extracted when available:
  - preschool distance
  - transport station distance
  - supermarket distance
- Distances were converted into meters for consistency.
- Missing values were stored as `None`.
- Some listings did not contain POI information, so missing values were expected.

### 12. Dataset creation

- A CSV file was created to store all scraped information.
- The dataset included:
  - property_id
  - url
  - price
  - property_type
  - postal_code
  - city
  - region
  - province
  - bedrooms
  - bathrooms
  - garage
  - terrace
  - garden
  - furnished
  - cellar
  - attic
  - veranda
  - swimming_pool
  - preschool_distance
  - train_station_distance
  - supermarket_distance

### 13. Multi-threading tests

- A `ThreadPoolExecutor` was implemented to speed up scraping.
- Multiple property pages were scraped simultaniously.
- A thread lock was added to protect CSV writing operations.
- Tests confirmed:
  - faster execution time
  - no duplicate rows
  - no CSV corruption
- This approach significantly reduced the total scraping duration.


### 14. Possible future improvements

- Add a retry system for failed requests.
- Extract more POI categories.
- Use logging instead of print statements.
- Add automatic data validation before exporting the final dataset.
- Optimise request management to reduce the risk of being blocked.
