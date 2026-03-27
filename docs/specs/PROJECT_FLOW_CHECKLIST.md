# PROJECT_FLOW_CHECKLIST.md
## End-to-End Runtime Checklist + Stage Status

This checklist is derived from `PROJECT_RUNTIME_FLOW.md` and current implementation behavior.

Last verified: **March 27, 2026**

Gate evidence from this verification pass:
- [x] `pytest -c pytest.ini -q` (passes)
- [x] `python scripts/check_runtime_setup.py` (passes)
- [x] `python scripts/check_runtime_setup.py --check-facebook-session` (passes)
- [ ] `python start.py` full completion verified in this pass (current run timed out locally after active post processing)

Legend:
- `DONE` = implemented and verified by tests/runtime evidence
- `PARTIAL` = implemented but final gate or full live confirmation still open
- `BLOCKED` = not working / blocked by runtime dependency

---

## Phase 1 - Specification Lock
**Status:** `DONE`
- [x] Goal defined: scan groups feed, process relevant recent posts, rank by AI score.
- [x] Scope boundaries enforced (no seller/comments/marketplace logic).
- [x] `PROJECT_RUNTIME_FLOW.md` is the source-of-truth document.

## Phase 2 - Technical Foundation
**Status:** `DONE`
- [x] `start.py` is the primary runtime entrypoint.
- [x] Runtime/env overrides are centralized in `settings.py` + `.env`.
- [x] Structured errors + debug trace + logger outputs are active.

## Phase 3 - Facebook Access
**Status:** `DONE`
- [x] Browser opens from persistent Chrome profile (`CHROME_USER_DATA_DIR`, `CHROME_PROFILE_DIRECTORY`).
- [x] Facebook home navigation is executed and verified.
- [x] Login state is validated; unauthenticated state maps to `ERR_FACEBOOK_NOT_LOGGED_IN`.
- [x] Optional browser-watch captures visual step screenshots for this phase.

## Phase 4 - Feed Filters
**Status:** `DONE`
- [x] Groups feed is opened and validated.
- [x] `Recent posts` filter is mandatory and verified.
- [x] URL fallback for recent filter exists if click path fails.
- [x] `Last 24 hours` is best-effort and logged (warning if missing).
- [x] Optional browser-watch captures filter state screenshots.

## Phase 5 - Feed Scan
**Status:** `DONE`
- [x] Feed is scanned in scroll rounds.
- [x] Candidate links are collected from multiple DOM strategies.
- [x] Link normalization + dedupe is enforced.
- [x] Round telemetry is logged (added/duplicates/invalid/unreadable).

## Phase 6 - Post Open
**Status:** `DONE`
- [x] Each candidate post is opened via permalink/post URL.
- [x] Post readiness selectors are awaited with retry logic.
- [x] Open failures map to explicit app errors and continue per policy.

## Phase 7 - DOM Extraction
**Status:** `DONE`
- [x] Extracted fields include text, images, publish date raw/normalized, link, post id.
- [x] "See more" expansion is attempted before text extraction.
- [x] Permalink and post-id fallback logic is implemented.

## Phase 8 - Extraction Validation
**Status:** `DONE`
- [x] Extraction success/failure is preserved.
- [x] Missing text/images/date are surfaced as warnings/codes.
- [x] Extraction quality flows downstream.

## Phase 9 - Screenshot Capture
**Status:** `DONE`
- [x] Mandatory per-post screenshot path is enforced.
- [x] Element screenshot is attempted first.
- [x] Full-page fallback is applied when element capture fails.
- [x] Failure maps to `ERR_POST_SCREENSHOT_CAPTURE_FAILED`.

## Phase 10 - Data Processing
**Status:** `DONE`
- [x] Post payload is normalized into one stable downstream schema.
- [x] Date fields are normalized and preserved.
- [x] Diagnostics (`raw_post_data`, warnings, extraction flags) are retained.

## Phase 11 - Time Decision
**Status:** `DONE`
- [x] Parser recency diagnostics are executed and stored.
- [x] Parser rejection reason is retained for observability.
- [x] Final recency decision uses AI field `is_recent_24h`.

## Phase 12 - AI Input
**Status:** `DONE`
- [x] AI payload includes query + normalized post + image refs + screenshot + diagnostics.
- [x] Screenshot file existence is validated before send.
- [x] Structured prompt/payload builder pipeline is active.

## Phase 13 - AI Analysis
**Status:** `DONE`
- [x] AI call retry/backoff flow is implemented.
- [x] JSON/schema parsing and validation are enforced.
- [x] AI error classes are mapped to cataloged app errors.

## Phase 14 - Relevance Filter
**Status:** `DONE`
- [x] Posts with `is_relevant=false` are excluded.
- [x] Posts with `is_recent_24h=false` are excluded.
- [x] Rejection reasons are visible in debug trace.

## Phase 15 - Score
**Status:** `DONE`
- [x] Score source is AI `match_score` only.
- [x] AI explanation/confidence/detected item are preserved in result payload.

## Phase 16 - Rank
**Status:** `DONE`
- [x] Ranking is deterministic and descending by score.
- [x] Ranked output is stable for presentation layer.

## Phase 17 - Result List
**Status:** `DONE`
- [x] List view fields are produced (`post_link`, score, summary, publish time, status, confidence).
- [x] Top results subset is generated.
- [x] List is available in CLI/JSON and optional local UI.

## Phase 18 - Result Detail
**Status:** `DONE`
- [x] Detailed result payload includes extracted post + AI analysis + explanation.
- [x] Detail payload is available in report artifacts and UI detail view.

## Phase 19 - Logging
**Status:** `DONE`
- [x] Human-readable debug trace exists (`data/logs/debug_trace.txt`).
- [x] Technical logger exists (`data/logs/app.log`).
- [x] Stage-level and post-level observability events are present.

## Phase 20 - Error Handling
**Status:** `DONE`
- [x] Per-post failures are isolated (`continue_on_post_error` behavior).
- [x] Fatal scan failures stop with explicit error codes.
- [x] Error catalog mapping is enforced across startup/browser/extraction/AI.

## Phase 21 - Performance
**Status:** `DONE`
- [x] Candidate dedupe prevents duplicate post processing.
- [x] Scroll-round scanning is bounded by `FB_MAX_SCROLL_ROUNDS`.
- [x] Retry counts/timeouts are configurable.

## Phase 22 - Production Gate
**Status:** `PARTIAL`
- [x] Tests pass in this verification pass.
- [x] `doctor` and `doctor-session` pass in this verification pass.
- [ ] Full `start.py` completion confirmed in this verification pass.
- [ ] Final gate should be marked `DONE` only after a successful end-to-end `start.py` run completes and writes fresh final artifacts for the same pass.

---

## Optional UI Observability Layer (Add-on)
**Status:** `DONE` (add-on, not replacing canonical CLI)
- [x] Interactive local UI can start runs.
- [x] Clean Debug timeline view exists with noise filtering toggles.
- [x] Browser-watch visual step gallery exists for "see with eyes" troubleshooting.
- [x] Canonical runtime remains CLI + JSON artifacts.


