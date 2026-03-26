"""
Central runtime settings for normal day-to-day use.

Edit this file, then run:
    python start.py

Important:
- Change API keys and Chrome profile paths in .env, not here.
- Keep values simple. If you do not need an advanced override, leave it as None.
"""


# ---------------------------------------------------------------------------
# QUICK CONTROL
# These are the settings you will change most often.
# ---------------------------------------------------------------------------

# Options: True, False
# What it does:
# - True  -> prints a clear step-by-step explanation in the terminal.
# - False -> prints a shorter terminal output.
DEBUGGING = True

# Options: path string (for example "data/logs/debug_trace.txt")
# What it does:
# - Used only when DEBUGGING=True.
# - Stores the same human-readable debug trace that is printed to terminal.
# - The file is overwritten on every run (fresh file per run).
DEBUG_TRACE_FILE = "data/logs/debug_trace.txt"

# Options: "query", "file", "interactive", "demo"
# What it does:
# - "query"       -> uses the QUERY text below
# - "file"        -> loads input from INPUT_FILE
# - "interactive" -> asks you to type the query in the terminal
# - "demo"        -> runs a built-in demo query
RUN_MODE = "file"


# ---------------------------------------------------------------------------
# INPUT
# Only one input source is used, based on RUN_MODE.
# ---------------------------------------------------------------------------

# Used only when RUN_MODE == "query"
# What it does:
# - This is the text the system will try to match against Facebook posts.
# Example:
# - "iphone 13"
# - "playstation 5"
QUERY = "iphone 13"

# Used only when RUN_MODE == "file"
# What it does:
# - Points to a JSON file that contains the query payload.
# Expected JSON shape:
#   {"query": "iphone 13"}
INPUT_FILE = "data/sample_search_input.json"


# ---------------------------------------------------------------------------
# MAIN RUNTIME LIMITS
# These change speed, coverage, and how much work the run performs.
# ---------------------------------------------------------------------------

# Options: any positive integer
# What it does:
# - Limits how many candidate posts the program will inspect in one run.
# Lower number:
# - faster run
# - fewer posts checked
# Higher number:
# - slower run
# - more coverage
# Recommended:
# - 5 to 20 for quick testing
# - 20 to 40 for wider scanning
MAX_POSTS = 20


# ---------------------------------------------------------------------------
# OUTPUT
# These control where results are saved.
# ---------------------------------------------------------------------------

# Options:
# - a file path string, for example "data/reports/latest.json"
# - None, to auto-create a timestamped JSON file inside data/reports/
# What it does:
# - Saves the final run result as JSON.
OUTPUT_JSON = "data/reports/latest.json"

# Options: True, False
# What it does:
# - True  -> also saves the run into data/run_history.json
# - False -> does not update run history
SAVE_RUN_HISTORY = True


# ---------------------------------------------------------------------------
# ERROR HANDLING
# These control what happens if one post fails during the run.
# ---------------------------------------------------------------------------

# Options: True, False
# What it does:
# - True  -> skip broken posts and keep going
# - False -> stop the whole run on the first post error
CONTINUE_ON_POST_ERROR = True

# Options:
# - None -> no post-error limit
# - a positive integer like 1, 3, 5
# What it does:
# - Stops the run after this many post-processing errors.
# Example:
# - 3 means: after 3 broken posts, stop the run.
STOP_AFTER_POST_ERRORS = None


# ---------------------------------------------------------------------------
# ADVANCED AI OVERRIDES
# Leave these as None unless you want start.py to override .env values.
# Secrets still stay in .env.
# ---------------------------------------------------------------------------

# Options: None, "groq", "gemini"
# What it does:
# - Overrides AI_PROVIDER from .env for this run only.
AI_PROVIDER_OVERRIDE = None

# Options: None or a Groq model name string
# What it does:
# - Overrides GROQ_MODEL_NAME from .env for this run only.
GROQ_MODEL_NAME_OVERRIDE = None

# Options: None or a Gemini model name string
# What it does:
# - Overrides GEMINI_MODEL_NAME from .env for this run only.
GEMINI_MODEL_NAME_OVERRIDE = None

# Options: None or a positive integer
# What it does:
# - Maximum time to wait for one AI request before it is treated as failed.
AI_TIMEOUT_SECONDS_OVERRIDE = None

# Options: None or an integer >= 0
# What it does:
# - How many extra times to retry the AI call after the first failure.
# Example:
# - 0 means no retry
# - 2 means first try + 2 more tries
AI_RETRY_ATTEMPTS_OVERRIDE = None

# Options: None or a number >= 0
# What it does:
# - Delay between AI retries.
# Higher number:
# - slower retry cycle
# - can be more stable if provider is flaky
AI_RETRY_BACKOFF_SECONDS_OVERRIDE = None

# Options: None or a positive integer
# What it does:
# - Upper limit for the AI response size.
AI_MAX_OUTPUT_TOKENS_OVERRIDE = None

# Options: None or a float, usually between 0.0 and 1.0
# What it does:
# - Lower value -> more stable and predictable AI output
# - Higher value -> more varied output
# Recommended:
# - keep low for structured JSON responses
AI_TEMPERATURE_OVERRIDE = None


# ---------------------------------------------------------------------------
# ADVANCED FACEBOOK / BROWSER OVERRIDES
# Leave these as None unless you need to tune browser behavior.
# Chrome profile paths still belong in .env.
# ---------------------------------------------------------------------------

# Options: None, True, False
# What it does:
# - None  -> use HEADLESS from .env
# - True  -> run Chrome hidden in the background
# - False -> run Chrome visible on screen
# Recommended:
# - False for Facebook troubleshooting
# - True only if your saved profile works reliably in headless mode
HEADLESS_OVERRIDE = None

# Options: None or a positive integer
# What it does:
# - Maximum wait time for Facebook page actions, in milliseconds.
# Example:
# - 15000 = 15 seconds
FB_TIMEOUT_MS_OVERRIDE = None

# Options: None or an integer >= 0
# What it does:
# - How many extra times to retry Facebook feed scanning after a failure.
FB_RETRIES_OVERRIDE = None

# Options: None or a positive integer
# What it does:
# - How many scroll rounds the scanner may perform while collecting posts.
# Higher number:
# - can find more posts
# - takes longer
FB_MAX_SCROLL_ROUNDS_OVERRIDE = None

# Options: None or a positive integer
# What it does:
# - How long to pause after scrolling, in milliseconds.
# Higher number:
# - slower run
# - gives Facebook more time to load more posts
FB_SCROLL_PAUSE_MS_OVERRIDE = None


# ---------------------------------------------------------------------------
# .env VALUES YOU STILL CHANGE IN .env
# These are important, but they are not stored in this file because they are
# environment-specific or secret.
# ---------------------------------------------------------------------------

# AI_PROVIDER=groq or gemini
# GROQ_API_KEY=...
# GEMINI_API_KEY=...
# CHROME_USER_DATA_DIR=...
# CHROME_PROFILE_DIRECTORY=Default or Profile 1
