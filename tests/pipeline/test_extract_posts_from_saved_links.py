import json

from scripts.extract_posts_from_saved_links import _load_post_links


def test_load_post_links_accepts_list_payload(tmp_path):
    path = tmp_path / "links.json"
    path.write_text(json.dumps(["https://a", "https://b"]), encoding="utf-8")

    links = _load_post_links(path)
    assert links == ["https://a", "https://b"]


def test_load_post_links_accepts_object_payload(tmp_path):
    path = tmp_path / "links.json"
    path.write_text(json.dumps({"post_links": ["https://a"]}), encoding="utf-8")

    links = _load_post_links(path)
    assert links == ["https://a"]

