"""Google search client with Wikipedia-only filtering."""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import List, Optional
import requests
from urllib.parse import urlencode

try:
    from googlesearch import search as google_search
except ImportError:  # pragma: no cover - optional dependency
    google_search = None


logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: Optional[str] = None


class SearchError(Exception):
    """Custom exception for search errors."""


class WikipediaSearchClient:
    """Google search client restricted to Wikipedia results."""

    GOOGLE_SEARCH_API = "https://www.googleapis.com/customsearch/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        cse_id: Optional[str] = None,
        serpapi_key: Optional[str] = None,
        rate_limit: float = 1.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = api_key
        self.cse_id = cse_id
        self.serpapi_key = serpapi_key
        self.rate_limit = rate_limit
        self.session = session or requests.Session()
        self._last_call: float = 0.0

    def _apply_site_filter(self, query: str) -> str:
        query = query.strip()
        if "site:wikipedia.org" not in query:
            query = f"site:wikipedia.org {query}"
        return query

    def _respect_rate_limit(self) -> None:
        now = time.time()
        elapsed = now - self._last_call
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_call = time.time()

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        query = self._apply_site_filter(query)
        self._respect_rate_limit()

        if self.api_key and self.cse_id:
            return self._search_google_custom(query, max_results)
        elif self.serpapi_key:
            return self._search_serpapi(query, max_results)
        elif google_search is not None:
            return self._search_html(query, max_results)
        else:
            raise SearchError(
                "No search backend configured. Provide GOOGLE_API_KEY & GOOGLE_CSE_ID, SERPAPI_KEY, or install googlesearch-python."
            )

    def _search_google_custom(self, query: str, max_results: int) -> List[SearchResult]:
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": max(1, min(max_results, 10)),
        }
        response = self.session.get(self.GOOGLE_SEARCH_API, params=params, timeout=30)
        if response.status_code != 200:
            raise SearchError(f"Google Custom Search API error: {response.status_code} {response.text}")

        data = response.json()
        items = data.get("items", [])
        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet"),
            )
            for item in items
        ]

    def _search_serpapi(self, query: str, max_results: int) -> List[SearchResult]:
        params = {
            "engine": "google",
            "q": query,
            "num": max_results,
            "api_key": self.serpapi_key,
        }
        response = self.session.get("https://serpapi.com/search", params=params, timeout=30)
        if response.status_code != 200:
            raise SearchError(f"SerpAPI error: {response.status_code} {response.text}")

        organic_results = response.json().get("organic_results", [])
        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet"),
            )
            for item in organic_results[:max_results]
        ]

    def _search_html(self, query: str, max_results: int) -> List[SearchResult]:
        if google_search is None:
            raise SearchError("googlesearch-python not installed")

        results = []
        try:
            for url in google_search(query, num=max_results, stop=max_results):
                results.append(SearchResult(title="", url=url))
        except Exception as e:  # pragma: no cover - dependent on external service
            raise SearchError(f"HTML search failed: {e}")
        return results
