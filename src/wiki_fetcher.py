"""Wikipedia article fetcher with Markdown conversion."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
import html2text

logger = logging.getLogger(__name__)

@dataclass
class ArticleStructure:
    url: str
    title: str
    summary: str  # The lead paragraph(s) before the first section
    sections: List[str]  # List of section headings (Table of Contents)

class WikipediaArticleFetcher:
    """Fetches Wikipedia articles and allows structured access (TOC vs Content)."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'MusiqueSolver/0.2 (Research Agent)'
        })
        self._cache: Dict[str, BeautifulSoup] = {}

    def _get_soup(self, url: str) -> BeautifulSoup:
        if url in self._cache:
            return self._cache[url]
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            self._cleanup_soup(soup)
            self._cache[url] = soup
            return soup
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise

    def get_article_structure(self, url: str) -> ArticleStructure:
        """Returns the 'Skeleton' of the article: Title, Summary, and TOC."""
        soup = self._get_soup(url)
        
        # 1. Extract Title
        title_tag = soup.find('h1', {'id': 'firstHeading'})
        title = title_tag.get_text().strip() if title_tag else "Unknown Title"

        # 2. Extract Lead Section (Summary) - everything before the first h2
        content_div = soup.find('div', {'id': 'mw-content-text'})
        summary_text = ""
        if content_div:
            # Get the parser output div
            parser_output = content_div.find('div', class_='mw-parser-output')
            if parser_output:
                # Iterate until first h2
                lead_elements = []
                for element in parser_output.children:
                    if element.name == 'h2':
                        break
                    if element.name == 'p':
                        lead_elements.append(str(element))
                summary_text = self._html_to_markdown("".join(lead_elements))

        # 3. Extract Sections (H2 headers)
        sections = []
        if content_div:
            for h2 in content_div.find_all('h2'):
                span = h2.find('span', class_='mw-headline')
                if span:
                    sections.append(span.get_text().strip())

        return ArticleStructure(url=url, title=title, summary=summary_text, sections=sections)

    def get_section_content(self, url: str, section_title: str) -> str:
        """Returns the full text of a specific section."""
        soup = self._get_soup(url)
        content_div = soup.find('div', {'id': 'mw-content-text'})
        
        if not content_div:
            return ""

        # Find the h2 with the specific span id or text
        target_h2 = None
        for h2 in content_div.find_all('h2'):
            if section_title.lower() in h2.get_text().lower():
                target_h2 = h2
                break
        
        if not target_h2:
            return f"Section '{section_title}' not found."

        # Collect all siblings until the next h2
        section_html = []
        for sibling in target_h2.next_siblings:
            if sibling.name == 'h2':
                break
            if sibling.name in ['p', 'ul', 'ol', 'dl', 'table', 'div']:
                section_html.append(str(sibling))

        return self._html_to_markdown("".join(section_html))

    def _cleanup_soup(self, soup: BeautifulSoup):
        """Removes noise (navboxes, references, styles) from the soup."""
        for element in soup.find_all(['script', 'style', 'sup', 'div'], 
                                     class_=['navbox', 'reflist', 'reference', 'mw-editsection']):
            element.decompose()

    def _html_to_markdown(self, html: str) -> str:
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
