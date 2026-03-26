from app.extraction.post_normalizer import normalize_post_data


def test_normalize_post_data_keeps_only_allowed_fields():
    result = normalize_post_data(
        {
            "post_link": "https://www.facebook.com/groups/1/posts/2",
            "post_text": "iPhone 13 for sale",
            "images": ["https://img/1", "https://img/1", "https://img/2"],
            "publish_date": "2 hours ago",
            "seller_name": "ignored",
            "comments": ["ignored"],
        }
    )

    assert result == {
        "post_link": "https://www.facebook.com/groups/1/posts/2",
        "post_text": "iPhone 13 for sale",
        "images": ["https://img/1", "https://img/2"],
        "publish_date": "2 hours ago",
    }
