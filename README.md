# Immo Eliza Scraping

## Description

This project collects real estate data in Belgium for the Immo Eliza machine learning project. The goal is to build a dataset that can later be used to predict property prices.

Our main source is [Immovlan](https://immovlan.be), because it gives clear property pages with price, location, surface, bedrooms, energy information, and useful nearby points of interest. We also explored [Zimmo](https://www.zimmo.be) as a secondary source to compare or enrich the dataset.

The current pipeline works in two main steps:

1. Collect property URLs from Immovlan search pages.
2. Visit each property page and parse the useful fields into a structured JSON dataset.

The project is still in progress. The README is written as a working documentation draft so the team can update it as the scraper, dataset, and review process evolve.

## Project Goals

- Collect at least 10,000 unique Belgian properties (currently 16K+ from Immovlan and 6K+ from Zimmo).
- Cover all Belgian provinces.
- Save missing values as `None`.
- Prefer numerical values where possible.
- Avoid duplicate rows by checking the property ID.
- Output structured data in JSON.
- Keep the code understandable enough for the full team to review and maintain.

## Sources

### Immovlan

Immovlan is the main source. We scrape:

- Search result pages to collect property URLs.
- Property detail pages to extract the final data.
- Script tags for latitude, longitude, and property type.
- The "More information" HTML section for fields such as bedrooms, livable surface, build year, terrace, garage, and energy consumption.
- The "Points of interest" section for nearby preschool, train station, and supermarket distance.

### Zimmo

Zimmo is used as a secondary scraper experiment. The goal is lighter: collect property URLs by province and parse a smaller set of property fields. This gives the team a backup or comparison source if needed.

## Approach

### 1. URL Collection

The Immovlan URL scraper is in:

```text
src/url_fetcher.py
```

It searches Immovlan by:

- Region
- Province
- Price range
- Page number

We use price ranges because search pages can have result limits. Splitting by price range helps collect more URLs than a single broad search.

The scraper uses:

- `requests.Session()` for connection reuse.
- `ThreadPoolExecutor` for faster URL collection.
- `fake_useragent` to rotate user agents.
- Deduplication before saving URLs.

The URL output is saved to:

```text
data/url_by_province.csv
```

The file format is:

```text
region;province;url
```

### 2. Property Detail Scraping

The detail scraper is in:

```text
src/html_scraper.py
```

For each URL, it extracts:

- Property ID
- Province
- Address
- Postal code
- City
- Price
- Latitude
- Longitude
- Property type
- Livable surface
- Total land surface
- Bedroom count
- Build year
- Property state
- PEB / energy consumption
- Garage
- Terrace
- Swimming pool
- Nearby preschool distance
- Nearby train station distance
- Nearby supermarket distance

The parser keeps the existing Immovlan HTML structure in mind. Some information comes from normal HTML sections, while other fields come from script tags.

Example:

```javascript
window.AD_LONGITUDE = '4.7114746';
window.AD_LATITUDE = '50.3674556';
```

Property type is taken from the script section that stores property details, because other parts of the page may show broader search filters like `house,apartment`, which is not precise enough for one property.

### 3. Main Pipeline

The main entry point is:

```text
main.py
```

It:

1. Runs the URL scraper.
2. Reads `data/url_by_province.csv`.
3. Scrapes each property detail page.
4. Removes duplicates using `property_id`.
5. Groups the final JSON by province and postal code.
6. Saves the final dataset.

The final output is saved to:

```text
belgium_properties.json
```

## Output Structure

The final JSON is grouped like this:

```json
{
  "brussels": {
    "1000": [
      {
        "property_id": "VBE33925",
        "property_type": "apartment",
        "province": "brussels",
        "postcode": "1000",
        "city": "Brussels",
        "address": "...",
        "price": 339000
      }
    ]
  }
}
```

## Data Dictionary

| Column | Type | Description |
| --- | --- | --- |
| `property_id` | string | Unique Immovlan property reference |
| `property_type` | string | `house` or `apartment` when available |
| `province` | string | Belgian province used during URL collection |
| `postcode` | string | Postal code |
| `city` | string | City or municipality |
| `address` | string or `None` | Property address when available |
| `price` | integer or `None` | Sale price in euros |
| `livable_surface` | integer or `None` | Livable surface in square meters |
| `total_surface` | integer or `None` | Land surface in square meters |
| `bedroom_count` | integer or `None` | Number of bedrooms |
| `build_year` | integer or `None` | Construction year |
| `property_state` | string or `None` | Property condition such as new, good, to renovate |
| `peb_category` | integer or `None` | Specific primary energy consumption when available |
| `garage` | integer or `None` | `1` if garage exists, `0` if not |
| `terrace` | integer or `None` | `1` if terrace exists, `0` if not |
| `swimming_pool` | integer or `None` | `1` if swimming pool exists, `0` if not |
| `latitude` | float or `None` | Latitude from Immovlan script data |
| `longitude` | float or `None` | Longitude from Immovlan script data |
| `Preschool_distance` | integer or `None` | Walking distance to nearest preschool in meters |
| `Train_station_distance` | integer or `None` | Walking distance to nearest train station in meters |
| `Supermarket_distance` | integer or `None` | Walking distance to nearest supermarket in meters |

## Secondary Zimmo Scraper

The Zimmo URL scraper is in:

```text
src/zimmo_url_fetcher.py
```

It collects property URLs by province and saves them as JSON. This scraper uses BeautifulSoup to grab property links from search pages.

The Zimmo parser is in:

```text
src/zimmo_html_scraper.py
```

It extracts a smaller set of fields such as:

- Property ID
- Property type
- Postal code
- City
- Address
- Price
- Bedrooms
- Livable surface
- Total surface
- Build year
- Garage
- PEB

Zimmo is not the main pipeline yet. It is kept as a secondary source and can be used later for comparison or enrichment.

## Installation

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirement.txt
```

## Usage

Run the full Immovlan pipeline from the project root:

```bash
python main.py
```

Run only the Immovlan URL collector:

```bash
python src/url_fetcher.py
```

Run a single property parser test:

```bash
python src/html_scraper.py
```

Run the Zimmo URL scraper:

```bash
python src/zimmo_url_fetcher.py
```

## Repository Structure

```text
main/
  .gitignore
  config.json
  config.py
  main.py
  secondary.py
  requirement.txt
  README.md
  data/
    data.json
    dataframe.json
    salary_mean_localities.csv
    url_by_province.csv
    zimmo_properties.csv
    zimmo_urls_by_province.csv
  dev/
    firstscrapingSieg.py
    Imadscrapping.py
    lien_belgium_properties.json
    lien_test.ipynb
    max-eploratory-zimmo.ipynb
    max-exploratory-work.ipynb
    MLscraping-training.py
  src/
    __init__.py
    html_scraper.py
    nearest_cities.py
    points_of_interest.py
    url_fetcher.py
    zimmo_html_scraper.py
    zimmo_url_fetcher.py
```

## Current Features

- Province-based Immovlan URL collection.
- Price-range splitting to get more results.
- Threaded URL scraping.
- Session reuse during URL collection.
- User-Agent rotation.
- Detail page HTML parsing.
- Latitude and longitude extraction.
- Property type extraction from page scripts.
- Point-of-interest enrichment.
- Duplicate checking by property ID.
- JSON output grouped by province and postal code.
- Secondary Zimmo URL scraper and parser draft.
- Configurable scraping parameters via `config.json` and `config.py`.
- Basic logging during scraping.

## Current Limitations

- The final 16,000+ Immovlan and 6,000+ Zimmo dataset still needs full validation.
- Some fields may be missing depending on the property page.
- Some boolean fields still depend on exact website text, so they need review.
- Progress checkpointing is not fully implemented yet.
- Error logging exists, but a dedicated `scraping_errors.log` file is still a future improvement.
- Zimmo is a secondary draft and is not fully integrated into the main dataset yet.
- The project still needs review, cleaning, and presentation preparation.

## Contributors

| Team member | Main contributions |
| --- | --- |
| Max | Main scraper, HTML parsing,latitude/longitude, Zimmo scraper/parser,comment reviews, data structure work, trello kanban board management, |
| Lien | Main scraper, HTML scraper, code reviews, comment reviews, output JSON, data structure work |
| Imad | Documentation, hidden API exploration, Zimmo URL scraper, main URL/HTML scraper optimization, latitude/longitude/property type support,code carbon |
| Siegried | Main scraper, repository setup and GitHub management,merge requests, optimization zimmo scrapper, branch protection |

## Timeline

| Day | Work |
| --- | --- |
| Friday | Role assignment, first exploration, solo scraping practice |
| Monday | Work split, URL scraping, HTML scraping, first optimization work |
| Tuesday morning | Hidden API exploration, Zimmo scraper, dev branch work |
| Tuesday afternoon | Finished second scraper draft, bug fixing before merge |
| Wednesday | Optimization, documentation, validation, review |
| Final review period | Dataset checks, troubleshooting, presentation preparation |

<img width="2072" height="987" alt="timeline" src="https://github.com/user-attachments/assets/a93531e6-4172-4255-9a4d-932cbce9313d" />


## Emission in CO2
0.00027 kg CO2eq, which is 0.27 grams of CO2.


