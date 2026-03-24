import unittest
from unittest.mock import patch

from app.scraper.facebook_access_adapter import FacebookAccessAdapter, FacebookAuthenticationRequiredError
from app.scraper.facebook_login_state_detector import FacebookLoginStateDetector, is_logged_in_to_facebook
from config.platform_access_config import PlatformAccessConfig


class _FakeNode:
    def __init__(self, text: str) -> None:
        self._text = text

    def inner_text(self) -> str:
        return self._text


class _FakeContext:
    def __init__(self, cookies=None) -> None:
        self._cookies = list(cookies or [])

    def cookies(self):
        return list(self._cookies)


class _FakePage:
    def __init__(self, url: str, title: str = "", body_text: str = "", cookies=None, selectors=None) -> None:
        self.url = url
        self._title = title
        self._body_text = body_text
        self.context = _FakeContext(cookies=cookies)
        self._selectors = dict(selectors or {})
        self.goto_calls = []

    def title(self) -> str:
        return self._title

    def query_selector(self, selector: str):
        if selector == "body":
            return _FakeNode(self._body_text)
        return self._selectors.get(selector)

    def goto(self, url: str, wait_until: str, timeout: int):
        self.goto_calls.append({"url": url, "wait_until": wait_until, "timeout": timeout})
        self.url = url
        return None

    def wait_for_timeout(self, value: int):
        return value


class _FakeSession:
    def __init__(self, page) -> None:
        self.page = page
        self.closed = False

    def close(self):
        self.closed = True


class _FakeSessionFactory:
    def __init__(self, page) -> None:
        self.page = page
        self.last_session = None

    def __call__(self, config):
        factory = self

        class _Manager:
            def open(self_nonlocal):
                factory.last_session = _FakeSession(factory.page)
                return factory.last_session

        return _Manager()


class FacebookLoginStateDetectorTests(unittest.TestCase):
    def test_detects_logged_in_when_auth_cookies_exist(self):
        page = _FakePage(
            url="https://www.facebook.com/marketplace/",
            title="Facebook",
            body_text="Marketplace feed",
            cookies=[{"name": "c_user"}, {"name": "xs"}],
        )

        detector = FacebookLoginStateDetector()

        self.assertTrue(detector.is_logged_in_to_facebook(page))
        self.assertTrue(is_logged_in_to_facebook(page))

    def test_detects_login_page_as_not_logged_in(self):
        page = _FakePage(
            url="https://www.facebook.com/login",
            title="Log in to Facebook",
            body_text="",
            selectors={"input[name='email']": _FakeNode("")},
        )

        result = FacebookLoginStateDetector().detect_login_state(page)

        self.assertFalse(result.is_logged_in)
        self.assertEqual(result.state, "login_page")

    def test_detects_checkpoint_as_not_logged_in(self):
        page = _FakePage(
            url="https://www.facebook.com/checkpoint/123",
            title="Checkpoint",
            body_text="checkpoint",
        )

        result = FacebookLoginStateDetector().detect_login_state(page)

        self.assertFalse(result.is_logged_in)
        self.assertEqual(result.state, "checkpoint")

    def test_detects_blank_page_as_not_logged_in(self):
        page = _FakePage(url="about:blank", title="", body_text="")

        result = FacebookLoginStateDetector().detect_login_state(page)

        self.assertFalse(result.is_logged_in)
        self.assertEqual(result.state, "blank_page")


class FacebookAccessAdapterTests(unittest.TestCase):
    def test_authenticated_session_raises_when_not_logged_in(self):
        page = _FakePage(url="https://www.facebook.com/login", title="Log in to Facebook", body_text="")
        factory = _FakeSessionFactory(page)
        config = PlatformAccessConfig(facebook_home_url="https://www.facebook.com/")

        with patch("app.scraper.facebook_access_adapter.BrowserSessionManager", new=factory):
            adapter = FacebookAccessAdapter(config=config)

            with self.assertRaises(FacebookAuthenticationRequiredError):
                with adapter.authenticated_session():
                    self.fail("session should not be yielded when not logged in")

        self.assertEqual(page.goto_calls[0]["url"], "https://www.facebook.com/")
        self.assertFalse(any("/login" in item["url"] for item in page.goto_calls))
        self.assertTrue(factory.last_session.closed)

    def test_authenticated_session_yields_when_logged_in(self):
        page = _FakePage(
            url="https://www.facebook.com/marketplace/",
            title="Facebook",
            body_text="Marketplace feed",
            cookies=[{"name": "c_user"}, {"name": "xs"}],
        )
        factory = _FakeSessionFactory(page)
        config = PlatformAccessConfig(facebook_home_url="https://www.facebook.com/")

        with patch("app.scraper.facebook_access_adapter.BrowserSessionManager", new=factory):
            adapter = FacebookAccessAdapter(config=config)

            with adapter.authenticated_session() as session:
                self.assertIs(session.page, page)

        self.assertTrue(factory.last_session.closed)