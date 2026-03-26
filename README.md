# Facebook Groups Post Finder & Matcher

## Authoritative Spec

The source of truth for this repository is:

- `AGENTS.md`
- `SYSTEM_DESIGN.md`
- `PROJECT_DEVELOPMENT_PHASES.md`
- `TASKS.md`

If any older docs or legacy notes conflict with those files, follow the four root spec files.

## Overview

This project is a minimal AI-powered matcher for Facebook groups posts.

It:

1. Opens Facebook using an existing Chrome profile
2. Scans the groups feed for candidate post links
3. Opens each post and extracts only:
   - post text
   - images
   - publish date
   - post link
4. Applies a hard 24-hour filter
5. Sends the post to AI for:
   - relevance
   - match score
   - detected item
   - match reason
   - confidence
6. Keeps only relevant posts
7. Ranks them by AI `match_score`

The project does not implement seller analysis, comment analysis, risk logic, marketplace logic, or fake fallback results.

## Project Structure

```text
app/
  ai/            AI client, prompt, payload, parser, and retry service
  browser/       Chrome session handling and Facebook groups feed scanning
  config/        Runtime configuration and startup validation
  domain/        Shared data contracts used across the pipeline
  extraction/    Post extraction and normalization
  pipeline/      Query validation, time filter, search flow, and orchestration
  presentation/  Result formatting and run-history persistence
  ranking/       Match-score sorting
  utils/         Shared logger

scripts/
  doctor.py                    Environment and session diagnostics
  bootstrap_chrome_profile.py  Safe Chrome profile copy helper

tests/
  ai/
  config/
  extraction/
  pipeline/
  presentation/
  ranking/
```

## Requirements

- Python 3.10+
- Google Chrome installed
- Playwright runtime installed
- A copied Chrome profile root, not the default Chrome User Data root

## Installation

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
playwright install
```

## Configuration

Required environment variables:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_groq_key
CHROME_USER_DATA_DIR=C:/path/to/copied/chrome_user_data
CHROME_PROFILE_DIRECTORY=Default
```

Optional environment variables:

```env
GROQ_MODEL_NAME=llama-3.1-8b-instant
GEMINI_API_KEY=
GEMINI_MODEL_NAME=gemini-1.5-flash
FACEBOOK_HOME_URL=https://www.facebook.com/
FACEBOOK_GROUPS_FEED_URL=https://www.facebook.com/groups/feed/
HEADLESS=false
AI_TIMEOUT_SECONDS=20
AI_RETRY_ATTEMPTS=2
AI_RETRY_BACKOFF_SECONDS=0.4
AI_MAX_OUTPUT_TOKENS=700
AI_TEMPERATURE=0.2
FB_TIMEOUT_MS=15000
FB_RETRIES=2
FB_MAX_SCROLL_ROUNDS=8
FB_SCROLL_PAUSE_MS=800
```

If you need a dedicated Chrome profile copy for Playwright, use:

```bash
python scripts/bootstrap_chrome_profile.py "C:/Users/You/AppData/Local/Google/Chrome/User Data/Profile 5"
```

## Input

The active runtime input is a single query:

```json
{
  "query": "iphone 13"
}
```

## Run

JSON input file mode:

```bash
python main.py --input-file data/sample_search_input.json --output-json data/reports/latest.json
```

CLI query mode:

```bash
python main.py --query "iphone 13" --output-json data/reports/latest.json
```

Interactive mode:

```bash
python main.py --interactive
```

Demo mode:

```bash
python main.py --demo
```

Launcher:

```bash
python run_app.py --mode file
python run_app.py --mode test
python run_app.py --mode doctor
```

## Tests

```bash
pytest -q
```

## Outputs

- Console summary of top matches
- Optional JSON report via `--output-json`
- Run history persisted in `data/run_history.json`

## Notes

- Facebook login must already exist in the configured Chrome profile.
- No automatic login is performed.
- If extraction or AI analysis fails for a post, that post is skipped and the run continues.
