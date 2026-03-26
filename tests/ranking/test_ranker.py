from app.ranking.ranker import PostRanker


def test_ranker_sorts_by_match_score_only():
    ranker = PostRanker()
    ranked = ranker.rank(
        [
            {
                "post": {"post_link": "https://example.com/low"},
                "ai_match": {"match_score": 20, "match_reason": "low"},
            },
            {
                "post": {"post_link": "https://example.com/high"},
                "ai_match": {"match_score": 95, "match_reason": "high"},
            },
            {
                "post": {"post_link": "https://example.com/mid"},
                "ai_match": {"match_score": 55, "match_reason": "mid"},
            },
        ]
    )

    assert [item["post"]["post_link"] for item in ranked] == [
        "https://example.com/high",
        "https://example.com/mid",
        "https://example.com/low",
    ]
    assert [item["rank"] for item in ranked] == [1, 2, 3]
