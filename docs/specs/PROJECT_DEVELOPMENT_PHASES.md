# PROJECT_DEVELOPMENT_PHASES.md
## Delivery Phases

This phase list tracks implementation order aligned to `Project_Flow.md`.

---

## Phase 1 - Spec Lock

- keep `Project_Flow.md` authoritative
- align all spec docs

## Phase 2 - Foundation

- validate config/startup
- stable logging/debug trace
- stable error catalog

## Phase 3 - Facebook Access

- browser profile startup
- Facebook/session validation
- groups feed navigation

## Phase 4 - Feed Filters

- enforce and verify `Recent posts`
- apply `Last 24 hours` best effort

## Phase 5 - Feed Scan

- collect canonical links
- dedupe
- scan telemetry by round

## Phase 6 - Post Open

- reliable post page loading
- stable container readiness checks

## Phase 7 - DOM Extraction

- text, images, publish date raw/normalized, permalink, post id

## Phase 8 - Extraction Validation

- derive `extraction_quality`
- surface partial/failed extraction clearly

## Phase 9 - Screenshot Capture

- mandatory screenshot per post
- element-first, fallback path coded

## Phase 10 - Data Processing

- normalize final post schema
- preserve diagnostics fields

## Phase 11 - Time Decision

- parser diagnostics retained
- AI recency final decision enforced

## Phase 12 - AI Input

- build stable payload from normalized post + screenshot + diagnostics

## Phase 13 - AI Analysis

- parse and validate AI schema

## Phase 14 - Relevance Filter

- keep only relevant posts

## Phase 15 - Score

- use AI match score only

## Phase 16 - Rank

- deterministic descending ranking

## Phase 17 - Result List

- expose list fields needed for CLI/reporting

## Phase 18 - Result Detail

- expose full extracted payload + AI analysis

## Phase 19 - Logging

- full stage observability

## Phase 20 - Error Handling

- per-post failure isolation

## Phase 21 - Performance

- reduce scan/extraction inefficiency

## Phase 22 - Production Gate

- pass:
  - `pytest -q`
  - `python scripts/doctor.py`
  - `python scripts/doctor.py --check-facebook-session`
  - `python start.py`
