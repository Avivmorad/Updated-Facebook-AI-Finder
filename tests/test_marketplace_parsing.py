import unittest

from app.scraper.platform_search_executor import PlatformSearchExecutor
from app.scraper.post_extractor import PostExtractor


class MarketplaceParsingTests(unittest.TestCase):
    def test_parse_card_text_extracts_price_title_and_region(self):
        parsed = PlatformSearchExecutor()._parse_card_text("240 US$\nIPHONE 13\nSan Jose, CA")

        self.assertEqual(parsed["price_text"], "240 US$")
        self.assertEqual(parsed["title"], "IPHONE 13")
        self.assertEqual(parsed["region"], "San Jose, CA")

    def test_page_title_fallback_extracts_listing_title(self):
        title = PostExtractor()._title_from_page_title(
            "IPHONE 13 - Cell Phones - San Jose | Marketplace של פייסבוק | Facebook"
        )

        self.assertEqual(title, "IPHONE 13")


if __name__ == "__main__":
    unittest.main()