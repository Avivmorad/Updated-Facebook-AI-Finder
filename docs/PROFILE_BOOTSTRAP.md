# Profile bootstrap

Use the `scripts/bootstrap_chrome_profile.py` helper to copy a Chrome profile
from your system into a repo-local folder that Playwright can use safely.

Example usage:

```bash
python scripts/bootstrap_chrome_profile.py "C:/Users/You/AppData/Local/Google/Chrome/User Data/Profile 5"
```

This will copy the profile to `data/chrome_user_data/Profile 5`.
Then set your `.env` or environment variable:

```
CHROME_USER_DATA_DIR=data/chrome_user_data
CHROME_PROFILE_DIRECTORY=Profile 5
```

If the destination already exists, rerun with `--overwrite` to replace it.
