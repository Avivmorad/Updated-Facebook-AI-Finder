def bootstrap_facebook_session() -> None:
    raise RuntimeError(
        "bootstrap_facebook_session is deprecated. Automatic Facebook login was removed. "
        "Use an existing Chrome profile that is already logged in, configure CHROME_USER_DATA_DIR and "
        "CHROME_PROFILE_DIRECTORY, then run python check_facebook_session.py."
    )