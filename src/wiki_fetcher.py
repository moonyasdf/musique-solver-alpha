"""Wikipedia article fetcher using MediaWiki API (Reliable Structure)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Dict
import requests
import html2text

logger = logging.getLogger(__name__)

@dataclass
class ArticleStructure:
    url: str
    title: str
    summary: str  # Lead section converted to Markdown
    sections: List[str]  # List of section headings (Table of Contents)

class WikipediaArticleFetcher:
    """Fetches Wikipedia articles using the stable MediaWiki API."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'MusiqueSolver/0.3 (Research Agent; contact: research@musique-solver.local)'
        })
        self.api_url = "https://en.wikipedia.org/w/api.php"
        self._cache: Dict[str, dict] = {} # Simple cache for section maps

    def get_article_structure(self, url: str) -> ArticleStructure:
        """
        Returns the 'Skeleton' of the article: Title, Summary (Lead), and TOC.
        Uses action=parse&prop=sections|text&section=0
        """
        title_slug = self._extract_title_slug(url)
        
        try:
            # 1. Fetch Sections (ToC)
            # We use prop=sections despite deprecation warning because it returns 
            # a flat list with indexes, which is perfect for programmatic access.
            params = {
                "action": "parse",
                "page": title_slug,
                "prop": "sections",
                "format": "json",
                "redirects": 1,
                "origin": "*"
            }
            resp = self.session.get(self.api_url, params=params, timeout=10)
            
            # Handle graceful failures if API fails
            if resp.status_code != 200:
                logger.error(f"API returned {resp.status_code}")
                return ArticleStructure(url, title_slug, "Error fetching article structure.", [])

            data = resp.json()
            
            if "error" in data:
                logger.error(f"API Error for {url}: {data['error']}")
                return ArticleStructure(url, title_slug, f"API Error: {data['error'].get('info', 'Unknown')}", [])

            parse_data = data.get("parse", {})
            real_title = parse_data.get("title", title_slug.replace("_", " "))
            
            # Extract section names
            sections_data = parse_data.get("sections", [])
            sections = [s['line'] for s in sections_data]
            
            # Cache the section map for later use in get_section_content
            self._cache[url] = sections_data

            # 2. Fetch Lead Section (Section 0)
            params_lead = {
                "action": "parse",
                "page": title_slug,
                "prop": "text",
                "section": 0,
                "format": "json",
                "redirects": 1,
                "origin": "*"
            }
            resp_lead = self.session.get(self.api_url, params=params_lead, timeout=10)
            lead_html = resp_lead.json().get("parse", {}).get("text", {}).get("*", "")
            
            summary_text = self._html_to_markdown(lead_html)

            return ArticleStructure(
                url=url, 
                title=real_title, 
                summary=summary_text, 
                sections=sections
            )

        except Exception as e:
            logger.error(f"Failed to fetch structure for {url}: {e}")
            return ArticleStructure(url, title_slug, f"Error: {str(e)}", [])

    def get_section_content(self, url: str, section_name: str) -> str:
        """
        Returns the full text of a specific section by mapping name to index.
        """
        title_slug = self._extract_title_slug(url)
        
        # Ensure we have the section map
        if url not in self._cache:
            # Refresh structure to populate cache
            self.get_article_structure(url)
            
        sections_data = self._cache.get(url, [])
        
        # Fuzzy match for section index
        target_index = None
        normalized_target = section_name.lower().strip()
        
        # 1. Check for Lead/Intro requests
        if normalized_target in ["", "lead", "introduction", "summary", "intro", "0"]:
            target_index = 0
        else:
            # 2. Match against TOC
            for sec in sections_data:
                # Clean HTML tags from section line just in case (API usually sends clean text in 'line')
                sec_line = sec['line'].lower()
                # Remove common HTML entities if present
                sec_line = sec_line.replace("&nbsp;", " ")
                
                if normalized_target == sec_line or normalized_target in sec_line:
                    target_index = sec['index']
                    break
        
        if target_index is None:
            available = [s['line'] for s in sections_data[:5]] # Show first 5 suggestions
            return f"Section '{section_name}' not found. Available sections: {available}..."

        try:
            params = {
                "action": "parse",
                "page": title_slug,
                "prop": "text",
                "section": target_index,
                "format": "json",
                "redirects": 1,
                "origin": "*"
            }
            resp = self.session.get(self.api_url, params=params, timeout=10)
            html_content = resp.json().get("parse", {}).get("text", {}).get("*", "")
            
            if not html_content:
                return f"Section '{section_name}' returned empty content."
                
            return self._html_to_markdown(html_content)
            
        except Exception as e:
            logger.error(f"Failed to fetch section {section_name}: {e}")
            return f"Error fetching section: {e}"

    def _extract_title_slug(self, url: str) -> str:
        """Extracts 'Mankatha_(soundtrack)' from url."""
        if "/wiki/" in url:
            # Decode URL mostly for logging/debugging, but API handles encoded fine usually
            # However, extracting the raw slug is safer
            return url.split("/wiki/")[-1]
        return url

    def _html_to_markdown(self, html: str) -> str:
        if not html:
            return ""
        h = html2text.HTML2Text()
        h.ignore_links = False 
        h.ignore_images = True
        h.body_width = 0
        h.unicode_snob = True
        h.decode_errors = 'ignore'
        result = h.handle(html).strip()
        
        # Remove excessive newlines
        import re
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result