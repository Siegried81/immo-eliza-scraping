# Immo Eliza Scraping

## Description

This project collects real estate data in Belgium for the Immo Eliza machine learning project. The goal is to build a dataset that can later be used to predict property prices.

Our main source is [Immovlan](https://immovlan.be), because it gives clear property pages with price, location, surface, bedrooms, energy information, and useful nearby points of interest. We also explored [Zimmo](https://www.zimmo.be) as a secondary source to compare or enrich the dataset.

The current pipeline works in two main steps:

1. Collect property URLs from Immovlan search pages.
2. Visit each property page and parse the useful fields into a structured JSON dataset.

The project is still in progress. The README is written as a working documentation draft so the team can update it as the scraper, dataset, and review process evolve.

## Project Goals

- Collect at least 10,000 unique Belgian properties.
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
src/zimmo_scraper.py
```

It collects property URLs by province and saves them as JSON. This scraper uses BeautifulSoup to grab property links from search pages.

The Zimmo parser is in:

```text
src/zimmo_parser.py
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
pip install beautifulsoup4 lxml requests pandas fake-useragent
```

There is currently no final `requirements.txt`, so this section should be updated once dependencies are frozen.

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
python src/zimmo_scraper.py
```

## Repository Structure

```text
newdev/
  main.py
  README.md
  assets/
    BE.txt
  data/
    url_by_province.csv
  src/
    html_scraper.py
    points_of_interest.py
    url_fetcher.py
    zimmo_parser.py
    zimmo_scraper.py
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
- Basic logging during scraping.

## Current Limitations

- The final 10,000+ dataset still needs full validation.
- Some fields may be missing depending on the property page.
- Some boolean fields still depend on exact website text, so they need review.
- Progress checkpointing is not fully implemented yet.
- Error logging exists, but a dedicated `scraping_errors.log` file is still a future improvement.
- Zimmo is a secondary draft and is not fully integrated into the main dataset yet.
- The project still needs review, cleaning, and presentation preparation.

## Contributors

| Team member | Main contributions |
| --- | --- |
| Max | Main scraper, HTML parsing, Zimmo scraper/parser, data structure work |
| Lien | Main scraper, HTML scraping, output JSON, Kanban board |
| Imad | Documentation, hidden API exploration, Zimmo URL scraper, URL/HTML scraper optimization, latitude/longitude/property type support |
| Siegried | Main scraper, repository setup and GitHub management, optimization, branch protection |

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



## Teacher Requirements Coverage

| Requirement | Current status |
| --- | --- |
| Properties across Belgium | Covered through province-based URL collection |
| Minimum 10,000 data points | Targeted, still needs final dataset validation |
| Missing values encoded as `None` | Implemented in parser defaults |
| Numerical values where possible | Implemented for price, surfaces, bedroom count, coordinates, boolean fields |
| No duplicates | Checked by `property_id` in `main.py` |
| Clear contribution | Documented in this README |
| Threading / performance | Implemented in URL collection |
| Session persistence | Used in URL collection |
| User-Agent rotation | Used through `fake_useragent` |
| Hidden API exploration | Explored during development; main pipeline currently uses HTML parsing because detail data is richer there |
| Coordinates capture | Implemented from script data |
| Secondary source | Zimmo scraper/parser draft exists |

## Notes for Future Work

- Add `requirements.txt`.
- Add a proper `data/raw` and `data/cleaned` structure.
- Add checkpointing so the scraper can resume after interruption.
- Write failed URLs to a log file.
- Validate final row count and duplicate count.
- Check numerical conversion for every final column.
- Decide if Zimmo data should be merged or kept separate.
- Prepare a short slide deck with the pipeline diagram and final dataset summary.
