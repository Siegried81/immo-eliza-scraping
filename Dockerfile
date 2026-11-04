# immo-eliza-scraping — threaded Immovlan scraper.
# Every fetch checks robots.txt (src.polite.polite_get); main.py also runs
# src.compliance.GATE once before the thread pool starts. This image changes none of that.
# Needs network at run time.
#   docker build -t immo-eliza-scraping .
#   docker run --rm -v "$PWD/data:/app/data" immo-eliza-scraping
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Progress is appended to data/properties.jsonl, so mount data/ to let --resume
# read it back after a restart. --yes runs unattended (no interactive prompt).
CMD ["python", "main.py", "--yes", "--resume"]
