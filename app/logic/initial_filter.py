from typing import Dict, List

from app.models.input_models import SearchRequest


class InitialFilter:
    def filter_posts(self, posts: List[Dict[str, object]], request: SearchRequest) -> List[Dict[str, object]]:
        filtered: List[Dict[str, object]] = []
        query_terms = self._query_terms(request)

        for post in posts:
            title = str(post.get("title", "")).lower().strip()
            snippet = str(post.get("snippet", "")).lower().strip()
            url = str(post.get("url", "")).strip()
            searchable_text = " ".join(part for part in [title, snippet] if part).strip()
            is_marketplace_item = "/marketplace/item/" in url

            if searchable_text and query_terms and not is_marketplace_item and not any(
                term in searchable_text for term in query_terms
            ):
                continue

            if any(forbidden.lower() in searchable_text for forbidden in request.forbidden_words):
                continue

            filtered.append(post)

        return filtered

    def _query_terms(self, request: SearchRequest) -> List[str]:
        terms: List[str] = []

        for source in [request.query_text, *request.tags, *request.secondary_attributes]:
            normalized = str(source).lower().strip()
            if not normalized:
                continue

            parts = [part for part in normalized.split() if len(part) >= 2]
            if normalized not in terms:
                terms.append(normalized)

            for part in parts:
                if part not in terms:
                    terms.append(part)

        return terms
