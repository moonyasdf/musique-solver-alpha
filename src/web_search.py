"""Google search client with Wikipedia-only filtering (Fixed)."""

from __future__ import annotations
import time
import logging
from dataclasses import dataclass
from typing import List, Optional
import requests

try:
    from googlesearch import search as google_search
except ImportError:
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
            raise SearchError("No search backend configured. Install googlesearch-python.")

    def _search_html(self, query: str, max_results: int) -> List[SearchResult]:
        results = []
        try:
            # FIX: Usamos 'stop' en lugar de 'num' y un generador para evitar errores de versión
            generator = google_search(query, stop=max_results, pause=2.0)
            for url in generator:
                results.append(SearchResult(title="Wikipedia Result", url=url))
                if len(results) >= max_results:
                    break
        except Exception as e:
            logger.warning(f"HTML search warning: {e}")
            
        if not results:
            logger.info("HTML search returned no results.")
            
        return results

    # (Mantener _search_google_custom y _search_serpapi igual si los usas, 
    # si no, el código de arriba es suficiente para scraping)
    def _search_google_custom(self, query: str, max_results: int) -> List[SearchResult]:
        # Placeholder para evitar errores si no se usa API Key
        return []

    def _search_serpapi(self, query: str, max_results: int) -> List[SearchResult]:
        # Placeholder
        return []