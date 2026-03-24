from dotenv import load_dotenv

from app.scraper.session_bootstrap import bootstrap_facebook_session


load_dotenv()


if __name__ == "__main__":
    bootstrap_facebook_session()