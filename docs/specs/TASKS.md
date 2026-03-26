# TASKS.md
## Facebook Groups Post Finder & Matcher

This file defines the exact implementation order for Codex or any coding agent.
Follow tasks in order.
Do not skip ahead unless the current task is completed or blocked.

---

## Global Rules

- Follow docs/specs/AGENTS.md strictly
- Follow docs/specs/SYSTEM_DESIGN.md strictly
- Follow docs/specs/PROJECT_DEVELOPMENT_PHASES.md strictly
- Do not implement anything outside scope
- Do not add seller logic
- Do not add comment logic
- Do not add risk logic
- Do not add Marketplace logic
- Do not add fake fallback data
- Keep changes small and modular
- Prefer working code over speculative architecture

---

## Task 1 — Project Scaffold

### Goal
Create a clean Python project structure for the system.

### Required Output
- Source folders
- Test folders
- Main entry file
- Basic config loading
- Logging setup
- Environment example file

### Definition of Done
- Project runs without crashing
- `start.py` or equivalent entry point exists
- `.env.example` exists
- Logging works
- Core folders exist

### Notes
Do not implement Facebook or AI logic yet.

---

## Task 2 — Configuration Layer

### Goal
Create a configuration system for environment-driven runtime settings.

### Required Output
Support configuration for:
- Chrome user data directory
- Chrome profile name
- Facebook groups feed URL
- AI provider
- API key
- Max posts to scan
- Headless mode
- Timeouts
- Log level

### Definition of Done
- Config loads from environment
- Missing required values produce clear errors
- Defaults exist where appropriate

---

## Task 3 — Browser Access Layer

### Goal
Create Playwright browser startup using an existing Chrome profile.

### Required Output
- Browser launcher
- Context initialization
- Existing Chrome profile support
- Open target Facebook page

### Definition of Done
- Browser opens using configured profile
- System can navigate to Facebook groups feed
- Basic page-load verification exists

### Notes
Do not implement login automation.

---

## Task 4 — Feed Navigation Layer

### Goal
Navigate reliably to the Facebook groups feed and prepare for scanning.

### Required Output
- Open groups feed
- Wait for stable page state
- Detect that feed content is present
- Handle loading delays gracefully

### Definition of Done
- Feed page opens successfully
- Post-like elements can be detected
- Errors are logged cleanly

---

## Task 5 — Feed Scanning

### Goal
Scan the feed and collect candidate post links.

### Required Output
- Controlled scrolling
- Post detection
- Link extraction
- Duplicate prevention
- Scan limit support

### Definition of Done
- System returns a list of unique post links
- Maximum scan limit is respected
- Empty results are handled safely

### Notes
Do not analyze posts here.

---

## Task 6 — Post Opening

### Goal
Open each post individually and prepare it for extraction.

### Required Output
- Open post page
- Wait for full content load
- Retry or skip on failure

### Definition of Done
- Valid post pages can be opened
- Failed posts are skipped without stopping the run

---

## Task 7 — Post Data Extraction

### Goal
Extract only the allowed fields from the post.

### Required Output
Extract:
- Post text
- Images
- Publish date
- Post link

Do NOT extract:
- Comments
- Seller info
- Likes
- Reactions

### Definition of Done
- Extracted data is returned in a consistent structure
- Missing fields are allowed
- No forbidden fields are collected

---

## Task 8 — Data Processing

### Goal
Normalize extracted post data.

### Required Output
- Clean text
- Normalize date representation
- Normalize image list
- Build stable post data model

### Definition of Done
- All extracted posts share one schema
- Empty/missing values are handled cleanly

---

## Task 9 — Time Filter

### Goal
Discard posts older than 24 hours.

### Required Output
- Date parsing
- Age calculation
- Recent/not-recent decision

### Definition of Done
- Posts outside the 24-hour window are excluded
- Invalid or missing dates are handled safely

### Notes
This is a hard filter.

---

## Task 10 — AI Client Layer

### Goal
Create a clean AI integration layer.

### Required Output
- AI client wrapper
- Request builder
- Response parser
- Error handling
- Timeout handling

### Definition of Done
- AI calls are isolated in one module
- Invalid AI responses are handled safely

---

## Task 11 — AI Prompting for Matching

### Goal
Send post data to AI so it can determine relevance and match score.

### Required Output
AI must receive:
- User query
- Post text
- Images

AI must return structured output:
- `is_relevant`
- `match_score`
- `detected_item`
- `match_reason`
- `confidence`

### Definition of Done
- Prompt is deterministic and structured
- JSON output is validated
- Non-JSON failures are handled

---

## Task 12 — Relevance Filtering

### Goal
Discard posts that are not relevant to the user query.

### Required Output
- Apply AI relevance decision
- Keep only relevant posts

### Definition of Done
- Non-relevant posts are removed
- Relevant posts continue to scoring

### Notes
This is a hard filter.

---

## Task 13 — Scoring

### Goal
Assign final score using AI match score only.

### Required Output
- Final score field
- Stable numeric handling
- Score validation

### Definition of Done
- Every relevant post has a final score
- No other scoring dimensions are added

---

## Task 14 — Ranking

### Goal
Sort relevant posts by match score.

### Required Output
- Descending sort
- Stable ordering
- Output-ready ranking list

### Definition of Done
- Highest score appears first
- Invalid score values do not break ranking

---

## Task 15 — Results Formatting

### Goal
Prepare results for presentation.

### Required Output
Each result should include:
- Post link
- Match score
- Short summary
- Detected item
- Match reason
- Confidence
- Price/free indicator if inferable from post

### Definition of Done
- Output is clean and readable
- Missing optional values are handled safely

---

## Task 16 — Logging

### Goal
Log the full pipeline clearly.

### Required Output
Log:
- Startup
- Config load
- Browser start
- Feed access
- Posts collected
- Posts opened
- Extraction failures
- AI failures
- Filtering results
- Final counts

### Definition of Done
- Logs are readable
- Errors include enough context for debugging

---

## Task 17 — Error Handling

### Goal
Make the system resilient.

### Required Output
- Per-post failure isolation
- Retry where appropriate
- Skip broken items safely
- No global crash from one bad post

### Definition of Done
- The run continues despite partial failures

---

## Task 18 — CLI / Run Flow

### Goal
Create a runnable user flow.

### Required Output
- Accept query input
- Start full pipeline
- Print or display ranked results

### Definition of Done
- A user can run the system end-to-end from one command

---

## Task 19 — UI Layer

### Goal
Create a minimal usable interface.

### Required Output
- Query input
- Start button
- Progress indicator
- Results list
- Detail view

### Definition of Done
- User can run search and inspect results visually

### Notes
Keep UI minimal. Do not overengineer.

---

## Task 20 — Tests

### Goal
Add practical tests for core parts.

### Required Output
Tests for:
- Config loading
- Data normalization
- Date filtering
- AI response validation
- Ranking

### Definition of Done
- Core logic has automated coverage
- Tests run without requiring Facebook login

---

## Task 21 — Final Cleanup

### Goal
Prepare the project for stable ongoing use.

### Required Output
- Remove dead code
- Ensure module boundaries are clean
- Improve naming
- Improve docs
- Verify run instructions

### Definition of Done
- Project is understandable
- Project is runnable
- Project follows scope strictly

---

## Execution Rule

Always work on the next unfinished task.
Do not jump to future tasks unless required by a dependency.
When a task is finished:
1. confirm what was implemented
2. list what remains
3. move to the next task

If blocked:
- explain the blocker clearly
- make the smallest safe progress possible
- do not invent unsupported behavior
