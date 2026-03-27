# PROJECT_DEVELOPMENT_PHASES.md
## Delivery Phases

This phase list tracks implementation order aligned to `PROJECT_RUNTIME_FLOW.md`.

---

## Latest Verification Snapshot (March 27, 2026)

- Runtime command: `python start.py`
- Runtime result:
  - pipeline core status: `completed`
  - processed posts: `20`
  - kept ranked results: `3`
  - elapsed seconds: `279.278`
  - artifacts: `data/reports/latest.json`, `data/logs/debug_trace.txt`
- Wrapper process result:
  - `start.py` exit code: `1`
  - terminal error after pipeline completion:
    - `ERR_PIPELINE_UNEXPECTED`
    - technical details: `'charmap' codec can't encode characters ...`

Legend:
- `DONE` = implemented and verified
- `PARTIAL` = implemented but gate not fully green
- `BLOCKED` = cannot proceed without fix/environment action

---

## Phase 1 - Spec Lock

Status: `DONE`
- [x] keep `PROJECT_RUNTIME_FLOW.md` authoritative
- [x] align all spec docs

## Phase 2 - Foundation

Status: `DONE`
- [x] validate config/startup
- [x] stable logging/debug trace
- [x] stable error catalog

## Phase 3 - Facebook Access

Status: `DONE`
- [x] browser profile startup
- [x] Facebook/session validation
- [x] groups feed navigation

## Phase 4 - Feed Filters

Status: `DONE`
- [x] enforce and verify `Recent posts`
- [x] apply `Last 24 hours` best effort

## Phase 5 - Feed Scan

Status: `DONE`
- [x] collect canonical links
- [x] dedupe
- [x] scan telemetry by round

## Phase 6 - Post Open

Status: `DONE`
- [x] reliable post page loading
- [x] stable container readiness checks

## Phase 7 - DOM Extraction

Status: `DONE`
- [x] text, images, publish date raw/normalized, permalink, post id

## Phase 8 - Extraction Validation

Status: `DONE`
- [x] derive `extraction_quality`
- [x] surface partial/failed extraction clearly

## Phase 9 - Screenshot Capture

Status: `DONE`
- [x] mandatory screenshot per post
- [x] element-first, fallback path coded

## Phase 10 - Data Processing

Status: `DONE`
- [x] normalize final post schema
- [x] preserve diagnostics fields

## Phase 11 - Time Decision

Status: `DONE`
- [x] parser diagnostics retained
- [x] AI recency final decision enforced

## Phase 12 - AI Input

Status: `DONE`
- [x] build stable payload from normalized post + screenshot + diagnostics

## Phase 13 - AI Analysis

Status: `DONE`
- [x] parse and validate AI schema

## Phase 14 - Relevance Filter

Status: `DONE`
- [x] keep only relevant posts

## Phase 15 - Score

Status: `DONE`
- [x] use AI match score only

## Phase 16 - Rank

Status: `DONE`
- [x] deterministic descending ranking

## Phase 17 - Result List

Status: `DONE`
- [x] expose list fields needed for CLI/reporting

## Phase 18 - Result Detail

Status: `DONE`
- [x] expose full extracted payload + AI analysis

## Phase 19 - Logging

Status: `DONE`
- [x] full stage observability

## Phase 20 - Error Handling

Status: `DONE`
- [x] per-post failure isolation

## Phase 21 - Performance

Status: `DONE`
- [x] reduce scan/extraction inefficiency

## Phase 22 - Production Gate

Status: `PARTIAL`
- [x] `pytest -q` (verified with `pytest -c pytest.ini -q`)
- [x] `python scripts/check_runtime_setup.py`
- [x] `python scripts/check_runtime_setup.py --check-facebook-session`
- [ ] `python start.py` exits `0` end-to-end
- Current blocker:
  - pipeline completed successfully, but wrapper exits with encoding exception (`charmap`), so gate is not fully green yet.

