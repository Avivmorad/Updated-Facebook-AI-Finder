# PROJECT_RUNTIME_FLOW.md
## Facebook Groups Post Finder & Matcher

This file is the primary source of truth for runtime behavior.
When other spec files differ, this file wins.

---

## Locked Runtime Decisions (March 2026)

1. Runtime scope is core pipeline only: browser access, scan, extraction, AI matching, ranking, CLI + JSON artifacts.
2. Recency final decision is AI-owned (`is_recent_24h`), while parser date is retained for diagnostics.
3. Screenshot capture is mandatory for each processed post before AI analysis.
4. "Recent posts" feed filter is run-blocking. If not applied and verified, the run fails.
5. Active provider policy is Groq vision path.
6. CLI + JSON artifacts remain the canonical interface; optional local UI dashboard is supported for run control and observability.

---

## Phase 1 - Specification Lock

- Define goal: scan groups feed, process recent posts, rank by query match.
- Confirm boundaries: groups feed only, no seller/comments/risk/marketplace/login automation.
- Confirm execution model: DOM-first extraction + mandatory screenshot + AI semantic analysis.

## Phase 2 - Technical Foundation

- Keep clean project structure, env config, runtime settings, logging, and error catalog.
- Ensure minimal end-to-end run path can execute from `start.py`.

## Phase 3 - Facebook Access

- Open browser with existing authenticated Chrome profile.
- Navigate to Facebook home and groups feed.
- Detect and surface profile/session/navigation failures with specific error codes.

## Phase 4 - Built-in Feed Filtering

- Apply Facebook built-in filters.
- Require and verify `Recent posts` selection.
- Attempt `Last 24 hours` as best-effort and log status.

## Phase 5 - Feed Scanning

- Scroll feed and collect candidate post links.
- Canonicalize links and prevent duplicates.
- Track scan telemetry per round (added, duplicate, invalid, unreadable).

## Phase 6 - Post Opening

- Open each post in dedicated post/permalink page when possible.
- Wait for stable page state and post container before extraction.

## Phase 7 - DOM-first Extraction

- Extract:
  - `post_text`
  - `images`
  - `image_count`
  - `publish_date_raw`
  - `publish_date_normalized`
  - `post_link`
  - `post_id`

- Do not extract:
  - comments
  - seller data
  - likes/reactions

## Phase 8 - Extraction Validation

- Evaluate extraction quality:
  - `good`
  - `partial`
  - `failed`

- Keep missing fields allowed, but classify quality explicitly.

## Phase 9 - Screenshot Capture

- Capture post-element screenshot for every processed post.
- If element capture fails, fallback to full-page capture and log the coded reason.
- Persist screenshot path in post payload.

## Phase 10 - Data Processing

- Normalize whitespace and text shape.
- Normalize date text representation.
- Normalize image list and counts.
- Build one stable post schema used by all downstream stages.

## Phase 11 - Time Filtering

- Run parser-based 24h diagnostics for observability.
- Keep final inclusion decision on AI recency output.

## Phase 12 - AI Input Construction

- Build AI payload from:
  - user query
  - normalized post text
  - image references
  - publish date hints
  - extraction quality
  - screenshot path

## Phase 13 - AI Matching Analysis

- AI decides:
  - relevance
  - match score
  - detected item
  - explanation
  - recency final decision

- AI does not do browser actions.

## Phase 14 - Relevance Filtering

- Discard when `is_relevant=false`.
- Continue only relevant posts.

## Phase 15 - Scoring

- Score is AI `match_score` only.
- Store explanation + structured AI fields.

## Phase 16 - Ranking

- Sort by score descending.
- Preserve stable deterministic ordering.

## Phase 17 - Results Presentation

- List output includes:
  - post link
  - match score
  - short explanation
  - publish time
  - extraction status
  - detected item
  - confidence
- Surface the same list output in CLI/report JSON and optional local UI.

## Phase 18 - Detail Output

- Detail output includes:
  - extracted data
  - screenshot references
  - AI analysis
  - match explanation
- Detail payload is available in report artifacts and optional local UI detail panel.

## Phase 19 - Logging

- Log scan, extraction, screenshot, AI, filtering, and final counters.
- Keep human-readable debug trace and technical logger output.

## Phase 20 - Error Handling

- Fail per post, not globally.
- Retry unstable steps.
- Skip broken posts and continue.
- Expose specific error codes.

## Phase 21 - Performance

- Avoid duplicate post processing.
- Reduce repeated DOM queries.
- Keep screenshot and extraction runtime stable.

## Phase 22 - Production Readiness

- Finalize schemas, prompts, config defaults, tests, and docs.
- Require live gate:
  - `pytest -q`
  - `python scripts/check_runtime_setup.py`
  - `python scripts/check_runtime_setup.py --check-facebook-session`
  - `python start.py`

