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
    except Exception:
        print("NOT_LOGGED_IN")