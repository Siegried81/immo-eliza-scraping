# Decisions

One dated entry per change that alters how the data is collected. Append, never rewrite.

## 2026-10-10 — robots.txt before every fetch, progress written as it arrives

- **What:** `src/compliance.py` reads a host's robots.txt once and every
  `session.get` in the URL collector and the property parser asks it first;
  the run stops before the thread pool starts when the site disallows us. Each
  parsed property is appended to `data/properties.jsonl` on arrival, and
  `--resume` skips the URLs it holds. `--yes`, `--refetch-urls` and `--max`
  replace the two `input()` menus for unattended runs. `requirements.txt`
  lists what the code imports (the old file was a `pip list` dump).
- **Why:** the results lived in memory until the whole batch finished, so a
  crash or a blocked IP late in the run lost everything. And no fetch checked
  robots.txt: a rotating User-Agent is not a collection policy.
- **What it does not settle:** robots.txt is the technical floor. The terms of
  use of the sites collected from, data retention and what may be republished
  were not reviewed here and remain the owner's call before any large run.
- **Revisit if:** a host publishes a `Crawl-delay` — `GATE.crawl_delay` reads
  it, nothing honours it yet.
