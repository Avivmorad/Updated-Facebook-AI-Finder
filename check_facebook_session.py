from dotenv import load_dotenv

from app.scraper.facebook_access_adapter import FacebookAccessAdapter


load_dotenv()


def main() -> None:
    adapter = FacebookAccessAdapter()
    with adapter.authenticated_session():
        print("LOGGED_IN")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"SESSION_CONFIG_ERROR: {exc}")
        print("NOT_LOGGED_IN")
    except RuntimeError as exc:
        print(f"SESSION_RUNTIME_ERROR: {exc}")
        print("NOT_LOGGED_IN")
    except Exception as exc:  # noqa: BLE001
        print(f"SESSION_UNKNOWN_ERROR: {exc}")
        print("NOT_LOGGED_IN")