"""Wikipedia-only search client that returns lightweight metadata for selector logic."""

from __future__ import annotations

import logging
import re
import textwrap
import time
import urllib.parse
from dataclasses import dataclass
from html import unescape
from typing import Callable, List, Optional

import requests

try:  # Optional dependency for HTML scraping fallback
    from googlesearch import search as google_search
except ImportError:  # pragma: no cover - fallback not available during tests
    google_search = None

logger = logging.getLogger(__name__)

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
SERP_API_URL = "https://serpapi.com/search"
DEFAULT_HEADERS = {"User-Agent": "musique-solver/0.2 (research@musique-solver)"}


@dataclass
class SearchResult:
    """Container for lightweight metadata returned to the agent."""

    title: str
    url: str
    snippet: Optional[str] = None


class SearchError(Exception):
    """Custom exception for search errors."""


class WikipediaSearchClient:
    """Search client that ONLY returns Wikipedia metadata (title/url/snippet)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cse_id: Optional[str] = None,
        serpapi_key: Optional[str] = None,
        rate_limit: float = 1.0,
    ) -> None:
        self.api_key = api_key
        self.cse_id = cse_id
        self.serpapi_key = serpapi_key
        self.rate_limit = rate_limit
        self._last_call: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Return lightweight metadata for Wikipedia pages relevant to the query."""
        if not query:
            raise SearchError("Empty query provided to WikipediaSearchClient")

        filtered_query = self._apply_site_filter(query)
        self._respect_rate_limit()

        backends = self._get_backends()
        errors = []
        for backend in backends:
            try:
                results = backend(filtered_query, max_results)
                if results:
                    # Ensure snippets are at most two lines to avoid flooding
                    for result in results:
                        if result.snippet:
                            result.snippet = self._format_snippet(result.snippet)
                    return results[:max_results]
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning(f"Search backend {backend.__name__} failed: {exc}")
                errors.append(str(exc))

        raise SearchError(
            "All configured search backends failed. "
            + ("; ".join(errors) if errors else "No backend available.")
        )

    # ------------------------------------------------------------------
    # Backend selection
    # ------------------------------------------------------------------
    def _get_backends(self) -> List[Callable[[str, int], List[SearchResult]]]:
        backends: List[Callable[[str, int], List[SearchResult]]] = []
        if self.api_key and self.cse_id:
            backends.append(self._search_google_custom)
        if self.serpapi_key:
            backends.append(self._search_serpapi)
        # Wikipedia's own search API is reliable and returns snippets
        backends.append(self._search_wikipedia_api)
        if google_search is not None:
            backends.append(self._search_html)
        return backends

    # ------------------------------------------------------------------
    # Backend implementations
    # ------------------------------------------------------------------
    def _search_google_custom(self, query: str, max_results: int) -> List[SearchResult]:
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": min(max_results, 10),
        }
        response = requests.get(GOOGLE_CSE_URL, params=params, headers=DEFAULT_HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        results: List[SearchResult] = []
        for item in items:
            link = item.get("link", "")
            if "wikipedia.org" not in link:
                continue
            title = item.get("title", "Wikipedia Result")
            snippet = item.get("snippet", "")
            results.append(SearchResult(title=title, url=link, snippet=snippet))
            if len(results) >= max_results:
                break
        return results

    def _search_serpapi(self, query: str, max_results: int) -> List[SearchResult]:
        params = {
            "engine": "google",
            "q": query,
            "api_key": self.serpapi_key,
            "num": min(max_results, 10),
        }
        response = requests.get(SERP_API_URL, params=params, headers=DEFAULT_HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()

        organic_results = data.get("organic_results", [])
        results: List[SearchResult] = []
        for item in organic_results:
            link = item.get("link", "")
            if "wikipedia.org" not in link:
                continue
            title = item.get("title", "Wikipedia Result")
            snippet = item.get("snippet", item.get("snippet_highlighted_words", ""))
            if isinstance(snippet, list):
                snippet = " ".join(snippet)
            results.append(SearchResult(title=title, url=link, snippet=snippet))
            if len(results) >= max_results:
                break
        return results

    def _search_wikipedia_api(self, query: str, max_results: int) -> List[SearchResult]:
        stripped_query = self._strip_site_filter(query)
        params = {
            "action": "query",
            "list": "search",
            "srsearch": stripped_query,
            "utf8": 1,
            "format": "json",
            "srlimit": max_results,
        }
        response = requests.get(WIKIPEDIA_API_URL, params=params, headers=DEFAULT_HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()

        search_results = data.get("query", {}).get("search", [])
        results: List[SearchResult] = []
        for item in search_results:
            title = item.get("title", "Wikipedia Result")
            snippet = item.get("snippet", "")
            url = self._build_wikipedia_url(title)
            results.append(SearchResult(title=title, url=url, snippet=snippet))
        return results

    def _search_html(self, query: str, max_results: int) -> List[SearchResult]:  # pragma: no cover - requires google_search
        if google_search is None:
            return []

        results: List[SearchResult] = []
        try:
            # Try different parameter names for different googlesearch versions
            try:
                generator = google_search(query, num_results=max_results, pause=2.0)
            except TypeError:
                try:
                    generator = google_search(query, stop=max_results, pause=2.0)
                except TypeError:
                    # Fallback to simple call
                    generator = google_search(query)
            
            for url in generator:
                if "wikipedia.org" not in url:
                    continue
                title = self._extract_title_from_url(url)
                snippet = self._fetch_extract(title)
                results.append(SearchResult(title=title, url=url, snippet=snippet))
                if len(results) >= max_results:
                    break
        except Exception as exc:
            logger.warning(f"HTML search fallback failed: {exc}")
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _apply_site_filter(self, query: str) -> str:
        query = query.strip()
        if "site:wikipedia.org" not in query:
            query = f"site:wikipedia.org {query}"
        return query

    def _strip_site_filter(self, query: str) -> str:
        return query.replace("site:wikipedia.org", "").strip()

    def _respect_rate_limit(self) -> None:
        now = time.time()
        elapsed = now - self._last_call
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_call = time.time()

    def _build_wikipedia_url(self, title: str) -> str:
        slug = title.replace(" ", "_")
        return f"https://en.wikipedia.org/wiki/{urllib.parse.quote(slug)}"

    def _extract_title_from_url(self, url: str) -> str:
        if "/wiki/" in url:
            slug = url.split("/wiki/")[-1]
            return urllib.parse.unquote(slug.replace("_", " "))
        return "Wikipedia Article"

    def _fetch_extract(self, title: str) -> str:
        if not title:
            return ""
        params = {
            "action": "query",
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "titles": title,
            "format": "json",
        }
        try:
            response = requests.get(WIKIPEDIA_API_URL, params=params, headers=DEFAULT_HEADERS, timeout=20)
            response.raise_for_status()
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return ""
            extract = next(iter(pages.values())).get("extract", "")
            return self._format_snippet(extract)
        except Exception:
            return ""

    def _format_snippet(self, raw_text: str) -> str:
        if not raw_text:
            return ""
        text = unescape(re.sub(r"<[^>]+>", " ", raw_text))
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""
        text = text[:280].strip()
        wrapped = textwrap.fill(text, width=100)
        lines = wrapped.splitlines()
        if len(lines) > 2:
            wrapped = "\n".join(lines[:2])
        return wrapped
