# Immo Eliza Scraping

## Description

This project collects real estate data in Belgium for the Immo Eliza machine learning project. The goal is to build a dataset that can later be used to predict property prices.

Our main source is [Immovlan](https://immovlan.be), because it gives clear property pages with price, location, surface, bedrooms, energy information, and useful nearby points of interest. We also explored [Zimmo](https://www.zimmo.be) as a secondary source to compare or enrich the dataset.

The current pipeline works in two main steps:

1. Collect property URLs from Immovlan search pages.
2. Visit each property page and parse the useful fields into a structured JSON dataset.

Every request goes through `src/polite.py`, which checks the host's `robots.txt`, waits between requests to the same host, and sends one honest, identifiable User-Agent. See [Scraping politeness](#scraping-politeness).

The project is still in progress. The README is written as a working documentation draft so the team can update it as the scraper, dataset, and review process evolve.

## Project Goals

- Collect at least 10,000 unique Belgian properties (currently 16K+ from Immovlan and 6K+ from Zimmo).
- Cover all Belgian provinces.
- Save missing values as `None`.
- Prefer numerical values where possible.
- Avoid duplicate rows by checking the property ID.
- Output structured data in JSON.
- Keep the code understandable enough for the full team to review and maintain.
- Stay within what the source sites allow, and stay identifiable while doing it.

## Scraping politeness

All HTTP traffic goes through `polite_get()` in `src/polite.py`. It does three
things before a request leaves the process:

1. **robots.txt.** The host's `robots.txt` is fetched once per host and cached.
   A path the file disallows raises `RobotsDisallowed` and is never requested.
   A `robots.txt` that cannot be read at all is treated as "disallowed": an
   unreachable file is not permission. `main.py` also checks the first detail
   URL before starting the thread pool, so a host that forbids those pages
   costs one request instead of thousands of refusals.
2. **One honest User-Agent.** Every request identifies the crawler as
   `ImmoElizaBot/1.0` with a contact address, taken from `scraper_contact` in
   `config.json`. Headers passed by a caller are merged in, but the User-Agent
   cannot be overridden. Earlier versions rotated random browser identities
   through `fake_useragent`; that is evasion, and it leaves a site operator no
   way to ask us to slow down.
3. **A delay per host.** `request_delay_seconds` (default `1.0`) is the minimum
   gap between two requests to the same host, and a `Crawl-delay` in
   `robots.txt` raises it. Threads take turns, so N workers make N spaced
   requests instead of N simultaneous ones.

Because the delay is per host, a large thread pool only puts threads in a
queue. `main_max_workers` and `url_fetcher_max_worker` are therefore `4`, not
the 25 and 10 used before.

Settings live in `config.json`:

```json
{
  "main_max_workers": 4,
  "main_max_scraped_properties": 10,
  "url_fetcher_max_worker": 4,
  "url_fetcher_max_pages": 50,
  "request_delay_seconds": 1.0,
  "scraper_contact": "immo-eliza-scraping@example.org"
}
```

Set `scraper_contact` to a real address before running a full scrape.

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
- `ThreadPoolExecutor` for parallel URL collection, with a small worker count.
- `src/polite.py` for the robots.txt check, the per-host delay and the project's User-Agent.
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

The final output is saved to two files:

```text
data/data.json        # grouped by province and postal code
data/dataframe.json   # flat list of records, ready for pandas
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

It collects property URLs by province and saves them as CSV. This scraper uses BeautifulSoup to grab property links from search pages.

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
pip install -r requirements.txt
```

## Usage

Run the full Immovlan pipeline from the project root:

```bash
python main.py                       # interactive menus
python main.py --yes                 # no prompts: reuse data/url_by_province.csv, then scrape
python main.py --yes --resume        # keep data/properties.jsonl and skip its URLs
python main.py --yes --refetch-urls  # collect the URL list again first
python main.py --max 500             # cap this run (default: config.json)
python -m pytest -q                  # the robots gate and the checkpoint, no network
```

Every fetch asks the site's `robots.txt` first and fails closed when it cannot
be read (`src/compliance.py`). Each property is appended to
`data/properties.jsonl` as soon as it is parsed, so an interrupted run keeps
what it had; `data.json` and `dataframe.json` are rebuilt from it at the end.
Terms of use and data retention are not checked by code: read them before a
large run.

Run only the Immovlan URL collector:

Run the Zimmo pipeline (secondary source) from the project root:

```bash
python secondary.py
```

Both are interactive: they ask whether to reuse the URLs already in `data/` or
to collect them again. The modules under `src/` are imported, not run directly:
they rely on `config` and `src.polite`, which resolve from the project root.

Run the tests (no network, nothing is fetched):

```bash
pip install -r requirements.txt
pytest
```

Run the Zimmo URL scraper:

```bash
python src/zimmo_url_fetcher.py
```

Expected: `37 passed`. Every test fakes its HTTP responses and fails if any
code tries to make a real request.

## Repository Structure

```text
immo-eliza-scraping/
  main.py                   # Immovlan pipeline (URLs + details)
  secondary.py              # Zimmo pipeline
  config.py                 # loads config.json at import time
  config.json               # worker counts, request delay, contact address
  requirements.txt
  README.md
  data/                     # scraped CSV/JSON output and scraper logs
  src/
    polite.py               # per-host delay, honest User-Agent, robots.txt per fetch
    compliance.py           # robots.txt gate main.py asks once before the workers
    checkpoint.py           # properties.jsonl written as they arrive; --resume
    url_fetcher.py          # Immovlan search pages -> property URLs
    html_scraper.py         # Immovlan property page -> dict
    points_of_interest.py   # preschool/station/supermarket distances
    nearest_cities.py       # nearest major city and its distance
    zimmo_url_fetcher.py    # Zimmo search pages -> property URLs
    zimmo_html_scraper.py   # Zimmo property page -> dict
  tests/
    test_polite.py
    test_compliance.py
    test_checkpoint.py
  dev/                      # individual exploration scripts and notebooks
```

## Current Features

- Province-based Immovlan URL collection.
- Price-range splitting to get more results.
- Threaded URL scraping.
- Session reuse during URL collection.
- robots.txt check, per-host delay and a single identifiable User-Agent (`src/polite.py`).
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


