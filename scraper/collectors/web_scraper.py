"""
Generic web scraper for layoff data from news/article pages.

Scrapes any HTML page, finds article-like elements, filters by layoff
keywords, and creates ScrapedArticle records for downstream processing.
"""

import hashlib
import logging
import re
from urllib.parse import urljoin

from django.utils.timezone import now

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup, Tag

from scraper.models import DataSource, ScrapedArticle
from scraper.pipeline import hash_url

logger = logging.getLogger(__name__)

# Common CSS/HTML patterns that identify article/list containers
ARTICLE_SELECTORS = [
    'article',
    '[class*="article"]',
    '[class*="post"]',
    '[class*="story"]',
    '[class*="teaser"]',
    '[class*="card"]',
    '[class*="headline"]',
    '[class*="entry"]',
    'li',
]

# Same keywords used in the RSS feed collector
LAYOFF_KEYWORDS = [
    'layoff', 'lay off', 'laid off', 'furlough',
    'workforce reduction', 'job cut', 'cutting jobs',
    'headcount reduction',
]


def _find_article_elements(soup: BeautifulSoup) -> list[Tag]:
    """Find all elements that look like article containers on the page."""
    found = []
    seen = set()

    for selector in ARTICLE_SELECTORS:
        elements = soup.select(selector)
        for el in elements:
            el_id = id(el)
            if el_id in seen:
                continue
            seen.add(el_id)

            # Must contain a link with text
            link = el.find('a')
            if not link or not link.get_text(strip=True):
                continue

            text = el.get_text(' ', strip=True)
            # Skip very short or very long blocks (noise)
            if len(text) < 15 or len(text) > 2000:
                continue

            # Must have a reasonable text-to-link ratio (mostly text, not just links)
            link_text_len = sum(len(a.get_text(strip=True)) for a in el.find_all('a'))
            if link_text_len > len(text) * 0.8:
                continue

            found.append(el)

    # Deduplicate by first link href to keep only one element per article
    seen_urls = set()
    unique = []
    for el in found:
        link = el.find('a')
        if not link:
            continue
        href = link.get('href', '')
        if href in seen_urls:
            continue
        seen_urls.add(href)
        unique.append(el)

    return unique


def _extract_article_data(el: Tag, base_url: str) -> tuple[str, str]:
    """Extract (title, full_url) from an article-like element."""
    link = el.find('a')
    href = link.get('href', '')
    full_url = urljoin(base_url, href) if href else ''

    # Title: use link text, or heading inside the element, or element text
    title = link.get_text(' ', strip=True)
    if not title or len(title) < 10:
        heading = el.find(['h1', 'h2', 'h3', 'h4'])
        if heading:
            title = heading.get_text(' ', strip=True)
    if not title or len(title) < 10:
        title = el.get_text(' ', strip=True)

    # Clean up whitespace
    title = re.sub(r'\s+', ' ', title).strip()

    return title, full_url


def scrape_web_source(source: DataSource) -> dict:
    """
    Scrape a web DataSource for layoff-related articles.

    Returns dict with counts of articles found, created, and any errors.
    """
    logger.info(f'Scraping web source: {source.name} ({source.url})')

    session = requests.Session()
    retries = Retry(total=2, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
    })

    try:
        resp = session.get(source.url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'HTTP error scraping {source.name}: {e}')
        source.consecutive_failures += 1
        source.save()
        return {'source': source.name, 'found': 0, 'created': 0, 'error': str(e)}

    soup = BeautifulSoup(resp.text, 'lxml')
    elements = _find_article_elements(soup)
    logger.info(f'Found {len(elements)} article-like elements on {source.name}')

    articles_found = 0
    articles_created = 0

    for el in elements:
        title, full_url = _extract_article_data(el, source.url)

        if not title or not full_url:
            continue

        # Check for layoff keywords
        text_lower = title.lower()
        if not any(kw in text_lower for kw in LAYOFF_KEYWORDS):
            continue

        articles_found += 1

        # Dedup by URL hash
        url_hash = hash_url(full_url)
        if ScrapedArticle.objects.filter(url_hash=url_hash).exists():
            continue

        content_el = el.find(['p', 'div', 'span'], class_=re.compile(
            r'(summary|description|excerpt|content|text|snippet)',
            re.I,
        ))
        content = content_el.get_text(strip=True) if content_el else title

        ScrapedArticle.objects.create(
            url=full_url,
            url_hash=url_hash,
            title=title,
            content_hash=hashlib.sha256(content.encode('utf-8')).hexdigest(),
            source=source,
        )
        articles_created += 1

    source.last_fetched = now()
    source.consecutive_failures = 0
    source.save()

    logger.info(
        f'Web scrape {source.name}: {articles_found} found, {articles_created} new'
    )
    return {
        'source': source.name,
        'elements_found': len(elements),
        'layoff_matches': articles_found,
        'created': articles_created,
    }
