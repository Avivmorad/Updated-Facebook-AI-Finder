# Facebook AI Finder

## Overview

This project runs a resilient pipeline to analyze Facebook Marketplace posts:

1. Search posts
2. Extract and normalize post data
3. Run logic analysis
4. Run AI analysis
5. Rank and present results
6. Save run history

## Resilience and Failure Surfacing

The system is designed to keep running after non-fatal failures.

- Post-level errors:
  - The pipeline continues when `continue_on_post_error=True`.
  - Non-fatal errors are surfaced in `presented_results.pipeline_notices`.
- AI failures:
  - AI requests use bounded retries.
  - If retries fail or parsing fails, AI fallback is used and marked in analysis output.
- Scraping failures:
  - Search and extraction use bounded retries and timeout controls.
  - Fallback results/data are returned when needed, with warnings.
- History failures:
  - History save/load errors are logged.
  - Save failures are surfaced in pipeline notices.

## Logging Design

Logs use structured event messages (`event=... | key=value`) to make troubleshooting easier.
Important events include pipeline start/end, search fallback, AI fallback, and post-level processing errors.

## Run Instructions

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Set the active AI provider and keys in `.env`.

Current default provider is `Groq`.

Recommended `.env`:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_new_groq_key_here
GROQ_MODEL_NAME=llama-3.1-8b-instant

# Future option if you switch providers later
GEMINI_API_KEY=
GEMINI_MODEL_NAME=gemini-1.5-flash

# Facebook access uses an existing Chrome profile only
FACEBOOK_HOME_URL=https://www.facebook.com/
FACEBOOK_MARKETPLACE_URL=https://www.facebook.com/marketplace
CHROME_USER_DATA_DIR=C:/Users/your-user/path/to/copied/chrome-user-data
CHROME_PROFILE_DIRECTORY=Default
HEADLESS=false
```

Notes:

- Right now the system should run on `Groq` only.
- `Gemini` support is prepared for future switching.
- If `Groq` fails, the system uses local degraded fallback, not another AI provider by default.
- Facebook access does not perform automatic login.
- The scraper requires an existing Chrome profile that is already logged in to Facebook manually.

### 3. Prepare the Chrome profile manually

Before running the project:

- Open normal Google Chrome yourself.
- Sign in to Facebook in the Chrome profile you plan to reuse.
- Copy your Chrome profile to a dedicated automation folder (recommended helper):
  `python scripts/bootstrap_chrome_profile.py "C:/Users/your-user/AppData/Local/Google/Chrome/User Data/Profile 5"`
- Set `CHROME_USER_DATA_DIR` to that copied folder (not the default `.../Google/Chrome/User Data`).
- Close extra Chrome windows that may lock the profile if Playwright cannot attach cleanly.

### 4. Check the Facebook session

Run the session check script:

```bash
python check_facebook_session.py
```

It prints exactly one of these results:

- `LOGGED_IN`
- `NOT_LOGGED_IN` (plus an error category like `SESSION_CONFIG_ERROR` when available)

### 5. Run the pipeline

```bash
python main.py
```

### 6. Run tests

```bash
python -m pytest -q
```

## Notes

- Run history is stored in `data/run_history.json`.
- To stop on first post failure, set `continue_on_post_error=False` in pipeline options.
- To switch provider in the future, change `AI_PROVIDER` to `gemini` and set `GEMINI_API_KEY`.
- After regenerating your Groq key, paste it into `GROQ_API_KEY` in `.env`.
- `bootstrap_facebook_session.py` is deprecated and intentionally no longer performs login automation.
