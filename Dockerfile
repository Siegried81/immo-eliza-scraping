# immo-eliza-scraping — threaded Immovlan scraper.
# The robots.txt gate (src.compliance.GATE) runs before any fetch; this image
# does not touch it. Needs network at run time.
#   docker build -t immo-eliza-scraping .
#   docker run --rm -v "$PWD/data:/app/data" immo-eliza-scraping
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Use requirements.txt (not the stale requirement.txt that also sits in the repo).
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Progress is appended to data/properties.jsonl, so mount data/ to let --resume
# read it back after a restart. --yes runs unattended (no interactive prompt).
CMD ["python", "main.py", "--yes", "--resume"]
